"""Experiment registry — SQLite-backed tracking of all backtest runs.

Every backtest gets a record: git hash, config snapshot, data fingerprint,
all metrics, parameters, and tags. Enables systematic research queries and
provides the trial count for Deflated Sharpe Ratio adjustment.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from forex_system.backtest.metrics import PerformanceMetrics
from forex_system.core.types import BacktestResult, ExperimentRecord


class ExperimentRegistry:
    """SQLite-backed registry of all backtest experiments."""

    def __init__(self, db_path: str | Path = "data/experiments.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                git_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                pair TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                tags_json TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def record(
        self,
        result: BacktestResult,
        metrics: PerformanceMetrics,
        config_snapshot: dict,
        data_hash: str,
        tags: list[str] | None = None,
    ) -> str:
        """Record an experiment. Returns experiment_id (UUID)."""
        experiment_id = str(uuid.uuid4())
        git_hash = _get_git_hash()
        timestamp = pd.Timestamp.now(tz="UTC").isoformat()
        config_hash = _hash_dict(config_snapshot)
        metrics_dict = asdict(metrics)
        params_dict = result.parameters

        self._conn.execute(
            """INSERT INTO experiments
               (experiment_id, git_hash, timestamp, strategy_name, pair,
                config_hash, data_hash, metrics_json, parameters_json, tags_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                experiment_id,
                git_hash,
                timestamp,
                result.strategy_name,
                result.pair,
                config_hash,
                data_hash,
                json.dumps(metrics_dict),
                json.dumps(params_dict),
                json.dumps(tags or []),
            ),
        )
        self._conn.commit()
        return experiment_id

    def query(
        self,
        strategy: str | None = None,
        pair: str | None = None,
        min_sharpe: float | None = None,
        tags: list[str] | None = None,
    ) -> list[ExperimentRecord]:
        """Query experiments by criteria."""
        conditions = []
        params: list = []

        if strategy:
            conditions.append("strategy_name = ?")
            params.append(strategy)
        if pair:
            conditions.append("pair = ?")
            params.append(pair)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(
            f"SELECT * FROM experiments {where} ORDER BY timestamp DESC", params
        ).fetchall()

        records = []
        for row in rows:
            metrics_dict = json.loads(row[7])
            params_dict = json.loads(row[8])
            tags_list = json.loads(row[9])

            # Filter by min_sharpe if specified
            if min_sharpe is not None and metrics_dict.get("sharpe_ratio", 0) < min_sharpe:
                continue

            # Filter by tags if specified (all requested tags must be present)
            if tags and not all(t in tags_list for t in tags):
                continue

            records.append(ExperimentRecord(
                experiment_id=row[0],
                git_hash=row[1],
                timestamp=pd.Timestamp(row[2]),
                strategy_name=row[3],
                pair=row[4],
                config_hash=row[5],
                data_hash=row[6],
                metrics=metrics_dict,
                parameters=params_dict,
                tags=tags_list,
            ))

        return records

    def trial_count(self) -> int:
        """Total experiments recorded — denominator for Deflated Sharpe Ratio."""
        row = self._conn.execute("SELECT COUNT(*) FROM experiments").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


def _get_git_hash() -> str:
    """Get current git commit hash, or 'unknown' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _hash_dict(d: dict) -> str:
    """Deterministic hash of a dict."""
    serialized = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
