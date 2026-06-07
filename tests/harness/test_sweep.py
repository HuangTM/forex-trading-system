"""Tests for harness/sweep.py.

Covers:
- Param parsing: _parse_param_arg, _coerce_value
- Nested config: _set_nested
- Cartesian product: correct number of combinations
- run_sweep: correct number of results, cohort metadata
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forex_system.harness.sweep import (
    _coerce_value,
    _parse_param_arg,
    _set_nested,
    run_sweep,
)


class TestParseParamArg:
    def test_parses_simple_key_value(self):
        key, vals = _parse_param_arg("target_vol=0.05,0.10")
        assert key == "target_vol"
        assert vals == ["0.05", "0.10"]

    def test_parses_dotted_key(self):
        key, vals = _parse_param_arg("strategies.vt.target_vol=0.05,0.10,0.15")
        assert key == "strategies.vt.target_vol"
        assert len(vals) == 3

    def test_single_value(self):
        key, vals = _parse_param_arg("pair=USDJPY")
        assert key == "pair"
        assert vals == ["USDJPY"]

    def test_raises_without_equals(self):
        with pytest.raises(ValueError, match="key=v1"):
            _parse_param_arg("no-equals-here")


class TestCoerceValue:
    def test_int(self):
        assert _coerce_value("252") == 252
        assert isinstance(_coerce_value("252"), int)

    def test_float(self):
        assert _coerce_value("0.10") == pytest.approx(0.10)
        assert isinstance(_coerce_value("0.10"), float)

    def test_string(self):
        assert _coerce_value("USDJPY") == "USDJPY"

    def test_bool_true(self):
        assert _coerce_value("true") is True
        assert _coerce_value("True") is True

    def test_bool_false(self):
        assert _coerce_value("false") is False


class TestSetNested:
    def test_shallow_key(self):
        d = {}
        _set_nested(d, "target_vol", 0.10)
        assert d["target_vol"] == pytest.approx(0.10)

    def test_dotted_key_creates_nested_dicts(self):
        d = {}
        _set_nested(d, "strategies.vt.target_vol", 0.10)
        assert d["strategies"]["vt"]["target_vol"] == pytest.approx(0.10)

    def test_overwrites_existing(self):
        d = {"a": {"b": 1}}
        _set_nested(d, "a.b", 99)
        assert d["a"]["b"] == 99

    def test_preserves_siblings(self):
        d = {"strategies": {"name": "vt", "params": {"vol_window": 252}}}
        _set_nested(d, "strategies.params.target_vol", 0.10)
        assert d["strategies"]["params"]["vol_window"] == 252
        assert d["strategies"]["params"]["target_vol"] == pytest.approx(0.10)


@pytest.fixture
def sweep_setup(tmp_path, monkeypatch):
    """Setup for run_sweep integration tests."""
    import forex_system.harness.run_trial as rt_mod
    import forex_system.harness.sweep as sw_mod

    monkeypatch.setattr(rt_mod, "_TRIALS_REGISTRY", tmp_path / "trials.jsonl")
    monkeypatch.setattr(rt_mod, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(sw_mod, "_TRIALS_REGISTRY", tmp_path / "trials.jsonl")
    monkeypatch.setattr(sw_mod, "_SWEEP_LOG", tmp_path / "sweeps.jsonl")

    # Minimal YAML config for EURUSD
    config_text = """
system:
  name: "test"
  log_level: "INFO"
data:
  base_dir: "data"
pairs:
  - symbol: "EURUSD"
    pip_value: 0.0001
    spread_pips: 1.0
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_day: 0.1
    swap_short_pips_per_day: -0.5
strategies:
  active:
    - "vol_target_carry"
  vol_target_carry:
    target_vol: 0.10
    vol_window: 20
    leverage_cap: 2.0
backtest:
  initial_capital: 100000.0
  position_sizing:
    method: "vol_target"
    leverage_cap: 2.0
    min_order_size: 0
    max_order_units: 5000000
  execution:
    entry_delay_bars: 1
  walkforward:
    enabled: false
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_text)

    pre_reg_path = tmp_path / "pre_reg.md"
    pre_reg_path.write_text("# Pre-Reg\ngate_threshold: 0.50\n")

    return {
        "config_path": str(config_path),
        "pre_reg_path": str(pre_reg_path),
        "tmp_path": tmp_path,
    }


class TestRunSweep:
    """Integration tests for run_sweep (uses real EURUSD data if available)."""

    def test_sweep_produces_correct_count(self, sweep_setup):
        """2x2 param grid should produce 4 results."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available")

        results = run_sweep(
            config_path=sweep_setup["config_path"],
            pair="EURUSD",
            pre_reg_path=sweep_setup["pre_reg_path"],
            param_specs=[
                "strategies.vol_target_carry.target_vol=0.08,0.12",
                "strategies.vol_target_carry.vol_window=20,40",
            ],
            n_workers=1,  # Serial for test reproducibility
        )

        assert len(results) == 4, f"Expected 4 results for 2x2 grid, got {len(results)}"

    def test_sweep_writes_cohort_to_registry(self, sweep_setup):
        """run_sweep should write a cohort entry to trials.jsonl."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available")

        import forex_system.harness.sweep as sw_mod
        results = run_sweep(
            config_path=sweep_setup["config_path"],
            pair="EURUSD",
            pre_reg_path=sweep_setup["pre_reg_path"],
            param_specs=["strategies.vol_target_carry.target_vol=0.08,0.12"],
            n_workers=1,
        )

        registry_path = sw_mod._TRIALS_REGISTRY
        entries = [json.loads(l) for l in registry_path.read_text().strip().split("\n")]
        cohort_entries = [e for e in entries if e.get("event") == "sweep.cohort"]
        assert len(cohort_entries) >= 1

        cohort = cohort_entries[-1]
        assert cohort["cohort_size"] == 2

    def test_sweep_all_results_have_param_overrides(self, sweep_setup):
        """Each result should record which params were used."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available")

        results = run_sweep(
            config_path=sweep_setup["config_path"],
            pair="EURUSD",
            pre_reg_path=sweep_setup["pre_reg_path"],
            param_specs=["strategies.vol_target_carry.vol_window=20,40"],
            n_workers=1,
        )

        for r in results:
            assert "param_overrides" in r
            assert "strategies.vol_target_carry.vol_window" in r["param_overrides"]
