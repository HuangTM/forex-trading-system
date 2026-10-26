#!/usr/bin/env python3
"""Currency-level carry + value + momentum, monthly, 7 currencies (G7 FX incl. USD).

Pre-registration: references/pre-registrations/fx_multifactor_monthly.md (read it first —
signals, weights, costs, windows, statistics and the verdict rule are fixed there).

Inputs (no backtest engine — monthly portfolio arithmetic in currency space):
  spot   data/factors/raw/DEX*.csv     Fed H.10 noon NY rates (month-end value)
  value  data/factors/raw/RB*BIS.csv   BIS real broad effective exchange rates
  rates  data/rates/raw/{CCY}.csv      same audited series as the rest of the repo

Usage:
    .venv/bin/python scripts/run_fx_multifactor.py           # full run, writes results JSON
    .venv/bin/python scripts/run_fx_multifactor.py --smoke   # builds signals/weights only
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

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from forex_system.harness.dsr import compute_dsr  # noqa: E402

PRE_REG_PATH = "references/pre-registrations/fx_multifactor_monthly.md"
CCYS = ["USD", "EUR", "JPY", "GBP", "AUD", "NZD", "CAD"]
FOREIGN = CCYS[1:]
# currency -> (H.10 series, quoted as USD per unit of currency?)
SPOT = {"EUR": ("DEXUSEU", True), "GBP": ("DEXUSUK", True), "AUD": ("DEXUSAL", True),
        "NZD": ("DEXUSNZ", True), "CAD": ("DEXCAUS", False), "JPY": ("DEXJPUS", False)}
REER = {"USD": "RBUSBIS", "EUR": "RBXMBIS", "JPY": "RBJPBIS", "GBP": "RBGBBIS",
        "AUD": "RBAUBIS", "NZD": "RBNZBIS", "CAD": "RBCABIS"}
# Trading pair per currency: (pair, pip size, Dukascopy 2021-25 median full spread in pips)
PAIRS = {"EUR": ("EURUSD", 1e-4, 0.3), "GBP": ("GBPUSD", 1e-4, 0.9), "AUD": ("AUDUSD", 1e-4, 1.0),
         "NZD": ("NZDUSD", 1e-4, 1.1), "CAD": ("USDCAD", 1e-4, 1.3), "JPY": ("USDJPY", 1e-2, 0.6)}
SLIP_PIPS = 0.4            # per side (firm CD0 convention)
COSTS = {"gross": (0.0, 0.0), "base": (1.0, 0.005), "high": (2.0, 0.010)}  # (cost mult, markup/yr)
FIRST_RETURN_MONTH = "2001-01"
LAST_RETURN_MONTH = "2026-09"
POST_PUB_START = "2012-01"
N_TRIALS = 35
BOOT_REPS = 10_000
BOOT_BLOCK = 6  # months


def _read(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy(),
                  index=pd.to_datetime(df.iloc[:, 0]))
    return s.dropna().sort_index()


def load_spot() -> pd.DataFrame:
    """Month-end USD per unit of each currency (USD = 1), indexed by month Period."""
    out = {"USD": None}
    for c, (sid, usd_per) in SPOT.items():
        s = _read(_PROJECT_ROOT / "data/factors/raw" / f"{sid}.csv")
        out[c] = s if usd_per else 1.0 / s
    df = pd.DataFrame({c: s for c, s in out.items() if s is not None})
    m = df.resample("ME").last()
    m.index = m.index.to_period("M")
    m["USD"] = 1.0
    return m[CCYS]


def load_rates() -> pd.DataFrame:
    """Monthly average policy/short rate (% p.a.) per currency, by month Period."""
    cols = {}
    for c in CCYS:
        s = _read(_PROJECT_ROOT / "data/rates/raw" / f"{c}.csv")
        daily = s.reindex(pd.date_range(s.index[0], "2026-12-31", freq="D")).ffill()
        cols[c] = daily
    m = pd.DataFrame(cols).resample("ME").mean()
    m.index = m.index.to_period("M")
    return m[CCYS]


def load_reer() -> pd.DataFrame:
    m = pd.DataFrame({c: _read(_PROJECT_ROOT / "data/factors/raw" / f"{sid}.csv")
                      for c, sid in REER.items()})
    m.index = m.index.to_period("M")
    return m[CCYS]


def excess_returns(spot: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Monthly excess return of holding each currency vs USD: log spot change + rate diff."""
    ds = np.log(spot).diff()
    carry = rates.sub(rates["USD"], axis=0) / 1200.0
    return (ds + carry.reindex(ds.index)).astype(float)


def rank_weights(score: pd.Series) -> pd.Series:
    """Demeaned cross-sectional ranks scaled to sum|w| = 2 ($1 long / $1 short)."""
    s = score.dropna()
    w = pd.Series(0.0, index=CCYS)
    if len(s) < 2:
        return w
    r = s.rank(method="average")
    r = r - r.mean()
    if r.abs().sum() == 0:
        return w
    w[r.index] = 2.0 * r / r.abs().sum()
    return w


def factor_weights(spot, rates, reer, xs) -> dict[str, pd.DataFrame]:
    """Weights formed at the end of month t (index t), held during month t+1.

    Every input is as of month t-1 or earlier (one-month publication lag for rates and
    REER; momentum skips the most recent month).
    """
    months = pd.period_range(FIRST_RETURN_MONTH, LAST_RETURN_MONTH, freq="M") - 1
    log_reer = np.log(reer)
    out = {"carry": {}, "value": {}, "momentum": {}}
    for t in months:
        lag1 = t - 1
        out["carry"][t] = rank_weights(rates.loc[lag1])
        past = log_reer.loc[t - 66:t - 54].mean()
        out["value"][t] = rank_weights(-(log_reer.loc[lag1] - past))
        out["momentum"][t] = rank_weights(xs.loc[t - 11:t - 1].sum(min_count=11))
    w = {k: pd.DataFrame(v).T for k, v in out.items()}
    w["composite"] = (w["carry"] + w["value"] + w["momentum"]) / 3.0
    return w


