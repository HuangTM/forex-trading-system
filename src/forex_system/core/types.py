"""Domain types for the forex trading system.

Immutable data containers — no logic, only shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd


class Direction(Enum):
    LONG = 1
    SHORT = -1
    FLAT = 0


@dataclass(frozen=True)
class PairInfo:
    """Static metadata for a currency pair."""

    symbol: str
    pip_value: float  # 0.0001 for most, 0.01 for JPY pairs
    spread_pips: float
    slippage_pips: float
    commission_pips: float
    swap_long_pips_per_day: float
    swap_short_pips_per_day: float


@dataclass(frozen=True)
class Trade:
    """A completed trade with full P&L accounting."""

    pair: str
    direction: Direction
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    size: float  # Position size in units
    pnl_pips: float
    pnl_dollars: float
    cost_pips: float
    cost_dollars: float
    strategy: str


@dataclass(frozen=True)
class BacktestResult:
    """Complete output of a single backtest run."""

    equity_curve: pd.Series  # Indexed by timestamp
    trade_log: list[Trade]
    signals: pd.Series  # Raw signals produced
    parameters: dict[str, Any]  # Strategy params used
    pair: str
    strategy_name: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp


# Standard OHLCV column names used throughout the system
OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]
