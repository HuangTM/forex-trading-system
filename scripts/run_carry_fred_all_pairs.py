#!/usr/bin/env python3
"""CONSENSUS Bet #1 — FRED-rates carry on 12-pair daily universe.

Runs the carry_fred strategy through the production harness for all 12 pairs,
computes an equal-vol-weighted portfolio Sharpe, and saves aggregate results
to data/results/carry_fred_aggregate_2026-04-25.json.

OOS holdout: 2023-04-25 to 2026-04-25 (last 36 months, reserved before code written).
IS period: everything before 2023-04-25.

The per-pair harness trials use the FULL dataset (harness is general-purpose).
This script slices to OOS at the portfolio level for the pre-registered kill test.

Usage:
    .venv/bin/python scripts/run_carry_fred_all_pairs.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path so this script is runnable directly from the repo root.
# noqa: E402 — sys.path manipulation must precede local imports
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from forex_system.backtest.engine import run_backtest  # noqa: E402
from forex_system.backtest.metrics import calculate_metrics  # noqa: E402
from forex_system.core.config import load_config  # noqa: E402
from forex_system.costs.model import RealisticCostModel  # noqa: E402
from forex_system.data.storage import load_parquet  # noqa: E402
from forex_system.features.registry import compute_indicators  # noqa: E402
from forex_system.strategies.carry_fred import CarryFREDStrategy  # noqa: E402

# Pre-registration constants (CONSENSUS Bet #1)
PAIRS = [
    "AUDJPY", "AUDUSD", "CADJPY", "EURGBP", "EURJPY", "EURUSD",
    "GBPJPY", "GBPUSD", "NZDJPY", "NZDUSD", "USDCAD", "USDJPY",
]
OOS_START = "2023-04-25"  # reserved before any code written
GATE_THRESHOLD = 0.30     # pre-registered kill criterion
PRE_REG_PATH = "references/pre-registrations/carry_fred.md"
CONFIG_PATH = "config/carry_fred.yaml"
RATE_DATA_PATH = "data/rates/rate_differentials.parquet"
RESULTS_PATH = "data/results/carry_fred_aggregate_2026-04-25.json"
TARGET_VOL = 0.10         # 10% annualized per leg (pre-registered)
TRADING_DAYS = 252


def _json_default(obj: object) -> object:
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj


def run_pair(
    pair: str,
    config,
    rate_data: pd.DataFrame,
    oos_start: str,
) -> dict:
    """Run backtest for one pair, return result dict with IS+OOS split."""
    print(f"\n  Running {pair}...")

    # Load data
    data = load_parquet(pair, "daily", config.data_dir)

    # Compute indicators
    strategy_params = dict(config.strategies[0].params)
    strategy_params["pair"] = pair.upper()
    strategy = CarryFREDStrategy(strategy_params, rate_data=rate_data)
    enriched = compute_indicators(data, strategy.required_indicators())
    enriched = enriched.dropna(subset=["atr_14"])

    # Build cost model
    pair_info = config.get_pair_info(pair)
    cost_model = RealisticCostModel(pair_configs={pair: pair_info})

    # Generate signals on FULL dataset
    signals = strategy.generate_signals(enriched)

    # Run backtest on FULL dataset (harness standard)
    bt_result = run_backtest(
        data=enriched,
        signals=signals,
        pair=pair.upper(),
        strategy_name="carry_fred",
        cost_model=cost_model,
        initial_capital=config.backtest.initial_capital,
        entry_delay_bars=config.backtest.entry_delay_bars,
    )

    # Full-period metrics
    full_metrics = calculate_metrics(bt_result.equity_curve, bt_result.trade_log)

    # OOS slice: last 36 months
    # Handle tz-aware equity curve index (engine uses UTC timestamps)
    ec = bt_result.equity_curve
    oos_start_ts = pd.Timestamp(oos_start)
    if ec.index.tz is not None:
        oos_start_ts = oos_start_ts.tz_localize(ec.index.tz)
    oos_ec = ec[ec.index >= oos_start_ts]
    is_ec = ec[ec.index < oos_start_ts]

    # OOS metrics
    if len(oos_ec) > 10:
        oos_rets = oos_ec.pct_change().dropna()
        oos_sharpe = float(oos_rets.mean() / oos_rets.std() * np.sqrt(TRADING_DAYS)) if oos_rets.std() > 0 else 0.0
        oos_dd = float(1 - (oos_ec / oos_ec.cummax()).min())
    else:
        oos_sharpe = float("nan")
        oos_dd = float("nan")

    # IS metrics
    if len(is_ec) > 10:
        is_rets = is_ec.pct_change().dropna()
        is_sharpe = float(is_rets.mean() / is_rets.std() * np.sqrt(TRADING_DAYS)) if is_rets.std() > 0 else 0.0
    else:
        is_sharpe = float("nan")

    # Per-pair realized vol (daily) on IS period (for vol-weighting)
    if len(is_ec) > 20:
        is_rets_clean = is_ec.pct_change().dropna()
        pair_realized_vol = float(is_rets_clean.std() * np.sqrt(TRADING_DAYS))
    else:
        pair_realized_vol = TARGET_VOL  # fallback: equal weight

    print(
        f"    {pair}: full_sharpe={full_metrics.sharpe_ratio:.3f}, "
        f"oos_sharpe={oos_sharpe:.3f}, is_sharpe={is_sharpe:.3f}, "
        f"n_trades={full_metrics.num_trades}, max_dd={full_metrics.max_drawdown:.1%}"
    )

    return {
        "pair": pair,
        "full_sharpe": full_metrics.sharpe_ratio,
        "oos_sharpe": oos_sharpe,
        "is_sharpe": is_sharpe,
        "max_dd": full_metrics.max_drawdown,
        "oos_max_dd": oos_dd,
        "n_trades": full_metrics.num_trades,
        "pair_realized_vol": pair_realized_vol,
        "equity_curve": bt_result.equity_curve,  # kept in-memory for portfolio calc
        "oos_equity_curve": oos_ec,
    }


def compute_portfolio_sharpe(
    pair_results: list[dict],
    oos_start: str,
    target_vol: float = TARGET_VOL,
) -> dict:
    """Equal-vol-weighted portfolio Sharpe on OOS period.

    Weight_pair = target_vol / pair_realized_vol (IS period).
    Then combine daily returns as sum(weight_i * rets_i) normalized to
    equal-vol-weighted portfolio.
    """
    # Collect OOS equity curves
    oos_rets_dict: dict[str, pd.Series] = {}
    for r in pair_results:
        ec = r["oos_equity_curve"]
        if len(ec) > 5:
            rets = ec.pct_change().dropna()
            oos_rets_dict[r["pair"]] = rets

    if not oos_rets_dict:
        return {"error": "No OOS data available"}

    # Align on common dates
    oos_rets_df = pd.DataFrame(oos_rets_dict).dropna(how="all")
    oos_rets_df = oos_rets_df.fillna(0.0)  # missing dates = flat

    # Vol-weights based on IS realized vol
    vol_weights: dict[str, float] = {}
    for r in pair_results:
        pair = r["pair"]
        if pair in oos_rets_df.columns:
            rv = r["pair_realized_vol"]
            # Avoid div-by-zero; cap weight at 5x target
            if rv > 0:
                w = min(target_vol / rv, 5.0)
            else:
                w = 1.0
            vol_weights[pair] = w

    if not vol_weights:
        return {"error": "No vol-weight data"}

    # Normalize weights to sum to 1 (equal-vol-weighted)
    total_w = sum(vol_weights.values())
    norm_weights = {p: w / total_w for p, w in vol_weights.items()}

    # Portfolio returns
    weights_series = pd.Series(norm_weights)
    available_pairs = [p for p in weights_series.index if p in oos_rets_df.columns]
    if not available_pairs:
        return {"error": "No overlapping pairs in OOS data"}

    port_rets = (oos_rets_df[available_pairs] * weights_series[available_pairs]).sum(axis=1)

    # Portfolio metrics
    vol_weighted_sharpe = float(
        port_rets.mean() / port_rets.std() * np.sqrt(TRADING_DAYS)
    ) if port_rets.std() > 0 else 0.0

    # Equal-weighted Sharpe (naive, all pairs equal weight)
    eq_rets = oos_rets_df[available_pairs].mean(axis=1)
    equal_weighted_sharpe = float(
        eq_rets.mean() / eq_rets.std() * np.sqrt(TRADING_DAYS)
    ) if eq_rets.std() > 0 else 0.0

    # Portfolio max drawdown
    port_equity = (1 + port_rets).cumprod()
    port_max_dd = float(1 - (port_equity / port_equity.cummax()).min())

    print(f"\n  Portfolio (vol-weighted): Sharpe={vol_weighted_sharpe:.4f}")
    print(f"  Portfolio (equal-weighted): Sharpe={equal_weighted_sharpe:.4f}")
    print(f"  Portfolio max drawdown: {port_max_dd:.1%}")
    print(f"  OOS period: {oos_start} to {oos_rets_df.index[-1].date()}")
    print(f"  OOS bars: {len(port_rets)}")
    print(f"  Pairs in portfolio: {len(available_pairs)}")

    return {
        "vol_weighted_sharpe": vol_weighted_sharpe,
        "equal_weighted_sharpe": equal_weighted_sharpe,
        "max_dd": port_max_dd,
        "oos_start": oos_start,
        "oos_end": str(oos_rets_df.index[-1].date()),
        "n_oos_bars": len(port_rets),
        "n_pairs": len(available_pairs),
        "vol_weights": {p: round(w, 4) for p, w in norm_weights.items() if p in available_pairs},
    }


def main() -> None:
    print("=" * 65)
    print("CONSENSUS Bet #1 — FRED-rates carry, 12-pair universe")
    print(f"OOS holdout: {OOS_START} to present (36 months)")
    print(f"Kill criterion: portfolio vol-weighted Sharpe >= {GATE_THRESHOLD}")
    print("=" * 65)

    # Validate pre-registration exists (pre-commit gate checks this too)
    pre_reg = Path(PRE_REG_PATH)
    if not pre_reg.exists():
        print(f"ERROR: Pre-registration not found: {PRE_REG_PATH}")
        sys.exit(1)
    print(f"\nPre-registration: {PRE_REG_PATH} [OK]")

    # Load config
    config = load_config(CONFIG_PATH)
    print(f"Config: {CONFIG_PATH} [OK]")

    # Load FRED rate data once (shared across all pairs)
    rate_data = pd.read_parquet(RATE_DATA_PATH)
    if rate_data.index.tz is not None:
        rate_data.index = rate_data.index.tz_localize(None)
    print(f"Rate data: {RATE_DATA_PATH} [{len(rate_data)} bars, {rate_data.columns.tolist()}]")

    # Run all 12 pairs
    print(f"\nRunning {len(PAIRS)} pairs...")
    pair_results = []
    errors = []
    for pair in PAIRS:
        try:
            result = run_pair(pair, config, rate_data, OOS_START)
            pair_results.append(result)
        except Exception as e:
            print(f"  ERROR {pair}: {e}")
            errors.append({"pair": pair, "error": str(e)})

    # Compute portfolio Sharpe
    print("\nComputing vol-weighted portfolio...")
    portfolio = compute_portfolio_sharpe(pair_results, OOS_START)

    # Assemble aggregate report
    per_pair_report = []
    for r in pair_results:
        per_pair_report.append({
            "pair": r["pair"],
            "sharpe": round(r["oos_sharpe"], 4) if not np.isnan(r["oos_sharpe"]) else None,
            "full_sharpe": round(r["full_sharpe"], 4),
            "is_sharpe": round(r["is_sharpe"], 4) if not np.isnan(r["is_sharpe"]) else None,
            "max_dd": round(r["oos_max_dd"], 4) if not np.isnan(r["oos_max_dd"]) else None,
            "n_trades": r["n_trades"],
            "pair_realized_vol": round(r["pair_realized_vol"], 4),
        })

    vol_weighted_sharpe = portfolio.get("vol_weighted_sharpe", float("nan"))
    passes = bool(vol_weighted_sharpe >= GATE_THRESHOLD) if not np.isnan(vol_weighted_sharpe) else False

    aggregate = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pre_registration": PRE_REG_PATH,
        "config": CONFIG_PATH,
        "oos_holdout_start": OOS_START,
        "n_pairs": len(pair_results),
        "pairs_errored": errors,
        "per_pair": per_pair_report,
        "portfolio": {
            "vol_weighted_sharpe": round(vol_weighted_sharpe, 4) if not np.isnan(vol_weighted_sharpe) else None,
            "equal_weighted_sharpe": round(portfolio.get("equal_weighted_sharpe", float("nan")), 4),
            "max_dd": round(portfolio.get("max_dd", float("nan")), 4),
            "oos_start": portfolio.get("oos_start"),
            "oos_end": portfolio.get("oos_end"),
            "n_oos_bars": portfolio.get("n_oos_bars"),
            "n_pairs": portfolio.get("n_pairs"),
        },
        "vs_threshold": {
            "threshold": GATE_THRESHOLD,
            "passes": passes,
            "actual": round(vol_weighted_sharpe, 4) if not np.isnan(vol_weighted_sharpe) else None,
        },
    }

    # Save results
    results_path = Path(RESULTS_PATH)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(aggregate, indent=2, default=_json_default))
    print(f"\nAggregate results saved: {results_path}")

    # Print summary table
    print("\n" + "=" * 65)
    print("CONSENSUS BET #1 — RESULTS")
    print("=" * 65)
    print(f"{'Pair':<10} {'OOS Sharpe':>12} {'Full Sharpe':>12} {'MaxDD':>8} {'Trades':>7}")
    print("-" * 55)
    for r in per_pair_report:
        oos_s = f"{r['sharpe']:.3f}" if r["sharpe"] is not None else "N/A"
        full_s = f"{r['full_sharpe']:.3f}"
        dd = f"{r['max_dd']:.1%}" if r["max_dd"] is not None else "N/A"
        print(f"{r['pair']:<10} {oos_s:>12} {full_s:>12} {dd:>8} {r['n_trades']:>7}")
    print("-" * 55)
    print(f"\nPortfolio vol-weighted Sharpe (OOS): {vol_weighted_sharpe:.4f}")
    print(f"Portfolio equal-weighted Sharpe (OOS): {portfolio.get('equal_weighted_sharpe', float('nan')):.4f}")
    print(f"Portfolio max drawdown (OOS): {portfolio.get('max_dd', float('nan')):.1%}")
    print(f"\nHoQR threshold: {GATE_THRESHOLD}")
    verdict = "PASS" if passes else "FAIL"
    print(f"Verdict: {verdict} (vol-weighted Sharpe {vol_weighted_sharpe:.4f} vs threshold {GATE_THRESHOLD})")
    print("=" * 65)

    if passes:
        print("\nCarry-as-edge-mechanism: EDGE EXISTS at this capacity scale.")
    else:
        print("\nCarry-as-edge-mechanism: EDGE DOES NOT EXIST at this capacity scale.")
        print("Per CONSENSUS Bet #1: carry research thread retired.")


if __name__ == "__main__":
    main()
