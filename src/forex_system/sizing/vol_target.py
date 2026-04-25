"""Position sizer for vol-targeted strategies.

Interprets `signal_strength` as a fraction of full leverage_cap × notional.
Long-only (negative signals → flat).

units = signal_strength * leverage_cap * account_equity

For Saxo FX, "units" means base-currency units (e.g., USD for USDJPY). So
account_equity in USD maps directly to units of base currency exposure with
no division by price. signal=1.0, leverage=2.0, equity=$1M → 2,000,000 USD
nominal exposure (= 2x leverage).

Doesn't use ATR — sizing is fully determined by the strategy's vol-targeted signal.

Engine P&L note
---------------
The backtest engine computes P&L as:
    pnl = price_change * units

For USD-quoted pairs (EURUSD, GBPUSD) where `price_change` is already in USD
per unit, this is correct. For JPY-quoted pairs (USDJPY, EURJPY) the engine
divides units by `current_price` internally (see _run_continuous) so that:
    pnl_usd = delta_price_jpy * (notional_usd / price) = fractional_return * notional_usd

This keeps the sizer's output as USD nominal (matching Saxo FX order semantics)
while the engine handles the quote-currency conversion transparently.
"""

from __future__ import annotations

from forex_system.core.interfaces import PositionSizer


class VolTargetSizer(PositionSizer):
    """Materialize a vol-targeted signal into USD-nominal units.

    signal=1.0 → leverage_cap × notional. signal=0.5 → 0.5 × leverage_cap × notional.
    Negative signals clamp to 0 (long-only).

    Output is always in USD nominal: 1 unit = 1 USD of base-currency exposure.
    For Saxo FX this maps directly to the order size field.

    The backtest engine's _run_continuous applies quote-currency correction
    for non-USD-quoted pairs (JPY, CHF, etc.) so that P&L is computed correctly.

    Args:
        leverage_cap: max leverage multiple matching the strategy (default 2.0)
        max_order_units: hard cap on units (circuit breaker)
        min_order_size: broker minimum (below = stay flat)
    """

    def __init__(
        self,
        leverage_cap: float = 2.0,
        max_order_units: float = 10_000_000.0,
        min_order_size: float = 1000.0,
    ):
        self.leverage_cap = leverage_cap
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
        if signal_strength <= 0 or current_price <= 0 or account_equity <= 0:
            return 0.0

        scale = min(signal_strength, 1.0)  # signal already in [0, 1] from strategy
        # Saxo FX: 1 unit = 1 base-currency unit (USD for USDJPY). Equity is in
        # USD, so units = equity for 1.0x leverage at signal=1.0.
        units = scale * self.leverage_cap * account_equity
        units *= confidence * ratchet_level
        units = min(units, self.max_order_units)

        if units < self.min_order_size:
            return 0.0
        return units
