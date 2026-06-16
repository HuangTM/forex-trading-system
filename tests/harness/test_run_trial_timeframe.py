"""P0 #1 final hop: run_trial selects the cost model by timeframe.

daily            -> fixed-spread RealisticCostModel (unchanged)
intraday + 4h spreads file present -> conservative HourlySpreadCostModel
intraday, no spreads file           -> RealisticCostModel fallback
"""

from __future__ import annotations

import pandas as pd

from forex_system.core.config import BacktestConfig, PairConfig, StrategyParams, SystemConfig
from forex_system.costs.hourly_spread import HourlySpreadCostModel
from forex_system.costs.model import RealisticCostModel
from forex_system.harness.run_trial import _build_cost_model


def _config(tmp_path) -> SystemConfig:
    pair = PairConfig(
        symbol="EURUSD", pip_value=0.0001, spread_pips=2.0, slippage_pips=0.5,
        commission_pips=0.5, swap_long_pips_per_day=-1.2, swap_short_pips_per_day=0.3,
    )
    return SystemConfig(
        pairs=[pair], strategies=[StrategyParams(name="x")],
        backtest=BacktestConfig(), data_dir=str(tmp_path),
    )


def test_daily_uses_fixed_spread_model(tmp_path):
    cm = _build_cost_model(_config(tmp_path), "EURUSD", "daily")
    assert type(cm) is RealisticCostModel  # exact type — not the time-varying subclass


def test_intraday_without_spreads_file_falls_back(tmp_path):
    cm = _build_cost_model(_config(tmp_path), "EURUSD", "1h")
    assert type(cm) is RealisticCostModel


def test_intraday_with_4h_spreads_uses_hourly_curve(tmp_path):
    spreads = tmp_path / "spreads"
    spreads.mkdir()
    pd.DataFrame(
        {"spread_pips": [2.0, 2.4, 8.0], "hour": [9, 17, 17], "day_of_week": [1, 1, 1]}
    ).to_parquet(spreads / "EURUSD_4h_spreads.parquet")
    cm = _build_cost_model(_config(tmp_path), "EURUSD", "1h")
    assert isinstance(cm, HourlySpreadCostModel)
    # q=0.9 conservative: 17:00 (thin) costs more than 09:00 (deep)
    deep = cm.entry_cost("EURUSD", 1.0, timestamp=pd.Timestamp("2021-01-04T09:00", tz="UTC"))
    thin = cm.entry_cost("EURUSD", 1.0, timestamp=pd.Timestamp("2021-01-04T17:00", tz="UTC"))
    assert thin > deep
