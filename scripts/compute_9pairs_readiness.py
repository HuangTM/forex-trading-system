"""
9-pairs readiness compute: C1 (DQ), C2 (rho_bar_eff), C3 (CD0 net-SR).
QD artifact: .fintech-org/artifacts/2026-06-24-9pairs-landed/quant-developer-compute.yaml

Reuses: src/forex_system/data/quality_gate_1h.py (existing DQ gate library)
        F1-F6 family specs from .fintech-org/artifacts/2026-06-22-6pairs-landed/CONSENSUS.md
        rho_bar_eff statistic per hoqr-rho-bar-amendment.yaml (eigenvalue/sign-blind)

No lookahead: signals computed at bar t, position applied at bar t+1 (shift(1)).
No trial counter increment: this is a descriptive screen.
EXCLUDE-NOT-IMPUTE: zero/missing spread bars excluded from CD0.
"""

from __future__ import annotations

import sys
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

# ── project paths ────────────────────────────────────────────────────────────
REPO = Path("/Users/huangtm/Projects/forex-trading-system")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from forex_system.data.quality_gate_1h import (
    load_gate_config,
    coverage_gate,
    apply_sc4_cross_pair_check,
)

# ── universe ──────────────────────────────────────────────────────────────────
ALL_9 = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "AUDJPY"]
USD_7 = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "EURJPY"]   # excl EURGBP+AUDJPY
USD_6 = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"]              # USD-majors-6 prior
CROSSES = ["EURJPY", "EURGBP", "AUDJPY"]
NEW_CROSSES = ["EURGBP", "AUDJPY"]

DATA_DIR = REPO / "data" / "processed"
ARTIFACT_DIR = REPO / ".fintech-org" / "artifacts" / "2026-06-24-9pairs-landed"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# ── cost model (matches prior CD0 screens) ───────────────────────────────────
SLIP_PIPS = 0.25
HAIRCUT_PIPS = 0.15   # paper-broker haircut per side

# Annualisation: sqrt(6150 bars/yr per 1h data)
ANN_FACTOR = math.sqrt(6150)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION C1: DQ gate for EURGBP and AUDJPY
# ─────────────────────────────────────────────────────────────────────────────
def run_c1_dq(pairs: list[str], config: dict) -> dict:
    """Run DQ gate for given pairs. Returns dict keyed by pair."""
    results = {}
    gate_results = []
    for pair in pairs:
        path = DATA_DIR / f"{pair}_1h.parquet"
        r = coverage_gate(path, pair, config, trade_window="5yr")
        results[pair] = r
        gate_results.append(r)
    # SC-4 cross-pair (flag only, does not change verdict for new pairs)
    apply_sc4_cross_pair_check(gate_results, config)
    return results


