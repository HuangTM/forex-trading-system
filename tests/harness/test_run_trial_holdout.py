"""OOS-holdout enforcement in run_trial (closes the bypass where run_trial
ignored a configured holdout and silently trained/tested on OOS rows).

Normal runs keep only PRE-holdout (in-sample) rows; final_oos_test reads the
full series via load_parquet(oos_mode=True). These cover the in-sample filter.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from forex_system.harness.run_trial import _apply_holdout_filter, _slice_to_oos


def _daily(start: str, n: int) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": range(n)}, index=idx)


def test_none_holdout_is_unchanged():
    df = _daily("2021-01-01", 100)
    assert _apply_holdout_filter(df, None) is df


def test_filters_to_pre_holdout_rows():
    df = _daily("2021-01-01", 300)  # spans well past 2021-06-01
    cutoff = "2021-06-01"
    out = _apply_holdout_filter(df, cutoff)
    assert len(out) < len(df)
    assert out.index.max() < pd.Timestamp(cutoff, tz="UTC")  # strictly pre-cutoff
    # the row exactly at/after the cutoff is excluded
    assert not (out.index >= pd.Timestamp(cutoff, tz="UTC")).any()


def test_future_holdout_keeps_all():
    df = _daily("2021-01-01", 100)
    out = _apply_holdout_filter(df, "2030-01-01")
    assert len(out) == len(df)


def test_naive_cutoff_against_tz_aware_index():
    """A naive ISO date string must compare cleanly against a tz-aware UTC index."""
    df = _daily("2021-01-01", 200)
    out = _apply_holdout_filter(df, "2021-03-01")  # naive string, tz-aware index
    assert 0 < len(out) < len(df)
    assert out.index.tz is not None  # tz preserved


def test_oos_slice_exactly_complements_in_sample_filter():
    """in-sample (< cutoff) and OOS (>= cutoff) must partition the data with no
    overlap and no gap."""
    df = _daily("2021-01-01", 300)
    cut = "2021-06-01"
    ins = _apply_holdout_filter(df, cut)
    oos, _ = _slice_to_oos(df, [], cut)
    assert len(ins) + len(oos) == len(df)
    assert ins.index.max() < pd.Timestamp(cut, tz="UTC") <= oos.index.min()


def test_oos_slice_keeps_only_trades_entered_in_oos():
    df = _daily("2021-01-01", 300)
    trades = [
        SimpleNamespace(entry_time=pd.Timestamp("2021-03-01", tz="UTC")),  # in-sample
        SimpleNamespace(entry_time=pd.Timestamp("2021-07-01", tz="UTC")),  # OOS
        SimpleNamespace(entry_time=None),                                   # guard: None skipped
    ]
    _, oos_trades = _slice_to_oos(df, trades, "2021-06-01")
    assert len(oos_trades) == 1
    assert oos_trades[0].entry_time == pd.Timestamp("2021-07-01", tz="UTC")
