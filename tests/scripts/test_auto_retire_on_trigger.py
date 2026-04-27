"""Tests for scripts/auto_retire_on_trigger.py.

Closes R1 Amendment 1 finding A1_C3 -- without these tests the auto-
retirement workflow is just claims in a YAML. The retirement record is
the audit-of-record for "this strategy is retired and no further capital
or research budget will be allocated"; getting that wrong is a
governance failure, not just a code defect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

import auto_retire_on_trigger as ar


@pytest.fixture
def tmp_trials_log(tmp_path, monkeypatch):
    """Redirect TRIALS_LOG to a tmp file so tests don't touch real audit log."""
    log = tmp_path / "trials.jsonl"
    monkeypatch.setattr(ar, "TRIALS_LOG", log)
    return log


class TestWriteRetirementRecord:
    def test_writes_jsonl_with_required_fields(self, tmp_trials_log):
        rec = ar.write_retirement_record(
            strategy="vol_target_carry",
            trigger_id="VTC-T6",
            reason="costs doubled stress",
            evidence_path="data/results/trials/abc.json",
            operator="test_op",
        )
        assert tmp_trials_log.exists()
        line = tmp_trials_log.read_text().strip()
        parsed = json.loads(line)
        # Required audit fields
        for field in ("trial_id", "timestamp", "git_hash", "strategy",
                      "status", "retirement_trigger_id", "retirement_reason",
                      "pre_reg_path", "evidence_path", "operator"):
            assert field in parsed, f"missing field: {field}"
        assert parsed["strategy"] == "vol_target_carry"
        assert parsed["status"] == "retired"
        assert parsed["retirement_trigger_id"] == "VTC-T6"
        assert parsed["pre_reg_path"] == "references/pre-registrations/vol_target_carry.md"
        assert parsed["operator"] == "test_op"

    def test_unknown_strategy_raises(self, tmp_trials_log):
        with pytest.raises(ValueError, match="Unknown strategy"):
            ar.write_retirement_record(
                strategy="not_a_real_strategy",
                trigger_id="X",
                reason="test",
            )


class TestIdempotency:
    """Re-running with the same {strategy, trigger_id} pair must not
    double-write. Otherwise an operator running the script twice for
    the same trigger would inflate the retirement-trigger count and
    confuse downstream Bonferroni accounting."""

    def test_already_retired_returns_true_after_write(self, tmp_trials_log):
        ar.write_retirement_record(
            strategy="vol_target_carry", trigger_id="VTC-T6", reason="r",
        )
        assert ar.already_retired_by_trigger("vol_target_carry", "VTC-T6")

    def test_different_trigger_not_already_retired(self, tmp_trials_log):
        ar.write_retirement_record(
            strategy="vol_target_carry", trigger_id="VTC-T6", reason="r",
        )
        assert not ar.already_retired_by_trigger("vol_target_carry", "VTC-T1")

    def test_different_strategy_not_already_retired(self, tmp_trials_log):
        ar.write_retirement_record(
            strategy="vol_target_carry", trigger_id="VTC-T6", reason="r",
        )
        assert not ar.already_retired_by_trigger("carry_fred", "VTC-T6")

    def test_no_log_means_not_retired(self, tmp_trials_log):
        # tmp_trials_log fixture creates path but file does not exist yet
        assert not ar.already_retired_by_trigger("vol_target_carry", "VTC-T6")


class TestGateOutputParsing:
    def test_cf_t9_triggered_envelope(self, tmp_path):
        gate_path = tmp_path / "cf_t9.json"
        gate_path.write_text(json.dumps({
            "monitor_id": "CF-T9",
            "triggered": True,
            "clause_a_boj_rate": {
                "latest_quarter_end": "2025-09-30",
                "latest_rate_pct": 0.75,
            },
            "clause_b_basket_sharpe": {
                "evidence": {"current": 0.15},
            },
        }))
        triggered, trigger_id, reason = ar.parse_gate_output(gate_path)
        assert triggered is True
        assert trigger_id == "CF-T9"
        assert "0.75" in reason and "0.15" in reason

    def test_cf_t9_not_triggered_returns_false(self, tmp_path):
        gate_path = tmp_path / "cf_t9.json"
        gate_path.write_text(json.dumps({
            "monitor_id": "CF-T9",
            "triggered": False,
        }))
        triggered, trigger_id, reason = ar.parse_gate_output(gate_path)
        assert triggered is False
        assert trigger_id is None

    def test_missing_gate_file_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="not found"):
            ar.parse_gate_output(tmp_path / "no_such_file.json")