def dq_detail(pair: str, r) -> dict:
    """Return human-readable manifest for one pair."""
    df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    n_rows = len(df)
    utc_range = f"{df.index[0]} → {df.index[-1]}"
    spread_all = df["spread_median_pips"]
    spread_p90_all = df["spread_p90_pips"]
    n_zero_spread = (spread_all == 0.0).sum()
    n_missing_spread = spread_all.isna().sum()

    # Spread distribution summary
    spread_pct5  = float(spread_all.quantile(0.05))
    spread_median_global = float(spread_all.median())
    spread_pct90_global = float(spread_all.quantile(0.90))
    spread_max   = float(spread_all.max())
    p90_spread_median_global = float(spread_p90_all.median())

    # Fraction of bars above e.g. 5 pips spread_median
    frac_above_5 = float((spread_all > 5.0).mean())

    return {
        "pair": pair,
        "n_rows": n_rows,
        "utc_range": utc_range,
        "bar_coverage_pct": round(r.bar_coverage_pct * 100, 2),
        "expected_trading_bars": r.expected_trading_bars,
        "in_session_bars": r.in_session_bars,
        "measured_spread_coverage_pct": round(r.measured_spread_fraction * 100, 2),
        "max_contiguous_gap_h": r.max_contiguous_gap_hours,
        "spread_median_pips_global": round(spread_median_global, 3),
        "spread_p90_pips_global_median": round(p90_spread_median_global, 3),
        "spread_p5": round(spread_pct5, 3),
        "spread_p90_of_spread_median": round(spread_pct90_global, 3),
        "spread_max": round(spread_max, 3),
        "frac_bars_above_5pips": round(frac_above_5, 4),
        "n_zero_spread_bars": int(n_zero_spread),
        "n_missing_spread_bars": int(n_missing_spread),
        "gate_spread_median_ceiling": None,  # filled below
        "gate_p90_ceiling": None,
        "verdict": r.verdict,
        "issues": r.issues,
        "spread_flags": r.spread_flags,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION C2: rho_bar_eff (eigenvalue/sign-blind)
# Formula: rho_bar_eff = (lambda_max(C) - 1) / (k - 1)
# N_eff routes:
#   route_1: k / lambda_max  (=N_raw_proxy; using k directly as N_raw stand-in)
#   route_2: k^2 / sum(lambda_i^2)  (participation ratio)
#   route_3: k^2 / ENB  (effective number of bets from squared eigenvalues)
# N_eff = k is the max (the raw); we use the MINIMUM route per amendment.
# Proxy: raw hourly log-returns (no signal series pre-pre-reg).
# ─────────────────────────────────────────────────────────────────────────────

def compute_rho_bar_eff(pairs: list[str]) -> dict:
    """Compute rho_bar_eff for a list of pairs using raw log-return correlation matrix."""
    k = len(pairs)
    # Load aligned hourly log-returns
    dfs = {}
    for p in pairs:
        df = pd.read_parquet(DATA_DIR / f"{p}_1h.parquet")
        lr = np.log(df["close"] / df["close"].shift(1)).dropna()
        dfs[p] = lr

    # Align on common index
    aligned = pd.DataFrame(dfs).dropna()
    n_obs = len(aligned)

    # Correlation matrix (Pearson)
    C = aligned.corr().values  # k x k

    # Eigenvalues
    eigenvalues = np.linalg.eigvalsh(C)
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]  # descending
    lambda_max = float(eigenvalues_sorted[0])
    lambda_sum_sq = float(np.sum(eigenvalues_sorted ** 2))

    # Participation ratio (PR) = k^2 / sum(lambda_i^2)
    PR = k**2 / lambda_sum_sq

    # Effective Number of Bets (ENB) = exp(entropy of normalized eigenvalues)
    lam_norm = eigenvalues_sorted / eigenvalues_sorted.sum()
    # Shannon entropy of normalized eigenvalues
    entropy = -float(np.sum(lam_norm * np.log(lam_norm + 1e-30)))
    ENB = math.exp(entropy)

    # rho_bar_eff = (lambda_max - 1) / (k - 1)
    rho_bar_eff = (lambda_max - 1.0) / (k - 1.0) if k > 1 else 0.0

    # N_eff routes (MIN-over-routes per amendment)
    # F-002 NOTE (2026-06-24): these are PARTICIPATION-RATIO-based effective bets counts,
    # NOT the amendment-scaled N_eff* used in DSR deflation. N_eff* is computed separately
    # in the DSR harness. The label "N_eff_min" below refers to min(route1, route2, route3),
    # the conservative effective-bets estimate that gates rho_bar_eff acceptance. It is NOT
    # the "k/λ_max" that reported 2.11 in prior sessions — that was route1; the min is smaller.
    N_route1 = k / lambda_max          # k/λ_max: relative effective rank (NOT amendment-N_eff*)
    N_route2 = PR                       # k²/Σλᵢ²: participation ratio (effective bets)
    N_route3 = ENB                      # exp(Shannon entropy of norm. eigenvalues): eff. num. bets

    N_eff = min(N_route1, N_route2, N_route3)  # conservative: min of three routes

    # PC1 explained variance fraction
    PC1 = lambda_max / k

    # Mean signed pairwise corr (for disclosure — NOT the gate stat)
    C_offdiag = C[np.triu_indices(k, k=1)]
    mean_signed = float(np.mean(C_offdiag))

    return {
        "k": k,
        "n_obs": n_obs,
        "lambda_max": round(lambda_max, 4),
        "PC1": round(PC1, 4),
        "rho_bar_eff": round(rho_bar_eff, 4),
        "N_eff_min": round(N_eff, 4),
        "N_eff_route1_k_over_lambda": round(N_route1, 4),
        "N_eff_route2_PR": round(N_route2, 4),
        "N_eff_route3_ENB": round(N_route3, 4),
        "PR": round(PR, 4),
        "ENB": round(ENB, 4),
        "lambda_sum_sq": round(lambda_sum_sq, 4),
        "mean_signed_corr": round(mean_signed, 4),
        "gate_threshold": 0.41,
        "gate_result": "FAIL" if rho_bar_eff > 0.41 else "PASS",
        "eigenvalues": [round(x, 4) for x in eigenvalues_sorted],
    }


