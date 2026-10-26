#!/usr/bin/env python3
"""FX fix-reversal strategy (Krohn, Mueller & Whelan, JF 2024) on 1h data, 2021-2025.

Pre-registration: references/pre-registrations/fix_reversal_1h.md (read it first —
windows, costs, statistics and verdict rule are fixed there).

Paper (Section V / V.E, all times New York / ET): long USD 17:00 -> Tokyo fix
(9:55 Tokyo = 00:55 UTC), short USD Tokyo fix -> 02:00; long USD 02:00 -> ECB fix
(08:15); flat 08:15 -> 11:00 (London fix); short USD 11:00 -> 17:00.
1h approximation: Tokyo boundary at 01:00 UTC, ECB boundary at 08:00 ET.

Usage:
    .venv/bin/python scripts/run_fix_reversal.py            # full run, writes results JSON
    .venv/bin/python scripts/run_fix_reversal.py --smoke    # executes only, prints no metrics
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

from forex_system.data.storage import load_parquet  # noqa: E402
from forex_system.harness.dsr import compute_dsr  # noqa: E402

PRE_REG_PATH = "references/pre-registrations/fix_reversal_1h.md"
# +1 = the pair's price rises when USD appreciates (USD is the base currency).
USD_PAIRS = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1, "USDJPY": 1, "USDCAD": 1}
SLIP_PIPS_PER_SIDE = 0.4   # CD0 convention: 2 * (0.25 slippage + 0.15 haircut) per round trip
N_TRIALS = 34              # honest-N: 33 + this test
BOOT_REPS = 10_000
BOOT_BLOCK = 20

SCHEDULES = ("combined", "tokyo", "europe", "combined_avoid_rollover")


def fix_windows(index: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Paper windows per bar, keyed by bar START time (UTC-aware index).

    Night = 17:00 -> 02:00 ET, split at the Tokyo boundary 01:00 UTC: night bars
    starting at 21-23 or 00 UTC are pre-Tokyo, 01-06 UTC post-Tokyo (DST-safe:
    17:00 ET is 21 or 22 UTC, 02:00 ET is 06 or 07 UTC).
    """
    h_et = index.tz_convert("America/New_York").hour
    h_utc = index.hour
    night = (h_et >= 17) | (h_et < 2)
    pre_t = night & ((h_utc >= 12) | (h_utc < 1))
    return {
        "pre_tokyo": np.asarray(pre_t),
        "post_tokyo": np.asarray(night & ~pre_t),
        "pre_ecb": np.asarray((h_et >= 2) & (h_et < 8)),
        "ecb_to_london": np.asarray((h_et >= 8) & (h_et < 11)),
        "post_london": np.asarray((h_et >= 11) & (h_et < 17)),
        "rollover_bar": np.asarray(h_et == 17),
    }


def usd_position(index: pd.DatetimeIndex, schedule: str) -> pd.Series:
    """Long-USD (+1) / short-USD (-1) / flat (0) per bar."""
    w = fix_windows(index)
    pos = np.zeros(len(index))
    if schedule in ("combined", "tokyo", "combined_avoid_rollover"):
        pos[w["pre_tokyo"]] = 1.0
        pos[w["post_tokyo"]] = -1.0
    if schedule in ("combined", "europe", "combined_avoid_rollover"):
        pos[w["pre_ecb"]] = 1.0
        pos[w["post_london"]] = -1.0
    if schedule == "combined_avoid_rollover":
        pos[w["rollover_bar"]] = 0.0  # skip the 17:00 ET bar (widest spread)
    return pd.Series(pos, index=index)


def bar_returns(df: pd.DataFrame) -> pd.Series:
    """Log return per bar; across a gap (e.g. weekend) use the bar's own open->close."""
    close_to_close = np.log(df["close"]).diff()
    contiguous = df.index.to_series().diff() == pd.Timedelta(hours=1)
    own = np.log(df["close"] / df["open"])
    return close_to_close.where(contiguous, own).fillna(0.0)


def pair_daily(pair: str, df: pd.DataFrame, schedule: str, cost: str) -> pd.DataFrame:
    """Daily (ET 17:00 -> 17:00 trading day) gross/net log returns for one pair."""
    sign = USD_PAIRS[pair]
    pip = 0.01 if pair.endswith("JPY") else 0.0001
    pos_usd = usd_position(df.index, schedule)
    pos_pair = sign * pos_usd
    gross = pos_pair * bar_returns(df)
    turnover = pos_pair.diff().abs().fillna(pos_pair.abs())
    if cost == "gross":
        per_side_pips = pd.Series(0.0, index=df.index)
    elif cost == "spread_only":
        per_side_pips = df["spread_median_pips"].fillna(0.0) / 2.0
    else:  # "cd0"
        per_side_pips = df["spread_median_pips"].fillna(0.0) / 2.0 + SLIP_PIPS_PER_SIDE
    cost_ret = turnover * per_side_pips * pip / df["open"]
    net = gross - cost_ret
    day = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize()
    out = pd.DataFrame({"gross": gross, "net": net, "turnover": turnover})
    out["day"] = day.tz_localize(None)
    return out.groupby("day").sum()


