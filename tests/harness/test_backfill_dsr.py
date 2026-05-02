"""Tests for scripts/backfill_dsr_existing_trials.py.

Fixture: 3 trials.jsonl entries:
  1. status="rejected" — must not be touched
  2. status="complete", dsr=null, sharpe=0.76 — must be backfilled
  3. status="complete", dsr=0.99 (already set) — must not be touched
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import the backfill function directly (not via subprocess) for fast, reliable testing.
import sys
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from backfill_dsr_existing_trials import backfill  # noqa: E402


@pytest.fixture()
def fixture_registry(tmp_path: Path) -> Path:
    """Create a trials.jsonl fixture with 3 entries."""
    entries = [
        {
            "trial_id": "rejected-001",
            "timestamp": "2026-04-28T00:00:00+00:00",
            "git_hash": "aabbccdd",
            "strategy": "test_strategy",
            "pair": "USDJPY",
            "config_hash": "abc123",
            "pre_reg_path": "references/pre-registrations/test.md",
            "sharpe": 0.10,
            "max_dd": 0.30,
            "n_trades": 10,
            "dsr": None,
            "n_trials_at_spawn": 5,
            "oos": True,
            "status": "rejected",
        },
        {
            "trial_id": "complete-null-dsr",
            "timestamp": "2026-04-28T00:01:00+00:00",
            "git_hash": "aabbccdd",
            "strategy": "test_strategy",
            "pair": "USDJPY",
            "config_hash": "abc456",
            "pre_reg_path": "references/pre-registrations/test.md",
            "sharpe": 0.76,
            "max_dd": 0.17,
            "n_trades": 23,
            "dsr": None,
            "n_trials_at_spawn": 13,
            "oos": True,
            "status": "complete",
            "report_path": "data/results/trials/complete-null-dsr.json",
        },
        {
            "trial_id": "complete-existing-dsr",
            "timestamp": "2026-04-28T00:02:00+00:00",
            "git_hash": "aabbccdd",
            "strategy": "test_strategy",
            "pair": "USDJPY",
            "config_hash": "abc789",
            "pre_reg_path": "references/pre-registrations/test.md",
            "sharpe": 0.80,
            "max_dd": 0.15,
            "n_trades": 30,
            "dsr": 0.99,
            "n_trials_at_spawn": 14,
            "oos": True,
            "status": "complete",
            "report_path": "data/results/trials/complete-existing-dsr.json",
        },
    ]
    registry = tmp_path / "trials.jsonl"
    registry.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return registry


class TestBackfillDSR:
    """Backfill script correctly updates only the right entry."""

    def test_only_complete_null_dsr_updated(self, fixture_registry: Path):
        """Only the complete-with-null-dsr entry should be backfilled."""
        n_updated = backfill(registry=fixture_registry, dry_run=False)
        assert n_updated == 1, f"Expected 1 line updated, got {n_updated}"

    def test_rejected_entry_untouched(self, fixture_registry: Path):
        """Entry with status='rejected' must not be modified."""
        backfill(registry=fixture_registry, dry_run=False)
        lines = fixture_registry.read_text().splitlines()
        rejected = next(json.loads(ln) for ln in lines if "rejected-001" in ln)
        assert rejected["dsr"] is None, "Rejected entry should remain with dsr=null"
        assert rejected["status"] == "rejected"

    def test_complete_null_dsr_populated(self, fixture_registry: Path):
        """Entry with status='complete' and dsr=null should have dsr set to a float."""
        backfill(registry=fixture_registry, dry_run=False)
        lines = fixture_registry.read_text().splitlines()
        entry = next(json.loads(ln) for ln in lines if "complete-null-dsr" in ln)
        assert entry["dsr"] is not None, "complete-null-dsr entry should have dsr set"
        assert isinstance(entry["dsr"], float), f"dsr should be float, got {type(entry['dsr'])}"
        assert 0.0 <= entry["dsr"] <= 1.0, f"dsr must be in [0,1], got {entry['dsr']}"

    def test_complete_existing_dsr_untouched(self, fixture_registry: Path):
        """Entry with dsr already set must not be overwritten."""
        backfill(registry=fixture_registry, dry_run=False)
        lines = fixture_registry.read_text().splitlines()
        entry = next(json.loads(ln) for ln in lines if "complete-existing-dsr" in ln)
        assert entry["dsr"] == pytest.approx(0.99), (
            f"Existing dsr should not be overwritten, got {entry['dsr']}"
        )

    def test_dry_run_does_not_write(self, fixture_registry: Path):
        """--dry-run must not modify the file."""
        original = fixture_registry.read_text()
        n_updated = backfill(registry=fixture_registry, dry_run=True)
        assert fixture_registry.read_text() == original, "Dry run must not modify file"
        assert n_updated == 1, "Dry run should still report 1 line would be updated"

    def test_idempotent(self, fixture_registry: Path):
        """Running twice produces same result as running once."""
        backfill(registry=fixture_registry, dry_run=False)
        first_state = fixture_registry.read_text()

        backfill(registry=fixture_registry, dry_run=False)
        second_state = fixture_registry.read_text()

        assert first_state == second_state, "Backfill is not idempotent"

    def test_schema_preserved(self, fixture_registry: Path):
        """Backfill must not drop any other field from the updated entry."""
        original_lines = fixture_registry.read_text().splitlines()
        original_entry = next(
            json.loads(ln) for ln in original_lines if "complete-null-dsr" in ln
        )
        original_keys = set(original_entry.keys())

        backfill(registry=fixture_registry, dry_run=False)

        updated_lines = fixture_registry.read_text().splitlines()
        updated_entry = next(
            json.loads(ln) for ln in updated_lines if "complete-null-dsr" in ln
        )
        updated_keys = set(updated_entry.keys())

        assert original_keys == updated_keys, (
            f"Field schema changed: missing={original_keys - updated_keys}, "
            f"added={updated_keys - original_keys}"
        )

    def test_uses_n_trials_at_spawn(self, fixture_registry: Path):
        """DSR computation must use n_trials_at_spawn from the record (N=13 here)."""
        from forex_system.harness.deflated_sharpe import deflated_sharpe

        backfill(registry=fixture_registry, dry_run=False)
        lines = fixture_registry.read_text().splitlines()
        entry = next(json.loads(ln) for ln in lines if "complete-null-dsr" in ln)

        # n_trades=23 used as n_obs proxy, n_trials_at_spawn=13
        expected_dsr = deflated_sharpe(
            sharpe=0.76, n_trials=13, n_obs=23, skew=0.0, excess_kurtosis=0.0
        )
        assert entry["dsr"] == pytest.approx(expected_dsr, abs=1e-8), (
            f"DSR value mismatch: got {entry['dsr']}, expected {expected_dsr}"
        )
