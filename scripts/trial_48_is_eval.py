"""Trial 48 IS-only evaluation — A2′ Overnight Mean-Reversion, EURUSD 1h.

Pre-registration: .fintech-org/artifacts/2026-06-17T02-37-59Z_intraday_eurusd_1h/qr-prereg-v2.yaml
Trial ID: 15923fe1

Computes the four pre-OOS kill gates from IS data (2021-01-03..2024-05-31) ONLY.
OOS (2024-07-01..2025-12-31) is NEVER read, sliced, or referenced.

Gates evaluated (in order):
    KILL-4: IS-extrapolated power gate. f_IS = qualifying trades / IS trading days.
            N_oos_expected = f_IS * OOS_trading_days. Fires if N_oos_expected < 48.
    KILL-1: Deflated Sharpe (DSR) at N=30 (ratified 2026-06-18) <= 0.95 on IS net-of-cost returns.
    KILL-2: Avg net trade <= 0 pips after 7.5-pip static cost on 2σ subset.
    KILL-3: 2σ single-bar reversion hit-rate <= 0.50.

Decision rule:
    - ANY gate fires → report KILL. OOS never burned.
    - ALL gates pass → report IS-PASSED-AWAITING-OOS-AUTHORIZATION.

Run:
    python scripts/trial_48_is_eval.py

OOS discipline:
    The data slice is performed STRICTLY before 2024-06-01. The embargo (June 2024)
    and OOS (2024-07-01 onward) are never loaded or referenced.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# --- Path setup ---
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from forex_system.backtest.engine import run_backtest  # noqa: E402
from forex_system.backtest.metrics import calculate_metrics, infer_periods_per_year  # noqa: E402
from forex_system.costs.static_roundtrip import StaticRoundTripCostModel  # noqa: E402
from forex_system.harness.dsr import compute_dsr  # noqa: E402
from forex_system.harness.honest_n import honest_n_deflation_denominator  # noqa: E402
from forex_system.strategies.overnight_mr import OvernightMRStrategy  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FROZEN CONSTANTS — DO NOT MODIFY (from pre-registration qr-prereg-v2.yaml)
# ---------------------------------------------------------------------------
IS_START = "2021-01-03"
IS_END = "2024-05-31"  # inclusive; embargo = June 2024; OOS starts 2024-07-01

# OOS trading-day count (computed from calendar, NOT from reading OOS price data)
# 2024-07-01 to 2025-12-31: ~378 weekdays (Mon-Fri), minus ~17 market holidays = ~361
# Conservative count: 378 weekdays * 5/7 days ratio is already weekday-only.
# Direct count: July 2024 = 23 days, Aug=22, Sep=21, Oct=23, Nov=21, Dec=22 = 132 (2024H2)
# 2025: Jan=23, Feb=20, Mar=21, Apr=22, May=21, Jun=21, Jul=23, Aug=21, Sep=22,
#       Oct=23, Nov=20, Dec=23 = 260 (full 2025)
# Total weekdays = 132 + 260 = 392. Less ~16 standard FX market holidays = 376.
# Using 376 as the conservative OOS trading-day count (fewer days = harder power gate).
OOS_TRADING_DAYS = 376

ENTRY_DELAY_BARS = 1
SIGMA_LOOKBACK = 20
ENTRY_THRESHOLD = 2.0
ROUND_TRIP_PIPS = 7.5
STATIC_COST_PIPS = ROUND_TRIP_PIPS  # per trade round-trip
_TRIALS_REGISTRY_PATH = PROJECT_ROOT / ".fintech-org" / "trials.jsonl"
# IC-14d fix: N_ORG_TRIALS computed mechanically, never hand-entered.
# NOTE on the absent +1: this is a RE-EVALUATION of an ALREADY-LEDGERED trial.
# Trial-48 (15923fe1) is already recorded in trials.jsonl with counts_toward=True,
# so honest_n_deflation_denominator already COUNTS it -> returns 30 (the ratified
# post-2026-06-18 denominator; retired value was 48).
# Passing n_trials=N_ORG_TRIALS=30 is correct for a re-evaluation.
# Do NOT add +1 here — that is for run_trial.py / run_falsification_trial.py which
# score a NEW trial BEFORE it is appended to the ledger.
#
# HISTORICAL NOTE: Trial-48's original verdict was "DSR=0.00 at N=48". N=48 is the
# RETIRED denominator (over-deflated relative to the ratified N=30). DSR is monotone
# DECREASING in N, so N=48 was too strict — the historical verdict may change at N=30.
# Recompute at N=30 is a tracked follow-on for HoQR/NHT (CTO spec 2026-06-18,
# decision 5 historical_result_flag). Do NOT assume the kill stands; do NOT silently
# re-grade without HoQR/NHT ratification.
N_ORG_TRIALS = honest_n_deflation_denominator(_TRIALS_REGISTRY_PATH)
POWER_FLOOR = 48  # min expected OOS qualifying trades (DIFFERENT constant from DSR denominator)

# CPCV parameters (from spec: N_groups=6, k=2, purge/embargo=480 bars)
CPCV_N_GROUPS = 6
CPCV_K = 2  # test-fold size in groups
CPCV_PURGE_BARS = 480  # ~20 same-hour-class bars × ~24h = ~480 contiguous 1h bars
CPCV_EMBARGO_BARS = 480  # same as purge per spec

# Pip value for EURUSD
PIP_VALUE = 0.0001

# DSR threshold
DSR_THRESHOLD = 0.95


def load_is_data() -> pd.DataFrame:
    """Load EURUSD 1h data, slice to IS window ONLY. Never touches OOS."""
    data_path = PROJECT_ROOT / "data" / "processed" / "EURUSD_1h.parquet"
    df = pd.read_parquet(data_path)

    # Slice: IS window only. Strict end at 2024-05-31 23:59:59.
    is_data = df[df.index <= f"{IS_END} 23:59:59"].copy()
    is_data = is_data[is_data.index >= IS_START].copy()

    logger.info("IS data: %d bars from %s to %s", len(is_data), is_data.index[0], is_data.index[-1])
    return is_data


def compute_signals(data: pd.DataFrame) -> pd.Series:
    """Compute overnight MR signals on IS data."""
    strategy = OvernightMRStrategy(params={})
    return strategy.generate_signals(data)


def count_is_trading_days(data: pd.DataFrame) -> int:
    """Count trading days in IS window (unique calendar dates with at least one bar)."""
    dates = data.index.normalize().unique()
    return len(dates)


def count_qualifying_trades(signals: pd.Series) -> int:
    """Count bars with non-zero signals (qualifying entry-gate trades after gap removal)."""
    return int((signals != 0.0).sum())


def compute_kill4_power_gate(signals: pd.Series, data: pd.DataFrame) -> dict:
    """KILL-4: power gate via IS-frequency extrapolation.

    f_IS = qualifying trades / IS trading days.
    N_oos_expected = f_IS * OOS_TRADING_DAYS.
    Fires if N_oos_expected < POWER_FLOOR (48).
    """
    n_qualifying = count_qualifying_trades(signals)
    n_trading_days = count_is_trading_days(data)
    f_is = n_qualifying / n_trading_days
    n_oos_expected = f_is * OOS_TRADING_DAYS
    fires = n_oos_expected < POWER_FLOOR

    logger.info(
        "KILL-4 power: qualifying=%d, IS_days=%d, f_IS=%.4f, "
        "OOS_days=%d, N_oos_expected=%.1f, floor=%d, fires=%s",
        n_qualifying,
        n_trading_days,
        f_is,
        OOS_TRADING_DAYS,
        n_oos_expected,
        POWER_FLOOR,
        fires,
    )
    return {
        "f_IS_trades_per_day": round(f_is, 4),
        "n_qualifying_IS": n_qualifying,
        "n_IS_trading_days": n_trading_days,
        "N_oos_expected": round(n_oos_expected, 2),
        "floor": POWER_FLOOR,
        "fires": fires,
    }


def _run_single_backtest(data: pd.DataFrame, signals: pd.Series) -> tuple[pd.DataFrame, float]:
    """Run backtest on given data/signals subset; return (trade_pnl_df, sharpe).

    Returns DataFrame with columns [pnl_pips, gross_pnl_pips] per trade,
    and the annualized net Sharpe.
    """
    cost_model = StaticRoundTripCostModel()
    result = run_backtest(
        data=data,
        signals=signals,
        pair="EURUSD",
        strategy_name="overnight_mr",
        cost_model=cost_model,
        initial_capital=100_000.0,
        entry_delay_bars=ENTRY_DELAY_BARS,
        rebalance_mode="discrete",
    )

    metrics = calculate_metrics(result.equity_curve, result.trade_log)
    return result.trade_log, metrics.sharpe_ratio


def _get_trade_stats(trade_log: list) -> dict:
    """Extract trade-level statistics for KILL-2 and KILL-3."""
    if not trade_log:
        return {"avg_net_pips": 0.0, "hit_rate": 0.0, "n_trades": 0}

    pnl_pips = [t.pnl_pips for t in trade_log]
    n = len(pnl_pips)
    avg_net = sum(pnl_pips) / n
    # hit rate: fraction of trades where price moved in predicted direction
    # (net pnl > 0 after cost means the reversion captured more than cost)
    # KILL-3 is about whether reversion happened (gross, before cost), not whether we profited.
    # Spec: "2σ single-bar reversion hit-rate <= 0.50"
    # Reversion = price moved in our favor (gross trade pnl > 0 before cost deduction).
    # gross = net + cost_pips per trade
    gross_pips = [t.pnl_pips + t.cost_pips for t in trade_log]
    n_winners = sum(1 for g in gross_pips if g > 0)
    hit_rate = n_winners / n

    return {"avg_net_pips": avg_net, "hit_rate": hit_rate, "n_trades": n}


def run_full_is_backtest(data: pd.DataFrame, signals: pd.Series) -> dict:
    """Run full IS backtest and return comprehensive stats."""
    cost_model = StaticRoundTripCostModel()
    result = run_backtest(
        data=data,
        signals=signals,
        pair="EURUSD",
        strategy_name="overnight_mr",
        cost_model=cost_model,
        initial_capital=100_000.0,
        entry_delay_bars=ENTRY_DELAY_BARS,
        rebalance_mode="discrete",
    )

    ec = result.equity_curve.dropna()
    ppy = infer_periods_per_year(ec.index)
    metrics = calculate_metrics(result.equity_curve, result.trade_log, periods_per_year=ppy)
    trade_stats = _get_trade_stats(result.trade_log)

    logger.info(
        "IS backtest: trades=%d gross_sharpe=%.4f net_sharpe=%.4f max_dd=%.4f",
        metrics.num_trades,
        metrics.sharpe_ratio,
        metrics.sharpe_ratio,
        metrics.max_drawdown,
    )

    return {
        "equity_curve": result.equity_curve,
        "trade_log": result.trade_log,
        "metrics": metrics,
        "trade_stats": trade_stats,
        "ppy": ppy,
    }


def _build_cpcv_folds(n_bars: int, n_groups: int, k: int, purge: int, embargo: int) -> list[dict]:
    """Build CPCV fold definitions.

    Splits [0, n_bars) into n_groups equal groups. Each combination of k groups
    is used as the test set; remaining groups form train. Purge and embargo are
    applied around each test fold boundary.

    Returns list of dicts with keys: train_mask, test_mask.
    Each mask is a boolean array of length n_bars.
    """
    from itertools import combinations

    group_size = n_bars // n_groups
    group_boundaries = []
    for g in range(n_groups):
        start = g * group_size
        end = (g + 1) * group_size if g < n_groups - 1 else n_bars
        group_boundaries.append((start, end))

    folds = []
    for test_groups in combinations(range(n_groups), k):
        test_mask = np.zeros(n_bars, dtype=bool)
        for tg in test_groups:
            s, e = group_boundaries[tg]
            test_mask[s:e] = True

        # Purge + embargo: zero out bars adjacent to test boundaries
        # For each test group boundary, remove purge bars before the test start
        # and embargo bars after the test end from the TRAIN set.
        embargo_mask = np.zeros(n_bars, dtype=bool)
        for tg in test_groups:
            s, e = group_boundaries[tg]
            # Purge: remove from train the purge bars before each test fold start
            purge_start = max(0, s - purge)
            embargo_mask[purge_start:s] = True
            # Embargo: remove from train the embargo bars after each test fold end
            embargo_end = min(n_bars, e + embargo)
            embargo_mask[e:embargo_end] = True

        train_mask = ~test_mask & ~embargo_mask

        if train_mask.sum() < SIGMA_LOOKBACK + 1:
            continue  # skip degenerate folds

        folds.append({"train_mask": train_mask, "test_mask": test_mask})

    return folds


def compute_cpcv_sharpe(data: pd.DataFrame, signals: pd.Series) -> dict:
    """Compute CPCV net-of-cost Sharpe for the DSR input.

    CPCV: N_groups=6, k=2 (test size), purge=480, embargo=480 bars.
    Each fold: train signals (passed to strategy) → apply to test bars.

    Since the strategy's sigma_sess is purely a function of the data's history
    (it doesn't "learn" parameters in the ML sense), the CPCV here validates
    the IS net Sharpe without train/test leakage via the rolling sigma window.

    The fold's test Sharpe is computed from the test-bar equity curve.
    CPCV Sharpe = weighted mean of fold Sharpes (weighted by n_test_trades).

    Returns dict with cpcv_sharpe, fold_sharpes, n_obs_total.
    """
    n_bars = len(data)
    folds = _build_cpcv_folds(n_bars, CPCV_N_GROUPS, CPCV_K, CPCV_PURGE_BARS, CPCV_EMBARGO_BARS)
    logger.info("CPCV: %d folds (N_groups=%d, k=%d)", len(folds), CPCV_N_GROUPS, CPCV_K)

    cost_model = StaticRoundTripCostModel()
    fold_results = []

    for i, fold in enumerate(folds):
        test_mask = fold["test_mask"]

        # Test data and signals: apply only the test fold bars
        test_data = data.iloc[test_mask]
        test_sigs = signals.iloc[test_mask]

        if len(test_data) < 10:
            continue

        # Run backtest on the test fold
        try:
            result = run_backtest(
                data=test_data,
                signals=test_sigs,
                pair="EURUSD",
                strategy_name="overnight_mr_cpcv",
                cost_model=cost_model,
                initial_capital=100_000.0,
                entry_delay_bars=ENTRY_DELAY_BARS,
                rebalance_mode="discrete",
            )
        except Exception as e:
            logger.warning("CPCV fold %d failed: %s", i, e)
            continue

        ec = result.equity_curve.dropna()
        if len(ec) < 5:
            continue

        ppy = infer_periods_per_year(ec.index)
        fold_metrics = calculate_metrics(
            result.equity_curve, result.trade_log, periods_per_year=ppy
        )
        n_trades = fold_metrics.num_trades

        fold_results.append(
            {
                "fold": i,
                "n_test_bars": int(test_mask.sum()),
                "n_trades": n_trades,
                "sharpe": fold_metrics.sharpe_ratio,
            }
        )
        logger.debug(
            "CPCV fold %d: n_test=%d n_trades=%d sharpe=%.4f",
            i,
            int(test_mask.sum()),
            n_trades,
            fold_metrics.sharpe_ratio,
        )

    if not fold_results:
        logger.error("CPCV: no valid folds produced results")
        return {"cpcv_sharpe": 0.0, "fold_sharpes": [], "n_obs_total": 0}

    # Weighted mean Sharpe by number of test-fold trades (0-trade folds contribute 0 weight)
    total_weight = sum(r["n_trades"] for r in fold_results)
    if total_weight == 0:
        cpcv_sharpe = float(np.mean([r["sharpe"] for r in fold_results]))
    else:
        cpcv_sharpe = sum(r["sharpe"] * r["n_trades"] for r in fold_results) / total_weight

    n_obs_total = sum(r["n_test_bars"] for r in fold_results)
    logger.info(
        "CPCV result: cpcv_sharpe=%.4f from %d folds, total_obs=%d",
        cpcv_sharpe,
        len(fold_results),
        n_obs_total,
    )

    return {
        "cpcv_sharpe": cpcv_sharpe,
        "fold_sharpes": [r["sharpe"] for r in fold_results],
        "n_obs_total": n_obs_total,
        "fold_details": fold_results,
    }


def compute_kill1_dsr(
    is_backtest: dict,
    cpcv_result: dict,
) -> dict:
    """KILL-1: Deflated Sharpe at N=30 (ratified denominator, post-2026-06-18).

    Uses the CPCV net Sharpe as the input to DSR. The n_observations is
    derived from the IS equity curve (bar count). Skew/kurtosis from per-bar
    equity returns.

    Fires if DSR <= 0.95.

    Historical note: originally evaluated at N=48 (retired denominator).
    N=48 over-deflated; N=30 is the correct ratified value. Recompute tracked
    as follow-on for HoQR/NHT (see HISTORICAL NOTE near N_ORG_TRIALS definition).
    """
    ec = is_backtest["equity_curve"].dropna()
    ppy = is_backtest["ppy"]

    # Per-bar returns for skew/kurtosis
    bar_returns = ec.pct_change().dropna()

    if len(bar_returns) < 4:
        logger.warning("KILL-1: insufficient bars for skew/kurtosis; using defaults")
        skew = 0.0
        ek = 0.0
    else:
        skew = float(scipy_stats.skew(bar_returns))
        ek = float(scipy_stats.kurtosis(bar_returns, fisher=True))  # excess kurtosis

    # Use CPCV Sharpe (more conservative than full-IS Sharpe)
    cpcv_sharpe = cpcv_result["cpcv_sharpe"]
    n_obs = len(ec)

    dsr = compute_dsr(
        sharpe_ratio=cpcv_sharpe,
        n_observations=n_obs,
        skewness=skew,
        excess_kurtosis=ek,
        n_trials=N_ORG_TRIALS,
        periods_per_year=ppy,
    )

    fires = dsr <= DSR_THRESHOLD
    net_sharpe = is_backtest["metrics"].sharpe_ratio

    logger.info(
        "KILL-1 DSR: cpcv_sharpe=%.4f net_sharpe=%.4f n_obs=%d skew=%.4f ek=%.4f "
        "ppy=%.0f N=%d -> DSR=%.4f, threshold=%.2f, fires=%s",
        cpcv_sharpe,
        net_sharpe,
        n_obs,
        skew,
        ek,
        ppy,
        N_ORG_TRIALS,
        dsr,
        DSR_THRESHOLD,
        fires,
    )

    return {
        "is_net_sharpe": round(net_sharpe, 4),
        "cpcv_sharpe": round(cpcv_sharpe, 4),
        "DSR_at_N30": round(dsr, 4),
        "n_observations": n_obs,
        "skewness": round(skew, 4),
        "excess_kurtosis": round(ek, 4),
        "periods_per_year": ppy,
        "threshold": DSR_THRESHOLD,
        "fires": fires,
    }


def compute_kill2_cost(is_backtest: dict) -> dict:
    """KILL-2: avg net trade <= 0 pips after 7.5-pip static cost on 2σ subset.

    The 2σ subset = all executed trades (since the signals are already conditioned
    on |r_t| >= 2σ). avg_net_pips is from the trade log's pnl_pips (already net of cost).

    Fires if avg_net_pips <= 0.
    """
    trade_stats = is_backtest["trade_stats"]
    avg_net = trade_stats["avg_net_pips"]
    fires = avg_net <= 0.0

    logger.info(
        "KILL-2 cost: avg_net_trade_pips=%.4f (n_trades=%d), fires=%s",
        avg_net,
        trade_stats["n_trades"],
        fires,
    )
    return {
        "avg_net_trade_pips": round(avg_net, 4),
        "n_trades": trade_stats["n_trades"],
        "fires": fires,
    }


def compute_kill3_hitrate(is_backtest: dict) -> dict:
    """KILL-3: 2σ single-bar reversion hit-rate <= 0.50.

    Hit rate = fraction of trades where gross price move was in our favor
    (before subtracting cost). A hit rate <= 0.50 means the conditioned move
    was more often information/continuation than noise.

    Fires if hit_rate <= 0.50.
    """
    trade_stats = is_backtest["trade_stats"]
    hit_rate = trade_stats["hit_rate"]
    fires = hit_rate <= 0.50

    logger.info(
        "KILL-3 hit rate: reversion_hit_rate=%.4f (n_trades=%d), fires=%s",
        hit_rate,
        trade_stats["n_trades"],
        fires,
    )
    return {
        "reversion_hit_rate": round(hit_rate, 4),
        "n_trades": trade_stats["n_trades"],
        "threshold": 0.50,
        "fires": fires,
    }


def determine_overall_result(gates: dict) -> tuple[str, str | None]:
    """Return (overall_result, first_kill_gate_name)."""
    if gates["kill4"]["fires"]:
        return "INSUFFICIENT-POWER", "KILL-4"
    if gates["kill1"]["fires"]:
        return "KILL-1", "KILL-1"
    if gates["kill2"]["fires"]:
        return "KILL-2", "KILL-2"
    if gates["kill3"]["fires"]:
        return "KILL-3", "KILL-3"
    return "IS-PASSED-AWAITING-OOS", None


def main() -> None:
    logger.info("=== Trial 48 IS Evaluation (A2′ Overnight MR) ===")
    logger.info("OOS DISCIPLINE: IS window only. OOS never read.")

    # 1. Load IS data
    data = load_is_data()
    logger.info("IS data shape: %s", data.shape)

    # 2. Generate signals
    logger.info("Computing signals...")
    signals = compute_signals(data)
    n_nonzero = int((signals != 0.0).sum())
    logger.info(
        "Non-zero signals: %d / %d bars (%.2f%%)",
        n_nonzero,
        len(signals),
        100 * n_nonzero / len(signals),
    )

    # 3. KILL-4: Power gate (IS extrapolation, no OOS data)
    logger.info("--- KILL-4: Power gate ---")
    kill4 = compute_kill4_power_gate(signals, data)

    if kill4["fires"]:
        logger.warning(
            "KILL-4 FIRES: N_oos_expected=%.1f < %d. INSUFFICIENT-POWER.",
            kill4["N_oos_expected"],
            POWER_FLOOR,
        )
        _print_final_result("INSUFFICIENT-POWER", kill4, None, None, None, signals, data)
        return

    # 4. Run full IS backtest (gates 1-3 need trade-level data)
    logger.info("--- Full IS backtest ---")
    is_backtest = run_full_is_backtest(data, signals)

    # 5. CPCV (for DSR input)
    logger.info("--- CPCV Sharpe ---")
    cpcv_result = compute_cpcv_sharpe(data, signals)

    # 6. KILL-1: DSR
    logger.info("--- KILL-1: DSR ---")
    kill1 = compute_kill1_dsr(is_backtest, cpcv_result)

    # 7. KILL-2: Cost domination
    logger.info("--- KILL-2: Cost ---")
    kill2 = compute_kill2_cost(is_backtest)

    # 8. KILL-3: Hit rate
    logger.info("--- KILL-3: Hit rate ---")
    kill3 = compute_kill3_hitrate(is_backtest)

    _print_final_result("", kill4, kill1, kill2, kill3, signals, data)


def _print_final_result(forced_result: str, kill4, kill1, kill2, kill3, signals, data) -> None:
    """Print final summary of all gate results."""
    if forced_result == "INSUFFICIENT-POWER":
        overall = "INSUFFICIENT-POWER"
    else:
        gates = {"kill4": kill4, "kill1": kill1, "kill2": kill2, "kill3": kill3}
        overall, _ = determine_overall_result(gates)

    print("\n" + "=" * 70)
    print("TRIAL 48 IS EVALUATION RESULTS")
    print("=" * 70)
    print(f"Overall result: {overall}")
    print("OOS touched: FALSE")
    print()
    print("KILL-4 Power:")
    print(f"  f_IS (trades/day): {kill4['f_IS_trades_per_day']}")
    print(f"  N_IS qualifying:   {kill4['n_qualifying_IS']}")
    print(f"  IS trading days:   {kill4['n_IS_trading_days']}")
    print(f"  N_OOS expected:    {kill4['N_oos_expected']}")
    print(f"  Power floor:       {kill4['floor']}")
    print(f"  FIRES:             {kill4['fires']}")

    if kill1 is not None:
        print()
        print("KILL-1 DSR:")
        print(f"  IS net Sharpe:     {kill1['is_net_sharpe']}")
        print(f"  CPCV Sharpe:       {kill1['cpcv_sharpe']}")
        print(f"  DSR at N=30:       {kill1['DSR_at_N30']}")
        print(f"  Threshold:         {kill1['threshold']}")
        print(f"  FIRES:             {kill1['fires']}")

    if kill2 is not None:
        print()
        print("KILL-2 Cost domination:")
        print(f"  Avg net trade pips: {kill2['avg_net_trade_pips']}")
        print(f"  FIRES:              {kill2['fires']}")

    if kill3 is not None:
        print()
        print("KILL-3 Reversion hit rate:")
        print(f"  Hit rate:          {kill3['reversion_hit_rate']}")
        print(f"  Threshold:         {kill3['threshold']}")
        print(f"  FIRES:             {kill3['fires']}")

    print()
    print(f"FINAL: {overall}")
    print("=" * 70)


if __name__ == "__main__":
    main()
