"""Tests for performance metrics."""

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.metrics import calculate_metrics
from forex_system.core.types import Direction, Trade


def test_linear_growth():
    """Known linear equity curve: 10% return over 252 days."""
    dates = pd.bdate_range("2020-01-01", periods=252, freq="B")
    equity = pd.Series(np.linspace(100_000, 110_000, 252), index=dates)
    trades = [
        Trade("EURUSD", Direction.LONG, dates[0], dates[-1], 1.10, 1.11,
              10000, 100, 10000, 2.0, 0.2, "test")
    ]
    metrics = calculate_metrics(equity, trades)
    assert metrics.total_return == pytest.approx(0.10, rel=0.01)
    assert metrics.num_trades == 1
    assert metrics.win_rate == 1.0


def test_known_drawdown():
    """Equity goes up then down — max drawdown should match."""
    dates = pd.bdate_range("2020-01-01", periods=100, freq="B")
    equity_values = np.concatenate([
        np.linspace(100_000, 120_000, 50),  # Up 20%
        np.linspace(120_000, 102_000, 50),  # Down to 102k (15% from peak)
    ])
    equity = pd.Series(equity_values, index=dates)
    metrics = calculate_metrics(equity, [])
    assert metrics.max_drawdown == pytest.approx(0.15, rel=0.01)


def test_no_trades():
    dates = pd.bdate_range("2020-01-01", periods=10, freq="B")
    equity = pd.Series(100_000.0, index=dates)
    metrics = calculate_metrics(equity, [])
    assert metrics.num_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.profit_factor == 0.0


def test_win_rate():
    dates = pd.bdate_range("2020-01-01", periods=10, freq="B")
    trades = [
        Trade("EURUSD", Direction.LONG, dates[0], dates[1], 1.10, 1.11,
              10000, 50, 5.0, 2.0, 0.2, "test"),  # Win
        Trade("EURUSD", Direction.SHORT, dates[2], dates[3], 1.11, 1.12,
              10000, -50, -5.0, 2.0, 0.2, "test"),  # Loss
        Trade("EURUSD", Direction.LONG, dates[4], dates[5], 1.10, 1.12,
              10000, 100, 10.0, 2.0, 0.2, "test"),  # Win
    ]
    equity = pd.Series(np.linspace(100_000, 110_000, 10), index=dates)
    metrics = calculate_metrics(equity, trades)
    assert metrics.win_rate == pytest.approx(2 / 3)
