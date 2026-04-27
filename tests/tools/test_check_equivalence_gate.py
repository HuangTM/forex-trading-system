"""Tests for tools/check_equivalence_gate.py.

Path B prerequisite P5 / CONSENSUS Q4. The hook is the sole structural
enforcement that engine output never diverges from canonical script output
beyond the firm's PROCESS-G1 tolerance. Misrouting (treating a sizer change
as not-triggering, or running tests but not blocking on failure) silently
disables the protection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

import check_equivalence_gate as gate


class TestTriggerDetection:
    """Verify that the right paths trigger the gate."""

    def test_strategy_change_triggers(self):
        triggered, paths = gate.files_trigger_gate(
            ["src/forex_system/strategies/vol_target_carry.py"]
        )
        assert triggered
        assert paths == ["src/forex_system/strategies/vol_target_carry.py"]

    def test_sizer_change_triggers(self):
        triggered, paths = gate.files_trigger_gate(
            ["src/forex_system/sizing/vol_target.py"]
        )
        assert triggered
        assert len(paths) == 1

    def test_engine_change_triggers(self):
        triggered, paths = gate.files_trigger_gate(
            ["src/forex_system/backtest/engine.py"]
        )
        assert triggered
        assert len(paths) == 1

    def test_canonical_script_triggers(self):
        """Per TRIGGER_SCRIPTS, scripts/vol_targeting.py is paired with
        the engine equivalence test and must trigger."""
        triggered, paths = gate.files_trigger_gate(["scripts/vol_targeting.py"])
        assert triggered

    def test_init_py_does_not_trigger(self):
        """__init__.py changes don't change behavior; don't run the gate."""
        triggered, _ = gate.files_trigger_gate(
            ["src/forex_system/strategies/__init__.py"]
        )
        assert not triggered

    def test_registry_does_not_trigger(self):
        """registry.py is a factory boilerplate; no behavior change."""
        triggered, _ = gate.files_trigger_gate(
            ["src/forex_system/strategies/registry.py"]
        )
        assert not triggered

    def test_test_file_does_not_trigger(self):
        """Test-file changes shouldn't trigger the gate (they don't ship)."""
        triggered, _ = gate.files_trigger_gate(
            ["tests/equivalence/test_engine_vs_script.py"]
        )
        assert not triggered

    def test_doc_change_does_not_trigger(self):
        triggered, _ = gate.files_trigger_gate(
            ["references/pre-registrations/vol_target_carry.md"]
        )
        assert not triggered

    def test_unrelated_script_does_not_trigger(self):
        triggered, _ = gate.files_trigger_gate(["scripts/check_swap_rates.py"])
        assert not triggered

    def test_multiple_files_dedup_correctly(self):
        triggered, paths = gate.files_trigger_gate([
            "src/forex_system/strategies/vol_target_carry.py",
            "src/forex_system/sizing/vol_target.py",
            "README.md",  # ignored
        ])
        assert triggered
        assert len(paths) == 2
        assert "README.md" not in paths


class TestEquivalenceTestDiscovery:
    """Verify the gate locates the equivalence-test files."""

    def test_finds_existing_tests(self):
        """At least one equivalence test must exist under tests/equivalence/."""
        files = gate.equivalence_tests_exist()
        assert len(files) >= 1
        assert any(f.name == "test_engine_vs_script.py" for f in files)

    def test_only_test_files_returned(self):
        files = gate.equivalence_tests_exist()
        for f in files:
            assert f.name.startswith("test_")
            assert f.name.endswith(".py")
            assert f.name != "__init__.py"


class TestTriggerScriptCoverage:
    """CTO 2026-04-27 condition: TRIGGER_SCRIPTS must cover canonical
    research scripts for ALL strategies that have an equivalence pair --
    not just vol_target_carry. Path-of-least-resistance failure: someone
    edits scripts/tas_ceiling_4h_canonical.py without the gate firing.
    """

    def test_vol_target_canonical_covered(self):
        assert "scripts/vol_targeting.py" in gate.TRIGGER_SCRIPTS

    def test_tas_ceiling_canonical_covered(self):
        """Bet #2 canonical script must be registered before H2 dispatch."""
        assert "scripts/tas_ceiling_4h_canonical.py" in gate.TRIGGER_SCRIPTS

    def test_tas_ceiling_canonical_actually_triggers(self):
        triggered, paths = gate.files_trigger_gate(
            ["scripts/tas_ceiling_4h_canonical.py"]
        )
        assert triggered
        assert "scripts/tas_ceiling_4h_canonical.py" in paths


