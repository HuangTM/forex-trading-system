"""Minimal Trend Basket IS-only evaluation — M1 (MACD cross) + M2 (EMA cross).

Pre-registration: .fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-minimal-trend-basket-v2.yaml
subtask_id: qd-minimal-basket-is-eval

Computes the four per-member pre-OOS kill gates from IS data (2021-01-03..2024-05-31) ONLY.
OOS (2024-07-01..2025-12-31) is NEVER read, sliced, or referenced.

Gates evaluated per member (in order):
    POWER   : IS net round-trip trade count < 30 → INSUFFICIENT-POWER
    KILL-1  : DSR at N=50 <= 0.95 on CPCV OOF net-of-cost returns → KILL-1
    KILL-2  : avg net trade pips <= 0 after 7.5-pip RT → KILL-2
    KILL-2B : positive net Sharpe in >= 2 of 3 IS year-blocks (regime consistency)

Decision rule per member:
    ALL gates pass → MEMBER-PASSED-AWAITING-OOS-AUTH (do NOT burn OOS)
    Any gate fires → report KILL with real numbers

Family rule:
    0 of 2 members pass ALL gates → FAMILY_KILL (clean negative evidence)
    >= 1 member passes ALL gates → MEMBER-PASSED-AWAITING-OOS-AUTH (stop, report, wait)

FROZEN CONSTANTS from pre-reg (DO NOT MODIFY):
    IS:     2021-01-03 to 2024-05-31
    N:      50 (honest-N at freeze, fixed denominator for ALL members)
    CPCV:   N_groups=8, k=2, purge=10 trading days, embargo=5 trading days (FIXED, not data-derived)
    cost:   7.5 pip round-trip static (StaticRoundTripCostModel)
    size:   vol-targeted, size_multiplier=0.25 (continuous mode)
    ATR:    14-bar (catastrophic stop only — not implemented as a gate here; stop is a risk rail)

Run:
    python scripts/trial_basket_is_eval.py

OOS discipline:
    The data slice is performed STRICTLY before 2024-06-01. The embargo (June 2024)
    and OOS (2024-07-01 onward) are never loaded or referenced.
"""

from __future__ import annotations

import logging
import sys
from itertools import combinations
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
from forex_system.features.registry import compute_indicators  # noqa: E402
from forex_system.harness.dsr import compute_dsr  # noqa: E402
from forex_system.sizing.vol_target import VolTargetSizer  # noqa: E402
from forex_system.strategies.ema_cross import EMACrossStrategy  # noqa: E402
from forex_system.strategies.macd_cross import MACDCrossStrategy  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FROZEN CONSTANTS — DO NOT MODIFY (from pre-registration qr-minimal-trend-basket-v2.yaml)
# ---------------------------------------------------------------------------
IS_START = "2021-01-03"
IS_END = "2024-05-31"  # inclusive; embargo = June 2024; OOS starts 2024-07-01

# Denominator FIXED at freeze; killed members do NOT reduce it (HC-5)
N_ORG_TRIALS = 50

# CPCV parameters (pre-registration: N_groups=8, k=2, FIXED purge=10d/embargo=5d)
CPCV_N_GROUPS = 8
CPCV_K = 2  # test-fold size in groups
# Trading days → 1h bars: 10 trading days × 24h/day × (5/7) ≈ 171 bars
# But for FX 1h the data is continuous weekdays; ~10 trading days ≈ 240 bars
# Using calendar: 10 trading days × 24h = 240 bars (each weekday = 24 bars of trading)
# This is the FIXED constant frozen in the pre-reg.
CPCV_PURGE_BARS = 240   # 10 trading days × 24 1h bars
CPCV_EMBARGO_BARS = 120  # 5 trading days × 24 1h bars

# Power floor: >= 30 IS round-trip trades
POWER_FLOOR = 30

# Cost: 7.5-pip round-trip (frozen, HC-4)
ROUND_TRIP_PIPS = 7.5

# DSR threshold
DSR_THRESHOLD = 0.95

