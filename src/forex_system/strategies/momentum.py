"""Simple Momentum — long when recent return positive, short when negative.

Uses percentage return over a lookback period.
Default: 20-day lookback.
"""

import pandas as pd

from forex_system.core.interfaces import Strategy


class MomentumStrategy(Strategy):

    @property
    def name(self) -> str:
        return "momentum"

    def required_indicators(self) -> list[str]:
        period = self.params.get("lookback_period", 20)
        return [f"momentum_{period}"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        period = self.params.get("lookback_period", 20)
        threshold = self.params.get("threshold", 0.0)
        mom_col = f"momentum_{period}"

        valid = data[mom_col].notna()
        signals = pd.Series(0.0, index=data.index)
        signals[valid & (data[mom_col] > threshold)] = 1.0
        signals[valid & (data[mom_col] < -threshold)] = -1.0

        return signals
