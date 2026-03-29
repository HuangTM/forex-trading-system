"""Data transformation — resampling, alignment, normalization."""

import pandas as pd

from forex_system.core.errors import DataError

# Mapping from user-friendly names to pandas offset aliases
TIMEFRAME_MAP = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "1H": "1h",
    "4H": "4h",
    "daily": "1D",
    "weekly": "1W",
    "monthly": "1ME",
}


def resample_ohlcv(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """Resample OHLCV data to a coarser timeframe.

    Uses standard aggregation: open=first, high=max, low=min, close=last, volume=sum.
    """
    freq = TIMEFRAME_MAP.get(target_timeframe)
    if freq is None:
        raise DataError(
            f"Unknown timeframe: {target_timeframe}. "
            f"Supported: {list(TIMEFRAME_MAP.keys())}"
        )

    resampled = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })

    # Drop bars where all OHLC are NaN (no data in that period)
    resampled = resampled.dropna(subset=["open", "high", "low", "close"], how="all")

    return resampled


def forward_fill_gaps(df: pd.DataFrame, max_gap: int = 3) -> pd.DataFrame:
    """Forward-fill small gaps in OHLCV data.

    Only fills gaps up to max_gap consecutive bars.
    Larger gaps are left as-is (they indicate genuine data absence).
    """
    filled = df.copy()

    # Identify gap runs
    is_nan = filled["close"].isna()
    gap_groups = is_nan.ne(is_nan.shift()).cumsum()
    gap_sizes = is_nan.groupby(gap_groups).transform("sum")

    # Only fill gaps <= max_gap
    fill_mask = is_nan & (gap_sizes <= max_gap)

    if fill_mask.any():
        # Only forward-fill rows that belong to small gaps
        for col in filled.columns:
            filled.loc[fill_mask, col] = filled[col].ffill()[fill_mask]

    return filled