# Size multiplier per spec: vol-targeted, size_multiplier=0.25 → leverage_cap=0.25
SIZE_MULTIPLIER = 0.25

# Pip value for EURUSD
PIP_VALUE = 0.0001

# IS year-block definitions for regime consistency gate
YEAR_BLOCKS = [
    ("2021-01-01", "2021-12-31", "2021"),
    ("2022-01-01", "2022-12-31", "2022"),
    ("2023-01-01", "2024-05-31", "2023+2024H1"),
]


def load_is_data() -> pd.DataFrame:
    """Load EURUSD 1h data, slice to IS window ONLY. Never touches OOS."""
    data_path = PROJECT_ROOT / "data" / "processed" / "EURUSD_1h.parquet"
    df = pd.read_parquet(data_path)

    # Slice: IS window only. Strict end at 2024-05-31 23:59:59.
    is_data = df[df.index <= f"{IS_END} 23:59:59"].copy()
    is_data = is_data[is_data.index >= IS_START].copy()

    logger.info(
        "IS data loaded: bars=%d range=%s to %s "
        "oos_touched=false source=EURUSD_1h.parquet",
        len(is_data),
        is_data.index[0],
        is_data.index[-1],
    )
    return is_data


def prepare_data_with_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Add ATR(14) and any other required indicators."""
    return compute_indicators(data, ["atr_14"])


def build_sizer() -> VolTargetSizer:
    """Build vol-targeted sizer with size_multiplier=0.25 per frozen spec."""
    return VolTargetSizer(
        leverage_cap=SIZE_MULTIPLIER,
        max_order_units=10_000_000.0,
        min_order_size=1000.0,
    )


def run_member_backtest(
    data: pd.DataFrame,
    signals: pd.Series,
    member_name: str,
) -> dict:
    """Run backtest for one member; return equity curve, trade log, metrics."""
    cost_model = StaticRoundTripCostModel()
    sizer = build_sizer()

    result = run_backtest(
        data=data,
        signals=signals,
        pair="EURUSD",
        strategy_name=member_name,
        cost_model=cost_model,
        initial_capital=100_000.0,
        entry_delay_bars=1,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.10,
        constant_capital_sizing=True,
    )

    ec = result.equity_curve.dropna()
    ppy = infer_periods_per_year(ec.index)
    metrics = calculate_metrics(result.equity_curve, result.trade_log, periods_per_year=ppy)

    return {
        "equity_curve": result.equity_curve,
        "trade_log": result.trade_log,
        "metrics": metrics,
        "ppy": ppy,
    }


def compute_trade_stats(trade_log: list) -> dict:
    """Compute avg net trade pips from the trade log."""
    if not trade_log:
        return {"n_trades": 0, "avg_net_pips": 0.0}

    # Round-trips only: count reversal events (each cross = 1 round-trip)
    # In continuous mode the trade_log has rebalance delta trades; we aggregate
    # by pnl_pips (net of cost, already deducted by the engine)
    pnl_pips = [t.pnl_pips for t in trade_log]
    n = len(pnl_pips)
    avg_net = sum(pnl_pips) / n if n > 0 else 0.0

    return {
        "n_trades": n,
        "avg_net_pips": avg_net,
    }


def compute_regime_consistency(data: pd.DataFrame, signals: pd.Series, member_name: str) -> dict:
    """Compute net Sharpe in each of the 3 IS year-blocks.

    Returns dict with per-block Sharpe and count of positive-Sharpe blocks.
    Fires regime-consistency KILL if positive blocks < 2.
    """
    block_results = []
    cost_model = StaticRoundTripCostModel()
    sizer = build_sizer()

    for start_str, end_str, label in YEAR_BLOCKS:
        block_mask = (data.index >= start_str) & (data.index <= f"{end_str} 23:59:59")
        block_data = data[block_mask]
        block_sigs = signals[block_mask]

        if len(block_data) < 100:
            block_results.append({"label": label, "sharpe": 0.0, "n_bars": 0})
            continue

        try:
            result = run_backtest(
                data=block_data,
                signals=block_sigs,
                pair="EURUSD",
                strategy_name=f"{member_name}_block_{label}",
                cost_model=cost_model,
                initial_capital=100_000.0,
                entry_delay_bars=1,
                sizer=sizer,
                rebalance_mode="continuous",
                rebalance_threshold=0.10,
                constant_capital_sizing=True,
            )
            ec = result.equity_curve.dropna()
            ppy = infer_periods_per_year(ec.index)
            m = calculate_metrics(result.equity_curve, result.trade_log, periods_per_year=ppy)
            block_results.append({"label": label, "sharpe": m.sharpe_ratio, "n_bars": len(block_data)})
        except Exception as e:
            logger.warning("Regime block %s failed: %s", label, e)
            block_results.append({"label": label, "sharpe": 0.0, "n_bars": 0})

    n_positive = sum(1 for b in block_results if b["sharpe"] > 0.0)
    fires = n_positive < 2

    logger.info(
        "regime_consistency member=%s blocks=%s n_positive=%d fires=%s",
        member_name,
        [(b["label"], round(b["sharpe"], 4)) for b in block_results],
        n_positive,
        fires,
    )

    return {
        "block_sharpes": {b["label"]: round(b["sharpe"], 4) for b in block_results},
        "n_positive_blocks": n_positive,
        "fires": fires,
    }


def _build_cpcv_folds(n_bars: int, n_groups: int, k: int, purge: int, embargo: int) -> list[dict]:
    """Build CPCV fold definitions with FIXED purge and embargo.

    Splits [0, n_bars) into n_groups equal groups. Each C(n_groups, k)
    combination is used as test; remaining groups form train. FIXED purge
    and embargo (not data-derived, per F-004 fix in pre-reg v2).

    Returns list of dicts with keys: train_mask, test_mask.
    """
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

        embargo_mask = np.zeros(n_bars, dtype=bool)
        for tg in test_groups:
            s, e = group_boundaries[tg]
            # FIXED purge: remove train bars before each test fold start
            purge_start = max(0, s - purge)
            embargo_mask[purge_start:s] = True
            # FIXED embargo: remove train bars after each test fold end
            embargo_end = min(n_bars, e + embargo)
            embargo_mask[e:embargo_end] = True

        train_mask = ~test_mask & ~embargo_mask

        if train_mask.sum() < 100:
            continue  # skip degenerate folds

        folds.append({"train_mask": train_mask, "test_mask": test_mask})

    return folds


def compute_cpcv_oof_returns(
    data: pd.DataFrame,
    signals: pd.Series,
    member_name: str,
) -> dict:
    """Compute CPCV OOF net-of-cost return series and Sharpe for DSR input.

    CPCV: N_groups=8, k=2 → C(8,2)=28 combinations → 28 OOF paths.
    FIXED purge=240 bars (10 trading days) + FIXED embargo=120 bars (5 trading days).
    These are NOT derived from in-fold data (F-004 fix).

    For always-in trend strategies, signals on the test fold are evaluated
    directly — no training phase is needed since no parameters are fit to data
    (the EMA/MACD params are literature-fixed).
    """
    n_bars = len(data)
    folds = _build_cpcv_folds(n_bars, CPCV_N_GROUPS, CPCV_K, CPCV_PURGE_BARS, CPCV_EMBARGO_BARS)
    logger.info(
        "CPCV member=%s folds=%d N_groups=%d k=%d "
        "purge_bars=%d embargo_bars=%d purge_source=frozen_prereg",
        member_name,
        len(folds),
        CPCV_N_GROUPS,
        CPCV_K,
        CPCV_PURGE_BARS,
        CPCV_EMBARGO_BARS,
    )

    cost_model = StaticRoundTripCostModel()
    sizer = build_sizer()
    fold_results = []

    for i, fold in enumerate(folds):
        test_mask = fold["test_mask"]
        test_data = data.iloc[test_mask]
        test_sigs = signals.iloc[test_mask]

        if len(test_data) < 50:
            continue

        try:
            result = run_backtest(
                data=test_data,
                signals=test_sigs,
                pair="EURUSD",
                strategy_name=f"{member_name}_cpcv_fold{i}",
                cost_model=cost_model,
                initial_capital=100_000.0,
                entry_delay_bars=1,
                sizer=sizer,
                rebalance_mode="continuous",
                rebalance_threshold=0.10,
                constant_capital_sizing=True,
            )
        except Exception as e:
            logger.warning("CPCV fold %d member=%s failed: %s", i, member_name, e)
            continue

        ec = result.equity_curve.dropna()
        if len(ec) < 5:
            continue

        ppy = infer_periods_per_year(ec.index)
        fold_metrics = calculate_metrics(result.equity_curve, result.trade_log, periods_per_year=ppy)
        n_trades = fold_metrics.num_trades

        fold_results.append({
            "fold": i,
            "n_test_bars": int(test_mask.sum()),
            "n_trades": n_trades,
            "sharpe": fold_metrics.sharpe_ratio,
        })

        logger.debug(
            "CPCV fold %d member=%s: n_test=%d n_trades=%d sharpe=%.4f",
            i,
            member_name,
            int(test_mask.sum()),
            n_trades,
            fold_metrics.sharpe_ratio,
        )

    if not fold_results:
        logger.error("CPCV: no valid folds for member=%s", member_name)
        return {"cpcv_sharpe": 0.0, "fold_sharpes": [], "n_obs_total": 0}

    # Weighted mean Sharpe by test-fold trades (0-trade folds get 0 weight)
    total_weight = sum(r["n_trades"] for r in fold_results)
    if total_weight == 0:
        cpcv_sharpe = float(np.mean([r["sharpe"] for r in fold_results]))
    else:
        cpcv_sharpe = sum(r["sharpe"] * r["n_trades"] for r in fold_results) / total_weight

    n_obs_total = sum(r["n_test_bars"] for r in fold_results)

    logger.info(
        "CPCV result: member=%s cpcv_sharpe=%.4f folds=%d total_obs=%d",
        member_name,
        cpcv_sharpe,
        len(fold_results),
        n_obs_total,
    )

    return {
        "cpcv_sharpe": cpcv_sharpe,
        "fold_sharpes": [r["sharpe"] for r in fold_results],
        "fold_details": fold_results,
        "n_obs_total": n_obs_total,
    }


def compute_dsr_gate(
    is_backtest: dict,
    cpcv_result: dict,
    member_name: str,
) -> dict:
    """Compute DSR at N=50 (frozen denominator per HC-5).

    Uses CPCV OOF Sharpe (more conservative than full-IS Sharpe).
    Fires if DSR <= 0.95.
    """
    ec = is_backtest["equity_curve"].dropna()
    ppy = is_backtest["ppy"]

    bar_returns = ec.pct_change().dropna()

    if len(bar_returns) < 4:
        logger.warning("DSR gate: insufficient bars for member=%s; using skew/kurt=0", member_name)
        skew = 0.0
        ek = 0.0
    else:
        skew = float(scipy_stats.skew(bar_returns))
        ek = float(scipy_stats.kurtosis(bar_returns, fisher=True))  # excess kurtosis

    cpcv_sharpe = cpcv_result["cpcv_sharpe"]
    n_obs = len(ec)

    dsr = compute_dsr(
        sharpe_ratio=cpcv_sharpe,
        n_observations=n_obs,
        skewness=skew,
        excess_kurtosis=ek,
        n_trials=N_ORG_TRIALS,  # FIXED at 50, never reduced per HC-5
        periods_per_year=ppy,
    )

    fires = dsr <= DSR_THRESHOLD
    net_sharpe = is_backtest["metrics"].sharpe_ratio

    logger.info(
        "DSR gate: member=%s cpcv_sharpe=%.4f net_sharpe=%.4f n_obs=%d "
        "skew=%.4f ek=%.4f ppy=%.0f N=%d dsr=%.4f threshold=%.2f fires=%s",
        member_name,
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
        "DSR_at_N50": round(dsr, 4),
        "n_observations": n_obs,
        "skewness": round(skew, 4),
        "excess_kurtosis": round(ek, 4),
        "periods_per_year": ppy,
        "N_trials": N_ORG_TRIALS,
        "threshold": DSR_THRESHOLD,
        "fires": fires,
    }


def evaluate_member(
    data: pd.DataFrame,
    member_name: str,
    strategy,
    trial_id: str,
) -> dict:
    """Run all IS gates for one basket member and return full result dict."""
    logger.info("=== Evaluating member: %s (trial_id=%s) ===", member_name, trial_id)

    # 1. Generate signals on full IS data
    signals = strategy.generate_signals(data)
    n_nonzero = int((signals != 0.0).sum())
    logger.info(
        "signals.generated member=%s nonzero=%d/%d bars",
        member_name,
        n_nonzero,
        len(signals),
    )

    # 2. Run full IS backtest
    is_backtest = run_member_backtest(data, signals, member_name)
    n_trades = is_backtest["metrics"].num_trades
    trade_stats = compute_trade_stats(is_backtest["trade_log"])

    logger.info(
        "IS backtest complete: member=%s n_trades=%d avg_net_pips=%.4f is_sharpe=%.4f",
        member_name,
        n_trades,
        trade_stats["avg_net_pips"],
        is_backtest["metrics"].sharpe_ratio,
    )

    # 3. POWER gate: IS round-trips >= 30
    power_ok = n_trades >= POWER_FLOOR
    if not power_ok:
        logger.warning(
            "POWER gate fires: member=%s n_trades=%d < %d",
            member_name,
            n_trades,
            POWER_FLOOR,
        )
        return {
            "member": member_name,
            "trial_id": trial_id,
            "trades_IS": n_trades,
            "avg_net_trade_pips": round(trade_stats["avg_net_pips"], 4),
            "cpcv_net_sharpe": None,
            "DSR_at_N50": None,
            "power_ok": False,
            "regime_consistency": None,
            "verdict": "INSUFFICIENT-POWER",
            "kill_gate": "POWER",
        }

    # 4. CPCV OOF Sharpe
    cpcv_result = compute_cpcv_oof_returns(data, signals, member_name)

    # 5. DSR gate (KILL-1)
    dsr_gate = compute_dsr_gate(is_backtest, cpcv_result, member_name)

    # 6. KILL-2: avg net trade pips
    kill2_fires = trade_stats["avg_net_pips"] <= 0.0
    logger.info(
        "KILL-2 gate: member=%s avg_net_pips=%.4f fires=%s",
        member_name,
        trade_stats["avg_net_pips"],
        kill2_fires,
    )

    # 7. Regime consistency gate
    regime = compute_regime_consistency(data, signals, member_name)

    # 8. Determine verdict
    if dsr_gate["fires"]:
        verdict = "KILL-1"
        kill_gate = "KILL-1 (DSR)"
    elif kill2_fires:
        verdict = "KILL-2"
        kill_gate = "KILL-2 (avg_net_trade_pips <= 0)"
    elif regime["fires"]:
        verdict = "KILL-2"  # regime consistency maps to KILL-2 per spec
        kill_gate = "KILL-2B (regime consistency: positive Sharpe blocks < 2)"
    else:
        verdict = "PASS"
        kill_gate = None

    logger.info(
        "member.verdict member=%s verdict=%s kill_gate=%s "
        "trades=%d avg_net_pips=%.4f dsr=%.4f n_positive_blocks=%d",
        member_name,
        verdict,
        kill_gate,
        n_trades,
        trade_stats["avg_net_pips"],
        dsr_gate["DSR_at_N50"],
        regime["n_positive_blocks"],
    )

    return {
        "member": member_name,
        "trial_id": trial_id,
        "trades_IS": n_trades,
        "avg_net_trade_pips": round(trade_stats["avg_net_pips"], 4),
        "cpcv_net_sharpe": cpcv_result["cpcv_sharpe"],
        "DSR_at_N50": dsr_gate["DSR_at_N50"],
        "power_ok": True,
        "regime_consistency": regime,
        "dsr_detail": dsr_gate,
        "verdict": verdict,
        "kill_gate": kill_gate,
    }


def main() -> None:
    logger.info("=== Minimal Trend Basket IS Evaluation ===")
    logger.info(
        "pre_reg=qr-minimal-trend-basket-v2.yaml "
        "N=%d purge_bars=%d embargo_bars=%d cost_rt_pips=%.1f "
        "size_multiplier=%.2f oos_touched=false",
        N_ORG_TRIALS,
        CPCV_PURGE_BARS,
        CPCV_EMBARGO_BARS,
        ROUND_TRIP_PIPS,
        SIZE_MULTIPLIER,
    )

    # 1. Load IS data only
    raw_data = load_is_data()
    data = prepare_data_with_indicators(raw_data)

    # 2. Evaluate M1: MACD(12,26,9) cross
    m1_strategy = MACDCrossStrategy(params={})
    m1_result = evaluate_member(data, "M1_MACD_cross", m1_strategy, "82497d05")

    # 3. Evaluate M2: EMA(50)/EMA(200) cross
    m2_strategy = EMACrossStrategy(params={})
    m2_result = evaluate_member(data, "M2_EMA_50_200", m2_strategy, "b309935c")

    # 4. Family verdict
    m1_pass = m1_result["verdict"] == "PASS"
    m2_pass = m2_result["verdict"] == "PASS"

    if m1_pass or m2_pass:
        family_result = "MEMBER-PASSED-AWAITING-OOS"
        logger.info(
            "family.verdict=MEMBER-PASSED-AWAITING-OOS "
            "m1_pass=%s m2_pass=%s OOS_NOT_BURNED",
            m1_pass,
            m2_pass,
        )
    else:
        family_result = "FAMILY_KILL"
        logger.info(
            "family.verdict=FAMILY_KILL "
            "m1_verdict=%s m2_verdict=%s "
            "clean_negative_evidence=trend_family_also_cost_bound_at_1h",
            m1_result["verdict"],
            m2_result["verdict"],
        )

    # 5. Print summary
    _print_summary(m1_result, m2_result, family_result)


def _print_summary(m1: dict, m2: dict, family_result: str) -> None:
    """Print final gate results."""
    print("\n" + "=" * 70)
    print("MINIMAL TREND BASKET IS EVALUATION RESULTS")
    print("=" * 70)
    print("Pre-registration: qr-minimal-trend-basket-v2.yaml")
    print(f"N_trials (FIXED, HC-5): {N_ORG_TRIALS}")
    print(f"CPCV: N_groups={CPCV_N_GROUPS}, k={CPCV_K}, purge={CPCV_PURGE_BARS}bars, embargo={CPCV_EMBARGO_BARS}bars")
    print(f"Cost: {ROUND_TRIP_PIPS} pips round-trip (frozen)")
    print(f"Size multiplier: {SIZE_MULTIPLIER} (vol-targeted continuous)")
    print("OOS touched: FALSE")
    print()

    for m in [m1, m2]:
        print(f"--- {m['member']} (trial_id={m['trial_id']}) ---")
        print(f"  trades_IS:          {m['trades_IS']}")
        print(f"  power_ok (>=30):    {m['power_ok']}")
        print(f"  avg_net_pips:       {m['avg_net_trade_pips']}")
        cpcv_str = f"{m['cpcv_net_sharpe']:.4f}" if m['cpcv_net_sharpe'] is not None else "N/A"
        dsr_str = f"{m['DSR_at_N50']:.4f}" if m['DSR_at_N50'] is not None else "N/A"
        print(f"  CPCV net Sharpe:    {cpcv_str}")
        print(f"  DSR at N=50:        {dsr_str}")
        if m.get("regime_consistency"):
            rc = m["regime_consistency"]
            print(f"  regime blocks:      {rc['block_sharpes']}")
            print(f"  positive blocks:    {rc['n_positive_blocks']}/3")
        print(f"  VERDICT:            {m['verdict']}")
        if m.get("kill_gate"):
            print(f"  Kill gate:          {m['kill_gate']}")
        print()

    print(f"FAMILY RESULT: {family_result}")
    print("=" * 70)


if __name__ == "__main__":
    main()
