"""Tests for configuration loading."""

import pytest

from forex_system.core.config import load_config
from forex_system.core.errors import ConfigError


def test_load_valid_config(sample_config_path):
    config = load_config(sample_config_path)
    assert len(config.pairs) == 1
    assert config.pairs[0].symbol == "EURUSD"
    assert len(config.strategies) == 1
    assert config.strategies[0].name == "ma_crossover"
    assert config.backtest.initial_capital == 100_000.0


def test_missing_config_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/config.yaml")


def test_get_pair_info(sample_config_path):
    config = load_config(sample_config_path)
    pair = config.get_pair_info("EURUSD")
    assert pair.pip_value == 0.0001
    assert pair.spread_pips == 0.5


def test_get_pair_info_missing(sample_config_path):
    config = load_config(sample_config_path)
    with pytest.raises(ConfigError, match="not found"):
        config.get_pair_info("AUDUSD")


_MINIMAL_PAIR = """
pairs:
  - symbol: "EURUSD"
    pip_value: 0.0001
    spread_pips: 0.5
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_day: -1.2
    swap_short_pips_per_day: 0.3
strategies:
  active:
    - "ma_crossover"
  ma_crossover:
    fast_period: 10
    slow_period: 30
"""


def test_walkforward_enabled_true(tmp_path):
    """walkforward.enabled: true is parsed into BacktestConfig.walkforward_enabled=True."""
    config_file = tmp_path / "wf_enabled.yaml"
    config_file.write_text(
        _MINIMAL_PAIR + """
backtest:
  initial_capital: 100000.0
  walkforward:
    enabled: true
    train_window_days: 504
    test_window_days: 504
    step_days: 252
"""
    )
    config = load_config(config_file)
    assert config.backtest.walkforward_enabled is True


def test_walkforward_enabled_false(tmp_path):
    """walkforward.enabled: false is parsed into BacktestConfig.walkforward_enabled=False."""
    config_file = tmp_path / "wf_disabled.yaml"
    config_file.write_text(
        _MINIMAL_PAIR + """
backtest:
  initial_capital: 100000.0
  walkforward:
    enabled: false
    train_window_days: 504
    test_window_days: 504
    step_days: 252
"""
    )
    config = load_config(config_file)
    assert config.backtest.walkforward_enabled is False


def test_walkforward_enabled_absent(tmp_path):
    """When walkforward.enabled is absent, defaults to False."""
    config_file = tmp_path / "wf_absent.yaml"
    config_file.write_text(
        _MINIMAL_PAIR + """
backtest:
  initial_capital: 100000.0
  walkforward:
    train_window_days: 504
    test_window_days: 504
    step_days: 252
"""
    )
    config = load_config(config_file)
    assert config.backtest.walkforward_enabled is False


def test_empty_strategies(tmp_path):
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("""
pairs:
  - symbol: "EURUSD"
    pip_value: 0.0001
    spread_pips: 0.5
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_day: -1.2
    swap_short_pips_per_day: 0.3
strategies:
  active: []
""")
    with pytest.raises(ConfigError, match="strategy"):
        load_config(config_file)
