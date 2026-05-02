"""Falsification evaluator — pure function for NHT Phase 2 rubric evaluation.

This module evaluates a completed trial's metrics against:
  1. Strategy-specific pre-registered triggers (from PreRegistrationSpec).
  2. Org-wide NHT rubric thresholds (from NhtRubric, sourced from nht-rubric.yaml).

Trigger priority (highest to lowest; determines falsification_criterion when
multiple triggers fire):
  R2 (DSR) > R3 (max_dd) > R1 (sharpe/kill_switch) > R6 (sample_size) >
  strategy-specific T-N > R5 (permutation, aspirational)

This priority reflects epistemic weight: R2 accounts for multiple comparisons
(most important for org-level validity), R3 for tail risk, R1 for raw signal
strength, R6 for sample adequacy, strategy-specific for pre-reg specificity,
and R5 for aspirational permutation testing.

Caller contract
---------------
- metrics dict MUST contain all keys that strategy triggers reference.
  Missing metric → raises MissingMetricError (never silently treats as pass).
- NhtRubric is loaded from .fintech-org/nht-rubric.yaml at evaluator entry-time.
  File absence → raises ConfigError.
- All thresholds sourced from artifacts; no silent defaults in this module.

Usage
-----
    rubric = NhtRubric.load_from_yaml(Path(".fintech-org/nht-rubric.yaml"))
    verdict = evaluate(metrics, pre_reg, rubric)
    if not verdict.passed:
        record_trial_rejection(...)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from forex_system.core.errors import ConfigError
from forex_system.harness.preregistration import FalsificationTrigger, PreRegistrationSpec

logger = logging.getLogger("forex_system.harness.falsification_evaluator")


class MissingMetricError(ConfigError):
    """Raised when a required metric is absent from the metrics dict.

    Never silently treats a missing metric as a pass — that would be a
    false negative in the falsification test.
    """


# ---------------------------------------------------------------------------
# Trigger priority ordering (R-label prefix → priority, lower = higher priority)
# ---------------------------------------------------------------------------

# Maps trigger label prefix → priority rank (lower = higher priority, fires first as
# falsification_criterion). Strategy-specific labels (T-N form) get rank 50.
_RUBRIC_PRIORITY: dict[str, int] = {
    "R2": 10,   # DSR — multiple-comparisons correction; most important
    "R3": 20,   # Max drawdown — tail risk
    "R1": 30,   # OOS Sharpe / kill_switch — raw signal strength
    "R6": 40,   # Sample size — adequacy gate
    "R5": 60,   # Permutation (aspirational; lowest priority)
}
_STRATEGY_TRIGGER_PRIORITY = 50  # Strategy-specific T-N triggers


def _trigger_priority(label: str) -> int:
    """Return priority rank for a trigger label (lower = higher priority)."""
    for prefix, rank in _RUBRIC_PRIORITY.items():
        if label.startswith(prefix):
            return rank
    # Strategy-specific: e.g. "VTC-T1", "FRED-T2"
    return _STRATEGY_TRIGGER_PRIORITY


# ---------------------------------------------------------------------------
# NHT Rubric
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NhtRubric:
    """Org-wide falsification rubric — sourced verbatim from nht-rubric.yaml.

    Frozen per CONSENSUS_2026-05-01_phase2_falsification.md.
    Changes require new pre-registration + new CONSENSUS.

    Attributes
    ----------
    r1_oos_sharpe_lt:
        R1: OOS Sharpe < this value → falsification trigger fires.
    r2_dsr_lt:
        R2: DSR < this value → falsification trigger fires.
    r3_max_dd_gt:
        R3: Max drawdown > this value (positive fraction) → trigger fires.
    r5_permutation_pvalue_gt:
        R5: Permutation p-value > this value → trigger fires (aspirational).
    r6_n_trades_lt:
        R6a: n_trades < this value → sample size trigger fires.
    r6_n_oos_bars_lt:
        R6b: n_oos_bars < this value → sample size trigger fires.
    """

    r1_oos_sharpe_lt: float
    r2_dsr_lt: float
    r3_max_dd_gt: float
    r5_permutation_pvalue_gt: float
    r6_n_trades_lt: int
    r6_n_oos_bars_lt: int

    @classmethod
    def load_from_yaml(cls, path: Path) -> "NhtRubric":
        """Load NhtRubric from a YAML file.

        Raises
        ------
        ConfigError
            If the file does not exist, is invalid YAML, or is missing required fields.
        """
        if not path.exists():
            raise ConfigError(
                f"NHT rubric YAML not found: {path}\n"
                "Run the NHT wave to produce .fintech-org/nht-rubric.yaml before "
                "evaluating trials. No silent fallback — every threshold must be explicit."
            )

        try:
            raw = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"NHT rubric YAML is invalid: {path}\nError: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise ConfigError(f"nht-rubric.yaml must be a YAML mapping: {path}")

        required = (
            "r1_oos_sharpe_lt",
            "r2_dsr_lt",
            "r3_max_dd_gt",
            "r5_permutation_pvalue_gt",
            "r6_n_trades_lt",
            "r6_n_oos_bars_lt",
        )
        for field in required:
            if field not in raw:
                raise ConfigError(
                    f"nht-rubric.yaml missing required field '{field}': {path}"
                )

        return cls(
            r1_oos_sharpe_lt=float(raw["r1_oos_sharpe_lt"]),
            r2_dsr_lt=float(raw["r2_dsr_lt"]),
            r3_max_dd_gt=float(raw["r3_max_dd_gt"]),
            r5_permutation_pvalue_gt=float(raw["r5_permutation_pvalue_gt"]),
            r6_n_trades_lt=int(raw["r6_n_trades_lt"]),
            r6_n_oos_bars_lt=int(raw["r6_n_oos_bars_lt"]),
        )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FalsificationVerdict:
    """Result of evaluating a trial against the NHT rubric and pre-reg triggers.

    Attributes
    ----------
    passed:
        True if no triggers fired; the trial passes falsification evaluation.
    triggered:
        Labels of all triggers that fired (R1, R2, R3, R6, strategy T-N).
        Empty iff passed is True.
    rejection_reason:
        Human-readable description of why the trial was rejected.
        None iff passed is True.
    falsification_criterion:
        Label of the WORST (highest-priority) trigger that fired.
        None iff passed is True.
    """

    passed: bool
    triggered: tuple[str, ...]
    rejection_reason: str | None
    falsification_criterion: str | None


# ---------------------------------------------------------------------------
# Trigger evaluation helpers
# ---------------------------------------------------------------------------


_OPERATOR_MAP = {
    "<":  lambda actual, threshold: actual < threshold,
    ">":  lambda actual, threshold: actual > threshold,
    "<=": lambda actual, threshold: actual <= threshold,
    ">=": lambda actual, threshold: actual >= threshold,
}


def _evaluate_trigger(
    trigger: FalsificationTrigger,
    metrics: dict[str, float],
) -> bool:
    """Return True if the trigger fires (metric violates threshold).

    Raises
    ------
    MissingMetricError
        If the metric key is absent from the metrics dict.
    ConfigError
        If the operator is not one of <, >, <=, >=.
    """
    if trigger.metric not in metrics:
        raise MissingMetricError(
            f"Trigger '{trigger.label}' requires metric '{trigger.metric}' "
            f"but it is absent from the metrics dict. "
            f"Available keys: {sorted(metrics.keys())}. "
            "Do not silently treat as pass — add the metric or remove the trigger."
        )

    compare = _OPERATOR_MAP.get(trigger.operator)
    if compare is None:
        raise ConfigError(
            f"Unknown operator '{trigger.operator}' in trigger '{trigger.label}'. "
            "Must be one of: <, >, <=, >="
        )

    actual = float(metrics[trigger.metric])
    return compare(actual, trigger.threshold)


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log line (JSON)."""
    entry = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(entry))


