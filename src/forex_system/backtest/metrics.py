"""Performance metrics — pure functions from equity curve and trade log.

All metrics are calculated from realized data, no lookahead.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from forex_system.core.constants import TRADING_DAYS_PER_YEAR
from forex_system.core.types import Trade


@dataclass
class PerformanceMetrics:
    """Complete performance summary."""

    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_trade_pnl_pips: float
    avg_trade_duration_days: float
    exposure_pct: float


def calculate_metrics(
    equity_curve: pd.Series,
    trade_log: list[Trade],
    risk_free_rate: float = 0.0,
) -> PerformanceMetrics:
    """Calculate all performance metrics from backtest results."""
    if len(equity_curve.dropna()) < 2:
        return _empty_metrics()

    ec = equity_curve.dropna()

    # Returns
    total_return = (ec.iloc[-1] / ec.iloc[0]) - 1.0
    n_days = (ec.index[-1] - ec.index[0]).days
    n_years = max(n_days / 365.25, 1e-6)
    # Guard against total_loss case: if equity wiped out (total_return <= -1),
    # position was liquidated. Annualized return = -1.0 (total loss).
    if total_return <= -1.0:
        annualized_return = -1.0
    else:
        annualized_return = (1 + total_return) ** (1.0 / n_years) - 1.0

    # Daily returns
    daily_returns = ec.pct_change().dropna()

    # Sharpe ratio (annualized)
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        excess = daily_returns.mean() - risk_free_rate / TRADING_DAYS_PER_YEAR
        sharpe_ratio = excess / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation only)
    downside = daily_returns[daily_returns < 0]
    if len(downside) > 1 and downside.std() > 0:
        excess = daily_returns.mean() - risk_free_rate / TRADING_DAYS_PER_YEAR
        sortino_ratio = excess / downside.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        sortino_ratio = sharpe_ratio  # No downside = use Sharpe

    # Max drawdown
    # Clamp to [0, 1]: unrealized mark-to-market equity can go below zero when a
    # highly-leveraged position's paper loss exceeds initial capital (no margin-call
    # simulation in the engine). The ratio (ec - cummax) / cummax would then exceed
    # -1.0 in magnitude, producing an economically nonsensical result > 100%.
    cummax = ec.cummax()
    drawdown = (ec - cummax) / cummax
    max_drawdown = min(1.0, abs(drawdown.min())) if len(drawdown) > 0 else 0.0

    # Max drawdown duration
    max_dd_duration = _max_drawdown_duration(ec)

    # Trade-level metrics
    num_trades = len(trade_log)
    if num_trades > 0:
        wins = [t for t in trade_log if t.pnl_pips > 0]
        losses = [t for t in trade_log if t.pnl_pips <= 0]
        win_rate = len(wins) / num_trades

        gross_profit = sum(t.pnl_pips for t in wins)
        gross_loss = abs(sum(t.pnl_pips for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.9

        avg_trade_pnl_pips = sum(t.pnl_pips for t in trade_log) / num_trades

        durations = [(t.exit_time - t.entry_time).days for t in trade_log]
        avg_trade_duration = sum(durations) / len(durations)
    else:
        win_rate = 0.0
        profit_factor = 0.0
        avg_trade_pnl_pips = 0.0
        avg_trade_duration = 0.0

    # Exposure percentage (fraction of time in a position)
    if len(trade_log) > 0 and n_days > 0:
        total_days_in_market = sum((t.exit_time - t.entry_time).days for t in trade_log)
        exposure_pct = min(total_days_in_market / n_days, 1.0)
    else:
        exposure_pct = 0.0

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_duration_days=max_dd_duration,
        win_rate=win_rate,
        profit_factor=profit_factor,
        num_trades=num_trades,
        avg_trade_pnl_pips=avg_trade_pnl_pips,
        avg_trade_duration_days=avg_trade_duration,
        exposure_pct=exposure_pct,
    )


def _max_drawdown_duration(equity_curve: pd.Series) -> int:
    """Calculate max drawdown duration in calendar days."""
    cummax = equity_curve.cummax()
    in_drawdown = equity_curve < cummax

    if not in_drawdown.any():
        return 0

    max_duration = 0
    current_start = None

    for ts, is_dd in in_drawdown.items():
        if is_dd and current_start is None:
            current_start = ts
        elif not is_dd and current_start is not None:
            duration = (ts - current_start).days
            max_duration = max(max_duration, duration)
            current_start = None

    # Handle case where drawdown extends to the end
    if current_start is not None:
        duration = (equity_curve.index[-1] - current_start).days
        max_duration = max(max_duration, duration)

    return max_duration


def _empty_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return=0.0,
        annualized_return=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        max_drawdown=0.0,
        max_drawdown_duration_days=0,
        win_rate=0.0,
        profit_factor=0.0,
        num_trades=0,
        avg_trade_pnl_pips=0.0,
        avg_trade_duration_days=0.0,
        exposure_pct=0.0,
    )
