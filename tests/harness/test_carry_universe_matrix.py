"""Tests for harness/carry_universe_matrix.py — STEP 2b joint return matrix.

Test coverage:
  (a) matrix is rectangular with correct shape
  (b) labels match columns exactly (label count == k, no gaps)
  (c) a known-droppable cell is logged + excluded with reason in dropped list
  (d) smoke run_r5_on_carry_universe on 2×2 subset returns valid p-values in [0,1]
  (e) returns are derived from equity_curve.pct_change() (net-of-cost, not gross)
  (f) integration test on real data/processed/ (2 variants × 2 pairs, fast)
  (g) window parameter slices the matrix correctly
  (h) empty matrix (k=0) raises ValueError
  (i) k < 2 in run_r5_on_carry_universe raises ValueError
  [C-1] _VARIANT_EXEC sizer params match committed config files (config-fidelity gate)
  [E-1] continuous vs discrete mode on same carry_momentum input produces materially
        different return series (numeric lock on F2 fix — not just a log claim)

Unit tests use synthetic OHLCV data and mock-out the data loader for speed.
Integration tests (marked with pytest.mark.integration) use REAL data/processed/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.core.types import BacktestResult
from forex_system.harness.carry_universe_matrix import (
    CARRY_PAIRS,
    CARRY_VARIANTS,
    DroppedCell,
    JointReturnMatrix,
    R5CarryResult,
    _VARIANT_EXEC,
    _drop_cell,
    build_joint_return_matrix,
    run_r5_on_carry_universe,
)

# ---------------------------------------------------------------------------
# Helpers — synthetic data factories
# ---------------------------------------------------------------------------

_SEED = 42
_N_BARS = 300  # Enough for ATR warm-up + meaningful returns


def _make_ohlcv(n: int = _N_BARS, seed: int = _SEED) -> pd.DataFrame:
    """Synthetic daily OHLCV for JPY pairs (close in realistic 100–160 range)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    rets = rng.normal(0.0002, 0.005, n)
    close = 120.0 * np.exp(np.cumsum(rets))
    daily_range = np.abs(rng.normal(0, 0.5, n))
    high = close + daily_range * 0.6
    low = close - daily_range * 0.4
    open_prices = np.roll(close, 1) + rng.normal(0, 0.2, n)
    open_prices[0] = 120.0
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))
    return pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": close, "volume": 1e6},
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


def _make_rate_data(n: int = _N_BARS, seed: int = _SEED) -> pd.DataFrame:
    """Synthetic rate_differentials DataFrame for all 6 JPY crosses."""
    rng = np.random.default_rng(seed + 1)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    cols = {
        "USDJPY": "USDJPY_diff",
        "EURJPY": "EURJPY_diff",
        "GBPJPY": "GBPJPY_diff",
        "AUDJPY": "AUDJPY_diff",
        "CADJPY": "CADJPY_diff",
        "NZDJPY": "NZDJPY_diff",
        # Also include full 12-pair universe for carry_fred cross-sectional z-score
        "AUDUSD": "AUDUSD_diff",
        "CADUSD": "CADUSD_diff",
        "EURGBP": "EURGBP_diff",
        "EURUSD": "EURUSD_diff",
        "GBPUSD": "GBPUSD_diff",
        "NZDUSD": "NZDUSD_diff",
        "USDCAD": "USDCAD_diff",
    }
    data = {}
    for _sym, col in cols.items():
        data[col] = rng.uniform(0.001, 0.04, n)
    return pd.DataFrame(data, index=pd.DatetimeIndex(dates, name="datetime"))


