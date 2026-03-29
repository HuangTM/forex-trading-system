"""Shared test fixtures — synthetic data for deterministic testing."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv():
    """100 bars of synthetic OHLCV data with a known trend."""
    rng = np.random.default_rng(42)
    n = 100
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B", tz="UTC")

    # Create an uptrend for first 50 bars, downtrend for last 50
    trend = np.concatenate([
        np.linspace(1.1000, 1.1500, 50),
        np.linspace(1.1500, 1.1000, 50),
    ])
    noise = rng.normal(0, 0.001, n)
    close = trend + noise

    daily_range = np.abs(rng.normal(0, 0.002, n))
    high = close + daily_range * 0.6
    low = close - daily_range * 0.4
    open_prices = np.roll(close, 1) + rng.normal(0, 0.0005, n)
    open_prices[0] = 1.1000

    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))

    return pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": close, "volume": 100000.0},
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


@pytest.fixture
def long_ohlcv():
    """500 bars for walk-forward testing."""
    rng = np.random.default_rng(123)
    n = 500
    dates = pd.bdate_range("2018-01-01", periods=n, freq="B", tz="UTC")

    returns = rng.normal(0.0001, 0.005, n)
    prices = 1.1000 * np.exp(np.cumsum(returns))

    daily_range = np.abs(rng.normal(0, 0.002, n)) * prices
    high = prices + daily_range * 0.6
    low = prices - daily_range * 0.4
    open_prices = np.roll(prices, 1) * (1 + rng.normal(0, 0.001, n))
    open_prices[0] = 1.1000

    high = np.maximum(high, np.maximum(open_prices, prices))
    low = np.minimum(low, np.minimum(open_prices, prices))

    return pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": prices, "volume": 100000.0},
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


@pytest.fixture
def sample_config_path(tmp_path):
    """Write a minimal config file and return its path."""
    config_content = """
system:
  log_level: "DEBUG"

data:
  base_dir: "data"

pairs:
  - symbol: "EURUSD"
    pip_value: 0.0001
    spread_pips: 0.5
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_day: -1.2
    swap_short_pips_per_day: 0.3

strategies:
  active:
    - "ma_crossover"
  ma_crossover:
    fast_period: 10
    slow_period: 30

backtest:
  initial_capital: 100000.0
  position_sizing:
    risk_per_trade: 0.02
    stop_loss_atr_multiple: 2.0
  execution:
    entry_delay_bars: 1
  walkforward:
    train_window_days: 100
    test_window_days: 50
    step_days: 25
"""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content)
    return config_path
