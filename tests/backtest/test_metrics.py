"""Tests for performance metrics."""

import warnings

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


def test_max_drawdown_standard_case():
    """$100K → $80K → $120K → $90K: drawdown is $120K → $90K = 25%."""
    dates = pd.bdate_range("2020-01-01", periods=4, freq="B")
    equity = pd.Series([100_000, 80_000, 120_000, 90_000], index=dates, dtype=float)
    metrics = calculate_metrics(equity, [])
    # Peak at 120K, trough at 90K: (90K - 120K) / 120K = -0.25
    assert metrics.max_drawdown == pytest.approx(0.25, rel=0.01)
    assert 0.0 <= metrics.max_drawdown <= 1.0


def test_max_drawdown_leveraged_long_only_clamped():
    """Leveraged position can push mark-to-market equity below zero.

    Mimics trial 43c9b481: equity grew from $1M to $116M (1 trade, long USDJPY,
    VolTargetSizer fixed size at entry). The underlying issue is that the position
    size (2x leverage on $1M = $2M nominal) was held fixed for 16 years, so
    unrealized P&L relative to a previous peak can mathematically exceed 100%
    when the mark-to-market equity series dips below zero (no margin-call guard
    in the engine).

    The formula (ec - cummax) / cummax gives a ratio < -1 when ec < 0, which
    is structurally impossible as a drawdown. max_drawdown must be clamped to [0, 1].
    """
    # Simulate: equity grows to $116M then has one bar where mark-to-market goes
    # deeply negative (e.g., $-5M) due to a leveraged paper loss, then recovers.
    dates = pd.bdate_range("2008-01-01", periods=5, freq="B")
    equity_values = [1_000_000, 50_000_000, 116_000_000, -5_000_000, 90_000_000]
    equity = pd.Series(equity_values, index=dates, dtype=float)
    metrics = calculate_metrics(equity, [])
    # Without clamping: (ec=-5M, cummax=116M) → (-5M - 116M) / 116M = -1.043 → abs = 1.043
    # With clamping: must be ≤ 1.0
    assert metrics.max_drawdown <= 1.0
    assert metrics.max_drawdown >= 0.0


def test_max_drawdown_monotonic_growth_with_small_dip():
    """Equity grows from $1M to $116M with one ~10% intra-period dip.

    max_dd should be ~0.10, not anywhere near 3.0.
    """
    n = 4233  # Matches trial 43c9b481 observation count (n_obs=4231 returns → 4232 equity points)
    dates = pd.bdate_range("2008-01-01", periods=n, freq="B")
    # Monotonic growth from 1M → 116M with one 10% drawdown in the middle
    equity_values = np.linspace(1_000_000, 116_000_000, n)
    # Inject a ~10% drawdown around bar 2000
    peak_before_dip = equity_values[2000]
    equity_values[2001:2051] = peak_before_dip * np.linspace(1.0, 0.90, 50)
    equity_values[2051:2100] = peak_before_dip * np.linspace(0.90, 1.0, 49)
    equity = pd.Series(equity_values, index=dates, dtype=float)
    metrics = calculate_metrics(equity, [])
    assert metrics.max_drawdown == pytest.approx(0.10, abs=0.02)
    assert 0.0 <= metrics.max_drawdown <= 1.0


def test_annualized_return_total_loss():
    """Equity wiped out (goes to zero or below) over 10 years.

    Should return annualized_return = -1.0 (total loss) with no RuntimeWarning.
    """
    dates = pd.bdate_range("2015-01-01", periods=2521, freq="B")  # ~10 years
    # Start at $1M, steadily decline to $0
    equity_values = np.linspace(1_000_000, 0, len(dates))
    equity = pd.Series(equity_values, index=dates, dtype=float)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        metrics = calculate_metrics(equity, [])
        # Check no RuntimeWarning was raised
        runtime_warns = [warn for warn in w
                         if issubclass(warn.category, RuntimeWarning)]
        assert len(runtime_warns) == 0, f"Got RuntimeWarning: {runtime_warns}"

    assert metrics.annualized_return == -1.0
    assert metrics.total_return == -1.0
