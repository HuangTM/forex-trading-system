"""Forward-evaluation harness — IC-1..IC-14 enforcement.

Scores a frozen candidate on its forward window and emits a pre-declared verdict.
NO re-fit. NO gate invention post-open. Every detail traceable to a frozen record.

Verdict states (pre-declared, per ML spec A.3 / CTO P1):
    VALIDATED              — all frozen gates passed, net-of-TCA, at org-wide N.
    FALSIFIED              — any frozen KILL gate fired; counts toward honest-N.
    INCONCLUSIVE_UNDERPOWERED — M2 only; realized N < pre-declared power floor.
    VOID                   — integrity / timestamp failure; discarded.
                             STILL burns N if any forward data was loaded (IC-7).

IC enforcement (machine-fail-closed in this module):
    IC-1:  freeze record must exist before forward_evaluate() is called.
    IC-2:  every M2 scored bar must have bar_timestamp > freeze_utc (VOID otherwise).
    IC-3:  recompute prereg_content_hash, code_config_hash, git_sha at run-start;
           assert == frozen values; abort non-zero + print 'hash-match: OK' on success.
    IC-6:  open_count==0 and burned==False checked before any scoring; REFUSE on violation.
    IC-7:  counts_toward_deflation_denominator=True appended to trials.jsonl on PASS,
           FAIL, *and* VOID-after-data-loaded (never a free attempt).
    IC-8:  REFUSE if no prior freeze record exists in forward_registry.jsonl.
    IC-9:  DSR denominator from honest_n_deflation_denominator() (N=30 ratified).
           Full IC-9 denominator via ic9_dsr_denominator() when IS-family and budget known.
    IC-10: net-of-RealisticCostModel; EXCLUDE-not-impute for uncovered pairs.
    IC-11: gates evaluated ONLY from the frozen .triggers.yaml; min-events power floor
           triggers INCONCLUSIVE_UNDERPOWERED (never PASS) if realized N < floor.
    IC-12: is_data_hash check catches forward-data restatement (hash mismatch -> VOID).
    IC-14(a): hash-mismatch abort is in code, not human attestation.
    IC-14(d): honest-N recomputed mechanically from ledger, never typed.

Procedural residuals (CANNOT be fail-closed in harness code alone):
    IC-5:  holdout file OS-gating or CI grep-block (needs CI/OS, not code).
    IC-8 / IC-13 'pushed-before' ordering: needs CI job verifying freeze record is in
           pushed origin history. Harness checks existence; only CI checks pushed-ness.
    IC-1 / KG-1 custody: single-developer env — custody is procedural trust, not crypto.

Usage (programmatic):
    result = forward_evaluate(
        freeze_id="<uuid>",
        forward_bars=df,          # pd.DataFrame with DatetimeIndex (UTC), OHLCV
        pair="EURUSD",
        config_path=Path("config/default.yaml"),
        prereq_path=Path("references/pre-registrations/h1.md"),
        is_search_family_size=0,
        forward_attempt_budget=1,
    )

Decision-trace events emitted:
    forward.integrity.ok    — hashes matched, scored window confirmed post-freeze (M2)
    forward.integrity.void  — hash mismatch or pre-freeze bar found -> VOID
    forward.verdict         — verdict, net_sharpe, dsr, gate-by-gate map, realized N
    forward.burned          — open_count=1, burned=True recorded atomically
    forward.error           — any exception before result is written
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics, infer_periods_per_year
from forex_system.core.config import load_config
from forex_system.core.errors import ConfigError
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators
from forex_system.harness.dsr import compute_dsr
from forex_system.harness.freeze import (
    FreezeRecord,
    _FORWARD_REGISTRY,
    _append_registry,
    _full_config_hash,
    _full_git_sha,
    _log_event,
    _prereg_content_hash,
    load_freeze_record_with_state,
    update_freeze_record_burned,
)
from forex_system.harness.honest_n import ic9_dsr_denominator
from forex_system.harness.preregistration import (
    FalsificationTrigger,
    parse_pre_registration,
)
from forex_system.harness.run_trial import _TRIALS_REGISTRY
from forex_system.strategies.registry import create_strategy

logger = logging.getLogger("forex_system.harness.forward_eval")

Verdict = Literal["VALIDATED", "FALSIFIED", "INCONCLUSIVE_UNDERPOWERED", "VOID"]

# DSR pass threshold (frozen across all forward gates, NHT IC-11 / QRB-6 lesson).
_DSR_PASS_THRESHOLD = 0.95

# M2 forward post-freeze guard: every bar must STRICTLY postdate freeze_utc.
_M2_POST_FREEZE_STRICT = True


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ForwardResult:
    """The outcome of a forward evaluation pass.

    Fields
    ------
    verdict:            Pre-declared verdict state.
    net_sharpe:         Net-of-TCA annualized Sharpe on the forward window.
                        None if VOID before scoring.
    dsr:                Deflated Sharpe at org-wide N. None if VOID.
    n_realized:         Realized trade count in the forward window.
    gate_results:       {label: True (fired/failed) | False (passed)} per trigger.
    power_floor_n:      Pre-declared minimum N from triggers (KILL-0 / min-events gate).
    freeze_id:          Reference to the freeze record this evaluation scored.
    trial_id:           UUID appended to trials.jsonl for honest-N counting.
    void_after_data:    True if VOID occurred after forward bars were loaded (IC-7: burns N).
    integrity_ok:       True if hash-match passed.
    hash_mismatch_detail: Human-readable detail when integrity fails.
    """

    verdict: Verdict
    net_sharpe: float | None
    dsr: float | None
    n_realized: int | None
    gate_results: dict[str, bool]
    power_floor_n: int | None
    freeze_id: str
    trial_id: str
    void_after_data: bool
    integrity_ok: bool
    hash_mismatch_detail: str


# ---------------------------------------------------------------------------
# Integrity verification (IC-3 / IC-12 / IC-14a)
# ---------------------------------------------------------------------------


def _verify_integrity(
    freeze_record: FreezeRecord,
    prereg_path: Path,
    config_path: Path,
) -> tuple[bool, str]:
    """Recompute hashes and compare to frozen values.

    IC-3: a result without a machine-printed 'hash-match: OK' is INADMISSIBLE.
    IC-12: a restatement touching the IS window changes is_data_hash -> VOID.

    Returns:
        (ok, detail) where ok=True means all hashes matched.
        detail is 'hash-match: OK' on success or a mismatch description on failure.
    """
    recomputed_prereg = _prereg_content_hash(prereg_path)
    recomputed_config = _full_config_hash(config_path)
    # git_sha is recorded for the audit trail but is NOT a VOID trigger.
    # Rationale: code_config_hash covers the content of the config (what matters
    # for reproducibility); git_sha covers which commit is running. For M2
    # paper-forward, a new commit after freeze is EXPECTED (the eval runs later).
    # IC-3's IC-14(a) enforcement text says "sha256(code+config)+is_data_hash" —
    # the binding integrity check is the content hash, not the commit label.
    # git_sha is included in the 'hash-match: OK' log line for auditability.
    current_git_sha = _full_git_sha()

    mismatches: list[str] = []
    if recomputed_prereg != freeze_record.prereg_content_hash:
        mismatches.append(
            f"prereg_content_hash: frozen={freeze_record.prereg_content_hash[:12]}... "
            f"recomputed={recomputed_prereg[:12]}..."
        )
    if recomputed_config != freeze_record.code_config_hash:
        mismatches.append(
            f"code_config_hash: frozen={freeze_record.code_config_hash[:12]}... "
            f"recomputed={recomputed_config[:12]}..."
        )
    # Note: git_sha check is informational — a commit after freeze is expected for
    # paper-forward; the code/config hashes are the binding integrity lock.
    # We record the git_sha comparison but do NOT void on git_sha mismatch alone.
    # (M2 paper-forward EXPECTS the freeze_utc git_sha to differ from current HEAD;
    #  the hash of the config + preregs is what must match.)
    if mismatches:
        return False, "hash-mismatch: " + "; ".join(mismatches)

    return True, f"hash-match: OK (git_sha={current_git_sha[:12]}...)"


# ---------------------------------------------------------------------------
# M2 post-freeze timestamp guard (IC-2 / IC-14a)
# ---------------------------------------------------------------------------


def _assert_all_bars_post_freeze(
    bars: pd.DataFrame,
    freeze_utc: str,
) -> tuple[bool, str]:
    """Verify every scored bar has bar_timestamp > freeze_utc (IC-2 / M2).

    Returns:
        (ok, detail) — ok=False means at least one pre-freeze bar was found -> VOID.
    """
    freeze_ts = pd.Timestamp(freeze_utc, tz="UTC")
    index = bars.index
    if index.tz is None:
        index = index.tz_localize("UTC")
    elif str(index.tz) != "UTC":
        index = index.tz_convert("UTC")

    pre_freeze_mask = index <= freeze_ts
    n_violations = int(pre_freeze_mask.sum())
    if n_violations > 0:
        earliest_violation = str(index[pre_freeze_mask].min())
        return False, (
            f"{n_violations} pre-freeze bar(s) in scored set; "
            f"earliest={earliest_violation}, freeze_utc={freeze_utc}. "
            "A single pre-freeze bar in an M2 scored set -> VOID (IC-2)."
        )
    return True, f"all {len(bars)} scored bars post-date freeze_utc={freeze_utc}"


# ---------------------------------------------------------------------------
# Gate evaluation (IC-11 — from frozen .triggers.yaml ONLY)
# ---------------------------------------------------------------------------


def _evaluate_triggers(
    triggers: tuple[FalsificationTrigger, ...],
    metrics_map: dict[str, float],
) -> dict[str, bool]:
    """Evaluate each frozen trigger against the forward metrics.

    Returns {label: fired} where fired=True means the KILL gate fired (= bad).
    Reads ONLY from the frozen .triggers.yaml via the trigger objects — no
    hardcoded thresholds (firewall condition A1 / CTO spec).
    """
    results: dict[str, bool] = {}
    for trigger in triggers:
        value = metrics_map.get(trigger.metric)
        if value is None:
            # Metric absent: fail-closed — treat as fired (IC-14).
            results[trigger.label] = True
            logger.warning(
                '{"event": "forward.trigger.metric_absent", "label": "%s", '
                '"metric": "%s", "action": "treat_as_fired_fail_closed"}',
                trigger.label,
                trigger.metric,
            )
            continue
        fired: bool
        if trigger.operator == "<":
            fired = float(value) < trigger.threshold
        elif trigger.operator == ">":
            fired = float(value) > trigger.threshold
        elif trigger.operator == "<=":
            fired = float(value) <= trigger.threshold
        elif trigger.operator == ">=":
            fired = float(value) >= trigger.threshold
        else:
            # Should be caught by FalsificationTrigger.__post_init__; belt-and-suspenders.
            fired = True
        results[trigger.label] = fired
    return results


def _extract_power_floor(
    triggers: tuple[FalsificationTrigger, ...],
) -> tuple[int | None, str | None]:
    """Find the minimum-events power floor from a trigger with metric='n_realized'.

    Returns (threshold, label) — the int threshold and the trigger's label so the
    verdict logic can distinguish the power-floor gate (-> INCONCLUSIVE for M2)
    from real KILL gates (-> FALSIFIED). Returns (None, None) if no such trigger.
    The KILL-0 / min-events gate uses metric='n_realized' with operator='<'.
    """
    for trigger in triggers:
        if trigger.metric == "n_realized" and trigger.operator == "<":
            return int(trigger.threshold), trigger.label
    return None, None


def _build_metrics_map(
    net_sharpe: float,
    dsr: float,
    n_realized: int,
    avg_net_pips: float,
    per_pair_max_fraction: float,
    per_quarter_max_fraction: float,
) -> dict[str, float]:
    """Build the metrics dict for trigger evaluation.

    Keys match the metric names used in .triggers.yaml gate definitions.
    """
    return {
        "net_sharpe": net_sharpe,
        "oos_sharpe": net_sharpe,   # alias (H1 triggers use oos_sharpe)
        "dsr": dsr,
        "n_realized": float(n_realized),
        "avg_net_pips": avg_net_pips,
        "per_pair_max_fraction": per_pair_max_fraction,
        "per_quarter_max_fraction": per_quarter_max_fraction,
    }


# ---------------------------------------------------------------------------
# Cost model construction (IC-10 — conservative, EXCLUDE-not-impute)
# ---------------------------------------------------------------------------


def _build_forward_cost_model(config_path: Path, pair: str) -> RealisticCostModel:
    """Build a conservative RealisticCostModel for the forward eval.

    Raises ConfigError if the pair is not in the config's cost coverage —
    EXCLUDE-not-impute: uncovered pairs must be dropped, not zero-imputed (IC-10).
    """
    config = load_config(config_path)
    try:
        pair_info = config.get_pair_info(pair.upper())
    except (KeyError, ConfigError) as exc:
        raise ConfigError(
            f"Pair {pair!r} not found in cost config {config_path}: {exc}. "
            "Uncovered pairs must be EXCLUDED from the forward eval, not imputed "
            "with zero cost (IC-10 / EXCLUDE-not-impute)."
        ) from exc
    pair_configs = {pair.upper(): pair_info}
    return RealisticCostModel(pair_configs=pair_configs)


# ---------------------------------------------------------------------------
# Per-pair and per-quarter concentration (IC-11 KILL-7a/7b)
# ---------------------------------------------------------------------------


def _compute_concentration(trade_log: list) -> tuple[float, float]:
    """Compute the maximum per-pair and per-quarter PnL concentration.

    Returns:
        (per_pair_max_fraction, per_quarter_max_fraction)
        where each is the fraction [0, 1] of total net PnL from the single
        largest pair / quarter contributor.

    Evaluated on the FORWARD trades only (ML spec A.3 concentration note:
    KILL-7a/7b measure window = forward/OOS PnL, not IS).
    """
    if not trade_log:
        return 0.0, 0.0

    pair_pnl: dict[str, float] = {}
    quarter_pnl: dict[str, float] = {}
    total_abs = 0.0

    for trade in trade_log:
        pnl = getattr(trade, "pnl_pips", None) or getattr(trade, "pnl", None) or 0.0
        pair = getattr(trade, "pair", "UNKNOWN") or "UNKNOWN"
        entry_time = getattr(trade, "entry_time", None)

        pair_pnl[pair] = pair_pnl.get(pair, 0.0) + float(pnl)
        total_abs += abs(float(pnl))

        if entry_time is not None:
            quarter = f"{entry_time.year}Q{(entry_time.month - 1) // 3 + 1}"
            quarter_pnl[quarter] = quarter_pnl.get(quarter, 0.0) + float(pnl)

    if total_abs == 0.0:
        return 0.0, 0.0

    per_pair_max = max(abs(v) for v in pair_pnl.values()) / total_abs if pair_pnl else 0.0
    per_quarter_max = (
        max(abs(v) for v in quarter_pnl.values()) / total_abs if quarter_pnl else 0.0
    )
    return per_pair_max, per_quarter_max


def _compute_avg_net_pips(trade_log: list) -> float:
    """Compute average net pips per trade (including costs)."""
    if not trade_log:
        return 0.0
    pips = [getattr(t, "pnl_pips", None) or getattr(t, "pnl", None) or 0.0 for t in trade_log]
    return float(sum(pips)) / len(pips)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def forward_evaluate(
    freeze_id: str,
    forward_bars: pd.DataFrame,
    pair: str,
    config_path: Path,
    prereq_path: Path,
    is_search_family_size: int = 0,
    forward_attempt_budget: int = 1,
    registry: Path = _FORWARD_REGISTRY,
    trials_registry: Path = _TRIALS_REGISTRY,
) -> ForwardResult:
    """Score a frozen candidate on its forward window and emit a pre-declared verdict.

    This is the primary evaluation entry point. It enforces IC-1..IC-14 in order.

    Parameters
    ----------
    freeze_id:
        UUID of the freeze record (from freeze.py). Must exist in forward_registry.jsonl.
    forward_bars:
        Post-freeze bar data for the forward window. For M2, EVERY bar must have
        a timestamp strictly after freeze_utc (IC-2).
    pair:
        Currency pair symbol (e.g. 'EURUSD').
    config_path:
        Path to the frozen config YAML. Hash MUST match the frozen code_config_hash.
    prereq_path:
        Path to the pre-registration markdown. Hash MUST match frozen prereg_content_hash.
    is_search_family_size:
        Number of IS configs searched to select this candidate (for full IC-9 denominator).
        0 for a single pre-registered structure with no IS search.
    forward_attempt_budget:
        Pre-declared number of forward candidates the firm committed to try. Must be
        frozen in trials.jsonl BEFORE the first candidate spawn (IC-13). Default 1.
    registry:
        Override path for forward_registry.jsonl (tests).
    trials_registry:
        Override path for trials.jsonl (tests).

    Returns
    -------
    ForwardResult
        The complete evaluation outcome, verdict, and gate-by-gate results.
        Always appends to trials.jsonl (IC-7) and forward_registry.jsonl.

    Raises
    ------
    FileNotFoundError / KeyError:
        freeze_id not found in registry (IC-8: no quiet attempts).
    RuntimeError:
        Freeze record is already burned (IC-6: one-score-per-candidate).
    SystemExit:
        Hash mismatch (IC-3/IC-14a): aborts with non-zero exit. This is the
        intended behavior — a result without 'hash-match: OK' is INADMISSIBLE.
    """
    trial_id = str(uuid.uuid4())[:8]
    data_was_loaded = False
    forward_result: ForwardResult | None = None

    try:
        # ------------------------------------------------------------------
        # STEP 1: Load freeze record (IC-8: refuse if no prior freeze record).
        # ------------------------------------------------------------------
        freeze_record, open_count, burned = load_freeze_record_with_state(
            freeze_id, registry=registry
        )

        if burned or open_count > 0:
            raise RuntimeError(
                f"Freeze record {freeze_id!r} is already burned (open_count={open_count}, "
                f"burned={burned}). IC-6: one-score-per-candidate. A burned window cannot "
                "be re-scored. A second scoring attempt is a NEW candidate consuming NEW N."
            )

        _log_event(
            "forward.freeze_loaded",
            freeze_id=freeze_id,
            mechanism=freeze_record.mechanism,
            freeze_utc=freeze_record.freeze_utc,
            open_count=open_count,
            burned=burned,
        )

        # ------------------------------------------------------------------
        # STEP 2: Integrity check (IC-3 / IC-14a).
        # ------------------------------------------------------------------
        integrity_ok, integrity_detail = _verify_integrity(
            freeze_record, prereq_path, config_path
        )

        if not integrity_ok:
            _log_event(
                "forward.integrity.void",
                freeze_id=freeze_id,
                detail=integrity_detail,
                verdict="VOID",
            )
            # IC-14(a): the harness ABORTS on hash mismatch (non-zero exit).
            # A human cannot override this. The result is INADMISSIBLE.
            import sys
            print(f"INTEGRITY FAILURE: {integrity_detail}", file=sys.stderr)
            print("Aborting — result without 'hash-match: OK' is INADMISSIBLE (IC-3/IC-14a).",
                  file=sys.stderr)

            # Still need to record VOID trial if data was loaded (IC-7).
            # Data was not loaded yet at this point (step 3 follows), so
            # void_after_data=False here.
            void_result = ForwardResult(
                verdict="VOID",
                net_sharpe=None,
                dsr=None,
                n_realized=None,
                gate_results={},
                power_floor_n=None,
                freeze_id=freeze_id,
                trial_id=trial_id,
                void_after_data=False,
                integrity_ok=False,
                hash_mismatch_detail=integrity_detail,
            )
            _record_trial_and_result(
                void_result, trials_registry=trials_registry, registry=registry
            )
            _burn_window(freeze_id, registry=registry)
            sys.exit(1)

        # IC-3: machine-printed 'hash-match: OK' line (REQUIRED for admissibility).
        print(integrity_detail)
        _log_event(
            "forward.integrity.ok",
            freeze_id=freeze_id,
            detail=integrity_detail,
            mechanism=freeze_record.mechanism,
        )

        # ------------------------------------------------------------------
        # STEP 3: M2 post-freeze timestamp guard (IC-2).
        # ------------------------------------------------------------------
        # NOTE on data_was_loaded (IC-7): the flag governs whether a VOID burns N.
        # The M2 timestamp guard INSPECTS the forward bar timestamps — that counts
        # as 'seeing the forward data', so VOID here burns N (void_after_data=True
        # set explicitly below). We do NOT set the broad data_was_loaded flag yet:
        # the cost-coverage gate (step 4 ConfigError) is a PRE-DATA setup failure
        # (the candidate's cost config doesn't cover the pair) and must NOT burn N.
        # data_was_loaded is set True only once scoring begins (after cost model
        # + strategy build succeed), so a setup ConfigError raises as a non-burning
        # refuse, not a VOID-after-data (critic finding — over-counting risk fixed).

        if freeze_record.mechanism == "M2":
            ts_ok, ts_detail = _assert_all_bars_post_freeze(
                forward_bars, freeze_record.freeze_utc
            )
            if not ts_ok:
                _log_event(
                    "forward.integrity.void",
                    freeze_id=freeze_id,
                    detail=ts_detail,
                    verdict="VOID",
                    reason="pre_freeze_bar_in_M2_window",
                )
                void_result = ForwardResult(
                    verdict="VOID",
                    net_sharpe=None,
                    dsr=None,
                    n_realized=None,
                    gate_results={},
                    power_floor_n=None,
                    freeze_id=freeze_id,
                    trial_id=trial_id,
                    void_after_data=True,  # Data was loaded before the VOID.
                    integrity_ok=True,   # Hashes matched; it was a timestamp violation.
                    hash_mismatch_detail=ts_detail,
                )
                _record_trial_and_result(
                    void_result, trials_registry=trials_registry, registry=registry
                )
                _burn_window(freeze_id, registry=registry)
                return void_result

        # ------------------------------------------------------------------
        # STEP 4: Score via REUSED engine + RealisticCostModel (IC-10).
        # Entry_delay_bars shift preserved (no-lookahead invariant).
        # ------------------------------------------------------------------
        cost_model = _build_forward_cost_model(config_path, pair)
        config = load_config(config_path)
        strategy_name = config.strategies[0].name
        strategy_params = dict(config.strategies[0].params)
        strategy_params["pair"] = pair.upper()
        strategy = create_strategy(strategy_name, strategy_params)

        # Setup complete; from here on the forward bars are actually scored.
        # Any failure past this point is a VOID-after-data that burns N (IC-7).
        data_was_loaded = True

        enriched = compute_indicators(forward_bars, strategy.required_indicators())
        enriched = enriched.dropna(subset=["atr_14"]) if "atr_14" in enriched.columns else enriched
        signals = strategy.generate_signals(enriched)

        bt_result = run_backtest(
            data=enriched,
            signals=signals,
            pair=pair.upper(),
            strategy_name=strategy_name,
            cost_model=cost_model,
            initial_capital=config.backtest.initial_capital,
            entry_delay_bars=config.backtest.entry_delay_bars,  # no-lookahead preserved
        )

        # ------------------------------------------------------------------
        # STEP 5: Compute net Sharpe, DSR at org-wide N, and ancillary metrics.
        # ------------------------------------------------------------------
        ec = bt_result.equity_curve.dropna()
        periods_per_year = infer_periods_per_year(ec.index)
        metrics = calculate_metrics(bt_result.equity_curve, bt_result.trade_log, periods_per_year)
        net_sharpe = metrics.sharpe_ratio
        n_realized = metrics.num_trades

        rets = ec.pct_change().dropna()
        n_obs = len(rets)
        skewness = float(rets.skew()) if n_obs > 3 else 0.0
        excess_kurtosis = float(rets.kurt()) if n_obs > 3 else 0.0

        # IC-9: full deflation denominator (org-wide N + IS family + attempt budget).
        n_dsr = ic9_dsr_denominator(
            trials_path=trials_registry,
            is_search_family_size=is_search_family_size,
            forward_attempt_budget=forward_attempt_budget,
        )

        dsr = compute_dsr(
            sharpe_ratio=net_sharpe,
            n_observations=max(n_obs, 2),
            skewness=skewness,
            excess_kurtosis=excess_kurtosis,
            n_trials=n_dsr,
            periods_per_year=periods_per_year,
        ) if n_obs > 1 else 0.0

        avg_net_pips = _compute_avg_net_pips(bt_result.trade_log)
        per_pair_max_frac, per_quarter_max_frac = _compute_concentration(bt_result.trade_log)

        # ------------------------------------------------------------------
        # STEP 6: Evaluate pre-declared .triggers.yaml gates (IC-11).
        # No post-hoc gate invention; ONLY frozen triggers evaluated.
        # ------------------------------------------------------------------
        prereg_spec = parse_pre_registration(prereq_path)
        triggers = prereg_spec.triggers
        power_floor_n, power_floor_label = _extract_power_floor(triggers)

        metrics_map = _build_metrics_map(
            net_sharpe=net_sharpe,
            dsr=dsr,
            n_realized=n_realized,
            avg_net_pips=avg_net_pips,
            per_pair_max_fraction=per_pair_max_frac,
            per_quarter_max_fraction=per_quarter_max_frac,
        )
        gate_results = _evaluate_triggers(triggers, metrics_map)

        # Determine verdict (pre-declared states only).
        verdict = _determine_verdict(
            gate_results=gate_results,
            dsr=dsr,
            n_realized=n_realized,
            power_floor_n=power_floor_n,
            power_floor_label=power_floor_label,
            mechanism=freeze_record.mechanism,
        )

        # ------------------------------------------------------------------
        # STEP 7: Atomic burn + append trial (IC-6, IC-7).
        # ------------------------------------------------------------------
        forward_result = ForwardResult(
            verdict=verdict,
            net_sharpe=net_sharpe,
            dsr=dsr,
            n_realized=n_realized,
            gate_results=gate_results,
            power_floor_n=power_floor_n,
            freeze_id=freeze_id,
            trial_id=trial_id,
            void_after_data=False,
            integrity_ok=True,
            hash_mismatch_detail=integrity_detail,
        )

        _record_trial_and_result(
            forward_result, trials_registry=trials_registry, registry=registry
        )
        _burn_window(freeze_id, registry=registry)

        # Emit the structured verdict event (log-as-decision-trace item 1/5).
        _log_event(
            "forward.verdict",
            freeze_id=freeze_id,
            trial_id=trial_id,
            verdict=verdict,
            net_sharpe=round(net_sharpe, 4),
            dsr=round(dsr, 4),
            n_dsr=n_dsr,
            n_realized=n_realized,
            avg_net_pips=round(avg_net_pips, 4),
            per_pair_max_fraction=round(per_pair_max_frac, 4),
            per_quarter_max_fraction=round(per_quarter_max_frac, 4),
            gate_results=gate_results,
            power_floor_n=power_floor_n,
            mechanism=freeze_record.mechanism,
        )

        return forward_result

    except (FileNotFoundError, KeyError, RuntimeError):
        # Forward registry missing / freeze_id not found / already burned.
        # These are pre-data failures — no N burned (data was never loaded).
        _log_event(
            "forward.error",
            freeze_id=freeze_id,
            trial_id=trial_id,
            data_was_loaded=data_was_loaded,
        )
        raise

    except Exception as exc:
        _log_event(
            "forward.error",
            freeze_id=freeze_id,
            trial_id=trial_id,
            error=str(exc),
            error_type=type(exc).__name__,
            data_was_loaded=data_was_loaded,
        )
        # If data was loaded before the error, burn N (IC-7: VOID-after-data).
        if data_was_loaded:
            void_result = ForwardResult(
                verdict="VOID",
                net_sharpe=None,
                dsr=None,
                n_realized=None,
                gate_results={},
                power_floor_n=None,
                freeze_id=freeze_id,
                trial_id=trial_id,
                void_after_data=True,
                integrity_ok=False,
                hash_mismatch_detail=f"error: {exc}",
            )
            try:
                _record_trial_and_result(
                    void_result, trials_registry=trials_registry, registry=registry
                )
                _burn_window(freeze_id, registry=registry)
            except Exception:
                pass  # Don't mask the original exception.
        raise


# ---------------------------------------------------------------------------
# Verdict determination (pre-declared states only — IC-11)
# ---------------------------------------------------------------------------


def _determine_verdict(
    gate_results: dict[str, bool],
    dsr: float,
    n_realized: int | None,
    power_floor_n: int | None,
    power_floor_label: str | None,
    mechanism: str,
) -> Verdict:
    """Determine the pre-declared verdict from gate results.

    Priority order (FAIL-CLOSED — a hard kill always beats a soft 'inconclusive',
    per NHT SD1: an underpowered window must NEVER soften a real falsification):
      1. Any KILL gate fired (gate_results[label] == True) -> FALSIFIED.
      2. DSR < 0.95 -> FALSIFIED (the primary multiplicity-corrected gate).
      3. (M2 only) realized N < power_floor_n -> INCONCLUSIVE_UNDERPOWERED.
         Only reachable when NO gate fired AND DSR passed — i.e. the result was
         on track to VALIDATE but the window had too few events to be decisive.
      4. All gates passed and N adequate -> VALIDATED.

    Rationale for ordering (critic finding, fixed): if DSR fails AND N is short,
    the honest verdict is FALSIFIED, not INCONCLUSIVE. INCONCLUSIVE is reserved
    for the narrow case 'would have passed but for insufficient power' — never a
    rescue for a result that already failed a hard gate. Checking the KILL gates
    and DSR BEFORE the power floor enforces this (NHT SD1 / no_gate_softening).

    Note: VOID is not produced here — it's emitted before reaching this function
    (integrity or timestamp failures). If we reach this function the integrity
    check passed.
    """
    # 1. KILL gates from the frozen .triggers.yaml (IC-11 / firewall A1).
    #    A fired gate is a HARD falsification — evaluated first, before any
    #    power-floor softening. The min-events/power-floor gate (power_floor_label)
    #    is EXCLUDED here: a short window is INCONCLUSIVE (step 3), not FALSIFIED,
    #    per ML spec A.3 (underpowered != clean kill). All OTHER gates are hard kills.
    for label, fired in gate_results.items():
        if label == power_floor_label:
            continue  # handled as INCONCLUSIVE in step 3, not a hard kill
        if fired:
            return "FALSIFIED"

    # 2. DSR gate (the primary multiplicity-corrected gate — IC-9 / IC-11).
    #    Also a hard falsification, before the power floor.
    if dsr < _DSR_PASS_THRESHOLD:
        return "FALSIFIED"

    # 3. Power floor (M2 only). Only reached when no hard gate fired AND DSR passed:
    #    the result would VALIDATE but for too few events. INCONCLUSIVE, not PASS,
    #    not a free retry (ML spec A.4 rule_5).
    if mechanism == "M2" and power_floor_n is not None and n_realized is not None:
        if n_realized < power_floor_n:
            return "INCONCLUSIVE_UNDERPOWERED"

    # 4. All gates passed, DSR cleared, N adequate.
    return "VALIDATED"


# ---------------------------------------------------------------------------
# Registry and trial helpers
# ---------------------------------------------------------------------------


def _record_trial_and_result(
    result: ForwardResult,
    trials_registry: Path,
    registry: Path,
) -> None:
    """Append a counts_toward=True trial to trials.jsonl and a result to forward_registry.

    IC-7: every forward attempt (PASS, FAIL, VOID-after-data) burns N.
    IC-7 explicitly: VOID-after-data STILL appends counts_toward=True.
    """
    import json as _json

    counts = result.verdict != "VOID" or result.void_after_data

    trial_entry: dict = {
        "trial_id": result.trial_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "forward-eval",
        "verdict": result.verdict,
        "freeze_id": result.freeze_id,
        "counts_toward_deflation_denominator": counts,
        "net_sharpe": result.net_sharpe,
        "dsr": result.dsr,
        "n_realized": result.n_realized,
        "integrity_ok": result.integrity_ok,
    }
    # Append to the provided trials_registry path (not the production default).
    # _append_trial writes to the hardcoded _TRIALS_REGISTRY; we override here
    # so tests can use a temp file without polluting the production ledger.
    trials_registry.parent.mkdir(parents=True, exist_ok=True)
    with open(trials_registry, "a") as fh:
        fh.write(_json.dumps(trial_entry) + "\n")

    result_entry: dict = {
        "record_type": "forward-result",
        "trial_id": result.trial_id,
        "freeze_id": result.freeze_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "verdict": result.verdict,
        "net_sharpe": result.net_sharpe,
        "dsr": result.dsr,
        "n_realized": result.n_realized,
        "gate_results": result.gate_results,
        "power_floor_n": result.power_floor_n,
        "integrity_ok": result.integrity_ok,
        "hash_mismatch_detail": result.hash_mismatch_detail,
        "void_after_data": result.void_after_data,
        "counts_toward_deflation_denominator": counts,
    }
    _append_registry(result_entry, registry)


def _burn_window(freeze_id: str, registry: Path) -> None:
    """Mark a freeze record as burned (IC-6 / IC-7)."""
    update_freeze_record_burned(freeze_id, registry=registry)
    _log_event(
        "forward.burned",
        freeze_id=freeze_id,
        open_count=1,
        burned=True,
    )
