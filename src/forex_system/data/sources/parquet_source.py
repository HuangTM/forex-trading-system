"""Parquet data source — primary source after initial ingestion."""

from pathlib import Path

import pandas as pd

from forex_system.core.errors import DataError
from forex_system.core.interfaces import DataSource


class ParquetSource(DataSource):
    """Load OHLCV data from local Parquet store."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def fetch(
        self, pair: str, start: str, end: str, timeframe: str = "daily"
    ) -> pd.DataFrame:
        path = self.data_dir / f"{pair.upper()}_{timeframe}.parquet"

        if not path.exists():
            raise DataError(f"Parquet file not found: {path}")

        df = pd.read_parquet(path)

        if not isinstance(df.index, pd.DatetimeIndex):
            raise DataError(f"Parquet index is not DatetimeIndex: {path}")

        df = df.loc[start:end]

        if df.empty:
            raise DataError(f"No data for {pair} between {start} and {end}")

        return df[["open", "high", "low", "close", "volume"]]
