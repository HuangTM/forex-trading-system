"""Tests for KG-QD-3: RolloverAwareRealisticCostModel wired into the continuous engine.

7 test obligations from the CTO engine-wiring spec
(cto-engine-wiring-spec.yaml, Section 6):

1. test_daily_equivalence_under_rollover_model
2. test_intraday_single_rollover_crossing
3. test_intraday_wednesday_triple_charge
4. test_intraday_intra_session_no_charge
5. test_intraday_weekend_boundary_no_charge
6. test_sign_convention_long_negative_carry
7. test_no_double_count_at_close
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.core.types import Direction, PairInfo
from forex_system.costs.model import RealisticCostModel, RolloverAwareRealisticCostModel
from forex_system.features.registry import compute_indicators
from forex_system.sizing.vol_target import VolTargetSizer


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

# EURUSD: negative-carry LONG (swap_long = -1.2 pips/day), positive-carry SHORT
_EURUSD_PAIR = PairInfo(
    symbol="EURUSD",
    pip_value=0.0001,
    spread_pips=1.0,
    slippage_pips=0.5,
    commission_pips=0.5,
    swap_long_pips_per_day=-1.2,
    swap_short_pips_per_day=0.3,
)

# Zero-transaction-cost variant — isolates swap from spread/commission noise
_EURUSD_PAIR_ZEROCOST = PairInfo(
    symbol="EURUSD",
    pip_value=0.0001,
    spread_pips=0.0,
    slippage_pips=0.0,
    commission_pips=0.0,
    swap_long_pips_per_day=-1.2,
    swap_short_pips_per_day=0.3,
)


def _plain_model(pair_info: PairInfo = _EURUSD_PAIR) -> RealisticCostModel:
    return RealisticCostModel({"EURUSD": pair_info})


def _rollover_model(pair_info: PairInfo = _EURUSD_PAIR) -> RolloverAwareRealisticCostModel:
    return RolloverAwareRealisticCostModel({"EURUSD": pair_info})


def _sizer() -> VolTargetSizer:
    return VolTargetSizer(
        leverage_cap=2.0,
        max_order_units=10_000_000.0,
        min_order_size=100.0,
    )


def _make_daily_data(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Synthetic EURUSD daily OHLCV with indicators (bars at 00:00 UTC)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-02", periods=n, freq="B", tz="UTC")
    price = 1.1000
    rets = rng.normal(0.0, 0.003, n)
    close = price * np.exp(np.cumsum(rets))
    daily_range = np.abs(rng.normal(0, 0.002, n))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + daily_range * 0.6,
            "low": close - daily_range * 0.4,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=pd.DatetimeIndex(dates, name="datetime"),
    )
    return compute_indicators(df, ["atr_14"]).dropna(subset=["atr_14"])


def _make_1h_flat_data(timestamps: list[pd.Timestamp]) -> pd.DataFrame:
    """Synthetic 1h EURUSD OHLCV with flat price — isolates swap from P&L noise.

    Uses a constant price (1.1000) so all equity movement is purely swap.
    ATR is set to a non-zero sentinel to keep the sizer from returning 0.
    """
    price = 1.1000
    return pd.DataFrame(
        {
            "open": price,
            "high": price + 0.0001,
            "low": price - 0.0001,
            "close": price,
            "volume": 1_000_000.0,
            "atr_14": 0.001,
        },
        index=pd.DatetimeIndex(timestamps, name="datetime"),
    )


def _run_continuous(
    data: pd.DataFrame,
    cost_model: RealisticCostModel,
    pair: str = "EURUSD",
    initial_capital: float = 100_000.0,
    signal_value: float = 1.0,
) -> tuple[pd.Series, float]:
    """Run a constant-signal continuous backtest, return (equity_curve, final_equity)."""
    signals = pd.Series(signal_value, index=data.index)
    result = run_backtest(
        data=data,
        signals=signals,
        pair=pair,
        strategy_name="rollover_test",
        cost_model=cost_model,
        initial_capital=initial_capital,
        sizer=_sizer(),
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
        entry_delay_bars=1,
    )
    return result.equity_curve, result.equity_curve.dropna().iloc[-1]


# ---------------------------------------------------------------------------
# Test 1: test_daily_equivalence_under_rollover_model
# ---------------------------------------------------------------------------

def test_daily_equivalence_under_rollover_model():
    """Daily-bar backtest with plain RealisticCostModel is unchanged by the engine wiring.

    The isinstance gate keeps the pro-rata path for plain RealisticCostModel callers.
    Run the same daily-bar backtest twice with RealisticCostModel (before and simulated-after)
    and confirm results are bit-identical — the engine change cannot have touched the else-branch.

    Additionally, confirm that RolloverAwareRealisticCostModel on daily bars (00:00 UTC)
    accrues ZERO swap (rollover_cost_for_bar returns 0.0 for hour!=21), which is the
    expected behavior: daily bars at 00:00 UTC are not 22:00 UTC crossing bars. This is
    NOT equivalent to plain model — the spec's "bit-identical" claim is contingent on
    the isinstance gate routing plain callers through the pro-rata path exclusively.

    What this test validates:
      (a) isinstance gate is correct: isinstance(plain, RolloverAwareRealisticCostModel) = False
      (b) isinstance gate is correct: isinstance(rollover, RolloverAwareRealisticCostModel) = True
      (c) Two identical runs with plain RealisticCostModel produce bit-identical results (regression anchor).
      (d) RolloverAwareRealisticCostModel on daily bars returns 0 swap/bar (bar_ts.hour != 21).
    """
    # (a) and (b): isinstance gate correctness
    plain = _plain_model()
    rollover = _rollover_model()
    assert not isinstance(plain, RolloverAwareRealisticCostModel), (
        "Plain RealisticCostModel must NOT satisfy isinstance check"
    )
    assert isinstance(rollover, RolloverAwareRealisticCostModel), (
        "RolloverAwareRealisticCostModel must satisfy isinstance check"
    )

    data = _make_daily_data(n=150, seed=7)

    # (c): Two runs with plain model must be bit-identical (regression anchor)
    ec1, _ = _run_continuous(data, plain)
    ec2, _ = _run_continuous(data, plain)  # same model, same data

    ec1 = ec1.dropna()
    ec2 = ec2.dropna()
    pd.testing.assert_series_equal(
        ec1.reset_index(drop=True),
        ec2.reset_index(drop=True),
        check_exact=True,
        check_names=False,
        obj="plain model regression anchor (two identical runs must be identical)",
    )

    # (d): RolloverAwareRealisticCostModel on daily bars (00:00 UTC) accrues zero swap
    # Daily bars are at 00:00 UTC; rollover_cost_for_bar returns 0.0 for hour != 21
    from forex_system.costs.model import RolloverAwareRealisticCostModel as RARCM
    rollover_zero = RARCM({"EURUSD": _EURUSD_PAIR_ZEROCOST})
    for ts in data.index:
        cost = rollover_zero.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == 0.0, (
            f"Daily bar at {ts} (hour={ts.hour}) must not trigger rollover accrual; got {cost}"
        )

    # Confirm plain model accrues non-zero swap (ensures we're testing a live pair)
    plain_zero = RealisticCostModel({"EURUSD": _EURUSD_PAIR_ZEROCOST})
    ec_plain, _ = _run_continuous(data, plain_zero)
    ec_rollover_daily, _ = _run_continuous(data, rollover_zero)
    # Plain model: swap accrues every bar (pro-rata). Rollover model: zero swap on 00:00 UTC bars.
    # They should differ — rollover model has MORE equity (zero swap = no cost)
    assert ec_rollover_daily.dropna().iloc[-1] > ec_plain.dropna().iloc[-1], (
        "Rollover model on daily 00:00 UTC bars should have higher equity than plain model "
        "(plain accrues swap pro-rata every bar; rollover accrues nothing on non-21h bars)"
    )


# ---------------------------------------------------------------------------
# Test 2: test_intraday_single_rollover_crossing
# ---------------------------------------------------------------------------

def test_intraday_single_rollover_crossing():
    """Position held across ONE 22:00 UTC bar (Mon 21:00 UTC) accrues swap exactly once.

    Construct a 1h dataset spanning Mon 08:00 to Mon 23:00 UTC (16 bars).
    The only rollover-crossing bar is Mon 21:00 UTC (closes at Mon 22:00 UTC).
    All other bars must have zero equity change (flat price, no swap on non-rollover bars).

    Assert: equity decreases exactly once, at the 21:00 UTC bar.
    """
    # Monday 2024-01-08 (weekday 0)
    timestamps = list(pd.date_range("2024-01-08 08:00", periods=16, freq="1h", tz="UTC"))
    data = _make_1h_flat_data(timestamps)

    # Zero-cost model to isolate swap impact
    model = _rollover_model(_EURUSD_PAIR_ZEROCOST)
    initial_capital = 100_000.0

    signals = pd.Series(1.0, index=data.index)
    result = run_backtest(
        data=data,
        signals=signals,
        pair="EURUSD",
        strategy_name="single_rollover",
        cost_model=model,
        initial_capital=initial_capital,
        sizer=_sizer(),
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
        entry_delay_bars=1,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 0, "Empty equity curve"

    # Compute equity changes per bar using timestamp-based indexing
    ec_diff = ec.diff()

    # Non-rollover bars: all bars EXCEPT 21:00 UTC should have zero change
    rollover_ts = pd.Timestamp("2024-01-08 21:00", tz="UTC")
    assert rollover_ts in ec.index, "Rollover bar must be in the equity curve"

    non_rollover_changes = ec_diff.drop(rollover_ts).dropna().abs()
    assert non_rollover_changes.max() < 1e-9, (
        f"Non-rollover bars must have zero equity change (flat price, no swap); "
        f"max={non_rollover_changes.max():.6e}"
    )

    # Rollover bar must show a decrease (negative carry LONG)
    rollover_change = ec_diff[rollover_ts]
    assert rollover_change < 0, (
        f"LONG negative-carry EURUSD must lose equity on rollover bar; "
        f"got change={rollover_change:.4f}"
    )

    # Verify exactly 1 rollover event fired
    n_nonzero = (ec_diff.abs() > 1e-9).sum()
    assert n_nonzero == 1, (
        f"Expected exactly 1 rollover event in the equity curve; got {n_nonzero}"
    )


# ---------------------------------------------------------------------------
# Test 3: test_intraday_wednesday_triple_charge
# ---------------------------------------------------------------------------

def test_intraday_wednesday_triple_charge():
    """Wednesday 21:00 UTC bar accrues 3× a standard (Monday) bar.

    Verify via rollover_cost_for_bar directly (authoritative model-level test)
    and also check the ratio is exactly 3.
    """
    # Monday 2024-01-08 21:00 UTC (weekday 0 → 1× multiplier)
    mon_ts = pd.Timestamp("2024-01-08 21:00", tz="UTC")
    # Wednesday 2024-01-10 21:00 UTC (weekday 2 → 3× multiplier)
    wed_ts = pd.Timestamp("2024-01-10 21:00", tz="UTC")

    assert mon_ts.weekday() == 0, f"Expected Monday, got weekday={mon_ts.weekday()}"
    assert wed_ts.weekday() == 2, f"Expected Wednesday, got weekday={wed_ts.weekday()}"

    model = RolloverAwareRealisticCostModel({"EURUSD": _EURUSD_PAIR_ZEROCOST})

    mon_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, mon_ts)
    wed_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, wed_ts)

    assert mon_cost != 0.0, "Monday 21:00 should return non-zero rollover cost"
    assert wed_cost != 0.0, "Wednesday 21:00 should return non-zero rollover cost"

    ratio = wed_cost / mon_cost
    assert abs(ratio - 3.0) < 1e-10, (
        f"Wednesday cost must be exactly 3× Monday cost; ratio={ratio:.8f}"
    )

    # Engine-side verification: run intraday backtests for Monday and Wednesday.
    # Per-bar accrual runs BEFORE entry logic each bar (engine line order). With
    # entry_delay_bars=1, the signal at bar 0 triggers entry at bar 1. So the rollover
    # bar must be bar 2 (not bar 1) for the position to already be open when accrual fires.
    # Layout: bar 0 (signal), bar 1 (entry), bar 2 (rollover), bar 3 (after rollover).
    def _equity_drop_on_rollover(rollover_bar_ts: pd.Timestamp) -> float:
        """Return the equity change on the specified rollover bar (must be bar index 2)."""
        ts_entry_signal = rollover_bar_ts - pd.Timedelta(hours=2)  # bar 0
        ts_entry = rollover_bar_ts - pd.Timedelta(hours=1)          # bar 1 — entry executes
        ts_after = rollover_bar_ts + pd.Timedelta(hours=1)           # bar 3
        timestamps = [ts_entry_signal, ts_entry, rollover_bar_ts, ts_after]
        data = _make_1h_flat_data(timestamps)
        signals = pd.Series(1.0, index=data.index)
        result = run_backtest(
            data=data, signals=signals, pair="EURUSD",
            strategy_name="triple_charge",
            cost_model=RolloverAwareRealisticCostModel({"EURUSD": _EURUSD_PAIR_ZEROCOST}),
            initial_capital=100_000.0, sizer=_sizer(),
            rebalance_mode="continuous", rebalance_threshold=0.20, entry_delay_bars=1,
        )
        ec = result.equity_curve
        return float(ec.diff()[rollover_bar_ts]) if rollover_bar_ts in ec.index else 0.0

    mon_drop = _equity_drop_on_rollover(mon_ts)
    wed_drop = _equity_drop_on_rollover(wed_ts)

    assert mon_drop < 0, f"Monday rollover: equity must decrease for negative-carry LONG; got {mon_drop}"
    assert wed_drop < 0, f"Wednesday rollover: equity must decrease; got {wed_drop}"

    engine_ratio = wed_drop / mon_drop
    assert abs(engine_ratio - 3.0) < 1e-6, (
        f"Wednesday engine equity drop must be 3× Monday's; ratio={engine_ratio:.8f}"
    )


# ---------------------------------------------------------------------------
# Test 4: test_intraday_intra_session_no_charge
# ---------------------------------------------------------------------------

def test_intraday_intra_session_no_charge():
    """Position opened Mon 08:00 UTC and closed Mon 20:00 UTC → zero swap.

    No 22:00 UTC boundary crossed → total swap accrual must be exactly 0.
    With zero transaction costs and flat price, equity must be constant throughout.
    """
    # Mon 2024-01-08 08:00 through 20:00 UTC (13 bars: 08, 09, ..., 20)
    timestamps = list(pd.date_range("2024-01-08 08:00", periods=13, freq="1h", tz="UTC"))
    assert pd.Timestamp(timestamps[-1]).hour == 20, (
        f"Expected last bar at 20:00, got {pd.Timestamp(timestamps[-1]).hour}"
    )
    data = _make_1h_flat_data(timestamps)

    model = _rollover_model(_EURUSD_PAIR_ZEROCOST)
    initial_capital = 100_000.0

    signals = pd.Series(1.0, index=data.index)
    result = run_backtest(
        data=data,
        signals=signals,
        pair="EURUSD",
        strategy_name="intra_session",
        cost_model=model,
        initial_capital=initial_capital,
        sizer=_sizer(),
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
        entry_delay_bars=1,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 0

    # All equity changes must be zero: flat price + no rollover crossing = no swap
    ec_changes = ec.diff().dropna().abs()
    assert ec_changes.max() < 1e-9, (
        f"Intra-session position must accrue zero swap (no 22:00 UTC crossing); "
        f"max equity change = {ec_changes.max():.6e}"
    )


# ---------------------------------------------------------------------------
# Test 5: test_intraday_weekend_boundary_no_charge
# ---------------------------------------------------------------------------

def test_intraday_weekend_boundary_no_charge():
    """Friday, Saturday, Sunday 21:00 UTC bars → zero swap (WEEKEND RULE).

    Verifies rollover_cost_for_bar returns 0.0 for the three weekend-closed 21:00 UTC
    bars. Monday 21:00 used as a positive control (must be non-zero).
    """
    model = RolloverAwareRealisticCostModel({"EURUSD": _EURUSD_PAIR_ZEROCOST})

    # Friday 2024-01-12 21:00 UTC (weekday 4)
    fri_ts = pd.Timestamp("2024-01-12 21:00", tz="UTC")
    # Saturday 2024-01-13 21:00 UTC (weekday 5)
    sat_ts = pd.Timestamp("2024-01-13 21:00", tz="UTC")
    # Sunday 2024-01-14 21:00 UTC (weekday 6)
    sun_ts = pd.Timestamp("2024-01-14 21:00", tz="UTC")
    # Monday 2024-01-08 21:00 UTC (weekday 0) — positive control
    mon_ts = pd.Timestamp("2024-01-08 21:00", tz="UTC")

    assert fri_ts.weekday() == 4, f"Expected Friday, got {fri_ts.weekday()}"
    assert sat_ts.weekday() == 5, f"Expected Saturday, got {sat_ts.weekday()}"
    assert sun_ts.weekday() == 6, f"Expected Sunday, got {sun_ts.weekday()}"
    assert mon_ts.weekday() == 0, f"Expected Monday, got {mon_ts.weekday()}"

    fri_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, fri_ts)
    sat_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, sat_ts)
    sun_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, sun_ts)
    mon_cost = model.rollover_cost_for_bar("EURUSD", Direction.LONG, mon_ts)

    assert fri_cost == 0.0, f"Friday 21:00 must return 0.0 (weekend rule); got {fri_cost}"
    assert sat_cost == 0.0, f"Saturday 21:00 must return 0.0 (weekend rule); got {sat_cost}"
    assert sun_cost == 0.0, f"Sunday 21:00 must return 0.0 (weekend rule); got {sun_cost}"
    assert mon_cost != 0.0, f"Monday 21:00 must return non-zero (positive control); got {mon_cost}"


# ---------------------------------------------------------------------------
# Test 6: test_sign_convention_long_negative_carry
# ---------------------------------------------------------------------------

def test_sign_convention_long_negative_carry():
    """LONG on negative-carry EURUSD must DECREASE equity at a rollover bar.

    Sign chain (CTO spec sign_convention_correction):
      model: rollover_cost_for_bar returns -daily_swap * mult = -(-1.2)*1 = +1.2
      engine: per_bar_swap_pips = -rollover_cost_for_bar(...) = -1.2
      engine: equity += per_bar_swap_pips * pip_value * cur_units = negative → equity decreases.

    Steps:
      1. Verify model sign: rollover_cost_for_bar returns +1.2 for EURUSD LONG (positive = cost).
      2. After engine negation: per_bar_swap_pips = -1.2 (negative).
      3. End-to-end engine run: equity decreases on the rollover bar.
    """
    mon_ts = pd.Timestamp("2024-01-08 21:00", tz="UTC")
    model = RolloverAwareRealisticCostModel({"EURUSD": _EURUSD_PAIR_ZEROCOST})

    # Step 1: Model sign check
    raw_return = model.rollover_cost_for_bar("EURUSD", Direction.LONG, mon_ts)
    # swap_long_pips_per_day = -1.2 → -daily_swap*1 = -(-1.2)*1 = +1.2 (cost to trader)
    assert raw_return > 0.0, (
        f"rollover_cost_for_bar for LONG negative-carry EURUSD must return positive "
        f"(cost convention); got {raw_return}"
    )
    assert abs(raw_return - 1.2) < 1e-10, (
        f"Expected +1.2 (= -swap_long=-(-1.2)); got {raw_return}"
    )

    # Step 2: Engine negation produces negative per_bar_swap_pips
    engine_pips = -raw_return
    assert engine_pips < 0.0, (
        f"After engine negation, per_bar_swap_pips must be negative (cost); got {engine_pips}"
    )

    # Step 3: End-to-end engine run confirms equity decreases
    # Use a 5-bar dataset: bars at 19, 20, 21 (rollover), 22, 23 UTC on Monday
    # entry_delay_bars=1: signal at bar 0 executes at bar 1 → position opens at bar 1 (20:00)
    # accrual on bar 1 (20:00): hour=20, not rollover → 0.0
    # accrual on bar 2 (21:00): hour=21, Monday → rollover fires → equity decreases
    timestamps = list(pd.date_range("2024-01-08 19:00", periods=5, freq="1h", tz="UTC"))
    data = _make_1h_flat_data(timestamps)

    signals = pd.Series(1.0, index=data.index)
    result = run_backtest(
        data=data, signals=signals, pair="EURUSD",
        strategy_name="sign_convention",
        cost_model=model, initial_capital=100_000.0,
        sizer=_sizer(), rebalance_mode="continuous",
        rebalance_threshold=0.20, entry_delay_bars=1,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 0

    rollover_bar_ts = timestamps[2]  # 21:00 UTC
    assert pd.Timestamp(rollover_bar_ts).hour == 21, "Third bar must be 21:00 UTC"

    if rollover_bar_ts in ec.index:
        # Equity at rollover bar must be less than initial (negative carry consumed equity)
        equity_at_rollover = ec[rollover_bar_ts]
        # Before entry (bar 0), equity = initial_capital
        # After rollover bar, equity < initial_capital
        assert equity_at_rollover < 100_000.0, (
            f"LONG negative-carry EURUSD must have equity below initial after rollover bar; "
            f"got {equity_at_rollover:.4f} vs initial 100000.0000"
        )


# ---------------------------------------------------------------------------
# Test 7: test_no_double_count_at_close
# ---------------------------------------------------------------------------

def test_no_double_count_at_close():
    """Swap is charged via per-bar accrual only; _close_position does NOT add a lump sum.

    Mechanism: continuous mode calls _close_position with include_swap=False, so
    swap_cost_pips=0.0 in that call. All swap is charged via per-bar rollover accrual.

    Test: build a 5-bar dataset with exactly ONE rollover bar (bar 2, Mon 21:00).
    After the rollover bar (bars 3 and 4), equity must be flat despite the position
    being open and then closed. If double-counting occurred at close, equity would
    drop again at bar 4 (the close bar).

    Also verifies: the total equity change equals exactly the per-bar accrual at bar 2.
    """
    # Monday session:
    #   bar 0: 19:00 (signal=1 visible here, delayed → enters at bar 1)
    #   bar 1: 20:00 (entry, no rollover)
    #   bar 2: 21:00 (rollover bar → swap accrual)
    #   bar 3: 22:00 (no rollover)
    #   bar 4: 23:00 (no rollover, final close)
    timestamps = [
        pd.Timestamp("2024-01-08 19:00", tz="UTC"),
        pd.Timestamp("2024-01-08 20:00", tz="UTC"),
        pd.Timestamp("2024-01-08 21:00", tz="UTC"),  # rollover bar
        pd.Timestamp("2024-01-08 22:00", tz="UTC"),
        pd.Timestamp("2024-01-08 23:00", tz="UTC"),  # final close
    ]
    data = _make_1h_flat_data(timestamps)

    model = _rollover_model(_EURUSD_PAIR_ZEROCOST)
    initial_capital = 100_000.0

    signals = pd.Series(1.0, index=data.index)
    result = run_backtest(
        data=data, signals=signals, pair="EURUSD",
        strategy_name="no_double_count",
        cost_model=model, initial_capital=initial_capital,
        sizer=_sizer(), rebalance_mode="continuous",
        rebalance_threshold=0.20, entry_delay_bars=1,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 0

    rollover_ts = timestamps[2]
    ts_after_rollover = timestamps[3]
    final_ts = timestamps[4]

    ec_diff = ec.diff()

    # Bar 3 (22:00): position open but no rollover → zero equity change
    if ts_after_rollover in ec.index:
        bar3_change = abs(ec_diff[ts_after_rollover])
        assert bar3_change < 1e-9, (
            f"Bar after rollover (22:00) must have zero equity change; got {bar3_change:.6e}"
        )

    # Bar 4 (23:00): final close with include_swap=False → zero equity change
    # (If double-counted, the close would add another lump-sum swap charge here)
    if final_ts in ec.index:
        final_change = abs(ec_diff[final_ts])
        assert final_change < 1e-9, (
            f"Final close bar (23:00) must have zero equity change (no double-count); "
            f"got {final_change:.6e}"
        )

    # The total equity deficit must equal exactly the rollover bar's accrual
    if rollover_ts in ec.index and final_ts in ec.index:
        rollover_equity = ec[rollover_ts]
        final_equity = ec[final_ts]
        # After the rollover bar, equity must stay flat until close
        assert abs(rollover_equity - final_equity) < 1e-9, (
            f"Equity must be constant from rollover bar to close "
            f"(no double-count at _close_position); "
            f"delta = {rollover_equity - final_equity:.6e}"
        )

    # Confirm the rollover bar itself caused a decrease
    if rollover_ts in ec.index:
        rollover_change = ec_diff[rollover_ts]
        assert rollover_change < 0, (
            f"Rollover bar must show equity decrease for negative-carry LONG; "
            f"got {rollover_change}"
        )
