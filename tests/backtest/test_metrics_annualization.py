"""Frequency-aware annualisation for Sharpe/Sortino (P0 #1b).

A daily-hardcoded sqrt(252) factor understates an hourly Sharpe by ~5x. These
tests pin three things:
  1. Default behaviour is unchanged (daily, 252) — zero regression for callers.
  2. An explicit hourly factor scales the Sharpe by exactly sqrt(6240/252).
  3. infer_periods_per_year snaps bar spacing to the canonical factor.
  4. The fix does NOT move DSR (SR and periods_per_year scale together → cancel).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.metrics import calculate_metrics, infer_periods_per_year
from forex_system.core.constants import TRADING_DAYS_PER_YEAR, TRADING_HOURS_PER_YEAR
from forex_system.harness.dsr import compute_dsr


def _equity(index: pd.DatetimeIndex) -> pd.Series:
    rng = np.random.default_rng(0)
    rets = rng.normal(0.0002, 0.005, len(index))
    return pd.Series(100_000 * np.cumprod(1.0 + rets), index=index)


def test_default_is_daily_252_regression():
    """Default (periods_per_year=None) must equal explicit 252 — no behaviour change."""
    idx = pd.bdate_range("2021-01-01", periods=300, freq="B", tz="UTC")
    ec = _equity(idx)
    m_default = calculate_metrics(ec, [])
    m_explicit = calculate_metrics(ec, [], periods_per_year=TRADING_DAYS_PER_YEAR)
    assert m_default.sharpe_ratio == m_explicit.sharpe_ratio
    assert m_default.sortino_ratio == m_explicit.sortino_ratio


def test_default_no_arg_path_infers_for_intraday_callers():
    """walkforward / arson_test / null_hypothesis call calculate_metrics WITHOUT
    periods_per_year. Verify that no-arg path infers the intraday factor (not the
    old hardcoded 252), so those callers are correct on 1h/4h data."""
    idx = pd.date_range("2021-01-01", periods=2000, freq="h", tz="UTC")
    ec = _equity(idx)
    m_default = calculate_metrics(ec, [])  # how the pass-through callers invoke it
    m_explicit = calculate_metrics(ec, [], periods_per_year=TRADING_HOURS_PER_YEAR)
    assert m_default.sharpe_ratio == m_explicit.sharpe_ratio
    # and it is NOT the old daily-hardcoded value
    m_old = calculate_metrics(ec, [], periods_per_year=TRADING_DAYS_PER_YEAR)
    assert m_default.sharpe_ratio != m_old.sharpe_ratio


def test_hourly_scales_sharpe_by_sqrt_ratio():
    idx = pd.date_range("2021-01-01", periods=2000, freq="h", tz="UTC")
    ec = _equity(idx)
    m_daily = calculate_metrics(ec, [], periods_per_year=TRADING_DAYS_PER_YEAR)
    m_hourly = calculate_metrics(ec, [], periods_per_year=TRADING_HOURS_PER_YEAR)
    expected = (TRADING_HOURS_PER_YEAR / TRADING_DAYS_PER_YEAR) ** 0.5
    assert m_hourly.sharpe_ratio / m_daily.sharpe_ratio == pytest.approx(expected, rel=1e-9)


def test_infer_periods_per_year_snaps_to_canonical():
    daily = pd.bdate_range("2021-01-01", periods=300, freq="B", tz="UTC")
    hourly = pd.date_range("2021-01-01", periods=300, freq="h", tz="UTC")
    h4 = pd.date_range("2021-01-01", periods=300, freq="4h", tz="UTC")
    assert infer_periods_per_year(daily) == float(TRADING_DAYS_PER_YEAR)
    assert infer_periods_per_year(hourly) == float(TRADING_HOURS_PER_YEAR)
    assert infer_periods_per_year(h4) == TRADING_HOURS_PER_YEAR / 4.0


def test_infer_robust_to_weekend_gaps():
    """Real hourly forex data has weekend gaps; median spacing is still 1h."""
    idx = pd.date_range("2021-01-04", periods=24 * 5, freq="h", tz="UTC")  # one trading week
    # inject a weekend gap then resume
    idx2 = idx.append(pd.date_range(idx[-1] + pd.Timedelta(hours=49), periods=24 * 5, freq="h"))
    assert infer_periods_per_year(idx2) == float(TRADING_HOURS_PER_YEAR)


def test_infer_4h_with_weekend_gaps():
    """A normal-length 4h series with weekend gaps still snaps to 1560."""
    weeks = []
    start = pd.Timestamp("2021-01-04", tz="UTC")
    for w in range(8):  # 8 trading weeks of 4h bars, Mon-Fri
        wk = pd.date_range(start + pd.Timedelta(weeks=w), periods=30, freq="4h", tz="UTC")
        weeks.append(wk)
    idx = weeks[0]
    for wk in weeks[1:]:
        idx = idx.append(wk)  # gaps between weeks
    assert infer_periods_per_year(idx) == TRADING_HOURS_PER_YEAR / 4.0


def test_infer_non_datetime_index_falls_back():
    assert infer_periods_per_year(pd.RangeIndex(100)) == float(TRADING_DAYS_PER_YEAR)


def test_infer_two_bar_hourly():
    idx = pd.DatetimeIndex(["2021-01-04T00:00", "2021-01-04T01:00"], tz="UTC")
    assert infer_periods_per_year(idx) == float(TRADING_HOURS_PER_YEAR)


def test_infer_all_same_timestamp_falls_back():
    idx = pd.DatetimeIndex(["2021-01-04", "2021-01-04", "2021-01-04"], tz="UTC")
    assert infer_periods_per_year(idx) == float(TRADING_DAYS_PER_YEAR)


def test_dsr_invariant_to_annualisation():
    """The headline Sharpe fix must NOT change DSR (the test_dsr.py unit-invariance
    property, exercised through the realistic daily<->hourly rescale)."""
    c = (TRADING_HOURS_PER_YEAR / TRADING_DAYS_PER_YEAR) ** 0.5
    d_daily = compute_dsr(1.5, 5000, 0.0, 0.0, 5, periods_per_year=float(TRADING_DAYS_PER_YEAR))
    d_hourly = compute_dsr(1.5 * c, 5000, 0.0, 0.0, 5, periods_per_year=float(TRADING_HOURS_PER_YEAR))
    assert d_daily == pytest.approx(d_hourly, abs=1e-12)
