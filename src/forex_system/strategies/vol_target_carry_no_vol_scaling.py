"""Ablation: vol_target_carry without volatility-targeted sizing.

This module is an ablation of the validated VolTargetCarryStrategy. It removes
the vol-targeting position-sizing signal, replacing it with unit/fixed sizing
(signal = 1.0 always long, same carry direction). Everything else — the
long-only carry direction, the carry filter, the required indicators interface
— is unchanged.

Purpose
-------
Tests whether vol-targeting is load-bearing for the edge in vol_target_carry,
or incidental. If this ablation also achieves Sharpe >= 0.30 on OOS-2022, that
suggests vol-targeting is NOT the source of alpha (and carry direction alone
drives it). If it rejects, vol-targeting is likely load-bearing or the combination
(carry + vol scale) is necessary for the validated edge.

Pre-reg: references/pre-registrations/vol_target_carry_no_vol_scaling.md
Wave-5 Round-2 candidate #6.

Signal encoding
---------------
signal = 1.0 always (unit long; no vol scaling).
The backtester applies its own position sizer on top; with a FixedFractional or
default sizer this means constant position size per bar (no volatility targeting).

DO NOT modify validated vol_target_carry.py — this is a separate module.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy


class VolTargetCarryNoVolScalingStrategy(Strategy):
    """Long-only carry with fixed (unit) sizing — no volatility targeting.

    This is an ablation of VolTargetCarryStrategy. The vol-targeting signal
    (target_vol / realized_vol).clip(0, leverage_cap) is replaced with a
    constant signal of 1.0 (always max long). The carry-filter gate is
    preserved intact to keep the test honest: if this ablation uses the same
    carry filter, any Sharpe difference is attributable to vol-scaling alone.

    Params
    ------
    pair : str
        Currency pair (informational only; used for carry filter lookup).
    min_carry : float
        Only go long when rate_diff >= this threshold (default -inf = always).
        Mirrors the vol_target_carry min_carry param for ablation parity.
    """

    def __init__(self, params: dict[str, Any], rate_data: pd.DataFrame | None = None):
        super().__init__(params)
        self.rate_data = rate_data

    @property
    def name(self) -> str:
        return "vol_target_carry_no_vol_scaling"

    def required_indicators(self) -> list[str]:
        # Preserved from vol_target_carry for interface compatibility.
        # atr_14 is not used for signal generation in either strategy (kept for compat).
        return ["atr_14"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate constant long signal (1.0) with optional carry filter.

        No vol-targeting: signal = 1.0 throughout. The carry filter (if
        min_carry is set) gates the signal to 0.0 when rate_diff is below
        the threshold — identical to the parent strategy's carry-filter logic.
        """
        min_carry = self.params.get("min_carry", -np.inf)

        # Base signal: always long (unit sizing, no vol targeting).
        signals = pd.Series(1.0, index=data.index, dtype=float)

        # Optional carry filter — preserves ablation parity with vol_target_carry.
        if min_carry > -np.inf and self.rate_data is not None:
            pair = self.params.get("pair")
            if pair and pair in self.rate_data.columns:
                rate_series = self.rate_data[pair]
                if data.index.tz is not None and rate_series.index.tz is None:
                    rate_series = rate_series.copy()
                    rate_series.index = rate_series.index.tz_localize(data.index.tz)
                aligned = rate_series.reindex(data.index, method="ffill")
                signals = signals.where(aligned >= min_carry, 0.0)

        return signals
