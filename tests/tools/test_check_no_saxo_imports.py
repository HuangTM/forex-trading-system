"""Tests for tools/check_no_saxo_imports.py.

Operationalizes PROCESS-IMPL-1 from references/pre-registrations/
tas_ceiling_4h.md. The original pre-reg shipped a syntactically broken
grep stub; CTO 2026-04-27 routed the fix here.

Two correctness invariants:
  (a) A clean backtest entry point (scripts/run_backtest.py) PASSES.
  (b) A paper-trading entry point (scripts/run_paper_trading_vt.py)
      BLOCKS with at least one finding citing forex_system.saxo.
If either invariant flips, the firewall is broken or the guard is
broken; both are P0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

import check_no_saxo_imports as guard


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestForbiddenDetection:
    def test_paper_runner_blocked(self):
        """The paper trader transitively imports forex_system.saxo;
        guard MUST flag it."""
        graph = guard.walk_import_graph(REPO_ROOT / "scripts" / "run_paper_trading_vt.py")
        findings = guard.find_forbidden(graph)
        assert findings, (
            "Paper runner imports forex_system.saxo -- guard must surface "
            "at least one finding"
        )
        # At least one finding must cite a saxo module by name (not just path)
        why_strings = [why for _, why in findings]
        assert any("forex_system.saxo" in w for w in why_strings)

    def test_backtest_runner_passes(self):
        """The backtest entry point must NOT pull in Saxo / paper-trading code.
        If this test fails, either the firewall regressed or someone made
        the backtest path depend on broker code -- both are P0."""
        entry = REPO_ROOT / "scripts" / "run_backtest.py"
        if not entry.exists():
            pytest.skip("scripts/run_backtest.py not present")
        graph = guard.walk_import_graph(entry)
        findings = guard.find_forbidden(graph)
        assert not findings, (
            f"Backtest entry point pulls in forbidden code: {findings}"
        )


class TestImportParsing:
    def test_parse_imports_returns_module_names(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "from forex_system.saxo.client import SaxoClient\n"
            "from forex_system.strategies.foo import Foo\n"
        )
        names = guard.parse_imports(f)
        assert "os" in names
        assert "pathlib" in names
        assert "forex_system.saxo.client" in names
        assert "forex_system.strategies.foo" in names

    def test_parse_imports_raises_on_syntax_error(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def x(:\n  pass\n")
        with pytest.raises(RuntimeError):
            guard.parse_imports(f)


class TestModuleResolution:
    def test_third_party_returns_none(self):
        assert guard.resolve_module_to_path("numpy") is None
        assert guard.resolve_module_to_path("pandas") is None

    def test_project_module_resolves(self):
        path = guard.resolve_module_to_path("forex_system.strategies.vol_target_carry")
        assert path is not None
        assert path.exists()
        assert "vol_target_carry.py" in str(path)

    def test_nonexistent_project_module_returns_none(self):
        assert guard.resolve_module_to_path("forex_system.nope.does_not_exist") is None


class TestCLI:
    def test_cli_exits_0_for_clean_entry(self):
        entry = REPO_ROOT / "scripts" / "run_backtest.py"
        if not entry.exists():
            pytest.skip("scripts/run_backtest.py not present")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "check_no_saxo_imports.py"),
             str(entry)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}\n{result.stdout}\n{result.stderr}"
        )

    def test_cli_exits_1_for_paper_runner(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "check_no_saxo_imports.py"),
             str(REPO_ROOT / "scripts" / "run_paper_trading_vt.py")],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 1, (
            f"Expected exit 1 (forbidden imports found); got {result.returncode}\n"
            f"{result.stdout}"
        )
        assert "BLOCKED" in result.stdout

    def test_cli_exits_2_for_missing_entry(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "check_no_saxo_imports.py"),
             str(tmp_path / "does_not_exist.py")],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 2
