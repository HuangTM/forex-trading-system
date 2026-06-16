"""Transaction cost modeling — the make-or-break of Phase 0.

Realistic costs determine whether apparent alpha survives to become real edge.
"""

import pandas as pd

from forex_system.core.constants import DEFAULT_PAIRS
from forex_system.core.interfaces import CostModel
from forex_system.core.types import Direction, PairInfo


class RealisticCostModel(CostModel):
    """Fixed spread + slippage + commission + daily swap costs.

    Per-pair parameters from config or defaults.
    """

    def __init__(self, pair_configs: dict[str, PairInfo] | None = None):
        self.pairs = pair_configs or DEFAULT_PAIRS

    def _get_pair(self, pair: str) -> PairInfo:
        p = self.pairs.get(pair.upper())
        if p is None:
            raise ValueError(f"No cost config for pair: {pair}")
        return p

    def entry_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to enter a position (half spread + slippage).

        ``timestamp`` is accepted for interface compatibility but ignored — this
        model uses a fixed per-pair spread.
        """
        p = self._get_pair(pair)
        return p.spread_pips / 2.0 + p.slippage_pips

    def exit_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to exit (half spread + slippage + commission). ``timestamp`` ignored."""
        p = self._get_pair(pair)
        return p.spread_pips / 2.0 + p.slippage_pips + p.commission_pips

    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        """Swap cost in pips for holding a position over N days."""
        p = self._get_pair(pair)
        if direction == Direction.LONG:
            daily_swap = p.swap_long_pips_per_day
        elif direction == Direction.SHORT:
            daily_swap = p.swap_short_pips_per_day
        else:
            return 0.0
        # Negative swap = cost, positive swap = income
        # Return as cost (positive = money lost)
        return -daily_swap * days

    def round_trip_cost(self, pair: str, size: float) -> float:
        """Total cost in pips for entering and exiting a position (excluding swap)."""
        return self.entry_cost(pair, size) + self.exit_cost(pair, size)