class TestHookFailClosed:
    """CTO 2026-04-27 condition: missing checker file must FAIL CLOSED, not
    silently skip. Verifies the bash-hook contract by running the hook in a
    temporary clone where the checker file is absent.
    """

    def test_hook_blocks_when_equivalence_checker_missing(self, tmp_path):
        """Running the installed hook against a clone with no
        check_equivalence_gate.py must exit non-zero with a clear message."""
        import shutil
        import subprocess

        repo_root = Path(__file__).resolve().parent.parent.parent
        hook_src = repo_root / "tools" / "git-hooks" / "pre-commit"
        if not hook_src.exists():
            pytest.skip("pre-commit hook source not present")

        # Build a minimal stub repo: copy the hook + check_pre_registration
        # (so gate 1 doesn't pre-empt the gate 2 missing-file branch).
        stub = tmp_path / "stub_repo"
        stub.mkdir()
        (stub / "tools").mkdir()
        shutil.copy(repo_root / "tools" / "check_pre_registration.py",
                    stub / "tools" / "check_pre_registration.py")
        # Deliberately do NOT copy check_equivalence_gate.py; that's the
        # missing-file we're testing. Also need an empty .venv/bin/python3
        # symlink-style shim so the hook's PYTHON detection finds something.
        (stub / ".venv" / "bin").mkdir(parents=True)
        venv_py = stub / ".venv" / "bin" / "python3"
        # Symlink to the actually-installed venv python so subprocess works.
        actual_py = repo_root / ".venv" / "bin" / "python3"
        if not actual_py.exists():
            pytest.skip(".venv/bin/python3 not found in repo")
        venv_py.symlink_to(actual_py)

        hook_dst = stub / "pre-commit"
        shutil.copy(hook_src, hook_dst)
        hook_dst.chmod(0o755)

        # Init a git repo and stage a doc-only file so gate 1 is no-op
        subprocess.run(["git", "init", "-q"], cwd=stub, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"],
                       cwd=stub, check=True)
        subprocess.run(["git", "config", "user.name", "test"],
                       cwd=stub, check=True)
        (stub / "README.md").write_text("test\n")
        subprocess.run(["git", "add", "README.md"], cwd=stub, check=True)

        # Run the hook directly
        result = subprocess.run(
            [str(hook_dst)],
            cwd=stub,
            capture_output=True,
            text=True,
        )
        # Expect non-zero exit (fail-closed) and the BLOCKING message
        assert result.returncode != 0, (
            f"Hook should fail closed when checker missing; got exit "
            f"{result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
        )
        assert "BLOCKING" in result.stdout or "BLOCKING" in result.stderr, (
            "Fail-closed message must include BLOCKING token for operator clarity"
        )


class TestPolicyViolationLog:
    """The gate records bypassed/failed events for forensic audit."""

    def test_violation_log_appends_jsonl(self, tmp_path, monkeypatch):
        log_path = tmp_path / "policy-violations.jsonl"
        monkeypatch.setattr(gate, "POLICY_LOG", log_path)
        gate.log_policy_violation("test_reason", ["src/forex_system/strategies/x.py"])
        gate.log_policy_violation("test_reason_2", ["scripts/vol_targeting.py"])
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2
        import json
        for line in lines:
            entry = json.loads(line)
            assert entry["policy"] == "equivalence-gate-Q4-P5"
            assert "timestamp" in entry
            assert "triggering_files" in entry
