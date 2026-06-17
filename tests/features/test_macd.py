"""Tests for the MACD indicator and its registry integration."""

import numpy as np
import pandas as pd
import pytest

from forex_system.features.indicators import macd
from forex_system.features.registry import compute_indicators


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_series(n: int = 100, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    prices = 1.1000 + np.cumsum(rng.normal(0, 0.001, n))
    return pd.Series(prices, dtype=float)


# ---------------------------------------------------------------------------
# Correctness: match pandas.ewm reference implementation
# ---------------------------------------------------------------------------


def test_macd_line_matches_reference():
    """MACD line = EMA(12) − EMA(26), verified against pandas.ewm directly."""
    s = _make_series(100)
    macd_line, signal_line, histogram = macd(s, fast=12, slow=26, signal=9)

    ref_fast = s.ewm(span=12, adjust=False, min_periods=12).mean()
    ref_slow = s.ewm(span=26, adjust=False, min_periods=26).mean()
    ref_macd = ref_fast - ref_slow

    pd.testing.assert_series_equal(macd_line, ref_macd, check_names=False)


def test_signal_line_is_ema_of_macd():
    """Signal line = EMA(9) of the MACD line, NOT of price."""
    s = _make_series(100)
    macd_line, signal_line, histogram = macd(s, fast=12, slow=26, signal=9)

    # Compute expected: EMA(9) applied to the macd_line series
    ref_signal = macd_line.ewm(span=9, adjust=False, min_periods=9).mean()

    pd.testing.assert_series_equal(signal_line, ref_signal, check_names=False)


def test_histogram_equals_macd_minus_signal():
    """Histogram = MACD line − signal line at every bar."""
    s = _make_series(100)
    macd_line, signal_line, histogram = macd(s, fast=12, slow=26, signal=9)

    expected_hist = macd_line - signal_line
    pd.testing.assert_series_equal(histogram, expected_hist, check_names=False)


def test_macd_returns_three_series():
    """Function must return exactly three pd.Series."""
    s = _make_series(50)
    result = macd(s)
    assert len(result) == 3
    for item in result:
        assert isinstance(item, pd.Series)


def test_macd_warmup_nans():
    """Bars before slow EMA warmup must be NaN for MACD line."""
    s = _make_series(100)
    macd_line, signal_line, _ = macd(s, fast=12, slow=26, signal=9)

    # First (slow-1) bars of MACD line must be NaN (min_periods=slow)
    assert macd_line.iloc[:25].isna().all(), "Expected NaN during slow-EMA warmup"
    # Signal line needs additional warmup (signal-1 more bars after macd starts)
    assert signal_line.iloc[:33].isna().all(), "Expected NaN during signal-line warmup"


# ---------------------------------------------------------------------------
# No-lookahead: truncation invariance
# ---------------------------------------------------------------------------


def test_macd_no_lookahead():
    """Value at index t must be unchanged when future bars are appended.

    This is the indicator-level no-lookahead invariant: EMA is causal
    (each value depends only on present and past), so truncating at t
    must not change the value at t.
    """
    s = _make_series(200)
    # Pick a midpoint well past warmup (slow=26 + signal=9 + buffer)
    t = 80

    # Compute on the full series
    macd_full, sig_full, hist_full = macd(s, fast=12, slow=26, signal=9)

    # Compute on truncated series (only bars 0..t inclusive)
    s_truncated = s.iloc[: t + 1]
    macd_trunc, sig_trunc, hist_trunc = macd(s_truncated, fast=12, slow=26, signal=9)

    assert macd_full.iloc[t] == pytest.approx(macd_trunc.iloc[t], rel=1e-10), (
        "MACD line at t changes when future bars appended — LOOKAHEAD DETECTED"
    )
    assert sig_full.iloc[t] == pytest.approx(sig_trunc.iloc[t], rel=1e-10), (
        "Signal line at t changes when future bars appended — LOOKAHEAD DETECTED"
    )
    assert hist_full.iloc[t] == pytest.approx(hist_trunc.iloc[t], rel=1e-10), (
        "Histogram at t changes when future bars appended — LOOKAHEAD DETECTED"
    )


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


def test_registry_parses_macd_12_26_9(sample_ohlcv):
    """Registry must parse 'macd_12_26_9' and produce three output columns."""
    result = compute_indicators(sample_ohlcv, ["macd_12_26_9"])

    assert "macd_line_12_26_9" in result.columns
    assert "macd_signal_12_26_9" in result.columns
    assert "macd_hist_12_26_9" in result.columns


def test_registry_macd_values_match_direct(sample_ohlcv):
    """Registry-computed MACD must match direct indicator call."""
    result = compute_indicators(sample_ohlcv, ["macd_12_26_9"])
    macd_line, signal_line, histogram = macd(sample_ohlcv["close"], 12, 26, 9)

    pd.testing.assert_series_equal(
        result["macd_line_12_26_9"].rename(None),
        macd_line.rename(None),
        check_names=False,
    )
    pd.testing.assert_series_equal(
        result["macd_signal_12_26_9"].rename(None),
        signal_line.rename(None),
        check_names=False,
    )


def test_registry_macd_idempotent(sample_ohlcv):
    """Calling compute_indicators twice with the same name must not duplicate work."""
    r1 = compute_indicators(sample_ohlcv, ["macd_12_26_9"])
    r2 = compute_indicators(r1, ["macd_12_26_9"])
    # Columns should exist exactly once
    assert list(r2.columns).count("macd_line_12_26_9") == 1


def test_registry_unknown_indicator_raises(sample_ohlcv):
    """Unknown indicator names must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown indicator"):
        compute_indicators(sample_ohlcv, ["unknown_99"])
