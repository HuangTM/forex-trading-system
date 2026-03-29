"""Parquet storage for validated OHLCV data."""

from pathlib import Path

import pandas as pd

from forex_system.core.errors import DataError


def save_parquet(df: pd.DataFrame, pair: str, timeframe: str, data_dir: str | Path) -> Path:
    """Save validated OHLCV data to Parquet."""
    data_dir = Path(data_dir) / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    path = data_dir / f"{pair.upper()}_{timeframe}.parquet"
    df.to_parquet(path, engine="pyarrow")
    return path


def load_parquet(pair: str, timeframe: str, data_dir: str | Path) -> pd.DataFrame:
    """Load OHLCV data from Parquet store."""
    path = Path(data_dir) / "processed" / f"{pair.upper()}_{timeframe}.parquet"
    if not path.exists():
        raise DataError(f"No data found: {path}")
    return pd.read_parquet(path)


def list_available(data_dir: str | Path) -> list[dict[str, str]]:
    """List all available pair/timeframe combinations in the store."""
    processed = Path(data_dir) / "processed"
    if not processed.exists():
        return []

    available = []
    for f in sorted(processed.glob("*.parquet")):
        parts = f.stem.split("_", 1)
        if len(parts) == 2:
            available.append({"pair": parts[0], "timeframe": parts[1]})
    return available
