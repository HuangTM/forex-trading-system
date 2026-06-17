"""EMA Golden/Death Cross Strategy — Basket Member M2.

Frozen spec: .fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-minimal-trend-basket-v2.yaml
Trial ID: b309935c
basket_member: M2_EMA_50_200_cross

Signal logic (FROZEN — do not modify without new pre-registration):
  indicator: ema_50 / ema_200 (canonical golden/death cross)
  - Compute EMA(50) and EMA(200) of close
  - Golden cross: EMA(50) > EMA(200) → +1.0 (long)
  - Death cross:  EMA(50) < EMA(200) → -1.0 (short)
  - Flat (0.0): EMA(50) == EMA(200) (exact equality, extremely rare)
  - Always-in: reverses on the opposite cross (no time-stop, no profit target)
  - NOTE: spec mandates EMA (exponential), NOT SMA. MACrossoverStrategy is
    a template using SMA — this class uses ema() directly, per the spec.

Warmup: NaN for the first 200 bars (EMA-200 min_periods=200).
entry_delay_bars=1 applied by the engine (not here).

No-lookahead: EMA at bar t uses data[0..t] only (causal EMA, adjust=False,
min_periods enforced). See test_no_lookahead_ema_cross.
"""

from __future__ import annotations

import logging

import pandas as pd

from forex_system.core.interfaces import Strategy
from forex_system.features.indicators import ema

logger = logging.getLogger(__name__)

# Frozen canonical EMA periods (industry-standard golden/death cross) — DO NOT MODIFY
_FAST: int = 50
_SLOW: int = 200


class EMACrossStrategy(Strategy):
    """EMA(50)/EMA(200) golden/death cross, always-in trend-follower.

    Basket member M2 (trial_id b309935c). Parameters are LITERATURE-FIXED
    (canonical golden/death cross). This class accepts a ``params`` dict for
    interface compatibility but ignores all values — every degree of freedom
    is frozen.

    NOTE: Uses EMA (exponential), not SMA. The existing MACrossoverStrategy
    uses SMA and is NOT reused here because the spec explicitly mandates EMA.
    ema() from features/indicators.py is reused (line 15).
    """

    @property
    def name(self) -> str:
        return "ema_cross"

    def required_indicators(self) -> list[str]:
        """EMA columns are computed internally; no external registry needed."""
        return []

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate always-in EMA(50)/EMA(200) golden/death cross signals.

        Args:
            data: OHLCV DataFrame with close column. Must cover IS window only
                  (caller is responsible for slicing to avoid OOS contamination).

        Returns:
            Series of signals in {-1.0, 0.0, +1.0}, same index as data.
            +1.0 = long (EMA50 > EMA200, golden cross regime)
            -1.0 = short (EMA50 < EMA200, death cross regime)
             0.0 = flat (insufficient warmup or exact equality)

        No-lookahead: EMA at bar t uses data[0..t] only (causal, adjust=False).
        Frozen params: fast=50, slow=200 (canonical golden/death cross).
        """
        if data.empty:
            return pd.Series(dtype=float)

        # Compute EMAs (causal, no lookahead) — reuse existing ema() function
        ema_fast = ema(data["close"], _FAST)
        ema_slow = ema(data["close"], _SLOW)

        signals = pd.Series(0.0, index=data.index)

        # Only generate signals where both EMAs have valid values (past warmup)
        valid = ema_fast.notna() & ema_slow.notna()

        signals[valid & (ema_fast > ema_slow)] = 1.0
        signals[valid & (ema_fast < ema_slow)] = -1.0

        n_long = int((signals == 1.0).sum())
        n_short = int((signals == -1.0).sum())
        n_warmup = int((~valid).sum())

        logger.info(
            "ema_cross.generate_signals: "
            "bars=%d warmup_bars=%d long=%d short=%d flat=%d "
            "params_source=canonical_golden_death_cross fast_ema=%d slow_ema=%d",
            len(data),
            n_warmup,
            n_long,
            n_short,
            len(data) - n_warmup - n_long - n_short,
            _FAST,
            _SLOW,
        )

        return signals
