"""Configuration loading and validation."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from forex_system.core.errors import ConfigError
from forex_system.core.types import PairInfo


@dataclass
class PairConfig:
    symbol: str
    pip_value: float
    spread_pips: float
    slippage_pips: float
    commission_pips: float
    swap_long_pips_per_day: float
    swap_short_pips_per_day: float

    def to_pair_info(self) -> PairInfo:
        return PairInfo(**{k: getattr(self, k) for k in PairInfo.__dataclass_fields__})


@dataclass
class StrategyParams:
    name: str
    params: dict = field(default_factory=dict)


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.02
    stop_loss_atr_multiple: float = 2.0
    max_position_pct: float = 0.10
    entry_delay_bars: int = 1
    walkforward_enabled: bool = False
    walkforward_train_days: int = 504
    walkforward_test_days: int = 126
    walkforward_step_days: int = 63
    rebalance_mode: str = "discrete"
    rebalance_threshold: float = 0.20


@dataclass
class SystemConfig:
    """Top-level configuration for the forex trading system."""

    pairs: list[PairConfig]
    strategies: list[StrategyParams]
    backtest: BacktestConfig
    data_dir: str = "data"
    log_level: str = "INFO"

    def get_pair_info(self, symbol: str) -> PairInfo:
        for p in self.pairs:
            if p.symbol == symbol:
                return p.to_pair_info()
        raise ConfigError(f"Pair {symbol} not found in config")

    @property
    def pair_symbols(self) -> list[str]:
        return [p.symbol for p in self.pairs]


def load_config(path: str | Path) -> SystemConfig:
    """Load and validate YAML configuration."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

    try:
        # Parse pairs
        pairs = []
        for p in raw.get("pairs", []):
            pairs.append(PairConfig(**p))
        if not pairs:
            raise ConfigError("At least one pair must be configured")

        # Parse strategies
        strategies = []
        strategy_section = raw.get("strategies", {})
        active = strategy_section.get("active", [])
        for name in active:
            params = strategy_section.get(name, {})
            strategies.append(StrategyParams(name=name, params=params))
        if not strategies:
            raise ConfigError("At least one strategy must be active")

        # Parse backtest config
        bt_raw = raw.get("backtest", {})
        ps_raw = bt_raw.get("position_sizing", {})
        exec_raw = bt_raw.get("execution", {})
        wf_raw = bt_raw.get("walkforward", {})

        backtest = BacktestConfig(
            initial_capital=bt_raw.get("initial_capital", 100_000.0),
            risk_per_trade=ps_raw.get("risk_per_trade", 0.02),
            stop_loss_atr_multiple=ps_raw.get("stop_loss_atr_multiple", 2.0),
            max_position_pct=ps_raw.get("max_position_pct", 0.10),
            entry_delay_bars=exec_raw.get("entry_delay_bars", 1),
            walkforward_enabled=bool(wf_raw.get("enabled", False)),
            walkforward_train_days=wf_raw.get("train_window_days", 504),
            walkforward_test_days=wf_raw.get("test_window_days", 126),
            walkforward_step_days=wf_raw.get("step_days", 63),
            rebalance_mode=exec_raw.get("rebalance_mode", "discrete"),
            rebalance_threshold=float(exec_raw.get("rebalance_threshold", 0.20)),
        )

        return SystemConfig(
            pairs=pairs,
            strategies=strategies,
            backtest=backtest,
            data_dir=raw.get("data", {}).get("base_dir", "data"),
            log_level=raw.get("system", {}).get("log_level", "INFO"),
        )

    except (KeyError, TypeError) as e:
        raise ConfigError(f"Invalid config structure: {e}") from e
