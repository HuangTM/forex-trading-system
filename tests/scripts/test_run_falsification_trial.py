"""Tests for scripts/run_falsification_trial.py.

All backtest engine calls are mocked — no real I/O to parquet data files.
Fixtures use temporary files to isolate registry and cache writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_registry(tmp_path: Path) -> Path:
    """Temporary trials.jsonl path."""
    return tmp_path / "trials.jsonl"


@pytest.fixture()
def tmp_dominance_cache(tmp_path: Path) -> Path:
    """Temporary dominance_benchmarks.json path."""
    return tmp_path / "dominance_benchmarks.json"


@pytest.fixture()
def nht_rubric_path(tmp_path: Path) -> Path:
    """Write a minimal nht-rubric.yaml to a temp file.

    All fields required by NhtRubric.load_from_yaml must be present.
    Fixture was missing r5_window_percentile_gt and r5_spa_pvalue_gt which were
    made mandatory by the R5 remediation — this caused ConfigError on every test
    that loaded the rubric.  R5 fields added here; R5 triggers only fire when the
    pre-reg declares r5_active=True (not the case for these fixtures).
    """
    rubric = tmp_path / "nht-rubric.yaml"
    rubric.write_text(
        "r1_oos_sharpe_lt: 0.30\n"
        "r2_dsr_lt: 0.50\n"
        "r3_max_dd_gt: 0.25\n"
        "r5_permutation_pvalue_gt: 0.05\n"
        "r5_window_percentile_gt: 95.0\n"
        "r5_spa_pvalue_gt: 0.10\n"
        "r6_n_trades_lt: 30\n"
        "r6_n_oos_bars_lt: 252\n"
    )
    return rubric


@pytest.fixture()
def pre_reg_dir(tmp_path: Path) -> Path:
    """Create a minimal pre-reg markdown + sidecar for carry_baseline."""
    d = tmp_path / "pre_regs"
    d.mkdir()

    md = d / "carry_baseline.md"
    md.write_text(
        "# Pre-Registration: carry_baseline\n\n"
        "**Strategy ID:** carry\n"
        "**Pair:** EURUSD\n\n"
        "## Hypothesis\n\n"
        "Carry generates alpha.\n\n"
        "## Falsification Criteria\n\n"
        "- **carry_baseline-T1:** OOS Sharpe < 0.50\n\n"
        "kill_switch_threshold: 0.50\n"
        "gate_threshold: 0.50\n"
    )

    sidecar = d / "carry_baseline.triggers.yaml"
    sidecar.write_text(
        "strategy: carry\n"
        "pair: EURUSD\n"
        "oos_overlap: false\n"
        'oos_window_start: "2022-01-01"\n'
        'oos_window_end: "2023-12-31"\n'
        "triggers:\n"
        "  - label: carry_baseline-T1\n"
        "    metric: oos_sharpe\n"
        "    operator: '<'\n"
        "    threshold: 0.50\n"
        "    raw_text: OOS Sharpe < 0.50\n"
    )

    return d


@pytest.fixture()
def pre_reg_dir_wide(tmp_path: Path) -> Path:
    """Pre-reg with a wider OOS window (2020-01-01 to 2023-12-31 → ~1043 OOS bars).

    Used by test_passing_verdict_writes_complete_entry to produce genuinely strong
    DSR inputs (n_obs ~1043, SR_ann=1.0, N=2 → DSR ≈ 0.93 >> 0.50 threshold).
    """
    d = tmp_path / "pre_regs_wide"
    d.mkdir()

    md = d / "carry_baseline.md"
    md.write_text(
        "# Pre-Registration: carry_baseline\n\n"
        "**Strategy ID:** carry\n"
        "**Pair:** EURUSD\n\n"
        "## Hypothesis\n\n"
        "Carry generates alpha.\n\n"
        "## Falsification Criteria\n\n"
        "- **carry_baseline-T1:** OOS Sharpe < 0.50\n\n"
        "kill_switch_threshold: 0.50\n"
        "gate_threshold: 0.50\n"
    )

    sidecar = d / "carry_baseline.triggers.yaml"
    sidecar.write_text(
        "strategy: carry\n"
        "pair: EURUSD\n"
        "oos_overlap: false\n"
        'oos_window_start: "2020-01-01"\n'
        'oos_window_end: "2023-12-31"\n'
        "triggers:\n"
        "  - label: carry_baseline-T1\n"
        "    metric: oos_sharpe\n"
        "    operator: '<'\n"
        "    threshold: 0.50\n"
        "    raw_text: OOS Sharpe < 0.50\n"
    )

    return d


@pytest.fixture()
def pre_reg_with_dominance(tmp_path: Path) -> Path:
    """Pre-reg markdown + sidecar that includes a T5 dominance trigger."""
    d = tmp_path / "pre_regs_dom"
    d.mkdir()

    md = d / "carry_baseline.md"
    md.write_text(
        "# Pre-Registration: carry_baseline\n\n"
        "**Strategy ID:** carry\n"
        "**Pair:** EURUSD\n\n"
        "## Hypothesis\n\n"
        "Carry generates alpha.\n\n"
        "## Falsification Criteria\n\n"
        "- **carry_baseline-T1:** OOS Sharpe < 0.50\n"
        "- **carry_baseline-T5:** dominance trigger\n\n"
        "kill_switch_threshold: 0.50\n"
        "gate_threshold: 0.50\n"
    )

    sidecar = d / "carry_baseline.triggers.yaml"
    sidecar.write_text(
        "strategy: carry\n"
        "pair: EURUSD\n"
        "oos_overlap: false\n"
        'oos_window_start: "2022-01-01"\n'
        'oos_window_end: "2023-12-31"\n'
        "triggers:\n"
        "  - label: carry_baseline-T1\n"
        "    metric: oos_sharpe\n"
        "    operator: '<'\n"
        "    threshold: 0.50\n"
        "    raw_text: OOS Sharpe < 0.50\n"
        "  - label: carry_baseline-T5\n"
        "    metric: sharpe_minus_carry_fred_sharpe\n"
        "    operator: '<'\n"
        "    threshold: -0.20\n"
        "    raw_text: dominance trigger\n"
    )

    return d


def _make_backtest_result(
    sharpe: float = 0.75,
    max_dd: float = 0.10,
    n_trades: int = 50,
    n_bars: int = 504,
    start_date: str = "2022-01-01",
) -> MagicMock:
    """Build a mock BacktestResult with realistic equity curve."""
    rng = np.random.default_rng(42)
    dates = pd.date_range(start_date, periods=n_bars, freq="B")
    equity = 100_000.0 * (1 + rng.normal(0.0003, 0.01, n_bars)).cumprod()
    equity_series = pd.Series(equity, index=dates)
    signals = pd.Series(np.ones(n_bars), index=dates)
    trade_mock = MagicMock()
    result = MagicMock()
    result.equity_curve = equity_series
    result.signals = signals
    result.trade_log = [trade_mock] * n_trades
    return result


def _make_metrics(
    sharpe: float = 0.75,
    max_dd: float = 0.10,
    n_trades: int = 50,
) -> MagicMock:
    m = MagicMock()
    m.sharpe_ratio = sharpe
    m.max_drawdown = max_dd
    m.num_trades = n_trades
    m.total_return = 0.15
    m.annualized_return = 0.07
    m.sortino_ratio = 1.1
    m.win_rate = 0.55
    m.profit_factor = 1.4
    return m


# ---------------------------------------------------------------------------
# Test 1: Pre-reg loaded; sidecar parsed; NhtRubric loaded
# ---------------------------------------------------------------------------


def test_pre_reg_and_rubric_loaded(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """Verify that parse_pre_registration and NhtRubric.load_from_yaml are called."""
    pre_reg_path = pre_reg_dir / "carry_baseline.md"

    bt_result = _make_backtest_result()
    metrics_mock = _make_metrics()

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
        )

    assert result["strategy"] == "carry"
    assert result["oos_window_start"] == "2022-01-01"
    assert result["oos_window_end"] == "2023-12-31"
    assert "oos_sharpe" in result["metrics"]
    assert "dsr" in result


def _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm) -> None:
    """Configure common mock return values."""
    idx = pd.date_range("2020-01-01", periods=1200, freq="B")
    df = pd.DataFrame(
        {"open": 1.1, "high": 1.15, "low": 1.05, "close": 1.12, "volume": 1000.0,
         "atr_14": 0.01},
        index=idx,
    )
    mock_load.return_value = df
    mock_ind.return_value = df

    strategy_mock = MagicMock()
    strategy_mock.required_indicators.return_value = ["atr_14"]
    strategy_mock.generate_signals.return_value = pd.Series(1.0, index=idx)
    mock_strat.return_value = strategy_mock

    config_mock = MagicMock()
    config_mock.backtest.initial_capital = 100_000.0
    config_mock.backtest.entry_delay_bars = 1
    config_mock.backtest.rebalance_mode = "threshold"
    config_mock.backtest.rebalance_threshold = 0.05
    config_mock.data_dir = "data/processed_synthetic_phase0"
    mock_cfg.return_value = config_mock

    cm_mock = MagicMock()
    mock_cm.return_value = cm_mock


def _setup_mocks_wide(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm) -> None:
    """Configure mock return values with 2500 rows starting 2015-01-01.

    This produces ~1043 OOS bars when filtered to the 2020-01-01/2023-12-31 window,
    satisfying the NHT-directed n_obs requirement for the passing-verdict test.
    """
    idx = pd.date_range("2015-01-01", periods=2500, freq="B")
    df = pd.DataFrame(
        {"open": 1.1, "high": 1.15, "low": 1.05, "close": 1.12, "volume": 1000.0,
         "atr_14": 0.01},
        index=idx,
    )
    mock_load.return_value = df
    mock_ind.return_value = df

    strategy_mock = MagicMock()
    strategy_mock.required_indicators.return_value = ["atr_14"]
    strategy_mock.generate_signals.return_value = pd.Series(1.0, index=idx)
    mock_strat.return_value = strategy_mock

    config_mock = MagicMock()
    config_mock.backtest.initial_capital = 100_000.0
    config_mock.backtest.entry_delay_bars = 1
    config_mock.backtest.rebalance_mode = "threshold"
    config_mock.backtest.rebalance_threshold = 0.05
    config_mock.data_dir = "data/processed_synthetic_phase0"
    mock_cfg.return_value = config_mock

    cm_mock = MagicMock()
    mock_cm.return_value = cm_mock


# ---------------------------------------------------------------------------
# Test 2: Mock backtest → metrics computed → verdict computed → completion path
# ---------------------------------------------------------------------------


def test_passing_verdict_writes_complete_entry(
    pre_reg_dir_wide: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """When verdict passes with genuinely strong evidence, _append_trial is called.

    Input selection (NHT-directed, 2026-05-31):
      - SR_ann = 1.0  (modest, realistic)
      - n_obs  ≈ 1043 (dominant lever: OOS window 2020-01-01 to 2023-12-31 over
                       2500-row mock, filtered to business days in that range)
      - N = 2         (honest_n_deflation_denominator=1, so n_trials_total=2)
      → DSR ≈ 0.93 >> 0.50 threshold — genuinely strong, not fudged.

    Other gates: max_dd=0.10 < 0.25 (R3 pass); n_trades=60 >= 30 (R6 pass).
    """
    pre_reg_path = pre_reg_dir_wide / "carry_baseline.md"
    # n_bars=2500 starting 2015-01-01 covers OOS window 2020-2023 (~1043 bars).
    bt_result = _make_backtest_result(
        sharpe=1.0, max_dd=0.10, n_trades=60, n_bars=2500, start_date="2015-01-01"
    )
    metrics_mock = _make_metrics(sharpe=1.0, max_dd=0.10, n_trades=60)

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        # N=2: 1 prior trial + this trial → minimal multiple-comparisons penalty
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=1),
        patch("scripts.run_falsification_trial._append_trial") as mock_append,
        patch("scripts.run_falsification_trial.record_trial_rejection") as mock_reject,
    ):
        _setup_mocks_wide(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=False,
        )

    assert result["verdict"]["passed"] is True
    mock_append.assert_called_once()
    mock_reject.assert_not_called()

    # Verify the appended entry has expected fields.
    entry = mock_append.call_args[0][0]
    assert entry["status"] == "complete"
    assert entry["strategy"] == "carry"
    assert entry["oos"] is True


# ---------------------------------------------------------------------------
# Test 3: Mock backtest → rejection path called correctly
# ---------------------------------------------------------------------------


def test_failing_verdict_writes_rejected_entry(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """When verdict fails (OOS Sharpe below threshold), record_trial_rejection is called."""
    pre_reg_path = pre_reg_dir / "carry_baseline.md"
    # Sharpe 0.20 → below carry_baseline-T1 threshold of 0.50 → should fail.
    bt_result = _make_backtest_result(sharpe=0.20, max_dd=0.10, n_trades=60)
    metrics_mock = _make_metrics(sharpe=0.20, max_dd=0.10, n_trades=60)

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial") as mock_append,
        patch("scripts.run_falsification_trial.record_trial_rejection") as mock_reject,
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=False,
        )

    assert result["verdict"]["passed"] is False
    mock_reject.assert_called_once()
    mock_append.assert_not_called()

    kwargs = mock_reject.call_args
    assert kwargs[1]["registry"] == tmp_registry or kwargs[0][4] == tmp_registry


# ---------------------------------------------------------------------------
# Test 4: --dry-run does not write to registry
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """With dry_run=True, neither _append_trial nor record_trial_rejection is called."""
    pre_reg_path = pre_reg_dir / "carry_baseline.md"
    # Low sharpe → would normally reject.
    bt_result = _make_backtest_result(sharpe=0.10, max_dd=0.10, n_trades=60)
    metrics_mock = _make_metrics(sharpe=0.10, max_dd=0.10, n_trades=60)

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial") as mock_append,
        patch("scripts.run_falsification_trial.record_trial_rejection") as mock_reject,
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
        )

    assert result["dry_run"] is True
    mock_append.assert_not_called()
    mock_reject.assert_not_called()
    # Registry file should NOT exist (no writes).
    assert not tmp_registry.exists()


# ---------------------------------------------------------------------------
# Test 5a: Dominance benchmark — cache hit
# ---------------------------------------------------------------------------


def test_dominance_cache_hit(
    pre_reg_with_dominance: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_path: Path,
) -> None:
    """When dominance cache contains carry_fred Sharpe, no backtest is re-run."""
    pre_reg_path = pre_reg_with_dominance / "carry_baseline.md"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        json.dumps({"fred_carry_stripped|2022-01-01|2023-12-31": 0.72})
    )

    bt_result = _make_backtest_result(sharpe=0.80, max_dd=0.10, n_trades=60)
    metrics_mock = _make_metrics(sharpe=0.80, max_dd=0.10, n_trades=60)

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", cache_path),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result) as mock_bt,
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial"),
        patch("scripts.run_falsification_trial.record_trial_rejection"),
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
        )

    # Sharpe minus carry_fred: 0.80 - 0.72 = 0.08; T5 threshold is -0.20 → should pass T5.
    assert "sharpe_minus_carry_fred_sharpe" in result["metrics"]
    assert abs(result["metrics"]["sharpe_minus_carry_fred_sharpe"] - 0.08) < 0.01
    # run_backtest called only once (the candidate pair), NOT for carry_fred again.
    assert mock_bt.call_count == 1


# ---------------------------------------------------------------------------
# Test 5b: Dominance benchmark — cache miss triggers carry_fred run
# ---------------------------------------------------------------------------


def test_dominance_cache_miss_computes_benchmark(
    pre_reg_with_dominance: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_path: Path,
) -> None:
    """On cache miss, carry_fred is run to compute benchmark; result cached."""
    pre_reg_path = pre_reg_with_dominance / "carry_baseline.md"
    cache_path = tmp_path / "cache.json"
    # Cache is empty.

    candidate_result = _make_backtest_result(sharpe=0.80, max_dd=0.10, n_trades=60)
    carry_fred_result = _make_backtest_result(sharpe=0.70, max_dd=0.08, n_trades=45)
    candidate_metrics = _make_metrics(sharpe=0.80, max_dd=0.10, n_trades=60)
    carry_fred_metrics = _make_metrics(sharpe=0.70, max_dd=0.08, n_trades=45)

    call_counter = {"n": 0}

    def _bt_side_effect(*args, **kwargs):
        call_counter["n"] += 1
        # First call: candidate strategy; subsequent calls: carry_fred per pair.
        if call_counter["n"] == 1:
            return candidate_result
        return carry_fred_result

    def _calc_side_effect(eq, trades):
        if eq is candidate_result.equity_curve:
            return candidate_metrics
        return carry_fred_metrics

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", cache_path),
        patch("scripts.run_falsification_trial.run_backtest", side_effect=_bt_side_effect),
        patch("scripts.run_falsification_trial.calculate_metrics", side_effect=_calc_side_effect),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_cm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial"),
        patch("scripts.run_falsification_trial.record_trial_rejection"),
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_cm)
        from scripts.run_falsification_trial import run_falsification_trial

        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=False,
        )

    assert "sharpe_minus_carry_fred_sharpe" in result["metrics"]
    # Cache should now be written.
    assert cache_path.exists()
    cache = json.loads(cache_path.read_text())
    assert "fred_carry_stripped|2022-01-01|2023-12-31" in cache


# ---------------------------------------------------------------------------
# Test 6a: Missing sidecar → ConfigError
# ---------------------------------------------------------------------------


def test_missing_sidecar_raises_config_error(
    tmp_path: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
) -> None:
    """Pre-reg with no paired sidecar raises ConfigError — not a silent pass."""
    d = tmp_path / "pre_regs"
    d.mkdir()
    md = d / "mystery.md"
    md.write_text(
        "# Mystery\n\n"
        "**Strategy ID:** momentum\n"
        "**Pair:** EURUSD\n\n"
        "## Hypothesis\n\nSomething.\n\n"
        "kill_switch_threshold: 0.30\n"
    )
    # Sidecar intentionally NOT created.

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
    ):
        from scripts.run_falsification_trial import run_falsification_trial
        from forex_system.core.errors import ConfigError as CE

        with pytest.raises(CE, match="sidecar"):
            run_falsification_trial(
                pre_reg_path=md,
                config_path=tmp_path / "config.yaml",
                registry=tmp_registry,
                dry_run=True,
            )


# ---------------------------------------------------------------------------
# Test 6b: Missing kill_switch_threshold → ConfigError
# ---------------------------------------------------------------------------


def test_missing_kill_switch_threshold_raises(
    tmp_path: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
) -> None:
    """Pre-reg without kill_switch_threshold raises ConfigError during parse."""
    d = tmp_path / "pre_regs"
    d.mkdir()
    md = d / "nokillswitch.md"
    md.write_text(
        "# No Kill Switch\n\n"
        "**Strategy ID:** momentum\n"
        "**Pair:** EURUSD\n\n"
        "## Hypothesis\n\nSomething.\n\n"
        "# No kill_switch_threshold field here\n"
    )
    sidecar = d / "nokillswitch.triggers.yaml"
    sidecar.write_text(
        "strategy: momentum\n"
        "pair: EURUSD\n"
        "oos_overlap: false\n"
        'oos_window_start: "2022-01-01"\n'
        'oos_window_end: "2023-12-31"\n'
        "triggers: []\n"
    )

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
    ):
        from scripts.run_falsification_trial import run_falsification_trial
        from forex_system.core.errors import ConfigError as CE

        with pytest.raises(CE, match="kill_switch_threshold"):
            run_falsification_trial(
                pre_reg_path=md,
                config_path=tmp_path / "config.yaml",
                registry=tmp_registry,
                dry_run=True,
            )


# ---------------------------------------------------------------------------
# Test 3c.1.1: pair_resolved correctness via entry-point (bug-fix regression)
# ---------------------------------------------------------------------------


def test_loads_real_phase2_pre_reg_with_resolved_pairs() -> None:
    """Entry-point parses ma_crossover.md → pair_resolved == Phase-2 universe.

    Verifies that:
      1. kill_switch_threshold has no trailing backtick.
      2. pair_resolved expands sidecar ``pair: all`` to the three Phase-2 pairs.

    Backtest engine is NOT invoked — we only verify the parser output via the
    PreRegistrationSpec returned by parse_pre_registration.
    """
    from pathlib import Path as _Path
    repo_root = _Path(__file__).resolve().parent.parent.parent
    md_path = repo_root / "references/pre-registrations/ma_crossover.md"
    sidecar_path = repo_root / "references/pre-registrations/ma_crossover.triggers.yaml"

    if not md_path.exists():
        pytest.skip("ma_crossover.md not found in this environment")
    if not sidecar_path.exists():
        pytest.skip("ma_crossover.triggers.yaml not found in this environment")

    from forex_system.harness.preregistration import parse_pre_registration

    spec = parse_pre_registration(md_path, sidecar_path=sidecar_path)

    assert spec.kill_switch_threshold == "0.30", (
        f"Expected '0.30' (no trailing backtick) but got {spec.kill_switch_threshold!r}"
    )
    assert spec.pair_resolved == ("EURUSD", "USDJPY", "GBPUSD"), (
        f"Expected Phase-2 universe tuple but got {spec.pair_resolved!r}"
    )


# ---------------------------------------------------------------------------
# Wave-5 Round-2: cost_multiplier hook tests
# ---------------------------------------------------------------------------


def test_cost_multiplier_builds_scaled_model() -> None:
    """_build_scaled_cost_model multiplies all cost params by the given factor."""
    from unittest.mock import MagicMock
    from scripts.run_falsification_trial import _build_scaled_cost_model
    from forex_system.core.types import PairInfo
    from forex_system.costs.model import RealisticCostModel

    base_pair = PairInfo(
        symbol="EURUSD",
        pip_value=0.0001,
        spread_pips=1.0,
        slippage_pips=0.5,
        commission_pips=0.2,
        swap_long_pips_per_day=0.1,
        swap_short_pips_per_day=-0.3,
    )
    base_model = RealisticCostModel(pair_configs={"EURUSD": base_pair})

    with patch("scripts.run_falsification_trial._build_cost_model", return_value=base_model):
        result = _build_scaled_cost_model(
            config=MagicMock(),
            pair_symbol="EURUSD",
            cost_multiplier=3.0,
        )

    scaled = result.pairs["EURUSD"]
    assert abs(scaled.spread_pips - 3.0) < 1e-9, "spread_pips should be 3x"
    assert abs(scaled.slippage_pips - 1.5) < 1e-9, "slippage_pips should be 3x"
    assert abs(scaled.commission_pips - 0.6) < 1e-9, "commission_pips should be 3x"
    assert abs(scaled.swap_long_pips_per_day - 0.3) < 1e-9, "swap_long should be 3x"
    assert abs(scaled.swap_short_pips_per_day - (-0.9)) < 1e-9, "swap_short should be 3x"
    # pip_value is NOT a cost — must remain unchanged.
    assert scaled.pip_value == 0.0001, "pip_value must not be scaled"


def test_cost_multiplier_hook_passes_override_to_engine(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """When cost_multiplier != 1.0, _build_scaled_cost_model is called, not _build_cost_model."""
    from scripts.run_falsification_trial import run_falsification_trial as _rft
    from forex_system.core.types import PairInfo
    from forex_system.costs.model import RealisticCostModel

    pre_reg_path = pre_reg_dir / "carry_baseline.md"
    bt_result = _make_backtest_result(sharpe=0.10)
    metrics_mock = _make_metrics(sharpe=0.10)

    base_pair = PairInfo("EURUSD", 0.0001, 1.0, 0.5, 0.2, 0.1, -0.3)
    base_model = RealisticCostModel(pair_configs={"EURUSD": base_pair})

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model", return_value=base_model) as mock_bcm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial"),
        patch("scripts.run_falsification_trial.record_trial_rejection"),
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_bcm)
        result = _rft(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
            cost_multiplier=3.0,
        )

    # _build_cost_model must be called (once for the scaled-model build).
    assert mock_bcm.call_count >= 1
    # Result completes without error — cost-stress hook applied.
    assert "oos_sharpe" in result["metrics"]


def test_cost_multiplier_1x_does_not_invoke_scaled_model(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """When cost_multiplier == 1.0 (default), _build_scaled_cost_model is NOT called."""
    from scripts.run_falsification_trial import run_falsification_trial as _rft

    pre_reg_path = pre_reg_dir / "carry_baseline.md"
    bt_result = _make_backtest_result(sharpe=0.80)
    metrics_mock = _make_metrics(sharpe=0.80)

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", return_value=bt_result),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_bcm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial"),
        patch("scripts.run_falsification_trial.record_trial_rejection"),
        patch("scripts.run_falsification_trial._build_scaled_cost_model") as mock_scaled,
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_bcm)
        _rft(
            pre_reg_path=pre_reg_path,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
            cost_multiplier=1.0,  # default — no scaling
        )

    mock_scaled.assert_not_called()


# ---------------------------------------------------------------------------
# Wave-5 Round-2: pair_restrict hook tests
# ---------------------------------------------------------------------------


def test_pair_restrict_valid_subset_accepted(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_dominance_cache: Path,
    tmp_path: Path,
) -> None:
    """--pair-restrict with a valid subset of sidecar pairs runs only those pairs."""
    from scripts.run_falsification_trial import run_falsification_trial as _rft

    # Use a pre-reg with pair: all (3 pairs); restrict to EURUSD.
    d = tmp_path / "pr_multi"
    d.mkdir()
    md = d / "multi_strategy.md"
    md.write_text(
        "# Multi Strategy\n\n"
        "**Strategy ID:** carry\n"
        "**Pair:** EURUSD, USDJPY, GBPUSD\n\n"
        "## Hypothesis\n\nCarry generates alpha.\n\n"
        "## Falsification Criteria\n\n"
        "- **T1:** OOS Sharpe < 0.30\n\n"
        "kill_switch_threshold: 0.30\n"
    )
    sidecar = d / "multi_strategy.triggers.yaml"
    sidecar.write_text(
        "strategy: carry\n"
        "pair: all\n"
        "oos_overlap: false\n"
        'oos_window_start: "2022-01-01"\n'
        'oos_window_end: "2023-12-31"\n'
        "triggers:\n"
        "  - label: T1\n"
        "    metric: oos_sharpe\n"
        "    operator: '<'\n"
        "    threshold: 0.30\n"
        "    raw_text: OOS Sharpe < 0.30\n"
    )

    bt_result = _make_backtest_result(sharpe=0.80)
    metrics_mock = _make_metrics(sharpe=0.80)
    run_calls: list[str] = []

    def _bt_side_effect(*args, **kwargs):
        # Capture which pairs are run.
        run_calls.append(kwargs.get("pair", "unknown"))
        return bt_result

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
        patch("scripts.run_falsification_trial._DOMINANCE_CACHE_PATH", tmp_dominance_cache),
        patch("scripts.run_falsification_trial.run_backtest", side_effect=_bt_side_effect),
        patch("scripts.run_falsification_trial.calculate_metrics", return_value=metrics_mock),
        patch("scripts.run_falsification_trial.load_parquet") as mock_load,
        patch("scripts.run_falsification_trial.compute_indicators") as mock_ind,
        patch("scripts.run_falsification_trial.create_strategy") as mock_strat,
        patch("scripts.run_falsification_trial.load_config") as mock_cfg,
        patch("scripts.run_falsification_trial._build_cost_model") as mock_bcm,
        patch("scripts.run_falsification_trial._build_sizer", return_value=None),
        patch("scripts.run_falsification_trial.honest_n_deflation_denominator", return_value=5),
        patch("scripts.run_falsification_trial._append_trial"),
        patch("scripts.run_falsification_trial.record_trial_rejection"),
    ):
        _setup_mocks(mock_load, mock_ind, mock_strat, mock_cfg, mock_bcm)
        result = _rft(
            pre_reg_path=md,
            config_path=tmp_path / "config.yaml",
            registry=tmp_registry,
            dry_run=True,
            pair_restrict="EURUSD",
        )

    # Only EURUSD should have been run (not USDJPY or GBPUSD).
    assert run_calls == ["EURUSD"], f"Expected only EURUSD, got {run_calls}"
    assert "oos_sharpe" in result["metrics"]


def test_pair_restrict_unknown_pair_raises_config_error(
    pre_reg_dir: Path,
    nht_rubric_path: Path,
    tmp_registry: Path,
    tmp_path: Path,
) -> None:
    """--pair-restrict with a pair not in sidecar's pair_resolved raises ConfigError."""
    from scripts.run_falsification_trial import run_falsification_trial as _rft
    from forex_system.core.errors import ConfigError as CE

    pre_reg_path = pre_reg_dir / "carry_baseline.md"  # pair: EURUSD in sidecar

    with (
        patch("scripts.run_falsification_trial._NHT_RUBRIC_PATH", nht_rubric_path),
    ):
        with pytest.raises(CE, match="not in sidecar pair_resolved"):
            _rft(
                pre_reg_path=pre_reg_path,
                config_path=tmp_path / "config.yaml",
                registry=tmp_registry,
                dry_run=True,
                pair_restrict="AUDUSD",  # not in sidecar
            )
