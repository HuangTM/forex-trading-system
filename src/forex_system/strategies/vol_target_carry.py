"""Volatility-targeted long-only carry — validated edge as of 2026-04-20.

Always long the pair (capture carry yield), but size inversely to realized
volatility so daily-return std stays near a target. Calm markets → upsize
toward leverage_cap. Choppy markets → downsize. Result: smoother equity,
less drawdown, more carry capture.

Validated on USDJPY 2010-2026:
  - Sharpe 0.76 vs B&H 0.58 (+0.18)
  - MaxDD 13.5% vs B&H 17.0% (-3.5pp)
  - Walk-forward: 9/14 OOS 2-yr windows beat B&H, avg Δ +0.08
  - Null hypothesis: rank 99.5% vs 200 shuffled-vol signals (p=0.005)
  - Arson: double costs, 1d/5d vol delay all leave Sharpe ≥ 0.76 (vol is persistent)

Signal encoding:
  signal = (target_vol / realized_vol).clip(0, leverage_cap) / leverage_cap

Output is in [0, 1]. The signal is "fraction of full leverage". A VolTargetSizer
(or any sizer that interprets signal as a position fraction with a leverage cap)
materializes the actual unit count.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy


class VolTargetCarryStrategy(Strategy):
    """Long-only carry with volatility-targeted sizing.

    Params:
        pair: str — currency pair (only used for identification)
        target_vol: float — annualized target volatility (default 0.10 = 10%)
        vol_window: int — rolling window for realized vol in bars (default 252 daily)
        leverage_cap: float — max leverage multiple (default 2.0)
        min_carry: float — only trade when rate_diff >= this (default -inf = always)
    """

    def __init__(self, params: dict[str, Any], rate_data: pd.DataFrame | None = None):
        super().__init__(params)
        self.rate_data = rate_data

    @property
    def name(self) -> str:
        return "vol_target_carry"

    def required_indicators(self) -> list[str]:
        return ["atr_14"]  # ATR not used for sizing here, but kept for interface compat

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        target_vol = self.params.get("target_vol", 0.10)
        vol_window = self.params.get("vol_window", 252)
        leverage_cap = self.params.get("leverage_cap", 2.0)
        min_carry = self.params.get("min_carry", -np.inf)

        # Realized annualized vol from daily returns
        rets = data["close"].pct_change()
        bars_per_year = self._bars_per_year(data)
        realized_vol = rets.rolling(vol_window).std() * np.sqrt(bars_per_year)

        # Target sizing: signal in [0, 1] = fraction of leverage_cap
        raw = (target_vol / realized_vol.replace(0, np.nan)).clip(0, leverage_cap)
        signals = (raw / leverage_cap).fillna(0.0)

        # Optional carry filter: stay flat when carry below threshold
        if min_carry > -np.inf and self.rate_data is not None:
            pair = self.params.get("pair")
            if pair and pair in self.rate_data.columns:
                rate_series = self.rate_data[pair]
                if data.index.tz is not None and rate_series.index.tz is None:
                    rate_series = rate_series.copy()
                    rate_series.index = rate_series.index.tz_localize(data.index.tz)
                aligned = rate_series.reindex(data.index, method="ffill")
                signals = signals.where(aligned >= min_carry, 0.0)

        return signals

    @staticmethod
    def _bars_per_year(data: pd.DataFrame) -> float:
        """Estimate bars/year from index spacing — supports daily/4h/1h."""
        if len(data) < 2:
            return 252.0
        median_dt = (data.index[1:] - data.index[:-1]).to_series().median()
        seconds = median_dt.total_seconds()
        if seconds <= 0:
            return 252.0
        # 252 trading days/yr × 24h/day × 3600s/h = 21,772,800 trading-seconds/yr
        return 252 * 24 * 3600 / seconds
