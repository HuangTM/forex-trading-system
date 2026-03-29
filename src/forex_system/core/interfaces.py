"""Abstract base classes defining contracts between modules.

Every module depends on these interfaces, never on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from forex_system.core.types import Direction


class DataSource(ABC):
    """Contract for all data providers."""

    @abstractmethod
    def fetch(
        self, pair: str, start: str, end: str, timeframe: str = "daily"
    ) -> pd.DataFrame:
        """Fetch OHLCV data.

        Returns DataFrame with columns: open, high, low, close, volume
        Index: DatetimeIndex (UTC)
        """
        ...


class Strategy(ABC):
    """Contract for all trading strategies."""

    def __init__(self, params: dict[str, Any]):
        self.params = params

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals from enriched OHLCV data.

        Input:  DataFrame with OHLCV + any required indicators
        Output: Series of floats in [-1.0, +1.0]
                +1.0 = max long, -1.0 = max short, 0.0 = flat

        Must NOT use future data (no lookahead).
        Must be indexed identically to input data.
        """
        ...

    @abstractmethod
    def required_indicators(self) -> list[str]:
        """Indicator names this strategy needs pre-computed.

        Example: ["sma_50", "sma_200"]
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""
        ...


class CostModel(ABC):
    """Contract for transaction cost estimation."""

    @abstractmethod
    def entry_cost(self, pair: str, size: float) -> float:
        """Cost in pips to enter a position."""
        ...

    @abstractmethod
    def exit_cost(self, pair: str, size: float) -> float:
        """Cost in pips to exit a position."""
        ...

    @abstractmethod
    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        """Swap/financing cost in pips for holding a position."""
        ...


class PositionSizer(ABC):
    """Contract for position sizing logic."""

    @abstractmethod
    def calculate_size(
        self,
        signal_strength: float,
        account_equity: float,
        current_price: float,
        atr: float,
        pair: str,
    ) -> float:
        """Calculate position size in units.

        signal_strength: [-1.0, 1.0] from strategy
        atr: for stop-loss distance calculation
        """
        ...


@dataclass
class ValidationReport:
    """Result of data quality validation."""

    passed: bool
    pair: str
    issues: list[str]
    row_count: int
    date_range: tuple[str, str] | None = None
