"""
10-pairs readiness compute: C1 (DQ CADJPY), C2 (rho_bar_eff ALL-10/ALL-9/subsets), C3 (CD0 CADJPY).
QD artifact: .fintech-org/artifacts/2026-06-25-cadjpy-10pairs-readiness/quant-developer-compute.yaml

REUSES: compute_9pairs_readiness.py — all helper functions imported directly.
        config/data_quality_gates_1h.yaml (CADJPY entry added before this run).
        src/forex_system/data/quality_gate_1h.py (unchanged DQ gate library).

Changes vs compute_9pairs_readiness.py:
  - Adds CADJPY to universe (ALL_10 = ALL_9 + CADJPY).
  - C1: DQ gate for CADJPY only (not re-running prior 9).
  - C2: ALL-10, ALL-9 (confirm 0.4090), JPY-cross subset, crosses-only subset.
  - C3: CD0 F1-F6 for CADJPY only (uniform pip=0.0001, matches prior canonical spec).

No trial counter increment: descriptive readiness update.
EXCLUDE-NOT-IMPUTE: zero/missing spread bars excluded from CD0.
No lookahead: shift(1) in _net_pnl_pips.
"""

from __future__ import annotations

import sys
import json
import math
from pathlib import Path
import datetime as dt

import numpy as np
import pandas as pd

# ── project paths ─────────────────────────────────────────────────────────────
REPO = Path("/Users/huangtm/Projects/forex-trading-system")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

# Import ALL helpers from compute_9pairs_readiness (REUSE — do NOT reinvent)
from compute_9pairs_readiness import (
    run_c1_dq,
    dq_detail,
    compute_rho_bar_eff,
    pairwise_corr_matrix,
    run_c3_cd0,
    run_cd0_family,
    verdict,
    DATA_DIR,
    SLIP_PIPS,
    HAIRCUT_PIPS,
    ANN_FACTOR,
)
from forex_system.data.quality_gate_1h import (
    load_gate_config,
    coverage_gate,
    apply_sc4_cross_pair_check,
)

# ── universe ──────────────────────────────────────────────────────────────────
ALL_9  = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "AUDJPY"]
ALL_10 = ALL_9 + ["CADJPY"]

# Subsets for C2
JPY_CROSS_3 = ["EURJPY", "AUDJPY", "CADJPY"]   # all JPY-quote crosses in universe
CROSSES_4   = ["EURJPY", "EURGBP", "AUDJPY", "CADJPY"]  # all non-USD-denominated crosses

