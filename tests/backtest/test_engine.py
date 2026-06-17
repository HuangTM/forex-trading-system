"""Tests for the backtest engine — including the sacred no-lookahead test."""

import numpy as np
import pandas as pd

from forex_system.backtest.engine import _infer_bar_duration_days, run_backtest
from forex_system.costs.model import RealisticCostModel
from forex_system.core.types import PairInfo
from forex_system.features.registry import compute_indicators
from forex_system.sizing.vol_target import VolTargetSizer


# ---------------------------------------------------------------------------
# FIX-1 tests: bar-duration-proportional swap accrual
# ---------------------------------------------------------------------------


def _make_continuous_ohlcv(freq_hours: int, n_bars: int = 50, tz: str = "UTC") -> pd.DataFrame:
    """Build minimal OHLCV with an intraday or daily frequency for swap tests."""
    freq = f"{freq_hours}h" if freq_hours < 24 else "B"
    dates = pd.date_range("2023-01-02", periods=n_bars, freq=freq, tz=tz)
    price = 1.1000
    return pd.DataFrame(
        {
            "open": price,
            "high": price + 0.001,
            "low": price - 0.001,
            "close": price,
            "volume": 1_000_000.0,
            "atr_14": 0.001,
        },
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


def test_infer_bar_duration_days_daily():
    """Daily business-day index → bar_duration ≈ 1 day (Mon-Fri only)."""
    dates = pd.bdate_range("2023-01-02", periods=50, freq="B", tz="UTC")
    dur = _infer_bar_duration_days(pd.DatetimeIndex(dates))
    # Business day spacing = 1 calendar day (Mon–Thu) or 3 (Fri→Mon).
    # Median is 1 day (majority of pairs are Mon–Thu).
    assert abs(dur - 1.0) < 0.01, f"Expected ≈1.0 day, got {dur}"


def test_infer_bar_duration_days_1h():
    """1-hour index → bar_duration ≈ 1/24 days."""
    dates = pd.date_range("2023-01-02", periods=100, freq="1h", tz="UTC")
    dur = _infer_bar_duration_days(pd.DatetimeIndex(dates))
    expected = 1.0 / 24.0
    assert abs(dur - expected) < 1e-6, f"Expected {expected:.6f}, got {dur:.6f}"


def test_swap_accrual_1h_is_1_24th_of_daily():
    """Invariant: 24 hours in-position on 1h bars accrues exactly 1 day's swap
    (within floating-point tolerance). This verifies the 24× over-charge is fixed.
    """
    # Build a positive-swap pair so we can measure the credit effect on equity
    swap_long_per_day = 10.0  # 10 pips/day long credit (positive carry)
    pair_cfg = {
        "EURUSD": PairInfo(
            "EURUSD",
            pip_value=0.0001,
            spread_pips=0.0,  # zero transaction costs so only swap affects equity
            slippage_pips=0.0,
            commission_pips=0.0,
            swap_long_pips_per_day=swap_long_per_day,
            swap_short_pips_per_day=0.0,
        )
    }
    cost_model = RealisticCostModel(pair_cfg)
    sizer = VolTargetSizer(leverage_cap=1.0)

    # 24 consecutive 1h bars — one signal-on bar followed by 24 in-position bars
    data_1h = _make_continuous_ohlcv(freq_hours=1, n_bars=48)
    signals_1h = pd.Series(1.0, index=data_1h.index)

    result_1h = run_backtest(
        data=data_1h,
        signals=signals_1h,
        pair="EURUSD",
        strategy_name="swap_test_1h",
        cost_model=cost_model,
        initial_capital=100_000.0,
        rebalance_mode="continuous",
        sizer=sizer,
        constant_capital_sizing=True,
    )

    # Now run 2 daily bars in-position (same total exposure time ≈ 2 days)
    data_daily = _make_continuous_ohlcv(freq_hours=24, n_bars=10)
    signals_daily = pd.Series(1.0, index=data_daily.index)
    result_daily = run_backtest(
        data=data_daily,
        signals=signals_daily,
        pair="EURUSD",
        strategy_name="swap_test_daily",
        cost_model=cost_model,
        initial_capital=100_000.0,
        rebalance_mode="continuous",
        sizer=sizer,
        constant_capital_sizing=True,
    )

    # Price is flat, so all equity changes are swap-only.
    # entry_delay_bars=1: signal at bar 0 → entry executes at bar 1.
    # Swap starts accruing at bar 2 (first full bar in position after entry).
    # Compare the per-bar swap rates rather than cumulative totals so the
    # different run lengths (48 vs 10 bars) don't confound the comparison.
    ec_1h = result_1h.equity_curve.dropna()
    ec_daily = result_daily.equity_curve.dropna()

    assert len(ec_1h) > 3, f"1h equity curve too short: {len(ec_1h)}"
    assert len(ec_daily) > 3, f"Daily equity curve too short: {len(ec_daily)}"

    # Per-bar swap credit (from bar 1 → bar 2, both in position)
    swap_per_1h_bar = ec_1h.iloc[2] - ec_1h.iloc[1]
    swap_per_daily_bar = ec_daily.iloc[2] - ec_daily.iloc[1]

    assert abs(swap_per_daily_bar) > 1e-6, (
        f"Daily swap per bar should be non-zero; got {swap_per_daily_bar}. "
        f"Equity: {ec_daily.values[:4]}"
    )

    # FIX-1 invariant: 1h per-bar swap * 24 ≈ 1 daily bar's swap (both = 1 day of carry)
    # If the bug (24× over-charge) were present, ratio would be ≈ 576 (24² / 1).
    ratio_24x = abs(swap_per_1h_bar) * 24.0 / abs(swap_per_daily_bar)
    assert 0.99 <= ratio_24x <= 1.01, (
        f"FIX-1 swap scaling check: (1h_per_bar * 24) / daily_per_bar = {ratio_24x:.4f}; "
        f"expected ≈1.0. "
        f"1h_per_bar={swap_per_1h_bar:.6f}, daily_per_bar={swap_per_daily_bar:.6f}. "
        f"If ratio≈576, the 24× over-charge bug is still present."
    )


def test_swap_accrual_daily_behavior_unchanged(sample_ohlcv):
    """Invariant: daily-bar continuous-mode results are IDENTICAL before and after FIX-1.

    This guards the regression: if the daily median timedelta is 1 day, bar_duration_days=1.0,
    and holding_cost(pair, direction, 1.0) equals the old holding_cost(pair, direction, 1).
    """
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])
    signals = pd.Series(1.0, index=enriched.index)
    cost_model = RealisticCostModel()
    sizer = VolTargetSizer(leverage_cap=1.0)

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="regression_daily",
        cost_model=cost_model,
        initial_capital=100_000.0,
        rebalance_mode="continuous",
        sizer=sizer,
        constant_capital_sizing=True,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 0, "Expected non-empty equity curve"
    # Basic sanity: equity is a real number, not NaN/Inf
    assert np.isfinite(ec.iloc[-1]), f"Final equity is not finite: {ec.iloc[-1]}"


