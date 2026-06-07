"""QRB-6 CONFIRMATORY tests (trial 53981a4a).

The confirmatory re-uses the EXACT exploratory QRB-6 pipeline on a FORWARD event
window [window_start, window_end].  These tests verify, ADDITIVELY (without
breaking the exploratory path):

  1. apply_date_window filters event sets correctly (synthetic events in/out).
  2. The exploratory path is UNAFFECTED (regression): no-window → unchanged;
     enforce_exploratory_count default still guards 506.
  3. The qrb6_confirmatory receipt-target field-spec (n_sel==1, distinct sr0_note,
     window_start, reused cost-manifest sha, p-threshold fields present).
  4. Empty-forward-window → RULE-0 (the runner HALTs, never silently passes).
  5. The forward_acquisition_stub is a DO-NOT-RUN-YET stub (raises NotImplementedError).

kill_test_executed: false (no statistical computation on real return data).
no-capital-instruction: true
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Repo layout helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_CALENDAR_PATH = _REPO_ROOT / "data" / "rates" / "cb_decision_dates.parquet"
_CUT_SCRIPT_PATH = _REPO_ROOT / "scripts" / "cut_freeze_receipt.py"
_RUN_QRB6_PATH = _REPO_ROOT / "scripts" / "run_qrb6.py"

# Frozen exploratory cost manifest sha (REUSED verbatim by the confirmatory).
_FROZEN_COST_MANIFEST_SHA = (
    "6ec6937e6a8de84e32c49001c68d0335cc72b5c2932676eba73f4f6514c8b283"
)
# Forbidden cross-trial sr0_pp literals for the confirmatory.
_EXPLORATORY_SR0_PP = 0.026861   # fa0f982a N_sel=3 — forbidden for confirmatory
_R5_SR0_PP = 0.022906            # R5-only — forbidden
_CARRY_CONF_SR0_PP = 0.034921    # carry-confirmatory — forbidden


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _load_targets() -> dict:
    return _load_module("cut_freeze_receipt", _CUT_SCRIPT_PATH)._TARGETS  # type: ignore[attr-defined]


def _synthetic_event_set() -> pd.DataFrame:
    """Synthetic event set spanning the exploratory terminus and the forward window."""
    return pd.DataFrame(
        {
            "bank": ["FED", "BOJ", "RBA", "BOC", "FED", "BOJ"],
            "currency": ["USD", "JPY", "AUD", "CAD", "USD", "JPY"],
            "date": pd.to_datetime(
                [
                    "2026-03-18",  # before exploratory terminus — OUT of forward window
                    "2026-04-06",  # exact exploratory terminus — OUT (window starts 04-07)
                    "2026-04-07",  # window_start — IN (inclusive)
                    "2026-09-15",  # mid-window — IN
                    "2027-01-01",  # window_end — IN (inclusive)
                    "2027-06-01",  # after window_end — OUT
                ]
            ),
            "verification": ["verified-official"] * 6,
        }
    )


# ---------------------------------------------------------------------------
# 1. apply_date_window filters correctly
# ---------------------------------------------------------------------------


class TestApplyDateWindow:
    @pytest.fixture(autouse=True)
    def _import(self):
        from forex_system.harness.qrb6_decision import apply_date_window
        self.apply = apply_date_window
        self.events = _synthetic_event_set()

    def test_forward_window_keeps_only_in_window_events(self):
        """[2026-04-07, 2027-01-01] inclusive → keeps the 3 in-window dates."""
        out = self.apply(self.events, "2026-04-07", "2027-01-01")
        assert len(out) == 3
        dates = set(out["date"].dt.strftime("%Y-%m-%d"))
        assert dates == {"2026-04-07", "2026-09-15", "2027-01-01"}

    def test_window_start_is_inclusive(self):
        """A date exactly on window_start is KEPT."""
        out = self.apply(self.events, "2026-04-07", "2027-12-31")
        assert "2026-04-07" in set(out["date"].dt.strftime("%Y-%m-%d"))

    def test_window_end_is_inclusive(self):
        """A date exactly on window_end is KEPT."""
        out = self.apply(self.events, "2026-04-07", "2027-01-01")
        assert "2027-01-01" in set(out["date"].dt.strftime("%Y-%m-%d"))

    def test_exploratory_terminus_excluded(self):
        """2026-04-06 (the exploratory terminus) is OUT — zero overlap with fa0f982a."""
        out = self.apply(self.events, "2026-04-07", "2027-01-01")
        assert "2026-04-06" not in set(out["date"].dt.strftime("%Y-%m-%d"))
        assert "2026-03-18" not in set(out["date"].dt.strftime("%Y-%m-%d"))

    def test_no_window_returns_unchanged(self):
        """Both endpoints None → event set returned UNCHANGED (exploratory invariance)."""
        out = self.apply(self.events, None, None)
        assert out is self.events  # identity — no copy, no filter
        assert len(out) == 6

    def test_index_reset_after_filter(self):
        """Filtered result has a reset integer index (required by the iterrows loop)."""
        out = self.apply(self.events, "2026-04-07", "2027-01-01")
        assert list(out.index) == [0, 1, 2]

    def test_empty_when_no_events_in_window(self):
        """A forward window with no events yields an EMPTY frame (runner RULE-0s on it)."""
        out = self.apply(self.events, "2028-01-01", "2029-01-01")
        assert len(out) == 0


# ---------------------------------------------------------------------------
# 2. Exploratory path unaffected (regression)
# ---------------------------------------------------------------------------


class TestExploratoryRegression:
    def test_build_default_still_enforces_506(self):
        """Default build (no flag) still enforces the frozen 506-count guard."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        if not _CALENDAR_PATH.exists():
            pytest.skip(f"Calendar parquet not present: {_CALENDAR_PATH}")
        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        assert len(event_set) == 506

    def test_build_wrong_count_raises_by_default(self):
        """A short calendar must STILL raise under the default exploratory guard."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        df = _synthetic_event_set()  # 6 rows, not 506
        with pytest.raises(ValueError, match="count mismatch"):
            build_scenario_a_event_set(calendar_df=df)

    def test_confirmatory_relaxes_count_guard(self):
        """enforce_exploratory_count=False (confirmatory) does NOT raise on != 506."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        df = _synthetic_event_set()
        out = build_scenario_a_event_set(
            calendar_df=df, enforce_exploratory_count=False
        )
        # 6 distinct dates, all verified-official Scenario-A banks → 6 deduped rows
        assert len(out) == 6

    def test_apply_window_none_is_noop_on_built_set(self):
        """apply_date_window(None, None) on a built set returns it unchanged."""
        from forex_system.harness.qrb6_decision import (
            apply_date_window,
            build_scenario_a_event_set,
        )

        if not _CALENDAR_PATH.exists():
            pytest.skip(f"Calendar parquet not present: {_CALENDAR_PATH}")
        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        out = apply_date_window(event_set, None, None)
        assert out is event_set
        assert len(out) == 506