def cost_per_unit(spot: pd.DataFrame, mult: float) -> pd.DataFrame:
    """One-way cost (return units) of trading 1 unit of each foreign currency vs USD."""
    out = {}
    for c, (pair, pip, spread) in PAIRS.items():
        pair_px = spot[c] if pair.endswith("USD") else 1.0 / spot[c]
        out[c] = mult * (spread / 2.0 + SLIP_PIPS) * pip / pair_px
    return pd.DataFrame(out)


def portfolio_returns(w: pd.DataFrame, xs: pd.DataFrame, spot: pd.DataFrame, cost: str) -> pd.Series:
    mult, markup = COSTS[cost]
    held = w.copy()
    held.index = held.index + 1                      # weights formed at t earn month t+1
    gross = (held * xs.reindex(held.index)).sum(axis=1)
    if mult == 0 and markup == 0:
        return gross
    turnover = w[FOREIGN].diff().abs()
    turnover.iloc[0] = w[FOREIGN].iloc[0].abs()
    trade_cost = (turnover * cost_per_unit(spot, mult).reindex(w.index)).sum(axis=1)
    trade_cost.index = trade_cost.index + 1
    financing = markup / 12.0 * held[FOREIGN].abs().sum(axis=1)
    return gross - trade_cost - financing


def boot_p(x: np.ndarray, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    obs = x.mean()
    y0 = x - obs
    n = len(x)
    hits = 0
    for _ in range(BOOT_REPS):
        idx = np.empty(n, dtype=int)
        i = 0
        while i < n:
            take = min(rng.geometric(1.0 / BOOT_BLOCK), n - i)
            idx[i:i + take] = (rng.integers(0, n) + np.arange(take)) % n
            i += take
        hits += y0[idx].mean() >= obs
    return hits / BOOT_REPS


def summarize(r: pd.Series) -> dict:
    x = r.to_numpy()
    sr = float(x.mean() / x.std() * np.sqrt(12)) if x.std() > 0 else 0.0
    eq = np.exp(np.cumsum(x))
    return {
        "sharpe": round(sr, 3),
        "t": round(float(x.mean() / (x.std() / np.sqrt(len(x)))), 2),
        "p_boot": round(boot_p(x), 4),
        "dsr_n35": round(compute_dsr(sr, len(x), float(stats.skew(x)), float(stats.kurtosis(x)),
                                     N_TRIALS, 12.0), 4),
        "ann_return": round(float(x.mean()) * 12, 4),
        "ann_vol": round(float(x.std()) * np.sqrt(12), 4),
        "max_dd": round(float(1 - (eq / np.maximum.accumulate(eq)).min()), 4),
        "n_months": len(x),
        "start": str(r.index[0]),
        "end": str(r.index[-1]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true", help="build signals and weights only")
    ap.add_argument("--out", default="data/results/fx_multifactor_monthly_2026-10-26.json")
    args = ap.parse_args()
    if not Path(PRE_REG_PATH).exists():
        print(f"ERROR: pre-registration missing: {PRE_REG_PATH}")
        return 1

    spot, rates, reer = load_spot(), load_rates(), load_reer()
    xs = excess_returns(spot, rates)
    weights = factor_weights(spot, rates, reer, xs)

    if args.smoke:
        for k, w in weights.items():
            gross = w.abs().sum(axis=1)
            print(f"  smoke {k:9s}: {len(w)} formation months {w.index[0]}..{w.index[-1]}, "
                  f"max|sum w| {w.sum(axis=1).abs().max():.1e}, gross {gross.min():.2f}-{gross.max():.2f}, "
                  f"NaN {int(w.isna().sum().sum())} — ok")
        return 0

    post = pd.Period(POST_PUB_START, "M")
    results: dict = {"cells": {}, "per_year": {}, "factor_correlation": {}}
    for factor, w in weights.items():
        for cost in COSTS:
            r = portfolio_returns(w, xs, spot, cost)
            r = r.loc[FIRST_RETURN_MONTH:LAST_RETURN_MONTH]
            results["cells"][f"{factor}|{cost}"] = {
                "full": summarize(r),
                "pre_2012": summarize(r[r.index < post]),
                "post_2012": summarize(r[r.index >= post]),
            }
            if cost == "base":
                results["per_year"][factor] = {int(y): round(float(g.sum()) * 100, 2)
                                               for y, g in r.groupby(r.index.year)}
    base = {f: portfolio_returns(w, xs, spot, "base").loc[FIRST_RETURN_MONTH:LAST_RETURN_MONTH]
            for f, w in weights.items() if f != "composite"}
    results["factor_correlation"] = pd.DataFrame(base).corr().round(3).to_dict()

    primary = results["cells"]["composite|base"]
    full, post_r = primary["full"], primary["post_2012"]
    if full["t"] >= 1.65 and full["dsr_n35"] >= 0.95 and post_r["sharpe"] > 0:
        verdict = "PASS"
    elif full["sharpe"] <= 0 or post_r["sharpe"] <= 0:
        verdict = "FAIL"
    else:
        verdict = "INCONCLUSIVE"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pre_registration": PRE_REG_PATH,
        "summary": {"verdict": verdict},
        **results,
    }, indent=2, default=str))
    print(f"Saved {out}\nVerdict: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