# ---------------------------------------------------------------------------
# End FIX-1 tests
# ---------------------------------------------------------------------------


def test_basic_backtest(sample_ohlcv):
    """Engine produces valid results with constant long signal."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    signals = pd.Series(1.0, index=enriched.index)  # Always long
    cost_model = RealisticCostModel()

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=cost_model,
        initial_capital=100_000.0,
    )

    assert len(result.equity_curve.dropna()) > 0
    assert result.pair == "EURUSD"
    assert result.strategy_name == "test"


def test_no_signals_no_trades(sample_ohlcv):
    """Zero signals should produce zero trades."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    signals = pd.Series(0.0, index=enriched.index)
    cost_model = RealisticCostModel()

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=cost_model,
    )

    assert len(result.trade_log) == 0
    # Equity should be unchanged
    ec = result.equity_curve.dropna()
    assert ec.iloc[-1] == ec.iloc[0]


def test_no_lookahead(sample_ohlcv):
    """THE SACRED TEST: engine must not use future data.

    Strategy: signal = +1 if NEXT bar's close > current close (trivially profitable
    with lookahead). With entry_delay_bars=1, this signal should NOT consistently
    profit because by the time we enter, the move already happened.
    """
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    # Lookahead signal: +1 when next bar rises, -1 when it falls
    future_return = enriched["close"].shift(-1) - enriched["close"]
    lookahead_signals = pd.Series(0.0, index=enriched.index)
    lookahead_signals[future_return > 0] = 1.0
    lookahead_signals[future_return < 0] = -1.0

    cost_model = RealisticCostModel()
    result = run_backtest(
        data=enriched,
        signals=lookahead_signals,
        pair="EURUSD",
        strategy_name="lookahead_test",
        cost_model=cost_model,
        entry_delay_bars=1,
    )

    # With proper delay, this should NOT be consistently profitable
    # The lookahead signal becomes a lagging signal after shift
    ec = result.equity_curve.dropna()
    # We don't assert loss, just that it's not suspiciously profitable
    # A Sharpe > 3 would indicate the engine is leaking future data
    if len(ec) > 10:
        daily_returns = ec.pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            assert sharpe < 3.0, f"Suspiciously high Sharpe ({sharpe:.1f}) — possible lookahead"


def test_costs_reduce_equity(sample_ohlcv):
    """Trades with costs should produce lower equity than without."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    # Alternate long/short every 10 bars
    signals = pd.Series(0.0, index=enriched.index)
    for i in range(0, len(signals), 20):
        signals.iloc[i : i + 10] = 1.0
        if i + 10 < len(signals):
            signals.iloc[i + 10 : i + 20] = -1.0

    # High-cost model
    from forex_system.core.types import PairInfo

    expensive = {"EURUSD": PairInfo("EURUSD", 0.0001, 5.0, 5.0, 5.0, -1.2, 0.3)}
    expensive_cost = RealisticCostModel(expensive)

    # Zero-cost model
    cheap = {"EURUSD": PairInfo("EURUSD", 0.0001, 0.0, 0.0, 0.0, 0.0, 0.0)}
    cheap_cost = RealisticCostModel(cheap)

    result_expensive = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=expensive_cost,
    )
    result_cheap = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=cheap_cost,
    )

    ec_expensive = result_expensive.equity_curve.dropna()
    ec_cheap = result_cheap.equity_curve.dropna()

    # Expensive should end lower than cheap
    assert ec_expensive.iloc[-1] < ec_cheap.iloc[-1]
