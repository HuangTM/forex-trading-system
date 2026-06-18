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
from pathlib import Path

import pandas as pd
import pytest

from forex_system.core.errors import ConfigError
from forex_system.harness.run_trial import _parse_pre_reg_threshold, run_trial


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    """Override the trials registry and results dir to tmp_path.

    Writes a minimal honest-n-classification record so honest_n_deflation_denominator
    works against the tmp registry without raising (0 legacy counted ids: fresh env
    starts at 0 prior attempts, not the real 30).

    NOTE: The old fixture wrote an 'honest-n-reconciliation' record (retired integer-
    offset approach). Updated to 'honest-n-classification' per the 2026-06-18 rebuild.
    """
    import json
    import forex_system.harness.run_trial as rt_mod

    registry_path = tmp_path / "trials.jsonl"
    # Write the classification record so honest_n_deflation_denominator doesn't raise.
    # counted_trial_ids=[] means the test env starts fresh (no prior attempts).
    classification = {
        "event": "honest-n-classification",
        "version": 1,
        "ratified_n": 0,
        "ratified_by": ["test-fixture"],
        "counted_trial_ids": [],
        "excluded_trial_ids": [],
        "n_legacy_classified": 0,
        "forward_classification": "all new trials classify mechanically",
        "ts": "2026-06-18T00:00:00Z",
    }
    with open(registry_path, "w") as f:
        f.write(json.dumps(classification) + "\n")

    monkeypatch.setattr(rt_mod, "_TRIALS_REGISTRY", registry_path)
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

        # Skeleton must have been written before the error.
        # Note: lines[0] is the reconciliation baseline record written by the fixture;
        # the spawned skeleton is the FIRST trial record (skip non-trial lines).
        assert registry_path.exists(), "Registry should exist after spawn"
        all_records = [json.loads(l) for l in registry_path.read_text().strip().split("\n")]
        trial_records = [r for r in all_records if "trial_id" in r]
        assert len(trial_records) >= 1, "At least one trial record must exist"
        entry = trial_records[0]
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

        # Check registry was updated.
        # Filter out non-trial records (e.g. the baseline reconciliation record).
        registry_path = rt_mod._TRIALS_REGISTRY
        all_records = [json.loads(l) for l in registry_path.read_text().strip().split("\n")]
        trial_records = [r for r in all_records if "trial_id" in r]
        trial_ids = [r["trial_id"] for r in trial_records]
        assert report["trial_id"] in trial_ids

        # Check complete entry
        complete_entries = [r for r in trial_records if r.get("status") == "complete"]
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

    def test_walkforward_enabled_produces_results(self, tmp_registry, minimal_pre_reg, tmp_path):
        """Harness with walkforward enabled must not crash and must populate windows counts.

        Regression test for the missing pair= keyword in run_walkforward() call.
        Uses a very short train/test window so the test stays fast on CI.
        """
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available in this environment")

        config_text = """
system:
  name: "test-wf"
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
    rebalance_mode: continuous
    rebalance_threshold: 0.20
  walkforward:
    enabled: true
    train_window_days: 252
    test_window_days: 126
    step_days: 126
"""
        config_path = tmp_path / "config_wf.yaml"
        config_path.write_text(config_text)

        report = run_trial(
            config_path=str(config_path),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        # Walkforward must have produced at least one window
        wf = report.get("walkforward", {})
        assert wf.get("windows_total") is not None, (
            "walkforward.windows_total must be populated when walkforward is enabled"
        )
        assert isinstance(wf["windows_total"], int), (
            f"windows_total must be int, got {type(wf['windows_total'])}"
        )
        assert wf["windows_total"] > 0, (
            f"Expected at least one walk-forward window, got {wf['windows_total']}"
        )
        assert wf.get("windows_beat_zero") is not None, (
            "walkforward.windows_beat_zero must be populated"
        )

    def test_equity_parquet_written(self, tmp_registry, minimal_config, minimal_pre_reg):
        """run_trial must write a _equity.parquet sibling alongside the JSON report."""
        data_path = Path("data/processed/EURUSD_daily.parquet")
        if not data_path.exists():
            pytest.skip("EURUSD daily data not available in this environment")


        report = run_trial(
            config_path=str(minimal_config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        # equity_curve_path must be present in the report
        assert "equity_curve_path" in report, "report must contain equity_curve_path"
        equity_path = Path(report["equity_curve_path"])
        assert equity_path.exists(), f"Equity parquet not found: {equity_path}"

        # Verify columns
        ec_df = pd.read_parquet(equity_path)
        assert "timestamp" in ec_df.columns
        assert "equity" in ec_df.columns
        assert "signal" in ec_df.columns

        # Row count must be positive
        assert len(ec_df) > 0
