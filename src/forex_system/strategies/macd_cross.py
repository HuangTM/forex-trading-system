"""MACD Signal-Line Cross Strategy — Basket Member M1.

Frozen spec: .fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-minimal-trend-basket-v2.yaml
Trial ID: 82497d05
basket_member: M1_MACD_cross

Signal logic (FROZEN — do not modify without new pre-registration):
  indicator: macd_12_26_9 (Appel canonical, Gerald Appel 2005)
  - Compute MACD line = EMA(12) - EMA(26)
  - Compute signal line = EMA(9) of MACD line
  - Long (+1.0) when MACD line > signal line
  - Short (-1.0) when MACD line < signal line
  - Flat (0.0) when MACD line == signal line (exact equality; rare)
  - Always-in: reverses on opposite cross (no time-stop, no profit target)

Warmup: NaN for first max(26, 26+9-1) = 34 bars (EMA warmup propagated).
entry_delay_bars=1 applied by the engine (not here).

No-lookahead guarantee: EMA values at bar t use data[0..t] only (causal EMA,
adjust=False, min_periods enforced). The signal at bar t is generated from
data available at bar t close — the engine shifts by entry_delay_bars=1 so
the trade executes at bar t+1. See test_no_lookahead_macd_cross.
"""

from __future__ import annotations

import logging

import pandas as pd

from forex_system.core.interfaces import Strategy
from forex_system.features.indicators import macd

logger = logging.getLogger(__name__)

# Frozen canonical MACD parameters (Appel 2005) — DO NOT MODIFY
_FAST: int = 12
_SLOW: int = 26
_SIGNAL: int = 9


class MACDCrossStrategy(Strategy):
    """MACD(12,26,9) signal-line cross, always-in trend-follower.

    Basket member M1 (trial_id 82497d05). Parameters are LITERATURE-FIXED
    (Appel canonical). This class accepts a ``params`` dict for interface
    compatibility but ignores all values — every degree of freedom is frozen.
    """

    @property
    def name(self) -> str:
        return "macd_cross"

    def required_indicators(self) -> list[str]:
        """MACD columns are computed internally; no external registry needed."""
        return []

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate always-in MACD signal-line cross signals.

        Args:
            data: OHLCV DataFrame with close column. Must cover IS window only
                  (caller is responsible for slicing to avoid OOS contamination).

        Returns:
            Series of signals in {-1.0, 0.0, +1.0}, same index as data.
            +1.0 = long (MACD line > signal line, bullish momentum)
            -1.0 = short (MACD line < signal line, bearish momentum)
             0.0 = flat (insufficient warmup or exact equality)

        No-lookahead: EMA at bar t uses data[0..t] only (causal, adjust=False).
        Frozen params: fast=12, slow=26, signal=9 (Appel canonical).
        """
        if data.empty:
            return pd.Series(dtype=float)

        # Compute MACD components (causal EMAs, no lookahead)
        macd_line, signal_line, _ = macd(
            data["close"],
            fast=_FAST,
            slow=_SLOW,
            signal=_SIGNAL,
        )

        signals = pd.Series(0.0, index=data.index)

        # Only generate signals where both lines have valid values (past warmup)
        valid = macd_line.notna() & signal_line.notna()

        signals[valid & (macd_line > signal_line)] = 1.0
        signals[valid & (macd_line < signal_line)] = -1.0

        n_long = int((signals == 1.0).sum())
        n_short = int((signals == -1.0).sum())
        n_warmup = int((~valid).sum())

        logger.info(
            "macd_cross.generate_signals: "
            "bars=%d warmup_bars=%d long=%d short=%d flat=%d "
            "params_source=Appel_2005_canonical fast=%d slow=%d signal=%d",
            len(data),
            n_warmup,
            n_long,
            n_short,
            len(data) - n_warmup - n_long - n_short,
            _FAST,
            _SLOW,
            _SIGNAL,
        )

        return signals
