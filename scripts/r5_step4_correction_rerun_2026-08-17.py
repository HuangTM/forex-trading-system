"""Informational correction re-run of the R5 STEP-4 computation (2026-08-17).

WHY: the 2026-06-06 STEP-4 result (r5_carry_universe_kill_test.STEP4-RESULT.yaml)
was computed with two evidence-invalidating defects, found in the 2026-08-17
independent audit and fixed the same day:

  1. The 6 carry_momentum:* cells ran continuous mode + ContinuousSizer WITHOUT
     the usd_nominal unit contract -> JPY-quoted pairs carried ~1/price (~1/150)
     of intended risk, plus silent min_order_size clipping. Those columns of the
     joint matrix were near-flat by construction. Fix: ContinuousSizer now takes
     usd_nominal=True (carry_universe_matrix._build_sizer).
  2. (Unrelated to this matrix: the 3 fake daily pairs AUDUSD/USDCAD/EURGBP —
     not part of the 36-cell JPY-pair matrix, so no effect here.)

This script mirrors scripts/run_r5_step4.py's computation EXACTLY (same frozen
constants: master_seed, B, SR0_PP, Politis-White block length, studentized k*
selection, DSR gate, decision functional) but:
  - does NOT require/consume a freeze receipt,
  - does NOT overwrite the ratified STEP4-RESULT.yaml,
  - writes its output to a separate .correction-rerun.yaml artifact,
  - additionally dumps per-cell annualized Sharpe so the voided
    carry_momentum cells can be compared old-vs-new.

It is an EVIDENCE-CORRECTION artifact (precedent: B1 capital-mismatch fix re-run,
2026-06-27), not a new one-shot burn — the STEP-4 data window was already
consumed by the 2026-06-06 run, and this re-run uses the identical window.
Governance disposition (whether the corrected numbers supersede the ratified
result) is left to CEO ratification; this script only produces the numbers.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import numpy as np
import yaml

_MASTER_SEED = 576746  # frozen, r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml
_B = 5000              # frozen

_OUT_PATH = Path(
    "references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.correction-rerun.yaml"
)
_CELL_SHARPE_PATH = Path(
    "references/pre-registrations/r5_carry_universe_kill_test.correction-rerun-cell-sharpes.yaml"
)


def main() -> int:
    import scipy.stats as sp_stats

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

    run_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[rerun] start {run_utc}", flush=True)

    matrix = build_joint_return_matrix(
        variants=list(CARRY_VARIANTS),
        pairs=list(CARRY_PAIRS),
    )
    print(f"[rerun] matrix built T={matrix.T} k={matrix.k}", flush=True)

    # Per-cell annualized Sharpe (informational; not part of the frozen spec).
    cell_sharpes = {}
    for j, label in enumerate(matrix.labels):
        r = matrix.R[:, j]
        sd = r.std(ddof=1)
        cell_sharpes[label] = float(r.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0
    with open(_CELL_SHARPE_PATH, "w") as fh:
        yaml.dump(
            {"run_utc": run_utc, "cell_sharpes_ann": cell_sharpes},
            fh,
            default_flow_style=False,
            sort_keys=False,
        )
    print("[rerun] per-cell Sharpes written", flush=True)

    L_auto = politis_white_block_length_multivariate(matrix.R)
    L_int = max(1, round(L_auto))
    print(f"[rerun] block length L_auto={L_auto} L_int={L_int}", flush=True)

    r5c = r5c_hansen_spa(
        pair_returns=matrix.R,
        master_seed=_MASTER_SEED,
        block_length=L_int,
        B=_B,
    )
    print(
        f"[rerun] SPA p={r5c.pvalue_consistent} RC p={r5c.white_rc_pvalue}",
        flush=True,
    )

    k_star_idx, t_k_star, sr_ann_kstar = select_k_star_studentized(
        R=matrix.R,
        block_length=L_int,
    )
    k_star_label = matrix.labels[k_star_idx]

    returns_kstar = matrix.R[:, k_star_idx]
    skew_kstar = float(sp_stats.skew(returns_kstar, bias=True))
    ek_kstar = float(sp_stats.kurtosis(returns_kstar, fisher=True, bias=True))

    dsr = compute_dsr_gate(
        sr_ann_best_cell=sr_ann_kstar,
        skew=skew_kstar,
        excess_kurtosis=ek_kstar,
        T=matrix.T,
    )
    dsr_cleared = dsr >= 0.95

    decision = evaluate_decision(
        p_spa=r5c.pvalue_consistent,
        p_rc=r5c.white_rc_pvalue,
        dsr=dsr,
        technical_failure=False,
    )

    payload = {
        "run_utc": run_utc,
        "artifact_type": "evidence-correction-rerun (informational; not a ratified STEP-4)",
        "reason": "carry_momentum cells voided by ContinuousSizer usd_nominal unit bug; fixed 2026-08-17",
        "decision": decision,
        "p_spa_consistent": r5c.pvalue_consistent,
        "p_spa_lower": r5c.pvalue_lower,
        "p_spa_upper": r5c.pvalue_upper,
        "p_rc": r5c.white_rc_pvalue,
        "dsr": dsr,
        "dsr_cleared": dsr_cleared,
        "k_star_label": k_star_label,
        "k_star_idx": int(k_star_idx),
        "t_k_star": float(t_k_star),
        "sr_ann_kstar": sr_ann_kstar,
        "skew_kstar": skew_kstar,
        "excess_kurtosis_kstar": ek_kstar,
        "SR0_PP_frozen": SR0_PP,
        "T": matrix.T,
        "k": matrix.k,
        "labels": matrix.labels,
        "dropped_count": len(matrix.dropped),
        "dropped_labels": [d.label for d in matrix.dropped],
        "block_length_used": r5c.block_length_used,
        "block_length_auto": r5c.block_length_auto,
        "B": r5c.B,
        "master_seed": _MASTER_SEED,
        "original_step4_result": "references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml (2026-06-06, decision=AMBIGUOUS_GATE_FAIL)",
    }
    with open(_OUT_PATH, "w") as fh:
        yaml.dump(payload, fh, default_flow_style=False, sort_keys=False)

    print(f"[rerun] decision={decision} dsr={dsr:.4f} k*={k_star_label}", flush=True)
    print(f"[rerun] wrote {_OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
