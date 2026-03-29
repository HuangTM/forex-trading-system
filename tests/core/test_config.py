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
