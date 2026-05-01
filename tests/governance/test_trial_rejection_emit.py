"""Governance tests: trial rejection emit path.

Verifies that record_trial_rejection() correctly appends a status='rejected'
entry to trials.jsonl with the two new fields required by CTO CONDITION-1
(CONSENSUS_2026-04-28.md): rejection_reason and falsification_criterion.

These tests use a TEMP file (tmp_path fixture) — production
.fintech-org/trials.jsonl is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

from forex_system.harness.run_trial import record_trial_rejection


class TestTrialRejectionEmit:
    """record_trial_rejection writes correct schema to a temp registry."""

    def test_appends_rejected_entry(self, tmp_path: Path) -> None:
        """Calling record_trial_rejection appends exactly one line."""
        registry = tmp_path / "trials.jsonl"
        record_trial_rejection(
            trial_id="test-abc123",
            strategy="vol_target_carry",
            rejection_reason="OOS Sharpe 0.12 < VTC-T1 threshold 0.30",
            falsification_criterion="VTC-T1",
            registry=registry,
        )
        lines = registry.read_text().strip().splitlines()
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"

    def test_status_is_rejected(self, tmp_path: Path) -> None:
        """The appended entry has status == 'rejected'."""
        registry = tmp_path / "trials.jsonl"
        record_trial_rejection(
            trial_id="test-abc124",
            strategy="vol_target_carry",
            rejection_reason="OOS Sharpe 0.05 < VTC-T1 threshold 0.30",
            falsification_criterion="VTC-T1",
            registry=registry,
        )
        entry = json.loads(registry.read_text().strip())
        assert entry["status"] == "rejected"

    def test_rejection_reason_field_present(self, tmp_path: Path) -> None:
        """Entry contains rejection_reason field with the supplied value."""
        registry = tmp_path / "trials.jsonl"
        reason = "OOS Sharpe 0.08 < FRED-T2 threshold 0.30"
        record_trial_rejection(
            trial_id="test-abc125",
            strategy="carry_fred",
            rejection_reason=reason,
            falsification_criterion="FRED-T2",
            registry=registry,
        )
        entry = json.loads(registry.read_text().strip())
        assert "rejection_reason" in entry, "rejection_reason field missing"
        assert entry["rejection_reason"] == reason

    def test_falsification_criterion_field_present(self, tmp_path: Path) -> None:
        """Entry contains falsification_criterion field with the supplied value."""
        registry = tmp_path / "trials.jsonl"
        criterion = "VTC-T3"
        record_trial_rejection(
            trial_id="test-abc126",
            strategy="vol_target_carry",
            rejection_reason="Max drawdown 35% > VTC-T3 limit 25%",
            falsification_criterion=criterion,
            registry=registry,
        )
        entry = json.loads(registry.read_text().strip())
        assert "falsification_criterion" in entry, "falsification_criterion field missing"
        assert entry["falsification_criterion"] == criterion

    def test_filter_rejected_entries(self, tmp_path: Path) -> None:
        """Filtering status=='rejected' works — satisfies CONDITION-1 >=10 check."""
        registry = tmp_path / "trials.jsonl"

        # Seed the file with mixed-status entries
        other_entries = [
            {"trial_id": "t001", "status": "spawned", "strategy": "vol_target_carry"},
            {"trial_id": "t002", "status": "complete", "strategy": "vol_target_carry",
             "sharpe": 0.85},
        ]
        with open(registry, "w") as f:
            for e in other_entries:
                f.write(json.dumps(e) + "\n")

        # Emit 3 rejection entries
        for i in range(3):
            record_trial_rejection(
                trial_id=f"reject-{i:04d}",
                strategy="vol_target_carry",
                rejection_reason=f"OOS Sharpe {0.05 + i * 0.01:.2f} < VTC-T1 threshold 0.30",
                falsification_criterion="VTC-T1",
                registry=registry,
            )

        # Read back and filter
        all_entries = [
            json.loads(line)
            for line in registry.read_text().strip().splitlines()
            if line.strip()
        ]
        rejected = [e for e in all_entries if e.get("status") == "rejected"]

        assert len(rejected) == 3, f"Expected 3 rejected entries, got {len(rejected)}"
        assert all(
            "rejection_reason" in e and "falsification_criterion" in e
            for e in rejected
        ), "Some rejected entries missing required fields"

    def test_return_value_matches_appended_entry(self, tmp_path: Path) -> None:
        """record_trial_rejection returns the dict that was written."""
        registry = tmp_path / "trials.jsonl"
        result = record_trial_rejection(
            trial_id="test-abc127",
            strategy="vol_target_carry",
            rejection_reason="OOS Sharpe 0.10 < VTC-T1 threshold 0.30",
            falsification_criterion="VTC-T1",
            registry=registry,
        )
        written = json.loads(registry.read_text().strip())
        assert result["trial_id"] == written["trial_id"]
        assert result["status"] == "rejected"
        assert result["rejection_reason"] == written["rejection_reason"]
        assert result["falsification_criterion"] == written["falsification_criterion"]

    def test_does_not_touch_production_registry(self, tmp_path: Path) -> None:
        """Supplying a temp registry path never writes to .fintech-org/trials.jsonl."""
        production_registry = Path(".fintech-org/trials.jsonl")
        if production_registry.exists():
            before = production_registry.stat().st_size
        else:
            before = None

        registry = tmp_path / "trials.jsonl"
        record_trial_rejection(
            trial_id="test-isolation",
            strategy="vol_target_carry",
            rejection_reason="isolation test",
            falsification_criterion="VTC-T1",
            registry=registry,
        )

        if before is not None:
            after = production_registry.stat().st_size
            assert after == before, "Production trials.jsonl was modified!"
        else:
            assert not production_registry.exists(), "Production trials.jsonl was created!"
