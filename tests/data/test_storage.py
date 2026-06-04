"""Tests for Parquet storage."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forex_system.core.errors import DataError
from forex_system.data.storage import (
    _assert_price_range,
    list_available,
    load_parquet,
    save_parquet,
)


def test_save_and_load(sample_ohlcv, tmp_path):
    save_parquet(sample_ohlcv, "EURUSD", "daily", str(tmp_path))
    loaded = load_parquet("EURUSD", "daily", str(tmp_path))
    assert len(loaded) == len(sample_ohlcv)
    pd.testing.assert_frame_equal(loaded, sample_ohlcv, check_freq=False)


def test_load_missing(tmp_path):
    with pytest.raises(DataError, match="No data found"):
        load_parquet("XXXYYY", "daily", str(tmp_path))


def test_list_available(sample_ohlcv, tmp_path):
    save_parquet(sample_ohlcv, "EURUSD", "daily", str(tmp_path))
    save_parquet(sample_ohlcv, "USDJPY", "daily", str(tmp_path))
    available = list_available(str(tmp_path))
    assert len(available) == 2
    symbols = {a["pair"] for a in available}
    assert "EURUSD" in symbols
    assert "USDJPY" in symbols


# ---------------------------------------------------------------------------
# _assert_price_range — table-driven inversion tests (PR FINDING-3).
# Each case names the invariant it locks, not just the input.
# ---------------------------------------------------------------------------

_DUMMY = Path("dummy.parquet")


def _close(values) -> pd.DataFrame:
    return pd.DataFrame({"close": values})


def test_range_rejects_close_above_upper_bound():
    # USDJPY upper bound 245 — a max above it is corruption (or wrong dir).
    with pytest.raises(DataError, match="sanity check FAILED"):
        _assert_price_range(_close([100.0, 300.0, 120.0]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_close_below_lower_bound():
    # USDJPY lower bound 20 — the synthetic 5–8 series must be caught here.
    with pytest.raises(DataError, match="sanity check FAILED"):
        _assert_price_range(_close([5.0, 6.0, 7.5]), "USDJPY", "daily", _DUMMY)


def test_range_accepts_in_bounds_close():
    # Real-scale USDJPY must pass cleanly (no false positive).
    _assert_price_range(_close([80.0, 150.0, 161.0]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_all_nan_close():
    # FINDING-1: NaN comparisons are False, so an all-NaN series would pass the
    # gate OPEN unless guarded explicitly. It must fail closed.
    with pytest.raises(DataError, match="non-finite"):
        _assert_price_range(_close([np.nan, np.nan, np.nan]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_partial_nan_close():
    with pytest.raises(DataError, match="non-finite"):
        _assert_price_range(_close([100.0, np.nan, 120.0]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_infinite_close():
    with pytest.raises(DataError, match="non-finite"):
        _assert_price_range(_close([100.0, np.inf, 120.0]), "USDJPY", "daily", _DUMMY)
    with pytest.raises(DataError, match="non-finite"):
        _assert_price_range(_close([100.0, -np.inf, 120.0]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_empty_close():
    with pytest.raises(DataError, match="empty"):
        _assert_price_range(_close([]), "USDJPY", "daily", _DUMMY)


def test_range_rejects_missing_close_column():
    # FINDING-5: an OHLCV frame with no close column is itself malformed.
    with pytest.raises(DataError, match="no 'close' column"):
        _assert_price_range(pd.DataFrame({"open": [1.0, 2.0]}), "USDJPY", "daily", _DUMMY)


def test_range_passes_through_unlisted_pair():
    # A pair with no registered bounds is not range-checked (unknown convention),
    # but finite data must not raise.
    _assert_price_range(_close([9.0, 14.0]), "AUDUSD", "daily", _DUMMY)


def test_range_skips_listed_skip_pair_but_still_rejects_non_finite():
    # 4h skip-pair: finite data passes (range unguarded by design)...
    _assert_price_range(_close([5.0, 8.0]), "USDJPY", "4h", _DUMMY)
    # ...but the basic-validity guard still fires on non-finite even when skipped.
    with pytest.raises(DataError, match="non-finite"):
        _assert_price_range(_close([5.0, np.nan]), "USDJPY", "4h", _DUMMY)


# --- Integration against the real and corrupted on-disk parquets ------------

_REAL_DIR = Path("data/processed")
_SYNTH_DIR = Path("data/processed_synthetic_phase0")
_JPY = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY"]


@pytest.mark.parametrize("pair", _JPY)
def test_real_processed_jpy_passes_range_check(pair):
    fp = _REAL_DIR / f"{pair}_daily.parquet"
    if not fp.exists():
        pytest.skip(f"{fp} not present")
    _assert_price_range(pd.read_parquet(fp), pair, "daily", fp)  # must not raise


@pytest.mark.parametrize("pair", ["USDJPY", "GBPJPY", "CADJPY"])
def test_corrupted_synthetic_jpy_is_rejected(pair):
    fp = _SYNTH_DIR / f"{pair}_daily.parquet"
    if not fp.exists():
        pytest.skip(f"{fp} not present")
    with pytest.raises(DataError):
        _assert_price_range(pd.read_parquet(fp), pair, "daily", fp)
