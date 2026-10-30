#!/usr/bin/env python3
"""Carry with a speculative-crowding overlay (CFTC COT), monthly — trial #36.

Pre-registration: references/pre-registrations/fx_cot_crowding_carry_monthly.md
(every rule below is fixed there). Universe, spot, rates, costs and statistics are
reused from scripts/run_fx_multifactor.py so the two trials are directly comparable;
rates enter with their measured publication lags (as --pit-rates there).

--smoke builds signals and weights only and never loads spot, so it computes no return.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from forex_system.harness.dsr import compute_dsr  # noqa: E402
from scripts.download_fred_rates import PUBLICATION_LAG_MONTHS  # noqa: E402
from scripts.run_fx_multifactor import (  # noqa: E402
    CCYS, COSTS, FIRST_RETURN_MONTH, FOREIGN, LAST_RETURN_MONTH, POST_PUB_START,
    boot_p, excess_returns, load_rates, load_spot, portfolio_returns, rank_weights,
)

PRE_REG_PATH = "references/pre-registrations/fx_cot_crowding_carry_monthly.md"
COT_PATH = _PROJECT_ROOT / "data/factors/raw/cot_legacy_fx.csv"
N_TRIALS = 36
Z_WINDOW = 156          # weekly reports (3 years)
Z_MIN = 78
STALE_DAYS = 45
CROWD_Z = 1.0
CUT = 0.5
RELEASE_LAG_DAYS = 6    # usable iff as_of + 6 days < formation date

# Government-shutdown overrides, keyed by formation-date window.
FROZEN = [  # (window start, window end, latest usable as-of)
    ("2013-10-01", "2013-11-07", "2013-09-24"),
    ("2018-12-22", "2019-03-07", "2018-12-18"),
]
SHUTDOWN_2025 = ("2025-10-01", "2025-12-28")
RELEASED_2025 = {  # as-of -> release date (CFTC notice of 2025-12-09)
    "2025-09-30": "2025-11-19", "2025-10-07": "2025-11-21", "2025-10-14": "2025-11-25",
    "2025-10-21": "2025-12-02", "2025-10-28": "2025-12-05", "2025-11-04": "2025-12-09",
    "2025-11-10": "2025-12-10", "2025-11-18": "2025-12-12", "2025-11-25": "2025-12-15",
    "2025-12-02": "2025-12-17", "2025-12-09": "2025-12-19", "2025-12-16": "2025-12-23",
    "2025-12-23": "2025-12-29",
}


def load_cot() -> pd.DataFrame:
    d = pd.read_csv(COT_PATH, parse_dates=["as_of"])
    d = d[d["ccy"].isin(FOREIGN)].copy()
    d["net_oi"] = (d["noncomm_long"] - d["noncomm_short"]) / d["open_interest"]
    return d.sort_values(["ccy", "as_of"])


def usable_reports(g: pd.DataFrame, formation: pd.Timestamp) -> tuple[pd.DataFrame, bool]:
    """Reports usable at the formation date; second value = inside a shutdown window."""
    for start, end, last in FROZEN:
        if pd.Timestamp(start) <= formation <= pd.Timestamp(end):
            return g[g["as_of"] <= pd.Timestamp(last)], True
    normal = g["as_of"] + pd.Timedelta(days=RELEASE_LAG_DAYS) < formation
    if pd.Timestamp(SHUTDOWN_2025[0]) <= formation <= pd.Timestamp(SHUTDOWN_2025[1]):
        rel = g["as_of"].dt.strftime("%Y-%m-%d").map(RELEASED_2025)
        late = rel.notna()
        ok = (~late & normal & (g["as_of"] < pd.Timestamp("2025-09-30"))) | (
            late & (pd.to_datetime(rel) < formation))
        return g[ok], True
    return g[normal], False


def crowding_z(cot: pd.DataFrame, formation: pd.Timestamp) -> pd.Series:
    z = {}
    for c in FOREIGN:
        g, in_shutdown = usable_reports(cot[cot["ccy"] == c], formation)
        hist = g["net_oi"].iloc[-Z_WINDOW:]
        stale = g.empty or (not in_shutdown and (formation - g["as_of"].iloc[-1]).days > STALE_DAYS)
        if stale or len(hist) < Z_MIN or hist.std() == 0:
            z[c] = 0.0
        else:
            z[c] = float((hist.iloc[-1] - hist.mean()) / hist.std())
    return pd.Series(z)


def build_weights(rates: pd.DataFrame, cot: pd.DataFrame) -> dict[str, pd.DataFrame]:
    lags = {c: max(1, PUBLICATION_LAG_MONTHS[c] - 1) for c in CCYS}
    months = pd.period_range(FIRST_RETURN_MONTH, LAST_RETURN_MONTH, freq="M") - 1
    carry, overlay, crowded = {}, {}, {}
    for t in months:
        w0 = rank_weights(pd.Series({c: rates.at[t - lags[c], c] for c in CCYS}))
        formation = pd.offsets.BMonthEnd().rollforward(t.start_time)
        s = crowding_z(cot, formation) * np.sign(w0[FOREIGN])
        cut = s > CROWD_Z
        w1 = w0.copy()
        w1[cut[cut].index] *= CUT
        g0, g1 = w0[FOREIGN].abs().sum(), w1[FOREIGN].abs().sum()
        if g1 > 0:
            w1[FOREIGN] *= g0 / g1
        w1["USD"] = -w1[FOREIGN].sum()
        carry[t], overlay[t], crowded[t] = w0, w1, cut
    return {"carry": pd.DataFrame(carry).T, "overlay": pd.DataFrame(overlay).T,
            "crowded": pd.DataFrame(crowded).T}


def summarize(r: pd.Series) -> dict:
    x = r.to_numpy()
    sr = float(x.mean() / x.std() * np.sqrt(12)) if x.std() > 0 else 0.0
    eq = np.exp(np.cumsum(x))
    return {
        "sharpe": round(sr, 3),
        "t": round(float(x.mean() / (x.std() / np.sqrt(len(x)))), 2),
        "p_boot": round(boot_p(x), 4),
        "dsr_n36": round(compute_dsr(sr, len(x), float(stats.skew(x)), float(stats.kurtosis(x)),
                                     N_TRIALS, 12.0), 4),
        "ann_return": round(float(x.mean()) * 12, 4),
        "ann_vol": round(float(x.std()) * np.sqrt(12), 4),
        "max_dd": round(float(1 - (eq / np.maximum.accumulate(eq)).min()), 4),
        "n_months": len(x),
    }


def paired(d: pd.Series) -> dict:
    x = d.to_numpy()
    return {
        "mean_monthly": float(x.mean()),
        "ann_mean": round(float(x.mean()) * 12, 5),
        "t": round(float(x.mean() / (x.std() / np.sqrt(len(x)))), 2),
        "p_boot_one_sided": round(boot_p(x), 4),
        "info_ratio": round(float(x.mean() / x.std() * np.sqrt(12)), 3) if x.std() > 0 else 0.0,
        "n_months": len(x),
    }


def verdict(full_d: dict, post_d: dict, ov_full: dict, ov_post: dict) -> str:
    if full_d["mean_monthly"] <= 0 or post_d["mean_monthly"] <= 0 or ov_full["sharpe"] <= 0:
        return "FAIL"
    if (full_d["p_boot_one_sided"] <= 0.05 and ov_full["dsr_n36"] >= 0.95
            and ov_post["sharpe"] > 0):
        return "PASS"
    if full_d["p_boot_one_sided"] <= 0.05:
        return "INCONCLUSIVE_IMPROVES_CARRY"
    return "INCONCLUSIVE"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--smoke", action="store_true", help="signals and weights only (no spot)")
    ap.add_argument("--out", default="data/results/fx_cot_crowding_carry_monthly.json")
    args = ap.parse_args()
    if not (_PROJECT_ROOT / PRE_REG_PATH).exists():
        print(f"ERROR: pre-registration missing: {PRE_REG_PATH}")
        return 1

    w = build_weights(load_rates(), load_cot())
    if args.smoke:
        for k in ("carry", "overlay"):
            x = w[k]
            print(f"  smoke {k:8s}: {len(x)} months {x.index[0]}..{x.index[-1]}, "
                  f"max|sum w| {x.sum(axis=1).abs().max():.1e}, "
                  f"foreign gross {x[FOREIGN].abs().sum(axis=1).min():.2f}-"
                  f"{x[FOREIGN].abs().sum(axis=1).max():.2f}, NaN {int(x.isna().sum().sum())}")
        gross_gap = (w["overlay"][FOREIGN].abs().sum(axis=1)
                     - w["carry"][FOREIGN].abs().sum(axis=1)).abs().max()
        n_cut = w["crowded"].sum(axis=1)
        print(f"  smoke foreign-gross mismatch overlay vs carry: {gross_gap:.1e}")
        print(f"  smoke crowded legs/month: mean {n_cut.mean():.2f}, months with >=1: "
              f"{int((n_cut > 0).sum())}/{len(n_cut)}, by ccy {w['crowded'].sum().to_dict()}")
        return 0

    spot, rates = load_spot(), load_rates()
    xs = excess_returns(spot, rates)
    post = pd.Period(POST_PUB_START, "M")
    window = slice(FIRST_RETURN_MONTH, LAST_RETURN_MONTH)
    results: dict = {"cells": {}, "paired": {}, "per_year_d": {}}
    for cost in COSTS:
        r = {k: portfolio_returns(w[k], xs, spot, cost).loc[window] for k in ("carry", "overlay")}
        for k, s in r.items():
            results["cells"][f"{k}|{cost}"] = {
                "full": summarize(s), "pre_2012": summarize(s[s.index < post]),
                "post_2012": summarize(s[s.index >= post])}
        d = r["overlay"] - r["carry"]
        results["paired"][cost] = {"full": paired(d), "pre_2012": paired(d[d.index < post]),
                                   "post_2012": paired(d[d.index >= post])}
        if cost == "base":
            results["per_year_d"] = {int(y): round(float(g.sum()) * 100, 3)
                                     for y, g in d.groupby(d.index.year)}
    for k in ("carry", "overlay"):
        results[f"turnover_{k}"] = round(float(w[k][FOREIGN].diff().abs().sum(axis=1).mean()), 3)
    results["crowded_legs_by_ccy"] = {c: int(v) for c, v in w["crowded"].sum().items()}

    pb, ob = results["paired"]["base"], results["cells"]["overlay|base"]
    v = verdict(pb["full"], pb["post_2012"], ob["full"], ob["post_2012"])
    out = _PROJECT_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pre_registration": PRE_REG_PATH,
        "summary": {"verdict": v},
        **results,
    }, indent=2, default=str))
    print(f"Saved {out}\nVerdict: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
