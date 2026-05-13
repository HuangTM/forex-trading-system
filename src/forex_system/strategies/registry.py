"""Strategy registry — maps config names to strategy classes."""

from forex_system.core.interfaces import Strategy
from forex_system.strategies.bollinger_rsi import BollingerRSIStrategy
from forex_system.strategies.carry import CarryStrategy
from forex_system.strategies.carry_fred import CarryFREDStrategy
from forex_system.strategies.carry_momentum import CarryMomentumStrategy
from forex_system.strategies.fred_carry_stripped import FredCarryStrippedStrategy
from forex_system.strategies.ma_crossover import MACrossoverStrategy
from forex_system.strategies.momentum import MomentumStrategy
from forex_system.strategies.tas_ceiling_4h import TasCeiling4hStrategy
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy
from forex_system.strategies.vol_target_carry_no_vol_scaling import (
    VolTargetCarryNoVolScalingStrategy,
)

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "ma_crossover": MACrossoverStrategy,
    "bollinger_rsi": BollingerRSIStrategy,
    "momentum": MomentumStrategy,
    "carry": CarryStrategy,
    "carry_fred": CarryFREDStrategy,
    "carry_momentum": CarryMomentumStrategy,
    "fred_carry_stripped": FredCarryStrippedStrategy,
    "vol_target_carry": VolTargetCarryStrategy,
    "vol_target_carry_no_vol_scaling": VolTargetCarryNoVolScalingStrategy,
    "tas_ceiling_4h": TasCeiling4hStrategy,
}


def create_strategy(
    name: str,
    params: dict,
    *,
    rate_data=None,  # Optional[pd.DataFrame] — keyword-only per D-1.1 ABC contract
) -> Strategy:
    """Instantiate a strategy by name with given parameters.

    REM-1 / D-1.1: rate_data is a keyword-only argument that is forwarded to
    the strategy __init__.  All strategies accept rate_data=None (the ABC
    contract guarantees this).  Callers that need rate data pass it explicitly;
    callers that do not (backtest, walk-forward) omit it.

    No reflection, no allowlist — the unified ABC contract handles all strategies.
    """
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")
    return cls(params, rate_data=rate_data)