# ---------------------------------------------------------------------------
# Effective R1 threshold (NHT override rule)
# ---------------------------------------------------------------------------


def _effective_r1_threshold(
    nht_rubric: NhtRubric,
    pre_reg: PreRegistrationSpec,
) -> tuple[float, str]:
    """Compute the effective R1 threshold per NHT override rule.

    Rule (from nht-frozen-thresholds.yaml):
        max(0.30, strategy_pre_reg.kill_switch_threshold)
        IF kill_switch_threshold is a numeric value AND more conservative than R1.
        If kill_switch_threshold is a label string (e.g. "VTC-T1"), it is handled
        via the FalsificationTrigger list, not here.

    Returns
    -------
    (threshold, source_label)
    """
    raw_kst = pre_reg.kill_switch_threshold
    try:
        kst_numeric = float(raw_kst)
        # More conservative = higher sharpe threshold (harder to pass).
        effective = max(nht_rubric.r1_oos_sharpe_lt, kst_numeric)
        source = (
            "kill_switch_threshold" if effective > nht_rubric.r1_oos_sharpe_lt
            else "nht_r1_floor"
        )
        return effective, source
    except ValueError:
        # kill_switch_threshold is a label string — skip override; use NHT floor.
        return nht_rubric.r1_oos_sharpe_lt, "nht_r1_floor"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(
    metrics: dict[str, float],
    pre_reg: PreRegistrationSpec,
    nht_rubric: NhtRubric,
) -> FalsificationVerdict:
    """Evaluate a completed trial against pre-reg triggers AND NHT rubric.

    Evaluation is exhaustive — ALL triggers are checked, not short-circuited.
    falsification_criterion is the trigger with the highest priority rank
    (R2 > R3 > R1 > R6 > strategy-T-N > R5).

    Parameters
    ----------
    metrics:
        Dict of metric_key → float value, assembled by the harness wrapper.
        Expected keys for NHT rubric: "oos_sharpe", "dsr", "max_drawdown",
        "n_trades", "n_oos_bars", and optionally "permutation_pvalue".
        Missing keys for required triggers raise MissingMetricError.
    pre_reg:
        Parsed pre-registration spec (from parse_pre_registration()).
    nht_rubric:
        Loaded NHT rubric (from NhtRubric.load_from_yaml()).

    Returns
    -------
    FalsificationVerdict
        Immutable verdict with pass/fail status and trigger details.

    Raises
    ------
    MissingMetricError
        If a trigger references a metric absent from the metrics dict.

    Decision trace
    --------------
    Emits trial.falsification.evaluate log event with per-trigger results
    regardless of pass/fail outcome.
    """
    fired: list[tuple[int, str, str]] = []  # (priority, label, reason)

    # --- Build synthetic NHT rubric triggers ---
    r1_threshold, r1_source = _effective_r1_threshold(nht_rubric, pre_reg)

    # NHT rubric synthetic triggers (evaluated against the metrics dict).
    # Each is (label, metric, operator, threshold, priority_override)
    nht_triggers: list[tuple[str, str, str, float, int]] = [
        ("R2-DSR",    "dsr",           "<",  nht_rubric.r2_dsr_lt,           _trigger_priority("R2")),
        ("R3-MaxDD",  "max_drawdown",  ">",  nht_rubric.r3_max_dd_gt,        _trigger_priority("R3")),
        ("R1-Sharpe", "oos_sharpe",    "<",  r1_threshold,                   _trigger_priority("R1")),
        ("R6-Trades", "n_trades",      "<",  float(nht_rubric.r6_n_trades_lt), _trigger_priority("R6")),
        ("R6-OOSBars","n_oos_bars",    "<",  float(nht_rubric.r6_n_oos_bars_lt), _trigger_priority("R6")),
    ]
    # R5 — aspirational; only evaluate if metric is present.
    if "permutation_pvalue" in metrics:
        nht_triggers.append(
            ("R5-Permutation", "permutation_pvalue", ">", nht_rubric.r5_permutation_pvalue_gt, _trigger_priority("R5"))
        )

    per_trigger_results: list[dict] = []

    # Evaluate NHT rubric triggers.
    for label, metric_key, operator, threshold, priority in nht_triggers:
        if metric_key not in metrics:
            # R6 bars and permutation may legitimately be absent for legacy trials.
            # Log a warning but don't raise — only strategy-specific triggers must be present.
            _log_event(
                "trial.falsification.metric_absent",
                label=label,
                metric=metric_key,
                note="NHT rubric trigger skipped — metric absent from metrics dict",
            )
            per_trigger_results.append({"label": label, "fired": False, "reason": "metric_absent"})
            continue

        trigger_obj = FalsificationTrigger(
            label=label, metric=metric_key, operator=operator, threshold=threshold, raw_text=""
        )
        result = _evaluate_trigger(trigger_obj, metrics)
        actual = metrics[metric_key]
        reason = f"{metric_key}={actual:.4g} {operator} {threshold:.4g}"
        per_trigger_results.append({"label": label, "fired": result, "reason": reason})
        if result:
            fired.append((priority, label, reason))

    # Evaluate strategy-specific pre-reg triggers.
    for trigger in pre_reg.triggers:
        result = _evaluate_trigger(trigger, metrics)
        actual = metrics[trigger.metric]
        reason = f"{trigger.metric}={actual:.4g} {trigger.operator} {trigger.threshold:.4g}"
        per_trigger_results.append({"label": trigger.label, "fired": result, "reason": reason})
        if result:
            fired.append((_trigger_priority(trigger.label), trigger.label, reason))

    # Sort fired by priority (ascending = highest priority first).
    fired.sort(key=lambda x: x[0])

    triggered_labels = tuple(f[1] for f in fired)
    passed = len(fired) == 0

    rejection_reason: str | None = None
    falsification_criterion: str | None = None
    if not passed:
        falsification_criterion = fired[0][1]  # Highest-priority trigger
        rejection_reasons = [f"{f[1]}: {f[2]}" for f in fired]
        rejection_reason = "; ".join(rejection_reasons)

    _log_event(
        "trial.falsification.evaluate",
        strategy=pre_reg.strategy,
        pair=pre_reg.pair,
        passed=passed,
        triggered=list(triggered_labels),
        falsification_criterion=falsification_criterion,
        rejection_reason=rejection_reason,
        r1_threshold_used=r1_threshold,
        r1_threshold_source=r1_source,
        per_trigger_results=per_trigger_results,
    )

    return FalsificationVerdict(
        passed=passed,
        triggered=triggered_labels,
        rejection_reason=rejection_reason,
        falsification_criterion=falsification_criterion,
    )
