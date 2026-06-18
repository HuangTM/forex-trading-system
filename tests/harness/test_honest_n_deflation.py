"""Acceptance tests for honest_n_deflation_denominator (P0 / IC-9 / IC-14d).

Pins the mechanical counting rule ratified by HoQR + NHT 2026-06-18.
Denominator N = 30 (retired: N = 48, which had a phantom 15-integer offset).

Tests:
1. test_sacred_dsr_denominator_value  — SACRED: pins ==30 on the real ledger.
2. test_withdrawn_pre_freeze_excluded    — explicit false flag / withdrawn-pre-freeze does not count.
3. test_missing_classification_record_raises — fail-closed: absence of classification record raises.
4. test_spawn_complete_same_id_counts_once — spawn+complete for same trial_id = ONE slot (not two).
5. test_event_lines_without_trial_id_skipped — non-trial metadata lines do not add slots.
6. test_ambiguous_status_counts          — unknown/archive-event status counts (SD2 over-deflate rule).
7. test_compute_honest_n_not_feeding_dsr_call_sites — regression: compute_honest_n (the 11-view)
       must NOT appear at the run_trial or run_falsification_trial DSR call sites.
8. test_ic9_dsr_denominator_adds_is_search_and_budget — full IC-9 helper composes correctly.
9. test_empty_ledger_without_classification_raises — empty ledger raises (no classification record).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forex_system.harness.honest_n import (
    honest_n_deflation_denominator,
    ic9_dsr_denominator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLASSIFICATION_EVENT = "honest-n-classification"


def _write_jsonl(records: list) -> Path:
    """Write records to a temp JSONL file and return the path.

    Accepts dicts or already-serialised JSON strings.
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


def _classification_record(counted_ids: list[str], excluded_ids: list[str]) -> dict:
    """Minimal honest-n-classification record for test fixtures.

    Replaces the retired _reconciliation_record / honest-n-reconciliation approach.
    """
    return {
        "event": _CLASSIFICATION_EVENT,
        "version": 1,
        "ratified_n": len(counted_ids),
        "ratified_by": ["test-hoqr", "test-nht"],
        "counted_trial_ids": [{"trial_id": tid, "reason": "test"} for tid in counted_ids],
        "excluded_trial_ids": [{"trial_id": tid, "reason": "test"} for tid in excluded_ids],
        "n_legacy_classified": len(counted_ids),
    }


# ---------------------------------------------------------------------------
# 1. Sacred test — pins ==30 on the real programme ledger
# ---------------------------------------------------------------------------

class TestHonestNSacred:
    """Sacred acceptance test: pins the exact value on the ratified programme ledger."""

    def test_sacred_dsr_denominator_value(self):
        """SACRED: honest_n_deflation_denominator on the real trials.jsonl == 30.

        This is the IC-9 acceptance test (CTO spec 2026-06-18 acceptance_tests[0]).
        Value ratified: 30 = 34 distinct trial_ids - 4 drops (2 spawned-only + 1 re-run
        + 1 withdrawn-pre-freeze).  Replaces the retired N=48 (which had a phantom
        15-integer offset back-solved against the 48 anchor, not line-derived).

        Ratification: HoQR (hoqr-dsr-debate-r1.yaml) + NHT (nht-dsr-debate-r1.yaml)
        converged 2026-06-18; CTO spec approved; CEO digest RECONCILED-CONVERGED.
        """
        trials_path = Path(".fintech-org/trials.jsonl")
        if not trials_path.exists():
            pytest.skip("trials.jsonl not found — run from project root")

        # Check classification record is present first (informative fail vs skip).
        with open(trials_path) as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
        has_classification = any(r.get("event") == _CLASSIFICATION_EVENT for r in lines)
        if not has_classification:
            pytest.fail(
                "honest-n-classification record not present in trials.jsonl. "
                "QD must append the ratified classification record before tests pass."
            )

        n = honest_n_deflation_denominator(trials_path)
        assert n == 30, (
            f"SACRED FAILURE: honest_n_deflation_denominator must return 30 on the "
            f"ratified ledger; got {n}. "
            f"Ratified 2026-06-18: 30 = 34 distinct ids - 4 drops."
        )


