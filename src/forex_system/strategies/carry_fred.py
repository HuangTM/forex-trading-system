"""FRED-rates carry strategy — long-short on cross-sectional rate-differential rank.

HoQR CONSENSUS Bet #1 pre-registered 2026-04-25.

Signal construction (pre-registered):
  1. rate_differential = base_rate - quote_rate from FRED, forward-filled daily
  2. Cross-sectional rank-normalization (z-score) across all 12 pairs at each bar
  3. Long-short balanced: top quintile long (+signal), bottom quintile short
     (-signal), neutral middle. Implemented by clipping z-score to [-1, +1].

All 12 pairs share a single rate_data DataFrame (date-indexed, 12 diff columns).
Each strategy instance receives one pair symbol and extracts its column.

OOS holdout enforced externally in harness config (oos_holdout_start: 2023-04-25).
This class has no awareness of the holdout boundary — the harness slices data.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy

# Maps pair symbol -> column name in rate_differentials.parquet
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

# Default path relative to project root
_DEFAULT_RATE_DATA_PATH = "data/rates/rate_differentials.parquet"


def _load_rate_data(path: str) -> pd.DataFrame:
    """Load FRED rate differentials. Index must be datetime."""
    df = pd.read_parquet(path)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


class CarryFREDStrategy(Strategy):
    """FX carry strategy using FRED central-bank rate differentials.

    Pre-registered as CONSENSUS Bet #1 (2026-04-25).

    Params:
        pair: str — currency pair symbol (e.g., "USDJPY")
        rate_data_path: str — path to rate_differentials.parquet
            (default: data/rates/rate_differentials.parquet)
        rank_normalize: bool — if True (default), z-score the per-pair
            differential against ALL 12 pairs at each bar (cross-sectional
            rank). If False, uses raw differential / max_differential.
        min_differential: float — abs threshold below which signal = 0.0
            (default 0.001 = 0.1%, avoids near-zero noise)
        max_differential: float — differential that maps to |signal|=1.0
            when rank_normalize=False (default 0.05 = 5%)

    Note on cross-sectional ranking:
        rank_normalize=True computes z-scores across all 12 PAIR columns at
        each daily bar, then clips to [-1, +1]. This requires the full 12-pair
        rate_data DataFrame (all columns present). The z-score approach ensures
        long-short balance (positive and negative signals cancel in expectation).
    """

    def __init__(self, params: dict[str, Any], *, rate_data: pd.DataFrame | None = None):
        """
        Args:
            params: Strategy parameters (see class docstring).
            rate_data: If supplied, used directly (for testing). If None,
                       loaded from params['rate_data_path'] on first signal call.
                       Keyword-only per REM-1 / D-1.1 ABC contract.
        """
        super().__init__(params, rate_data=rate_data)
        # self.rate_data is set by ABC __init__; mirror to _rate_data for compat
        self._rate_data = rate_data  # pre-loaded (tests or portfolio runner)
        self._rate_data_loaded = rate_data is not None

    @property
    def name(self) -> str:
        return "carry_fred"

    def required_indicators(self) -> list[str]:
        return ["atr_14"]

    def _get_rate_data(self) -> pd.DataFrame:
        """Lazy-load rate data on first use."""
        if not self._rate_data_loaded:
            path = self.params.get("rate_data_path", _DEFAULT_RATE_DATA_PATH)
            self._rate_data = _load_rate_data(path)
            self._rate_data_loaded = True
        return self._rate_data  # type: ignore[return-value]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate long-short carry signals for this pair.

        Returns a pd.Series aligned to data.index with values in [-1, +1].
        0.0 = no position. Positive = long base, negative = short base.
        """
        pair = str(self.params.get("pair", "")).upper()
        if not pair:
            raise ValueError("CarryFREDStrategy: 'pair' param is required")

        col = _PAIR_TO_COL.get(pair)
        if col is None:
            raise ValueError(
                f"CarryFREDStrategy: unknown pair '{pair}'. "
                f"Supported: {list(_PAIR_TO_COL.keys())}"
            )

        rate_data = self._get_rate_data()

        # REM-1 column-name tolerance: injected rate_data may have been renamed.
        # Accept both naming conventions: prefer _diff suffix; fall back to bare pair name.
        if col not in rate_data.columns:
            bare_col = pair
            if bare_col in rate_data.columns:
                rename_map = {p: f"{p}_diff" for p in _PAIR_TO_COL if p in rate_data.columns}
                rate_data = rate_data.rename(columns=rename_map)
            else:
                raise ValueError(
                    f"CarryFREDStrategy: column '{col}' (or '{bare_col}') "
                    f"not found in rate_data. Available: {list(rate_data.columns)}"
                )

        rank_normalize = bool(self.params.get("rank_normalize", True))
        min_diff = float(self.params.get("min_differential", 0.001))

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
        """Cross-sectional z-score rank signal.

        At each bar, z-score this pair's differential against all 12 pairs.
        This produces a long-short balanced signal bounded to [-1, +1].
        """
        # Use only the 12 pre-registered diff columns that exist in the data
        available_cols = [c for c in _PAIR_TO_COL.values() if c in rate_data.columns]
        cross_section = rate_data[available_cols]

        # Forward-fill to daily frequency aligned to OHLCV dates
        # Handle tz mismatch: normalize both to tz-naive
        ohlcv_index = data.index
        if ohlcv_index.tz is not None:
            ohlcv_index_naive = ohlcv_index.tz_localize(None)
        else:
            ohlcv_index_naive = ohlcv_index

        # Reindex rate_data to daily ohlcv index, forward-fill
        if rate_data.index.tz is not None:
            cs_reindexed = cross_section.copy()
            cs_reindexed.index = cs_reindexed.index.tz_localize(None)
        else:
            cs_reindexed = cross_section

        # Create a combined index for clean ffill
        combined_idx = cs_reindexed.index.union(ohlcv_index_naive).sort_values()
        cs_daily = cs_reindexed.reindex(combined_idx).ffill().reindex(ohlcv_index_naive)

        # Cross-sectional z-score at each bar
        cross_mean = cs_daily.mean(axis=1)
        cross_std = cs_daily.std(axis=1)

        this_pair_diff = cs_daily[col]

        # Z-score: (x - mean) / std; fill where std=0
        z_score = (this_pair_diff - cross_mean) / cross_std.replace(0.0, np.nan)
        z_score = z_score.fillna(0.0)

        # Clip to [-1, +1]: top quintile ≈ z > 0.84, bottom ≈ z < -0.84
        # We clip the full z-score to preserve signal magnitude within ±1
        signals = z_score.clip(-1.0, 1.0)

        # Zero out where abs(raw differential) is below minimum threshold
        # (avoid trading near-zero carry which is noise)
        raw_diff = cs_daily[col]
        signals = signals.where(raw_diff.abs() >= min_diff, 0.0)

        # Re-align index to original ohlcv index (restore tz if needed)
        signals.index = data.index

        return signals.fillna(0.0)

    def _raw_signals(
        self,
        data: pd.DataFrame,
        rate_data: pd.DataFrame,
        col: str,
        min_diff: float,
    ) -> pd.Series:
        """Simplified fallback: signal = sign(rate_differential).

        Used when rank_normalize=False. Documented simplification per pre-reg.
        """
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
