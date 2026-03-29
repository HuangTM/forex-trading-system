"""Position sizing — fixed fractional risk model.

Calculates position size based on account equity, ATR-based stop distance,
and risk percentage per trade.
"""

from forex_system.core.interfaces import PositionSizer


class FixedFractionalSizer(PositionSizer):
    """Risk a fixed percentage of equity per trade.

    Size = (equity * risk_pct) / (ATR * atr_multiple * pip_value)
    """

    def __init__(
        self,
        risk_per_trade: float = 0.02,
        atr_multiple: float = 2.0,
        max_position_pct: float = 0.10,
    ):
        self.risk_per_trade = risk_per_trade
        self.atr_multiple = atr_multiple
        self.max_position_pct = max_position_pct

    def calculate_size(
        self,
        signal_strength: float,
        account_equity: float,
        current_price: float,
        atr: float,
        pair: str,
    ) -> float:
        if atr <= 0 or current_price <= 0 or account_equity <= 0:
            return 0.0

        # Risk amount in account currency
        risk_amount = account_equity * self.risk_per_trade * abs(signal_strength)

        # Stop distance in price units
        stop_distance = atr * self.atr_multiple

        # Position size in units of base currency
        size = risk_amount / stop_distance

        # Cap at max position size
        max_size = (account_equity * self.max_position_pct) / current_price
        size = min(size, max_size)

        return size
