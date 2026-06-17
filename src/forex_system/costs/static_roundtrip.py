"""Static Round-Trip Cost Model — Trial 48 (A2′ overnight mean-reversion).

A frozen, conservative round-trip cost of 7.5 pips charged to EVERY trade,
regardless of pair, size, or timestamp.

Justification (from pre-registration qr-prereg-v2.yaml):
    Built from the empirical 4h spread distribution for the 02:00-05:00 UTC
    overnight session: per-side spread P90 ~2.6 pips (rounding toward all-session
    P90, conservative vs measured overnight P90 ~2.1), x2 legs = 5.2; plus
    ~1.6 pips round-trip thin-book slippage; plus ~0.7 pips round-trip commission
    = 7.5 pips total. This is NOT the median (4.0 rt), NOT the config default
    (1.5/side optimistic). It is deliberately OVER-STATED so that any strategy
    surviving it has real margin.

Design:
    Round-trip = 7.5 pips total. The engine charges entry_cost at entry and
    exit_cost at exit. We split 3.75 / 3.75 for symmetry. Total is exactly 7.5.
    holding_cost returns 0.0 — single-bar hold, swap inert per frozen spec.

DO NOT modify the constants without a new pre-registration. They are FROZEN.
"""

from __future__ import annotations

import pandas as pd

from forex_system.core.interfaces import CostModel
from forex_system.core.types import Direction

# Frozen — do not change without new pre-registration
_ROUND_TRIP_PIPS: float = 7.5
_HALF_COST_PIPS: float = _ROUND_TRIP_PIPS / 2.0  # 3.75 each leg


class StaticRoundTripCostModel(CostModel):
    """Fixed 7.5-pip round-trip cost applied to every trade (Trial 48, frozen).

    Ignores pair, size, and timestamp — the frozen constant is the same
    regardless of execution conditions. This is conservative-by-construction:
    it charges the P90-grade overnight spread + thin-book slippage + commission
    to every single trade, including those that would have traded at the median.

    Usage::

        cost_model = StaticRoundTripCostModel()
        # entry cost: 3.75 pips; exit cost: 3.75 pips; total: 7.5 pips
    """

    def entry_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Return half the static round-trip cost (3.75 pips)."""
        return _HALF_COST_PIPS

    def exit_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Return the other half of the static round-trip cost (3.75 pips)."""
        return _HALF_COST_PIPS

    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        """Return 0.0 — single-bar hold; swap is inert per frozen spec (F-004)."""
        return 0.0
