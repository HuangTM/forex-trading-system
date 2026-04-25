"""Strategy registry — maps config names to strategy classes."""

from forex_system.core.interfaces import Strategy
from forex_system.strategies.bollinger_rsi import BollingerRSIStrategy
from forex_system.strategies.carry import CarryStrategy
from forex_system.strategies.carry_momentum import CarryMomentumStrategy
from forex_system.strategies.ma_crossover import MACrossoverStrategy
from forex_system.strategies.momentum import MomentumStrategy
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "ma_crossover": MACrossoverStrategy,
    "bollinger_rsi": BollingerRSIStrategy,
    "momentum": MomentumStrategy,
    "carry": CarryStrategy,
    "carry_momentum": CarryMomentumStrategy,
    "vol_target_carry": VolTargetCarryStrategy,
}


def create_strategy(name: str, params: dict) -> Strategy:
    """Instantiate a strategy by name with given parameters."""
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")
    return cls(params)