# ---------------------------------------------------------------------------
# 3. qrb6_confirmatory receipt-target field-spec
# ---------------------------------------------------------------------------


class TestConfirmatoryFreezeTarget:
    @pytest.fixture(scope="class")
    def targets(self) -> dict:
        return _load_targets()

    @pytest.fixture(scope="class")
    def conf(self, targets) -> dict:
        assert "qrb6_confirmatory" in targets, (
            "cut_freeze_receipt._TARGETS must have a 'qrb6_confirmatory' key."
        )
        return targets["qrb6_confirmatory"]

    def test_prereg_and_receipt_paths(self, conf):
        assert str(conf["prereg_path"]) == (
            "references/pre-registrations/qrb6_confirmatory_cb_event_study.md"
        )
        assert str(conf["receipt_path"]) == (
            "references/pre-registrations/"
            "qrb6_confirmatory_cb_event_study.FREEZE-RECEIPT.yaml"
        )

    def test_trial_id(self, conf):
        assert conf["fields"]["trial_id"] == "53981a4a"

    def test_n_sel_is_one(self, conf):
        """N_sel=1 — the structure is pre-committed; the selection charge is removed."""
        assert conf["fields"]["n_sel"] == 1

    def test_window_start_frozen(self, conf):
        """window_start is the frozen forward rule 2026-04-07 (strictly > 2026-04-06)."""
        assert conf["fields"]["window_start"] == "2026-04-07"

    def test_window_end_is_assembly_placeholder(self, conf):
        """window_end is a Math-derived look date — [ASSEMBLY] placeholder pre-freeze."""
        assert conf["fields"]["window_end"] == "[ASSEMBLY]"

    def test_cost_manifest_sha_reuses_frozen_exploratory(self, conf):
        """Confirmatory REUSES the frozen exploratory cost manifest sha verbatim."""
        assert conf["fields"]["cost_manifest_sha256"] == _FROZEN_COST_MANIFEST_SHA

    def test_dsr_and_spread_z(self, conf):
        assert conf["fields"]["dsr_threshold"] == 0.95
        assert conf["fields"]["spread_z_threshold"] == 3.0

    def test_p_threshold_fields_present(self, conf):
        """The confirmatory has its OWN p_reject/p_straddle (placeholders pre-assembly)."""
        for field in ("p_reject_threshold", "p_straddle_hi", "kill_switch_threshold"):
            assert field in conf["fields"], f"missing {field}"

    def test_sr0_note_distinct_from_exploratory(self, conf):
        """sr0_note must name N_sel=1 confirmatory and disavow the other trials' values."""
        note = conf["fields"]["sr0_note"]
        assert "N_sel=1" in note
        assert "NOT exploratory fa0f982a" in note
        assert "NOT R5" in note
        assert "NOT carry-confirmatory" in note

    def test_sr0_pp_not_forbidden_literal(self, conf):
        """If sr0_pp is filled (not [ASSEMBLY]), it must not be a forbidden cross-trial value."""
        sr0 = conf["fields"]["sr0_pp"]
        if isinstance(sr0, float):
            for forbidden in (_EXPLORATORY_SR0_PP, _R5_SR0_PP, _CARRY_CONF_SR0_PP):
                assert abs(sr0 - forbidden) > 1e-6, (
                    f"confirmatory sr0_pp={sr0} equals forbidden {forbidden}"
                )

    def test_prior_targets_still_present(self, targets):
        """The 3 prior receipt targets are untouched (additive change only)."""
        for key in ("r5", "confirmatory", "qrb6"):
            assert key in targets, f"prior target {key!r} missing — non-additive change"

    def test_prior_target_fields_unchanged(self, targets):
        """Spot-check the prior targets' immutable sr0_pp values are unchanged."""
        assert targets["r5"]["fields"]["sr0_pp"] == pytest.approx(0.022906, abs=1e-9)
        assert targets["confirmatory"]["fields"]["sr0_pp"] == pytest.approx(
            0.034921, abs=1e-9
        )
        assert targets["qrb6"]["fields"]["sr0_pp"] == pytest.approx(0.026861, abs=1e-9)