def pairwise_corr_matrix(pairs: list[str]) -> pd.DataFrame:
    """Return pairwise correlation matrix for the pairs."""
    dfs = {}
    for p in pairs:
        df = pd.read_parquet(DATA_DIR / f"{p}_1h.parquet")
        lr = np.log(df["close"] / df["close"].shift(1)).dropna()
        dfs[p] = lr
    aligned = pd.DataFrame(dfs).dropna()
    return aligned.corr().round(3)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION C3: CD0 net-SR screen with real per-bar spreads
# Families (from 2026-06-19 CONSENSUS.md and 2026-06-22 QD cycle-2):
#   F1: hourly reversal — signal = -sign(close - open), 1-bar hold, shift(1)
#   F2: session-open momentum — enter at 07:00 UTC, signal = sign(07:00 bar return), hold 1 bar
#   F3: intraday momentum 3-bar — signal = sign(sum of last 3 bar returns), shift(1)
#   F4: vol breakout — signal = sign if range > rolling_24h_max_range * 0.5, shift(1)
#   F5: London AM drift — signal = 1 (long) 08:00-12:00 UTC (4 bars), sign = sign of open vs prior close
#   F6: spread-filtered reversal — F1 but only when spread_median_pips < threshold (q50)
# EXCLUDE-NOT-IMPUTE: bars where spread_median_pips = 0 or NA excluded from PnL
# Cost per RT: half_spread (spread_median_pips/2) + slip + haircut, both sides = full RT cost
# RT_cost_pips = spread_median_pips + 2*(slip + haircut) [full round-trip]
# ─────────────────────────────────────────────────────────────────────────────

def _compute_gross_pnl_series(df_clean: pd.DataFrame, raw_signal: pd.Series) -> pd.Series:
    """Shift signal by 1 bar (no lookahead), multiply by log-return."""
    pos = raw_signal.shift(1).fillna(0.0)
    log_ret = np.log(df_clean["close"] / df_clean["close"].shift(1)).fillna(0.0)
    return pos * log_ret


def _position_changes(pos: pd.Series) -> pd.Series:
    """
    F-001 FIX (2026-06-24): Return the MAGNITUDE of position change at each bar.

    Original (buggy): returned a binary flag (pos.diff().abs() > 0).astype(float).
    A direct flip +1→−1 (diff=2) was charged the same as a simple open (diff=1) —
    one round-trip instead of two. This is fixed by using the raw absolute diff.

    Convention (matches RT cost model):
      - flat→±1 or ±1→flat: diff=1 → 1 round-trip
      - +1→−1 or −1→+1 (direct flip): diff=2 → 2 round-trips
      - no change: diff=0 → 0 cost

    Usage: cost_pips = _position_changes(pos) * rt_cost
    A flip charges 2 × rt_cost (close existing leg + open new leg). Correct.
    """
    return pos.diff().abs().fillna(0.0)


