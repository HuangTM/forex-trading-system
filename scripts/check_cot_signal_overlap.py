#!/usr/bin/env python3
"""Signal-only check: does COT speculative positioning just restate carry?

Run BEFORE any COT pre-registration. Reads only interest rates and COT positions;
it never loads spot rates, so no return of any kind can be computed. Question: if
positioning ranks track carry ranks, "carry rank - positioning rank" cancels into
noise and the trial is not worth spending.

Timing mirrors run_fx_multifactor.py --pit-rates: weights formed at the end of
month t use each rate no earlier than its publication, and the latest COT report
released (as-of Tuesday + 3 days, 15:30 ET) strictly before the month's last
business day. Shutdown-delayed releases (2013, 2018-19, 2025) are NOT modelled
here; that only matters for the eventual trial, not for this overlap statistic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.download_fred_rates import PUBLICATION_LAG_MONTHS  # noqa: E402
from scripts.run_fx_multifactor import (  # noqa: E402
    CCYS, FIRST_RETURN_MONTH, LAST_RETURN_MONTH, POST_PUB_START, load_rates, rank_weights,
)

COT_PATH = _PROJECT_ROOT / "data/factors/raw/cot_legacy_fx.csv"
OUT = _PROJECT_ROOT / "data/results/cot_signal_overlap_2026-10-29.json"
FOREIGN = [c for c in CCYS if c != "USD"]
Z_WINDOW_WEEKS = 156  # 3-year own-history window for the time-series crowding z-score


def load_cot() -> pd.DataFrame:
    """Weekly net speculative position / open interest per foreign currency."""
    d = pd.read_csv(COT_PATH, parse_dates=["as_of"])
    d = d[d["ccy"].isin(FOREIGN)]
    d["net_oi"] = (d["noncomm_long"] - d["noncomm_short"]) / d["open_interest"]
    d["release"] = d["as_of"] + pd.Timedelta(days=3)
    return d


def positioning_at(cot: pd.DataFrame, t: pd.Period) -> tuple[pd.Series, pd.Series]:
    """Level and own-history z-score of net/OI, from reports released before formation."""
    formation = pd.offsets.BMonthEnd().rollforward(t.start_time)  # last business day of t
    level, z = {}, {}
    for c, g in cot.groupby("ccy"):
        g = g[g["release"] < formation].sort_values("as_of")
        if g.empty or (formation - g["as_of"].iloc[-1]).days > 45:
            continue  # no report, or too stale to use
        level[c] = g["net_oi"].iloc[-1]
        hist = g["net_oi"].iloc[-Z_WINDOW_WEEKS:]
        if len(hist) >= Z_WINDOW_WEEKS // 2 and hist.std() > 0:
            z[c] = (hist.iloc[-1] - hist.mean()) / hist.std()
    return pd.Series(level, dtype=float), pd.Series(z, dtype=float)


def spearman(a: pd.Series, b: pd.Series) -> float:
    idx = a.dropna().index.intersection(b.dropna().index)
    if len(idx) < 4:
        return np.nan
    return float(a[idx].rank().corr(b[idx].rank()))


def summarize(s: pd.Series) -> dict:
    s = s.dropna()
    return {"n_months": int(len(s)), "mean": round(float(s.mean()), 3),
            "median": round(float(s.median()), 3),
            "share_gt_0.5": round(float((s > 0.5).mean()), 3),
            "share_lt_0": round(float((s < 0).mean()), 3)}


def main() -> int:
    rates = load_rates()
    lags = {c: max(1, PUBLICATION_LAG_MONTHS[c] - 1) for c in CCYS}
    cot = load_cot()
    months = pd.period_range(FIRST_RETURN_MONTH, LAST_RETURN_MONTH, freq="M") - 1

    rows, w_carry, w_pos, w_comp = [], {}, {}, {}
    for t in months:
        carry = pd.Series({c: rates.at[t - lags[c], c] for c in FOREIGN})
        level, z = positioning_at(cot, t)
        rows.append({"t": t, "level": spearman(carry, level), "z": spearman(carry, z),
                     "n_ccy": int(level.notna().sum())})
        common = carry.index.intersection(level.index)
        rc, rp = carry[common].rank(), level[common].rank()
        w_carry[t] = rank_weights(carry[common].reindex(CCYS))
        w_pos[t] = rank_weights(level.reindex(CCYS))
        w_comp[t] = rank_weights((rc - rp).reindex(CCYS))

    df = pd.DataFrame(rows).set_index("t")
    post = df.index >= pd.Period(POST_PUB_START, "M")
    wc, wp, wm = (pd.DataFrame(w).T for w in (w_carry, w_pos, w_comp))
    comp_vs_carry = [float(np.corrcoef(wm.loc[t], wc.loc[t])[0, 1])
                     for t in wm.index if wm.loc[t].abs().sum() > 0 and wc.loc[t].abs().sum() > 0]

    result = {
        "note": "signals only; no spot or return data was read",
        "universe": FOREIGN,
        "cross_sectional_spearman_carry_vs_positioning_level": {
            "full": summarize(df["level"]), "pre_2012": summarize(df.loc[~post, "level"]),
            "post_2012": summarize(df.loc[post, "level"])},
        "cross_sectional_spearman_carry_vs_positioning_zscore_3y": {
            "full": summarize(df["z"]), "pre_2012": summarize(df.loc[~post, "z"]),
            "post_2012": summarize(df.loc[post, "z"])},
        "composite_weights_corr_with_carry_weights": summarize(pd.Series(comp_vs_carry)),
        "mean_monthly_turnover_sum_abs_dw": {
            "carry": round(float(wc.diff().abs().sum(axis=1).mean()), 3),
            "positioning_level": round(float(wp.diff().abs().sum(axis=1).mean()), 3),
            "composite": round(float(wm.diff().abs().sum(axis=1).mean()), 3)},
        "months_with_fewer_than_6_currencies": int((df["n_ccy"] < 6).sum()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
