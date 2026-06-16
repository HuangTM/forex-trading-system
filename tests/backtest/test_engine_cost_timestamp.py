"""P0 #1 Part B: the engine threads each bar's timestamp into the cost model,
so a time-varying (hour-of-day) spread is actually applied per-bar."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.core.interfaces import CostModel
from forex_system.core.types import Direction, PairInfo
from forex_system.costs.hourly_spread import HourlySpreadCostModel
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators

_PAIR_CFG = {
    "EURUSD": PairInfo(
        symbol="EURUSD", pip_value=0.0001, spread_pips=2.0, slippage_pips=0.5,
        commission_pips=0.5, swap_long_pips_per_day=-1.2, swap_short_pips_per_day=0.3,
    )
}


class _RecordingCostModel(CostModel):
    """Records the timestamps the engine passes to entry/exit cost calls."""

    def __init__(self):
        self.entry_ts: list = []
        self.exit_ts: list = []

    def entry_cost(self, pair, size, timestamp=None):
        self.entry_ts.append(timestamp)
        return 1.0

    def exit_cost(self, pair, size, timestamp=None):
        self.exit_ts.append(timestamp)
        return 1.0

    def holding_cost(self, pair, direction: Direction, days):
        return 0.0


def _hourly_data(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2021-01-04T00:00", periods=n, freq="h", tz="UTC")
    rng = np.random.default_rng(0)
    close = 1.20 + np.cumsum(rng.normal(0, 0.0005, n))
    df = pd.DataFrame(
        {"open": close, "high": close + 0.0008, "low": close - 0.0008,
         "close": close, "volume": 1000.0},
        index=idx,
    )
    return compute_indicators(df, ["atr_14"]).dropna(subset=["atr_14"])


def _entry_then_exit_signals(index) -> pd.Series:
    sig = pd.Series(1.0, index=index)
    sig.iloc[len(index) // 2:] = -1.0  # flip → forces a close then re-entry
    return sig


def test_engine_passes_bar_timestamp_to_cost_model():
    data = _hourly_data()
    rec = _RecordingCostModel()
    run_backtest(
        data=data, signals=_entry_then_exit_signals(data.index),
        pair="EURUSD", strategy_name="t", cost_model=rec,
    )
    assert rec.entry_ts, "expected at least one entry"
    assert rec.exit_ts, "expected at least one exit"
    # every timestamp the engine handed the cost model is a real bar, never None
    assert all(ts is not None for ts in rec.entry_ts + rec.exit_ts)
    assert all(ts in data.index for ts in rec.entry_ts + rec.exit_ts)


def test_realistic_cost_model_unchanged_through_engine():
    """Equivalence guard: the engine now passes a timestamp, but RealisticCostModel
    ignores it, so a flat-spread run is identical to a HourlySpreadCostModel run
    whose curve is uniform at the same spread."""
    data = _hourly_data()
    signals = _entry_then_exit_signals(data.index)
    flat_curve = {h: 2.0 for h in range(24)}  # == PairInfo.spread_pips
    r_fixed = run_backtest(data=data, signals=signals, pair="EURUSD", strategy_name="t",
                           cost_model=RealisticCostModel(_PAIR_CFG))
    r_curve = run_backtest(data=data, signals=signals, pair="EURUSD", strategy_name="t",
                           cost_model=HourlySpreadCostModel(_PAIR_CFG, flat_curve))
    assert r_fixed.equity_curve.equals(r_curve.equity_curve)


def test_hourly_curve_changes_realized_cost_in_engine():
    """A spiked hour-of-day curve must cost more through the engine than a cheap one."""
    data = _hourly_data()
    signals = _entry_then_exit_signals(data.index)
    cheap = run_backtest(data=data, signals=signals, pair="EURUSD", strategy_name="t",
                         cost_model=HourlySpreadCostModel(_PAIR_CFG, {h: 1.0 for h in range(24)}))
    pricey = run_backtest(data=data, signals=signals, pair="EURUSD", strategy_name="t",
                          cost_model=HourlySpreadCostModel(_PAIR_CFG, {h: 12.0 for h in range(24)}))
    cheap_cost = sum(t.cost_pips for t in cheap.trade_log)
    pricey_cost = sum(t.cost_pips for t in pricey.trade_log)
    assert pricey_cost > cheap_cost
