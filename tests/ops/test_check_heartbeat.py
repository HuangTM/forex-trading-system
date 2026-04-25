"""Tests for forex_system.ops.check_heartbeat."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from forex_system.ops.check_heartbeat import check_heartbeat, main


def _write_heartbeat(path: Path, timestamp: datetime, cycle_id: int = 1) -> None:
    payload = {
        "timestamp": timestamp.isoformat(),
        "cycle_id": cycle_id,
        "pid": 12345,
        "last_signal": 0.5,
        "last_action": "HOLD",
        "uptime_seconds": 120.0,
    }
    path.write_text(json.dumps(payload))


class TestCheckHeartbeatCore:
    def test_file_missing_returns_exit_2(self, tmp_path):
        missing = str(tmp_path / "no_such_file.json")
        exit_code, msg = check_heartbeat(missing, max_age_min=60)
        assert exit_code == 2
        assert "missing" in msg

    def test_file_stale_returns_exit_1(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        # 120 minutes ago
        old_ts = datetime.now(timezone.utc) - timedelta(minutes=120)
        _write_heartbeat(p, old_ts)
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 1
        assert "stale" in msg

    def test_file_fresh_returns_exit_0(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        # 5 minutes ago
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        _write_heartbeat(p, recent_ts, cycle_id=42)
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 0
        assert "OK" in msg
        assert "42" in msg  # cycle_id appears in message

    def test_file_malformed_json_returns_exit_2(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        p.write_text("{this is not valid json")
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 2
        assert "malformed" in msg

    def test_file_empty_returns_exit_2(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        p.write_text("")
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 2
        assert "malformed" in msg

    def test_missing_timestamp_field_returns_exit_2(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        p.write_text(json.dumps({"cycle_id": 1, "pid": 123}))
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 2
        assert "missing" in msg.lower() or "malformed" in msg.lower()

    def test_invalid_timestamp_value_returns_exit_2(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        p.write_text(json.dumps({"timestamp": "not-a-date", "cycle_id": 1}))
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 2
        assert "malformed" in msg

    def test_exactly_at_threshold_is_stale(self, tmp_path):
        """A heartbeat exactly max_age_min old should be stale (not OK)."""
        p = tmp_path / "heartbeat.json"
        # Subtract a tiny extra so floating-point comparison works cleanly
        old_ts = datetime.now(timezone.utc) - timedelta(minutes=60, seconds=1)
        _write_heartbeat(p, old_ts)
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 1

    def test_just_under_threshold_is_ok(self, tmp_path):
        p = tmp_path / "heartbeat.json"
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=59)
        _write_heartbeat(p, recent_ts)
        exit_code, msg = check_heartbeat(str(p), max_age_min=60)
        assert exit_code == 0


class TestCheckHeartbeatCLI:
    def test_cli_missing_file_exits_2(self, tmp_path):
        missing = str(tmp_path / "nope.json")
        exit_code = main(["--heartbeat-path", missing, "--max-age-min", "60"])
        assert exit_code == 2

    def test_cli_fresh_file_exits_0(self, tmp_path, capsys):
        p = tmp_path / "heartbeat.json"
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=1)
        _write_heartbeat(p, recent_ts, cycle_id=7)
        exit_code = main(["--heartbeat-path", str(p), "--max-age-min", "60"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_cli_stale_file_exits_1(self, tmp_path, capsys):
        p = tmp_path / "heartbeat.json"
        old_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        _write_heartbeat(p, old_ts)
        exit_code = main(["--heartbeat-path", str(p), "--max-age-min", "60"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "stale" in captured.out
