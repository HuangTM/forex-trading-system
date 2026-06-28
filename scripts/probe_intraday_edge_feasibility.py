"""Intraday edge-feasibility probe (descriptive, $0, honest-N untouched).

Post-backfill reassessment (2026-06-27): with the 12-pair 1h universe complete
and the USD-correlation breadth wall broken (rho_bar_eff 0.40 < 0.41 gate on
all-12; 0.26 on the curated 7-pair subset), does any simple price-only intraday
factor show a net-positive, COST-SURVIVING edge that a diversified portfolio
could confirm?

Factor under test: time-series momentum (best-evidenced FX factor) at a
PRE-SPECIFIED set of lookbacks {12,24,48,96}h, sign-of-rolling-return,
hold-until-flip, position shift(1) (no lookahead). ALL cells reported (no
cherry-picking). Cost = real per-bar spread + 2*(0.25 slip + 0.15 haircut),
charged on flips (the firm's CD0 cost model). Annualization sqrt(6150).

Result (2026-06-27): 0/12 pairs net-positive at every lookback; best portfolio
GROSS Sharpe +0.30 (12h) is below the 5yr confirmability bar (~0.89) even
frictionless; negative gross at longer horizons. Combined with the earlier
F1-F6 CD0 screen (also all net-negative), the simple price-only intraday factor
space on this universe is exhausted with a NEGATIVE result. Breadth was not the
binding constraint; EDGE is, and it is absent here.

Reproduce: python3 scripts/probe_intraday_edge_feasibility.py
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"
ALL = ['AUDJPY', 'AUDUSD', 'CADJPY', 'EURGBP', 'EURJPY', 'EURUSD',
       'GBPJPY', 'GBPUSD', 'NZDJPY', 'NZDUSD', 'USDCAD', 'USDJPY']
SUB7 = ['CADJPY', 'EURGBP', 'EURJPY', 'EURUSD', 'NZDUSD', 'USDCAD', 'USDJPY']  # rho_bar_eff 0.26
LOOKBACKS = [12, 24, 48, 96]
SLIP, HAIR = 0.25, 0.15
ANN = math.sqrt(6150)
PIP = {p: (0.01 if p.endswith('JPY') else 0.0001) for p in ALL}
CONFIRM_BAR = 2 / math.sqrt(5)  # ~0.89 net Sharpe -> t>=2 over the 5yr sample


def load():
    d = {}
    for p in ALL:
        df = pd.read_parquet(DATA / f"{p}_1h.parquet")
        df['lr'] = np.log(df['close'] / df['close'].shift(1))
        d[p] = df
    return d


def net_return_series(df, pair, lookback):
    pip = PIP[pair]
    sig = np.sign(df['lr'].rolling(lookback).sum())
    pos = sig.shift(1).fillna(0.0)
    ret = df['lr'].fillna(0.0)
    gross = pos * ret
    spread = df['spread_median_pips'].fillna(0.0).clip(lower=0.0)
    rt_cost_pips = spread + 2 * (SLIP + HAIR)
    turn = pos.diff().abs().fillna(0.0)
    cost = turn * rt_cost_pips * pip / df['close']
    return gross, gross - cost, turn.sum()


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * ANN) if x.std() > 0 else float('nan')


def main():
    data = load()
    print(f"Confirmability bar (5yr, t>=2): net Sharpe >= {CONFIRM_BAR:.2f}\n")
    for L in LOOKBACKS:
        per_net, per_gross, npos, tr_yr = {}, {}, 0, []
        for p in ALL:
            g, n, tr = net_return_series(data[p], p, L)
            per_net[p], per_gross[p] = n, g
            if sharpe(n) > 0:
                npos += 1
            tr_yr.append(tr / 5.0)

        def port(pairs, series):
            return sharpe(pd.DataFrame({p: series[p] for p in pairs}).dropna().mean(axis=1))

        nsh = [sharpe(per_net[p]) for p in ALL]
        gsh = [sharpe(per_gross[p]) for p in ALL]
        print(f"=== TSMOM lookback {L}h | ~{np.mean(tr_yr):.0f} trades/yr/pair ===")
        print(f"  per-pair NET   Sharpe: min {np.nanmin(nsh):+.2f}  med {np.nanmedian(nsh):+.2f}  "
              f"max {np.nanmax(nsh):+.2f}  | net-positive pairs: {npos}/12")
        print(f"  per-pair GROSS Sharpe: min {np.nanmin(gsh):+.2f}  med {np.nanmedian(gsh):+.2f}  "
              f"max {np.nanmax(gsh):+.2f}")
        print(f"  PORTFOLIO net Sharpe:  all-12 {port(ALL, per_net):+.2f}   "
              f"sub-7 {port(SUB7, per_net):+.2f}   (gross all-12 {port(ALL, per_gross):+.2f})")
        conf = "CONFIRMABLE in 5yr" if max(port(ALL, per_net), port(SUB7, per_net)) >= CONFIRM_BAR \
            else "below confirmability bar"
        print(f"  -> {conf}\n")


if __name__ == "__main__":
    main()
