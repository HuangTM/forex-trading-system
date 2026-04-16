"""Carry trade strategy — long high-yield, short low-yield currency.

The one FX strategy with decades of academic evidence (Sharpe ~0.89
historically). Signal is proportional to interest rate differential
between the base and quote currencies.

Dynamic mode: uses historical FRED rate differential data.
Static fallback: constant signal from PairInfo swap direction (with warning).
"""

from __future__ import annotations

import warnings
from typing import Any

import pandas as pd

from forex_system.core.interfaces import Strategy


class CarryStrategy(Strategy):
    """FX Carry: long high-yield, short low-yield currency.

    Params:
        pair: str — currency pair symbol (e.g., "USDJPY")
        min_differential: float — minimum abs differential to trade (default 0.005 = 0.5%)
        max_differential: float — differential that maps to signal=1.0 (default 0.05 = 5%)
        swap_long_pips_per_day: float — for static fallback mode
        swap_short_pips_per_day: float — for static fallback mode
    """

    def __init__(self, params: dict[str, Any], rate_data: pd.DataFrame | None = None):
        """
        Args:
            params: Strategy parameters (see class docstring).
            rate_data: DataFrame indexed by date with a column per pair
                       containing rate differentials as decimals (e.g., 0.0289
                       for 2.89%). If None, falls back to static swap direction.
        """
        super().__init__(params)
        self.rate_data = rate_data
        self._warned_static = False

    @property
    def name(self) -> str:
        return "carry"

    def required_indicators(self) -> list[str]:
        return ["atr_14"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate carry signals.

        Dynamic mode: signal proportional to interest rate differential.
        Static fallback: constant signal from swap direction.
        """
        if self.rate_data is not None:
            return self._dynamic_signals(data)
        return self._static_signals(data)

    def _dynamic_signals(self, data: pd.DataFrame) -> pd.Series:
        """Signals from historical rate differentials."""
        pair = self.params.get("pair")
        if pair is None or pair not in self.rate_data.columns:
            available = list(self.rate_data.columns)
            raise ValueError(
                f"Rate data missing column for pair '{pair}'. "
                f"Available: {available}"
            )

        min_diff = self.params.get("min_differential", 0.005)
        max_diff = self.params.get("max_differential", 0.05)

        # Align rate data to OHLCV dates (forward-fill: rates change infrequently)
        rate_series = self.rate_data[pair]
        # Handle timezone mismatch: normalize both to tz-naive for reindex
        if data.index.tz is not None and rate_series.index.tz is None:
            rate_series = rate_series.copy()
            rate_series.index = rate_series.index.tz_localize(data.index.tz)
        elif data.index.tz is None and rate_series.index.tz is not None:
            rate_series = rate_series.copy()
            rate_series.index = rate_series.index.tz_localize(None)
        aligned = rate_series.reindex(data.index, method="ffill")

        # Signal proportional to differential, clipped to [-1, 1]
        signals = (aligned / max_diff).clip(-1.0, 1.0)

        # Zero out signals below minimum threshold
        signals = signals.where(aligned.abs() >= min_diff, 0.0)

        return signals.fillna(0.0)

    def _static_signals(self, data: pd.DataFrame) -> pd.Series:
        """Fallback: constant signal from static swap direction."""
        if not self._warned_static:
            warnings.warn(
                "CarryStrategy: using static swap rates. Signals will be constant. "
                "Pass rate_data for dynamic signals.",
                UserWarning,
                stacklevel=3,
            )
            self._warned_static = True

        swap_long = self.params.get("swap_long_pips_per_day", 0.0)
        swap_short = self.params.get("swap_short_pips_per_day", 0.0)

        if swap_long > swap_short:
            signal_val = 1.0
        elif swap_short > swap_long:
            signal_val = -1.0
        else:
            signal_val = 0.0

        return pd.Series(signal_val, index=data.index)
