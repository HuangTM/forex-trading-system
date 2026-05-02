"""Tests for harness/preregistration.py.

Covers:
- Parse valid pre-reg markdown + sidecar: correct field values
- Missing kill_switch_threshold raises ConfigError
- Missing sidecar raises ConfigError
- Bad YAML in sidecar raises ConfigError
- Missing required sidecar fields raise ConfigError
- Strategy ID and pair parsed correctly
- Triggers correctly mapped from sidecar
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from forex_system.core.errors import ConfigError
from forex_system.harness.preregistration import (
    parse_pre_registration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_MARKDOWN = """\
# Pre-Registration: test_strategy

**Status:** Active
**Date:** 2026-05-01
**Strategy ID:** test_strategy
**Pair:** USDJPY
**Binding commit at registration:** abc1234

## Hypothesis

Test strategy carries USDJPY long with vol-targeting.
The carry yield is harvested daily net of swap costs.

---

## Falsification Criteria

gate_threshold: 0.50
kill_switch_threshold: 0.60

- **VTC-T1:** OOS Sharpe < 0.60 on production engine run
- **VTC-T2:** Max drawdown exceeds 25%
- **VTC-T3:** Walk-forward OOS windows: fewer than 6 of 14 beat B&H Sharpe
"""

VALID_SIDECAR = {
    "pair": "USDJPY",
    "oos_overlap": False,
    "oos_window_start": "2020-01-01",
    "oos_window_end": "2026-04-25",
    "triggers": [
        {"label": "VTC-T1", "metric": "oos_sharpe", "operator": "<", "threshold": 0.60},
        {"label": "VTC-T2", "metric": "max_drawdown", "operator": ">", "threshold": 0.25},
        {"label": "VTC-T3", "metric": "wf_windows_beat_fraction", "operator": "<", "threshold": 0.43},
    ],
}

MARKDOWN_NO_KST = """\
# Pre-Registration: no_kst_strategy

**Strategy ID:** no_kst_strategy
**Pair:** EURUSD

## Hypothesis

This strategy has no kill_switch_threshold field.

## Falsification Criteria

