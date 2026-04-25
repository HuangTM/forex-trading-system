"""Tests for tools/check_pre_registration.py.

Tests the check_pre_registration function and the main() gating logic.
Does NOT test the git-diff subprocess (that's environment-dependent);
instead tests the check logic directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to path so we can import tools/check_pre_registration
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.check_pre_registration import check_pre_registration, main


@pytest.fixture
def tmp_pre_reg_dir(tmp_path, monkeypatch):
    """Override _PRE_REG_DIR to a tmp directory."""
    import tools.check_pre_registration as crp
    monkeypatch.setattr(crp, "_PRE_REG_DIR", tmp_path / "pre-registrations")
    (tmp_path / "pre-registrations").mkdir()
    return tmp_path / "pre-registrations"


class TestCheckPreRegistration:
    """Unit tests for check_pre_registration()."""

    def test_passes_when_pre_reg_exists(self, tmp_pre_reg_dir):
        """If a .md pre-reg exists, check returns True."""
        pre_reg = tmp_pre_reg_dir / "my_strategy.md"
        pre_reg.write_text("# Pre-Reg\ngate_threshold: 0.50")

        strategy_file = Path("src/forex_system/strategies/my_strategy.py")
        passed, message = check_pre_registration(strategy_file)

        assert passed is True
        assert "PASS" in message

    def test_fails_when_pre_reg_missing(self, tmp_pre_reg_dir):
        """If no .md pre-reg exists, check returns False."""
        strategy_file = Path("src/forex_system/strategies/new_strategy.py")
        passed, message = check_pre_registration(strategy_file)

        assert passed is False
        assert "FAIL" in message
        assert "new_strategy" in message

    def test_uses_stem_not_extension(self, tmp_pre_reg_dir):
        """Strategy name is derived from file stem (no .py)."""
        pre_reg = tmp_pre_reg_dir / "carry_trade.md"
        pre_reg.write_text("# Pre-Reg")

        strategy_file = Path("src/forex_system/strategies/carry_trade.py")
        passed, _ = check_pre_registration(strategy_file)
        assert passed is True

    def test_message_shows_expected_path(self, tmp_pre_reg_dir):
        """Failure message names the expected pre-reg path."""
        strategy_file = Path("src/forex_system/strategies/alpha_v2.py")
        _, message = check_pre_registration(strategy_file)

        assert "alpha_v2.md" in message

    def test_existing_vol_target_carry_passes(self):
        """The backfill pre-reg for vol_target_carry must already pass."""
        pre_reg = Path("references/pre-registrations/vol_target_carry.md")
        if not pre_reg.exists():
            pytest.skip("vol_target_carry pre-registration not yet created")

        strategy_file = Path("src/forex_system/strategies/vol_target_carry.py")
        passed, message = check_pre_registration(strategy_file)
        assert passed is True


class TestMainGating:
    """Test the main() exit code logic."""

    def test_main_exits_0_with_no_staged_files(self, monkeypatch):
        """When no staged strategy files exist, main() exits 0."""
        import tools.check_pre_registration as crp
        monkeypatch.setattr(crp, "get_staged_new_strategy_files", lambda: [])

        result = main_wrapper(["--staged"])
        assert result == 0

    def test_main_exits_0_all_mode_when_all_have_pre_reg(self, tmp_pre_reg_dir, monkeypatch):
        """--all mode: exits 0 when all strategies have pre-registrations."""
        import tools.check_pre_registration as crp

        # One strategy, one pre-reg
        pre_reg = tmp_pre_reg_dir / "test_strat.md"
        pre_reg.write_text("# Pre-Reg\ngate_threshold: 0.5")

        fake_file = Path("src/forex_system/strategies/test_strat.py")
        monkeypatch.setattr(crp, "get_all_strategy_files", lambda: [fake_file])

        result = main_wrapper(["--all"])
        assert result == 0

    def test_main_exits_1_when_pre_reg_missing(self, tmp_pre_reg_dir, monkeypatch):
        """When a staged strategy lacks a pre-reg, main() exits 1."""
        import tools.check_pre_registration as crp

        fake_file = Path("src/forex_system/strategies/unregistered_strat.py")
        monkeypatch.setattr(crp, "get_staged_new_strategy_files", lambda: [fake_file])

        result = main_wrapper(["--staged"])
        assert result == 1


def main_wrapper(args: list[str]) -> int:
    """Run main() with controlled sys.argv."""
    original = sys.argv[:]
    try:
        sys.argv = ["check_pre_registration.py"] + args
        return main()
    finally:
        sys.argv = original
