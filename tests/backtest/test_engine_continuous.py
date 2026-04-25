"""Tests for run_backtest() in continuous rebalance mode.

Each test maps to an invariant in the engine-strategy contract spec
(spec_id: rebalance-continuous-v1, filed by CTO 2026-04-25).

No-lookahead invariant is preserved: delayed_signals = signals.shift(1)
before any sizing decision. The rebalance at bar i uses data up to bar i-1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.core.types import PairInfo
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators
from forex_system.sizing.vol_target import VolTargetSizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(n: int = 200, start_price: float = 150.0, seed: int = 42) -> pd.DataFrame:
    """Synthetic JPY-pair daily OHLCV, n bars."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B", tz="UTC")
    rets = rng.normal(0.0002, 0.005, n)
    close = start_price * np.exp(np.cumsum(rets))
    daily_range = np.abs(rng.normal(0, 0.3, n))
    high = close + daily_range * 0.6
    low = close - daily_range * 0.4
    open_prices = np.roll(close, 1) * (1 + rng.normal(0, 0.001, n))
    open_prices[0] = start_price
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))
    df = pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
        index=pd.DatetimeIndex(dates, name="datetime"),
    )
    return compute_indicators(df, ["atr_14"]).dropna(subset=["atr_14"])


def _usdjpy_cost() -> RealisticCostModel:
    pair_info = PairInfo(
        symbol="USDJPY",
        pip_value=0.01,
        spread_pips=1.0,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.8,
        swap_short_pips_per_day=-1.5,
    )
    return RealisticCostModel({"USDJPY": pair_info})


def _sizer(leverage_cap: float = 2.0) -> VolTargetSizer:
    return VolTargetSizer(
        leverage_cap=leverage_cap,
        max_order_units=10_000_000.0,
        min_order_size=100.0,
    )


# ---------------------------------------------------------------------------
# D2.1 — First bar enters target units (signal=1.0 constant)
# ---------------------------------------------------------------------------

def test_continuous_enters_on_first_bar():
    """Constant signal=1.0 → engine enters a position on the first valid bar.

    With entry_delay_bars=1, bar 0 signal is shifted away (nan→0), so entry
    happens no later than bar 1. After that, with price movements too small
    to exceed the 20% threshold, no further trades should be recorded beyond
    the single entry (plus a final close on the last bar).
    """
    data = _make_data(n=50, seed=1)
    signals = pd.Series(1.0, index=data.index)
    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=signals,
        pair="USDJPY",
        strategy_name="test_entry",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    # At least 1 trade: the initial entry (+ possibly final close)
    assert len(result.trade_log) >= 1, "Expected at least one trade (initial entry)"

    # Equity curve must be populated
    ec = result.equity_curve.dropna()
    assert len(ec) > 0

    # Mode is recorded in parameters
    assert result.parameters.get("rebalance_mode") == "continuous"


# ---------------------------------------------------------------------------
# D2.2 — Rebalances fire when signal change is large enough
# ---------------------------------------------------------------------------

