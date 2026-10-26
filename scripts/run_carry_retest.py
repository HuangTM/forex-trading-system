#!/usr/bin/env python3
"""carry_fred retest under corrected swap accounting.

Pre-registration: references/pre-registrations/carry_fred_retest_2026-10-25.md
(read it first — it fixes every cell, window, trigger and verdict rule below).

Part A: 2010–2026 re-evaluation of Bet #1's binding triggers (NOT blind).
Part B: 2003–2009 blind holdout (needs --holdout-dir with pre-2010 daily data and
        a rate file whose EUR gap is filled).

Usage:
    .venv/bin/python scripts/run_carry_retest.py --part A
    .venv/bin/python scripts/run_carry_retest.py --part B --holdout-dir data/holdout_pre2010 \
        --rate-data data/rates/rate_differentials.parquet
    .venv/bin/python scripts/run_carry_retest.py --smoke    # executes only, prints no metrics
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from forex_system.backtest.engine import run_backtest  # noqa: E402
from forex_system.core.config import load_config  # noqa: E402
from forex_system.costs.model import (  # noqa: E402
    RateDifferentialSwapCostModel,
    RealisticCostModel,
)
from forex_system.data.storage import load_parquet  # noqa: E402
from forex_system.features.registry import compute_indicators  # noqa: E402
from forex_system.harness.dsr import compute_dsr  # noqa: E402
from forex_system.strategies.carry_fred import CarryFREDStrategy  # noqa: E402

PAIRS = [
    "AUDJPY", "AUDUSD", "CADJPY", "EURGBP", "EURJPY", "EURUSD",
    "GBPJPY", "GBPUSD", "NZDJPY", "NZDUSD", "USDCAD", "USDJPY",
]
JPY_CROSSES = ["AUDJPY", "CADJPY", "EURJPY", "GBPJPY", "NZDJPY", "USDJPY"]
CONFIG_PATH = "config/carry_fred.yaml"
PRE_REG_PATH = "references/pre-registrations/carry_fred_retest_2026-10-25.md"
TRADING_DAYS = 252
TARGET_VOL = 0.10
N_TRIALS = 33          # honest-N: ledger 32 + this retest
BOOT_REPS = 10_000
BOOT_BLOCK = 20

# Part A windows (pre-registered)
A_END = "2026-04-06"
A_OOS_START = "2023-04-25"
# Part B window (pre-registered)
B_START = "2003-01-01"
B_END = "2009-12-31"

VARIANTS = {
    "V1_clip": {"rank_normalize": True, "min_differential": 0.001, "selection": "clip"},
    "V2_quintile": {"rank_normalize": True, "min_differential": 0.001, "selection": "quintile"},
    "V3_sign": {"rank_normalize": False, "min_differential": 0.001, "max_differential": 0.05},
}
# name -> (swap model, markup, transaction-cost multiplier)
COSTS = {
    "C1_static": ("static", 0.0, 1.0),
    "C2_rate_m0.5": ("rate", 0.005, 1.0),
    "C3_rate_m0.0": ("rate", 0.0, 1.0),
    "C4_rate_m1.0": ("rate", 0.010, 1.0),
    "C2x2": ("rate", 0.010, 2.0),
}
CELLS_A = [
    ("V1_clip", "C1_static"), ("V1_clip", "C2_rate_m0.5"), ("V1_clip", "C3_rate_m0.0"),
    ("V1_clip", "C4_rate_m1.0"), ("V1_clip", "C2x2"),
    ("V2_quintile", "C2_rate_m0.5"), ("V2_quintile", "C2x2"),
    ("V3_sign", "C2_rate_m0.5"),
    ("JPY_basket", "C2_rate_m0.5"),
]
CELLS_B = [
    ("V1_clip", "C2_rate_m0.5"), ("V1_clip", "C1_static"), ("V2_quintile", "C2_rate_m0.5"),
    ("V3_sign", "C2_rate_m0.5"), ("JPY_basket", "C2_rate_m0.5"),
]


def _naive(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_convert("UTC").tz_localize(None) if idx.tz is not None else idx


def load_prices(pairs: list[str], holdout_dir: Path | None, end: str) -> dict[str, pd.DataFrame]:
    """Daily OHLCV + atr_14 per pair, truncated at ``end``. Missing pairs are skipped."""
    out = {}
    for pair in pairs:
        if holdout_dir is None:
            df = load_parquet(pair, "daily", "data")
        else:
            path = holdout_dir / f"{pair}_daily.parquet"
            if not path.exists():
                print(f"  {pair}: no holdout file — flat in portfolio")
                continue
            df = pd.read_parquet(path)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
        df = df[_naive(df.index) <= pd.Timestamp(end)]
        df = compute_indicators(df, ["atr_14"]).dropna(subset=["atr_14"])
        if len(df) > 30:
            out[pair] = df
    return out


def make_cost_model(cost: str, pair: str, config, rate_data: pd.DataFrame, close: pd.Series):
    kind, markup, mult = COSTS[cost]
    info = config.get_pair_info(pair)
    if mult != 1.0:
        info = dataclasses.replace(
            info,
            spread_pips=info.spread_pips * mult,
            slippage_pips=info.slippage_pips * mult,
            commission_pips=info.commission_pips * mult,
        )
    if kind == "static":
        return RealisticCostModel({pair: info})
    return RateDifferentialSwapCostModel(
        {pair: info}, rate_differentials=rate_data, prices={pair: close}, markup=markup
    )


def run_cell(variant, cost, prices, config, rate_data) -> dict[str, pd.Series]:
    """Per-pair daily equity returns for one (variant, cost) cell."""
    rets = {}
    pairs = JPY_CROSSES if variant == "JPY_basket" else list(prices)
    for pair in pairs:
        if pair not in prices:
            continue
        data = prices[pair]
        if variant == "JPY_basket":
            signals = pd.Series(1.0, index=data.index)
        else:
            params = dict(VARIANTS[variant], pair=pair)
            signals = CarryFREDStrategy(params, rate_data=rate_data).generate_signals(data)
        model = make_cost_model(cost, pair, config, rate_data, data["close"])
        result = run_backtest(
            data=data, signals=signals, pair=pair, strategy_name=f"retest_{variant}",
            cost_model=model, initial_capital=1e6, entry_delay_bars=1,
        )
        ec = result.equity_curve.copy()
        ec.index = _naive(ec.index)
        rets[pair] = ec.pct_change().dropna()
    return rets


def sharpe(r: pd.Series) -> float:
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS)) if len(r) > 2 and r.std() > 0 else 0.0


def boot_p(r: pd.Series, seed: int = 0) -> float:
    """Stationary block bootstrap: P(SR* >= SR_obs) under demeaned returns."""
    x = (r - r.mean()).to_numpy()
    n = len(x)
    if n < 2 * BOOT_BLOCK:
        return float("nan")
    rng = np.random.default_rng(seed)
    obs = sharpe(r)
    hits = 0
    for _ in range(BOOT_REPS):
        idx = np.empty(n, dtype=int)
        i = 0
        while i < n:
            start = rng.integers(0, n)
            length = rng.geometric(1.0 / BOOT_BLOCK)
            take = min(length, n - i)
            idx[i:i + take] = (start + np.arange(take)) % n
            i += take
        y = x[idx]
        hits += (y.mean() / y.std() * np.sqrt(TRADING_DAYS)) >= obs
    return hits / BOOT_REPS


def window_stats(r: pd.Series) -> dict:
    sr = sharpe(r)
    years = len(r) / TRADING_DAYS
    eq = (1 + r).cumprod()
    return {
        "sharpe": round(sr, 4),
        "t": round(sr * np.sqrt(years), 3),
        "p_boot": round(boot_p(r), 4),
        "dsr_n33": round(compute_dsr(sr, len(r), float(stats.skew(r)),
                                     float(stats.kurtosis(r)), N_TRIALS, TRADING_DAYS), 4),
        "ann_return": round(float(eq.iloc[-1] ** (1 / years) - 1), 4) if years > 0 else None,
        "max_dd": round(float(1 - (eq / eq.cummax()).min()), 4),
        "n_obs": len(r),
        "start": str(r.index[0].date()),
        "end": str(r.index[-1].date()),
    }


def portfolio(rets: dict[str, pd.Series], weights: dict[str, float] | None) -> pd.Series:
    df = pd.DataFrame(rets).fillna(0.0)
    if weights is None:
        return df.mean(axis=1)
    w = pd.Series(weights)[df.columns]
    return (df * w).sum(axis=1)


def vol_weights(rets: dict[str, pd.Series], is_end: pd.Timestamp) -> dict[str, float]:
    raw = {}
    for pair, r in rets.items():
        rv = r[r.index < is_end].std() * np.sqrt(TRADING_DAYS)
        raw[pair] = min(TARGET_VOL / rv, 5.0) if rv > 0 else 1.0
    total = sum(raw.values())
    return {p: w / total for p, w in raw.items()}


def part_a(config, rate_data, cells, pairs, end) -> dict:
    prices = load_prices(pairs, None, end)
    oos = pd.Timestamp(A_OOS_START)
    results = {}
    for variant, cost in cells:
        print(f"  {variant} x {cost} ...")
        rets = run_cell(variant, cost, prices, config, rate_data)
        vw = vol_weights(rets, oos)
        cell = {}
        for wname, weights in (("vol_weighted", vw), ("equal_weighted", None)):
            port = portfolio(rets, weights)
            cell[wname] = {
                "IS": window_stats(port[port.index < oos]),
                "OOS": window_stats(port[port.index >= oos]),
            }
        cell["per_pair_oos_sharpe"] = {p: round(sharpe(r[r.index >= oos]), 4)
                                       for p, r in rets.items()}
        cell["per_pair_is_sharpe"] = {p: round(sharpe(r[r.index < oos]), 4)
                                      for p, r in rets.items()}
        results[f"{variant}|{cost}"] = cell
    return results


def triggers_a(results: dict, rate_data: pd.DataFrame) -> dict:
    p = results["V1_clip|C2_rate_m0.5"]
    vw_oos = p["vol_weighted"]["OOS"]
    pair_srs = list(p["per_pair_oos_sharpe"].values())
    t5 = stats.ttest_1samp(pair_srs, 0.0)
    oos_rates = rate_data.loc[A_OOS_START:A_END]
    constant = [c for c in oos_rates.columns if oos_rates[c].nunique() <= 1]
    v3 = results["V3_sign|C2_rate_m0.5"]["vol_weighted"]["OOS"]["sharpe"]
    trig = {
        "CF-T1": {"value": vw_oos["sharpe"], "fires": vw_oos["sharpe"] < 0.30},
        "CF-T2": {"value": sum(s < 0 for s in pair_srs), "fires": sum(s < 0 for s in pair_srs) > 8},
        "CF-T3": {"value": constant, "fires": bool(constant)},
        "CF-T4": {"value": vw_oos["max_dd"], "fires": vw_oos["max_dd"] > 0.40},
        "CF-T5": {"value": round(float(t5.pvalue), 4), "fires": float(t5.pvalue) > 0.10},
        "CF-T6": {"value": results["V1_clip|C2x2"]["vol_weighted"]["IS"]["sharpe"],
                  "fires": results["V1_clip|C2x2"]["vol_weighted"]["IS"]["sharpe"] < 0.20},
        "CF-T7": {"value": round(vw_oos["sharpe"] - v3, 4), "fires": None,
                  "note": "wording internally inconsistent; reported, not used for verdict"},
        "CF-T8": {"value": p["vol_weighted"]["IS"]["sharpe"],
                  "fires": p["vol_weighted"]["IS"]["sharpe"] < 0.40},
    }
    fired = [k for k, v in trig.items() if v["fires"] is True]
    return {"triggers": trig, "fired": fired, "verdict": "PASS" if not fired else "FAIL"}


def part_b(config, rate_data, holdout_dir: Path) -> dict:
    prices = load_prices(PAIRS, holdout_dir, B_END)
    start = pd.Timestamp(B_START)
    coverage = {p: [str(_naive(d.index)[0].date()), str(_naive(d.index)[-1].date())]
                for p, d in prices.items()}
    results = {"coverage": coverage}
    for variant, cost in CELLS_B:
        print(f"  {variant} x {cost} ...")
        rets = run_cell(variant, cost, prices, config, rate_data)
        rets = {p: r[r.index >= start] for p, r in rets.items()}
        port = portfolio(rets, None)
        cell = {"equal_weighted": window_stats(port),
                "per_year_sharpe": {int(y): round(sharpe(g), 2)
                                    for y, g in port.groupby(port.index.year)},
                "per_pair_sharpe": {p: round(sharpe(r), 4) for p, r in rets.items()}}
        results[f"{variant}|{cost}"] = cell
    primary = results["V1_clip|C2_rate_m0.5"]["equal_weighted"]
    if primary["sharpe"] >= 0.30 and primary["t"] >= 1.65:
        verdict = "CONFIRMED"
    elif primary["sharpe"] <= 0:
        verdict = "REFUTED"
    else:
        verdict = "INCONCLUSIVE"
    results["verdict"] = verdict
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", choices=["A", "B"])
    ap.add_argument("--holdout-dir", type=Path)
    ap.add_argument("--rate-data", default="data/rates/rate_differentials.parquet")
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true",
                    help="2 pairs, 2010-2011, C1+C2 only; prints no metrics")
    args = ap.parse_args()

    if not Path(PRE_REG_PATH).exists():
        print(f"ERROR: pre-registration missing: {PRE_REG_PATH}")
        return 1
    config = load_config(CONFIG_PATH)
    rate_data = pd.read_parquet(args.rate_data)
    if rate_data.index.tz is not None:
        rate_data.index = rate_data.index.tz_localize(None)

    if args.smoke:
        cells = [("V1_clip", "C1_static"), ("V2_quintile", "C2_rate_m0.5"),
                 ("V3_sign", "C2_rate_m0.5"), ("JPY_basket", "C2_rate_m0.5")]
        prices = load_prices(["USDJPY", "EURUSD"], None, "2011-12-31")
        for variant, cost in cells:
            rets = run_cell(variant, cost, prices, config, rate_data)
            print(f"  smoke {variant} x {cost}: {len(rets)} pairs, "
                  f"{sum(len(r) for r in rets.values())} return rows — ok")
        return 0

    if args.part == "A":
        results = part_a(config, rate_data, CELLS_A, PAIRS, A_END)
        summary = triggers_a(results, rate_data)
    elif args.part == "B":
        if args.holdout_dir is None:
            ap.error("--part B needs --holdout-dir")
        results = part_b(config, rate_data, args.holdout_dir)
        summary = {"verdict": results["verdict"]}
    else:
        ap.error("--part or --smoke required")

    out = Path(args.out or f"data/results/carry_retest_part{args.part}_2026-10-25.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pre_registration": PRE_REG_PATH,
        "part": args.part,
        "rate_data": args.rate_data,
        "summary": summary,
        "cells": results,
    }, indent=2, default=str))
    print(f"\nSaved {out}\nVerdict: {summary['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
