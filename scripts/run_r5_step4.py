"""R5 STEP-4 one-shot kill-test runner.

ABSOLUTE PROHIBITION: this script MUST NOT be executed before the pre-registration
freeze-receipt is committed.  Running it early voids the pre-registration (§1.3).
The runner gate-checks BOTH a CLI flag pair AND an on-disk receipt file with a
matching SHA-256 of the pre-reg document.

Usage:
    python scripts/run_r5_step4.py --i-am-step4 --freeze-receipt <path_to_receipt.yaml>

The freeze-receipt must have been written by scripts/cut_freeze_receipt.py AFTER
consensus ratification and CEO sign-off.  The runner verifies
sha256(prereg_file_bytes) == receipt.prereg_sha256 before reading any p-values.

Orchestration order:
    build matrix (full window) -> Politis-White auto block-length (multivariate)
    -> r5c_hansen_spa (B=5000, master_seed=576746)
    -> identify argmax cell k* -> compute SR_ann(k*), skew(k*), ek(k*)
    -> DSR gate (§7.3.4) -> decision functional (§7.3.6)
    -> write structured result artifact YAML + decision-trace logs

main() is NEVER executed in the build dispatch (STEP 3).  STEP 4 is a one-shot
run that happens only after the freeze-receipt is committed.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Logging setup — structured decision-trace per log-as-decision-trace rubric
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("forex_system.harness.r5_step4")


def _log(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log entry.

    Satisfies log-as-decision-trace rubric items 1 (outcome named), 2 (inputs
    included), 3 (parameter sources named), 8 (structured not prose), 9
    (dotted enumerable event name).
    """
    entry = {"event": event, **fields}
    logger.info(json.dumps(entry, default=str))


# ---------------------------------------------------------------------------
# Frozen constants (identical to r5_decision.py; both sourced from §7.3.3)
# ---------------------------------------------------------------------------

_PREREG_PATH = (
    "references/pre-registrations/r5_carry_universe_kill_test.md"
)
_MASTER_SEED = 576746
_B = 5000
_RESULT_PATH = (
    "references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml"
)