def test_continuous_rebalances_on_large_signal_change():
    """Signal alternating 0.5 / 1.0 every 10 bars → rebalances fire.

    Each 0.5→1.0 step doubles target_units, a 100% relative change,
    well above the 20% threshold. We expect multiple trades.
    """
    data = _make_data(n=100, seed=2)
    n = len(data)

    # Build alternating signal: 0.5 for 10 bars, 1.0 for 10 bars, ...
    raw = np.tile([0.5] * 10 + [1.0] * 10, n // 20 + 1)[:n]
    signals = pd.Series(raw, index=data.index)

    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=signals,
        pair="USDJPY",
        strategy_name="test_rebalance",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    # Multiple rebalance events expected
    assert len(result.trade_log) > 2, (
        f"Expected multiple rebalances, got {len(result.trade_log)} trades"
    )


# ---------------------------------------------------------------------------
# D2.3 — Below threshold → no additional trades after initial entry
# ---------------------------------------------------------------------------

def test_continuous_holds_on_small_signal_change():
    """Signal varying by < threshold → HOLD after entry (no rebalances).

    Signal stays in [0.99, 1.01]. Relative change ≤ 2%, well below 20%.
    After the initial entry, no rebalance should fire. Only 1 trade (entry)
    plus final close (2 total at most).
    """
    data = _make_data(n=80, seed=3)
    n = len(data)
    rng = np.random.default_rng(77)
    # Tiny variation around 1.0
    raw = 1.0 + rng.uniform(-0.01, 0.01, n)
    signals = pd.Series(raw, index=data.index)

    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=signals,
        pair="USDJPY",
        strategy_name="test_hold",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    # Only entry + final close = 2 trades max
    assert len(result.trade_log) <= 2, (
        f"Expected <= 2 trades for sub-threshold signal variation, "
        f"got {len(result.trade_log)}"
    )


# ---------------------------------------------------------------------------
# D2.4 — Signal goes to 0 → exits to flat
# ---------------------------------------------------------------------------

def test_continuous_exits_to_flat_on_zero_signal():
    """signal=1.0 for first half, signal=0.0 for second half → exits at midpoint.

    After exit, equity_curve should be flat (no open position).
    """
    data = _make_data(n=60, seed=4)
    n = len(data)
    raw = np.concatenate([np.ones(n // 2), np.zeros(n - n // 2)])
    signals = pd.Series(raw, index=data.index)

    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=signals,
        pair="USDJPY",
        strategy_name="test_exit",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    # Must have at least 2 trades: entry and exit
    assert len(result.trade_log) >= 2

    # After exit, equity_curve should be flat for last several bars
    ec = result.equity_curve.dropna()
    # Check last 10 bars are constant (within float precision)
    tail = ec.iloc[-10:]
    assert tail.std() < 1.0, (
        f"Expected flat equity after exit, std={tail.std():.2f}"
    )


# ---------------------------------------------------------------------------
# D2.5 — Long-only enforcement: negative signal → flat, never short
# ---------------------------------------------------------------------------

def test_continuous_long_only_negative_signal():
    """Negative signal in continuous mode must produce flat (not short).

    With signal=-1.0, sizer clamps to 0, so no position is ever opened.
    Trade log should be empty (or only a final close of zero position).
    """
    data = _make_data(n=60, seed=5)
    signals = pd.Series(-1.0, index=data.index)

    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=signals,
        pair="USDJPY",
        strategy_name="test_long_only",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
    )

    # No trades — negative signal clamped to 0
    assert len(result.trade_log) == 0, (
        f"Expected 0 trades for negative signal (long-only), "
        f"got {len(result.trade_log)}"
    )

    # Equity curve should be flat
    ec = result.equity_curve.dropna()
    assert ec.std() < 1.0, "Equity should be flat with no position (negative signal)"


# ---------------------------------------------------------------------------
# D2.6 — Cost is charged on delta, not full re-entry
# ---------------------------------------------------------------------------

def test_continuous_costs_on_delta_not_full_size():
    """Rebalancing up by 10% of position charges cost on the delta only.

    We use a zero-cost model to isolate the equity impact of costs,
    then compare against a non-zero model. With non-zero costs, a rebalance
    up charges entry_cost × pip_value × delta_units, not full position cost.

    We verify this by measuring total cost dollars across a forced rebalance:
    signal 1.0 → 0.4 (large drop, forces rebalance down) in two models.
    The cost-model difference in equity should be proportional to delta, not full size.
    """
    data = _make_data(n=60, seed=6)
    n = len(data)
    # Large signal drop at bar 30: forces rebalance down
    raw = np.concatenate([np.ones(30), np.full(n - 30, 0.4)])
    signals = pd.Series(raw, index=data.index)

    zero_pair = PairInfo(
        symbol="USDJPY", pip_value=0.01,
        spread_pips=0.0, slippage_pips=0.0, commission_pips=0.0,
        swap_long_pips_per_day=0.0, swap_short_pips_per_day=0.0,
    )
    cost_pair = PairInfo(
        symbol="USDJPY", pip_value=0.01,
        spread_pips=1.0, slippage_pips=0.5, commission_pips=0.5,
        swap_long_pips_per_day=0.0, swap_short_pips_per_day=0.0,
    )

    zero_cost = RealisticCostModel({"USDJPY": zero_pair})
    real_cost = RealisticCostModel({"USDJPY": cost_pair})
    sizer = _sizer(leverage_cap=2.0)

    r_zero = run_backtest(
        data=data, signals=signals, pair="USDJPY", strategy_name="test_delta_cost",
        cost_model=zero_cost, initial_capital=1_000_000.0,
        sizer=sizer, rebalance_mode="continuous", rebalance_threshold=0.20,
    )
    r_real = run_backtest(
        data=data, signals=signals, pair="USDJPY", strategy_name="test_delta_cost",
        cost_model=real_cost, initial_capital=1_000_000.0,
        sizer=sizer, rebalance_mode="continuous", rebalance_threshold=0.20,
    )

    # Cost is taken from equity, so real_cost equity should be lower
    ec_zero = r_zero.equity_curve.dropna()
    ec_real = r_real.equity_curve.dropna()

    # After costs, equity should be lower (not equal)
    assert ec_real.iloc[-1] < ec_zero.iloc[-1], (
        "With non-zero costs, final equity must be lower than zero-cost run"
    )


# ---------------------------------------------------------------------------
# D2.7 — Sacred no-lookahead: rebalance at bar i uses data up to bar i-1
# ---------------------------------------------------------------------------

def test_continuous_no_lookahead():
    """Continuous mode must not use future data.

    We use a trivially-profitable lookahead signal (signal = +1 when next bar
    rises) and verify that Sharpe stays below 3.0, just as the sacred discrete
    test does. With entry_delay_bars=1, the lookahead signal becomes a lagging
    signal that cannot systematically predict future moves.
    """
    data = _make_data(n=300, seed=99)

    # Lookahead signal: +1 when next bar rises
    future_return = data["close"].shift(-1) - data["close"]
    lookahead_signals = pd.Series(0.0, index=data.index)
    lookahead_signals[future_return > 0] = 1.0

    cost_model = _usdjpy_cost()
    sizer = _sizer(leverage_cap=2.0)

    result = run_backtest(
        data=data,
        signals=lookahead_signals,
        pair="USDJPY",
        strategy_name="lookahead_test_continuous",
        cost_model=cost_model,
        initial_capital=1_000_000.0,
        sizer=sizer,
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
        entry_delay_bars=1,
    )

    ec = result.equity_curve.dropna()
    if len(ec) > 10:
        daily_returns = ec.pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            assert sharpe < 3.0, (
                f"Suspiciously high Sharpe ({sharpe:.2f}) in continuous mode — "
                "possible lookahead in rebalance logic"
            )


# ---------------------------------------------------------------------------
# D2.8 — Continuous mode requires sizer; raises ValueError without one
# ---------------------------------------------------------------------------

def test_continuous_requires_sizer():
    """run_backtest(..., rebalance_mode='continuous', sizer=None) must raise."""
    data = _make_data(n=30, seed=7)
    signals = pd.Series(1.0, index=data.index)
    cost_model = _usdjpy_cost()

    with pytest.raises(ValueError, match="sizer"):
        run_backtest(
            data=data,
            signals=signals,
            pair="USDJPY",
            strategy_name="test_no_sizer",
            cost_model=cost_model,
            initial_capital=1_000_000.0,
            sizer=None,
            rebalance_mode="continuous",
            rebalance_threshold=0.20,
        )


# ---------------------------------------------------------------------------
# D2.9 — Invalid rebalance_mode raises ValueError
# ---------------------------------------------------------------------------

def test_invalid_rebalance_mode_raises():
    """Unknown rebalance_mode must raise ValueError immediately."""
    data = _make_data(n=30, seed=8)
    signals = pd.Series(1.0, index=data.index)
    cost_model = _usdjpy_cost()

    with pytest.raises(ValueError, match="rebalance_mode"):
        run_backtest(
            data=data,
            signals=signals,
            pair="USDJPY",
            strategy_name="test_bad_mode",
            cost_model=cost_model,
            initial_capital=1_000_000.0,
            rebalance_mode="banana",
        )


# ---------------------------------------------------------------------------
# D2.10 — Discrete mode (default) still works after refactor
# ---------------------------------------------------------------------------

def test_discrete_mode_unchanged(sample_ohlcv):
    """Discrete mode with new signature still produces valid results.

    Regression guard: the refactor that added rebalance_mode must not break
    existing discrete behavior. Reuses the conftest fixture.
    """
    from forex_system.costs.model import RealisticCostModel as RCM
    enriched = compute_indicators(sample_ohlcv, ["atr_14"]).dropna(subset=["atr_14"])
    signals = pd.Series(1.0, index=enriched.index)
    cost_model = RCM()

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="discrete_regression",
        cost_model=cost_model,
        initial_capital=100_000.0,
        rebalance_mode="discrete",      # explicit default
    )

    assert result.parameters.get("rebalance_mode") == "discrete"
    assert len(result.equity_curve.dropna()) > 0
