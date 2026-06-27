"""Tests for compute_honest_n and honest_n_deflation_denominator.

Covers:
- compute_honest_n: de-dup view (N ≈ 11, research portfolio ONLY)
- honest_n_deflation_denominator: DSR multiplicity denominator (N = 30, ratified)
- Sacred tests: N=11 for compute_honest_n; N=30 for honest_n_deflation_denominator
- Forbiddance: compute_honest_n must NOT be used at any compute_dsr call site
- Regression: no integer offset, no _RECONCILIATION_EVENT path, no dead code
"""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

import pytest

from forex_system.harness.honest_n import (
    _normalize_strategy,
    compute_honest_n,
    honest_n_deflation_denominator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLASSIFICATION_EVENT = "honest-n-classification"


def _make_trials_file(records: list[dict], include_classification: bool = False) -> Path:
    """Write records to a temporary JSONL file and return the path.

    When include_classification=True, prepends a minimal honest-n-classification
    record so honest_n_deflation_denominator does not fail-close.
    """
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)

    if include_classification:
        # Build counted/excluded lists from the records passed in.
        # Only records with a terminal status and no withdrawal are counted by default.
        counted = [
            {"trial_id": r["trial_id"], "reason": "test fixture"}
            for r in records
            if r.get("counts_toward_deflation_denominator") is not False
            and r.get("status") != "withdrawn-pre-freeze"
            and r.get("status") != "spawned"
        ]
        excluded = [
            {"trial_id": r["trial_id"], "reason": "test fixture excluded"}
            for r in records
            if r.get("counts_toward_deflation_denominator") is False
            or r.get("status") == "withdrawn-pre-freeze"
            or r.get("status") == "spawned"
        ]
        classification = {
            "event": _CLASSIFICATION_EVENT,
            "version": 1,
            "ratified_n": len(counted),
            "ratified_by": ["test"],
            "counted_trial_ids": counted,
            "excluded_trial_ids": excluded,
            "n_legacy_classified": len(counted),
        }
        tmp.write(json.dumps(classification) + "\n")

    for r in records:
        tmp.write(json.dumps(r) + "\n")
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _make_classification_record(counted_ids: list[str], excluded_ids: list[str]) -> dict:
    """Build a minimal honest-n-classification record for test fixtures."""
    return {
        "event": _CLASSIFICATION_EVENT,
        "version": 1,
        "ratified_n": len(counted_ids),
        "ratified_by": ["test-hoqr", "test-nht"],
        "counted_trial_ids": [{"trial_id": tid, "reason": "test"} for tid in counted_ids],
        "excluded_trial_ids": [{"trial_id": tid, "reason": "test"} for tid in excluded_ids],
        "n_legacy_classified": len(counted_ids),
    }


def _write_jsonl(records: list) -> Path:
    """Write records as JSONL to a temp file, return path.

    Accepts a list of dicts or already-serialised JSON strings.
    """
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    for r in records:
        if isinstance(r, str):
            tmp.write(r + "\n")
        else:
            tmp.write(json.dumps(r) + "\n")
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# TestNormalizeStrategy
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestComputeHonestN — DE-DUP VIEW (N ≈ 11); RESEARCH PORTFOLIO ONLY
# ---------------------------------------------------------------------------

