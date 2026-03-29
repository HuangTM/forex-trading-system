"""Moving Average Crossover — trend-following baseline.

Long when fast SMA > slow SMA, short when fast < slow.
Default: 50/200 SMA (Golden Cross / Death Cross).
"""

import pandas as pd

from forex_system.core.interfaces import Strategy


class MACrossoverStrategy(Strategy):

    @property
    def name(self) -> str:
        return "ma_crossover"

    def required_indicators(self) -> list[str]:
        fast = self.params.get("fast_period", 50)
        slow = self.params.get("slow_period", 200)
        return [f"sma_{fast}", f"sma_{slow}"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast = self.params.get("fast_period", 50)
        slow = self.params.get("slow_period", 200)

        fast_col = f"sma_{fast}"
        slow_col = f"sma_{slow}"

        # Only generate signals where both MAs have valid values
        valid = data[fast_col].notna() & data[slow_col].notna()
        signals = pd.Series(0.0, index=data.index)
        signals[valid & (data[fast_col] > data[slow_col])] = 1.0
        signals[valid & (data[fast_col] < data[slow_col])] = -1.0

        return signals