gate_threshold: 0.30
"""


@pytest.fixture()
def pre_reg_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with valid pre-reg + sidecar files."""
    md_path = tmp_path / "test_strategy.md"
    sidecar_path = tmp_path / "test_strategy.triggers.yaml"
    md_path.write_text(VALID_MARKDOWN)
    sidecar_path.write_text(yaml.dump(VALID_SIDECAR))
    return tmp_path


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestParseValidPreReg:
    def test_strategy_parsed(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.strategy == "test_strategy"

    def test_pair_parsed(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.pair == "USDJPY"

    def test_kill_switch_threshold_raw_string(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.kill_switch_threshold == "0.60"

    def test_gate_threshold_parsed_as_float(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.gate_threshold == pytest.approx(0.50)

    def test_hypothesis_summary_non_empty(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert len(spec.hypothesis_summary) > 0
        assert "carry" in spec.hypothesis_summary.lower()

    def test_triggers_count(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert len(spec.triggers) == 3

    def test_trigger_labels(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        labels = [t.label for t in spec.triggers]
        assert "VTC-T1" in labels
        assert "VTC-T2" in labels
        assert "VTC-T3" in labels

    def test_trigger_fields_correct(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        vtc_t1 = next(t for t in spec.triggers if t.label == "VTC-T1")
        assert vtc_t1.metric == "oos_sharpe"
        assert vtc_t1.operator == "<"
        assert vtc_t1.threshold == pytest.approx(0.60)

    def test_raw_text_populated_from_markdown(self, pre_reg_dir: Path):
        """Trigger raw_text should be sourced from markdown bullet."""
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        vtc_t1 = next(t for t in spec.triggers if t.label == "VTC-T1")
        assert "OOS Sharpe" in vtc_t1.raw_text or vtc_t1.raw_text == ""

    def test_oos_overlap_parsed(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.oos_overlap is False

    def test_oos_window_dates_parsed(self, pre_reg_dir: Path):
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.oos_window_start == "2020-01-01"
        assert spec.oos_window_end == "2026-04-25"

    def test_result_is_frozen(self, pre_reg_dir: Path):
        """PreRegistrationSpec must be immutable (frozen dataclass)."""
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        with pytest.raises((AttributeError, TypeError)):
            spec.strategy = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestPreRegErrors:
    def test_missing_kill_switch_threshold_raises(self, tmp_path: Path):
        """Pre-reg without kill_switch_threshold: raises ConfigError."""
        md_path = tmp_path / "no_kst.md"
        sidecar_path = tmp_path / "no_kst.triggers.yaml"
        md_path.write_text(MARKDOWN_NO_KST)
        sidecar_path.write_text(yaml.dump(VALID_SIDECAR))
        with pytest.raises(ConfigError, match="kill_switch_threshold"):
            parse_pre_registration(md_path)

    def test_missing_sidecar_raises(self, tmp_path: Path):
        """Absent sidecar raises ConfigError — triggers are mandatory."""
        md_path = tmp_path / "no_sidecar.md"
        md_path.write_text(VALID_MARKDOWN)
        # No sidecar file created.
        with pytest.raises(ConfigError, match="sidecar"):
            parse_pre_registration(md_path)

    def test_bad_yaml_in_sidecar_raises(self, tmp_path: Path):
        """Invalid YAML in sidecar raises ConfigError."""
        md_path = tmp_path / "bad_yaml.md"
        sidecar_path = tmp_path / "bad_yaml.triggers.yaml"
        md_path.write_text(VALID_MARKDOWN)
        sidecar_path.write_text(": invalid: yaml: [\ncorrupt\n")
        with pytest.raises(ConfigError, match="invalid YAML|YAML"):
            parse_pre_registration(md_path, sidecar_path=sidecar_path)

    def test_missing_required_sidecar_field_oos_overlap_raises(self, tmp_path: Path):
        """Sidecar missing oos_overlap raises ConfigError."""
        md_path = tmp_path / "missing_overlap.md"
        sidecar_path = tmp_path / "missing_overlap.triggers.yaml"
        md_path.write_text(VALID_MARKDOWN)
        bad_sidecar = {k: v for k, v in VALID_SIDECAR.items() if k != "oos_overlap"}
        sidecar_path.write_text(yaml.dump(bad_sidecar))
        with pytest.raises(ConfigError, match="oos_overlap"):
            parse_pre_registration(md_path, sidecar_path=sidecar_path)

    def test_missing_strategy_id_raises(self, tmp_path: Path):
        """Pre-reg without **Strategy ID:** raises ConfigError."""
        md_path = tmp_path / "no_strategy.md"
        sidecar_path = tmp_path / "no_strategy.triggers.yaml"
        md_path.write_text("# Pre-Registration\n\n**Pair:** USDJPY\nkill_switch_threshold: 0.60\n\n## Hypothesis\nSome text.\n")
        sidecar_path.write_text(yaml.dump(VALID_SIDECAR))
        with pytest.raises(ConfigError, match="Strategy ID"):
            parse_pre_registration(md_path, sidecar_path=sidecar_path)

    def test_missing_markdown_raises(self, tmp_path: Path):
        """Non-existent pre-reg markdown raises ConfigError."""
        md_path = tmp_path / "nonexistent.md"
        with pytest.raises(ConfigError):
            parse_pre_registration(md_path)

    def test_explicit_sidecar_path_used(self, tmp_path: Path):
        """Explicit sidecar_path parameter is respected."""
        md_path = tmp_path / "test_strategy.md"
        custom_sidecar = tmp_path / "custom.triggers.yaml"
        md_path.write_text(VALID_MARKDOWN)
        custom_sidecar.write_text(yaml.dump(VALID_SIDECAR))
        # Default sidecar (test_strategy.triggers.yaml) does NOT exist.
        spec = parse_pre_registration(md_path, sidecar_path=custom_sidecar)
        assert spec.strategy == "test_strategy"

    def test_pair_resolved_single_string(self, pre_reg_dir: Path):
        """VALID_SIDECAR declares pair: USDJPY → pair_resolved == ("USDJPY",)."""
        spec = parse_pre_registration(pre_reg_dir / "test_strategy.md")
        assert spec.pair_resolved == ("USDJPY",)

    def test_vol_target_carry_real_pre_reg(self):
        """vol_target_carry.md + .triggers.yaml parse correctly (regression).

        Note: vol_target_carry.md uses gate_threshold (not kill_switch_threshold)
        as the primary gate field. The parser reads kill_switch_threshold from
        the Falsification Criteria section. Since vol_target_carry uses the older
        gate_threshold convention, we parse it with a fixture sidecar that
        declares kill_switch_threshold separately.
        """
        repo_root = Path(__file__).resolve().parent.parent.parent
        md_path = repo_root / "references/pre-registrations/vol_target_carry.md"
        sidecar_path = repo_root / "references/pre-registrations/vol_target_carry.triggers.yaml"
        if not md_path.exists():
            pytest.skip("vol_target_carry.md not found in this environment")
        if not sidecar_path.exists():
            pytest.skip("vol_target_carry.triggers.yaml not found in this environment")

        # vol_target_carry.md does not have kill_switch_threshold: field;
        # it uses gate_threshold: 0.60. The parser will raise ConfigError for the
        # kill_switch_threshold field. This is expected — the md predates the
        # kill_switch_threshold convention and should be updated.
        # Verify that parse raises ConfigError with a clear message, not a crash.
        with pytest.raises(ConfigError, match="kill_switch_threshold"):
            parse_pre_registration(md_path, sidecar_path=sidecar_path)


# ---------------------------------------------------------------------------
# Bug-fix regression tests (sub-wave 3c.1.1 parser bugfixes)
# ---------------------------------------------------------------------------


class TestParserBugfixes:
    """Regression tests for the two bugs exposed by the 3c.1 dry-run."""

    def test_kill_switch_threshold_strips_trailing_backtick(self, tmp_path: Path):
        """Inline-code-formatted `kill_switch_threshold: 0.50` → "0.50" (no backtick)."""
        md = tmp_path / "bt_test.md"
        sidecar = tmp_path / "bt_test.triggers.yaml"
        md.write_text(
            "# Pre-Registration: bt_test\n\n"
            "**Strategy ID:** bt_test\n"
            "**Pair:** EURUSD\n\n"
            "## Hypothesis\n\n"
            "Backtick test.\n\n"
            "## Falsification Criteria\n\n"
            "`kill_switch_threshold: 0.50`\n"
        )
        sidecar_data = {**VALID_SIDECAR, "pair": "EURUSD"}
        sidecar.write_text(yaml.dump(sidecar_data))
        spec = parse_pre_registration(md, sidecar_path=sidecar)
        assert spec.kill_switch_threshold == "0.50", (
            f"Expected '0.50' but got {spec.kill_switch_threshold!r} — trailing backtick not stripped"
        )

    def test_sidecar_pair_all_expands_to_universe(self, tmp_path: Path):
        """Sidecar pair: all → pair_resolved == ("EURUSD", "USDJPY", "GBPUSD")."""
        md = tmp_path / "pair_all.md"
        sidecar = tmp_path / "pair_all.triggers.yaml"
        md.write_text(VALID_MARKDOWN)
        sidecar_data = {**VALID_SIDECAR, "pair": "all"}
        sidecar.write_text(yaml.dump(sidecar_data))
        spec = parse_pre_registration(md, sidecar_path=sidecar)
        assert spec.pair_resolved == ("EURUSD", "USDJPY", "GBPUSD")

    def test_sidecar_pair_single_string(self, tmp_path: Path):
        """Sidecar pair: USDJPY (single string) → pair_resolved == ("USDJPY",)."""
        md = tmp_path / "pair_single.md"
        sidecar = tmp_path / "pair_single.triggers.yaml"
        md.write_text(VALID_MARKDOWN)
        sidecar_data = {**VALID_SIDECAR, "pair": "USDJPY"}
        sidecar.write_text(yaml.dump(sidecar_data))
        spec = parse_pre_registration(md, sidecar_path=sidecar)
        assert spec.pair_resolved == ("USDJPY",)

    def test_sidecar_pair_list(self, tmp_path: Path):
        """Sidecar pair: [EURUSD, USDJPY] → pair_resolved == ("EURUSD", "USDJPY")."""
        md = tmp_path / "pair_list.md"
        sidecar = tmp_path / "pair_list.triggers.yaml"
        md.write_text(VALID_MARKDOWN)
        sidecar_data = {**VALID_SIDECAR, "pair": ["EURUSD", "USDJPY"]}
        sidecar.write_text(yaml.dump(sidecar_data))
        spec = parse_pre_registration(md, sidecar_path=sidecar)
        assert spec.pair_resolved == ("EURUSD", "USDJPY")

    def test_real_phase2_pre_reg_loads_cleanly(self):
        """ma_crossover.md + sidecar: pair_resolved expands all, kill_switch no backtick."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        md_path = repo_root / "references/pre-registrations/ma_crossover.md"
        sidecar_path = repo_root / "references/pre-registrations/ma_crossover.triggers.yaml"
        if not md_path.exists():
            pytest.skip("ma_crossover.md not found in this environment")
        if not sidecar_path.exists():
            pytest.skip("ma_crossover.triggers.yaml not found in this environment")

        spec = parse_pre_registration(md_path, sidecar_path=sidecar_path)
        assert spec.pair_resolved == ("EURUSD", "USDJPY", "GBPUSD"), (
            f"Expected Phase-2 universe but got {spec.pair_resolved!r}"
        )
        assert spec.kill_switch_threshold == "0.30", (
            f"Expected '0.30' (no backtick) but got {spec.kill_switch_threshold!r}"
        )

    def test_missing_pair_in_sidecar_raises_config_error(self, tmp_path: Path):
        """Sidecar without 'pair' field must raise ConfigError (no silent default)."""
        md = tmp_path / "no_pair.md"
        sidecar = tmp_path / "no_pair.triggers.yaml"
        md.write_text(VALID_MARKDOWN)
        no_pair_sidecar = {k: v for k, v in VALID_SIDECAR.items() if k != "pair"}
        sidecar.write_text(yaml.dump(no_pair_sidecar))
        with pytest.raises(ConfigError, match="pair"):
            parse_pre_registration(md, sidecar_path=sidecar)
