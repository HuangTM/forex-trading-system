"""Tests for Bollinger Bands + RSI strategy."""

import numpy as np
import pandas as pd

from forex_system.features.registry import compute_indicators
from forex_system.strategies.bollinger_rsi import BollingerRSIStrategy


def test_signal_values():
    strategy = BollingerRSIStrategy({
        "bb_period": 10, "bb_std": 2.0, "rsi_period": 7,
        "rsi_oversold": 30, "rsi_overbought": 70,
    })
    n = 100
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    close = pd.Series(1.0 + rng.normal(0, 0.01, n).cumsum(), index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.005, "low": close - 0.005,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    unique = set(signals.dropna().unique())
    assert unique.issubset({-1.0, 0.0, 1.0})


def test_oversold_gives_buy():
    """Sharply dropping prices should trigger buy (mean reversion)."""
    strategy = BollingerRSIStrategy({
        "bb_period": 10, "bb_std": 2.0, "rsi_period": 7,
        "rsi_oversold": 30, "rsi_overbought": 70,
    })
    n = 100
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")

    # Flat period then sharp drop
    flat = [1.1000] * 80
    drop = [1.1000 - 0.005 * i for i in range(20)]
    close = pd.Series(flat + drop, index=dates)
    df = pd.DataFrame({"open": close, "high": close + 0.001, "low": close - 0.001,
                        "close": close, "volume": 100000}, index=dates)
    enriched = compute_indicators(df, strategy.required_indicators())
    signals = strategy.generate_signals(enriched)

    # Expect at least one buy signal in the drop region
    drop_signals = signals.iloc[80:]
    assert (drop_signals == 1.0).any()
