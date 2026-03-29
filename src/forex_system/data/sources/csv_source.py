"""CSV data source for HistData.com and Dukascopy formats."""

from pathlib import Path

import pandas as pd

from forex_system.core.errors import DataError
from forex_system.core.interfaces import DataSource


class CSVSource(DataSource):
    """Load OHLCV data from CSV files.

    Supports:
    - HistData format: DateTime, Open, High, Low, Close, Volume
    - Generic format: date/datetime column + OHLCV columns
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def fetch(
        self, pair: str, start: str, end: str, timeframe: str = "daily"
    ) -> pd.DataFrame:
        csv_path = self._find_csv(pair, timeframe)
        if csv_path is None:
            raise DataError(f"No CSV found for {pair} ({timeframe}) in {self.data_dir}")

        df = self._load_csv(csv_path)
        df = df.loc[start:end]

        if df.empty:
            raise DataError(f"No data for {pair} between {start} and {end}")

        return df

    def _find_csv(self, pair: str, timeframe: str) -> Path | None:
        """Search for CSV matching pair and timeframe."""
        pair_upper = pair.upper().replace("/", "")
        pair_lower = pair_upper.lower()

        patterns = [
            f"{pair_upper}*.csv",
            f"{pair_lower}*.csv",
            f"{pair_upper}_{timeframe}*.csv",
        ]

        for pattern in patterns:
            matches = list(self.data_dir.glob(pattern))
            if matches:
                return sorted(matches)[-1]  # Most recent if multiple

        return None

    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Load CSV and normalize to standard OHLCV format."""
        df = pd.read_csv(path)

        # Normalize column names to lowercase
        df.columns = [c.strip().lower() for c in df.columns]

        # Find and parse datetime column
        date_col = None
        for candidate in ["datetime", "date", "time", "timestamp"]:
            if candidate in df.columns:
                date_col = candidate
                break

        if date_col is None:
            # Try first column as datetime
            date_col = df.columns[0]

        df[date_col] = pd.to_datetime(df[date_col], utc=True)
        df = df.set_index(date_col)
        df.index.name = "datetime"

        # Ensure standard OHLCV columns exist
        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise DataError(f"CSV missing columns: {missing} in {path}")

        if "volume" not in df.columns:
            df["volume"] = 0.0

        # Select and order standard columns
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        df = df.sort_index()

        return df
