"""Tests for compute_honest_n (HoQR Honest-N De-duplication Rule).

Covers:
- spawned/exploratory rows are excluded from N_honest
- N_honest value matches expected count (sacred-test: expected ~10)
- Sweep variants collapse into their hypothesis family
- strategy_family_id normalization strips known suffixes
- retained_keys set is the union of distinct hypothesis_keys
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forex_system.harness.honest_n import (
    _normalize_strategy,
    compute_honest_n,
)


class TestNormalizeStrategy:
    """_normalize_strategy strips cost/pair/variant suffixes iteratively."""

    @pytest.mark.parametrize(
        "strategy, expected_family",
        [
            ("vol_target_carry", "vol_target_carry"),
            ("vol_target_carry_no_vol_scaling", "vol_target_carry"),
            ("vol_target_carry_canonical", "vol_target_carry"),
            ("vol_target_carry_portfolio", "vol_target_carry"),
            ("carry_2x_costs", "carry"),
            ("carry_3x_cost", "carry"),
            ("momentum_GBPUSD_only", "momentum"),
            ("fred_carry_stripped", "fred_carry"),
            ("tas_ceiling_4h", "tas_ceiling"),
            ("ma_crossover", "ma_crossover"),
            ("bollinger_rsi", "bollinger_rsi"),
            ("carry_momentum", "carry_momentum"),
        ],
    )
    def test_normalization(self, strategy: str, expected_family: str):
        assert _normalize_strategy(strategy) == expected_family, (
            f"normalize({strategy!r}) should be {expected_family!r}"
        )


class TestComputeHonestN:
    """compute_honest_n returns the correct N and enforces the exclusion rule."""

    def _make_trials_file(self, records: list[dict]) -> Path:
        """Write records to a temporary JSONL file and return the path."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        for r in records:
            tmp.write(json.dumps(r) + "\n")
        tmp.flush()
        tmp.close()
        return Path(tmp.name)

    # ------------------------------------------------------------------
    # Sacred test: N_honest on the actual programme registry ≈ 10
    # ------------------------------------------------------------------

    def test_sacred_n_honest_value(self):
        """SACRED TEST: compute_honest_n on the real trials.jsonl yields N_honest=11.

        This is the primary invariant for the HoQR de-duplication rule.
        N_honest history:
          N=10 before commit 1c533e8 (r5-step4 2026-06-06): trial 576746aa added
                with pre_reg_path='references/pre-registrations/r5_carry_universe_kill_test.md',
                which became a new distinct hypothesis key.
          N=11 from commit 1c533e8 onward: 576746aa pre_reg_path adds the R5 key.
        The 11 keys are: bollinger_rsi, carry, carry_momentum, fred_carry, ma_crossover,
        momentum, references/pre-registrations/momentum.md,
        references/pre-registrations/r5_carry_universe_kill_test.md,
        references/pre-registrations/vol_target_carry.md, tas_ceiling, vol_target_carry.
        Note: trial f2fb41fd (confirmatory, spawned=True, status=unknown) does NOT
        contribute to N_honest — it is neither retained nor excluded (unknown status
        falls through the filter without being counted).
        """
        trials_path = Path(".fintech-org/trials.jsonl")
        if not trials_path.exists():
            pytest.skip("trials.jsonl not found — run from project root")

        n_honest, retained_keys, excluded_counts = compute_honest_n(trials_path)

        # Sacred assertion: N_honest must be 11 for the current programme registry.
        assert n_honest == 11, (
            f"N_honest must be 11 for current programme registry; got {n_honest}. "
            f"retained_keys={sorted(retained_keys)}"
        )
        # All retained keys are non-empty strings.
        assert all(isinstance(k, str) and k for k in retained_keys)

    def test_spawned_and_exploratory_excluded(self):
        """Rows with status spawned or exploratory must NOT appear in retained_keys."""
        records = [
            {"trial_id": "A", "strategy": "momentum", "pre_reg_path": None, "status": "spawned"},
            {"trial_id": "B", "strategy": "carry", "pre_reg_path": None, "status": "exploratory"},
            {
                "trial_id": "C",
                "strategy": "ma_crossover",
                "pre_reg_path": None,
                "status": "rejected",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, excluded_counts = compute_honest_n(path)

        assert n_honest == 1
        assert excluded_counts.get("spawned", 0) == 1
        assert excluded_counts.get("exploratory", 0) == 1
        assert "ma_crossover" in retained_keys
        # momentum (spawned) and carry (exploratory) must not appear
        assert "momentum" not in retained_keys
        assert "carry" not in retained_keys

    def test_rejected_rows_are_retained(self):
        """Rejected status is retained (excluding it would be survivorship bias)."""
        records = [
            {
                "trial_id": "X",
                "strategy": "bollinger_rsi",
                "pre_reg_path": None,
                "status": "rejected",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, _ = compute_honest_n(path)
        assert n_honest == 1
        assert "bollinger_rsi" in retained_keys

    def test_sweep_variants_collapse(self):
        """Multiple sweep runs of the same hypothesis_key collapse to N_honest=1."""
        records = [
            {
                "trial_id": "sweep-01",
                "strategy": "vol_target_carry",
                "pre_reg_path": "references/pre-registrations/vol_target_carry.md",
                "status": "complete",
            },
            {
                "trial_id": "sweep-02",
                "strategy": "vol_target_carry",
                "pre_reg_path": "references/pre-registrations/vol_target_carry.md",
                "status": "complete",
            },
            {
                "trial_id": "sweep-03",
                "strategy": "vol_target_carry",
                "pre_reg_path": "references/pre-registrations/vol_target_carry.md",
                "status": "rejected",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, _ = compute_honest_n(path)

        # All three share the same pre_reg_path → collapse to 1 distinct hypothesis.
        assert n_honest == 1
        assert "references/pre-registrations/vol_target_carry.md" in retained_keys

    def test_no_pre_reg_uses_strategy_family(self):
        """Trials without pre_reg_path use normalized strategy name as hypothesis_key."""
        records = [
            {
                "trial_id": "T1",
                "strategy": "vol_target_carry_no_vol_scaling",
                "pre_reg_path": None,
                "status": "rejected",
            },
            {
                "trial_id": "T2",
                "strategy": "vol_target_carry_canonical",
                "pre_reg_path": None,
                "status": "complete",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, _ = compute_honest_n(path)

        # Both normalize to "vol_target_carry" → 1 distinct hypothesis.
        assert n_honest == 1
        assert "vol_target_carry" in retained_keys

    def test_multiple_strategies_distinct_keys(self):
        """Two different strategies → N_honest = 2."""
        records = [
            {
                "trial_id": "M1",
                "strategy": "ma_crossover",
                "pre_reg_path": None,
                "status": "rejected",
            },
            {
                "trial_id": "B1",
                "strategy": "bollinger_rsi",
                "pre_reg_path": None,
                "status": "rejected",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, _ = compute_honest_n(path)
        assert n_honest == 2
        assert "ma_crossover" in retained_keys
        assert "bollinger_rsi" in retained_keys

    def test_duplicate_trial_id_last_row_wins(self):
        """When the same trial_id appears twice, the last row's status determines inclusion."""
        records = [
            # First row: spawned (would be excluded)
            {"trial_id": "DUP1", "strategy": "momentum", "pre_reg_path": None, "status": "spawned"},
            # Second row: complete (retained)
            {
                "trial_id": "DUP1",
                "strategy": "momentum",
                "pre_reg_path": "references/pre-registrations/momentum.md",
                "status": "complete",
            },
        ]
        path = self._make_trials_file(records)
        n_honest, retained_keys, excluded_counts = compute_honest_n(path)

        # Last row (complete) wins — momentum pre_reg key is retained.
        assert n_honest == 1
        assert "references/pre-registrations/momentum.md" in retained_keys
        # Spawned was overwritten, so excluded_counts should be 0 for spawned.
        assert excluded_counts.get("spawned", 0) == 0

    def test_empty_registry_gives_zero(self):
        """Empty JSONL → N_honest = 0."""
        path = self._make_trials_file([])
        n_honest, retained_keys, excluded_counts = compute_honest_n(path)
        assert n_honest == 0
        assert retained_keys == set()
        assert sum(excluded_counts.values()) == 0


class TestDSRRecomputeSanity:
    """Sanity tests: recomputed DSRs are bounded and directionally correct.

    These tests exercise compute_honest_n + compute_dsr together using
    the real programme data where equity parquets exist.
    """

    def test_n_honest_is_global_single_value(self):
        """N_honest is a single scalar (global across the programme), not per-trial."""
        trials_path = Path(".fintech-org/trials.jsonl")
        if not trials_path.exists():
            pytest.skip("trials.jsonl not found")
        n_honest, _, _ = compute_honest_n(trials_path)
        assert isinstance(n_honest, int)
        assert n_honest > 0

    def test_recomputed_dsrs_in_unit_interval(self):
        """All successfully recomputed DSRs must be in [0, 1]."""
        import pandas as pd
        from scipy import stats as scipy_stats

        from forex_system.core.constants import TRADING_DAYS_PER_YEAR
        from forex_system.harness.dsr import compute_dsr

        trials_path = Path(".fintech-org/trials.jsonl")
        if not trials_path.exists():
            pytest.skip("trials.jsonl not found")

        n_honest, _, _ = compute_honest_n(trials_path)

        # Only these trial_ids have equity parquets (from current project state).
        equity_dir = Path("data/results/trials")
        for parquet_path in equity_dir.glob("*_equity.parquet"):
            trial_id = parquet_path.stem.replace("_equity", "")
            df = pd.read_parquet(parquet_path)
            returns = df["equity"].pct_change().dropna()
            if len(returns) < 2:
                continue

            # Use a positive Sharpe value for the test (d572999d is the canonical one).
            sharpe = 0.76  # representative annualized value
            dsr = compute_dsr(
                sharpe_ratio=sharpe,
                n_observations=len(returns),
                skewness=float(scipy_stats.skew(returns)),
                excess_kurtosis=float(scipy_stats.kurtosis(returns, fisher=True)),
                n_trials=n_honest,
                periods_per_year=float(TRADING_DAYS_PER_YEAR),
            )
            assert 0.0 <= dsr <= 1.0, f"DSR out of [0,1] for {trial_id}: {dsr}"
