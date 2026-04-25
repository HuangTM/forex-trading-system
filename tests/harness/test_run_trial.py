"""Tests for harness/run_trial.py.

Covers:
- Pre-reg validation: missing pre-reg raises ConfigError
- Missing config raises ConfigError
- Valid run: trial appended to registry, report written
- parse_pre_reg_threshold: extracts gate_threshold field
- Output structure: report contains required keys
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forex_system.core.errors import ConfigError
from forex_system.harness.run_trial import _parse_pre_reg_threshold, run_trial


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    """Override the trials registry and results dir to tmp_path."""
    import forex_system.harness.run_trial as rt_mod
    monkeypatch.setattr(rt_mod, "_TRIALS_REGISTRY", tmp_path / "trials.jsonl")
    monkeypatch.setattr(rt_mod, "_RESULTS_DIR", tmp_path / "results")
    return tmp_path


@pytest.fixture
def minimal_pre_reg(tmp_path):
    """A minimal valid pre-registration markdown."""
    p = tmp_path / "pre_reg.md"
    p.write_text("# Pre-Registration\ngate_threshold: 0.50\n")
    return p


@pytest.fixture
def minimal_config(tmp_path):
    """A minimal YAML config for EURUSD with vol_target_carry strategy."""
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
    p = tmp_path / "config.yaml"
    p.write_text(config_text)
    return p


# ---------------------------------------------------------------------------
# Tests for _parse_pre_reg_threshold
# ---------------------------------------------------------------------------

class TestParsePreRegThreshold:
    def test_finds_gate_threshold(self):
        text = "# Pre-Reg\ngate_threshold: 0.60\nSome other text"
        result = _parse_pre_reg_threshold(text)
        assert result == pytest.approx(0.60)

    def test_returns_none_when_missing(self):
        text = "# Pre-Reg\nNo threshold here."
        result = _parse_pre_reg_threshold(text)
        assert result is None

    def test_handles_float_variations(self):
        for val in ["0.5", "1.0", "0.75", "2"]:
            text = f"gate_threshold: {val}"
            result = _parse_pre_reg_threshold(text)
            assert result == pytest.approx(float(val))


# ---------------------------------------------------------------------------
# Tests for run_trial — error paths
# ---------------------------------------------------------------------------

class TestRunTrialErrors:
    def test_missing_pre_reg_raises(self, tmp_registry, minimal_config):
        """Missing pre-registration must raise ConfigError immediately."""
        with pytest.raises(ConfigError, match="Pre-registration not found"):
            run_trial(
                config_path=str(minimal_config),
                pair="EURUSD",
                pre_reg_path="/nonexistent/pre_reg.md",
            )

    def test_missing_config_raises(self, tmp_registry, minimal_pre_reg):
        """Missing config must raise ConfigError."""
        with pytest.raises(ConfigError):
            run_trial(
                config_path="/nonexistent/config.yaml",
                pair="EURUSD",
                pre_reg_path=str(minimal_pre_reg),
            )

    def test_pair_not_in_config_raises(self, tmp_registry, minimal_config, minimal_pre_reg):
        """Pair not in config cost model raises ValueError."""
        with pytest.raises(Exception):
            run_trial(
                config_path=str(minimal_config),
                pair="XYZABC",  # Not in config
                pre_reg_path=str(minimal_pre_reg),
            )

    def test_missing_pre_reg_still_appends_skeleton(self, tmp_registry, minimal_config):
        """Even failed trials should append a skeleton entry to the registry."""
        import forex_system.harness.run_trial as rt_mod
        registry_path = rt_mod._TRIALS_REGISTRY

        try:
            run_trial(
                config_path=str(minimal_config),
                pair="EURUSD",
                pre_reg_path="/nonexistent/pre_reg.md",
            )
        except ConfigError:
            pass

        # Skeleton must have been written before the error
        assert registry_path.exists(), "Registry should exist after spawn"
        lines = registry_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        entry = json.loads(lines[0])
        assert entry["status"] == "spawned"
        assert entry["pair"] == "EURUSD"


# ---------------------------------------------------------------------------
# Tests for run_trial — integration (uses real EURUSD daily data)
# ---------------------------------------------------------------------------

class TestRunTrialIntegration:
    """Integration tests that run against real parquet data."""

    def test_run_trial_produces_report(self, tmp_registry, minimal_config, minimal_pre_reg):
        """Full run against EURUSD daily should produce a report file."""
        import forex_system.harness.run_trial as rt_mod

        # Only run if EURUSD daily data exists
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available in this environment")

        report = run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        # Check required keys
        assert "trial_id" in report
        assert "metrics" in report
        assert "dsr" in report
        assert "gate" in report
        assert report["pair"] == "EURUSD"
        assert report["metrics"]["n_trades"] >= 0
        assert 0.0 <= report["dsr"]["value"] <= 1.0

        # Check report file was written
        report_path = Path(report["report_path"])
        assert report_path.exists()

        # Check registry was updated
        registry_path = rt_mod._TRIALS_REGISTRY
        lines = [json.loads(l) for l in registry_path.read_text().strip().split("\n")]
        trial_ids = [l["trial_id"] for l in lines]
        assert report["trial_id"] in trial_ids

        # Check complete entry
        complete_entries = [l for l in lines if l.get("status") == "complete"]
        assert len(complete_entries) >= 1

    def test_run_trial_registry_grows(self, tmp_registry, minimal_config, minimal_pre_reg):
        """Two runs should produce two complete entries in the registry."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available in this environment")

        import forex_system.harness.run_trial as rt_mod

        run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )
        run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        registry_path = rt_mod._TRIALS_REGISTRY
        lines = [json.loads(l) for l in registry_path.read_text().strip().split("\n")]
        complete_entries = [l for l in lines if l.get("status") == "complete"]
        assert len(complete_entries) >= 2

    def test_second_trial_has_higher_n_trials(self, tmp_registry, minimal_config, minimal_pre_reg):
        """Second trial should see more prior trials than the first."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available in this environment")

        import forex_system.harness.run_trial as rt_mod

        report1 = run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )
        report2 = run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        n1 = report1["dsr"]["n_trials"]
        n2 = report2["dsr"]["n_trials"]
        assert n2 > n1, f"Second trial should see more trials: got n1={n1}, n2={n2}"
