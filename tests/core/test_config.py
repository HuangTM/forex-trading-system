"""Tests for configuration loading."""

import pytest

from forex_system.core.config import SystemConfig, load_config
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


# ---------------------------------------------------------------------------
# Gap-1 / BC-COST-RECON: SystemConfig.raw field and config-wiring tests
# ---------------------------------------------------------------------------


def test_load_config_populates_raw(tmp_path):
    """Gap-1: load_config populates SystemConfig.raw with the full parsed YAML dict."""
    config_file = tmp_path / "raw_test.yaml"
    config_file.write_text(
        _MINIMAL_PAIR + """
paper:
  cost_reconciliation:
    tol_rel: 0.01
    tol_abs: 250.0
    reconciliation_enforce: true
    consecutive_breach_halt_n: 5
"""
    )
    config = load_config(config_file)
    assert isinstance(config.raw, dict), "raw must be a dict"
    assert "paper" in config.raw, "raw must contain the 'paper' key from the YAML"
    recon = config.raw["paper"]["cost_reconciliation"]
    assert abs(recon["tol_rel"] - 0.01) < 1e-9
    assert abs(recon["tol_abs"] - 250.0) < 1e-9
    assert recon["reconciliation_enforce"] is True
    assert recon["consecutive_breach_halt_n"] == 5


def test_load_config_raw_wires_into_ledger(tmp_path):
    """Gap-1: non-default tolerance in config.raw actually propagates to the ledger.

    This is the liveness test: proves the config wire is live, not just that
    raw is populated.  If ledger_from_config receives config.raw, it must read
    the non-default tol_rel and enforce flag from the paper.cost_reconciliation
    section.
    """
    from forex_system.paper.cost_reconciliation import ledger_from_config

    config_file = tmp_path / "wiring_test.yaml"
    config_file.write_text(
        _MINIMAL_PAIR + """
paper:
  cost_reconciliation:
    tol_rel: 0.02
    tol_abs: 750.0
    reconciliation_enforce: true
    consecutive_breach_halt_n: 7
"""
    )
    config = load_config(config_file)
    # The wire is: pass config.raw (the full dict) into ledger_from_config.
    ledger = ledger_from_config("wiring_test", config.raw)
    assert abs(ledger.tol_rel - 0.02) < 1e-9, (
        f"Gap-1: tol_rel not propagated; got {ledger.tol_rel}, expected 0.02. "
        "config.raw is likely empty or ledger_from_config is not reading it."
    )
    assert abs(ledger.tol_abs - 750.0) < 1e-9, f"Gap-1: tol_abs not propagated; got {ledger.tol_abs}"
    assert ledger.enforce is True, "Gap-1: enforce flag not propagated"
    assert ledger.consecutive_n == 7, f"Gap-1: consecutive_n not propagated; got {ledger.consecutive_n}"


def test_system_config_raw_defaults_empty():
    """SystemConfig constructed without raw= must default to empty dict.

    All existing call sites that construct SystemConfig directly (tests, scripts)
    do not pass raw=; the default must be empty dict so no regression.
    """
    from forex_system.core.config import BacktestConfig, PairConfig, StrategyParams

    pair = PairConfig(
        symbol="EURUSD",
        pip_value=0.0001,
        spread_pips=0.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=-1.2,
        swap_short_pips_per_day=0.3,
    )
    cfg = SystemConfig(
        pairs=[pair],
        strategies=[StrategyParams(name="ma_crossover")],
        backtest=BacktestConfig(),
    )
    assert cfg.raw == {}, "SystemConfig.raw must default to empty dict when not supplied"


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
