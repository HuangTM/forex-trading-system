"""Tests for OOS holdout enforcement in storage.load_parquet.

Covers:
- No holdout_after: passes through all data normally
- holdout_after set, data all pre-holdout: no error, returns full data
- holdout_after set, data crosses holdout boundary, oos_mode=False: LookaheadError
- holdout_after set, data crosses holdout boundary, oos_mode=True: returns full data + burns log
- Burn log written on oos_mode access
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from forex_system.core.errors import LookaheadError
from forex_system.data.storage import load_parquet, save_parquet


@pytest.fixture
def sample_parquet(tmp_path):
    """Write a sample parquet file spanning 2020-01-01 to 2025-12-31."""
    dates = pd.date_range("2020-01-01", "2025-12-31", freq="B")
    df = pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1_000_000,
        },
        index=dates,
    )
    save_parquet(df, "TESTUSD", "daily", tmp_path)
    return tmp_path


@pytest.fixture
def tmp_burns_log(tmp_path, monkeypatch):
    """Override OOS burns log path to tmp directory."""
    import forex_system.data.storage as storage_mod
    burns_path = tmp_path / ".fintech-org" / "oos-burns.jsonl"
    monkeypatch.setattr(storage_mod, "_OOS_BURNS_LOG", burns_path)
    return burns_path


class TestNoHoldout:
    def test_no_holdout_returns_all_data(self, sample_parquet):
        """Without holdout_after, all data is returned."""
        df = load_parquet("TESTUSD", "daily", sample_parquet)
        assert len(df) > 0
        # No error, no filtering
        full_df = load_parquet("TESTUSD", "daily", sample_parquet, holdout_after=None)
        assert len(df) == len(full_df)


class TestHoldoutEnforcement:
    def test_pre_holdout_data_no_error(self, sample_parquet, tmp_burns_log):
        """If all data is before holdout_after, no error and no filtering."""
        df = load_parquet(
            "TESTUSD", "daily", sample_parquet,
            holdout_after="2030-01-01",  # Future — all data is pre-holdout
        )
        assert len(df) > 0

    def test_holdout_blocks_in_standard_mode(self, sample_parquet, tmp_burns_log):
        """Data spanning the holdout date raises LookaheadError in standard mode."""
        with pytest.raises(LookaheadError, match="OOS holdout"):
            load_parquet(
                "TESTUSD", "daily", sample_parquet,
                holdout_after="2024-01-01",  # Data extends past this date
                oos_mode=False,
            )

    def test_oos_mode_allows_holdout_access(self, sample_parquet, tmp_burns_log):
        """oos_mode=True allows access to holdout data."""
        df = load_parquet(
            "TESTUSD", "daily", sample_parquet,
            holdout_after="2024-01-01",
            oos_mode=True,
        )
        assert len(df) > 0
        # Returned data should include post-holdout rows
        holdout_ts = pd.Timestamp("2024-01-01")
        assert (df.index >= holdout_ts).any()

    def test_oos_mode_writes_burn_log(self, sample_parquet, tmp_burns_log):
        """oos_mode=True access writes an entry to oos-burns.jsonl."""
        load_parquet(
            "TESTUSD", "daily", sample_parquet,
            holdout_after="2024-01-01",
            oos_mode=True,
        )
        assert tmp_burns_log.exists(), "Burns log should be created on OOS access"
        entries = [json.loads(l) for l in tmp_burns_log.read_text().strip().split("\n")]
        assert len(entries) >= 1
        burn = entries[-1]
        assert burn["event"] == "oos.burn"
        assert burn["pair"] == "TESTUSD"
        assert burn["holdout_after"] == "2024-01-01"

    def test_standard_mode_no_burn_log(self, sample_parquet, tmp_burns_log):
        """Standard mode (blocked) must not write a burn log."""
        try:
            load_parquet(
                "TESTUSD", "daily", sample_parquet,
                holdout_after="2024-01-01",
                oos_mode=False,
            )
        except LookaheadError:
            pass  # Expected

        # Burn log should NOT have been written
        assert not tmp_burns_log.exists(), "No burn should be logged on blocked access"

    def test_error_message_names_holdout_date(self, sample_parquet, tmp_burns_log):
        """LookaheadError message must include the holdout date."""
        with pytest.raises(LookaheadError, match="2024-01-01"):
            load_parquet(
                "TESTUSD", "daily", sample_parquet,
                holdout_after="2024-01-01",
            )

    def test_multiple_oos_accesses_accumulate_burns(self, sample_parquet, tmp_burns_log):
        """Each oos_mode access appends a new burn entry."""
        for _ in range(3):
            load_parquet(
                "TESTUSD", "daily", sample_parquet,
                holdout_after="2024-01-01",
                oos_mode=True,
            )
        entries = [json.loads(l) for l in tmp_burns_log.read_text().strip().split("\n")]
        assert len(entries) == 3


class TestBackwardCompatibility:
    """Existing callers without holdout_after must not be affected."""

    def test_existing_callers_unaffected(self, sample_parquet):
        """Callers that don't pass holdout_after get unchanged behavior."""
        df1 = load_parquet("TESTUSD", "daily", sample_parquet)
        df2 = load_parquet("TESTUSD", "daily", sample_parquet, holdout_after=None)
        assert len(df1) == len(df2)

    def test_missing_parquet_still_raises_data_error(self, tmp_path):
        """Non-existent file still raises DataError (not LookaheadError)."""
        from forex_system.core.errors import DataError
        with pytest.raises(DataError):
            load_parquet("NONEXISTENT", "daily", tmp_path, holdout_after="2024-01-01")
