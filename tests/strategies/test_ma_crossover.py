"""Tests for MA Crossover strategy."""

import numpy as np
import pandas as pd

from forex_system.features.registry import compute_indicators
from forex_system.strategies.ma_crossover import MACrossoverStrategy


def test_signal_values():
    """Signals must be exactly +1, -1, or 0."""
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 10})
    n = 50
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")

    # Uptrend data — fast SMA should be above slow SMA
    close = pd.Series(np.linspace(1.0, 2.0, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    unique_vals = set(signals.dropna().unique())
    assert unique_vals.issubset({-1.0, 0.0, 1.0})


def test_uptrend_gives_long():
    """In a clear uptrend, strategy should be long."""
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 10})
    n = 50
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(1.0, 2.0, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    # After warmup, should be long
    assert signals.iloc[-1] == 1.0


def test_downtrend_gives_short():
    """In a clear downtrend, strategy should be short."""
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 10})
    n = 50
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(2.0, 1.0, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    assert signals.iloc[-1] == -1.0


def test_no_lookahead():
    """Signal at bar N must only use data from bars 0..N."""
    strategy = MACrossoverStrategy({"fast_period": 5, "slow_period": 10})
    n = 50
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(1.0, 2.0, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())

    # Full signals
    full_signals = strategy.generate_signals(enriched)

    # Signals computed on partial data (first 30 bars only)
    partial = enriched.iloc[:30]
    partial_signals = strategy.generate_signals(partial)

    # Signals on overlapping bars must match
    pd.testing.assert_series_equal(
        full_signals.iloc[:30],
        partial_signals,
        check_names=False,
    )
