"""Tests for transaction cost model."""

import pytest

from forex_system.core.constants import DEFAULT_PAIRS
from forex_system.core.types import Direction
from forex_system.costs.model import RealisticCostModel


@pytest.fixture
def cost_model():
    return RealisticCostModel()


def test_entry_cost(cost_model):
    cost = cost_model.entry_cost("EURUSD", 10000)
    # Half spread (0.25) + slippage (0.5) = 0.75 pips
    assert cost == pytest.approx(0.75)


def test_exit_cost(cost_model):
    cost = cost_model.exit_cost("EURUSD", 10000)
    # Half spread (0.25) + slippage (0.5) + commission (0.5) = 1.25 pips
    assert cost == pytest.approx(1.25)


def test_round_trip(cost_model):
    rt = cost_model.round_trip_cost("EURUSD", 10000)
    assert rt == pytest.approx(2.0)  # entry 0.75 + exit 1.25


def test_holding_cost_long(cost_model):
    # EURUSD long swap is -1.2 pips/day, so holding cost = +1.2 * days
    cost = cost_model.holding_cost("EURUSD", Direction.LONG, 5.0)
    assert cost == pytest.approx(6.0)  # -(-1.2) * 5 = 6.0


def test_holding_cost_short(cost_model):
    # EURUSD short swap is +0.3 pips/day, so holding cost = -0.3 * days (negative = income)
    cost = cost_model.holding_cost("EURUSD", Direction.SHORT, 5.0)
    assert cost == pytest.approx(-1.5)  # -(0.3) * 5 = -1.5


def test_jpy_pair(cost_model):
    cost = cost_model.entry_cost("USDJPY", 10000)
    assert cost > 0


def test_unknown_pair(cost_model):
    with pytest.raises(ValueError, match="No cost config"):
        cost_model.entry_cost("XXXYYY", 10000)