class TestComputeHonestN:
    """compute_honest_n returns the correct N and enforces the exclusion rule.

    IMPORTANT: compute_honest_n is the RESEARCH-PORTFOLIO de-dup view.
    It MUST NOT be used at any compute_dsr call site.  See TestForbiddance.
    """

    # ------------------------------------------------------------------
    # Sacred test: N_honest on the actual programme registry = 11
    # ------------------------------------------------------------------

    def test_sacred_n_honest_value(self):
        """SACRED TEST (RE-SCOPED): compute_honest_n on the real trials.jsonl yields N=11.

        This function is the HoQR research-portfolio de-duplication view ONLY.
        It is FORBIDDEN at any compute_dsr call site (see test_compute_honest_n_not_used_at_dsr_sites).
        N=11 must NEVER be passed to compute_dsr as n_trials — it under-deflates and
        manufactures false passes (the unacceptable error direction).

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
        # This pins the de-dup view; it does NOT pin the DSR deflation denominator.
        assert n_honest == 11, (
            f"N_honest must be 11 for current programme registry (de-dup view); got {n_honest}. "
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
        path = _make_trials_file(records)
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
        path = _make_trials_file(records)
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
        path = _make_trials_file(records)
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
        path = _make_trials_file(records)
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
        path = _make_trials_file(records)
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
        path = _make_trials_file(records)
        n_honest, retained_keys, excluded_counts = compute_honest_n(path)

        # Last row (complete) wins — momentum pre_reg key is retained.
        assert n_honest == 1
        assert "references/pre-registrations/momentum.md" in retained_keys
        # Spawned was overwritten, so excluded_counts should be 0 for spawned.
        assert excluded_counts.get("spawned", 0) == 0

    def test_empty_registry_gives_zero(self):
        """Empty JSONL → N_honest = 0."""
        path = _make_trials_file([])
        n_honest, retained_keys, excluded_counts = compute_honest_n(path)
        assert n_honest == 0
        assert retained_keys == set()
        assert sum(excluded_counts.values()) == 0


# ---------------------------------------------------------------------------
# TestDsrDenominator — DEFLATION DENOMINATOR (N = 30, ratified 2026-06-18)
# ---------------------------------------------------------------------------

class TestDsrDenominator:
    """honest_n_deflation_denominator: the org-wide DSR multiplicity denominator.

    Ratified N = 30 as of 2026-06-18 (HoQR + NHT converged; CTO spec approved).
    This function IS the correct source for compute_dsr n_trials at all 4 org-N sites.
    """

    # ------------------------------------------------------------------
    # Sacred test: DSR denominator on the real ledger = 30
    # ------------------------------------------------------------------

    def test_sacred_dsr_denominator_value(self):
        """SACRED TEST: honest_n_deflation_denominator on real trials.jsonl yields N=30.

        This pins the org-wide DSR deflation denominator to the ratified value.
        This test MUST FAIL if anyone reverts to 48, 11, 49, or drifts the
        classification record.

        Ratification: HoQR (hoqr-dsr-debate-r1.yaml) + NHT (nht-dsr-debate-r1.yaml)
        converged 2026-06-18; CTO spec approved; CEo digest RECONCILED-CONVERGED.
        """
        trials_path = Path(".fintech-org/trials.jsonl")
        if not trials_path.exists():
            pytest.skip("trials.jsonl not found — run from project root")

        n = honest_n_deflation_denominator(trials_path)

        assert n == 30, (
            f"DSR deflation denominator MUST be 30 (ratified 2026-06-18 by HoQR+NHT); "
            f"got {n}. Check the honest-n-classification record in trials.jsonl and "
            f"ensure it has exactly 30 counted_trial_ids."
        )

    # ------------------------------------------------------------------
    # Fail-closed: missing classification record raises RuntimeError
    # ------------------------------------------------------------------

    def test_fail_closed_no_classification_record(self):
        """RuntimeError when the 'honest-n-classification' record is absent (fail-closed)."""
        records = [
            {"trial_id": "T1", "strategy": "carry", "status": "complete", "sharpe": 0.5},
        ]
        path = _write_jsonl(records)
        with pytest.raises(RuntimeError, match="honest-n-classification"):
            honest_n_deflation_denominator(path)

    # ------------------------------------------------------------------
    # Spawned-only excluded
    # ------------------------------------------------------------------

    def test_spawned_only_excluded(self):
        """A trial with only a spawned record (sharpe=null) is NOT counted."""
        counted_id = "counted-01"
        spawned_id = "spawned-01"
        classification = _make_classification_record([counted_id], [spawned_id])
        records = [
            json.dumps(classification),
            json.dumps({"trial_id": counted_id, "strategy": "carry", "status": "complete", "sharpe": 0.5}),
            # spawned-only: no terminal record, sharpe=null
            json.dumps({"trial_id": spawned_id, "strategy": "carry", "status": "spawned", "sharpe": None}),
        ]
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        for r in records:
            tmp.write(r + "\n")
        tmp.flush()
        tmp.close()
        n = honest_n_deflation_denominator(Path(tmp.name))
        assert n == 1, f"spawned-only trial must not be counted; got {n}"

    # ------------------------------------------------------------------
    # Re-run-equivalent excluded; different config_hash with same sharpe counts
    # ------------------------------------------------------------------

    def test_rerun_equivalent_excluded_same_config_hash_and_sharpe(self):
        """A trial with same config_hash AND same sharpe as a counted id is NOT counted.

        This covers a9bc0d21: same config_hash 48ac as 7dde9154, sharpe -0.0756 identical.
        """
        base_id = "base-001"
        rerun_id = "rerun-001"

        classification = _make_classification_record([base_id], [])
        base_record = {
            "trial_id": base_id,
            "strategy": "carry",
            "status": "complete",
            "sharpe": -0.0756,
            "config_hash": "48acc248c1db",
        }
        # re-run: same config_hash AND same sharpe
        rerun_record = {
            "trial_id": rerun_id,
            "strategy": "carry",
            "status": "complete",
            "sharpe": -0.0756,
            "config_hash": "48acc248c1db",
        }
        path = _write_jsonl([classification, base_record, rerun_record])
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"re-run-equivalent (same config_hash AND same sharpe) must be excluded; got {n}"
        )

    def test_same_sharpe_different_config_hash_counts(self):
        """A trial with same sharpe BUT different config_hash IS counted (covers a9c0902d).

        a9c0902d has the same sharpe (-0.0756) as 7dde9154 but a different config_hash (7b46
        vs 48ac) — identity-as-rerun is UNPROVABLE -> COUNT per SD2 (over-deflate).
        """
        base_id = "base-002"
        different_config_id = "diff-002"

        classification = _make_classification_record([base_id], [])
        base_record = {
            "trial_id": base_id,
            "strategy": "carry",
            "status": "complete",
            "sharpe": -0.0756,
            "config_hash": "48acc248c1db",
        }
        # same sharpe, DIFFERENT config_hash -> must count
        diff_record = {
            "trial_id": different_config_id,
            "strategy": "carry",
            "status": "complete",
            "sharpe": -0.0756,
            "config_hash": "7b4607069a6b",
        }
        path = _write_jsonl([classification, base_record, diff_record])
        n = honest_n_deflation_denominator(path)
        assert n == 2, (
            f"same sharpe but different config_hash must be counted (unprovable re-run); got {n}"
        )

    def test_two_new_trials_same_signature_first_counts_second_drops(self):
        """Two NEW (non-legacy) trials with identical config_hash+sharpe: first counts,
        second drops as re-run-equivalent. Deterministic in ledger order."""
        classification = _make_classification_record([], [])
        first = {
            "trial_id": "new-first",
            "strategy": "carry",
            "status": "complete",
            "sharpe": 0.42,
            "config_hash": "deadbeef00",
        }
        second = {
            "trial_id": "new-second",
            "strategy": "carry",
            "status": "complete",
            "sharpe": 0.42,
            "config_hash": "deadbeef00",
        }
        path = _write_jsonl([classification, first, second])
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"two new trials sharing config_hash+sharpe: first counts, second drops as "
            f"re-run-equivalent (no new max); got {n}"
        )

    def test_new_exploratory_null_sharpe_counts_not_dropped_as_spawned(self):
        """A NEW trial with status='exploratory' and sharpe=null is NOT dropped as
        spawned-only (only literal status=='spawned' drops). It COUNTS per SD2
        over-deflate — this is the CTO-spec finding (B) protection: don't over-drop
        ambiguous null-sharpe draws (backfills/frozen-pending-receipt class)."""
        classification = _make_classification_record([], [])
        exploratory = {
            "trial_id": "new-explore",
            "strategy": "carry",
            "status": "exploratory",
            "sharpe": None,
        }
        spawned = {
            "trial_id": "new-spawned",
            "strategy": "carry",
            "status": "spawned",
            "sharpe": None,
        }
        path = _write_jsonl([classification, exploratory, spawned])
        n = honest_n_deflation_denominator(path)
        # exploratory+null COUNTS (1); spawned+null DROPS (0). Total = 1.
        assert n == 1, (
            f"exploratory+null must count (ambiguous, SD2); spawned+null must drop; got {n}"
        )

    # ------------------------------------------------------------------
    # Withdrawn excluded; sticky
    # ------------------------------------------------------------------

    def test_withdrawn_excluded(self):
        """withdrawn-pre-freeze OR counts_toward_deflation_denominator==false is NOT counted."""
        counted_id = "counted-03"
        withdrawn_id = "withdrawn-03"
        flagged_id = "flagged-03"

        classification = _make_classification_record([counted_id], [withdrawn_id, flagged_id])
        records = [
            classification,
            {"trial_id": counted_id, "strategy": "carry", "status": "complete", "sharpe": 0.5},
            {
                "trial_id": withdrawn_id,
                "strategy": "carry",
                "status": "withdrawn-pre-freeze",
                "sharpe": None,
                "counts_toward_deflation_denominator": False,
            },
            {
                "trial_id": flagged_id,
                "strategy": "momentum",
                "status": "spawned",
                "sharpe": None,
                "counts_toward_deflation_denominator": False,
            },
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"withdrawn and flagged-false must be excluded; got {n}"

    def test_sticky_exclusion_survives_last_wins(self):
        """A trial_id that ONCE had counts_toward=False stays excluded even if a later
        record drops the flag (sticky exclusion — monotonic, cannot be resurrected)."""
        counted_id = "counted-sticky"
        sticky_id = "sticky-001"

        classification = _make_classification_record([counted_id], [sticky_id])
        records = [
            classification,
            {"trial_id": counted_id, "strategy": "carry", "status": "complete", "sharpe": 0.5},
            # First record flags it as false
            {
                "trial_id": sticky_id,
                "strategy": "carry",
                "status": "spawned",
                "counts_toward_deflation_denominator": False,
            },
            # Later record drops the flag — but sticky exclusion must hold
            {
                "trial_id": sticky_id,
                "strategy": "carry",
                "status": "complete",
                "sharpe": 0.5,
                # counts_toward_deflation_denominator ABSENT -> would default to count,
                # but sticky set must prevent resurrection.
            },
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"sticky exclusion must persist across last-wins; got {n}"
        )

    # ------------------------------------------------------------------
    # Ambiguous / null-status id counted once
    # ------------------------------------------------------------------

    def test_ambiguous_status_counted_once(self):
        """A frozen-pending-receipt / null-status id with no drop-evidence IS counted once.

        This covers f2fb41fd, fa0f982a, 15923fe1 — all explicitly in the ratified set.
        """
        ambiguous_id = "ambig-01"
        classification = _make_classification_record([ambiguous_id], [])
        record = {
            "trial_id": ambiguous_id,
            "strategy": "carry",
            # null status — genuinely ambiguous; over-deflate rule: COUNT
            "status": None,
            "sharpe": None,
        }
        path = _write_jsonl([classification, record])
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"ambiguous status must be counted once; got {n}"

    # ------------------------------------------------------------------
    # Increment by one for a new draw
    # ------------------------------------------------------------------

    def test_increment_by_one_for_new_draw(self):
        """Appending one new genuine draw (complete, not in legacy list) increments N by 1."""
        base_id = "base-incr"
        new_id = "new-incr"

        # Classification covers only base_id (N=1)
        classification = _make_classification_record([base_id], [])
        records = [
            classification,
            {"trial_id": base_id, "strategy": "carry", "status": "complete", "sharpe": 0.5},
            # New trial not in classification record -> classify mechanically -> count
            {"trial_id": new_id, "strategy": "momentum", "status": "complete", "sharpe": 0.8},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 2, f"one new genuine draw must increment denominator by 1; got {n}"

    # ------------------------------------------------------------------
    # Double-count guard
    # ------------------------------------------------------------------

    def test_double_count_guard_same_id_multiple_lines(self):
        """A trial_id appearing on multiple ledger lines is counted exactly ONCE."""
        trial_id = "dup-multi"
        classification = _make_classification_record([trial_id], [])
        records = [
            classification,
            {"trial_id": trial_id, "strategy": "carry", "status": "spawned", "sharpe": None},
            {"trial_id": trial_id, "strategy": "carry", "status": "complete", "sharpe": 0.5},
            {"trial_id": trial_id, "strategy": "carry", "status": "complete", "sharpe": 0.5},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"same trial_id on multiple lines must count only once; got {n}"

    def test_double_count_guard_legacy_and_new_line(self):
        """A trial_id in legacy counted AND appearing as a new ledger line counts once."""
        counted_id = "dup-legacy"
        classification = _make_classification_record([counted_id], [])
        records = [
            classification,
            # This id is in counted_trial_ids of the classification record.
            # A new ledger line for it must NOT add a second count.
            {"trial_id": counted_id, "strategy": "carry", "status": "complete", "sharpe": 0.7},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"legacy counted id appearing as a new ledger line must still count once; got {n}"
        )

    # ------------------------------------------------------------------
    # F-003 Guard (a): duplicate classification record raises
    # ------------------------------------------------------------------

    def test_guard_duplicate_classification_record_raises(self):
        """Guard (a): if MORE THAN ONE 'honest-n-classification' record exists → RuntimeError.

        A second classification record silently drops the first under last-wins semantics,
        making the count ambiguous.  The guard catches this as a ledger miscalibration.
        """
        classification_1 = _make_classification_record(["tid-a"], [])
        classification_2 = _make_classification_record(["tid-a", "tid-b"], [])
        trial_a = {"trial_id": "tid-a", "strategy": "carry", "status": "complete", "sharpe": 0.5}
        trial_b = {"trial_id": "tid-b", "strategy": "momentum", "status": "complete", "sharpe": 0.7}
        path = _write_jsonl([classification_1, trial_a, classification_2, trial_b])

        with pytest.raises(RuntimeError, match="honest-n-classification"):
            honest_n_deflation_denominator(path)

    # ------------------------------------------------------------------
    # F-003 Guard (b): ratified_n mismatch with len(counted_trial_ids) raises
    # ------------------------------------------------------------------

    def test_guard_ratified_n_mismatch_raises(self):
        """Guard (b): ratified_n != len(counted_trial_ids) → RuntimeError.

        A record that claims ratified_n=3 but only has 2 counted_trial_ids entries
        has drifted — the stated N no longer matches the census.
        """
        # Build a classification record where ratified_n is deliberately wrong.
        classification = {
            "event": _CLASSIFICATION_EVENT,
            "version": 1,
            "ratified_n": 3,          # WRONG: claims 3 but only 2 entries below
            "ratified_by": ["test-hoqr", "test-nht"],
            "counted_trial_ids": [
                {"trial_id": "tid-x", "reason": "test"},
                {"trial_id": "tid-y", "reason": "test"},
            ],
            "excluded_trial_ids": [],
            "n_legacy_classified": 2,
        }
        trial_x = {"trial_id": "tid-x", "strategy": "carry", "status": "complete", "sharpe": 0.5}
        trial_y = {"trial_id": "tid-y", "strategy": "momentum", "status": "complete", "sharpe": 0.7}
        path = _write_jsonl([classification, trial_x, trial_y])

        with pytest.raises(RuntimeError, match="ratified_n"):
            honest_n_deflation_denominator(path)

    def test_guard_ratified_n_missing_raises(self):
        """Guard (b): absent ratified_n field → RuntimeError (malformed record)."""
        classification = {
            "event": _CLASSIFICATION_EVENT,
            "version": 1,
            # ratified_n intentionally ABSENT
            "ratified_by": ["test-hoqr"],
            "counted_trial_ids": [{"trial_id": "tid-z", "reason": "test"}],
            "excluded_trial_ids": [],
        }
        trial_z = {"trial_id": "tid-z", "strategy": "carry", "status": "complete", "sharpe": 0.5}
        path = _write_jsonl([classification, trial_z])

        with pytest.raises(RuntimeError, match="ratified_n"):
            honest_n_deflation_denominator(path)


# ---------------------------------------------------------------------------
# TestNoOffsetNoDeadPath — regression: no integer offset, no old reconciliation path
# ---------------------------------------------------------------------------

class TestNoOffsetNoDeadPath:
    """Regression tests ensuring the old integer-offset / _RECONCILIATION_EVENT path is gone."""

    def test_no_reconciliation_event_in_source(self):
        """honest_n.py must NOT reference _RECONCILIATION_EVENT or prose_only_attempts.

        The old offset path was fully deleted (not dormant).  This catches a partial patch.
        """
        source_path = Path("src/forex_system/harness/honest_n.py")
        if not source_path.exists():
            pytest.skip("honest_n.py not found — run from project root")
        source = source_path.read_text()
        assert "_RECONCILIATION_EVENT" not in source, (
            "honest_n.py must NOT contain '_RECONCILIATION_EVENT' — the old offset path "
            "must be fully deleted, not dormant."
        )
        assert "prose_only_attempts" not in source, (
            "honest_n.py must NOT contain 'prose_only_attempts' — the old offset path "
            "must be fully deleted, not dormant."
        )

    def test_honest_n_offset_json_not_read_by_function(self):
        """honest_n.py must NOT reference honest_n_offset.json (the retired offset file)."""
        source_path = Path("src/forex_system/harness/honest_n.py")
        if not source_path.exists():
            pytest.skip("honest_n.py not found — run from project root")
        source = source_path.read_text()
        assert "honest_n_offset.json" not in source, (
            "honest_n.py must NOT read honest_n_offset.json — the phantom 15-offset is "
            "retired and must not be referenced in the function."
        )


# ---------------------------------------------------------------------------
# AST helpers for TestForbiddance
# ---------------------------------------------------------------------------

def _is_compute_honest_n_call(node: ast.expr) -> bool:
    """Return True if node is a call to compute_honest_n(...).

    Matches both bare-name calls (``compute_honest_n(...)``) and attribute-access
    calls (``honest_n.compute_honest_n(...)``), so an import-style change to
    qualified access cannot smuggle the forbidden source past the check.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "compute_honest_n"
    if isinstance(func, ast.Attribute):
        return func.attr == "compute_honest_n"
    return False


