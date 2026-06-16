"""Tests for the hour-of-day spread curve and HourlySpreadCostModel (P0 #1)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from forex_system.costs.hourly_spread import (
    HourlySpreadCostModel,
    build_hourly_spread_curve,
    build_hourly_spread_curve_from_frame,
)
from forex_system.core.types import Direction, PairInfo

_PAIR = {
    "EURUSD": PairInfo(
        symbol="EURUSD",
        pip_value=0.0001,
        spread_pips=0.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=-1.2,
        swap_short_pips_per_day=0.3,
    )
}


def _frame(hour_to_spread: dict[int, float]) -> pd.DataFrame:
    rows = [{"spread_pips": s, "hour": h} for h, s in hour_to_spread.items() for _ in range(3)]
    return pd.DataFrame(rows)


def test_curve_has_all_24_hours_and_matches_medians():
    src = {h: 2.0 for h in range(0, 24, 2)}  # even hours present
    src[16] = 3.5
    src[18] = 4.0
    curve = build_hourly_spread_curve_from_frame(_frame(src))
    assert set(curve.keys()) == set(range(24))
    assert curve[0] == pytest.approx(2.0)
    assert curve[16] == pytest.approx(3.5)
    assert curve[18] == pytest.approx(4.0)


def test_missing_hours_are_circular_interpolated():
    curve = build_hourly_spread_curve_from_frame(_frame({0: 2.0, 4: 6.0}))
    # h=2 sits midway between 0 (2.0) and 4 (6.0)
    assert curve[2] == pytest.approx(4.0)
    assert curve[1] == pytest.approx(3.0)
    assert curve[3] == pytest.approx(5.0)
    # h=23 interpolates circularly between 4 (far) and 0 (adjacent) -> near 2.0
    assert 2.0 <= curve[23] <= 2.5


def test_quantile_param_raises_the_curve():
    frame = pd.DataFrame({"spread_pips": [2.0, 2.0, 2.0, 10.0], "hour": [1, 1, 1, 1]})
    median = build_hourly_spread_curve_from_frame(frame, quantile=0.5)[1]
    p90 = build_hourly_spread_curve_from_frame(frame, quantile=0.9)[1]
    assert p90 > median


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        build_hourly_spread_curve_from_frame(pd.DataFrame({"hour": [1]}))  # no spread_pips
    with pytest.raises(ValueError):
        build_hourly_spread_curve_from_frame(_frame({0: 2.0}), quantile=1.5)


def test_cost_model_uses_curve_when_timestamp_given():
    curve = {h: 2.0 for h in range(24)}
    curve[17] = 4.0  # elevated thin-liquidity hour
    cm = HourlySpreadCostModel(pair_configs=_PAIR, hourly_spread_curve=curve)
    baseline = cm.entry_cost("EURUSD", 1.0, timestamp=pd.Timestamp("2021-01-04T01:00", tz="UTC"))
    elevated = cm.entry_cost("EURUSD", 1.0, timestamp=pd.Timestamp("2021-01-04T17:00", tz="UTC"))
    # entry_cost = spread/2 + slippage(0.5)
    assert baseline == pytest.approx(2.0 / 2 + 0.5)
    assert elevated == pytest.approx(4.0 / 2 + 0.5)
    assert elevated > baseline


def test_cost_model_falls_back_to_fixed_without_timestamp():
    from forex_system.costs.model import RealisticCostModel

    curve = {h: 9.9 for h in range(24)}  # curve would dominate IF used
    hourly = HourlySpreadCostModel(pair_configs=_PAIR, hourly_spread_curve=curve)
    fixed = RealisticCostModel(pair_configs=_PAIR)
    # No timestamp -> must equal the fixed-spread model exactly (drop-in safety)
    assert hourly.entry_cost("EURUSD", 1.0) == fixed.entry_cost("EURUSD", 1.0)
    assert hourly.exit_cost("EURUSD", 1.0) == fixed.exit_cost("EURUSD", 1.0)


def test_exit_cost_includes_commission_and_swap_inherited():
    curve = {h: 2.0 for h in range(24)}
    cm = HourlySpreadCostModel(pair_configs=_PAIR, hourly_spread_curve=curve)
    ts = pd.Timestamp("2021-01-04T01:00", tz="UTC")
    assert cm.exit_cost("EURUSD", 1.0, timestamp=ts) == pytest.approx(2.0 / 2 + 0.5 + 0.5)
    # holding_cost inherited unchanged from RealisticCostModel
    assert cm.holding_cost("EURUSD", Direction.LONG, 1.0) == pytest.approx(1.2)


def test_non_utc_timestamp_normalised_to_utc():
    """A tz-aware non-UTC timestamp must index the curve by its UTC hour."""
    curve = {h: 2.0 for h in range(24)}
    curve[22] = 5.0  # 22:00 UTC rollover
    cm = HourlySpreadCostModel(pair_configs=_PAIR, hourly_spread_curve=curve)
    # 17:00 America/New_York (EST, UTC-5) == 22:00 UTC -> must pick curve[22]=5.0
    ny = pd.Timestamp("2021-01-04T17:00", tz="America/New_York")
    assert cm.entry_cost("EURUSD", 1.0, timestamp=ny) == pytest.approx(5.0 / 2 + 0.5)
    # tz-naive is assumed UTC
    naive = pd.Timestamp("2021-01-04T22:00")
    assert cm.entry_cost("EURUSD", 1.0, timestamp=naive) == pytest.approx(5.0 / 2 + 0.5)


def test_weekend_saturday_filtered_by_default():
    """Saturday rows must be excluded by default. The effect is visible at a high
    quantile (the median is robust to a minority of outliers, so weekend bias only
    bites a conservative/quantile curve — which is exactly when it matters)."""
    rows = [{"spread_pips": 2.0, "hour": 21, "day_of_week": 1} for _ in range(50)]
    rows += [{"spread_pips": 40.0, "hour": 21, "day_of_week": 5} for _ in range(10)]  # Saturday
    frame = pd.DataFrame(rows)
    default_curve = build_hourly_spread_curve_from_frame(frame, quantile=0.9)  # drops Sat
    kept_curve = build_hourly_spread_curve_from_frame(frame, drop_days=(), quantile=0.9)
    assert default_curve[21] == pytest.approx(2.0)
    assert kept_curve[21] > default_curve[21]  # Saturday outliers enter the p90 tail when kept


def test_build_from_real_eurusd_4h_spreads_if_present():
    path = Path("data/spreads/EURUSD_4h_spreads.parquet")
    if not path.exists():
        pytest.skip("real spread file not present")
    curve = build_hourly_spread_curve(str(path))
    assert set(curve.keys()) == set(range(24))
    assert all(v > 0 for v in curve.values())
    # the 17-18 UTC thin-liquidity window should be >= the deep-liquidity hours
    assert curve[17] >= curve[9]
