"""FRED-rates carry strategy — regime-conditioning STRIPPED variant.

Phase-2 Falsification R7: Test whether BoJ-divergence regime filter in
carry_fred provides incremental alpha. This module runs the identical carry
signal construction as CarryFREDStrategy but with ALL regime / macro filters
removed. If this stripped version achieves OOS Sharpe >= 0.60 (matching or
exceeding carry_fred), the regime conditioning FAILS to falsify.

Signal construction (pre-registered R7):
  1. rate_differential = base_rate - quote_rate from FRED, forward-filled daily
  2. Cross-sectional rank-normalization (z-score) across all 12 pairs at each bar
  3. Long-short balanced: top quintile long (+signal), bottom quintile short
     (-signal), neutral middle. Implemented by clipping z-score to [-1, +1].

Differences from CarryFREDStrategy (carry_fred):
  - NO BoJ-divergence regime filter
  - NO FRED macro conditioning
  - Pure carry signal only

Decision trace: every signal batch is logged with regime_filter_applied=False
so the audit trail confirms the conditioning was deliberately absent.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy

logger = logging.getLogger("forex_system.strategies.fred_carry_stripped")

# Maps pair symbol -> column name in rate_differentials.parquet
# Identical to carry_fred; duplicated here to keep the module self-contained.
_PAIR_TO_COL: dict[str, str] = {
    "AUDJPY": "AUDJPY_diff",
    "AUDUSD": "AUDUSD_diff",
    "CADJPY": "CADJPY_diff",
    "EURGBP": "EURGBP_diff",
    "EURJPY": "EURJPY_diff",
    "EURUSD": "EURUSD_diff",
    "GBPJPY": "GBPJPY_diff",
    "GBPUSD": "GBPUSD_diff",
    "NZDJPY": "NZDJPY_diff",
    "NZDUSD": "NZDUSD_diff",
    "USDCAD": "USDCAD_diff",
    "USDJPY": "USDJPY_diff",
}

_DEFAULT_RATE_DATA_PATH = "data/rates/rate_differentials.parquet"


def _log_decision(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log line (JSON)."""
    entry = {"event": event, **fields}
    logger.info(json.dumps(entry))


def _load_rate_data(path: str) -> pd.DataFrame:
    """Load FRED rate differentials. Index must be datetime."""
    df = pd.read_parquet(path)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


