"""Engine-vs-script equivalence tests.

These tests exist to catch divergence between the ad-hoc research script
(scripts/vol_targeting.py::simulate_voltarget) and the production engine
(forex_system.backtest.engine::run_backtest with rebalance_mode="continuous").

The gap was discovered 2026-04-24: script Sharpe ≈ 0.76, engine Sharpe ≈ -0.08
on the same USDJPY data.

Root cause (resolved 2026-04-25):
    VolTargetSizer was outputting units = signal * leverage * equity (USD nominal)
    but the engine P&L formula is pnl = price_change * units, which for USDJPY
    (a JPY-quoted pair) requires units = notional_usd / price to give USD P&L.
    The fix divides by current_price for *JPY pairs, matching the script's
    (capital / cur_close) * scale convention.

Test 1 (test_sharpe_within_tolerance):
    Currently XFAILS strict=True. Track 2 reconciliation closed the gap from
    ~0.84 to ~0.16. Script Sharpe ≈ 0.76; Engine Sharpe ≈ 0.60. Residual gap
    likely from rebalance threshold / cost handling differences.
    The strict=True alerts when the gap closes inside tolerance.

Test 2 (test_equity_curve_correlation):
    Passes. Catches future regressions in directional agreement.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers to import script without polluting sys.modules long-term
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_SCRIPT_PATH = _SCRIPTS_DIR / "vol_targeting.py"


def _import_vol_targeting():
    """Dynamically import scripts/vol_targeting.py as a module."""
    spec = importlib.util.spec_from_file_location("vol_targeting_script", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Ensure src/ is on path so the script's own imports (forex_system.*) resolve
    src_dir = str(_SCRIPT_PATH.parent.parent / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Shared fixture: load USDJPY daily data once per module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def usdjpy_df():
    """USDJPY daily parquet — skip entire module if data absent."""
    from forex_system.data.storage import load_parquet
    data_path = Path("data/processed/USDJPY_daily.parquet")
    if not data_path.exists():
        pytest.skip("USDJPY daily parquet not present; skipping equivalence tests")
    return load_parquet("USDJPY", "daily", "data")


@pytest.fixture(scope="module")
def usdjpy_pair_info():
    """USDJPY PairInfo matching both script config and config/vol_target_carry.yaml."""
    from forex_system.core.types import PairInfo
    # Values from config/vol_target_carry.yaml
    return PairInfo(
        symbol="USDJPY",
        pip_value=0.01,
        spread_pips=1.0,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.8,
        swap_short_pips_per_day=-1.5,
    )


# ---------------------------------------------------------------------------
# Path A: Script equity curve
# ---------------------------------------------------------------------------

def _run_script_path(df: pd.DataFrame, pair_info) -> tuple[pd.Series, float]:
    """Run simulate_voltarget and return (equity_curve, sharpe)."""
    mod = _import_vol_targeting()

    CAPITAL = 1_000_000.0
    TARGET_VOL = 0.10
    LEVERAGE_CAP = 2.0

    realized_252 = df["close"].pct_change().rolling(252).std() * np.sqrt(252)

    equity, _ = mod.simulate_voltarget(
        df=df,
        pair_info=pair_info,
        capital=CAPITAL,
        realized_vol=realized_252,
        target_vol=TARGET_VOL,
        leverage_cap=LEVERAGE_CAP,
    )
    m = mod.metrics(equity)
    return equity, m["sharpe"]


# ---------------------------------------------------------------------------
# Path B: Production engine equity curve
# ---------------------------------------------------------------------------

def _run_engine_path(df: pd.DataFrame, pair_info) -> tuple[pd.Series, float]:
    """Run production engine with VolTargetCarryStrategy and return (equity_curve, sharpe)."""
    from forex_system.backtest.engine import run_backtest
    from forex_system.backtest.metrics import calculate_metrics
    from forex_system.costs.model import RealisticCostModel
    from forex_system.features.registry import compute_indicators
    from forex_system.sizing.vol_target import VolTargetSizer
    from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy

    CAPITAL = 1_000_000.0
    LEVERAGE_CAP = 2.0

    # Build cost model from the same PairInfo used by the script
    pair_configs = {"USDJPY": pair_info}
    cost_model = RealisticCostModel(pair_configs=pair_configs)

    # Build sizer matching vol_target_carry config
    sizer = VolTargetSizer(
        leverage_cap=LEVERAGE_CAP,
        max_order_units=5_000_000.0,
        min_order_size=100.0,
    )

    # Compute ATR indicator (required by strategy interface, not used in sizing)
    enriched = compute_indicators(df, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    # Strategy with same parameters as script
    strategy = VolTargetCarryStrategy(params={
        "target_vol": 0.10,
        "vol_window": 252,
        "leverage_cap": LEVERAGE_CAP,
        "pair": "USDJPY",
    })

    signals = strategy.generate_signals(enriched)

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="USDJPY",
        strategy_name="vol_target_carry",
        cost_model=cost_model,
        initial_capital=CAPITAL,
        entry_delay_bars=1,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    metrics = calculate_metrics(result.equity_curve, result.trade_log)
    return result.equity_curve, metrics.sharpe_ratio


# ---------------------------------------------------------------------------
# Test 1: Sharpe within tolerance — XFAIL until residual gap is closed
# Track 2 closed the gap from ~0.84 → ~0.16 by fixing the JPY unit conversion.
# Remaining gap likely from rebalance-threshold semantics or cost handling.
# strict=True alerts when the gap closes inside the 0.10 tolerance.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Residual engine-script Sharpe gap ~0.16 after JPY unit fix; tolerance is 0.10")
def test_sharpe_within_tolerance(usdjpy_df, usdjpy_pair_info):
    """Assert |Sharpe_engine - Sharpe_script| < 0.10.

    Fixed 2026-04-25: VolTargetSizer now divides by price for JPY-quoted pairs
    so the engine's pnl = price_change × units gives USD P&L, matching the
    script's (capital / cur_close) × scale convention.
    """
    equity_script, sharpe_script = _run_script_path(usdjpy_df, usdjpy_pair_info)
    equity_engine, sharpe_engine = _run_engine_path(usdjpy_df, usdjpy_pair_info)

    delta = abs(sharpe_engine - sharpe_script)

    # Always print the gap so the test log records today's divergence
    print(
        f"\n[equivalence] Sharpe gap report:"
        f"\n  Script  Sharpe: {sharpe_script:.4f}"
        f"\n  Engine  Sharpe: {sharpe_engine:.4f}"
        f"\n  |Delta|:        {delta:.4f}"
        f"\n  Tolerance:      0.10"
        f"\n  Status:         {'PASS' if delta < 0.10 else 'FAIL (gap too large)'}"
    )

    assert delta < 0.10, (
        f"Engine-script Sharpe divergence too large: "
        f"script={sharpe_script:.4f}, engine={sharpe_engine:.4f}, |delta|={delta:.4f} >= 0.10. "
        f"See commit 5a33fcb for context. Fix engine-script equivalence before removing xfail."
    )


# ---------------------------------------------------------------------------
# Test 2: Equity curve correlation — should pass today
# ---------------------------------------------------------------------------

def test_equity_curve_correlation(usdjpy_df, usdjpy_pair_info):
    """Assert Pearson correlation between equity curves > 0.5.

    Even if Sharpes differ, both curves should trend in the same direction
    (both are long-only USDJPY with vol-targeted sizing). A correlation drop
    below the threshold indicates a structural regression in one of the paths.

    Threshold set at 0.5 (the actual correlation on the day this test was
    written — calibrate upward as the gap closes).
    """
    equity_script, sharpe_script = _run_script_path(usdjpy_df, usdjpy_pair_info)
    equity_engine, sharpe_engine = _run_engine_path(usdjpy_df, usdjpy_pair_info)

    # Align on common index (engine may have fewer rows after dropna on atr_14)
    common_idx = equity_script.index.intersection(equity_engine.index)
    assert len(common_idx) > 100, (
        f"Too few common timestamps to compute correlation: {len(common_idx)}"
    )

    s = equity_script.loc[common_idx].dropna()
    e = equity_engine.loc[common_idx].dropna()

    # Re-align after individual dropna
    common_idx2 = s.index.intersection(e.index)
    s = s.loc[common_idx2]
    e = e.loc[common_idx2]

    corr = float(s.corr(e))

    print(
        f"\n[equivalence] Equity curve correlation:"
        f"\n  Pearson r:  {corr:.4f}"
        f"\n  Threshold:  0.50"
        f"\n  Script Sharpe:  {sharpe_script:.4f}"
        f"\n  Engine Sharpe:  {sharpe_engine:.4f}"
        f"\n  Common bars:    {len(common_idx2)}"
    )

    assert corr > 0.50, (
        f"Equity curve correlation too low: {corr:.4f} < 0.50. "
        f"Script Sharpe={sharpe_script:.4f}, Engine Sharpe={sharpe_engine:.4f}. "
        f"This suggests a structural regression in one of the simulation paths."
    )
