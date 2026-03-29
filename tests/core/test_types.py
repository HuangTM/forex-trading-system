"""Tests for core domain types."""

import pandas as pd
import pytest

from forex_system.core.types import BacktestResult, Direction, PairInfo, Trade


def test_direction_values():
    assert Direction.LONG.value == 1
    assert Direction.SHORT.value == -1
    assert Direction.FLAT.value == 0


def test_pair_info_frozen():
    pair = PairInfo("EURUSD", 0.0001, 0.5, 0.5, 0.5, -1.2, 0.3)
    with pytest.raises(AttributeError):
        pair.spread_pips = 1.0


def test_trade_frozen():
    trade = Trade(
        pair="EURUSD",
        direction=Direction.LONG,
        entry_time=pd.Timestamp("2020-01-01"),
        exit_time=pd.Timestamp("2020-01-10"),
        entry_price=1.10,
        exit_price=1.11,
        size=10000,
        pnl_pips=100,
        pnl_dollars=100,
        cost_pips=2.0,
        cost_dollars=2.0,
        strategy="test",
    )
    assert trade.pair == "EURUSD"
    with pytest.raises(AttributeError):
        trade.pair = "USDJPY"