def _make_equity_curve(
    n: int = _N_BARS - 15, seed: int = _SEED, initial: float = 1_000_000.0
) -> pd.Series:
    """Synthetic equity curve (n daily bars)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-15", periods=n, freq="B")
    rets = rng.normal(0.0003, 0.005, n)
    equity = initial * np.exp(np.cumsum(rets))
    return pd.Series(equity, index=pd.DatetimeIndex(dates, name="datetime"))


def _stub_backtest_result(label: str, n: int = _N_BARS - 15, seed: int = _SEED) -> BacktestResult:
    """Build a minimal BacktestResult for a synthetic cell."""
    ec = _make_equity_curve(n=n, seed=seed)
    pair = label.split(":")[-1] if ":" in label else label
    return BacktestResult(
        equity_curve=ec,
        trade_log=[],
        signals=pd.Series(1.0, index=ec.index),
        parameters={},
        pair=pair,
        strategy_name=label,
        start_date=ec.index[0],
        end_date=ec.index[-1],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rate_data() -> pd.DataFrame:
    return _make_rate_data()


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    return _make_ohlcv()


# ---------------------------------------------------------------------------
# Unit tests — mock data loader and run_backtest to avoid filesystem I/O
# ---------------------------------------------------------------------------


class TestBuildJointReturnMatrixUnit:
    """Unit tests: mock load_parquet and run_backtest for isolation."""

    def _patch_cell(
        self,
        monkeypatch: pytest.MonkeyPatch,
        variants: list[str],
        pairs: list[str],
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        seed_offset: int = 0,
    ) -> None:
        """Patch load_parquet to return synthetic OHLCV and run_backtest to return
        a stub BacktestResult. All cells return valid equity curves."""
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            strategy_name = kwargs.get("strategy_name", "unknown")
            # Vary seed by label for non-identical cells
            seed = abs(hash(strategy_name)) % (2**31)
            return _stub_backtest_result(strategy_name, seed=seed)

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

    def test_rectangular_matrix_correct_shape(
        self, monkeypatch: pytest.MonkeyPatch, ohlcv: pd.DataFrame, rate_data: pd.DataFrame
    ) -> None:
        """(a) Matrix is rectangular with shape (T, k) where k = variants × pairs."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY"]
        self._patch_cell(monkeypatch, variants, pairs, ohlcv, rate_data)

        result = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        assert isinstance(result, JointReturnMatrix)
        assert result.R.ndim == 2
        assert result.k == len(variants) * len(pairs)
        assert result.T > 0
        assert result.R.shape == (result.T, result.k)
        assert result.R.dtype == np.float64

    def test_labels_match_columns(
        self, monkeypatch: pytest.MonkeyPatch, ohlcv: pd.DataFrame, rate_data: pd.DataFrame
    ) -> None:
        """(b) Labels list length == k, and each label is 'variant:pair'."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY", "GBPJPY"]
        self._patch_cell(monkeypatch, variants, pairs, ohlcv, rate_data)

        result = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        assert len(result.labels) == result.k
        expected_labels = [f"{v}:{p}" for v in variants for p in pairs]
        assert result.labels == expected_labels

    def test_dropped_cell_logged_and_excluded(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """(c) A cell that fails to build is logged at WARNING and returned in dropped list."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY"]
        call_count = [0]

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            strategy_name = kwargs.get("strategy_name", "unknown")
            call_count[0] += 1
            # Fail the first cell ("carry:USDJPY")
            if strategy_name == "carry:USDJPY":
                raise ValueError("synthetic failure for test")
            seed = abs(hash(strategy_name)) % (2**30)
            return _stub_backtest_result(strategy_name, seed=seed)

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

        import logging
        with caplog.at_level(logging.WARNING, logger="forex_system.harness.carry_universe_matrix"):
            result = build_joint_return_matrix(
                variants=variants,
                pairs=pairs,
                data_dir="data",
                rate_data=rate_data,
            )

        # Cell was dropped
        assert len(result.dropped) == 1
        dropped = result.dropped[0]
        assert dropped.label == "carry:USDJPY"
        assert dropped.variant == "carry"
        assert dropped.pair == "USDJPY"
        assert "synthetic failure" in dropped.reason

        # Remaining k = 3 (not 4)
        assert result.k == 3
        assert "carry:USDJPY" not in result.labels

        # WARNING was logged
        warning_events = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("carry:USDJPY" in r.getMessage() for r in warning_events), (
            "Expected a WARNING log mentioning the dropped cell label"
        )

    def test_returns_from_equity_curve_pct_change(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(e) Returns are pct_change() of equity_curve (net-of-cost), not gross price changes."""
        variants = ["carry"]
        pairs = ["USDJPY"]

        # Deterministic equity curve with known values
        equity = _make_equity_curve(n=100, seed=99)
        expected_returns = equity.pct_change().dropna()

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            return BacktestResult(
                equity_curve=equity,
                trade_log=[],
                signals=pd.Series(1.0, index=equity.index),
                parameters={},
                pair="USDJPY",
                strategy_name="carry:USDJPY",
                start_date=equity.index[0],
                end_date=equity.index[-1],
            )

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

        result = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        assert result.k == 1
        col_returns = result.R[:, 0]

        # The returned values must exactly match pct_change() of the equity curve
        assert len(col_returns) == len(expected_returns)
        np.testing.assert_allclose(col_returns, expected_returns.to_numpy(), rtol=1e-10)

    def test_window_slices_correctly(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(g) Window parameter restricts the common index to [start, end]."""
        variants = ["carry"]
        pairs = ["USDJPY", "EURJPY"]
        self._patch_cell(monkeypatch, variants, pairs, ohlcv, rate_data)

        result_full = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        # Slice to the middle 50% of the full date range
        mid = len(result_full.index) // 2
        start = str(result_full.index[mid // 2].date())
        end = str(result_full.index[mid + mid // 2].date())

        result_windowed = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
            window=(start, end),
        )

        assert result_windowed.T < result_full.T
        # All dates in windowed matrix are within [start, end]
        assert all(result_windowed.index >= pd.Timestamp(start))
        assert all(result_windowed.index <= pd.Timestamp(end))
        # Shape is still (T_window, k)
        assert result_windowed.R.shape == (result_windowed.T, result_windowed.k)

    def test_empty_matrix_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(h) k=0 (all cells dropped due to data-insufficiency) raises ValueError.

        A data-insufficiency ValueError from run_backtest is a legitimate drop reason.
        The builder must raise ValueError when k=0 after all legitimate drops.
        Note: CODE ERRORS (RuntimeError, KeyError, etc.) now propagate immediately
        rather than being caught — that is tested in test_code_error_raises_not_silently_dropped.
        """
        variants = ["carry"]
        pairs = ["USDJPY"]

        # Simulate a data-insufficiency error (equity curve too short — legitimate drop)
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )

        def _fail_data_insufficient(**kwargs: Any) -> BacktestResult:
            # Raise ValueError to simulate a data-insufficiency (e.g. too few bars)
            raise ValueError("simulated data-insufficiency — too few bars after warm-up")

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _fail_data_insufficient,
        )

        with pytest.raises(ValueError, match="all cells failed"):
            build_joint_return_matrix(
                variants=variants,
                pairs=pairs,
                data_dir="data",
                rate_data=rate_data,
            )

    def test_no_nan_in_matrix(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """Matrix R must be entirely finite (no NaN/Inf)."""
        variants = ["carry", "vol_target_carry_no_vol_scaling"]
        pairs = ["USDJPY", "EURJPY"]
        self._patch_cell(monkeypatch, variants, pairs, ohlcv, rate_data)

        result = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        assert np.all(np.isfinite(result.R)), "Matrix R must not contain NaN or Inf"

    def test_all_columns_share_index(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(a) All columns are aligned to the same common DatetimeIndex."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY"]
        self._patch_cell(monkeypatch, variants, pairs, ohlcv, rate_data)

        result = build_joint_return_matrix(
            variants=variants,
            pairs=pairs,
            data_dir="data",
            rate_data=rate_data,
        )

        # Shape: T rows, k columns; index has length T
        assert result.R.shape[0] == len(result.index)
        # No NaN after inner-join alignment
        assert not result.index.isna().any()


class TestRunR5OnCarryUniverseUnit:
    """Unit tests for run_r5_on_carry_universe."""

    def _patch_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        n_cells: int = 4,
        n_bars: int = 200,
    ) -> None:
        """Patch loader and engine; return per-call synthetic equity curves."""
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )

        call_n = [0]

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            call_n[0] += 1
            seed = call_n[0] * 7
            rng_local = np.random.default_rng(seed)
            ec = pd.Series(
                1_000_000.0 * np.exp(np.cumsum(rng_local.normal(0.0003, 0.005, n_bars))),
                index=pd.bdate_range("2020-01-01", periods=n_bars, freq="B"),
            )
            return BacktestResult(
                equity_curve=ec,
                trade_log=[],
                signals=pd.Series(1.0, index=ec.index),
                parameters={},
                pair="USDJPY",
                strategy_name=kwargs.get("strategy_name", "unknown"),
                start_date=ec.index[0],
                end_date=ec.index[-1],
            )

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

    def test_smoke_returns_valid_pvalues(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(d) Smoke 2×2: p-values are in [0, 1], result has correct types."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY"]
        self._patch_all(monkeypatch, ohlcv, rate_data)

        result = run_r5_on_carry_universe(
            variants=variants,
            pairs=pairs,
            master_seed=42,
            data_dir="data",
            rate_data=rate_data,
            B=50,  # Tiny B for speed — not a valid statistical run
        )

        assert isinstance(result, R5CarryResult)
        assert 0.0 <= result.spa_pvalue_consistent <= 1.0
        assert 0.0 <= result.spa_pvalue_lower <= 1.0
        assert 0.0 <= result.spa_pvalue_upper <= 1.0
        assert 0.0 <= result.white_rc_pvalue <= 1.0
        assert result.T > 0
        assert result.k == 4
        assert len(result.labels) == 4
        assert result.block_length_used >= 1
        assert result.B == 50

    def test_k_lt_2_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """(i) k < 2 after drops raises ValueError."""
        variants = ["carry"]
        pairs = ["USDJPY"]
        self._patch_all(monkeypatch, ohlcv, rate_data, n_cells=1)

        # With k=1 the SPA max-statistic is degenerate — must raise
        with pytest.raises(ValueError, match="k=1"):
            run_r5_on_carry_universe(
                variants=variants,
                pairs=pairs,
                master_seed=42,
                data_dir="data",
                rate_data=rate_data,
                B=10,
            )

    def test_dropped_cells_logged_in_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Dropped cells from build_joint_return_matrix appear in result.dropped."""
        variants = ["carry", "carry_fred"]
        pairs = ["USDJPY", "EURJPY"]

        call_count = [0]

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            call_count[0] += 1
            strategy_name = kwargs.get("strategy_name", "")
            # Drop carry:USDJPY
            if strategy_name == "carry:USDJPY":
                raise ValueError("deliberate drop")
            rng_local = np.random.default_rng(call_count[0])
            ec = pd.Series(
                1_000_000.0 * np.exp(np.cumsum(rng_local.normal(0.0003, 0.005, 200))),
                index=pd.bdate_range("2020-01-01", periods=200, freq="B"),
            )
            return BacktestResult(
                equity_curve=ec,
                trade_log=[],
                signals=pd.Series(1.0, index=ec.index),
                parameters={},
                pair="USDJPY",
                strategy_name=strategy_name,
                start_date=ec.index[0],
                end_date=ec.index[-1],
            )

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

        import logging
        with caplog.at_level(logging.WARNING, logger="forex_system.harness.carry_universe_matrix"):
            result = run_r5_on_carry_universe(
                variants=variants,
                pairs=pairs,
                master_seed=42,
                data_dir="data",
                rate_data=rate_data,
                B=20,
            )

        assert len(result.dropped) == 1
        assert result.dropped[0].label == "carry:USDJPY"
        assert result.k == 3  # 4 - 1 = 3


# ---------------------------------------------------------------------------
# Integration tests — use REAL data/processed/
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBuildJointReturnMatrixIntegration:
    """Integration tests that read real data/processed/ files.

    Scoped to the minimal (2 variants × 2 pairs) subset to keep runtime fast.
    """

    _REAL_DATA_DIR = "data"
    _REAL_RATE_DATA_PATH = "data/rates/rate_differentials.parquet"

    def test_real_data_builds_matrix(self) -> None:
        """Integration: 2 variants × 2 JPY crosses builds a valid matrix from real data."""
        real_rate_data_path = Path(self._REAL_DATA_DIR) / "rates" / "rate_differentials.parquet"
        if not real_rate_data_path.exists():
            pytest.skip("rate_differentials.parquet not found — skipping integration test")

        for pair in ("USDJPY", "EURJPY"):
            p = Path(self._REAL_DATA_DIR) / "processed" / f"{pair}_daily.parquet"
            if not p.exists():
                pytest.skip(f"{pair}_daily.parquet not found — skipping integration test")

        result = build_joint_return_matrix(
            variants=["carry", "vol_target_carry_no_vol_scaling"],
            pairs=["USDJPY", "EURJPY"],
            data_dir=self._REAL_DATA_DIR,
            rate_data_path=self._REAL_RATE_DATA_PATH,
        )

        # Shape assertions: 2 variants × 2 pairs = up to 4 cells; all should build
        assert result.k == 4
        assert result.T > 500  # at least 2 years of trading days
        assert result.R.shape == (result.T, result.k)
        assert np.all(np.isfinite(result.R))

        # Labels correct
        assert len(result.labels) == result.k
        for label in result.labels:
            assert ":" in label
            variant, pair = label.split(":", 1)
            assert variant in ("carry", "vol_target_carry_no_vol_scaling")
            assert pair in ("USDJPY", "EURJPY")

    def test_real_data_returns_from_equity_curve(self) -> None:
        """Integration: verify returns are pct_change()-derived (net-of-cost check)."""
        real_rate_data_path = Path(self._REAL_DATA_DIR) / "rates" / "rate_differentials.parquet"
        if not real_rate_data_path.exists():
            pytest.skip("rate_differentials.parquet not found")

        for pair in ("USDJPY",):
            p = Path(self._REAL_DATA_DIR) / "processed" / f"{pair}_daily.parquet"
            if not p.exists():
                pytest.skip(f"{pair}_daily.parquet not found")

        # Intercept run_backtest to capture its equity_curve output
        captured_equity: dict[str, pd.Series] = {}
        original_run_backtest = run_backtest

        def _capturing_run_backtest(**kwargs: Any) -> BacktestResult:
            result = original_run_backtest(**kwargs)
            captured_equity[kwargs.get("strategy_name", "?")] = result.equity_curve
            return result

        import forex_system.harness.carry_universe_matrix as cmod
        original = cmod.run_backtest
        cmod.run_backtest = _capturing_run_backtest
        try:
            matrix = build_joint_return_matrix(
                variants=["carry"],
                pairs=["USDJPY"],
                data_dir=self._REAL_DATA_DIR,
                rate_data_path=self._REAL_RATE_DATA_PATH,
            )
        finally:
            cmod.run_backtest = original

        assert matrix.k >= 1
        # Compare matrix column to pct_change() of captured equity_curve.
        # Both guards are hard assertions — a vacuous pass means the test is broken.
        assert "carry:USDJPY" in captured_equity, (
            "Intercept did not capture equity_curve for carry:USDJPY — check patching"
        )
        ec = captured_equity["carry:USDJPY"].dropna()
        expected = ec.pct_change().dropna()
        common = matrix.index.intersection(expected.index)
        assert len(common) > 0, (
            "No common dates between matrix index and carry:USDJPY pct_change() — "
            "inner-join alignment or equity_curve index is wrong"
        )
        col_idx = matrix.labels.index("carry:USDJPY")
        matrix_rets = pd.Series(matrix.R[:, col_idx], index=matrix.index)
        np.testing.assert_allclose(
            matrix_rets.reindex(common).to_numpy(),
            expected.reindex(common).to_numpy(),
            rtol=1e-10,
            err_msg="Matrix returns must equal equity_curve.pct_change()",
        )

    def test_real_data_smoke_r5(self) -> None:
        """Integration smoke: run_r5_on_carry_universe 2×2 returns valid p-values."""
        real_rate_data_path = Path(self._REAL_DATA_DIR) / "rates" / "rate_differentials.parquet"
        if not real_rate_data_path.exists():
            pytest.skip("rate_differentials.parquet not found")

        for pair in ("USDJPY", "EURJPY"):
            p = Path(self._REAL_DATA_DIR) / "processed" / f"{pair}_daily.parquet"
            if not p.exists():
                pytest.skip(f"{pair}_daily.parquet not found")

        result = run_r5_on_carry_universe(
            variants=["carry", "vol_target_carry_no_vol_scaling"],
            pairs=["USDJPY", "EURJPY"],
            master_seed=42,
            data_dir=self._REAL_DATA_DIR,
            rate_data_path=self._REAL_RATE_DATA_PATH,
            B=100,  # Tiny B for CI speed — not a valid statistical run
        )

        assert isinstance(result, R5CarryResult)
        assert 0.0 <= result.spa_pvalue_consistent <= 1.0
        assert 0.0 <= result.white_rc_pvalue <= 1.0
        assert result.T > 200
        assert result.k == 4  # 2 variants × 2 pairs, all succeed
        assert result.block_length_used >= 1


# ---------------------------------------------------------------------------
# _drop_cell: unit test for the helper
# ---------------------------------------------------------------------------


class TestDropCell:
    def test_drop_cell_appends_and_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """_drop_cell appends a DroppedCell and logs at WARNING."""
        import logging
        dropped: list[DroppedCell] = []

        with caplog.at_level(logging.WARNING, logger="forex_system.harness.carry_universe_matrix"):
            _drop_cell(dropped, "carry:USDJPY", "carry", "USDJPY", "test reason")

        assert len(dropped) == 1
        assert dropped[0].label == "carry:USDJPY"
        assert dropped[0].variant == "carry"
        assert dropped[0].pair == "USDJPY"
        assert "test reason" in dropped[0].reason

        warning_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("carry:USDJPY" in m for m in warning_msgs)


# ---------------------------------------------------------------------------
# F3 tests: ALL 6 variants must BUILD (not silently drop) and each must run
# in the CORRECT mode/sizer. These tests are the ones that F1/F2 would have
# caught — they fail if any variant is silently dropped or runs wrong-mode.
# ---------------------------------------------------------------------------


class TestVariantExecConfigTable:
    """Validate _VARIANT_EXEC table coverage and mode assignments."""

    def test_all_6_variants_registered_in_exec_table(self) -> None:
        """Every variant in CARRY_VARIANTS must have an entry in _VARIANT_EXEC."""
        for variant in CARRY_VARIANTS:
            assert variant in _VARIANT_EXEC, (
                f"Variant '{variant}' is missing from _VARIANT_EXEC. "
                "Add an explicit rebalance_mode + sizer_type entry."
            )

    def test_carry_momentum_is_continuous_continuous_sizer(self) -> None:
        """carry_momentum must be continuous + ContinuousSizer (carry_momentum_portfolio.yaml)."""
        cfg = _VARIANT_EXEC["carry_momentum"]
        assert cfg.rebalance_mode == "continuous", (
            f"carry_momentum rebalance_mode must be 'continuous', got '{cfg.rebalance_mode}'"
        )
        assert cfg.sizer_type == "continuous", (
            f"carry_momentum sizer_type must be 'continuous', got '{cfg.sizer_type}'"
        )

    def test_vol_target_carry_is_continuous_vol_target_sizer(self) -> None:
        """vol_target_carry must be continuous + VolTargetSizer (vol_target_carry.yaml)."""
        cfg = _VARIANT_EXEC["vol_target_carry"]
        assert cfg.rebalance_mode == "continuous"
        assert cfg.sizer_type == "vol_target"

    def test_fred_carry_stripped_is_discrete_no_sizer(self) -> None:
        """fred_carry_stripped must be discrete + no sizer (pure rate-differential carry)."""
        cfg = _VARIANT_EXEC["fred_carry_stripped"]
        assert cfg.rebalance_mode == "discrete"
        assert cfg.sizer_type == "none"

    def test_discrete_variants_have_no_sizer(self) -> None:
        """All discrete variants must have sizer_type='none'."""
        discrete_variants = [v for v, c in _VARIANT_EXEC.items() if c.rebalance_mode == "discrete"]
        for v in discrete_variants:
            cfg = _VARIANT_EXEC[v]
            assert cfg.sizer_type == "none", (
                f"Discrete variant '{v}' must have sizer_type='none', "
                f"got '{cfg.sizer_type}'"
            )


class TestAllVariantsBuildUnit:
    """F3 (unit): ALL 6 variants must BUILD (none silently dropped).

    These tests mock load_parquet and run_backtest so they are fast and
    don't need real data files. They test that the cell-build plumbing
    correctly routes through _build_cell without hitting a code error
    (the F1 atr_14 KeyError or the F2 wrong-mode path).
    """

    def _patch_for_variant(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        n_bars: int = 200,
    ) -> None:
        """Patch load_parquet and run_backtest for all-variant testing."""
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )

        call_n = [0]

        def _mock_run_backtest(**kwargs: Any) -> BacktestResult:
            call_n[0] += 1
            rng_local = np.random.default_rng(call_n[0] * 13)
            ec = pd.Series(
                1_000_000.0 * np.exp(np.cumsum(rng_local.normal(0.0003, 0.005, n_bars))),
                index=pd.bdate_range("2020-01-01", periods=n_bars, freq="B"),
            )
            return BacktestResult(
                equity_curve=ec,
                trade_log=[],
                signals=pd.Series(1.0, index=ec.index),
                parameters={},
                pair=kwargs.get("pair", "USDJPY"),
                strategy_name=kwargs.get("strategy_name", "unknown"),
                start_date=ec.index[0],
                end_date=ec.index[-1],
            )

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _mock_run_backtest,
        )

    def test_fred_carry_stripped_builds_not_dropped(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """F1 regression: fred_carry_stripped cells MUST build — never dropped by atr_14 KeyError.

        fred_carry_stripped.required_indicators() == [] so dropna(subset=['atr_14'])
        must NOT be called. If this test fails, F1 has regressed.
        """
        # Rate data in _diff format for fred_carry_stripped
        rate_data_diff = _make_rate_data()  # has _diff suffix columns

        self._patch_for_variant(monkeypatch, ohlcv, rate_data_diff)

        result = build_joint_return_matrix(
            variants=["fred_carry_stripped"],
            pairs=["USDJPY", "EURJPY"],
            data_dir="data",
            rate_data=rate_data_diff,
        )

        # CRITICAL: no fred_carry_stripped cell must be dropped
        dropped_variants = {d.variant for d in result.dropped}
        assert "fred_carry_stripped" not in dropped_variants, (
            f"fred_carry_stripped cells were DROPPED — F1 regression! "
            f"Dropped: {[(d.label, d.reason, d.exc_type) for d in result.dropped]}"
        )
        assert result.k == 2, (
            f"Expected k=2 (1 variant × 2 pairs), got k={result.k}. "
            f"Dropped: {[(d.label, d.reason) for d in result.dropped]}"
        )

    def test_carry_momentum_builds_not_dropped(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """carry_momentum cells must build — none dropped."""
        self._patch_for_variant(monkeypatch, ohlcv, rate_data)

        result = build_joint_return_matrix(
            variants=["carry_momentum"],
            pairs=["USDJPY", "EURJPY"],
            data_dir="data",
            rate_data=rate_data,
        )

        dropped_variants = {d.variant for d in result.dropped}
        assert "carry_momentum" not in dropped_variants, (
            f"carry_momentum cells were dropped. "
            f"Dropped: {[(d.label, d.reason, d.exc_type) for d in result.dropped]}"
        )
        assert result.k == 2

    def test_all_6_variants_build_1_pair(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """ALL 6 variants must build for USDJPY — none silently dropped.

        This is the key invariant: the FWER family is exhaustive. A whole variant
        silently dropping is always a code error, never a legitimate data gap for USDJPY.
        """
        rate_data_diff = _make_rate_data()  # diff-suffix for fred/carry_fred

        self._patch_for_variant(monkeypatch, ohlcv, rate_data_diff)

        result = build_joint_return_matrix(
            variants=list(CARRY_VARIANTS),
            pairs=["USDJPY"],
            data_dir="data",
            rate_data=rate_data_diff,
        )

        dropped_by_variant: dict[str, list[str]] = {}
        for dc in result.dropped:
            dropped_by_variant.setdefault(dc.variant, []).append(dc.reason)

        # No variant should be wholly absent from the result
        built_variants = {label.split(":")[0] for label in result.labels}
        for variant in CARRY_VARIANTS:
            assert variant in built_variants, (
                f"Variant '{variant}' is WHOLLY ABSENT from the matrix — "
                f"a code error silently dropped all its cells. "
                f"Dropped reasons: {dropped_by_variant.get(variant, [])}"
            )

        assert result.k == len(CARRY_VARIANTS), (
            f"Expected k={len(CARRY_VARIANTS)} (all 6 variants × 1 pair), "
            f"got k={result.k}. Dropped: {[(d.label, d.reason) for d in result.dropped]}"
        )

    def test_carry_momentum_cell_ok_log_shows_continuous(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """F2 regression: carry_momentum cell_ok log must show rebalance_mode=continuous.

        If the cell_ok event shows rebalance_mode=discrete, F2 has regressed.
        """
        import json
        import logging

        self._patch_for_variant(monkeypatch, ohlcv, rate_data)

        with caplog.at_level(logging.INFO, logger="forex_system.harness.carry_universe_matrix"):
            result = build_joint_return_matrix(
                variants=["carry_momentum"],
                pairs=["USDJPY"],
                data_dir="data",
                rate_data=rate_data,
            )

        assert result.k == 1, f"carry_momentum:USDJPY must build. Dropped: {result.dropped}"

        # Find the cell_ok log for carry_momentum:USDJPY
        cell_ok_logs = []
        for record in caplog.records:
            try:
                entry = json.loads(record.getMessage())
                if entry.get("event") == "carry_matrix.cell_ok" and entry.get("variant") == "carry_momentum":
                    cell_ok_logs.append(entry)
            except (json.JSONDecodeError, AttributeError):
                pass

        assert len(cell_ok_logs) >= 1, (
            "No carry_matrix.cell_ok log found for carry_momentum — check _log call"
        )
        for log_entry in cell_ok_logs:
            assert log_entry.get("rebalance_mode") == "continuous", (
                f"carry_momentum cell_ok shows rebalance_mode={log_entry.get('rebalance_mode')!r} "
                f"— expected 'continuous'. F2 regression."
            )
            assert log_entry.get("sizer_type") == "continuous", (
                f"carry_momentum cell_ok shows sizer_type={log_entry.get('sizer_type')!r} "
                f"— expected 'continuous'. F2 regression."
            )

    def test_code_error_raises_not_silently_dropped(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """F4 regression: a CODE ERROR (e.g. KeyError) must RAISE, not silently drop.

        A KeyError in _build_cell must propagate out of build_joint_return_matrix,
        not be swallowed by a broad except Exception and silently recorded as a
        dropped cell. This is the failure mode that masked F1.
        """
        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.load_parquet",
            lambda pair, tf, data_dir, **kw: ohlcv,
        )

        # Inject a KeyError from run_backtest (simulates a code bug, not a data gap)
        def _raise_key_error(**kwargs: Any) -> BacktestResult:
            raise KeyError("simulated_code_bug_column")

        monkeypatch.setattr(
            "forex_system.harness.carry_universe_matrix.run_backtest",
            _raise_key_error,
        )

        # Must raise, not silently drop
        with pytest.raises(KeyError, match="simulated_code_bug_column"):
            build_joint_return_matrix(
                variants=["carry"],
                pairs=["USDJPY"],
                data_dir="data",
                rate_data=rate_data,
            )


@pytest.mark.integration
class TestAllVariantsBuildIntegration:
    """F3 (integration): ALL 6 variants × 6 pairs on real data/processed/.

    Verifies the full 36-cell universe (or the largest feasible subset given
    available data files). Asserts no variant is wholly absent from the result.
    Asserts carry_momentum runs continuous mode and fred_carry_stripped builds.
    """

    _REAL_DATA_DIR = "data"
    _REAL_RATE_DATA_PATH = "data/rates/rate_differentials.parquet"

    @classmethod
    def _check_data_available(cls) -> None:
        """Skip integration test if required data files are missing."""
        rate_path = Path(cls._REAL_DATA_DIR) / "rates" / "rate_differentials.parquet"
        if not rate_path.exists():
            pytest.skip("rate_differentials.parquet not found — skipping integration test")

        # Need at least one pair for each variant to run
        pair_files_found = []
        for pair in CARRY_PAIRS:
            p = Path(cls._REAL_DATA_DIR) / "processed" / f"{pair}_daily.parquet"
            if p.exists():
                pair_files_found.append(pair)

        if not pair_files_found:
            pytest.skip("No pair parquet files found in data/processed/ — skipping integration test")

    def test_all_6_variants_build_on_real_data(self) -> None:
        """Full 6-variant universe on all available real pairs — no variant wholly absent.

        This is the integration-level F1/F2 regression gate. It fails if:
          - fred_carry_stripped is wholly dropped (atr_14 KeyError regression = F1)
          - carry_momentum whole-variant drop for any code error (F2 regression)
          - Any variant is wholly absent from the matrix
        """
        self._check_data_available()

        # Use whatever pairs have data files on disk
        available_pairs = [
            pair for pair in CARRY_PAIRS
            if (Path(self._REAL_DATA_DIR) / "processed" / f"{pair}_daily.parquet").exists()
        ]

        result = build_joint_return_matrix(
            variants=list(CARRY_VARIANTS),
            pairs=available_pairs,
            data_dir=self._REAL_DATA_DIR,
            rate_data_path=self._REAL_RATE_DATA_PATH,
        )

        # Check no variant is wholly absent
        built_variants = {label.split(":")[0] for label in result.labels}
        dropped_by_variant: dict[str, list[tuple[str, str]]] = {}
        for dc in result.dropped:
            dropped_by_variant.setdefault(dc.variant, []).append((dc.reason, dc.category))

        for variant in CARRY_VARIANTS:
            assert variant in built_variants, (
                f"Variant '{variant}' WHOLLY ABSENT from real-data matrix — code error. "
                f"Dropped entries: {dropped_by_variant.get(variant, [])}. "
                f"Matrix labels: {result.labels}"
            )

        # Basic sanity: matrix must be rectangular and finite
        assert result.T > 200, f"T={result.T} too small — at least 1 year expected"
        assert np.all(np.isfinite(result.R)), "Matrix R must be finite after alignment"

        # No code-error drops anywhere
        code_error_drops = [d for d in result.dropped if d.category == "code-error"]
        assert not code_error_drops, (
            f"Code-error drops detected — these should raise, not be swallowed: "
            f"{[(d.label, d.reason, d.exc_type) for d in code_error_drops]}"
        )


# ---------------------------------------------------------------------------
# C-1: Config-fidelity tests — _VARIANT_EXEC sizer params match committed configs
# ---------------------------------------------------------------------------


class TestVariantExecConfigMatchesCommittedConfig:
    """C-1: Assert _VARIANT_EXEC sizer params equal the committed YAML config values.

    These tests READ the actual config files (not hardcoded expected values) so that
    future config drift between the config file and _VARIANT_EXEC is caught automatically.
    A failure here means someone updated the YAML but forgot to update _VARIANT_EXEC
    (or vice versa), which would corrupt the R5 kill-test return series.
    """

    @staticmethod
    def _load_yaml(path: str) -> dict:
        """Load a YAML config file. Skips the test if the file doesn't exist."""
        import yaml
        p = Path(path)
        if not p.exists():
            pytest.skip(f"Config file not found: {path} — cannot verify config fidelity")
        with open(p) as f:
            return yaml.safe_load(f)

    def test_carry_momentum_risk_per_trade_matches_config(self) -> None:
        """C-1: carry_momentum risk_per_trade in _VARIANT_EXEC must equal config value.

        Authority: config/carry_momentum_portfolio.yaml:backtest.position_sizing.risk_per_trade
        The runner script (scripts/run_carry_momentum.py) uses 0.02 for an exploratory sweep
        and is NOT the authority. The committed config is.
        """
        raw = self._load_yaml("config/carry_momentum_portfolio.yaml")
        config_value = raw["backtest"]["position_sizing"]["risk_per_trade"]

        exec_cfg = _VARIANT_EXEC["carry_momentum"]
        assert exec_cfg.risk_per_trade == pytest.approx(config_value), (
            f"_VARIANT_EXEC['carry_momentum'].risk_per_trade = {exec_cfg.risk_per_trade!r} "
            f"but config/carry_momentum_portfolio.yaml specifies {config_value!r}. "
            f"Update _VARIANT_EXEC to match the committed config (authority for R5)."
        )

    def test_carry_momentum_stop_loss_atr_multiple_matches_config(self) -> None:
        """C-1: carry_momentum stop_loss_atr_multiple in _VARIANT_EXEC must equal config value."""
        raw = self._load_yaml("config/carry_momentum_portfolio.yaml")
        config_value = raw["backtest"]["position_sizing"]["stop_loss_atr_multiple"]

        exec_cfg = _VARIANT_EXEC["carry_momentum"]
        assert exec_cfg.stop_loss_atr_multiple == pytest.approx(config_value), (
            f"_VARIANT_EXEC['carry_momentum'].stop_loss_atr_multiple = "
            f"{exec_cfg.stop_loss_atr_multiple!r} but config specifies {config_value!r}."
        )

    def test_vol_target_carry_sizer_params_match_config(self) -> None:
        """C-1: vol_target_carry sizer params in _VARIANT_EXEC must equal config values.

        Authority: config/vol_target_carry.yaml:backtest.position_sizing.*
        """
        raw = self._load_yaml("config/vol_target_carry.yaml")
        ps = raw["backtest"]["position_sizing"]

        exec_cfg = _VARIANT_EXEC["vol_target_carry"]

        assert exec_cfg.leverage_cap == pytest.approx(ps["leverage_cap"]), (
            f"leverage_cap mismatch: _VARIANT_EXEC={exec_cfg.leverage_cap!r}, "
            f"config={ps['leverage_cap']!r}"
        )
        assert exec_cfg.max_order_units == pytest.approx(ps["max_order_units"]), (
            f"max_order_units mismatch: _VARIANT_EXEC={exec_cfg.max_order_units!r}, "
            f"config={ps['max_order_units']!r}"
        )
        assert exec_cfg.min_order_size == pytest.approx(ps["min_order_size"]), (
            f"min_order_size mismatch: _VARIANT_EXEC={exec_cfg.min_order_size!r}, "
            f"config={ps['min_order_size']!r}"
        )

    def test_carry_fred_rebalance_threshold_matches_config(self) -> None:
        """C-1: carry + carry_fred rebalance_threshold must equal carry_fred.yaml value."""
        raw = self._load_yaml("config/carry_fred.yaml")
        config_threshold = raw["backtest"]["execution"]["rebalance_threshold"]

        for variant in ("carry", "carry_fred"):
            exec_cfg = _VARIANT_EXEC[variant]
            assert exec_cfg.rebalance_threshold == pytest.approx(config_threshold), (
                f"_VARIANT_EXEC['{variant}'].rebalance_threshold = "
                f"{exec_cfg.rebalance_threshold!r} but carry_fred.yaml specifies "
                f"{config_threshold!r}."
            )

    def test_vol_target_carry_rebalance_threshold_matches_config(self) -> None:
        """C-1: vol_target_carry rebalance_threshold must equal config value."""
        raw = self._load_yaml("config/vol_target_carry.yaml")
        config_threshold = raw["backtest"]["execution"]["rebalance_threshold"]

        exec_cfg = _VARIANT_EXEC["vol_target_carry"]
        assert exec_cfg.rebalance_threshold == pytest.approx(config_threshold), (
            f"_VARIANT_EXEC['vol_target_carry'].rebalance_threshold = "
            f"{exec_cfg.rebalance_threshold!r} but config specifies {config_threshold!r}."
        )

    def test_all_continuous_variants_have_sizer_params(self) -> None:
        """C-1: Every 'continuous' sizer variant must have non-None sizer params in _VARIANT_EXEC."""
        for variant, cfg in _VARIANT_EXEC.items():
            if cfg.sizer_type == "continuous":
                assert cfg.risk_per_trade is not None, (
                    f"_VARIANT_EXEC['{variant}'].risk_per_trade is None — "
                    f"must be sourced from committed config."
                )
                assert cfg.stop_loss_atr_multiple is not None, (
                    f"_VARIANT_EXEC['{variant}'].stop_loss_atr_multiple is None."
                )
            elif cfg.sizer_type == "vol_target":
                assert cfg.leverage_cap is not None, (
                    f"_VARIANT_EXEC['{variant}'].leverage_cap is None."
                )
                assert cfg.max_order_units is not None, (
                    f"_VARIANT_EXEC['{variant}'].max_order_units is None."
                )
                assert cfg.min_order_size is not None, (
                    f"_VARIANT_EXEC['{variant}'].min_order_size is None."
                )


# ---------------------------------------------------------------------------
# E-1: Mode-fidelity test — continuous vs discrete produce materially different returns
# ---------------------------------------------------------------------------


class TestCarryMomentumModeFidelityNumeric:
    """E-1: Lock the F2 fix with numeric evidence.

    Asserts that running carry_momentum in CONTINUOUS mode vs DISCRETE mode on the
    SAME input produces return series that differ materially (not just in a log claim).

    The mechanism:
      - Discrete mode: positions = np.sign(delayed_signal), collapsing 0.58 → 1.0
      - Continuous mode: positions scale with signal magnitude (0.58 stays 0.58)
    If both modes produce the same returns, the sizer is being ignored or
    continuous mode is accidentally collapsing the signal — a regression.
    """

    def test_continuous_and_discrete_returns_differ_materially(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ohlcv: pd.DataFrame,
        rate_data: pd.DataFrame,
    ) -> None:
        """E-1: Same carry_momentum input, continuous vs discrete → materially different returns.

        Uses a REAL run_backtest call (not mocked) so the engine code path is exercised.
        The ohlcv fixture is synthetic but the signal generation is real.
        """
        from forex_system.backtest.engine import run_backtest as real_run_backtest
        from forex_system.costs.model import RealisticCostModel
        from forex_system.features.registry import compute_indicators
        from forex_system.harness.carry_universe_matrix import _DEFAULT_PAIR_INFO
        from forex_system.sizing.continuous import ContinuousSizer
        from forex_system.strategies.registry import create_strategy

        pair = "USDJPY"
        variant = "carry_momentum"

        # Use the rate_data fixture (synthetic but valid format)
        # The fixture produces "USDJPY_diff" columns; rename to plain for carry_momentum
        rd_plain = rate_data.rename(
            columns={c: c.replace("_diff", "") for c in rate_data.columns if c.endswith("_diff")}
        )

        # Build strategy and enrich data
        strategy = create_strategy(
            variant,
            {"pair": pair},
            rate_data=rd_plain,
        )
        required = strategy.required_indicators()
        enriched = compute_indicators(ohlcv, required)
        if required:
            enriched = enriched.dropna(subset=required)

        signals = strategy.generate_signals(enriched)
        assert len(signals) > 0, "No signals generated — check synthetic data"

        # Verify the signal is actually magnitude-bearing (not all ±1 or 0)
        # If the signal collapsed to {-1, 0, 1} the test would not distinguish modes
        unique_vals = signals.dropna().unique()
        non_binary_vals = [v for v in unique_vals if v not in (-1.0, 0.0, 1.0)]
        assert len(non_binary_vals) > 0, (
            "carry_momentum signal collapsed to {-1,0,1} on synthetic data — "
            "E-1 test cannot distinguish continuous from discrete on a binary signal. "
            "Check the synthetic OHLCV / rate_data fixture."
        )

        pair_info = _DEFAULT_PAIR_INFO[pair]
        cost_model = RealisticCostModel(pair_configs={pair: pair_info})

        # Run CONTINUOUS mode (the correct mode per carry_momentum_portfolio.yaml)
        sizer_continuous = ContinuousSizer(
            risk_per_trade=0.007,   # carry_momentum_portfolio.yaml authority
            stop_loss_atr_multiple=2.0,
        )
        result_continuous = real_run_backtest(
            data=enriched,
            signals=signals,
            pair=pair,
            strategy_name=f"{variant}:{pair}:continuous",
            cost_model=cost_model,
            initial_capital=1_000_000.0,
            entry_delay_bars=1,
            sizer=sizer_continuous,
            rebalance_mode="continuous",
            rebalance_threshold=0.20,
        )

        # Run DISCRETE mode (the wrong mode F2 introduced — np.sign collapse)
        result_discrete = real_run_backtest(
            data=enriched,
            signals=signals,
            pair=pair,
            strategy_name=f"{variant}:{pair}:discrete",
            cost_model=cost_model,
            initial_capital=1_000_000.0,
            entry_delay_bars=1,
            sizer=None,
            rebalance_mode="discrete",
            rebalance_threshold=0.20,
        )

        ec_cont = result_continuous.equity_curve.dropna()
        ec_disc = result_discrete.equity_curve.dropna()

        # Align on common index
        common_idx = ec_cont.index.intersection(ec_disc.index)
        assert len(common_idx) > 50, (
            f"Too few common bars ({len(common_idx)}) to compare modes — "
            "check synthetic data length"
        )

        rets_cont = ec_cont.reindex(common_idx).pct_change().dropna()
        rets_disc = ec_disc.reindex(common_idx).pct_change().dropna()
        common_rets = rets_cont.index.intersection(rets_disc.index)

        # The two return series must differ materially.
        # Metric: mean absolute deviation of returns, normalized by the discrete series' std.
        # A value > 0.05 (5% of 1-sigma) is "material" — trivial noise differences are ~1e-10.
        rc = rets_cont.reindex(common_rets).to_numpy()
        rd = rets_disc.reindex(common_rets).to_numpy()
        diff = np.abs(rc - rd)
        disc_std = float(np.std(rd, ddof=1))

        assert disc_std > 0, "Discrete return series has zero variance — data problem"

        mean_normalized_diff = float(np.mean(diff)) / disc_std
        assert mean_normalized_diff > 0.05, (
            f"Continuous and discrete return series for carry_momentum are nearly identical "
            f"(mean_normalized_diff={mean_normalized_diff:.4f} <= 0.05). "
            f"This indicates F2 has regressed: continuous mode is not preserving signal "
            f"magnitude, or sizer is being ignored. "
            f"Discrete std={disc_std:.6f}, mean |cont-disc|={float(np.mean(diff)):.6f}"
        )