def window_breakdown(pair: str, df: pd.DataFrame) -> dict[str, float]:
    """Gross bp/day earned in each paper window (USD-direction returns, no positions)."""
    usd_ret = USD_PAIRS[pair] * bar_returns(df)
    et = df.index.tz_convert("America/New_York")
    n_days = len(pd.unique((et + pd.Timedelta(hours=7)).normalize()))
    windows = {k: m for k, m in fix_windows(df.index).items() if k != "rollover_bar"}
    return {f"{k}_usd_up": round(float(usd_ret[m].sum()) / n_days * 1e4, 3)
            for k, m in windows.items()}


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


def summarize(daily: pd.Series) -> dict:
    x = daily.to_numpy()
    years = (daily.index[-1] - daily.index[0]).days / 365.25
    per_year = len(x) / years
    sr = float(x.mean() / x.std() * np.sqrt(per_year)) if x.std() > 0 else 0.0
    t = float(x.mean() / (x.std() / np.sqrt(len(x))))
    return {
        "bp_per_day": round(float(x.mean()) * 1e4, 3),
        "ann_return": round(float(x.mean()) * per_year, 4),
        "sharpe": round(sr, 3),
        "t": round(t, 2),
        "p_boot": round(boot_p(x), 4),
        "dsr_n34": round(compute_dsr(sr, len(x), float(stats.skew(x)), float(stats.kurtosis(x)),
                                     N_TRIALS, per_year), 4),
        "n_days": len(x),
        "per_year_bp_per_day": {int(y): round(float(g.mean()) * 1e4, 2)
                                for y, g in daily.groupby(daily.index.year)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true", help="first 2000 bars, 2 pairs; no metrics")
    ap.add_argument("--out", default="data/results/fix_reversal_1h_2026-10-25.json")
    args = ap.parse_args()
    if not Path(PRE_REG_PATH).exists():
        print(f"ERROR: pre-registration missing: {PRE_REG_PATH}")
        return 1

    pairs = ["EURUSD", "USDJPY"] if args.smoke else list(USD_PAIRS)
    data = {}
    for p in pairs:
        df = load_parquet(p, "1h", "data")
        data[p] = df.iloc[:2000] if args.smoke else df

    results: dict = {"cells": {}, "per_pair": {}, "windows_gross_bp_per_day": {}}
    for schedule in SCHEDULES:
        for cost in ("gross", "spread_only", "cd0"):
            legs = {p: pair_daily(p, df, schedule, cost) for p, df in data.items()}
            port = pd.DataFrame({p: leg["net"] for p, leg in legs.items()}).fillna(0.0).mean(axis=1)
            turnover = float(np.mean([leg["turnover"].mean() for leg in legs.values()]))
            if args.smoke:
                print(f"  smoke {schedule} x {cost}: {len(port)} days, turnover/day {turnover:.1f} — ok")
                continue
            cell = summarize(port)
            cell["units_turnover_per_day"] = round(turnover, 2)
            results["cells"][f"{schedule}|{cost}"] = cell
            if schedule == "combined":
                results["per_pair"][cost] = {p: summarize(leg["net"])["bp_per_day"]
                                             for p, leg in legs.items()}
    if args.smoke:
        return 0
    results["windows_gross_bp_per_day"] = {p: window_breakdown(p, df) for p, df in data.items()}

    primary = results["cells"]["combined|cd0"]
    gross = results["cells"]["combined|gross"]
    replicates = gross["t"] >= 1.65
    if primary["t"] >= 1.65 and primary["dsr_n34"] >= 0.95:
        verdict = "PASS"
    elif primary["sharpe"] <= 0:
        verdict = "FAIL"
    else:
        verdict = "INCONCLUSIVE"
    summary = {"gross_pattern_replicates": replicates, "verdict": verdict}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pre_registration": PRE_REG_PATH,
        "summary": summary,
        **results,
    }, indent=2, default=str))
    print(f"Saved {out}\nGross pattern replicates: {replicates}\nVerdict: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
