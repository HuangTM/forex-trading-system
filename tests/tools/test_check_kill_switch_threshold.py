"""Tests for tools/check_kill_switch_threshold.py.

Validates Gate 3: CRO binding constraint #3 — every pre-registered trial must
declare kill_switch_threshold verbatim in its pre-reg markdown before commit.

Does NOT test the live git-diff subprocess (environment-dependent); instead
tests check_file() directly and mocks get_staged_new_pre_reg_files() for
integration tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so we can import tools/check_kill_switch_threshold
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.check_kill_switch_threshold import (
    check_file,
    get_staged_new_pre_reg_files,
    main,
)


# ---------------------------------------------------------------------------
# check_file() unit tests
# ---------------------------------------------------------------------------


class TestCheckFile:
    """Unit tests for check_file()."""

    def test_passes_with_numeric_threshold(self, tmp_path):
        """A pre-reg with `kill_switch_threshold: 0.30` passes."""
        pre_reg = tmp_path / "bet_alpha.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "strategy: bet_alpha\n"
            "kill_switch_threshold: 0.30\n"
            "gate_threshold: 0.50\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is True
        assert "PASS" in reason

    def test_fails_without_field(self, tmp_path):
        """A pre-reg with no kill_switch_threshold line is rejected."""
        pre_reg = tmp_path / "no_threshold.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "strategy: no_threshold\n"
            "gate_threshold: 0.50\n"
            "We will stop if things go badly.\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is False
        assert "FAIL" in reason
        assert "kill_switch_threshold" in reason

    def test_commented_out_field_still_passes_v0(self, tmp_path):
        """V0 known limitation: HTML-commented field still satisfies the regex.

        The regex scans all lines including those inside HTML comments. This is
        an acceptable v0 trade-off; future gate revision can add comment-awareness.
        """
        pre_reg = tmp_path / "commented.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "<!-- kill_switch_threshold: 0.30 -->\n"
            "No explicit field outside the comment.\n"
        )
        ok, _ = check_file(pre_reg)
        # V0: the commented line matches — gate passes (known limitation)
        assert ok is True  # See module docstring for the v0 caveat

    def test_case_sensitive_field_name(self, tmp_path):
        """Kill_Switch_Threshold (wrong case) does NOT satisfy the gate."""
        pre_reg = tmp_path / "wrong_case.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "Kill_Switch_Threshold: 0.30\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is False
        assert "FAIL" in reason

    def test_passes_with_label_value(self, tmp_path):
        """Field value may be a label string, not just a number."""
        pre_reg = tmp_path / "label_threshold.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "kill_switch_threshold: VTC-T1\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is True
        assert "PASS" in reason

    def test_passes_with_descriptive_label(self, tmp_path):
        """Value can be any non-whitespace token, including a reference label."""
        pre_reg = tmp_path / "descriptive_label.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "kill_switch_threshold: see-falsification-criteria-T1-T8\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is True
        assert "PASS" in reason

    def test_field_with_leading_whitespace_passes(self, tmp_path):
        """Field indented with spaces (e.g., in a YAML block) still matches."""
        pre_reg = tmp_path / "indented.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "  kill_switch_threshold: 0.25\n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is True

    def test_empty_value_does_not_pass(self, tmp_path):
        """kill_switch_threshold: with no value fails (requires \\S+)."""
        pre_reg = tmp_path / "empty_value.md"
        pre_reg.write_text(
            "# Pre-Registration\n"
            "kill_switch_threshold:   \n"
        )
        ok, reason = check_file(pre_reg)
        assert ok is False


# ---------------------------------------------------------------------------
# get_staged_new_pre_reg_files() unit tests
# ---------------------------------------------------------------------------


class TestGetStagedNewPreRegFiles:
    """Test that get_staged_new_pre_reg_files() filters to ADDED pre-reg files."""

    def test_returns_only_added_pre_reg_files(self, monkeypatch):
        """Only 'A'-status files under references/pre-registrations/ are returned."""
        mock_output = (
            "A\treferences/pre-registrations/new_trial.md\n"
            "M\treferences/pre-registrations/existing_trial.md\n"
            "A\tsrc/forex_system/strategies/new_strat.py\n"
            "A\treferences/pre-registrations/another_new.md\n"
        )

        class MockResult:
            returncode = 0
            stdout = mock_output
            stderr = ""

        monkeypatch.setattr(
            "tools.check_kill_switch_threshold.subprocess.run",
            lambda *a, **kw: MockResult(),
        )

        result = get_staged_new_pre_reg_files()
        names = [p.name for p in result]
        assert "new_trial.md" in names
        assert "another_new.md" in names
        # Modified file must NOT appear
        assert "existing_trial.md" not in names
        # Non-pre-reg file must NOT appear
        assert "new_strat.py" not in names

    def test_returns_empty_when_no_new_pre_regs(self, monkeypatch):
        """Returns [] when no ADDED pre-reg markdown files are staged."""
        mock_output = "M\treferences/pre-registrations/old_trial.md\n"

        class MockResult:
            returncode = 0
            stdout = mock_output
            stderr = ""

        monkeypatch.setattr(
            "tools.check_kill_switch_threshold.subprocess.run",
            lambda *a, **kw: MockResult(),
        )

        result = get_staged_new_pre_reg_files()
        assert result == []


# ---------------------------------------------------------------------------
# main() integration tests
# ---------------------------------------------------------------------------


def _run_main(argv: list[str]) -> int:
    """Run main() with controlled sys.argv."""
    original = sys.argv[:]
    try:
        sys.argv = ["check_kill_switch_threshold.py"] + argv
        return main()
    finally:
        sys.argv = original


class TestMainGating:
    """Integration tests for main() exit-code logic."""

    def test_main_exits_0_when_no_staged_files(self, monkeypatch):
        """No staged pre-reg files → exit 0 (gate is no-op)."""
        import tools.check_kill_switch_threshold as ckt
        monkeypatch.setattr(ckt, "get_staged_new_pre_reg_files", lambda: [])
        assert _run_main(["--staged"]) == 0

    def test_main_exits_0_when_all_files_compliant(self, tmp_path, monkeypatch):
        """All staged pre-regs have the field → exit 0."""
        import tools.check_kill_switch_threshold as ckt

        pre_reg = tmp_path / "compliant.md"
        pre_reg.write_text("kill_switch_threshold: 0.30\n")

        monkeypatch.setattr(ckt, "get_staged_new_pre_reg_files", lambda: [pre_reg])
        assert _run_main(["--staged"]) == 0

    def test_main_exits_1_when_field_missing(self, tmp_path, monkeypatch):
        """Staged pre-reg without the field → exit 1 (block)."""
        import tools.check_kill_switch_threshold as ckt

        pre_reg = tmp_path / "noncompliant.md"
        pre_reg.write_text("# Pre-Registration\ngate_threshold: 0.30\n")

        monkeypatch.setattr(ckt, "get_staged_new_pre_reg_files", lambda: [pre_reg])
        assert _run_main(["--staged"]) == 1

    def test_check_flag_passes_compliant_file(self, tmp_path):
        """--check <path> mode passes for a compliant file."""
        pre_reg = tmp_path / "ok.md"
        pre_reg.write_text("kill_switch_threshold: 0.30\n")
        assert _run_main(["--check", str(pre_reg)]) == 0

    def test_check_flag_fails_noncompliant_file(self, tmp_path):
        """--check <path> mode fails (exit 1) for a file without the field."""
        pre_reg = tmp_path / "bad.md"
        pre_reg.write_text("# No threshold here\n")
        assert _run_main(["--check", str(pre_reg)]) == 1