def _collect_assigned_names(target: ast.expr, names: set[str]) -> None:
    """Collect all Name ids from an assignment target (handles tuples/lists)."""
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _collect_assigned_names(elt, names)
    # Subscript / Attribute targets are ignored (not a simple name binding).


# ---------------------------------------------------------------------------
# TestForbiddance — compute_honest_n must NOT be used at compute_dsr sites
# ---------------------------------------------------------------------------

class TestForbiddance:
    """compute_honest_n (N≈11 de-dup view) must NOT be imported/called at any
    compute_dsr call site.  This is an import-graph / AST check.

    The four org-N compute_dsr sites are:
        src/forex_system/harness/run_trial.py
        scripts/run_falsification_trial.py
        scripts/trial_48_is_eval.py
        src/forex_system/harness/dsr_recompute.py  (the CRITICAL site)
    """

    _DSR_SITES = [
        Path("src/forex_system/harness/run_trial.py"),
        Path("scripts/run_falsification_trial.py"),
        Path("scripts/trial_48_is_eval.py"),
        Path("src/forex_system/harness/dsr_recompute.py"),
    ]

    def _imports_compute_honest_n(self, source: str) -> bool:
        """Return True if the source imports compute_honest_n."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "compute_honest_n":
                            return True
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "compute_honest_n" in alias.name:
                            return True
        return False

    def _calls_compute_honest_n(self, source: str) -> bool:
        """Return True if the source calls compute_honest_n(...)."""
        return "compute_honest_n(" in source

    @pytest.mark.parametrize("site_path", _DSR_SITES)
    def test_compute_honest_n_not_used_at_dsr_sites(self, site_path: Path):
        """compute_honest_n must NOT be imported or called at any compute_dsr org-N site.

        Covers all 4 call sites, including dsr_recompute.py (the previously LIVE
        violation where n_honest fed compute_dsr directly, under-deflating DSRs).
        """
        if not site_path.exists():
            pytest.skip(f"{site_path} not found — run from project root")

        source = site_path.read_text()

        imports_it = self._imports_compute_honest_n(source)
        calls_it = self._calls_compute_honest_n(source)

        # dsr_recompute.py may import compute_honest_n for the portfolio-view summary
        # fields, but must NOT pass its result to compute_dsr as n_trials.
        # The critical check for dsr_recompute.py is that compute_honest_n is
        # NOT the source feeding compute_dsr's n_trials argument.
        if site_path.name == "dsr_recompute.py":
            # AST-based check: compute_dsr must NOT receive the result of compute_honest_n
            # as its n_trials argument.
            #
            # Properties verified at the AST level for EVERY compute_dsr(...) call:
            #   (1) n_trials keyword exists (mandatory argument).
            #   (2) The n_trials expression subtree contains NO compute_honest_n(...) call
            #       (catches inline n_trials=compute_honest_n(...) directly).
            #   (3) If n_trials is a Name, it is NOT one assigned from compute_honest_n()
            #       elsewhere in the module (catches the variable-alias path).
            #   (4) The n_trials expression references the deflation denominator — its
            #       source segment must contain 'deflation_denominator' (a Name, an inline
            #       honest_n_deflation_denominator(...) call, or any other expression form
            #       that wires the ratified path through). A non-Name n_trials is NOT
            #       silently accepted: it must still name the denominator.
            #
            # compute_dsr is matched by call name whether bare or attribute-access.
            # This is stronger than a substring check because it cannot be fooled by
            # comments, strings, or variable aliases that happen to contain the forbidden
            # text without actually wiring it through to compute_dsr.
            tree = ast.parse(source)

            # Step 1: collect names assigned from compute_honest_n() calls (bare or
            # attribute-access). Handles simple, tuple/list, and augmented assignment.
            honest_n_assigned_names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if _is_compute_honest_n_call(node.value):
                        for target in node.targets:
                            _collect_assigned_names(target, honest_n_assigned_names)
                elif isinstance(node, ast.AugAssign):
                    if _is_compute_honest_n_call(node.value):
                        _collect_assigned_names(node.target, honest_n_assigned_names)

            def _is_compute_dsr_call(call_node: ast.Call) -> bool:
                func = call_node.func
                if isinstance(func, ast.Name):
                    return func.id == "compute_dsr"
                if isinstance(func, ast.Attribute):
                    return func.attr == "compute_dsr"
                return False

            # Step 2: verify compute_dsr call sites.
            compute_dsr_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and _is_compute_dsr_call(node)
            ]
            assert compute_dsr_calls, (
                "dsr_recompute.py: no compute_dsr call found — the AST forbiddance check "
                "expects at least one. Did the call site move or get renamed?"
            )

            for node in compute_dsr_calls:
                n_trials_kwarg = next(
                    (kw for kw in node.keywords if kw.arg == "n_trials"),
                    None,
                )
                assert n_trials_kwarg is not None, (
                    "dsr_recompute.py: compute_dsr call has no n_trials keyword argument. "
                    "The n_trials argument is mandatory — it must be the deflation denominator."
                )

                n_trials_val = n_trials_kwarg.value

                # (2) No compute_honest_n(...) call anywhere inside the n_trials expression.
                for sub in ast.walk(n_trials_val):
                    if isinstance(sub, ast.Call):
                        assert not _is_compute_honest_n_call(sub), (
                            "dsr_recompute.py: compute_dsr's n_trials expression calls "
                            "compute_honest_n() (the ~11 de-dup view). This under-deflates "
                            "DSRs and manufactures false passes. Use "
                            "honest_n_deflation_denominator() instead."
                        )

                # (3) If a Name, it must not alias a compute_honest_n() result.
                if isinstance(n_trials_val, ast.Name):
                    assert n_trials_val.id not in honest_n_assigned_names, (
                        f"dsr_recompute.py: compute_dsr(n_trials={n_trials_val.id!r}) — "
                        f"'{n_trials_val.id}' is assigned from compute_honest_n() (the ~11 "
                        "de-dup view). This under-deflates DSRs and manufactures false passes. "
                        "Use the result of honest_n_deflation_denominator() instead."
                    )

                # (4) The n_trials expression must reference the deflation denominator —
                # regardless of node type (Name, inline call, etc.). ast.get_source_segment
                # gives the exact source text of the expression (not comments/strings elsewhere).
                n_trials_src = ast.get_source_segment(source, n_trials_val) or ""
                assert "deflation_denominator" in n_trials_src, (
                    f"dsr_recompute.py: compute_dsr n_trials expression {n_trials_src!r} does "
                    "not reference the deflation denominator. Expected a variable or call "
                    "containing 'deflation_denominator' (the ratified 30-count path)."
                )
        else:
            # The other three sites must not import or call compute_honest_n at all.
            assert not imports_it and not calls_it, (
                f"{site_path} imports or calls compute_honest_n — FORBIDDEN at compute_dsr sites. "
                f"compute_honest_n (N≈11 de-dup view) under-deflates DSRs and manufactures "
                f"false passes. Use honest_n_deflation_denominator() instead."
            )


# ---------------------------------------------------------------------------
# TestDSRRecomputeSanity
# ---------------------------------------------------------------------------

class TestDSRRecomputeSanity:
    """Sanity tests: recomputed DSRs are bounded and directionally correct.

    These tests exercise compute_honest_n + compute_dsr together using
    the real programme data where equity parquets exist.
    """

    def test_n_honest_is_global_single_value(self):
        """N_honest (de-dup view) is a single scalar (global across the programme)."""
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

        # Use the DSR deflation denominator (ratified 30), not the de-dup view.
        n_trials = honest_n_deflation_denominator(trials_path)

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
                n_trials=n_trials,
                periods_per_year=float(TRADING_DAYS_PER_YEAR),
            )
            assert 0.0 <= dsr <= 1.0, f"DSR out of [0,1] for {trial_id}: {dsr}"
