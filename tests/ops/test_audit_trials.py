"""Tests for forex_system.ops.audit_trials."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from forex_system.ops.audit_trials import find_orphans, load_registry, main


def _ts(minutes_ago: float) -> str:
    """Return ISO timestamp for a time this many minutes ago."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _write_registry(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


# ---------------------------------------------------------------------------
# Core logic tests (find_orphans)
# ---------------------------------------------------------------------------

class TestFindOrphans:
    def test_empty_registry_returns_no_orphans(self):
        assert find_orphans([], orphan_age_min=60) == []

    def test_spawned_then_complete_returns_no_orphans(self):
        lines = [
            {"trial_id": "abc", "timestamp": _ts(120), "status": "spawned",
             "strategy": "test", "pair": "USDJPY", "config_hash": "aaa"},
            {"trial_id": "abc", "timestamp": _ts(119), "status": "complete",
             "strategy": "test", "pair": "USDJPY", "config_hash": "aaa"},
        ]
        assert find_orphans(lines, orphan_age_min=60) == []

    def test_spawned_then_error_returns_no_orphans(self):
        """An errored trial is not an orphan."""
        lines = [
            {"trial_id": "abc", "timestamp": _ts(120), "status": "spawned",
             "strategy": "test", "pair": "USDJPY", "config_hash": "aaa"},
            {"trial_id": "abc", "timestamp": _ts(118), "status": "error",
             "strategy": "test", "pair": "USDJPY", "config_hash": "aaa"},
        ]
        assert find_orphans(lines, orphan_age_min=60) == []

    def test_spawned_recent_within_grace_returns_no_orphans(self):
        """A spawned-only trial that is recent (< orphan_age_min) is not an orphan."""
        lines = [
            {"trial_id": "abc", "timestamp": _ts(10), "status": "spawned",
             "strategy": "test", "pair": "USDJPY", "config_hash": "aaa"},
        ]
        assert find_orphans(lines, orphan_age_min=60) == []

    def test_spawned_old_no_followup_returns_orphan(self):
        """A spawned-only trial older than orphan_age_min is an orphan."""
        lines = [
            {"trial_id": "xyz", "timestamp": _ts(120), "status": "spawned",
             "strategy": "vol_target_carry", "pair": "USDJPY", "config_hash": "abc123"},
        ]
        orphans = find_orphans(lines, orphan_age_min=60)
        assert len(orphans) == 1
        assert orphans[0]["trial_id"] == "xyz"
        assert orphans[0]["strategy"] == "vol_target_carry"
        assert orphans[0]["pair"] == "USDJPY"
        assert orphans[0]["config_hash"] == "abc123"
        assert orphans[0]["age_minutes"] >= 60

    def test_multiple_trials_mixed_returns_only_orphans(self):
        """Only the spawned-old trial is reported."""
        lines = [
            # Orphan: spawned 2h ago, no follow-up
            {"trial_id": "orphan1", "timestamp": _ts(120), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c1"},
            # Complete: spawned 3h ago, completed 2h 55m ago
            {"trial_id": "done1", "timestamp": _ts(180), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c2"},
            {"trial_id": "done1", "timestamp": _ts(175), "status": "complete",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c2"},
            # Recent spawn: within grace period
            {"trial_id": "new1", "timestamp": _ts(5), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c3"},
            # Error: old but errored
            {"trial_id": "err1", "timestamp": _ts(200), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c4"},
            {"trial_id": "err1", "timestamp": _ts(195), "status": "error",
             "strategy": "s", "pair": "USDJPY", "config_hash": "c4"},
        ]
        orphans = find_orphans(lines, orphan_age_min=60)
        assert len(orphans) == 1
        assert orphans[0]["trial_id"] == "orphan1"

    def test_multiple_orphans_all_reported(self):
        lines = [
            {"trial_id": "o1", "timestamp": _ts(90), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "h1"},
            {"trial_id": "o2", "timestamp": _ts(200), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "h2"},
        ]
        orphans = find_orphans(lines, orphan_age_min=60)
        assert len(orphans) == 2
        trial_ids = {o["trial_id"] for o in orphans}
        assert trial_ids == {"o1", "o2"}

    def test_spawned_exactly_at_threshold_is_not_orphan(self):
        """A trial spawned exactly orphan_age_min - 1 second ago is NOT an orphan."""
        lines = [
            # 59 minutes 50 seconds ago — just under 60 minute threshold
            {"trial_id": "borderline", "timestamp": _ts(59.833), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "h"},
        ]
        orphans = find_orphans(lines, orphan_age_min=60)
        assert orphans == []


# ---------------------------------------------------------------------------
# Registry loading tests
# ---------------------------------------------------------------------------

class TestLoadRegistry:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_registry(str(tmp_path / "does_not_exist.jsonl"))
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "trials.jsonl"
        p.write_text("")
        assert load_registry(str(p)) == []

    def test_blank_lines_skipped(self, tmp_path):
        p = tmp_path / "trials.jsonl"
        p.write_text('\n{"trial_id": "a", "status": "spawned"}\n\n')
        result = load_registry(str(p))
        assert len(result) == 1

    def test_all_lines_parsed(self, tmp_path):
        p = tmp_path / "trials.jsonl"
        _write_registry(p, [
            {"trial_id": "a", "status": "spawned"},
            {"trial_id": "b", "status": "complete"},
        ])
        result = load_registry(str(p))
        assert len(result) == 2


# ---------------------------------------------------------------------------
# CLI tests (main)
# ---------------------------------------------------------------------------

class TestAuditTrialsCLI:
    def test_empty_registry_exits_0(self, tmp_path, capsys):
        p = tmp_path / "trials.jsonl"
        p.write_text("")
        exit_code = main(["--registry", str(p), "--orphan-age-min", "60"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "No orphaned" in out

    def test_no_orphans_exits_0(self, tmp_path, capsys):
        p = tmp_path / "trials.jsonl"
        _write_registry(p, [
            {"trial_id": "done", "timestamp": _ts(120), "status": "spawned",
             "strategy": "s", "pair": "USDJPY", "config_hash": "h"},
            {"trial_id": "done", "timestamp": _ts(119), "status": "complete",
             "strategy": "s", "pair": "USDJPY", "config_hash": "h"},
        ])
        exit_code = main(["--registry", str(p), "--orphan-age-min", "60"])
        assert exit_code == 0

    def test_orphan_present_exits_1(self, tmp_path, capsys):
        p = tmp_path / "trials.jsonl"
        _write_registry(p, [
            {"trial_id": "stuck", "timestamp": _ts(200), "status": "spawned",
             "strategy": "vol_target_carry", "pair": "USDJPY", "config_hash": "abc"},
        ])
        exit_code = main(["--registry", str(p), "--orphan-age-min", "60"])
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "stuck" in out
        assert "vol_target_carry" in out

    def test_missing_registry_exits_0_with_message(self, tmp_path, capsys):
        """Missing registry file is treated as empty (0 orphans)."""
        missing = str(tmp_path / "nope.jsonl")
        exit_code = main(["--registry", missing, "--orphan-age-min", "60"])
        assert exit_code == 0

    def test_real_registry_has_some_orphans(self, tmp_path, capsys):
        """Simulate the actual trials.jsonl format with known orphans."""
        # Based on real .fintech-org/trials.jsonl: trials 3c9e952a and d18063d4 are spawned-only
        p = tmp_path / "trials.jsonl"
        _write_registry(p, [
            # complete pair
            {"trial_id": "43c9b481", "timestamp": _ts(200), "status": "spawned",
             "strategy": "unknown", "pair": "USDJPY", "config_hash": "91fe31efd083"},
            {"trial_id": "43c9b481", "timestamp": _ts(199), "status": "complete",
             "strategy": "vol_target_carry", "pair": "USDJPY", "config_hash": "91fe31efd083"},
            # orphan 1
            {"trial_id": "3c9e952a", "timestamp": _ts(180), "status": "spawned",
             "strategy": "unknown", "pair": "USDJPY", "config_hash": "7b4607069a6b"},
            # orphan 2
            {"trial_id": "d18063d4", "timestamp": _ts(175), "status": "spawned",
             "strategy": "unknown", "pair": "USDJPY", "config_hash": "7b4607069a6b"},
            # complete pair 2
            {"trial_id": "7dde9154", "timestamp": _ts(170), "status": "spawned",
             "strategy": "unknown", "pair": "USDJPY", "config_hash": "48acc248c1db"},
            {"trial_id": "7dde9154", "timestamp": _ts(169), "status": "complete",
             "strategy": "vol_target_carry", "pair": "USDJPY", "config_hash": "48acc248c1db"},
        ])
        exit_code = main(["--registry", str(p), "--orphan-age-min", "60"])
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "3c9e952a" in out
        assert "d18063d4" in out
        assert "43c9b481" not in out
        assert "7dde9154" not in out