# ---------------------------------------------------------------------------
# 2. Withdrawn / explicit-false records are excluded
# ---------------------------------------------------------------------------

class TestExclusions:
    """Records with counts_toward=False or withdrawn-pre-freeze do not increment."""

    def test_withdrawn_pre_freeze_excluded(self):
        """A withdrawn-pre-freeze trial (like 53981a4a) must NOT increment the count."""
        records = [
            _classification_record(["bbb"], ["aaa"]),  # classification: aaa excluded, bbb counted
            {"trial_id": "aaa", "status": "withdrawn-pre-freeze"},
            {"trial_id": "bbb", "status": "rejected"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"Only bbb should count; got {n}"

    def test_explicit_false_flag_excluded(self):
        """counts_toward_deflation_denominator: false overrides any status."""
        records = [
            _classification_record(["bbb"], ["aaa"]),
            {"trial_id": "aaa", "status": "complete", "counts_toward_deflation_denominator": False},
            {"trial_id": "bbb", "status": "complete"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"Only bbb should count (aaa has explicit flag=false); got {n}"

    def test_explicit_true_flag_counts(self):
        """counts_toward_deflation_denominator: true always counts (even unusual status)."""
        records = [
            _classification_record(["aaa"], []),
            {"trial_id": "aaa", "counts_toward_deflation_denominator": True, "event": "trial-spawned"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"aaa with explicit flag=true should count; got {n}"

    def test_sticky_exclusion_first_false_later_omits_flag(self):
        """STICKY: a trial flagged false early stays excluded even if a later record omits it.

        Regression for the over-count failure mode: last-wins collapse alone would
        resurrect a flagged-false trial when a later status-update record drops the flag.
        """
        records = [
            _classification_record(["real"], ["sticky"]),
            {"trial_id": "sticky", "status": "withdrawn-pre-freeze",
             "counts_toward_deflation_denominator": False},
            {"trial_id": "sticky", "status": "rejected"},  # later record omits the flag
            {"trial_id": "real", "status": "complete"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"'sticky' must stay excluded despite the later flag-less record; "
            f"only 'real' counts. Got {n}"
        )

    def test_sticky_exclusion_first_withdrawn_later_complete(self):
        """STICKY: withdrawn-pre-freeze early stays excluded even if later status=complete."""
        records = [
            _classification_record([], ["w"]),
            {"trial_id": "w", "status": "withdrawn-pre-freeze"},
            {"trial_id": "w", "status": "complete"},  # later record tries to resurrect
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 0, f"withdrawn-pre-freeze is sticky; trial must stay excluded. Got {n}"


# ---------------------------------------------------------------------------
# 3. Absent classification record raises (fail-closed)
# ---------------------------------------------------------------------------

class TestFailClosed:
    """Absence of the classification record must raise, not silently under-count."""

    def test_missing_classification_record_raises(self):
        """Without the classification record, function must raise RuntimeError.

        This is the IC-9 acceptance test for fail-closed behavior:
        honest_n() must NEVER silently return a smaller count.
        """
        records = [
            {"trial_id": "aaa", "status": "complete"},
            {"trial_id": "bbb", "status": "rejected"},
        ]
        path = _write_jsonl(records)
        with pytest.raises(RuntimeError, match="honest-n-classification"):
            honest_n_deflation_denominator(path)

    def test_empty_ledger_without_classification_raises(self):
        """Empty ledger has no classification record → raises."""
        path = _write_jsonl([])
        with pytest.raises(RuntimeError, match="honest-n-classification"):
            honest_n_deflation_denominator(path)


# ---------------------------------------------------------------------------
# 4. Spawn + complete for same trial_id counts as ONE slot
# ---------------------------------------------------------------------------

class TestCollapse:
    """Collapse logic: one slot per distinct trial_id, not per line."""

    def test_spawn_complete_same_id_counts_once(self):
        """A spawn line + a complete line for the same trial_id = ONE slot.

        This is the IC-9 acceptance test (CTO acceptance_tests[2] — kills the 49 bug).
        """
        records = [
            _classification_record(["trial-x"], []),
            # Same trial_id, two rows (spawn then complete).
            {"trial_id": "trial-x", "status": "spawned"},
            {"trial_id": "trial-x", "status": "complete"},  # last-wins
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"spawn+complete for the same trial_id must count as 1, not 2; got {n}"
        )

    def test_three_lines_same_id_counts_once(self):
        """Three lines for same trial_id (spawn, update, complete) = ONE slot."""
        records = [
            _classification_record(["t1"], []),
            {"trial_id": "t1", "status": "spawned"},
            {"trial_id": "t1", "status": "exploratory"},
            {"trial_id": "t1", "status": "complete"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"Three lines for same trial_id → 1 slot; got {n}"

    def test_event_lines_without_trial_id_skipped(self):
        """Non-trial metadata records (no trial_id) do not add slots.

        This is the IC-9 acceptance test (CTO acceptance_tests[3] — event-only lines).
        """
        records = [
            _classification_record(["real-trial"], []),
            {"event": "strategy-archived", "detail": "some info"},  # no trial_id
            {"trial_id": "real-trial", "status": "complete"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"Lines without trial_id must be skipped; got {n}"
        )


# ---------------------------------------------------------------------------
# 5. Ambiguous / unknown status counts (SD2 over-deflate rule)
# ---------------------------------------------------------------------------

class TestAmbiguousStatus:
    """Unknown or archive-event status must be counted, not dropped (SD2)."""

    def test_unknown_status_counts(self):
        """A trial with status='unknown' (e.g. fa0f982a archive line) must count.

        HoQR rule: 'DEFAULT_when_ambiguous: COUNT IT'. This fixes the silent-drop
        bug in compute_honest_n's else-branch.
        """
        records = [
            _classification_record(["ambig-1"], []),
            {"trial_id": "ambig-1", "status": "unknown"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"unknown status must count (SD2); got {n}"

    def test_missing_status_field_counts(self):
        """A trial with no status field at all must count (conservative default)."""
        records = [
            _classification_record(["no-status"], []),
            {"trial_id": "no-status", "event": "strategy-archived",
             "counts_toward_deflation_denominator": True},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, f"no-status with explicit flag=true must count; got {n}"

    def test_pre_registered_frozen_counts(self):
        """pre-registered-frozen-pending-receipt status must count (not dropped)."""
        records = [
            _classification_record(["frozen-1"], []),
            {"trial_id": "frozen-1", "status": "pre-registered-frozen-pending-receipt"},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 1, (
            f"pre-registered-frozen-pending-receipt must count; got {n}"
        )


# ---------------------------------------------------------------------------
# 6. Classification record arithmetic
# ---------------------------------------------------------------------------

class TestClassificationArithmetic:
    """Legacy counted list drives base N; new trials increment it mechanically."""

    def test_classification_n_matches_counted_list(self):
        """Classification record with 3 counted ids → base N = 3."""
        records = [
            _classification_record(["a", "b", "c"], []),
            {"trial_id": "a", "status": "complete", "sharpe": 0.5},
            {"trial_id": "b", "status": "rejected", "sharpe": 0.1},
            {"trial_id": "c", "status": "complete", "sharpe": 0.7},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 3, f"3 counted legacy ids → base N=3; got {n}"

    def test_zero_counted_zero_new(self):
        """classification with 0 counted ids, no new trials → returns 0."""
        records = [_classification_record([], [])]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 0, f"0 + 0 = 0; got {n}"

    def test_new_trial_increments_by_one(self):
        """A new trial (not in classification record) appended after the record increments N by 1."""
        records = [
            _classification_record(["base-1"], []),
            {"trial_id": "base-1", "strategy": "carry", "status": "complete", "sharpe": 0.5},
            # New trial not in either list → classify mechanically → count
            {"trial_id": "new-1", "strategy": "momentum", "status": "complete", "sharpe": 0.8},
        ]
        path = _write_jsonl(records)
        n = honest_n_deflation_denominator(path)
        assert n == 2, f"1 legacy + 1 new genuine draw = 2; got {n}"


# ---------------------------------------------------------------------------
# 7. Regression: compute_honest_n must NOT appear at DSR call sites
# ---------------------------------------------------------------------------

class TestNoDeduplicateFeedsDSR:
    """compute_honest_n (the 11-view) must not appear at any live DSR call site."""

    def test_run_trial_does_not_call_compute_honest_n(self):
        """run_trial.py must not import or call compute_honest_n for DSR."""
        run_trial_src = Path("src/forex_system/harness/run_trial.py").read_text()
        assert "compute_honest_n" not in run_trial_src, (
            "run_trial.py must not call compute_honest_n (the de-dup 11-view) — "
            "it must use honest_n_deflation_denominator for the DSR denominator."
        )

    def test_run_falsification_does_not_call_compute_honest_n(self):
        """run_falsification_trial.py must not import or call compute_honest_n for DSR."""
        script_src = Path("scripts/run_falsification_trial.py").read_text()
        assert "compute_honest_n" not in script_src, (
            "run_falsification_trial.py must not call compute_honest_n — "
            "it must use honest_n_deflation_denominator for the DSR denominator."
        )

    def test_count_prior_trials_not_at_live_call_sites(self):
        """_count_prior_trials raw-line-count must not be called at either live DSR site.

        The raw-line-count is wrong (IC-9 violation). It has been replaced by
        honest_n_deflation_denominator at both run_trial.py and run_falsification_trial.py.
        Its body now raises NotImplementedError (regression guard).
        """
        from forex_system.harness.run_trial import _count_prior_trials
        with pytest.raises(NotImplementedError, match="honest_n_deflation_denominator"):
            _count_prior_trials()


# ---------------------------------------------------------------------------
# 8. IC-9 full denominator helper
# ---------------------------------------------------------------------------

class TestIC9Denominator:
    """ic9_dsr_denominator composes org_n + IS_search + attempt_budget."""

    def test_ic9_adds_is_search_and_budget(self):
        """Full IC-9 denominator = org_n + is_search_family + forward_budget."""
        records = [
            _classification_record(["a", "b", "c"], []),
            {"trial_id": "a", "status": "complete", "sharpe": 0.1},
            {"trial_id": "b", "status": "rejected", "sharpe": 0.2},
            {"trial_id": "c", "status": "complete", "sharpe": 0.3},
        ]
        path = _write_jsonl(records)
        # org_n = 3; is_search=3; budget=2 → n_dsr = 8
        n_dsr = ic9_dsr_denominator(path, is_search_family_size=3, forward_attempt_budget=2)
        assert n_dsr == 8, f"3 + 3 + 2 = 8; got {n_dsr}"

    def test_ic9_zero_search_zero_budget(self):
        """Single frozen structure, budget=1: n_dsr = org_n + 0 + 1."""
        counted = [f"t{i}" for i in range(5)]
        records = [_classification_record(counted, [])] + [
            {"trial_id": tid, "status": "complete", "sharpe": 0.1} for tid in counted
        ]
        path = _write_jsonl(records)
        n_dsr = ic9_dsr_denominator(path, is_search_family_size=0, forward_attempt_budget=1)
        assert n_dsr == 6, f"5 + 0 + 1 = 6; got {n_dsr}"

    def test_ic9_strictly_ge_org_n(self):
        """ic9_dsr_denominator must always be >= honest_n_deflation_denominator."""
        counted = ["x", "y", "z"]
        records = [_classification_record(counted, [])] + [
            {"trial_id": tid, "status": "complete", "sharpe": 0.1} for tid in counted
        ]
        path = _write_jsonl(records)
        org_n = honest_n_deflation_denominator(path)
        n_dsr = ic9_dsr_denominator(path, is_search_family_size=2, forward_attempt_budget=1)
        assert n_dsr >= org_n, f"IC-9 denominator must be >= org_n ({org_n}); got {n_dsr}"
