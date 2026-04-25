"""Parquet storage for validated OHLCV data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from forex_system.core.errors import DataError, LookaheadError

_OOS_BURNS_LOG = Path(".fintech-org/oos-burns.jsonl")


def save_parquet(df: pd.DataFrame, pair: str, timeframe: str, data_dir: str | Path) -> Path:
    """Save validated OHLCV data to Parquet."""
    data_dir = Path(data_dir) / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    path = data_dir / f"{pair.upper()}_{timeframe}.parquet"
    df.to_parquet(path, engine="pyarrow")
    return path


def load_parquet(
    pair: str,
    timeframe: str,
    data_dir: str | Path,
    holdout_after: str | None = None,
    oos_mode: bool = False,
) -> pd.DataFrame:
    """Load OHLCV data from Parquet store.

    Args:
        pair: Currency pair symbol (e.g. "USDJPY").
        timeframe: Data timeframe (e.g. "daily", "4h").
        data_dir: Base data directory.
        holdout_after: ISO date string (e.g. "2024-01-01"). If set, data on or
            after this date is the OOS holdout. Access is allowed only when
            oos_mode=True (a one-shot final test mode). Raises LookaheadError
            if any caller tries to read holdout data without oos_mode=True.
        oos_mode: If True, access to holdout data is permitted. The first access
            is recorded in .fintech-org/oos-burns.jsonl. Once a holdout is burned
            for a pair/timeframe, callers should not re-access it in the same
            analysis session.

    Returns:
        DataFrame. In non-oos_mode, returns only pre-holdout rows.
        In oos_mode, returns full data and records the burn.

    Raises:
        DataError: if the parquet file is not found.
        LookaheadError: if holdout data is requested without oos_mode.
    """
    path = Path(data_dir) / "processed" / f"{pair.upper()}_{timeframe}.parquet"
    if not path.exists():
        raise DataError(f"No data found: {path}")

    df = pd.read_parquet(path)

    if holdout_after is None:
        return df

    # Parse holdout boundary
    holdout_ts = pd.Timestamp(holdout_after)

    # Check if any data falls on or after the holdout date
    if df.index.tz is not None:
        holdout_ts = holdout_ts.tz_localize(df.index.tz)
    has_holdout_data = (df.index >= holdout_ts).any()

    if not has_holdout_data:
        # All data is pre-holdout; no issue
        return df

    if not oos_mode:
        # Block access to holdout data — caller must use oos_mode=True
        raise LookaheadError(
            f"Data for {pair} {timeframe} contains dates on or after holdout_after={holdout_after!r}. "
            f"Access to the OOS holdout is blocked in standard mode. "
            f"Use oos_mode=True (harness --final-oos-test) to access holdout data. "
            f"Holdout access is a one-shot burn recorded in {_OOS_BURNS_LOG}."
        )

    # OOS mode: allowed, but record the burn
    _record_oos_burn(pair=pair, timeframe=timeframe, holdout_after=holdout_after)
    return df


def _record_oos_burn(pair: str, timeframe: str, holdout_after: str) -> None:
    """Write an oos-burn entry to .fintech-org/oos-burns.jsonl."""
    _OOS_BURNS_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "event": "oos.burn",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pair": pair.upper(),
        "timeframe": timeframe,
        "holdout_after": holdout_after,
    }
    with open(_OOS_BURNS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


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
