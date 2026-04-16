"""Prediction log — append-only record of every signal/prediction.

Every call to generate_signals() or generate_predictions() produces a log
entry with full context. Stored as Parquet, partitioned by month.

This log becomes:
- Trial registry (each unique params_hash is a trial)
- Future meta-labeling training data (label each prediction with outcome)
- DSR denominator (count unique strategy-param combos)
- Backtest-vs-live comparison dataset (compare signals from both systems)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


class PredictionLog:
    """Append-only log of every signal/prediction."""

    def __init__(self, output_dir: str | Path = "data/predictions"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[pd.DataFrame] = []
        self._buffer_rows = 0

    def log(
        self,
        signals: pd.Series,
        strategy_name: str,
        pair: str,
        parameters: dict | None = None,
        source: str = "backtest",
        predictions: pd.DataFrame | None = None,
    ) -> None:
        """Log a batch of signals/predictions.

        Args:
            signals: Signal series indexed by timestamp.
            strategy_name: Strategy that produced the signals.
            pair: Currency pair.
            parameters: Strategy parameters (hashed for grouping).
            source: "backtest", "paper", or "live".
            predictions: Optional richer DataFrame with confidence, model_id, etc.
        """
        params_hash = _hash_params(parameters or {})

        records = pd.DataFrame({
            "timestamp": signals.index,
            "pair": pair,
            "strategy": strategy_name,
            "signal": signals.values,
            "params_hash": params_hash,
            "source": source,
        })

        # Add prediction columns if available
        if predictions is not None:
            for col in predictions.columns:
                if col != "signal" and col in predictions.columns:
                    aligned = predictions[col].reindex(signals.index)
                    records[col] = aligned.values

        self._buffer.append(records)
        self._buffer_rows += len(records)

        # Auto-flush at 10K rows
        if self._buffer_rows >= 10_000:
            self.flush()

    def flush(self) -> None:
        """Write buffered predictions to Parquet files, partitioned by month."""
        if not self._buffer:
            return

        all_records = pd.concat(self._buffer, ignore_index=True)
        self._buffer = []
        self._buffer_rows = 0

        # Partition by year-month
        all_records["_month"] = pd.to_datetime(all_records["timestamp"]).dt.to_period("M")

        for month, group in all_records.groupby("_month"):
            month_str = str(month)  # e.g., "2024-01"
            path = self.output_dir / f"{month_str}.parquet"

            group = group.drop(columns=["_month"])

            if path.exists():
                existing = pd.read_parquet(path)
                combined = pd.concat([existing, group], ignore_index=True)
                combined.to_parquet(path, index=False)
            else:
                group.to_parquet(path, index=False)

    def load(
        self,
        start: str | None = None,
        end: str | None = None,
        strategy: str | None = None,
        pair: str | None = None,
        source: str | None = None,
    ) -> pd.DataFrame:
        """Load predictions from the log, optionally filtered.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).
            strategy: Filter by strategy name.
            pair: Filter by pair.
            source: Filter by source ("backtest", "paper", "live").

        Returns:
            DataFrame with all matching prediction records.
        """
        files = sorted(self.output_dir.glob("*.parquet"))
        if not files:
            return pd.DataFrame()

        parts = []
        for f in files:
            # Quick month-level filter from filename
            month_str = f.stem  # e.g., "2024-01"
            if start and month_str < start[:7]:
                continue
            if end and month_str > end[:7]:
                continue

            df = pd.read_parquet(f)
            parts.append(df)

        if not parts:
            return pd.DataFrame()

        result = pd.concat(parts, ignore_index=True)
        result["timestamp"] = pd.to_datetime(result["timestamp"])

        # Apply filters
        if start:
            result = result[result["timestamp"] >= pd.Timestamp(start)]
        if end:
            result = result[result["timestamp"] <= pd.Timestamp(end)]
        if strategy:
            result = result[result["strategy"] == strategy]
        if pair:
            result = result[result["pair"] == pair]
        if source:
            result = result[result["source"] == source]

        return result.sort_values("timestamp").reset_index(drop=True)

    def compare_sources(
        self,
        strategy: str,
        pair: str,
        source_a: str = "backtest",
        source_b: str = "paper",
    ) -> pd.DataFrame:
        """Compare signals between two sources (e.g., backtest vs paper).

        Returns DataFrame with columns: timestamp, signal_a, signal_b, diff.
        This is the "reality tax" measurement.
        """
        a = self.load(strategy=strategy, pair=pair, source=source_a)
        b = self.load(strategy=strategy, pair=pair, source=source_b)

        if a.empty or b.empty:
            return pd.DataFrame()

        a = a.set_index("timestamp")[["signal"]].rename(columns={"signal": f"signal_{source_a}"})
        b = b.set_index("timestamp")[["signal"]].rename(columns={"signal": f"signal_{source_b}"})

        merged = a.join(b, how="inner")
        merged["diff"] = merged.iloc[:, 0] - merged.iloc[:, 1]
        merged["agree"] = (merged.iloc[:, 0] * merged.iloc[:, 1]) > 0

        return merged

    def unique_trials(self) -> int:
        """Count unique (strategy, params_hash) combos — DSR denominator."""
        all_data = self.load()
        if all_data.empty:
            return 0
        return len(all_data.groupby(["strategy", "params_hash"]).size())

    def close(self) -> None:
        """Flush any remaining buffered data."""
        self.flush()


def _hash_params(params: dict) -> str:
    """Deterministic hash of strategy parameters."""
    serialized = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:12]
