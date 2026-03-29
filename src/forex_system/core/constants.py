"""System-wide constants and pair definitions."""

from forex_system.core.types import PairInfo

# Phase 0 target pairs — the 3 most liquid forex pairs
DEFAULT_PAIRS: dict[str, PairInfo] = {
    "EURUSD": PairInfo(
        symbol="EURUSD",
        pip_value=0.0001,
        spread_pips=0.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=-1.2,
        swap_short_pips_per_day=0.3,
    ),
    "USDJPY": PairInfo(
        symbol="USDJPY",
        pip_value=0.01,
        spread_pips=0.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.8,
        swap_short_pips_per_day=-1.5,
    ),
    "GBPUSD": PairInfo(
        symbol="GBPUSD",
        pip_value=0.0001,
        spread_pips=0.8,
        slippage_pips=0.6,
        commission_pips=0.5,
        swap_long_pips_per_day=-0.9,
        swap_short_pips_per_day=0.1,
    ),
}

# Trading days per year (approximate)
TRADING_DAYS_PER_YEAR = 252

# Default initial capital
DEFAULT_INITIAL_CAPITAL = 100_000.0
