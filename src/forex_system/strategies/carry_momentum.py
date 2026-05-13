"""Carry-adjusted momentum — the direction-timing hybrid.

Carry (slow, macro) tells you WHICH direction has structural edge.
Momentum (fast, technical) tells you WHEN to enter and exit.

Signal logic:
  - Compute carry direction from rate differentials
  - Compute momentum from price (SMA crossover or ROC)
  - Signal = carry_weight * carry_signal + momentum_weight * momentum_signal
  - When carry and momentum agree: strong signal
  - When they disagree: weak or zero signal (flat-as-default)

This produces more trades than pure carry (better statistical power)
while filtering out momentum signals that fight the macro direction.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy


class CarryMomentumStrategy(Strategy):
    """Carry-adjusted momentum: combine macro direction with price timing.

    Params:
        pair: str — currency pair
        carry_weight: float — weight of carry signal (default 0.5)
        momentum_weight: float — weight of momentum signal (default 0.5)
        min_differential: float — min carry to consider (default 0.002 = 0.2%)
        max_differential: float — carry that maps to signal=1 (default 0.05 = 5%)
        fast_period: int — fast SMA period for momentum (default 20)
        slow_period: int — slow SMA period for momentum (default 50)
        agreement_only: bool — only trade when carry and momentum agree (default True)
    """

    def __init__(self, params: dict[str, Any], *, rate_data: pd.DataFrame | None = None):
        # REM-1 / D-1.1: keyword-only rate_data per ABC contract
        super().__init__(params, rate_data=rate_data)
        # self.rate_data is set by ABC __init__

    @property
    def name(self) -> str:
        return "carry_momentum"

    def required_indicators(self) -> list[str]:
        fast = self.params.get("fast_period", 20)
        slow = self.params.get("slow_period", 50)
        return [f"sma_{fast}", f"sma_{slow}", "atr_14"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Combined carry + momentum signal."""
        carry = self._carry_signal(data)
        momentum = self._momentum_signal(data)

        carry_w = self.params.get("carry_weight", 0.5)
        momentum_w = self.params.get("momentum_weight", 0.5)
        agreement_only = self.params.get("agreement_only", True)

        if agreement_only:
            # Only trade when carry and momentum agree on direction
            carry_dir = np.sign(carry)
            mom_dir = np.sign(momentum)
            agree = (carry_dir == mom_dir) & (carry_dir != 0)

            # Combined signal where they agree, zero where they don't
            combined = (carry_w * carry + momentum_w * momentum).clip(-1.0, 1.0)
            signals = combined.where(agree, 0.0)
        else:
            # Weighted blend regardless of agreement
            signals = (carry_w * carry + momentum_w * momentum).clip(-1.0, 1.0)

        return signals.fillna(0.0)

    def _carry_signal(self, data: pd.DataFrame) -> pd.Series:
        """Carry component: direction from rate differentials."""
        if self.rate_data is None:
            return pd.Series(0.0, index=data.index)

        pair = self.params.get("pair")
        if pair is None or pair not in self.rate_data.columns:
            return pd.Series(0.0, index=data.index)

        min_diff = self.params.get("min_differential", 0.002)
        max_diff = self.params.get("max_differential", 0.05)

        rate_series = self.rate_data[pair]
        if data.index.tz is not None and rate_series.index.tz is None:
            rate_series = rate_series.copy()
            rate_series.index = rate_series.index.tz_localize(data.index.tz)

        aligned = rate_series.reindex(data.index, method="ffill")
        signals = (aligned / max_diff).clip(-1.0, 1.0)
        signals = signals.where(aligned.abs() >= min_diff, 0.0)
        return signals.fillna(0.0)

    def _momentum_signal(self, data: pd.DataFrame) -> pd.Series:
        """Momentum component: SMA crossover strength."""
        fast_period = self.params.get("fast_period", 20)
        slow_period = self.params.get("slow_period", 50)
        fast_col = f"sma_{fast_period}"
        slow_col = f"sma_{slow_period}"

        if fast_col not in data.columns or slow_col not in data.columns:
            return pd.Series(0.0, index=data.index)

        fast_sma = data[fast_col]
        slow_sma = data[slow_col]

        valid = fast_sma.notna() & slow_sma.notna() & (slow_sma > 0)

        # Normalized distance between fast and slow SMA
        # Positive when fast > slow (uptrend), negative when fast < slow (downtrend)
        distance = (fast_sma - slow_sma) / slow_sma
        # Scale to [-1, 1]: divide by typical distance (2% of price)
        scale = self.params.get("momentum_scale", 0.02)
        signals = (distance / scale).clip(-1.0, 1.0)

        return signals.where(valid, 0.0).fillna(0.0)
