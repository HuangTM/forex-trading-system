"""Continuous position sizing — signal strength maps to position size.

Flat-as-default: zero signal produces zero position. Weak signals get
proportionally smaller positions. No hard threshold to overfit.
"""

from __future__ import annotations

import logging

from forex_system.core.interfaces import PositionSizer

logger = logging.getLogger(__name__)


class ContinuousSizer(PositionSizer):
    """Signal strength maps continuously to position size.

    size = base_size * |signal| * confidence * ratchet_level

    where base_size = (equity * risk_per_trade) / (atr * atr_multiple)

    Output unit contract (usd_nominal):
        - usd_nominal=False (default, legacy): size is in the discrete-mode
          convention where P&L = price_change x size (quote currency). This is
          what the engine's discrete mode expects — do not change.
        - usd_nominal=True: size is USD-nominal exposure, the contract the
          engine's CONTINUOUS mode expects (see engine._to_engine_units and
          VolTargetSizer). For JPY-quoted pairs the legacy size is multiplied
          by current_price; for USD-quoted pairs it is already USD-nominal.
          Without this, continuous mode on JPY pairs divides the legacy size
          by price a second time, carrying ~1/price of the intended risk.

    Properties:
        - signal_strength=0 -> size=0 (flat-as-default)
        - signal_strength=1.0, confidence=1.0, ratchet_level=1.0 -> base_size
        - Weak signals get proportionally smaller positions
        - max_order_units caps the maximum size as a circuit breaker
        - min_order_size enforces broker minimum (below = stay flat); clips of
          nonzero sizes are counted on self.n_clipped_to_zero and logged once
    """

    def __init__(
        self,
        risk_per_trade: float = 0.02,
        stop_loss_atr_multiple: float = 2.0,
        max_order_units: float = 500_000.0,
        min_order_size: float = 1000.0,
        usd_nominal: bool = False,
    ):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_atr_multiple = stop_loss_atr_multiple
        self.max_order_units = max_order_units
        self.min_order_size = min_order_size
        self.usd_nominal = usd_nominal
        # Loud-floor accounting: number of nonzero target sizes clipped to 0.0
        # by the min_order_size floor. Read by the engine into result metadata.
        self.n_clipped_to_zero = 0

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
        """Calculate position size scaled by signal strength, confidence, and ratchet.

        Returns size in base currency units (usd_nominal=False) or USD-nominal
        exposure (usd_nominal=True). Always non-negative.
        """
        if abs(signal_strength) < 1e-9 or atr <= 0 or current_price <= 0 or account_equity <= 0:
            return 0.0

        # Base size from ATR-based risk (same formula as engine's _calculate_size)
        stop_distance = atr * self.stop_loss_atr_multiple
        base_size = account_equity * self.risk_per_trade / stop_distance

        # Scale by signal magnitude, confidence, and capital ratchet
        size = base_size * abs(signal_strength) * confidence * ratchet_level

        # Convert to the engine's continuous-mode USD-nominal convention.
        # Mirrors engine._to_engine_units: only JPY-quoted pairs need the
        # price multiplication; USD-quoted pairs are already USD-nominal.
        if self.usd_nominal and pair.upper().endswith("JPY"):
            size *= current_price

        # Circuit breaker cap (in output units)
        size = min(size, self.max_order_units)

        # Enforce broker minimum — below minimum means stay flat.
        # Fail-loud: a nonzero target clipped to flat used to be silent and
        # produced degenerate flat equity curves that looked like "no edge".
        if size < self.min_order_size:
            if size > 0.0:
                self.n_clipped_to_zero += 1
                if self.n_clipped_to_zero == 1:
                    logger.warning(
                        "ContinuousSizer: nonzero target size %.2f clipped to 0 by "
                        "min_order_size=%.2f (pair=%s). Further clips are counted on "
                        "sizer.n_clipped_to_zero and summarized by the engine at "
                        "end of run.",
                        size,
                        self.min_order_size,
                        pair,
                    )
            return 0.0

        return size
