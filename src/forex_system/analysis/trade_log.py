"""Structured trade log — append-only record of every execution.

Records every order placed, fill received, and position change with
full context. Stored as Parquet for efficient analysis.

Used for:
- Paper-vs-backtest comparison (the "reality tax")
- Execution quality analysis (slippage, spread at fill)
- Audit trail for all trading decisions
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

from forex_system.core.types import ExecutionResult


class TradeLog:
    """Append-only trade execution log."""

    def __init__(self, output_dir: str | Path = "data/trades"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []

    def record(
        self,
        result: ExecutionResult,
        signal: float,
        strategy: str,
        source: str = "paper",
        context: dict | None = None,
    ) -> None:
        """Record an execution result."""
        entry = {
            "timestamp": result.fill_time,
            "pair": result.pair,
            "direction": result.direction.name,
            "size": result.size,
            "requested_price": result.requested_price,
            "fill_price": result.fill_price,
            "slippage_pips": result.slippage_pips,
            "spread_at_fill": result.spread_at_fill,
            "success": result.success,
            "error": result.error,
            "signal": signal,
            "strategy": strategy,
            "source": source,
        }
        if context:
            for k, v in context.items():
                entry[f"ctx_{k}"] = v

        self._buffer.append(entry)

        if len(self._buffer) >= 100:
            self.flush()

    def flush(self) -> None:
        """Write buffered trades to Parquet (atomic via temp file + rename)."""
        if not self._buffer:
            return

        df = pd.DataFrame(self._buffer)
        self._buffer = []

        path = self.output_dir / "executions.parquet"
        if path.exists():
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df], ignore_index=True)

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(dir=self.output_dir, suffix=".parquet")
        os.close(fd)
        try:
            df.to_parquet(tmp_path, index=False)
            os.replace(tmp_path, path)
        except BaseException:
            os.unlink(tmp_path)
            raise

    def load(
        self,
        pair: str | None = None,
        source: str | None = None,
        strategy: str | None = None,
    ) -> pd.DataFrame:
        """Load trade log, optionally filtered."""
        path = self.output_dir / "executions.parquet"
        if not path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(path)
        if pair:
            df = df[df["pair"] == pair]
        if source:
            df = df[df["source"] == source]
        if strategy:
            df = df[df["strategy"] == strategy]
        return df

    def execution_quality_report(self) -> str:
        """Generate a summary of execution quality metrics."""
        df = self.load()
        if df.empty:
            return "No trades recorded."

        lines = [
            "=== Execution Quality Report ===",
            f"Total executions: {len(df)}",
            f"Success rate: {df['success'].mean():.1%}",
            f"Avg spread at fill: {df['spread_at_fill'].mean():.2f} pips",
            f"Avg slippage: {df['slippage_pips'].mean():.2f} pips",
            "",
            "By pair:",
        ]
        for pair, group in df.groupby("pair"):
            lines.append(
                f"  {pair}: {len(group)} fills, "
                f"avg spread={group['spread_at_fill'].mean():.2f}, "
                f"avg slippage={group['slippage_pips'].mean():.2f}"
            )
        return "\n".join(lines)

    def close(self) -> None:
        self.flush()
