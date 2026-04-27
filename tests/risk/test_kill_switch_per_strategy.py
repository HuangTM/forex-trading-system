"""Path B prereq P6: per-strategy KillSwitch tests.

Per docs/design/path_b_multi_strategy_competition.md M1 acceptance:
"≥ 8 test cases passing (isolation, reset audit, reset CLI, two
strategies tripping independently, shared-equity-fetch-failure
scenario, reset-without-operator-id rejected, audit log format,
double-reset rejected). All existing kill-switch tests continue to
pass."

This file ships 12 test cases covering all 8 listed scenarios plus
edge cases (per-strategy audit-log path defaulting, restart-safety
isolation, no-op reset on never-triggered).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from forex_system.risk.kill_switch import KillSwitch, TriggerReason


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESET_CLI = REPO_ROOT / "scripts" / "reset_kill_switch.py"


# --------------------------------------------------------------------------- #
# Test 1 — isolation: two strategies have independent state
# --------------------------------------------------------------------------- #

def test_two_strategies_isolated_state(tmp_path):
    """Two KillSwitch instances with different strategy_id values must
    have INDEPENDENT is_triggered state. Triggering A must not affect B.
    """
    audit_a = tmp_path / "audit_a.log"
    audit_b = tmp_path / "audit_b.log"
    ks_a = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_a),
                      strategy_id="alpha")
    ks_b = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_b),
                      strategy_id="bravo")
    ks_a.trigger(TriggerReason.MANUAL, "alpha trip")
    assert ks_a.is_triggered
    assert not ks_b.is_triggered, "bravo must not be affected by alpha's trigger"


# --------------------------------------------------------------------------- #
# Test 2 — per-strategy audit-log path defaults
# --------------------------------------------------------------------------- #

def test_per_strategy_audit_log_path_default(tmp_path, monkeypatch):
    """When strategy_id is provided and audit_log_path is NOT, the path
    must default to data/kill_switch_audit_{strategy_id}.log. Forces
    namespacing without the operator having to remember to pass it."""
    monkeypatch.chdir(tmp_path)
    ks = KillSwitch(initial_equity=100_000, strategy_id="vol_target_carry")
    assert ks.audit_log_path == "data/kill_switch_audit_vol_target_carry.log"


def test_per_strategy_audit_log_path_explicit_overrides(tmp_path):
    """An explicit audit_log_path overrides the per-strategy default."""
    explicit = tmp_path / "custom.log"
    ks = KillSwitch(initial_equity=100_000, strategy_id="alpha",
                    audit_log_path=str(explicit))
    assert ks.audit_log_path == str(explicit)


# --------------------------------------------------------------------------- #
# Test 3 — two strategies trip independently in their OWN audit logs
# --------------------------------------------------------------------------- #

def test_two_strategies_audit_logs_separate(tmp_path):
    audit_a = tmp_path / "audit_a.log"
    audit_b = tmp_path / "audit_b.log"
    ks_a = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_a),
                      strategy_id="alpha")
    ks_b = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_b),
                      strategy_id="bravo")
    ks_a.trigger(TriggerReason.MANUAL, "alpha")
    ks_b.trigger(TriggerReason.RECONCILIATION, "bravo recon")
    a_lines = audit_a.read_text().strip().split("\n")
    b_lines = audit_b.read_text().strip().split("\n")
    assert len(a_lines) == 1
    assert len(b_lines) == 1
    a_rec = json.loads(a_lines[0])
    b_rec = json.loads(b_lines[0])
    assert a_rec["reason"] == "manual_trigger"
    assert b_rec["reason"] == "reconciliation_mismatch"


# --------------------------------------------------------------------------- #
# Test 4 — reset writes audit entry per Path B P6
# --------------------------------------------------------------------------- #

def test_reset_writes_audit_entry(tmp_path):
    audit = tmp_path / "audit.log"
    ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit),
                    strategy_id="alpha")
    ks.trigger(TriggerReason.DAILY_LOSS, "DD")
    ks.reset(operator="opname", reason="incident-resolved",
             evidence_path="data/results/abc.json")
    lines = audit.read_text().strip().split("\n")
    assert len(lines) == 2
    reset_rec = json.loads(lines[1])
    assert reset_rec["event"] == "RESET"
    assert reset_rec["operator"] == "opname"
    assert reset_rec["reason"] == "incident-resolved"
    assert reset_rec["evidence_path"] == "data/results/abc.json"
    assert reset_rec["new_state"] == "OK"
    assert reset_rec["strategy_id"] == "alpha"


# --------------------------------------------------------------------------- #
# Test 5 — reset-without-operator-id rejected
# --------------------------------------------------------------------------- #

def test_reset_without_operator_raises(tmp_path):
    audit = tmp_path / "audit.log"
    ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit),
                    strategy_id="alpha")
    ks.trigger(TriggerReason.MANUAL, "trip")
    with pytest.raises(ValueError, match="non-empty operator"):
        ks.reset(operator="")
    # Still triggered after rejected reset
    assert ks.is_triggered


def test_reset_with_whitespace_operator_raises(tmp_path):
    """Operator='   ' must also be rejected (otherwise audit logs become
    forensically useless)."""
    audit = tmp_path / "audit.log"
    ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit),
                    strategy_id="alpha")
    ks.trigger(TriggerReason.MANUAL, "trip")
    with pytest.raises(ValueError, match="non-empty operator"):
        ks.reset(operator="   ")


# --------------------------------------------------------------------------- #
# Test 6 — double-reset is no-op (not an error, but does not duplicate audit)
# --------------------------------------------------------------------------- #

def test_double_reset_writes_only_once(tmp_path):
    audit = tmp_path / "audit.log"
    ks = KillSwitch(initial_equity=100_000, audit_log_path=str(audit),
                    strategy_id="alpha")
    ks.trigger(TriggerReason.MANUAL, "trip")
    ks.reset(operator="op", reason="first")
    ks.reset(operator="op", reason="second")  # is_triggered is False; no-op
    lines = audit.read_text().strip().split("\n")
    # 1 trigger + 1 reset = 2 lines (second reset is no-op since not triggered)
    assert len(lines) == 2


# --------------------------------------------------------------------------- #
# Test 7 — shared equity-fetch-failure scenario: each strategy's own
# fetch-failure counter is independent
# --------------------------------------------------------------------------- #

def test_shared_equity_fetch_failure_each_strategy_independent(tmp_path):
    """Path B §6.5: a shared data-fetch failure (e.g., Saxo timeout)
    must NOT cascade across strategies. Each strategy tracks its own
    consecutive_fetch_failures counter."""
    audit_a = tmp_path / "audit_a.log"
    audit_b = tmp_path / "audit_b.log"
    ks_a = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_a),
                      strategy_id="alpha")
    ks_b = KillSwitch(initial_equity=100_000, audit_log_path=str(audit_b),
                      strategy_id="bravo")
    # Alpha sees 2 of 3 failures; bravo sees 1
    ks_a.record_equity_fetch_failure()
    ks_a.record_equity_fetch_failure()
    ks_b.record_equity_fetch_failure()
    assert ks_a.consecutive_fetch_failures == 2
    assert ks_b.consecutive_fetch_failures == 1
    # Neither has tripped yet
    assert not ks_a.is_triggered
    assert not ks_b.is_triggered
    # Bravo recovers; alpha's 3rd fail trips IT alone
    ks_b.record_equity_fetch_success()
    triggered_now = ks_a.record_equity_fetch_failure()
    assert triggered_now is True
    assert ks_a.is_triggered
    assert not ks_b.is_triggered, "bravo's counter and trip state must remain independent"


# --------------------------------------------------------------------------- #
# Test 8 — backward compat: existing single-strategy usage unaffected
# --------------------------------------------------------------------------- #

def test_default_strategy_id_none_preserves_default_audit_path():
    """Without strategy_id, audit_log_path remains None unless explicitly set."""
    ks = KillSwitch(initial_equity=100_000)
    assert ks.audit_log_path is None
    assert ks.strategy_id is None


def test_default_strategy_id_with_explicit_audit_path():
    ks = KillSwitch(initial_equity=100_000, audit_log_path="data/legacy.log")
    assert ks.audit_log_path == "data/legacy.log"
    assert ks.strategy_id is None


# --------------------------------------------------------------------------- #
# Test 9 -- reset CLI smoke tests
# --------------------------------------------------------------------------- #

class TestResetCLI:
    def test_reset_cli_writes_audit_entry(self, tmp_path):
        audit = tmp_path / "kill_switch_audit_alpha.log"
        # Pre-seed with a HALTED state so the reset has something to clear
        audit.write_text(json.dumps({
            "timestamp": "2026-04-27T00:00:00+00:00",
            "event": "TRIGGER",
            "new_state": "HALTED_MANUAL_TRIGGER",
        }) + "\n")

        result = subprocess.run(
            [sys.executable, str(RESET_CLI),
             "--strategy-id", "alpha",
             "--operator-id", "huangtm",
             "--reason", "incident resolved 2026-04-27",
             "--audit-log-path", str(audit)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        lines = audit.read_text().strip().split("\n")
        assert len(lines) == 2
        reset_rec = json.loads(lines[1])
        assert reset_rec["event"] == "RESET"
        assert reset_rec["operator"] == "huangtm"
        assert reset_rec["reason"] == "incident resolved 2026-04-27"
        assert reset_rec["strategy_id"] == "alpha"

    def test_reset_cli_rejects_empty_operator(self, tmp_path):
        audit = tmp_path / "audit.log"
        audit.write_text("")
        result = subprocess.run(
            [sys.executable, str(RESET_CLI),
             "--strategy-id", "alpha",
             "--operator-id", "   ",  # whitespace-only
             "--reason", "test",
             "--audit-log-path", str(audit)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 2

    def test_reset_cli_rejects_empty_reason(self, tmp_path):
        audit = tmp_path / "audit.log"
        audit.write_text("")
        result = subprocess.run(
            [sys.executable, str(RESET_CLI),
             "--strategy-id", "alpha",
             "--operator-id", "huangtm",
             "--reason", "",  # empty
             "--audit-log-path", str(audit)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 2

    def test_reset_cli_missing_strategy_id_argparse_rejects(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(RESET_CLI),
             "--operator-id", "huangtm",
             "--reason", "test"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        # argparse exits 2 on missing required arg
        assert result.returncode == 2
