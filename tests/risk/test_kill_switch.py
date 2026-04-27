"""Tests for the binary kill switch."""

import json
import os

import pytest

from forex_system.risk.kill_switch import (
    MAX_CONSECUTIVE_FETCH_FAILURES,
    MAX_DAILY_LOSS_PCT,
    KillSwitch,
    TriggerReason,
)


class TestKillSwitchDefaults:
    def test_starts_not_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.is_triggered
        assert ks.status_line == "OK"

    def test_default_threshold_is_two_percent(self):
        assert MAX_DAILY_LOSS_PCT == 0.02

    def test_no_events_initially(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.events == []
        assert ks.last_event is None


class TestDailyLossTrigger:
    def test_small_loss_does_not_trigger(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.check_and_trigger(99_000)  # -1%
        assert not ks.is_triggered

    def test_loss_at_threshold_triggers(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.check_and_trigger(98_000)  # exactly -2%
        assert ks.is_triggered

    def test_loss_beyond_threshold_triggers(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.check_and_trigger(95_000)  # -5%
        assert ks.is_triggered

    def test_gain_does_not_trigger(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.check_and_trigger(110_000)
        assert not ks.is_triggered

    def test_trigger_records_event(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.check_and_trigger(97_000)
        assert len(ks.events) == 1
        assert ks.events[0].reason == TriggerReason.DAILY_LOSS
        assert ks.events[0].equity_at_trigger == 97_000

    def test_custom_threshold(self):
        ks = KillSwitch(initial_equity=100_000, max_daily_loss_pct=0.05)
        assert not ks.check_and_trigger(96_000)  # -4%, within 5%
        assert ks.check_and_trigger(94_000)  # -6%, beyond 5%
        assert ks.is_triggered


class TestManualTrigger:
    def test_trigger_reconciliation(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.RECONCILIATION, "size mismatch on USDJPY", 100_000)
        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.RECONCILIATION

    def test_trigger_auth_death(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.AUTH_DEATH, "token expires in 90s", 100_000)
        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.AUTH_DEATH

    def test_trigger_is_idempotent(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test 1", 100_000)
        ks.trigger(TriggerReason.MANUAL, "test 2", 100_000)
        assert len(ks.events) == 1  # Second trigger ignored

    def test_check_after_trigger_stays_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        assert ks.check_and_trigger(110_000)  # Even with gains


class TestReset:
    def test_reset_clears_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        ks.reset(operator="HuangTM")
        assert not ks.is_triggered
        assert ks.status_line == "OK"

    def test_reset_preserves_event_history(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        ks.reset(operator="HuangTM")
        assert len(ks.events) == 1  # History preserved

    def test_reset_when_not_triggered_is_noop(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.reset(operator="HuangTM")
        assert not ks.is_triggered

    def test_can_trigger_again_after_reset(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "first", 100_000)
        ks.reset(operator="HuangTM")
        ks.trigger(TriggerReason.MANUAL, "second", 95_000)
        assert ks.is_triggered
        assert len(ks.events) == 2


class TestConsecutiveFetchFailures:
    def test_single_failure_does_not_trigger(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.record_equity_fetch_failure()
        assert not ks.is_triggered
        assert ks.consecutive_fetch_failures == 1

    def test_threshold_triggers_with_error_reason(self):
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=3)
        assert not ks.record_equity_fetch_failure()
        assert not ks.record_equity_fetch_failure()
        assert ks.record_equity_fetch_failure()  # 3rd trips
        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.ERROR

    def test_success_resets_counter(self):
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=3)
        ks.record_equity_fetch_failure()
        ks.record_equity_fetch_failure()
        ks.record_equity_fetch_success()
        assert ks.consecutive_fetch_failures == 0
        # Two more failures should NOT trip now — counter was reset
        ks.record_equity_fetch_failure()
        ks.record_equity_fetch_failure()
        assert not ks.is_triggered

    def test_failure_after_trigger_is_noop(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "already halted", 100_000)
        assert not ks.record_equity_fetch_failure()  # returns False, no double-trigger
        assert len(ks.events) == 1


class TestStatusLine:
    def test_ok_when_not_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.status_line == "OK"

    def test_shows_reason_when_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.DAILY_LOSS, "lost too much", 95_000)
        assert "HALTED" in ks.status_line
        assert "daily_loss_exceeded" in ks.status_line


# ---------------------------------------------------------------------------
# Tests for kill-switch restart audit (Fix 3)
# ---------------------------------------------------------------------------

def _write_audit_log(path, entries: list[dict]) -> None:
    """Helper: write JSON-lines audit log to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestKillSwitchAuditOnStartup:
    """KillSwitch must refuse restart if last audit event was HALTED."""

    def test_no_audit_log_starts_clean(self, tmp_path, monkeypatch):
        """Missing audit log → KillSwitch starts without raising."""
        audit_path = tmp_path / "kill_switch_audit.log"
        # Ensure the env var is unset
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        # File does not exist — should start cleanly
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))
        assert not ks.is_triggered

    def test_empty_audit_log_starts_clean(self, tmp_path, monkeypatch):
        """Empty audit log → KillSwitch starts without raising."""
        audit_path = tmp_path / "kill_switch_audit.log"
        audit_path.write_text("")
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))
        assert not ks.is_triggered

    def test_last_event_ok_state_starts_clean(self, tmp_path, monkeypatch):
        """Last audit entry new_state=RUNNING → KillSwitch starts clean."""
        audit_path = tmp_path / "kill_switch_audit.log"
        _write_audit_log(audit_path, [
            {"timestamp": "2026-04-25T00:00:00+00:00", "event": "RESET",
             "operator": "testuser", "new_state": "RUNNING"},
        ])
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))
        assert not ks.is_triggered

    def test_last_event_halted_raises_without_force_reset(self, tmp_path, monkeypatch):
        """Last audit entry new_state=HALTED → raises RuntimeError without env var."""
        audit_path = tmp_path / "kill_switch_audit.log"
        _write_audit_log(audit_path, [
            {"timestamp": "2026-04-25T00:00:00+00:00", "event": "RESET",
             "operator": "testuser", "new_state": "HALTED"},
        ])
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        with pytest.raises(RuntimeError, match="HALTED"):
            KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))

    def test_last_event_flat_and_halted_raises_without_force_reset(self, tmp_path, monkeypatch):
        """Last audit entry new_state=FLAT_AND_HALTED → raises RuntimeError without env var.

        This matches the actual audit log state from 2026-04-25.
        """
        audit_path = tmp_path / "kill_switch_audit.log"
        _write_audit_log(audit_path, [
            {"timestamp": "2026-04-25T00:00:00+00:00", "event": "RESET",
             "operator": "huangtm@gmail.com",
             "new_state": "FLAT_AND_HALTED"},
        ])
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        with pytest.raises(RuntimeError, match="HALTED"):
            KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))

    def test_force_reset_env_var_allows_start(self, tmp_path, monkeypatch):
        """KILL_SWITCH_FORCE_RESET=1 with HALTED last state → starts without raising."""
        audit_path = tmp_path / "kill_switch_audit.log"
        _write_audit_log(audit_path, [
            {"timestamp": "2026-04-25T00:00:00+00:00", "event": "RESET",
             "operator": "testuser", "new_state": "FLAT_AND_HALTED"},
        ])
        monkeypatch.setenv("KILL_SWITCH_FORCE_RESET", "1")
        monkeypatch.setenv("USER", "test_operator")
        # Should NOT raise
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))
        assert not ks.is_triggered

    def test_force_reset_writes_audit_entry(self, tmp_path, monkeypatch):
        """KILL_SWITCH_FORCE_RESET=1 must append a FORCE_RESET_ON_STARTUP audit entry."""
        audit_path = tmp_path / "kill_switch_audit.log"
        _write_audit_log(audit_path, [
            {"timestamp": "2026-04-25T00:00:00+00:00", "event": "RESET",
             "operator": "testuser", "new_state": "FLAT_AND_HALTED"},
        ])
        monkeypatch.setenv("KILL_SWITCH_FORCE_RESET", "1")
        monkeypatch.setenv("USER", "test_operator")

        KillSwitch(initial_equity=100_000, audit_log_path=str(audit_path))

        # Read all audit entries
        lines = [json.loads(l) for l in audit_path.read_text().strip().splitlines()]
        # Should have 2 entries: the original + the new force-reset entry
        assert len(lines) == 2
        new_entry = lines[-1]
        assert new_entry["event"] == "FORCE_RESET_ON_STARTUP"
        assert new_entry["operator"] == "test_operator"
        assert "KILL_SWITCH_FORCE_RESET=1" in new_entry["reason"]

    def test_no_audit_log_path_skips_check(self, tmp_path, monkeypatch):
        """audit_log_path=None disables the startup check entirely."""
        monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
        ks = KillSwitch(initial_equity=100_000, audit_log_path=None)
        assert not ks.is_triggered


# ---------------------------------------------------------------------------
# Tests for balance-fetch WARN log with N/MAX context (D2)
# ---------------------------------------------------------------------------

class TestFetchFailureWarnContext:
    """WARN log must surface 'failure N of MAX' on each non-terminal fetch failure."""

    def test_first_failure_logs_warn_1_of_3(self, caplog):
        import logging
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=3)
        with caplog.at_level(logging.WARNING, logger="forex_system.risk.kill_switch"):
            ks.record_equity_fetch_failure()
        warn_lines = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("failure 1 of 3" in line for line in warn_lines), (
            f"Expected 'failure 1 of 3' in WARN lines, got: {warn_lines}"
        )

    def test_second_failure_logs_warn_2_of_3(self, caplog):
        import logging
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=3)
        ks.record_equity_fetch_failure()  # 1st — already checked above
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="forex_system.risk.kill_switch"):
            ks.record_equity_fetch_failure()
        warn_lines = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("failure 2 of 3" in line for line in warn_lines), (
            f"Expected 'failure 2 of 3' in WARN lines, got: {warn_lines}"
        )

    def test_third_failure_triggers_no_warn(self, caplog):
        """The 3rd failure reaches threshold → kill switch fires (CRITICAL), no WARN."""
        import logging
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=3)
        ks.record_equity_fetch_failure()
        ks.record_equity_fetch_failure()
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="forex_system.risk.kill_switch"):
            triggered = ks.record_equity_fetch_failure()
        assert triggered
        assert ks.is_triggered
        warn_lines = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        # Should not see "failure 3 of 3" WARN — the trigger path fires instead
        assert not any("failure 3 of 3" in line for line in warn_lines)

    def test_warn_uses_correct_max_when_overridden(self, caplog):
        """Custom max_consecutive_fetch_failures appears correctly in the WARN."""
        import logging
        ks = KillSwitch(initial_equity=100_000, max_consecutive_fetch_failures=5)
        with caplog.at_level(logging.WARNING, logger="forex_system.risk.kill_switch"):
            ks.record_equity_fetch_failure()
        warn_lines = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("failure 1 of 5" in line for line in warn_lines), (
            f"Expected 'failure 1 of 5' in WARN lines, got: {warn_lines}"
        )

    def test_max_consecutive_fetch_failures_constant(self):
        """Sanity-check that the module constant is still 3."""
        assert MAX_CONSECUTIVE_FETCH_FAILURES == 3


class TestWS03TriggerAuditAppend:
    """WS-03 (CTO consensus 2026-04-26): every trigger() must append a
    structured JSON-line to the audit log so the kill-switch state
    transition is reconstructable post-hoc.
    """

    def test_trigger_appends_audit_entry(self, tmp_path):
        audit = tmp_path / "audit.log"
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))
        ks.trigger(TriggerReason.MANUAL, "test trigger", equity=99_500.0)
        contents = audit.read_text().strip().split("\n")
        assert len(contents) == 1
        record = json.loads(contents[0])
        assert record["event"] == "TRIGGER"
        assert record["reason"] == "manual_trigger"
        assert record["detail"] == "test trigger"
        assert record["equity_at_trigger"] == 99_500.0
        # new_state must contain HALTED so a restart correctly refuses-to-start
        assert "HALTED" in record["new_state"]
        # Operator field present so audit format matches RESET/VERIFY entries
        assert record["operator"] == "system"

    def test_trigger_audit_new_state_per_reason(self, tmp_path):
        """new_state encodes the trigger reason for forensic clarity."""
        audit = tmp_path / "audit.log"
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))
        ks.trigger(TriggerReason.DAILY_LOSS, "DD")
        record = json.loads(audit.read_text().strip().split("\n")[0])
        assert record["new_state"] == "HALTED_DAILY_LOSS_EXCEEDED"

    def test_trigger_audit_disabled_when_no_path(self, tmp_path):
        """audit_log_path=None must not raise; trigger still flips state."""
        ks = KillSwitch(initial_equity=100_000, audit_log_path=None)
        ks.trigger(TriggerReason.RECONCILIATION, "no audit")
        assert ks.is_triggered  # state still flipped
        # No exception expected; nothing to assert on the (absent) file

    def test_trigger_audit_idempotent_with_first_event(self, tmp_path):
        """Idempotent trigger must NOT append a second audit entry."""
        audit = tmp_path / "audit.log"
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))
        ks.trigger(TriggerReason.MANUAL, "first")
        ks.trigger(TriggerReason.DAILY_LOSS, "second")  # ignored — already triggered
        lines = audit.read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["detail"] == "first"

    def test_trigger_audit_parseable_by_existing_parser(self, tmp_path):
        """The new TRIGGER entry must parse via _last_audit_entry() (line 72)."""
        from forex_system.risk.kill_switch import _last_audit_entry, _new_state_is_halted
        audit = tmp_path / "audit.log"
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))
        ks.trigger(TriggerReason.AUTH_DEATH, "token expired")
        last = _last_audit_entry(str(audit))
        assert last is not None
        assert _new_state_is_halted(last["new_state"])  # restart-safety guard fires

    def test_audit_write_failure_does_not_block_trigger(self, tmp_path, monkeypatch):
        """If the audit append raises, trigger() must STILL halt the system.

        The kill switch's halting-of-trading is a stronger invariant than the
        audit trail. An I/O failure (full disk, permission error, etc.) must
        not leave the system trading.
        """
        from forex_system.risk import kill_switch as ks_mod
        audit = tmp_path / "audit.log"
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))

        def fake_write(*args, **kwargs):
            raise IOError("disk full")

        monkeypatch.setattr(ks_mod, "_write_audit_entry", fake_write)
        ks.trigger(TriggerReason.MANUAL, "audit fails")
        assert ks.is_triggered
        # In-memory event preserved
        assert ks.last_event is not None
        assert ks.last_event.reason == TriggerReason.MANUAL

    def test_existing_reset_format_compatibility(self, tmp_path):
        """Pre-existing RESET/VERIFY entries co-exist with new TRIGGER entries.

        The audit log started with RESET (operator-side) and now includes
        TRIGGER (system-side). Both must parse via the same json.loads path.
        """
        audit = tmp_path / "audit.log"
        # Simulate an existing RESET entry (matches data/kill_switch_audit.log
        # format from production).
        audit.write_text(
            json.dumps({
                "timestamp": "2026-04-25T00:00:00+00:00",
                "event": "RESET",
                "operator": "huangtm",
                "previous_state": "HALTED",
                "new_state": "OK",
            }) + "\n"
        )
        # KillSwitch starts cleanly because last entry's new_state is "OK".
        ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit))
        ks.trigger(TriggerReason.DAILY_LOSS, "post-reset trigger")
        lines = audit.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "RESET"
        assert json.loads(lines[1])["event"] == "TRIGGER"
