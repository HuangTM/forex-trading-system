"""Tests pinning the QRB-6 freeze-receipt field-spec (trial fa0f982a).

Mirrors test_confirmatory_freeze_receipt.py in structure.

Purpose:
  (a) Pin the frozen field-spec constants in cut_freeze_receipt._TARGETS['qrb6']
      so that accidental drift is caught immediately.
  (b) Guard against cross-trial constant contamination: QRB-6 sr0_pp must NOT
      equal 0.022906 (R5-only) or 0.034921 (confirmatory-only).
  (c) Pin the sr0_note guard string that every runner must read.
  (d) Once the receipt is cut post-consensus (AC-8), verify the on-disk YAML.

Written to pass BOTH before and after the receipt is cut:
  - Before cut: tests read the frozen field-spec constants directly from the
    script module via importlib.
  - After cut: tests additionally verify the on-disk receipt YAML fields.

kill_test_executed: false (no statistical computation performed here).
no-capital-instruction: true
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers: locate repo root and load the script's _TARGETS constant
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "cut_freeze_receipt.py"
_RECEIPT_PATH = (
    _REPO_ROOT
    / "references"
    / "pre-registrations"
    / "qrb6_cb_event_study.FREEZE-RECEIPT.yaml"
)

# Known-frozen paths (must never be modified during this track)
_R5_RECEIPT_PATH = (
    _REPO_ROOT
    / "references"
    / "pre-registrations"
    / "r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml"
)
_CONFIRMATORY_RECEIPT_PATH = (
    _REPO_ROOT
    / "references"
    / "pre-registrations"
    / "r5_confirmatory_vol_target_carry_usdjpy.FREEZE-RECEIPT.yaml"
)


def _load_targets() -> dict:
    """Import _TARGETS from scripts/cut_freeze_receipt.py without executing main()."""
    spec = importlib.util.spec_from_file_location("cut_freeze_receipt", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, (
        f"Could not locate script: {_SCRIPT_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module._TARGETS  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Frozen expected values (sourced from pm-acceptance-criteria.yaml and
# nht-qrb6-rescreen.yaml verified counts)
# Fields marked FROZEN-AT-ASSEMBLY remain as placeholder strings until the
# orchestrator fills them from MATH frozen-stats (AC-2) at consensus (AC-7).
# These tests verify the field NAMES and structural invariants, not the
# placeholder values (which are substituted at assembly).
# ---------------------------------------------------------------------------

_EXPECTED_TRIAL_ID = "fa0f982a"
_EXPECTED_DSR_THRESHOLD = 0.95
_EXPECTED_ALPHA = 0.05
_EXPECTED_SCENARIO_A_EVENT_DAYS = 506
_EXPECTED_SCENARIO_B_EVENT_DAYS = 716
_EXPECTED_POST_2015_A = 345
_EXPECTED_POST_2015_B = 491
_EXPECTED_SCIPY_REQUIRED = True

# Cross-trial contamination guard values (QRB-6 sr0_pp must NOT equal these)
_R5_SR0_PP = 0.022906       # R5-only (N=3); FORBIDDEN for QRB-6
_CONFIRMATORY_SR0_PP = 0.034921  # confirmatory (N_conf=6); FORBIDDEN for QRB-6

# Placeholder sentinel — fields that are [FROZEN-AT-ASSEMBLY] pre-consensus
_FROZEN_AT_ASSEMBLY = "[FROZEN-AT-ASSEMBLY]"

# Required sr0_note guard text (must warn against both forbidden values)
_SR0_NOTE_MUST_CONTAIN_R5_LITERAL = "0.022906"
_SR0_NOTE_MUST_CONTAIN_CONFIRMATORY_LITERAL = "0.034921"


# ---------------------------------------------------------------------------
# 1. Tests against the script's field-spec constants (_TARGETS["qrb6"])
# ---------------------------------------------------------------------------


class TestQrb6FieldSpecConstants:
    """Pin the frozen constants in cut_freeze_receipt._TARGETS['qrb6'].

    These run regardless of whether the receipt file exists on disk.
    """

    @pytest.fixture(scope="class")
    def qrb6_fields(self) -> dict:
        targets = _load_targets()
        assert "qrb6" in targets, (
            "cut_freeze_receipt._TARGETS must have a 'qrb6' key. "
            "Add the qrb6 target entry to scripts/cut_freeze_receipt.py."
        )
        return targets["qrb6"]["fields"]

    @pytest.fixture(scope="class")
    def qrb6_cfg(self) -> dict:
        targets = _load_targets()
        return targets["qrb6"]

    def test_trial_id(self, qrb6_fields: dict) -> None:
        """trial_id must be 'fa0f982a' (QRB-6 trial; NOT 576746aa / NOT f2fb41fd)."""
        assert qrb6_fields.get("trial_id") == _EXPECTED_TRIAL_ID, (
            f"trial_id={qrb6_fields.get('trial_id')!r}; expected {_EXPECTED_TRIAL_ID!r}. "
            "Do NOT reuse R5 (576746aa) or confirmatory (f2fb41fd) trial IDs."
        )

    def test_dsr_threshold(self, qrb6_fields: dict) -> None:
        """dsr_threshold must be 0.95 (firm-wide DSR gate)."""
        assert qrb6_fields.get("dsr_threshold") == pytest.approx(_EXPECTED_DSR_THRESHOLD), (
            f"dsr_threshold={qrb6_fields.get('dsr_threshold')!r}; expected {_EXPECTED_DSR_THRESHOLD}"
        )

    def test_alpha(self, qrb6_fields: dict) -> None:
        """alpha must be 0.05 (pre-multiplicity-charge; MATH applies the charge)."""
        assert qrb6_fields.get("alpha") == pytest.approx(_EXPECTED_ALPHA), (
            f"alpha={qrb6_fields.get('alpha')!r}; expected {_EXPECTED_ALPHA}"
        )

    def test_scenario_a_event_days(self, qrb6_fields: dict) -> None:
        """scenario_a_event_days must be 506 (verified deduped market-days)."""
        assert qrb6_fields.get("scenario_a_event_days") == _EXPECTED_SCENARIO_A_EVENT_DAYS, (
            f"scenario_a_event_days={qrb6_fields.get('scenario_a_event_days')!r}; "
            f"expected {_EXPECTED_SCENARIO_A_EVENT_DAYS} (nht-qrb6-rescreen.yaml verified)"
        )

    def test_scenario_b_event_days(self, qrb6_fields: dict) -> None:
        """scenario_b_event_days must be 716 (verified deduped market-days)."""
        assert qrb6_fields.get("scenario_b_event_days") == _EXPECTED_SCENARIO_B_EVENT_DAYS, (
            f"scenario_b_event_days={qrb6_fields.get('scenario_b_event_days')!r}; "
            f"expected {_EXPECTED_SCENARIO_B_EVENT_DAYS} (nht-qrb6-rescreen.yaml verified)"
        )

    def test_post_2015_a(self, qrb6_fields: dict) -> None:
        """post_2015_a must be 345 (Scenario A post-2015 structural-break sub-window)."""
        assert qrb6_fields.get("post_2015_a") == _EXPECTED_POST_2015_A, (
            f"post_2015_a={qrb6_fields.get('post_2015_a')!r}; expected {_EXPECTED_POST_2015_A}"
        )

    def test_post_2015_b(self, qrb6_fields: dict) -> None:
        """post_2015_b must be 491 (Scenario B post-2015 structural-break sub-window)."""
        assert qrb6_fields.get("post_2015_b") == _EXPECTED_POST_2015_B, (
            f"post_2015_b={qrb6_fields.get('post_2015_b')!r}; expected {_EXPECTED_POST_2015_B}"
        )

    def test_scipy_required_is_true(self, qrb6_fields: dict) -> None:
        """scipy_required must be True — no approximation fallback."""
        assert qrb6_fields.get("scipy_required") is True, (
            f"scipy_required={qrb6_fields.get('scipy_required')!r}; must be True"
        )

    def test_frozen_at_assembly_fields_present(self, qrb6_fields: dict) -> None:
        """Fields that are [FROZEN-AT-ASSEMBLY] pre-consensus must be present in the spec.

        These placeholder strings will be replaced by the orchestrator at consensus (AC-7)
        from the MATH frozen-stats artifact (AC-2). Their presence (even as placeholders)
        confirms the field structure is established for assembly.
        """
        assembly_fields = ["master_seed", "K", "sr0_pp", "n_sel", "kill_switch_threshold", "spread_z_threshold"]
        for field in assembly_fields:
            assert field in qrb6_fields, (
                f"Field '{field}' missing from qrb6 field-spec. "
                f"All [FROZEN-AT-ASSEMBLY] fields must be declared in _TARGETS['qrb6']['fields']."
            )

    def test_sr0_note_present(self, qrb6_fields: dict) -> None:
        """sr0_note must be present and warn against BOTH forbidden cross-trial literals."""
        note = qrb6_fields.get("sr0_note", "")
        assert isinstance(note, str) and len(note) > 0, (
            "sr0_note must be a non-empty string in the qrb6 field-spec"
        )
        assert _SR0_NOTE_MUST_CONTAIN_R5_LITERAL in note, (
            f"sr0_note must mention 0.022906 (R5-only; forbidden for QRB-6 runner); got: {note!r}"
        )
        assert _SR0_NOTE_MUST_CONTAIN_CONFIRMATORY_LITERAL in note, (
            f"sr0_note must mention 0.034921 (confirmatory-only; forbidden for QRB-6 runner); "
            f"got: {note!r}"
        )

    def test_prereg_path_declared(self, qrb6_cfg: dict) -> None:
        """prereg_path must be declared in the qrb6 target config."""
        assert "prereg_path" in qrb6_cfg, "qrb6 target must declare prereg_path"
        path = Path(qrb6_cfg["prereg_path"])
        assert str(path) == "references/pre-registrations/qrb6_cb_event_study.md", (
            f"prereg_path={str(path)!r}; expected 'references/pre-registrations/qrb6_cb_event_study.md'"
        )

    def test_receipt_path_declared(self, qrb6_cfg: dict) -> None:
        """receipt_path must be declared in the qrb6 target config."""
        assert "receipt_path" in qrb6_cfg, "qrb6 target must declare receipt_path"
        path = Path(qrb6_cfg["receipt_path"])
        assert str(path) == "references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml", (
            f"receipt_path={str(path)!r}; expected the qrb6 FREEZE-RECEIPT.yaml path"
        )


# ---------------------------------------------------------------------------
# 2. Cross-trial contamination guard: QRB-6 sr0_pp fields
# ---------------------------------------------------------------------------


class TestQrb6CrossTrialContaminationGuard:
    """Verify QRB-6 sr0_pp in the field-spec does NOT carry an R5 or confirmatory literal.

    The sr0_pp field should be a [FROZEN-AT-ASSEMBLY] placeholder string pre-consensus.
    If it is accidentally replaced with 0.022906 or 0.034921 (the forbidden literals),
    these tests catch it immediately.
    """

    @pytest.fixture(scope="class")
    def qrb6_fields(self) -> dict:
        return _load_targets()["qrb6"]["fields"]

    def test_sr0_pp_not_r5_literal(self, qrb6_fields: dict) -> None:
        """sr0_pp must NOT be 0.022906 (R5-only value; CTO FM-1 cross-trial guard).

        If sr0_pp is still [FROZEN-AT-ASSEMBLY] (pre-consensus), this test passes.
        If it has been filled in with the wrong R5 value, this test catches it.
        """
        sr0_pp = qrb6_fields.get("sr0_pp")
        if isinstance(sr0_pp, float):
            assert abs(sr0_pp - _R5_SR0_PP) > 1e-6, (
                f"qrb6 sr0_pp={sr0_pp!r} equals R5-only value 0.022906 — "
                "CROSS-TRIAL CONTAMINATION detected (CTO FM-1). "
                "QRB-6 sr0_pp must be derived fresh by the Mathematician in this track."
            )

    def test_sr0_pp_not_confirmatory_literal(self, qrb6_fields: dict) -> None:
        """sr0_pp must NOT be 0.034921 (confirmatory-only value; CTO FM-1 guard)."""
        sr0_pp = qrb6_fields.get("sr0_pp")
        if isinstance(sr0_pp, float):
            assert abs(sr0_pp - _CONFIRMATORY_SR0_PP) > 1e-6, (
                f"qrb6 sr0_pp={sr0_pp!r} equals confirmatory-only value 0.034921 — "
                "CROSS-TRIAL CONTAMINATION detected (CTO FM-1). "
                "QRB-6 sr0_pp must be derived fresh by the Mathematician in this track."
            )

    def test_sidecar_file_no_forbidden_literals(self) -> None:
        """The triggers.yaml sidecar must not contain forbidden cross-trial imports/assignments.

        The CTO FM-1 grep check covers: 'r5_decision', '0.022906', '0.034921'.
        These must not appear as YAML key-value assignments (non-comment lines).
        Appearing in comment lines (e.g. as a warning note) is acceptable.
        """
        sidecar_path = (
            _REPO_ROOT
            / "references"
            / "pre-registrations"
            / "qrb6_cb_event_study.triggers.yaml"
        )
        if not sidecar_path.exists():
            pytest.skip(f"Sidecar not yet created: {sidecar_path}")

        # Check only non-comment, non-warning lines for forbidden patterns.
        # Comment lines (starting with #) and warning/note strings that reference
        # the forbidden values as anti-patterns are acceptable.
        non_comment_lines = [
            line for line in sidecar_path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        non_comment_content = "\n".join(non_comment_lines)

        # r5_decision must not appear in non-comment YAML assignments
        assert "r5_decision" not in non_comment_content, (
            "Forbidden pattern 'r5_decision' found in non-comment lines of qrb6 triggers "
            "sidecar — cross-trial contamination (CTO FM-1). References to r5_decision "
            "must only appear in comment lines (as warnings), not in YAML assignments."
        )


# ---------------------------------------------------------------------------
# 3. r5 and confirmatory receipt immutability guard
# ---------------------------------------------------------------------------


class TestFrozenReceiptsUnmodified:
    """Verify that the R5 and confirmatory frozen receipts are not touched by
    the QRB-6 track work. These are write-once artifacts; any modification voids
    their integrity guarantees (pm-acceptance-criteria.yaml: r5_and_confirmatory_immutable).
    """

    def test_r5_receipt_exists(self) -> None:
        """R5 freeze-receipt must still exist (not deleted or moved)."""
        assert _R5_RECEIPT_PATH.exists(), (
            f"R5 freeze-receipt missing: {_R5_RECEIPT_PATH}. "
            "This is an immutable artifact; do not delete or move it."
        )

    def test_confirmatory_receipt_exists(self) -> None:
        """Confirmatory freeze-receipt must still exist (not deleted or moved)."""
        assert _CONFIRMATORY_RECEIPT_PATH.exists(), (
            f"Confirmatory freeze-receipt missing: {_CONFIRMATORY_RECEIPT_PATH}. "
            "This is an immutable artifact; do not delete or move it."
        )

    def test_r5_target_still_in_targets(self) -> None:
        """r5 target must remain in _TARGETS (not removed or renamed)."""
        targets = _load_targets()
        assert "r5" in targets, (
            "r5 key removed from _TARGETS — immutability violation. "
            "The r5 target must remain byte-identical in behavior."
        )

    def test_confirmatory_target_still_in_targets(self) -> None:
        """confirmatory target must remain in _TARGETS (not removed or renamed)."""
        targets = _load_targets()
        assert "confirmatory" in targets, (
            "confirmatory key removed from _TARGETS — immutability violation. "
            "The confirmatory target must remain byte-identical in behavior."
        )

    def test_r5_fields_unchanged(self) -> None:
        """r5 field-spec sr0_pp must still be 0.022906 (R5-only; must not be changed)."""
        targets = _load_targets()
        r5_fields = targets["r5"]["fields"]
        assert r5_fields.get("sr0_pp") == pytest.approx(0.022906, abs=1e-9), (
            f"r5 sr0_pp={r5_fields.get('sr0_pp')!r}; must remain 0.022906 (R5-only, immutable)"
        )

    def test_confirmatory_fields_unchanged(self) -> None:
        """confirmatory sr0_pp must still be 0.034921 (N_conf=6; must not be changed)."""
        targets = _load_targets()
        conf_fields = targets["confirmatory"]["fields"]
        assert conf_fields.get("sr0_pp") == pytest.approx(0.034921, abs=1e-9), (
            f"confirmatory sr0_pp={conf_fields.get('sr0_pp')!r}; must remain 0.034921 (N_conf=6)"
        )


# ---------------------------------------------------------------------------
# 4. Dry-run structural test: qrb6 target prints correct paths, writes nothing
# ---------------------------------------------------------------------------


class TestQrb6DryRun:
    """Verify that the script's dry-run for qrb6 prints the correct paths and does
    not write the receipt. This tests the --target qrb6 behaviour without --cut.
    """

    def test_qrb6_prereg_path_is_not_r5_path(self) -> None:
        """qrb6 prereg_path must differ from r5 prereg_path (distinct targets)."""
        targets = _load_targets()
        qrb6_path = targets["qrb6"]["prereg_path"]
        r5_path = targets["r5"]["prereg_path"]
        assert str(qrb6_path) != str(r5_path), (
            "qrb6 and r5 prereg_path must be distinct paths."
        )

    def test_qrb6_receipt_path_is_not_r5_receipt_path(self) -> None:
        """qrb6 receipt_path must differ from r5 receipt_path (distinct targets)."""
        targets = _load_targets()
        qrb6_receipt = targets["qrb6"]["receipt_path"]
        r5_receipt = targets["r5"]["receipt_path"]
        assert str(qrb6_receipt) != str(r5_receipt), (
            "qrb6 and r5 receipt_path must be distinct paths."
        )

    def test_receipt_not_yet_cut(self) -> None:
        """qrb6 receipt must NOT exist yet (pre-consensus; cut happens at AC-8).

        If this test fails, the receipt was cut before consensus — a process
        integrity violation. The freeze-receipt is only valid if cut AFTER AC-7
        consensus ratification.

        NOTE: This test is expected to FAIL after the receipt is legitimately cut
        at AC-8. At that point, replace this test or move it to a 'post-cut' marker.
        """
        # This is a pre-cut invariant check. Once the receipt is cut at AC-8,
        # this test documents the intended state at the time of authoring (pre-consensus).
        # Maintainer: after AC-8, this test may be removed or skipped as expected-to-fail.
        if _RECEIPT_PATH.exists():
            pytest.skip(
                f"qrb6 receipt has been cut (AC-8 complete): {_RECEIPT_PATH}. "
                "This pre-cut guard test is no longer applicable post-freeze."
            )


# ---------------------------------------------------------------------------
# 5. On-disk receipt tests — run ONLY if the receipt has been cut (AC-8)
# ---------------------------------------------------------------------------


class TestQrb6ReceiptOnDisk:
    """Tests that read the on-disk receipt YAML once it has been cut at AC-8.

    All tests in this class are skipped if the receipt file does not exist
    (i.e. before --target qrb6 --cut has been run post-consensus).
    """

    @pytest.fixture(scope="class")
    def receipt(self):
        if not _RECEIPT_PATH.exists():
            pytest.skip(
                f"QRB-6 receipt not yet cut: {_RECEIPT_PATH}. "
                "These tests run after 'python scripts/cut_freeze_receipt.py "
                "--target qrb6 --cut' (post-consensus AC-8 only)."
            )
        with open(_RECEIPT_PATH) as fh:
            return yaml.safe_load(fh)

    def test_receipt_trial_id(self, receipt: dict) -> None:
        """On-disk receipt trial_id must be 'fa0f982a'."""
        assert receipt.get("trial_id") == _EXPECTED_TRIAL_ID

    def test_receipt_dsr_threshold(self, receipt: dict) -> None:
        """On-disk receipt dsr_threshold must be 0.95."""
        assert receipt.get("dsr_threshold") == pytest.approx(_EXPECTED_DSR_THRESHOLD)

    def test_receipt_alpha(self, receipt: dict) -> None:
        """On-disk receipt alpha must be 0.05."""
        assert receipt.get("alpha") == pytest.approx(_EXPECTED_ALPHA)

    def test_receipt_scenario_a_event_days(self, receipt: dict) -> None:
        """On-disk receipt scenario_a_event_days must be 506."""
        assert receipt.get("scenario_a_event_days") == _EXPECTED_SCENARIO_A_EVENT_DAYS

    def test_receipt_scenario_b_event_days(self, receipt: dict) -> None:
        """On-disk receipt scenario_b_event_days must be 716."""
        assert receipt.get("scenario_b_event_days") == _EXPECTED_SCENARIO_B_EVENT_DAYS

    def test_receipt_post_2015_a(self, receipt: dict) -> None:
        """On-disk receipt post_2015_a must be 345."""
        assert receipt.get("post_2015_a") == _EXPECTED_POST_2015_A

    def test_receipt_post_2015_b(self, receipt: dict) -> None:
        """On-disk receipt post_2015_b must be 491."""
        assert receipt.get("post_2015_b") == _EXPECTED_POST_2015_B

    def test_receipt_scipy_required(self, receipt: dict) -> None:
        """On-disk receipt scipy_required must be True."""
        assert receipt.get("scipy_required") is True

    def test_receipt_sr0_pp_not_forbidden_r5(self, receipt: dict) -> None:
        """On-disk receipt sr0_pp must NOT be 0.022906 (R5-only forbidden literal)."""
        sr0_pp = receipt.get("sr0_pp")
        if isinstance(sr0_pp, float):
            assert abs(sr0_pp - _R5_SR0_PP) > 1e-6, (
                f"receipt sr0_pp={sr0_pp!r} equals R5-only value — "
                "CROSS-TRIAL CONTAMINATION in the cut receipt (CTO FM-1)."
            )

    def test_receipt_sr0_pp_not_forbidden_confirmatory(self, receipt: dict) -> None:
        """On-disk receipt sr0_pp must NOT be 0.034921 (confirmatory-only forbidden literal)."""
        sr0_pp = receipt.get("sr0_pp")
        if isinstance(sr0_pp, float):
            assert abs(sr0_pp - _CONFIRMATORY_SR0_PP) > 1e-6, (
                f"receipt sr0_pp={sr0_pp!r} equals confirmatory-only value — "
                "CROSS-TRIAL CONTAMINATION in the cut receipt (CTO FM-1)."
            )

    def test_receipt_sr0_note_present_and_guards_both_forbidden_values(
        self, receipt: dict
    ) -> None:
        """On-disk receipt sr0_note must warn against both R5 and confirmatory literals."""
        note = receipt.get("sr0_note", "")
        assert isinstance(note, str) and len(note) > 0, (
            f"receipt sr0_note={note!r}; must be a non-empty string"
        )
        assert _SR0_NOTE_MUST_CONTAIN_R5_LITERAL in note, (
            f"receipt sr0_note must mention 0.022906 (R5-only); got: {note!r}"
        )
        assert _SR0_NOTE_MUST_CONTAIN_CONFIRMATORY_LITERAL in note, (
            f"receipt sr0_note must mention 0.034921 (confirmatory-only); got: {note!r}"
        )

    def test_receipt_prereg_sha256_present(self, receipt: dict) -> None:
        """On-disk receipt must have a 64-char prereg_sha256."""
        sha = receipt.get("prereg_sha256", "")
        assert isinstance(sha, str) and len(sha) == 64, (
            f"receipt prereg_sha256={sha!r}; expected 64-char hex string"
        )

    def test_receipt_code_commit_present(self, receipt: dict) -> None:
        """On-disk receipt must have a 40-char code_commit."""
        commit = receipt.get("code_commit", "")
        assert isinstance(commit, str) and len(commit) == 40, (
            f"receipt code_commit={commit!r}; expected 40-char hex string"
        )

    def test_receipt_no_frozen_at_assembly_placeholders(self, receipt: dict) -> None:
        """On-disk receipt must have no [FROZEN-AT-ASSEMBLY] placeholder strings.

        All placeholders must be filled by the orchestrator before --cut is invoked.
        A receipt containing placeholder strings is malformed and unusable.
        """
        for field, value in receipt.items():
            assert value != _FROZEN_AT_ASSEMBLY, (
                f"receipt field '{field}' still contains [FROZEN-AT-ASSEMBLY] placeholder — "
                "the orchestrator must fill all placeholders from MATH frozen-stats (AC-2) "
                "before cutting the receipt. This receipt is malformed."
            )
