"""Margin / liquidation simulation (discrete mode).

Without it, a sleeve could lose >100% and keep trading: the 2026-10-25 carry
retest's EURGBP sleeve fell to 0.7% of capital (below zero with static swap) and
then produced +958% "returns" on its near-zero equity base.
"""

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.core.interfaces import PositionSizer
from forex_system.core.types import MarginConfig, PairInfo
from forex_system.costs.model import RealisticCostModel

_MARGIN = MarginConfig(margin_rate=0.05, stop_out_level=0.5)  # 20:1, stop-out at 50%


class _FixedSizer(PositionSizer):
    def __init__(self, units: float):
        self.units = units

    def calculate_size(self, signal, account_equity, price, atr, pair):
        return self.units


def _free_model() -> RealisticCostModel:
    return RealisticCostModel({
        "EURUSD": PairInfo("EURUSD", 0.0001, 0.0, 0.0, 0.0, 0.0, 0.0),
    })


def _bars(closes, lows=None, highs=None, opens=None) -> pd.DataFrame:
    closes = np.asarray(closes, dtype=float)
    idx = pd.date_range("2023-01-02", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": closes if opens is None else opens,
            "high": closes if highs is None else highs,
            "low": closes if lows is None else lows,
            "close": closes,
            "atr_14": 0.001,
        },
        index=idx,
    )


def _run(data, signal, units, margin=_MARGIN, capital=10_000.0):
    return run_backtest(
        data, pd.Series(signal, index=data.index), "EURUSD", "t", _free_model(),
        initial_capital=capital, entry_delay_bars=1, sizer=_FixedSizer(units), margin=margin,
    )


def test_long_liquidated_at_stop_out_price():
    # 100k units at 1.0 on 10k equity (10x). Stop-out: 10k + (p-1)*1e5 = 0.5*0.05*1e5*p
    # -> p* = (1e5 - 1e4) / (1e5 * 0.975) = 0.923077
    closes = [1.0, 1.0, 0.99, 0.95, 0.90, 0.88]
    opens = [1.0, 1.0, 1.0, 0.99, 0.95, 0.90]  # no gaps: each bar opens at the prior close
    lows = [1.0, 1.0, 0.99, 0.95, 0.90, 0.88]
    res = _run(_bars(closes, lows=lows, opens=opens), 1.0, 100_000)
    p_star = 90_000 / 97_500
    assert res.parameters["n_liquidations"] == 1
    trade = res.trade_log[0]
    assert trade.exit_price == pytest.approx(p_star)
    # Equity after stop-out equals the stop-out level of used margin.
    assert res.equity_curve.iloc[4] == pytest.approx(0.5 * 0.05 * 100_000 * p_star)
    # No re-entry while the signal is unchanged.
    assert len(res.trade_log) == 1
    assert res.equity_curve.iloc[-1] == pytest.approx(res.equity_curve.iloc[4])


def test_gap_through_fills_at_open():
    closes = [1.0, 1.0, 0.99, 0.85, 0.85]
    opens = [1.0, 1.0, 0.99, 0.86, 0.85]
    res = _run(_bars(closes, opens=opens), 1.0, 100_000)
    assert res.trade_log[0].exit_price == pytest.approx(0.86)


def test_short_liquidated_on_high():
    # Short 100k at 1.0: p* = (1e4 + 1e5) / (1e5 * 1.025) = 1.073171
    closes = [1.0, 1.0, 1.02, 1.05, 1.06]
    highs = [1.0, 1.0, 1.03, 1.08, 1.06]
    res = _run(_bars(closes, highs=highs), -1.0, 100_000)
    assert res.parameters["n_liquidations"] == 1
    assert res.trade_log[0].exit_price == pytest.approx(110_000 / 102_500)


def test_entry_size_capped_by_leverage():
    res = _run(_bars([1.0] * 5), 1.0, 1_000_000)  # 100x requested, 20x allowed
    assert res.trade_log[0].size == pytest.approx(10_000 / (0.05 * 1.0))


def test_blown_account_does_not_reopen():
    # Gap far through the stop leaves equity negative; a later signal flip cannot open.
    closes = [1.0, 1.0, 0.80, 0.80, 0.80, 0.80]
    sig = [1.0, 1.0, 1.0, 1.0, -1.0, -1.0]
    res = _run(_bars(closes), sig, 200_000)  # 20x
    assert res.parameters["n_liquidations"] == 1
    assert res.equity_curve.iloc[2] < 0
    assert len(res.trade_log) == 1


def test_no_liquidation_when_margin_is_loose_matches_no_margin():
    rng = np.random.default_rng(1)
    closes = 1.1 + np.cumsum(rng.normal(0, 0.003, 60))
    data = _bars(closes, lows=closes - 0.001, highs=closes + 0.001)
    sig = np.where(np.arange(60) % 20 < 10, 1.0, -1.0)
    loose = MarginConfig(margin_rate=1e-6, stop_out_level=0.0)
    with_margin = _run(data, sig, 5_000, margin=loose)
    without = _run(data, sig, 5_000, margin=None)
    pd.testing.assert_series_equal(with_margin.equity_curve, without.equity_curve)


def test_margin_rejected_in_continuous_mode():
    data = _bars([1.0] * 5)
    with pytest.raises(NotImplementedError, match="discrete mode only"):
        run_backtest(data, pd.Series(1.0, index=data.index), "EURUSD", "t", _free_model(),
                     sizer=_FixedSizer(1), rebalance_mode="continuous", margin=_MARGIN)
