"""Tests for harness/falsification_evaluator.py.

Coverage (≥8 tests):
1. Pass case (no triggers fire)
2. Single-fire R1 (OOS Sharpe below threshold)
3. Single-fire R2 (DSR below threshold)
4. Single-fire R3 (max_drawdown above threshold)
5. Single-fire R6 (n_trades below threshold)
6. Multi-fire: worst selected per priority (R2 > R3 > R1)
7. Strategy-specific T-N overrides R1 via kill_switch_threshold numeric
8. Missing required metric raises MissingMetricError
9. Missing nht-rubric.yaml raises ConfigError
10. R1 threshold override: strategy kill_switch_threshold more conservative than 0.30
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from forex_system.core.errors import ConfigError
from forex_system.harness.falsification_evaluator import (
    MissingMetricError,
    NhtRubric,
    evaluate,
)
from forex_system.harness.preregistration import FalsificationTrigger, PreRegistrationSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_rubric(tmp_path: Path, **overrides) -> NhtRubric:
    """Create an NhtRubric from a temp YAML file with standard test values."""
    defaults = {
        "r1_oos_sharpe_lt": 0.30,
        "r2_dsr_lt": 0.50,
        "r3_max_dd_gt": 0.25,
        "r5_permutation_pvalue_gt": 0.05,
        "r5_window_percentile_gt": 0.90,
        "r5_spa_pvalue_gt": 0.05,
        "r6_n_trades_lt": 30,
        "r6_n_oos_bars_lt": 252,
    }
    defaults.update(overrides)
    yaml_path = tmp_path / "nht-rubric.yaml"
    yaml_path.write_text(yaml.dump(defaults))
    return NhtRubric.load_from_yaml(yaml_path)


def _make_pre_reg(
    strategy: str = "test_strategy",
    pair: str = "USDJPY",
    pair_resolved: tuple[str, ...] = ("USDJPY",),
    kill_switch_threshold: str = "0.60",
    gate_threshold: float | None = 0.60,
    triggers: tuple[FalsificationTrigger, ...] = (),
    oos_overlap: bool = False,
    oos_window_start: str = "2020-01-01",
    oos_window_end: str = "2026-04-25",
    r5_active: bool = False,
) -> PreRegistrationSpec:
    return PreRegistrationSpec(
        strategy=strategy,
        pair=pair,
        pair_resolved=pair_resolved,
        hypothesis_summary="Test hypothesis.",
        kill_switch_threshold=kill_switch_threshold,
        gate_threshold=gate_threshold,
        triggers=triggers,
        oos_overlap=oos_overlap,
        oos_window_start=oos_window_start,
        oos_window_end=oos_window_end,
        r5_active=r5_active,
    )


def _make_trigger(
    label: str,
    metric: str,
    operator: str,
    threshold: float,
    raw_text: str = "",
) -> FalsificationTrigger:
    return FalsificationTrigger(
        label=label, metric=metric, operator=operator, threshold=threshold, raw_text=raw_text
    )


# Good metrics: all above NHT thresholds, all strategy triggers pass.
GOOD_METRICS: dict[str, float] = {
    "oos_sharpe": 0.76,
    "dsr": 0.92,
    "max_drawdown": 0.17,
    "n_trades": 45.0,
    "n_oos_bars": 1260.0,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPassCase:
    """Test 1: No triggers fire → verdict.passed == True."""

    def test_all_good_metrics_pass(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        verdict = evaluate(GOOD_METRICS, pre_reg, rubric)
        assert verdict.passed is True
        assert len(verdict.triggered) == 0
        assert verdict.rejection_reason is None
        assert verdict.falsification_criterion is None


class TestSingleFireR1:
    """Test 2: OOS Sharpe below NHT R1 threshold (0.30)."""

    def test_r1_fires_when_sharpe_low(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        # kill_switch_threshold = "0.30" matches rubric; R1 is the active gate.
        pre_reg = _make_pre_reg(kill_switch_threshold="0.30", gate_threshold=None)
        metrics = {**GOOD_METRICS, "oos_sharpe": 0.12}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R1-Sharpe" in verdict.triggered
        assert verdict.rejection_reason is not None
        assert "0.12" in verdict.rejection_reason or "oos_sharpe" in verdict.rejection_reason


class TestSingleFireR2:
    """Test 3: DSR below R2 threshold (0.50)."""

    def test_r2_fires_when_dsr_low(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        metrics = {**GOOD_METRICS, "dsr": 0.30}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R2-DSR" in verdict.triggered


class TestSingleFireR3:
    """Test 4: Max drawdown above R3 threshold (0.25)."""

    def test_r3_fires_when_max_dd_high(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        metrics = {**GOOD_METRICS, "max_drawdown": 0.30}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R3-MaxDD" in verdict.triggered


class TestSingleFireR6:
    """Test 5: n_trades below R6 threshold (30)."""

    def test_r6_fires_when_n_trades_low(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        metrics = {**GOOD_METRICS, "n_trades": 10.0}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R6-Trades" in verdict.triggered


class TestMultiFire:
    """Test 6: Multiple triggers fire; worst selected per priority (R2 > R3 > R1)."""

    def test_r2_is_falsification_criterion_over_r1(self, tmp_path: Path):
        """R2 (DSR) fires alongside R1 (Sharpe); R2 must be the criterion."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(kill_switch_threshold="0.30", gate_threshold=None)
        metrics = {
            **GOOD_METRICS,
            "oos_sharpe": 0.12,  # R1 fires
            "dsr": 0.20,         # R2 fires
            "max_drawdown": 0.30,  # R3 fires
        }
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert verdict.falsification_criterion == "R2-DSR", (
            f"R2 should be worst (highest priority), got: {verdict.falsification_criterion}"
        )
        assert "R1-Sharpe" in verdict.triggered
        assert "R2-DSR" in verdict.triggered
        assert "R3-MaxDD" in verdict.triggered

    def test_r3_is_falsification_criterion_over_r1_when_no_r2(self, tmp_path: Path):
        """R3 fires alongside R1; R3 must win over R1 (higher priority)."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(kill_switch_threshold="0.30", gate_threshold=None)
        metrics = {
            **GOOD_METRICS,
            "oos_sharpe": 0.12,  # R1 fires
            "max_drawdown": 0.30,  # R3 fires
        }
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.falsification_criterion == "R3-MaxDD", (
            f"R3 should beat R1 in priority, got: {verdict.falsification_criterion}"
        )


class TestStrategyTriggerOverride:
    """Test 7: Strategy-specific T-N trigger; kill_switch_threshold overrides R1."""

    def test_strategy_kst_overrides_r1_when_more_conservative(self, tmp_path: Path):
        """kill_switch_threshold=0.60 > rubric R1=0.30; effective threshold = 0.60."""
        rubric = _make_rubric(tmp_path)
        # kill_switch_threshold is 0.60 — more conservative than R1's 0.30.
        pre_reg = _make_pre_reg(kill_switch_threshold="0.60", gate_threshold=0.60)
        # oos_sharpe=0.45 > 0.30 (would pass R1 floor) but < 0.60 (fails override).
        metrics = {**GOOD_METRICS, "oos_sharpe": 0.45}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R1-Sharpe" in verdict.triggered

    def test_strategy_trigger_fires_independently_of_rubric(self, tmp_path: Path):
        """Strategy-specific trigger fires even when NHT rubric gates pass."""
        rubric = _make_rubric(tmp_path)
        strategy_trigger = _make_trigger(
            label="VTC-T1",
            metric="oos_sharpe",
            operator="<",
            threshold=0.90,  # Stricter than NHT R1 (0.30)
        )
        pre_reg = _make_pre_reg(
            kill_switch_threshold="VTC-T1",  # Label string — not a numeric override.
            triggers=(strategy_trigger,),
        )
        # oos_sharpe=0.50 passes NHT R1 (>0.30) but fails VTC-T1 (<0.90).
        metrics = {**GOOD_METRICS, "oos_sharpe": 0.50}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "VTC-T1" in verdict.triggered


class TestMissingMetric:
    """Test 8: Missing required metric raises MissingMetricError."""

    def test_missing_strategy_trigger_metric_raises(self, tmp_path: Path):
        """Strategy trigger references missing metric → MissingMetricError."""
        rubric = _make_rubric(tmp_path)
        trigger = _make_trigger(
            label="TEST-T1",
            metric="nonexistent_metric",
            operator="<",
            threshold=1.0,
        )
        pre_reg = _make_pre_reg(triggers=(trigger,))
        with pytest.raises(MissingMetricError, match="nonexistent_metric"):
            evaluate(GOOD_METRICS, pre_reg, rubric)


class TestMissingRubricFile:
    """Test 9: Missing nht-rubric.yaml raises ConfigError."""

    def test_absent_rubric_yaml_raises(self, tmp_path: Path):
        absent_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigError, match="nht-rubric.yaml|not found"):
            NhtRubric.load_from_yaml(absent_path)

    def test_bad_yaml_rubric_raises(self, tmp_path: Path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": broken: yaml: [\n")
        with pytest.raises(ConfigError, match="invalid"):
            NhtRubric.load_from_yaml(bad_yaml)

    def test_missing_field_in_rubric_raises(self, tmp_path: Path):
        """Rubric YAML missing r2_dsr_lt raises ConfigError."""
        partial = tmp_path / "partial.yaml"
        partial.write_text(yaml.dump({
            "r1_oos_sharpe_lt": 0.30,
            # r2_dsr_lt intentionally missing
            "r3_max_dd_gt": 0.25,
            "r5_permutation_pvalue_gt": 0.05,
            "r5_window_percentile_gt": 0.90,
            "r5_spa_pvalue_gt": 0.05,
            "r6_n_trades_lt": 30,
            "r6_n_oos_bars_lt": 252,
        }))
        with pytest.raises(ConfigError, match="r2_dsr_lt"):
            NhtRubric.load_from_yaml(partial)

    def test_missing_r5_window_field_in_rubric_raises(self, tmp_path: Path):
        """Rubric YAML missing r5_window_percentile_gt raises ConfigError."""
        partial = tmp_path / "partial2.yaml"
        partial.write_text(yaml.dump({
            "r1_oos_sharpe_lt": 0.30,
            "r2_dsr_lt": 0.50,
            "r3_max_dd_gt": 0.25,
            "r5_permutation_pvalue_gt": 0.05,
            # r5_window_percentile_gt intentionally missing
            "r5_spa_pvalue_gt": 0.05,
            "r6_n_trades_lt": 30,
            "r6_n_oos_bars_lt": 252,
        }))
        with pytest.raises(ConfigError, match="r5_window_percentile_gt"):
            NhtRubric.load_from_yaml(partial)

    def test_missing_r5_spa_field_in_rubric_raises(self, tmp_path: Path):
        """Rubric YAML missing r5_spa_pvalue_gt raises ConfigError."""
        partial = tmp_path / "partial3.yaml"
        partial.write_text(yaml.dump({
            "r1_oos_sharpe_lt": 0.30,
            "r2_dsr_lt": 0.50,
            "r3_max_dd_gt": 0.25,
            "r5_permutation_pvalue_gt": 0.05,
            "r5_window_percentile_gt": 0.90,
            # r5_spa_pvalue_gt intentionally missing
            "r6_n_trades_lt": 30,
            "r6_n_oos_bars_lt": 252,
        }))
        with pytest.raises(ConfigError, match="r5_spa_pvalue_gt"):
            NhtRubric.load_from_yaml(partial)


class TestPermutationAspirational:
    """R5 evaluated only when permutation_pvalue is present in metrics."""

    def test_r5_not_evaluated_when_metric_absent(self, tmp_path: Path):
        """R5 skipped when permutation_pvalue absent — does not block."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        # GOOD_METRICS does not contain permutation_pvalue.
        verdict = evaluate(GOOD_METRICS, pre_reg, rubric)
        assert verdict.passed is True  # R5 absent → no gate

    def test_r5_fires_when_pvalue_high(self, tmp_path: Path):
        """R5 fires when permutation_pvalue > 0.05 and metric is present."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        metrics = {**GOOD_METRICS, "permutation_pvalue": 0.20}  # > 0.05 → fails
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R5-Permutation" in verdict.triggered


class TestR5Active:
    """R5-active strategies: missing R5 fields raise MissingMetricError."""

    def test_r5_active_missing_permutation_pvalue_raises(self, tmp_path: Path):
        """R5-active strategy missing permutation_pvalue → MissingMetricError."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        # GOOD_METRICS has no R5 fields
        with pytest.raises(MissingMetricError, match="permutation_pvalue"):
            evaluate(GOOD_METRICS, pre_reg, rubric)

    def test_r5_active_missing_r5b_metric_raises(self, tmp_path: Path):
        """R5-active strategy missing r5b_window_percentile → MissingMetricError."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        metrics = {**GOOD_METRICS, "permutation_pvalue": 0.01}
        # r5b_window_percentile still missing
        with pytest.raises(MissingMetricError, match="r5b_window_percentile"):
            evaluate(metrics, pre_reg, rubric)

    def test_r5_active_missing_r5c_metric_raises(self, tmp_path: Path):
        """R5-active strategy missing r5c_spa_pvalue_consistent → MissingMetricError."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        metrics = {
            **GOOD_METRICS,
            "permutation_pvalue": 0.01,
            "r5b_window_percentile": 0.50,
        }
        with pytest.raises(MissingMetricError, match="r5c_spa_pvalue_consistent"):
            evaluate(metrics, pre_reg, rubric)

    def test_r5_active_all_fields_present_no_error(self, tmp_path: Path):
        """R5-active with all R5 fields present → evaluates normally."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        metrics = {
            **GOOD_METRICS,
            "permutation_pvalue": 0.01,       # passes R5a
            "r5b_window_percentile": 0.50,    # passes R5b (< 0.90)
            "r5c_spa_pvalue_consistent": 0.01, # passes R5c
        }
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is True

    def test_r5_active_fires_when_r5b_window_pct_high(self, tmp_path: Path):
        """R5b fires when r5b_window_percentile >= 0.90 for R5-active strategy."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        metrics = {
            **GOOD_METRICS,
            "permutation_pvalue": 0.01,
            "r5b_window_percentile": 0.95,    # fails R5b (>= 0.90)
            "r5c_spa_pvalue_consistent": 0.01,
        }
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R5b-WindowPct" in verdict.triggered

    def test_r5_active_fires_when_spa_pvalue_high(self, tmp_path: Path):
        """R5c fires when r5c_spa_pvalue_consistent > 0.05 for R5-active strategy."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=True)
        metrics = {
            **GOOD_METRICS,
            "permutation_pvalue": 0.01,
            "r5b_window_percentile": 0.50,
            "r5c_spa_pvalue_consistent": 0.20,  # fails R5c
        }
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R5c-SPA" in verdict.triggered

    def test_non_r5_active_r5_fields_optional(self, tmp_path: Path):
        """Non-R5-active strategy with R5 fields present: evaluated opportunistically."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=False)
        # permutation_pvalue failing — should still fire
        metrics = {**GOOD_METRICS, "permutation_pvalue": 0.20}
        verdict = evaluate(metrics, pre_reg, rubric)
        assert verdict.passed is False
        assert "R5-Permutation" in verdict.triggered

    def test_non_r5_active_missing_r5_fields_no_error(self, tmp_path: Path):
        """Non-R5-active strategy missing R5 fields: no error (backward compat)."""
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg(r5_active=False)
        # No R5 fields → should pass without raising
        verdict = evaluate(GOOD_METRICS, pre_reg, rubric)
        assert verdict.passed is True


class TestVerdictImmutability:
    """FalsificationVerdict must be frozen (immutable)."""

    def test_verdict_is_frozen(self, tmp_path: Path):
        rubric = _make_rubric(tmp_path)
        pre_reg = _make_pre_reg()
        verdict = evaluate(GOOD_METRICS, pre_reg, rubric)
        with pytest.raises((AttributeError, TypeError)):
            verdict.passed = False  # type: ignore[misc]