class FredCarryStrippedStrategy(Strategy):
    """FX carry strategy using FRED rate differentials — NO regime filter.

    Phase-2 R7 falsification instrument. Identical carry signal to carry_fred
    with the BoJ-divergence regime conditioning removed. Compare OOS Sharpe
    against carry_fred to evaluate whether regime filter adds alpha.

    If stripped OOS Sharpe >= 0.60 → regime conditioning FAILS to falsify
    (trigger fred_carry_stripped-T5 fires).

    Params:
        pair: str — currency pair symbol (e.g., "USDJPY")
        rate_data_path: str — path to rate_differentials.parquet
            (default: data/rates/rate_differentials.parquet)
        rank_normalize: bool — if True (default), z-score cross-sectionally
        min_differential: float — abs threshold below which signal = 0.0
            (default 0.001)
        max_differential: float — used only when rank_normalize=False
            (default 0.05)
    """

    def __init__(self, params: dict[str, Any], rate_data: pd.DataFrame | None = None):
        super().__init__(params)
        self._rate_data = rate_data
        self._rate_data_loaded = rate_data is not None

    @property
    def name(self) -> str:
        return "fred_carry_stripped"

    def required_indicators(self) -> list[str]:
        # No indicators required — pure rate-differential signal
        return []

    def _get_rate_data(self) -> pd.DataFrame:
        """Lazy-load rate data on first use."""
        if not self._rate_data_loaded:
            path = self.params.get("rate_data_path", _DEFAULT_RATE_DATA_PATH)
            self._rate_data = _load_rate_data(path)
            self._rate_data_loaded = True
        return self._rate_data  # type: ignore[return-value]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate carry signals with NO regime conditioning.

        Returns pd.Series aligned to data.index with values in [-1, +1].
        Decision trace logs regime_filter_applied=False per every call.
        """
        pair = str(self.params.get("pair", "")).upper()
        if not pair:
            raise ValueError("FredCarryStrippedStrategy: 'pair' param is required")

        col = _PAIR_TO_COL.get(pair)
        if col is None:
            raise ValueError(
                f"FredCarryStrippedStrategy: unknown pair '{pair}'. "
                f"Supported: {list(_PAIR_TO_COL.keys())}"
            )

        rate_data = self._get_rate_data()

        if col not in rate_data.columns:
            raise ValueError(
                f"FredCarryStrippedStrategy: column '{col}' not found in rate_data. "
                f"Available: {list(rate_data.columns)}"
            )

        rank_normalize = bool(self.params.get("rank_normalize", True))
        min_diff = float(self.params.get("min_differential", 0.001))

        # Decision trace: confirm regime filter is absent
        _log_decision(
            "fred_carry_stripped.generate_signals",
            pair=pair,
            n_bars=len(data),
            rank_normalize=rank_normalize,
            regime_filter_applied=False,  # KEY: audit trail marker
            r7_instrument=True,
        )

        if rank_normalize:
            return self._ranked_signals(data, rate_data, col, min_diff)
        else:
            return self._raw_signals(data, rate_data, col, min_diff)

    def _ranked_signals(
        self,
        data: pd.DataFrame,
        rate_data: pd.DataFrame,
        col: str,
        min_diff: float,
    ) -> pd.Series:
        """Cross-sectional z-score rank signal (no regime conditioning)."""
        available_cols = [c for c in _PAIR_TO_COL.values() if c in rate_data.columns]
        cross_section = rate_data[available_cols]

        ohlcv_index = data.index
        if ohlcv_index.tz is not None:
            ohlcv_index_naive = ohlcv_index.tz_localize(None)
        else:
            ohlcv_index_naive = ohlcv_index

        if rate_data.index.tz is not None:
            cs_reindexed = cross_section.copy()
            cs_reindexed.index = cs_reindexed.index.tz_localize(None)
        else:
            cs_reindexed = cross_section

        combined_idx = cs_reindexed.index.union(ohlcv_index_naive).sort_values()
        cs_daily = cs_reindexed.reindex(combined_idx).ffill().reindex(ohlcv_index_naive)

        cross_mean = cs_daily.mean(axis=1)
        cross_std = cs_daily.std(axis=1)
        this_pair_diff = cs_daily[col]

        z_score = (this_pair_diff - cross_mean) / cross_std.replace(0.0, np.nan)
        z_score = z_score.fillna(0.0)
        signals = z_score.clip(-1.0, 1.0)

        raw_diff = cs_daily[col]
        signals = signals.where(raw_diff.abs() >= min_diff, 0.0)
        signals.index = data.index

        return signals.fillna(0.0)

    def _raw_signals(
        self,
        data: pd.DataFrame,
        rate_data: pd.DataFrame,
        col: str,
        min_diff: float,
    ) -> pd.Series:
        """Fallback: signal = clipped(raw_differential / max_differential)."""
        max_diff = float(self.params.get("max_differential", 0.05))

        rate_series = rate_data[col]
        if data.index.tz is not None and rate_series.index.tz is None:
            ohlcv_index_naive = data.index.tz_localize(None)
        elif data.index.tz is None and rate_series.index.tz is not None:
            ohlcv_index_naive = data.index
            rate_series = rate_series.copy()
            rate_series.index = rate_series.index.tz_localize(None)
        else:
            ohlcv_index_naive = data.index

        combined_idx = rate_series.index.union(ohlcv_index_naive).sort_values()
        aligned = rate_series.reindex(combined_idx).ffill().reindex(ohlcv_index_naive)

        signals = (aligned / max_diff).clip(-1.0, 1.0)
        signals = signals.where(aligned.abs() >= min_diff, 0.0)
        signals.index = data.index
        return signals.fillna(0.0)
