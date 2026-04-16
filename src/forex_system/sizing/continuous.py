"""Continuous position sizing — signal strength maps to position size.

Flat-as-default: zero signal produces zero position. Weak signals get
proportionally smaller positions. No hard threshold to overfit.
"""

from __future__ import annotations

from forex_system.core.interfaces import PositionSizer


class ContinuousSizer(PositionSizer):
    """Signal strength maps continuously to position size.

    size = base_size * |signal| * confidence * ratchet_level

    where base_size = (equity * risk_per_trade) / (atr * atr_multiple)

    Properties:
        - signal_strength=0 -> size=0 (flat-as-default)
        - signal_strength=1.0, confidence=1.0, ratchet_level=1.0 -> base_size
        - Weak signals get proportionally smaller positions
        - max_order_units caps the maximum size as a circuit breaker
        - min_order_size enforces broker minimum (below = stay flat)
    """

    def __init__(
        self,
        risk_per_trade: float = 0.02,
        stop_loss_atr_multiple: float = 2.0,
        max_order_units: float = 500_000.0,
        min_order_size: float = 1000.0,
    ):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_atr_multiple = stop_loss_atr_multiple
        self.max_order_units = max_order_units
        self.min_order_size = min_order_size

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

        Returns size in base currency units. Always non-negative.
        """
        if abs(signal_strength) < 1e-9 or atr <= 0 or current_price <= 0 or account_equity <= 0:
            return 0.0

        # Base size from ATR-based risk (same formula as engine's _calculate_size)
        stop_distance = atr * self.stop_loss_atr_multiple
        base_size = account_equity * self.risk_per_trade / stop_distance

        # Scale by signal magnitude, confidence, and capital ratchet
        scaled_size = base_size * abs(signal_strength) * confidence * ratchet_level

        # Circuit breaker cap in units (currency-agnostic)
        size = min(scaled_size, self.max_order_units)

        # Enforce broker minimum — below minimum means stay flat
        if size < self.min_order_size:
            return 0.0

        return size