ARTIFACT_DIR = REPO / ".fintech-org" / "artifacts" / "2026-06-25-cadjpy-10pairs-readiness"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("10-PAIRS READINESS COMPUTE: C1 (CADJPY DQ), C2 (rho_bar_eff), C3 (CADJPY CD0)")
    print("=" * 70)

    config = load_gate_config()

    # ── C1: DQ gate for CADJPY ────────────────────────────────────────────────
    print("\n── C1: DQ GATE (CADJPY) ──")

    cadjpy_path = DATA_DIR / "CADJPY_1h.parquet"
    r_cadjpy = coverage_gate(cadjpy_path, "CADJPY", config, trade_window="5yr")
    detail_cadjpy = dq_detail("CADJPY", r_cadjpy)

    pp_cfg = config["per_pair"]["CADJPY"]
    detail_cadjpy["gate_spread_median_ceiling"] = pp_cfg["spread_median_ceiling"]
    detail_cadjpy["gate_p90_ceiling"] = pp_cfg["spread_p90_ceiling"]

    print(f"\n  CADJPY:")
    print(f"    n_rows              = {detail_cadjpy['n_rows']}")
    print(f"    UTC range           = {detail_cadjpy['utc_range']}")
    print(f"    bar_coverage        = {detail_cadjpy['bar_coverage_pct']}%")
    print(f"    spread_coverage     = {detail_cadjpy['measured_spread_coverage_pct']}%")
    print(f"    max_gap_h           = {detail_cadjpy['max_contiguous_gap_h']}")
    print(f"    spread_median       = {detail_cadjpy['spread_median_pips_global']} pips (ceil={detail_cadjpy['gate_spread_median_ceiling']})")
    print(f"    spread_p90_med      = {detail_cadjpy['spread_p90_pips_global_median']} pips (ceil={detail_cadjpy['gate_p90_ceiling']})")
    print(f"    spread_p90_of_med   = {detail_cadjpy['spread_p90_of_spread_median']} pips")
    print(f"    spread_max          = {detail_cadjpy['spread_max']} pips")
    print(f"    frac_above_5pip     = {detail_cadjpy['frac_bars_above_5pips']:.2%}")
    print(f"    n_zero_spread       = {detail_cadjpy['n_zero_spread_bars']}")
    print(f"    n_missing_spread    = {detail_cadjpy['n_missing_spread_bars']}")
    print(f"    VERDICT             = {detail_cadjpy['verdict']}")
    if detail_cadjpy['issues']:
        for issue in detail_cadjpy['issues']:
            print(f"    ISSUE: {issue}")
    if detail_cadjpy['spread_flags']:
        for flag in detail_cadjpy['spread_flags']:
            print(f"    FLAG: {flag}")

    # Also run SC-4 across the full 10-pair admitted set for completeness
    all_10_results = []
    for pair in ALL_10:
        path = DATA_DIR / f"{pair}_1h.parquet"
        r = coverage_gate(path, pair, config, trade_window="5yr")
        all_10_results.append(r)
    apply_sc4_cross_pair_check(all_10_results, config)
    cadjpy_result_sc4 = next(r for r in all_10_results if r.pair == "CADJPY")
    print(f"\n  CADJPY after SC-4 cross-pair check: verdict={cadjpy_result_sc4.verdict}")
    if cadjpy_result_sc4.spread_flags:
        for flag in cadjpy_result_sc4.spread_flags:
            print(f"    SC-4 FLAG: {flag}")

    # ── C2: rho_bar_eff ───────────────────────────────────────────────────────
    print("\n── C2: rho_bar_eff (eigenvalue/sign-blind) ──")

    PRIOR_ALL9_RHO  = 0.4090

    subsets = {
        "ALL_10":        ALL_10,
        "ALL_9":         ALL_9,
        "JPY_cross_3":   JPY_CROSS_3,
        "CROSSES_4":     CROSSES_4,
    }

    c2_results = {}
    for label, pairs in subsets.items():
        res = compute_rho_bar_eff(pairs)
        c2_results[label] = res

        direction = "BELOW GATE (pass)" if res["rho_bar_eff"] <= 0.41 else f"ABOVE GATE (breach {res['rho_bar_eff']:.4f} > 0.41)"
        print(f"\n  {label} (k={res['k']}, n_obs={res['n_obs']}):")
        print(f"    lambda_max    = {res['lambda_max']}")
        print(f"    PC1           = {res['PC1']:.1%}")
        print(f"    rho_bar_eff   = {res['rho_bar_eff']}  [{direction}]")
        print(f"    gate_result   = {res['gate_result']}")
        print(f"    N_eff (min)   = {res['N_eff_min']}")
        print(f"    N_eff routes  = route1(k/λmax)={res['N_eff_route1_k_over_lambda']} / route2(PR)={res['N_eff_route2_PR']} / route3(ENB)={res['N_eff_route3_ENB']}")
        print(f"    mean_signed   = {res['mean_signed_corr']} (NOT gate stat; disclosed only)")

    # Delta: ALL-10 vs ALL-9 prior
    all10_rho = c2_results["ALL_10"]["rho_bar_eff"]
    delta_10v9 = all10_rho - PRIOR_ALL9_RHO
    direction_delta = "increases (worse)" if delta_10v9 > 0 else "decreases (better)" if delta_10v9 < 0 else "no change"
    print(f"\n  Delta ALL-10 vs ALL-9 prior ({PRIOR_ALL9_RHO}):")
    print(f"    rho_bar_eff {all10_rho} vs {PRIOR_ALL9_RHO} → delta={delta_10v9:+.4f} ({direction_delta})")

    all9_confirm = c2_results["ALL_9"]["rho_bar_eff"]
    print(f"\n  ALL-9 confirmation: computed={all9_confirm} (prior=0.4090, match={abs(all9_confirm - 0.4090) < 0.001})")

    # CADJPY pairwise correlations with the other 9
    print("\n  CADJPY pairwise correlations vs ALL_10 peers:")
    corr_10 = pairwise_corr_matrix(ALL_10)
    cadjpy_corrs = corr_10["CADJPY"].drop("CADJPY")
    print("    " + "  ".join(f"{p}={v:.3f}" for p, v in cadjpy_corrs.items()))

    # JPY-concentration note
    print("\n  JPY-cross correlation structure (EURJPY, AUDJPY, CADJPY):")
    for p in ["EURJPY", "AUDJPY"]:
        print(f"    CADJPY vs {p}: {corr_10.loc['CADJPY', p]:.3f}")

    # ── C3: CD0 CADJPY ────────────────────────────────────────────────────────
    print("\n── C3: CD0 NET-SR (CADJPY, F1-F6, real spreads) ──")
    # CADJPY is JPY-quote, physical pip = 0.01.
    # Per prior canonical spec: pip=0.0001 UNIFORM for all pairs (see run_cd0_family docstring).
    c3_cadjpy = run_c3_cd0(["CADJPY"])

    print(f"\n  {'Family':<25} {'Gross SR':>10} {'Net SR':>10} {'N_trades':>10} {'Verdict':<10}")
    print("  " + "-" * 65)
    for fname, fdata in c3_cadjpy["CADJPY"]["families"].items():
        v = verdict(fdata["net_SR"])
        print(f"  {fname:<25} {fdata['gross_SR']:>10.4f} {fdata['net_SR']:>10.4f} {fdata['n_trades']:>10} {v:<10}")

    best_net = max(fdata["net_SR"] for fdata in c3_cadjpy["CADJPY"]["families"].values())
    best_fam = max(c3_cadjpy["CADJPY"]["families"].items(), key=lambda x: x[1]["net_SR"])[0]
    print(f"\n  CADJPY best net SR: {best_net:.4f} ({best_fam}) → {verdict(best_net)}")

    # ── Save structured results ───────────────────────────────────────────────
    out = {
        "run_timestamp": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "C1_dq_cadjpy": {k: str(v) if not isinstance(v, (int, float, str, list, dict, bool, type(None))) else v
                         for k, v in detail_cadjpy.items()},
        "C1_cadjpy_sc4_verdict": cadjpy_result_sc4.verdict,
        "C1_cadjpy_sc4_flags": cadjpy_result_sc4.spread_flags,
        "C2_rho_bar_eff": c2_results,
        "C2_cadjpy_pairwise_corr": cadjpy_corrs.to_dict(),
        "C3_cd0_cadjpy": c3_cadjpy,
    }
    out_json = ARTIFACT_DIR / "compute_10pairs_raw.json"
    with out_json.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Raw results saved to: {out_json}")
    print("\n── DONE ──")
