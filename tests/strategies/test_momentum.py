"""Tests for Momentum strategy."""

import numpy as np
import pandas as pd

from forex_system.features.registry import compute_indicators
from forex_system.strategies.momentum import MomentumStrategy


def test_positive_momentum_long():
    strategy = MomentumStrategy({"lookback_period": 5, "threshold": 0.0})
    n = 30
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(1.0, 1.5, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    # Uptrend: should be long after warmup
    assert signals.iloc[-1] == 1.0


def test_negative_momentum_short():
    strategy = MomentumStrategy({"lookback_period": 5, "threshold": 0.0})
    n = 30
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(np.linspace(1.5, 1.0, n), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.01, "low": close - 0.01,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    assert signals.iloc[-1] == -1.0
