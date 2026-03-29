"""Vectorized backtest engine — the heart of Phase 0.

Takes OHLCV data + signals + cost model -> equity curve + trade log.
Strictly avoids lookahead: signals at bar N execute at bar N+1 open.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_system.core.types import BacktestResult, Direction, Trade
from forex_system.costs.model import RealisticCostModel


def run_backtest(
    data: pd.DataFrame,
    signals: pd.Series,
    pair: str,
    strategy_name: str,
    cost_model: RealisticCostModel,
    initial_capital: float = 100_000.0,
    risk_per_trade: float = 0.02,
    stop_loss_atr_multiple: float = 2.0,
    entry_delay_bars: int = 1,
) -> BacktestResult:
    """Run a vectorized backtest.

    Args:
        data: OHLCV DataFrame with indicators (must include atr_14)
        signals: Series of floats in [-1, +1], same index as data
        pair: Currency pair symbol
        strategy_name: Name for logging
        cost_model: Transaction cost model
        initial_capital: Starting equity in USD
        risk_per_trade: Fraction of equity to risk per trade
        stop_loss_atr_multiple: ATR multiplier for position sizing
        entry_delay_bars: Bars to delay signal execution (1 = next bar)
    """
    if data.empty:
        return _empty_result(pair, strategy_name, signals)

    # Shift signals forward to avoid lookahead
    delayed_signals = signals.shift(entry_delay_bars).fillna(0.0)

    # Discretize to positions: +1, -1, 0
    positions = np.sign(delayed_signals).astype(float)

    # Detect position changes — first bar change is 0 (no prior position)
    position_changes = positions.diff().fillna(0.0)

    atr_series = _get_atr(data)
    pip_value = _get_pip_value(pair)

    # Simulate bar by bar
    equity = initial_capital
    equity_curve = pd.Series(np.nan, index=data.index)
    trade_log: list[Trade] = []

    current_position = 0.0
    current_size = 0.0
    entry_price = 0.0
    entry_time: pd.Timestamp | None = None

    for i, (ts, row) in enumerate(data.iterrows()):
        price = row["close"]
        if pd.isna(price):
            equity_curve.iloc[i] = equity
            continue

        pos = positions.iloc[i]
        change = position_changes.iloc[i]

        # Close existing position if direction changed
        if change != 0 and current_position != 0:
            trade = _close_position(
                pair, strategy_name, cost_model, pip_value,
                current_position, current_size, entry_price, entry_time, ts, price,
            )
            trade_log.append(trade)
            equity += trade.pnl_dollars
            current_position = 0.0
            current_size = 0.0
            entry_time = None

        # Open new position if signal is non-zero
        if change != 0 and pos != 0:
            current_atr = atr_series.iloc[i]
            current_size = _calculate_size(
                equity, risk_per_trade, current_atr, stop_loss_atr_multiple, price,
            )

            entry_cost_pips = cost_model.entry_cost(pair, current_size)
            equity -= entry_cost_pips * pip_value * current_size

            current_position = pos
            entry_price = price
            entry_time = ts

        # Mark-to-market (unrealized P&L)
        if current_position != 0:
            unrealized_pips = (price - entry_price) / pip_value * current_position
            equity_curve.iloc[i] = equity + unrealized_pips * pip_value * current_size
        else:
            equity_curve.iloc[i] = equity

    # Close any remaining position at the last bar
    if current_position != 0:
        last_ts = data.index[-1]
        last_price = data["close"].iloc[-1]
        trade = _close_position(
            pair, strategy_name, cost_model, pip_value,
            current_position, current_size, entry_price, entry_time, last_ts, last_price,
        )
        trade_log.append(trade)
        equity += trade.pnl_dollars
        equity_curve.iloc[-1] = equity

    return BacktestResult(
        equity_curve=equity_curve,
        trade_log=trade_log,
        signals=signals,
        parameters={},
        pair=pair,
        strategy_name=strategy_name,
        start_date=data.index[0],
        end_date=data.index[-1],
    )


def _close_position(
    pair: str,
    strategy_name: str,
    cost_model: RealisticCostModel,
    pip_value: float,
    position: float,
    size: float,
    entry_price: float,
    entry_time: pd.Timestamp | None,
    exit_time: pd.Timestamp,
    exit_price: float,
) -> Trade:
    """Close a position and return the completed Trade."""
    direction = Direction.LONG if position > 0 else Direction.SHORT
    hold_days = (exit_time - entry_time).days if entry_time is not None else 0

    exit_cost_pips = cost_model.exit_cost(pair, size)
    swap_cost_pips = cost_model.holding_cost(pair, direction, hold_days)
    total_cost_pips = exit_cost_pips + swap_cost_pips

    price_diff_pips = (exit_price - entry_price) / pip_value * position
    net_pnl_pips = price_diff_pips - total_cost_pips

    pnl_dollars = net_pnl_pips * pip_value * size
    cost_dollars = total_cost_pips * pip_value * size

    return Trade(
        pair=pair,
        direction=direction,
        entry_time=entry_time or exit_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        pnl_pips=net_pnl_pips,
        pnl_dollars=pnl_dollars,
        cost_pips=total_cost_pips,
        cost_dollars=cost_dollars,
        strategy=strategy_name,
    )


def _calculate_size(
    equity: float,
    risk_per_trade: float,
    atr: float,
    atr_multiple: float,
    price: float,
) -> float:
    """Calculate position size based on ATR-based stop distance."""
    if not pd.isna(atr) and atr > 0:
        stop_distance = atr * atr_multiple
        return equity * risk_per_trade / stop_distance
    # Fallback: size based on 2% price move
    return equity * risk_per_trade / (price * 0.02) if price > 0 else 0.0


def _get_atr(data: pd.DataFrame) -> pd.Series:
    """Get ATR series from data, computing if absent."""
    if "atr_14" in data.columns:
        return data["atr_14"]
    tr = pd.concat([
        data["high"] - data["low"],
        (data["high"] - data["close"].shift(1)).abs(),
        (data["low"] - data["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(14).mean()


def _get_pip_value(pair: str) -> float:
    """Get pip value for a pair (0.0001 for most, 0.01 for JPY)."""
    if "JPY" in pair.upper():
        return 0.01
    return 0.0001


def _empty_result(
    pair: str, strategy_name: str, signals: pd.Series
) -> BacktestResult:
    return BacktestResult(
        equity_curve=pd.Series(dtype=float),
        trade_log=[],
        signals=signals,
        parameters={},
        pair=pair,
        strategy_name=strategy_name,
        start_date=pd.Timestamp.now(),
        end_date=pd.Timestamp.now(),
    )