# ---------------------------------------------------------------------------
# 4. Empty-forward-window → RULE-0
# ---------------------------------------------------------------------------


class TestEmptyForwardWindowRule0:
    def test_empty_window_raises_rule0(self, monkeypatch):
        """A forward window that selects zero events must RULE-0 (RuntimeError), not pass."""
        run_qrb6 = _load_module("run_qrb6", _RUN_QRB6_PATH)

        # Build the real (506-row) event set, then choose a forward window that is
        # entirely AFTER the calendar terminus → zero events → RULE-0.
        if not _CALENDAR_PATH.exists():
            pytest.skip(f"Calendar parquet not present: {_CALENDAR_PATH}")

        receipt = {
            "master_seed": 53981,
            "K": 100,
            "sr0_pp": 0.01,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.05,
            "p_reject_threshold": 0.04,
            "kill_switch_threshold": 1.0,
            "trial_id": "53981a4a",
            "n_sel": 1,
            "window_start": "2099-01-01",
            "window_end": "2099-12-31",
        }
        with pytest.raises(RuntimeError, match="empty|ZERO|RULE_0"):
            run_qrb6._run_pipeline(
                receipt=receipt,
                dry_run=True,
                date_window=("2099-01-01", "2099-12-31"),
            )


# ---------------------------------------------------------------------------
# 5. Forward-acquisition stub is DO-NOT-RUN-YET
# ---------------------------------------------------------------------------


class TestForwardAcquisitionStub:
    def test_stub_raises_not_implemented(self):
        """forward_acquisition_stub() is a DO-NOT-RUN-YET stub; calling it raises."""
        run_qrb6 = _load_module("run_qrb6_stub", _RUN_QRB6_PATH)
        with pytest.raises(NotImplementedError, match="PRE-LOOK OBLIGATION"):
            run_qrb6.forward_acquisition_stub()