# ---------------------------------------------------------------------------
# Receipt validation helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file as-is on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_receipt(receipt_path: Path) -> dict:
    """Load and validate the freeze-receipt.

    Checks:
      (a) receipt file exists
      (b) prereg_sha256 field present
      (c) sha256(prereg_file_bytes) == receipt.prereg_sha256

    Returns the parsed receipt dict on success.
    Calls sys.exit(1) on any validation failure (TECHNICAL FAILURE path).
    """
    if not receipt_path.exists():
        _log(
            "r5_step4.gate_refused",
            reason="freeze_receipt_missing",
            receipt_path=str(receipt_path),
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(
            f"ERROR: freeze-receipt file not found: {receipt_path}\n"
            "Run scripts/cut_freeze_receipt.py after consensus ratification "
            "to produce the receipt, then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(receipt_path) as fh:
        receipt = yaml.safe_load(fh)

    if "prereg_sha256" not in receipt:
        _log(
            "r5_step4.gate_refused",
            reason="receipt_missing_prereg_sha256_field",
            receipt_path=str(receipt_path),
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(
            f"ERROR: freeze-receipt {receipt_path} is missing 'prereg_sha256' field.",
            file=sys.stderr,
        )
        sys.exit(1)

    prereg_path = Path(receipt.get("prereg_path", _PREREG_PATH))
    if not prereg_path.exists():
        _log(
            "r5_step4.gate_refused",
            reason="prereg_file_missing",
            prereg_path=str(prereg_path),
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(f"ERROR: pre-reg file not found: {prereg_path}", file=sys.stderr)
        sys.exit(1)

    actual_sha256 = _sha256_file(prereg_path)
    expected_sha256 = receipt["prereg_sha256"]

    _log(
        "r5_step4.receipt_check",
        prereg_path=str(prereg_path),
        actual_sha256=actual_sha256,
        expected_sha256=expected_sha256,
        match=(actual_sha256 == expected_sha256),
        source="freeze_receipt_file",
    )

    if actual_sha256 != expected_sha256:
        _log(
            "r5_step4.gate_refused",
            reason="prereg_sha256_mismatch",
            actual_sha256=actual_sha256,
            expected_sha256=expected_sha256,
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(
            f"ERROR: pre-registration SHA-256 mismatch.\n"
            f"  Expected: {expected_sha256}\n"
            f"  Actual:   {actual_sha256}\n"
            "The pre-reg file has been modified after the freeze-receipt was written. "
            "This voids the pre-registration.  Do not read any p-values.",
            file=sys.stderr,
        )
        sys.exit(1)

    return receipt


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrate the R5 STEP-4 one-shot kill-test run.

    Gate: requires --i-am-step4 --freeze-receipt <path> AND a valid receipt.
    Never executes during the build dispatch (STEP 3).
    """
    parser = argparse.ArgumentParser(
        description=(
            "R5 STEP-4 one-shot kill-test runner.  Requires --i-am-step4 flag "
            "AND a valid --freeze-receipt file produced by cut_freeze_receipt.py "
            "after consensus ratification.  Running before freeze voids the pre-reg."
        )
    )
    parser.add_argument(
        "--i-am-step4",
        action="store_true",
        help=(
            "REQUIRED guard flag.  Confirms the operator intends to execute the "
            "one-shot kill test.  Must be combined with --freeze-receipt."
        ),
    )
    parser.add_argument(
        "--freeze-receipt",
        type=Path,
        metavar="PATH",
        help=(
            "Path to the freeze-receipt YAML produced by cut_freeze_receipt.py "
            "after consensus ratification.  The runner verifies the pre-reg SHA-256 "
            "from this receipt before proceeding."
        ),
    )
    args = parser.parse_args()

    # Gate 1: explicit opt-in flag
    if not args.i_am_step4:
        _log(
            "r5_step4.gate_refused",
            reason="missing_--i-am-step4_flag",
            action="PRINT_HELP_AND_EXIT_1",
        )
        parser.print_help()
        print(
            "\nERROR: --i-am-step4 flag is required.  This is a one-shot test. "
            "Read the pre-registration §1.3 before proceeding.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Gate 2: freeze-receipt path provided
    if args.freeze_receipt is None:
        _log(
            "r5_step4.gate_refused",
            reason="missing_--freeze-receipt_argument",
            action="EXIT_1",
        )
        print(
            "ERROR: --freeze-receipt <path> is required alongside --i-am-step4.",
            file=sys.stderr,
        )
        sys.exit(1)

    receipt_path: Path = args.freeze_receipt

    # Gate 3: receipt validation (SHA-256 of pre-reg file == receipt.prereg_sha256)
    _log(
        "r5_step4.gate_check_start",
        receipt_path=str(receipt_path),
        source="cli_args",
    )
    receipt = _validate_receipt(receipt_path)
    _log(
        "r5_step4.gate_passed",
        receipt_path=str(receipt_path),
        code_commit=receipt.get("code_commit", "UNKNOWN"),
        frozen_at_utc=receipt.get("frozen_at_utc", "UNKNOWN"),
        master_seed=receipt.get("master_seed", _MASTER_SEED),
        K=receipt.get("K", _B),
        sr0_pp=receipt.get("sr0_pp", "0.022906"),
        n_elected=receipt.get("n_elected", 3),
    )

    # ---------------------------------------------------------------------------
    # Import harness modules (deferred so --help works without scipy)
    # ---------------------------------------------------------------------------
    try:
        import scipy.stats as _sp_stats  # noqa: F401 — ensure scipy available
        from forex_system.harness.carry_universe_matrix import (
            CARRY_PAIRS,
            CARRY_VARIANTS,
            build_joint_return_matrix,
        )
        from forex_system.harness.r5_decision import (
            SR0_PP,
            compute_dsr_gate,
            evaluate_decision,
            select_k_star_studentized,
        )
        from forex_system.harness.reality_check import (
            politis_white_block_length_multivariate,
            r5c_hansen_spa,
        )
    except ImportError as exc:
        _log(
            "r5_step4.technical_failure",
            reason="import_error",
            error=str(exc),
            action="EXIT_1",
        )
        print(f"TECHNICAL FAILURE: import error: {exc}", file=sys.stderr)
        sys.exit(1)

    run_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _log(
        "r5_step4.run_start",
        run_utc=run_utc,
        master_seed=_MASTER_SEED,
        B=_B,
        variants=list(CARRY_VARIANTS),
        pairs=list(CARRY_PAIRS),
    )

    # ---------------------------------------------------------------------------
    # 1. Build joint return matrix (full window = no window slice per pre-reg)
    # ---------------------------------------------------------------------------
    _log(
        "r5_step4.matrix_build_start",
        variants=list(CARRY_VARIANTS),
        pairs=list(CARRY_PAIRS),
        window=None,
        source="pre_reg_section_2",
    )
    try:
        matrix = build_joint_return_matrix(
            variants=list(CARRY_VARIANTS),
            pairs=list(CARRY_PAIRS),
            # window=None: full common history (Method B snooped sample; §3.2)
        )
    except Exception as exc:
        _log(
            "r5_step4.technical_failure",
            reason="matrix_build_error",
            error=str(exc),
            action="RULE_0_TECHNICAL_FAILURE",
        )
        raise

    _log(
        "r5_step4.matrix_built",
        T=matrix.T,
        k=matrix.k,
        date_start=str(matrix.index[0].date()) if matrix.T > 0 else "N/A",
        date_end=str(matrix.index[-1].date()) if matrix.T > 0 else "N/A",
        labels=matrix.labels,
        dropped_count=len(matrix.dropped),
        dropped_labels=[d.label for d in matrix.dropped],
        source="carry_universe_matrix.build_joint_return_matrix",
    )

    # Verify k == 36 (pre-reg §2.2 NO-SILENT-EXCLUSION)
    k_expected = 36
    if matrix.k < k_expected:
        _log(
            "r5_step4.cell_count_check",
            k_actual=matrix.k,
            k_expected=k_expected,
            dropped_count=len(matrix.dropped),
            dropped_labels=[d.label for d in matrix.dropped],
            verdict="WARNING_INVESTIGATE_DROPS_BEFORE_READING_PVALUE",
        )
    else:
        _log(
            "r5_step4.cell_count_check",
            k_actual=matrix.k,
            k_expected=k_expected,
            dropped_count=len(matrix.dropped),
            verdict="OK_all_36_cells_built",
        )

    # ---------------------------------------------------------------------------
    # 2. Politis-White auto block-length (multivariate; §4 / step 2a commit)
    # ---------------------------------------------------------------------------
    _log(
        "r5_step4.block_length_start",
        algorithm="politis_white_block_length_multivariate",
        source="reality_check.politis_white_block_length_multivariate",
    )
    L_auto = politis_white_block_length_multivariate(matrix.R)
    L_int = max(1, round(L_auto))
    _log(
        "r5_step4.block_length_selected",
        L_auto=L_auto,
        L_int=L_int,
        T=matrix.T,
        k=matrix.k,
        source="politis_white_block_length_multivariate",
    )

    # ---------------------------------------------------------------------------
    # 3. R5c Hansen SPA + White RC (B=5000, master_seed=576746)
    # ---------------------------------------------------------------------------
    _log(
        "r5_step4.spa_run_start",
        B=_B,
        master_seed=_MASTER_SEED,
        block_length=L_int,
        source="r5c_hansen_spa",
    )
    r5c = r5c_hansen_spa(
        pair_returns=matrix.R,
        master_seed=_MASTER_SEED,
        block_length=L_int,
        B=_B,
    )
    _log(
        "r5_step4.spa_result",
        p_spa_consistent=r5c.pvalue_consistent,
        p_spa_lower=r5c.pvalue_lower,
        p_spa_upper=r5c.pvalue_upper,
        p_rc=r5c.white_rc_pvalue,
        t_spa_obs=r5c.t_spa_obs,
        t_rc_obs=r5c.t_rc_obs,
        B=r5c.B,
        seed=r5c.seed,
        block_length_used=r5c.block_length_used,
        block_length_auto=r5c.block_length_auto,
        source="r5c_hansen_spa",
    )

    p_spa = r5c.pvalue_consistent
    p_rc = r5c.white_rc_pvalue

    # ---------------------------------------------------------------------------
    # 4. Identify best cell k* (§7.3.4: argmax of STUDENTIZED T_k statistic)
    # ---------------------------------------------------------------------------
    # §7.3.4 defines k* as the cell attaining the family maximum of the
    # studentized statistic:
    #
    #   T_k = sqrt(T) * mean(d_k) / omega_hat_k
    #
    # where omega_hat_k is the Newey-West HAC SE with Bartlett kernel,
    # bandwidth h = block_length - 1 (floor 1), and a 1e-12 floor on omega,
    # mirroring r5c_hansen_spa exactly.  The DSR gate input remains the
    # annualized Sharpe of the chosen k* (mean/std(ddof=1)*sqrt(252)),
    # consistent with §7.3.4 — only the SELECTION of k* changes.
    k_star_idx, t_k_star, sr_ann_kstar = select_k_star_studentized(
        R=matrix.R,
        block_length=L_int,  # SAME block_length passed to r5c_hansen_spa above
    )
    k_star_label = matrix.labels[k_star_idx]

    _log(
        "r5_step4.best_cell_identified",
        k_star_idx=k_star_idx,
        k_star_label=k_star_label,
        t_k_star=t_k_star,
        sr_ann=sr_ann_kstar,
        source="argmax_studentized_T_k_hac",
    )

    # ---------------------------------------------------------------------------
    # 5. Compute skew and excess kurtosis for k* (§7.3.4 A-5 pins)
    # ---------------------------------------------------------------------------
    import scipy.stats as sp_stats

    returns_kstar = matrix.R[:, k_star_idx]
    # A-5 pin: bias=True (biased/MLE estimators; scipy default; §7.3.4)
    skew_kstar = float(sp_stats.skew(returns_kstar, bias=True))
    ek_kstar = float(sp_stats.kurtosis(returns_kstar, fisher=True, bias=True))

    _log(
        "r5_step4.kstar_moments",
        k_star_label=k_star_label,
        T_kstar=len(returns_kstar),
        sr_ann=sr_ann_kstar,
        skew=skew_kstar,
        excess_kurtosis=ek_kstar,
        estimator_convention="scipy.stats.skew(bias=True), scipy.stats.kurtosis(fisher=True, bias=True)",
        source="pre_reg_section_7_3_4_A5_pins",
    )

    # ---------------------------------------------------------------------------
    # 6. DSR gate (§7.3.4 / §7.3.5)
    # ---------------------------------------------------------------------------
    _log(
        "r5_step4.dsr_gate_start",
        sr_ann=sr_ann_kstar,
        skew=skew_kstar,
        excess_kurtosis=ek_kstar,
        T=matrix.T,
        SR0_PP_frozen=SR0_PP,
        SR0_PP_source="r5_decision.SR0_PP; = 0.363623/sqrt(252); elected N=3; pre_reg §7.3.3",
        dsr_threshold=0.95,
        dsr_threshold_source="pre_reg §7.3.5",
    )
    dsr = compute_dsr_gate(
        sr_ann_best_cell=sr_ann_kstar,
        skew=skew_kstar,
        excess_kurtosis=ek_kstar,
        T=matrix.T,
    )
    dsr_cleared = dsr >= 0.95
    _log(
        "r5_step4.dsr_gate_result",
        dsr=dsr,
        dsr_threshold=0.95,
        dsr_cleared=dsr_cleared,
        k_star_label=k_star_label,
        source="r5_decision.compute_dsr_gate",
    )

    # ---------------------------------------------------------------------------
    # 7. Decision functional (§7.3.6)
    # ---------------------------------------------------------------------------
    _log(
        "r5_step4.decision_start",
        p_spa=p_spa,
        p_rc=p_rc,
        dsr=dsr,
        technical_failure=False,
        rule_order="RULE0_techfail -> RULE1_straddle -> RULE2_windown -> RULE3_continue -> RULE4_ambiguous",
        source="r5_decision.evaluate_decision; pre_reg §7.3.6",
    )
    decision = evaluate_decision(
        p_spa=p_spa,
        p_rc=p_rc,
        dsr=dsr,
        technical_failure=False,
    )
    _log(
        "r5_step4.decision_result",
        decision=decision,
        p_spa=p_spa,
        p_rc=p_rc,
        dsr=dsr,
        dsr_cleared=dsr_cleared,
        k_star_label=k_star_label,
        source="r5_decision.evaluate_decision; pre_reg §7.3.6",
    )

    # ---------------------------------------------------------------------------
    # 8. Write structured result artifact YAML
    # ---------------------------------------------------------------------------
    result_payload: dict = {
        "run_utc": run_utc,
        "decision": decision,
        "p_spa_consistent": p_spa,
        "p_spa_lower": r5c.pvalue_lower,
        "p_spa_upper": r5c.pvalue_upper,
        "p_rc": p_rc,
        "dsr": dsr,
        "dsr_cleared": dsr_cleared,
        "k_star_label": k_star_label,
        "k_star_idx": k_star_idx,
        "sr_ann_kstar": sr_ann_kstar,
        "skew_kstar": skew_kstar,
        "excess_kurtosis_kstar": ek_kstar,
        "SR0_PP_frozen": SR0_PP,
        "SR0_PP_source": "r5_decision.SR0_PP = 0.363623/sqrt(252); elected N=3; pre_reg §7.3.3",
        "T": matrix.T,
        "k": matrix.k,
        "labels": matrix.labels,
        "dropped_count": len(matrix.dropped),
        "dropped_labels": [d.label for d in matrix.dropped],
        "block_length_used": r5c.block_length_used,
        "block_length_auto": r5c.block_length_auto,
        "B": r5c.B,
        "master_seed": _MASTER_SEED,
        "code_commit": receipt.get("code_commit", "UNKNOWN"),
        "frozen_at_utc": receipt.get("frozen_at_utc", "UNKNOWN"),
        "prereg_sha256": receipt.get("prereg_sha256", "UNKNOWN"),
        "freeze_receipt_path": str(receipt_path),
        "spec_ref": "references/pre-registrations/r5_carry_universe_kill_test.md §7.3.3-§7.3.6",
    }

    result_path = Path(_RESULT_PATH)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as fh:
        yaml.dump(result_payload, fh, default_flow_style=False, sort_keys=False)

    _log(
        "r5_step4.result_written",
        result_path=str(result_path),
        decision=decision,
    )
    print(f"\nSTEP-4 COMPLETE.  Decision: {decision}")
    print(f"Result artifact: {result_path}")


if __name__ == "__main__":
    main()
