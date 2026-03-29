"""Bollinger Bands + RSI — mean-reversion baseline.

Buy when price < lower band AND RSI < oversold threshold.
Sell when price > upper band AND RSI > overbought threshold.
Flat otherwise (hold current position until opposite signal).
"""

import pandas as pd

from forex_system.core.interfaces import Strategy


class BollingerRSIStrategy(Strategy):

    @property
    def name(self) -> str:
        return "bollinger_rsi"

    def required_indicators(self) -> list[str]:
        bb_period = self.params.get("bb_period", 20)
        bb_std = self.params.get("bb_std", 2.0)
        rsi_period = self.params.get("rsi_period", 14)
        return [f"bb_{bb_period}_{bb_std}", f"rsi_{rsi_period}"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        bb_period = self.params.get("bb_period", 20)
        bb_std = self.params.get("bb_std", 2.0)
        rsi_period = self.params.get("rsi_period", 14)
        rsi_oversold = self.params.get("rsi_oversold", 30)
        rsi_overbought = self.params.get("rsi_overbought", 70)

        upper_col = f"bb_upper_{bb_period}_{bb_std}"
        lower_col = f"bb_lower_{bb_period}_{bb_std}"
        rsi_col = f"rsi_{rsi_period}"

        # Only generate signals where all indicators are valid
        valid = (
            data[upper_col].notna() & data[lower_col].notna() & data[rsi_col].notna()
        )
        signals = pd.Series(0.0, index=data.index)

        # Buy signal: price below lower band AND RSI oversold
        buy_mask = valid & (data["close"] < data[lower_col]) & (data[rsi_col] < rsi_oversold)
        signals[buy_mask] = 1.0

        # Sell signal: price above upper band AND RSI overbought
        sell_mask = valid & (data["close"] > data[upper_col]) & (data[rsi_col] > rsi_overbought)
        signals[sell_mask] = -1.0

        # Forward-fill: hold position until opposite signal fires
        # Replace 0 with NA so ffill carries the last non-zero signal forward
        signals = signals.replace(0.0, pd.NA).ffill().fillna(0.0)

        return signals
