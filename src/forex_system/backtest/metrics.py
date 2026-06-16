"""Performance metrics — pure functions from equity curve and trade log.

All metrics are calculated from realized data, no lookahead.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from forex_system.core.constants import TRADING_DAYS_PER_YEAR, TRADING_HOURS_PER_YEAR
from forex_system.core.types import Trade

logger = logging.getLogger(__name__)


def infer_periods_per_year(index: pd.DatetimeIndex) -> float:
    """Infer the annualisation factor from an equity-curve index's bar spacing.

    Uses the MEDIAN spacing (robust to weekend/holiday gaps) and snaps to a
    canonical timeframe factor. Falls back to daily (252) on an unrecognised or
    empty spacing, logging a structured warning so the fallback is visible.
    """
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return float(TRADING_DAYS_PER_YEAR)
    median = index.to_series().diff().dropna().median()
    if median is pd.NaT or pd.isna(median) or median <= pd.Timedelta(0):
        return float(TRADING_DAYS_PER_YEAR)
    if median <= pd.Timedelta(hours=1, minutes=30):
        return float(TRADING_HOURS_PER_YEAR)  # 1h
    if median <= pd.Timedelta(hours=6):
        return TRADING_HOURS_PER_YEAR / 4.0  # 4h
    if median <= pd.Timedelta(days=2):
        return float(TRADING_DAYS_PER_YEAR)  # daily
    logger.warning(
        '{"event":"metrics.periods_per_year.unrecognised_spacing",'
        '"median_spacing":"%s","action":"fallback_daily_252"}',
        median,
    )
    return float(TRADING_DAYS_PER_YEAR)


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
    periods_per_year: float | None = None,
) -> PerformanceMetrics:
    """Calculate all performance metrics from backtest results.

    Args:
        periods_per_year: annualisation factor for the Sharpe/Sortino sqrt(P)
            term, matched to the equity curve's bar frequency. Default ``None``
            INFERS the factor from the equity curve's index spacing (snapping to
            daily 252 / 4h 1560 / 1h 6240; non-datetime or unrecognised index
            falls back to 252). Daily curves infer 252 exactly, so existing
            daily callers are unchanged; an hourly Sharpe annualised with 252
            would be understated ~5x, which the inference prevents.
    """
    if len(equity_curve.dropna()) < 2:
        return _empty_metrics()

    ec = equity_curve.dropna()
    ppy = float(periods_per_year) if periods_per_year is not None else infer_periods_per_year(ec.index)

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

    # Per-bar returns (frequency = equity curve's bar frequency; annualised via ppy)
    period_returns = ec.pct_change().dropna()

    # Sharpe ratio (annualized)
    if len(period_returns) > 1 and period_returns.std() > 0:
        excess = period_returns.mean() - risk_free_rate / ppy
        sharpe_ratio = excess / period_returns.std() * np.sqrt(ppy)
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation only)
    downside = period_returns[period_returns < 0]
    if len(downside) > 1 and downside.std() > 0:
        excess = period_returns.mean() - risk_free_rate / ppy
        sortino_ratio = excess / downside.std() * np.sqrt(ppy)
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
