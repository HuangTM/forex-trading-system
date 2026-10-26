"""Discrete-mode swap accrual: carry is booked daily, not as a lump sum at exit.

Before this fix a multi-year discrete hold booked its whole swap on the closing
bar, so the equity curve jumped by years of carry in one day (the carry_fred
NZDJPY single trade added +16% on 2026-04-06). Per-trade totals must be
unchanged; only the timing of swap in the equity curve moves.
"""

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.core.types import PairInfo
from forex_system.costs.model import RateDifferentialSwapCostModel, RealisticCostModel

_SWAP_LONG = 2.0  # pips/day credit
_SWAP_SHORT = -3.0  # pips/day charge


def _pair_cfg(spread: float = 0.0) -> dict[str, PairInfo]:
    return {
        "EURUSD": PairInfo(
            symbol="EURUSD",
            pip_value=0.0001,
            spread_pips=spread,
            slippage_pips=0.0,
            commission_pips=0.0,
            swap_long_pips_per_day=_SWAP_LONG,
            swap_short_pips_per_day=_SWAP_SHORT,
        )
    }


def _flat_daily(n: int = 30, price: float = 1.1) -> pd.DataFrame:
    idx = pd.date_range("2023-01-02", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": price, "high": price, "low": price, "close": price,
         "volume": 0.0, "atr_14": 0.001},
        index=idx,
    )


def _run(data, signals, cost_model):
    return run_backtest(data, signals, "EURUSD", "t", cost_model,
                        initial_capital=100_000.0, entry_delay_bars=1)


def test_swap_accrues_daily_in_equity_curve():
    """Flat price, long from bar 1: equity rises by one day's swap per bar."""
    data = _flat_daily()
    signals = pd.Series(1.0, index=data.index)
    result = _run(data, signals, RealisticCostModel(_pair_cfg()))

    size = result.trade_log[0].size
    daily_credit = _SWAP_LONG * 0.0001 * size
    steps = result.equity_curve.diff().iloc[2:-1]  # bar 1 = entry; last bar = close
    np.testing.assert_allclose(steps.to_numpy(), daily_credit, rtol=1e-9)


def test_no_lump_sum_on_exit_bar():
    """Closing a long hold must not book the accumulated swap on the exit bar."""
    data = _flat_daily()
    signals = pd.Series(1.0, index=data.index)
    signals.iloc[20:] = 0.0  # exit executes at bar 21
    result = _run(data, signals, RealisticCostModel(_pair_cfg()))

    size = result.trade_log[0].size
    exit_step = result.equity_curve.diff().iloc[21]
    assert exit_step == pytest.approx(_SWAP_LONG * 0.0001 * size, rel=1e-9)


def test_trade_totals_match_exit_time_lump_sum():
    """Final equity and trade PnL equal the old lump-sum formula (timing-only fix)."""
    data = _flat_daily(n=40)
    rng = np.random.default_rng(3)
    data["close"] = 1.1 + np.cumsum(rng.normal(0, 0.002, len(data)))
    signals = pd.Series(1.0, index=data.index)
    signals.iloc[12:25] = -1.0
    signals.iloc[25:] = 0.0
    cfg = _pair_cfg(spread=1.0)
    model = RealisticCostModel(cfg)
    result = _run(data, signals, model)

    expected_equity = 100_000.0
    for t in result.trade_log:
        hold_days = (t.exit_time - t.entry_time).days
        swap = model.holding_cost("EURUSD", t.direction, hold_days)
        exit_cost = model.exit_cost("EURUSD", t.size)
        sign = 1.0 if t.direction.name == "LONG" else -1.0
        price_pips = (t.exit_price - t.entry_price) / 0.0001 * sign
        assert t.pnl_pips == pytest.approx(price_pips - exit_cost - swap, rel=1e-9)
        expected_equity += t.pnl_dollars - model.entry_cost("EURUSD", t.size) * 0.0001 * t.size
    assert result.equity_curve.iloc[-1] == pytest.approx(expected_equity, rel=1e-12)


def test_open_position_at_data_end_includes_full_swap():
    data = _flat_daily(n=15)
    signals = pd.Series(-1.0, index=data.index)
    model = RealisticCostModel(_pair_cfg())
    result = _run(data, signals, model)

    trade = result.trade_log[-1]
    hold_days = (trade.exit_time - trade.entry_time).days
    assert trade.cost_pips == pytest.approx(-_SWAP_SHORT * hold_days)
    assert result.equity_curve.iloc[-1] == pytest.approx(100_000.0 + trade.pnl_dollars)


# ---------------------------------------------------------------------------
# RateDifferentialSwapCostModel
# ---------------------------------------------------------------------------


def _rate_model(diff: pd.Series, price: pd.Series, markup: float = 0.005):
    return RateDifferentialSwapCostModel(
        _pair_cfg(),
        rate_differentials=pd.DataFrame({"EURUSD_diff": diff}),
        prices={"EURUSD": price},
        markup=markup,
    )


def test_rate_model_prices_swap_from_differential():
    idx = pd.date_range("2023-01-01", periods=3, freq="D")
    model = _rate_model(pd.Series(0.03, index=idx), pd.Series(1.2, index=idx))
    from forex_system.core.types import Direction

    ts = pd.Timestamp("2023-01-02", tz="UTC")
    long_daily = (0.03 - 0.005) * 1.2 / 365 / 0.0001
    short_daily = (-0.03 - 0.005) * 1.2 / 365 / 0.0001
    assert model.holding_cost("EURUSD", Direction.LONG, 2, timestamp=ts) == pytest.approx(
        -2 * long_daily
    )
    assert model.holding_cost("EURUSD", Direction.SHORT, 1, timestamp=ts) == pytest.approx(
        -short_daily
    )
    # Legacy call without a timestamp: static config swap.
    assert model.holding_cost("EURUSD", Direction.LONG, 1) == pytest.approx(-_SWAP_LONG)


def test_rate_model_raises_before_data_start():
    idx = pd.date_range("2023-01-10", periods=3, freq="D")
    model = _rate_model(pd.Series(0.01, index=idx), pd.Series(1.0, index=idx))
    from forex_system.core.types import Direction

    with pytest.raises(ValueError, match="no data at or before"):
        model.holding_cost("EURUSD", Direction.LONG, 1, timestamp=pd.Timestamp("2023-01-01"))


def test_engine_tracks_time_varying_differential():
    """A differential that flips sign mid-hold turns daily carry from credit to charge."""
    data = _flat_daily(n=30, price=1.0)
    naive = data.index.tz_localize(None)
    diff = pd.Series(np.where(np.arange(30) < 15, 0.05, -0.05), index=naive)
    model = _rate_model(diff, data["close"].set_axis(naive), markup=0.0)
    result = _run(data, pd.Series(1.0, index=data.index), model)

    size = result.trade_log[0].size
    steps = result.equity_curve.diff()
    per_day = 0.05 * 1.0 / 365 * size
    assert steps.iloc[5] == pytest.approx(per_day, rel=1e-9)
    assert steps.iloc[20] == pytest.approx(-per_day, rel=1e-9)