def _net_pnl_pips(
    df_clean: pd.DataFrame,
    raw_signal: pd.Series,
    pip_size: float = 0.0001,
) -> tuple[pd.Series, pd.Series, int]:
    """
    Returns (gross_pnl_pips, net_pnl_pips, n_trades) using real per-bar spreads.
    EXCLUDE-NOT-IMPUTE: bars with spread_median_pips <= 0 or NA are excluded.
    """
    # Build position series (signal at bar t, position at bar t+1)
    pos = raw_signal.shift(1).fillna(0.0)

    # Log-return in pips (close-to-close, intra-bar)
    # For JPY pairs pip_size = 0.01; we detect by pair name (caller passes pip_size)
    close = df_clean["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    gross_pnl_price = pos * log_ret  # in price units (log)
    # Convert to pips: price_move / pip_size
    gross_pnl_pips = gross_pnl_price / pip_size

    # Cost: charged on position changes only (trade events)
    changes = _position_changes(pos)
    spread = df_clean["spread_median_pips"].copy()
    # EXCLUDE-NOT-IMPUTE: zero or missing spread => exclude bar from net cost AND gross
    exclude_mask = (spread <= 0) | spread.isna()
    spread_cost = spread.where(~exclude_mask, other=0.0)  # 0 cost on excluded bars
    # Full RT cost per position change = spread + 2*(slip + haircut) [both sides]
    rt_cost = spread_cost + 2.0 * (SLIP_PIPS + HAIRCUT_PIPS)
    cost_pips = changes * rt_cost

    # Zero out gross PnL on excluded spread bars (EXCLUDE-NOT-IMPUTE)
    gross_pnl_pips = gross_pnl_pips.where(~exclude_mask, other=0.0)

    net_pnl_pips = gross_pnl_pips - cost_pips
    n_trades = int(changes.sum())

    return gross_pnl_pips, net_pnl_pips, n_trades


def _annualized_sr(pnl_series: pd.Series) -> float:
    """Annualized Sharpe ratio from hourly pnl series (sqrt(6150) annualization)."""
    mu = float(pnl_series.mean())
    sigma = float(pnl_series.std(ddof=1))
    if sigma == 0 or np.isnan(sigma):
        return float("nan")
    return (mu / sigma) * ANN_FACTOR


def run_cd0_family(pair: str, df: pd.DataFrame, pip_size: float = 0.0001) -> dict:
    """
    NOTE on pip_size: Prior QD cycle-2 used pip=0.0001 UNIFORMLY for all pairs including JPY.
    This is stated as 'pip 0.0001' in the prior cost description and is confirmed by the
    PR independent reproduction (EURJPY F2 net=-0.872 verified). We match this convention
    for comparability. For JPY pairs (physical pip=0.01), this means log_ret/0.0001 gives
    gross returns in 'non-JPY pip units', and costs are charged in the same units.
    This is internally consistent and produces comparable SRs across pairs.
    Physically the gross pips for JPY are 10x larger per move, but spread costs are expressed
    in INSTRUMENT pips (0.01 each), so both scale together — net SR is comparable.
    DISCLOSURE: Using pip=0.0001 uniform as prior canonical F1-F6 spec requires.
    """
    """Run all 6 families on one pair. Returns dict of results."""
    results = {}

    # ── F1: hourly reversal ──────────────────────────────────────────────────
    # Signal = -sign(close - open), trades every bar
    f1_raw = -np.sign(df["close"] - df["open"]).replace(0, np.nan).ffill().fillna(0.0)
    g1, n1, nt1 = _net_pnl_pips(df, f1_raw, pip_size)
    results["F1_hourly_reversal"] = {
        "gross_SR": round(_annualized_sr(g1), 4),
        "net_SR": round(_annualized_sr(n1), 4),
        "n_trades": nt1,
    }

    # ── F2: session-open momentum ────────────────────────────────────────────
    # Enter at 07:00 UTC bar; signal = sign of the 07:00 bar's return
    # "session-open" = first London hour (07:00 UTC)
    is_session_open = (df.index.hour == 7)
    session_ret = np.log(df["close"] / df["open"])
    f2_raw = pd.Series(0.0, index=df.index)
    f2_raw.loc[is_session_open] = np.sign(session_ret.loc[is_session_open])
    # Position: hold 1 bar after session open signal (shift(1) applied in _net_pnl_pips)
    # But for session-open we want signal to fire AT 07:00 and hold only THAT bar's next bar
    # So raw_signal = sign at 07:00 hours, 0 elsewhere → position = shift(1) of that
    g2, n2, nt2 = _net_pnl_pips(df, f2_raw, pip_size)
    results["F2_session_open_mom"] = {
        "gross_SR": round(_annualized_sr(g2), 4),
        "net_SR": round(_annualized_sr(n2), 4),
        "n_trades": nt2,
    }

    # ── F3: intraday momentum 3-bar ──────────────────────────────────────────
    # Signal = sign(sum of last 3 bar log-returns)
    log_ret = np.log(df["close"] / df["close"].shift(1))
    f3_raw = np.sign(log_ret.rolling(3).sum()).fillna(0.0)
    g3, n3, nt3 = _net_pnl_pips(df, f3_raw, pip_size)
    results["F3_intraday_mom_3"] = {
        "gross_SR": round(_annualized_sr(g3), 4),
        "net_SR": round(_annualized_sr(n3), 4),
        "n_trades": nt3,
    }

    # ── F4: vol breakout ─────────────────────────────────────────────────────
    # Signal = sign(close - open) if range > rolling_24h_max_range * 0.5, else 0
    bar_range = df["high"] - df["low"]
    max_range_24h = bar_range.rolling(24).max().shift(1)  # shift to avoid lookahead
    is_breakout = bar_range > (max_range_24h * 0.5)
    f4_raw = pd.Series(0.0, index=df.index)
    f4_raw.loc[is_breakout] = np.sign(df["close"] - df["open"]).loc[is_breakout]
    g4, n4, nt4 = _net_pnl_pips(df, f4_raw, pip_size)
    results["F4_vol_breakout"] = {
        "gross_SR": round(_annualized_sr(g4), 4),
        "net_SR": round(_annualized_sr(n4), 4),
        "n_trades": nt4,
    }

    # ── F5: London AM drift ───────────────────────────────────────────────────
    # Enter at London open (08:00 UTC), exit at London midday (12:00 UTC).
    # Signal = sign(08:00 open vs prior close). Hold for 4 hours.
    # Implementation: signal fires at 08:00, holds for 4 bars (08-11 inclusive),
    # then closes (signal=0) at 12:00.
    # Use the prior-close-to-08:00-open direction as the entry signal.
    prior_close = df["close"].shift(1)
    f5_raw = pd.Series(0.0, index=df.index)
    # Signal at 08:00: sign(open - prior_close)
    at_8 = (df.index.hour == 8)
    f5_raw.loc[at_8] = np.sign(df["open"].loc[at_8] - prior_close.loc[at_8])
    # Forward fill for 4 bars (08, 09, 10, 11), close at 12 (zero)
    # Build position explicitly: at 08 signal, hold 4 bars
    pos_f5 = pd.Series(0.0, index=df.index)
    signal_at_8 = f5_raw.copy()
    for shift_val in range(4):
        pos_f5 += signal_at_8.shift(shift_val + 1).fillna(0.0)
    # Clip to [-1, 1] — we only want the direction, not accumulation
    pos_f5 = pos_f5.clip(-1, 1)
    # Compute PnL directly with this position (no additional shift — already shifted above)
    log_ret_f5 = np.log(df["close"] / df["close"].shift(1)).fillna(0.0)
    gross_pnl_f5 = pos_f5 * log_ret_f5 / pip_size
    # EXCLUDE-NOT-IMPUTE
    exclude_mask_f5 = (df["spread_median_pips"] <= 0) | df["spread_median_pips"].isna()
    gross_pnl_f5 = gross_pnl_f5.where(~exclude_mask_f5, other=0.0)
    # Cost on position changes
    changes_f5 = _position_changes(pos_f5)
    spread_f5 = df["spread_median_pips"].where(~exclude_mask_f5, other=0.0)
    rt_cost_f5 = spread_f5 + 2.0 * (SLIP_PIPS + HAIRCUT_PIPS)
    net_pnl_f5 = gross_pnl_f5 - changes_f5 * rt_cost_f5
    nt5 = int(changes_f5.sum())
    results["F5_london_am_drift"] = {
        "gross_SR": round(_annualized_sr(gross_pnl_f5), 4),
        "net_SR": round(_annualized_sr(net_pnl_f5), 4),
        "n_trades": nt5,
    }

    # ── F6: spread-filtered reversal ─────────────────────────────────────────
    # F1 but only when spread_median_pips < median spread (filter out illiquid bars)
    spread_threshold = float(df["spread_median_pips"].median())
    f6_raw = f1_raw.copy()
    f6_raw.loc[df["spread_median_pips"] >= spread_threshold] = 0.0
    g6, n6, nt6 = _net_pnl_pips(df, f6_raw, pip_size)
    results["F6_spread_filt_reversal"] = {
        "gross_SR": round(_annualized_sr(g6), 4),
        "net_SR": round(_annualized_sr(n6), 4),
        "n_trades": nt6,
    }

    return results


def run_c3_cd0(pairs: list[str]) -> dict:
    """Run CD0 screen for all pairs. Returns nested dict keyed by pair then family."""
    all_results = {}
    for pair in pairs:
        # Use uniform pip=0.0001 for ALL pairs to match prior QD canonical F1-F6 convention.
        # See run_cd0_family docstring for disclosure.
        pip_size = 0.0001
        df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
        # Ensure datetime index is UTC
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        elif str(df.index.tz) != "UTC":
            df.index = df.index.tz_convert("UTC")

        family_results = run_cd0_family(pair, df, pip_size)
        all_results[pair] = {
            "pip_size": pip_size,
            "n_bars_total": len(df),
            "families": family_results,
        }
    return all_results


def verdict(net_sr: float) -> str:
    if net_sr >= 1.76:
        return "PASS"
    elif net_sr >= 1.44:
        return "STRETCH"
    else:
        return "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("9-PAIRS READINESS COMPUTE: C1, C2, C3")
    print("=" * 70)

    # ── C1: DQ gate ──────────────────────────────────────────────────────────
    print("\n── C1: DQ GATE (EURGBP, AUDJPY) ──")
    config = load_gate_config()

    dq_manifest = {}
    for pair in NEW_CROSSES:
        path = DATA_DIR / f"{pair}_1h.parquet"
        r = coverage_gate(path, pair, config, trade_window="5yr")
        detail = dq_detail(pair, r)
        pp_cfg = config["per_pair"][pair]
        detail["gate_spread_median_ceiling"] = pp_cfg["spread_median_ceiling"]
        detail["gate_p90_ceiling"] = pp_cfg["spread_p90_ceiling"]
        dq_manifest[pair] = detail

        print(f"\n  {pair}:")
        print(f"    n_rows          = {detail['n_rows']}")
        print(f"    UTC range       = {detail['utc_range']}")
        print(f"    bar_coverage    = {detail['bar_coverage_pct']}%")
        print(f"    spread_coverage = {detail['measured_spread_coverage_pct']}%")
        print(f"    max_gap_h       = {detail['max_contiguous_gap_h']}")
        print(f"    spread_median   = {detail['spread_median_pips_global']} pips (ceil={detail['gate_spread_median_ceiling']})")
        print(f"    spread_p90_med  = {detail['spread_p90_pips_global_median']} pips (ceil={detail['gate_p90_ceiling']})")
        print(f"    spread_p90_of_spread_median = {detail['spread_p90_of_spread_median']} pips")
        print(f"    spread_max      = {detail['spread_max']} pips")
        print(f"    frac_above_5pip = {detail['frac_bars_above_5pips']:.2%}")
        print(f"    n_zero_spread   = {detail['n_zero_spread_bars']}")
        print(f"    n_missing_spread= {detail['n_missing_spread_bars']}")
        print(f"    VERDICT         = {detail['verdict']}")
        if detail['issues']:
            for issue in detail['issues']:
                print(f"    ISSUE: {issue}")
        if detail['spread_flags']:
            for flag in detail['spread_flags']:
                print(f"    FLAG: {flag}")

    # ── C2: rho_bar_eff ──────────────────────────────────────────────────────
    print("\n── C2: rho_bar_eff (eigenvalue/sign-blind) ──")

    # Prior reference values
    PRIOR_ALL7_RHO  = 0.502
    PRIOR_ALL7_NEFF = 1.74
    PRIOR_USD6_RHO  = 0.597
    PRIOR_USD6_NEFF = 1.51

    subsets = {
        "ALL_9":      ALL_9,
        "USD_majors_7": USD_7,
        "USD_majors_6": USD_6,
        "CROSSES_only": CROSSES,
    }

    # Determine candidate cross-inclusive subsets based on DQ verdicts
    # We always compute the ones required regardless
    c2_results = {}
    for label, pairs in subsets.items():
        res = compute_rho_bar_eff(pairs)
        c2_results[label] = res
        delta_rho = res["rho_bar_eff"] - PRIOR_ALL7_RHO if "ALL" in label else None
        direction = ""
        if res["rho_bar_eff"] <= 0.41:
            direction = "BELOW GATE ✓"
        else:
            direction = f"ABOVE GATE (breach {res['rho_bar_eff']:.4f} > 0.41)"

        print(f"\n  {label} (k={res['k']}, n_obs={res['n_obs']}):")
        print(f"    lambda_max    = {res['lambda_max']}")
        print(f"    PC1           = {res['PC1']:.1%}")
        print(f"    rho_bar_eff   = {res['rho_bar_eff']}  [{direction}]")
        print(f"    N_eff (min)   = {res['N_eff_min']}")
        print(f"    N_eff routes  = route1={res['N_eff_route1_k_over_lambda']} / route2(PR)={res['N_eff_route2_PR']} / route3(ENB)={res['N_eff_route3_ENB']}")
        print(f"    mean_signed   = {res['mean_signed_corr']} (NOT gate stat)")

    # Delta computations
    print("\n  Deltas vs prior:")
    for label, res in c2_results.items():
        prior_rho = PRIOR_ALL7_RHO if label in ("ALL_9", "USD_majors_7") else PRIOR_USD6_RHO if label == "USD_majors_6" else None
        if prior_rho is not None:
            delta = res["rho_bar_eff"] - prior_rho
            arrow = "↑ worse" if delta > 0 else "↓ better" if delta < 0 else "→ same"
            print(f"    {label}: rho_bar_eff {res['rho_bar_eff']} vs prior {prior_rho} → delta={delta:+.4f} ({arrow})")

    # Pairwise correlation with the two new crosses
    print("\n  Pairwise corr (ALL-9):")
    corr_9 = pairwise_corr_matrix(ALL_9)
    print(corr_9.to_string())

    print("\n  Cross-pair correlations for new pairs:")
    for new_p in NEW_CROSSES:
        if new_p in corr_9.columns:
            row = corr_9[new_p].drop(new_p)
            print(f"    {new_p}: " + "  ".join(f"{p}={v:.3f}" for p, v in row.items()))

    # ── C3: CD0 ──────────────────────────────────────────────────────────────
    print("\n── C3: CD0 NET-SR WITH REAL SPREADS ──")
    print("  Running new crosses (EURGBP, AUDJPY) first, then all 7 prior pairs")

    # Run new crosses
    c3_new = run_c3_cd0(NEW_CROSSES)

    print("\n  NEW CROSSES (EURGBP, AUDJPY):")
    print(f"  {'Pair':<10} {'Family':<25} {'Gross SR':>10} {'Net SR':>10} {'N_trades':>10} {'Verdict':<10}")
    print("  " + "-" * 75)
    for pair, pdata in c3_new.items():
        for fname, fdata in pdata["families"].items():
            v = verdict(fdata["net_SR"])
            print(f"  {pair:<10} {fname:<25} {fdata['gross_SR']:>10.4f} {fdata['net_SR']:>10.4f} {fdata['n_trades']:>10} {v:<10}")

    # Run prior 7 pairs (to check if real spreads materially change results)
    print("\n  PRIOR 7 PAIRS (with real spreads — comparison vs config-median prior):")
    c3_prior = run_c3_cd0(USD_7)
    print(f"  {'Pair':<10} {'Family':<25} {'Gross SR':>10} {'Net SR':>10} {'N_trades':>10} {'Verdict':<10}")
    print("  " + "-" * 75)
    for pair, pdata in c3_prior.items():
        for fname, fdata in pdata["families"].items():
            v = verdict(fdata["net_SR"])
            print(f"  {pair:<10} {fname:<25} {fdata['gross_SR']:>10.4f} {fdata['net_SR']:>10.4f} {fdata['n_trades']:>10} {v:<10}")

    # Summary: any STRETCH or PASS?
    print("\n  SUMMARY — best net SR per pair:")
    all_c3 = {**c3_new, **c3_prior}
    for pair, pdata in all_c3.items():
        best_net = max(fdata["net_SR"] for fdata in pdata["families"].values())
        best_fam = max(pdata["families"].items(), key=lambda x: x[1]["net_SR"])[0]
        v = verdict(best_net)
        print(f"    {pair}: best_net={best_net:.4f} ({best_fam}) → {v}")

    # ── Save structured results ───────────────────────────────────────────────
    import json
    out = {
        "C1_dq_manifest": {p: {k: str(v) if not isinstance(v, (int, float, str, list, dict, bool, type(None))) else v
                               for k, v in d.items()} for p, d in dq_manifest.items()},
        "C2_rho_bar_eff": c2_results,
        "C3_cd0_new_crosses": {p: pdata for p, pdata in c3_new.items()},
        "C3_cd0_prior_7": {p: pdata for p, pdata in c3_prior.items()},
    }
    out_json = ARTIFACT_DIR / "compute_9pairs_raw.json"
    with out_json.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Raw results saved to: {out_json}")
    print("\n── DONE ──")
