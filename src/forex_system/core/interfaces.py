"""Abstract base classes defining contracts between modules.

Every module depends on these interfaces, never on concrete implementations.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from forex_system.core.types import Direction

logger = logging.getLogger(__name__)


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
    """Contract for all trading strategies.

    ABC contract (REM-1 / D-1.1): __init__ accepts params plus an optional
    keyword-only argument rate_data. The keyword-only sentinel (*) ensures
    no positional caller accidentally passes rate_data where only params is
    expected.  This is backward-compatible: all existing cls(params) callers
    continue to work unchanged.

    rate_data is TRULY optional — any concrete subclass that requires
    rate_data must raise at signal-generation time (generate_signals) if it
    is missing, NOT at __init__ time.  A subclass that raises TypeError when
    rate_data=None is passed has re-introduced the Liskov violation in
    disguise.  The test REM-1-T1 enforces this invariant.
    """

    def __init__(self, params: dict[str, Any], *, rate_data: Optional[pd.DataFrame] = None):
        self.params = params
        self.rate_data = rate_data
        # REM-1 observability boundary: log construction path at INFO level so
        # post-hoc reconstruction can confirm which path fired for each strategy.
        logger.info(
            "strategy_constructed strategy_name=%s construction_path=%s",
            type(self).__name__,
            "params_and_rate_data" if rate_data is not None else "params_only",
        )

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
    def entry_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to enter a position.

        timestamp: the bar's timestamp, for time-varying cost models (e.g. an
        hour-of-day spread curve). Implementations that use a fixed spread
        ignore it; the engine passes the current bar's timestamp.
        """
        ...

    @abstractmethod
    def exit_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to exit a position. See ``entry_cost`` re: timestamp."""
        ...

    @abstractmethod
    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        """Swap/financing cost in pips for holding a position."""
        ...


class PositionSizer(ABC):
    """Contract for position sizing logic.

    Signal strength maps to position size. The confidence and ratchet_level
    parameters are optional extensions for continuous sizing and capital
    ratcheting — existing implementations can ignore them via defaults.
    """

    @abstractmethod
    def calculate_size(
        self,
        signal_strength: float,
        account_equity: float,
        current_price: float,
        atr: float,
        pair: str,
        confidence: float = 1.0,
        ratchet_level: float = 1.0,
    ) -> float:
        """Calculate position size in units.

        signal_strength: [-1.0, 1.0] from strategy
        atr: for stop-loss distance calculation
        confidence: [0.0, 1.0] signal confidence (1.0 = full confidence)
        ratchet_level: [0.0, 1.0] capital ratchet multiplier (1.0 = full size)
        """
        ...


class RoutingDisabledError(Exception):
    """Raised when order routing is attempted while routing_disabled=True.

    This is an architectural hard-block (Change 2, CRO requirement 2026-06-01):
    observe-only / canary runners set routing_disabled=True so that any attempt to
    route an order fails loudly rather than silently no-oping.  A misconfigured
    caller that reaches execute_signal in routing-disabled mode indicates a wiring
    error; raising here makes it visible immediately rather than producing a silent
    no-op that leaves the system in an inconsistent state.
    """


class ExecutionBackend(ABC):
    """Contract for execution — backtest, paper, or live."""

    @property
    def is_mock(self) -> bool:
        """Return True if this backend is a test/mock backend (not a real broker connection).

        MC-6: Backend-identity mock detection.  Production backends (SaxoExecutionBackend)
        override this to return False; test/stub backends override to return True.
        Defaults to False so that subclasses that don't override are treated as real
        (fail-safe: under-detecting mock is safer than over-detecting it).
        """
        return False

    @property
    def routing_disabled(self) -> bool:
        """Return True if order routing is architecturally disabled for this backend.

        When True, any call to execute_signal MUST hard-block with RoutingDisabledError
        (or a structured ERROR log + no-op for backends that choose that pattern).
        The canonical implementation raises RoutingDisabledError so that misconfigured
        callers fail loudly rather than silently no-oping.

        Knight-Capital defense (CRO requirement 2026-06-01): observe-only / canary
        runners set routing_disabled=True at construction so the guard is structural,
        not reliant on size_multiplier=0.0 alone.  Flipping to False requires an
        explicit construction-time argument change, not a one-line patch.

        Defaults to False (routing enabled) so existing concrete subclasses are
        unaffected — they must opt in to routing_disabled by passing it at init.
        """
        return False

    @abstractmethod
    def execute_signal(
        self, pair: str, signal: float, size: float,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a trading signal. Returns execution result.

        MUST check self.routing_disabled before placing any order and raise
        RoutingDisabledError if routing is disabled.
        """
        ...

    @abstractmethod
    def get_positions(self) -> dict:
        """Get current open positions."""
        ...

    @abstractmethod
    def flatten_all(self) -> list:
        """Close all open positions."""
        ...


@dataclass
class ValidationReport:
    """Result of data quality validation."""

    passed: bool
    pair: str
    issues: list[str]
    row_count: int
    date_range: tuple[str, str] | None = None
