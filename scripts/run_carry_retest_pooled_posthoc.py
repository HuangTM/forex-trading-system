#!/usr/bin/env python3
"""POST-HOC diagnostic for the carry_fred retest — NOT pre-registered.

Why it exists: in Part B the EURGBP sleeve lost ~99% (C2) / went below zero (C1)
in late 2008 (no margin simulation in the engine). The pre-registered portfolio
averages per-pair percentage returns, i.e. rebalances daily into a wiped-out
sleeve, so a near-zero equity base produced +958% "returns" and invalidated the
pre-registered Part B number. This script recomputes every cell as one pooled
account instead: sleeves start at 1/n of capital, P&L is summed in dollars, a
sleeve that reaches zero stays at zero, and pairs without data yet hold cash.

Usage:
    .venv/bin/python scripts/run_carry_retest_pooled_posthoc.py A
    .venv/bin/python scripts/run_carry_retest_pooled_posthoc.py B
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import run_carry_retest as R  # noqa: E402
from forex_system.core.config import load_config  # noqa: E402
from forex_system.harness.dsr import compute_dsr  # noqa: E402


def pooled_returns(rets: dict[str, pd.Series], start: str, n_sleeves: int) -> pd.Series:
    sleeves = []
    for r in rets.values():
        eq = (1 + r[r.index >= start]).cumprod()
        dead = (eq <= 0.0).cummax()
        sleeves.append(eq.where(~dead, 0.0).astype(float))
    equity = pd.concat(sleeves, axis=1).ffill().fillna(1.0)
    total = equity.sum(axis=1) + (n_sleeves - equity.shape[1])
    return total.pct_change().dropna()


def summary(r: pd.Series) -> dict:
    sr = R.sharpe(r)
    years = len(r) / R.TRADING_DAYS
    eq = (1 + r).cumprod()
    return {
        "sharpe": round(sr, 3),
        "t": round(float(sr * np.sqrt(years)), 2),
        "p_boot": round(R.boot_p(r), 3),
        "dsr_n33": round(compute_dsr(sr, len(r), float(stats.skew(r)),
                                     float(stats.kurtosis(r)), R.N_TRIALS, R.TRADING_DAYS), 3),
        "ann_return": round(float(eq.iloc[-1] ** (1 / years) - 1), 4),
        "max_dd": round(float(1 - (eq / eq.cummax()).min()), 4),
    }


def main() -> int:
    part = sys.argv[1] if len(sys.argv) > 1 else "A"
    config = load_config(R.CONFIG_PATH)
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    with contextlib.redirect_stdout(io.StringIO()):
        if part == "B":
            prices = R.load_prices(R.PAIRS, Path("data/holdout_pre2010"), R.B_END)
            cells = R.CELLS_B
        else:
            prices = R.load_prices(R.PAIRS, None, R.A_END)
            cells = R.CELLS_A
    for variant, cost in cells:
        rets = R.run_cell(variant, cost, prices, config, rate_data)
        n = len(R.JPY_CROSSES) if variant == "JPY_basket" else len(R.PAIRS)
        worst = {p: round(float((1 + r).cumprod().min()), 3) for p, r in rets.items()}
        worst = {p: m for p, m in worst.items() if m < 0.6}
        if part == "B":
            print(f"{variant} x {cost} 2003-2009: {summary(pooled_returns(rets, R.B_START, n))}")
        else:
            pr = pooled_returns(rets, "2000-01-01", n)
            oos = pd.Timestamp(R.A_OOS_START)
            print(f"{variant} x {cost} IS: {summary(pr[pr.index < oos])}")
            print(f"{' ' * len(variant + cost)}    OOS: {summary(pr[pr.index >= oos])}")
        print(f"    sleeves below 60% of start: {worst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
