"""Tests pinning the confirmatory freeze-receipt fields (trial f2fb41fd).

F-006 / NHT-F-1 remediation — ensures that:
  (a) The cut tool's confirmatory field-spec constants in cut_freeze_receipt.py
      carry the correct sr0_pp and scipy_required values; and
  (b) The confirmatory receipt file, once cut, contains the same values.

Written to pass BOTH before and after the receipt is cut:
  - Before cut: tests read the frozen field-spec constants directly from the
    script module (via importlib or direct dict access).
  - After cut: tests additionally verify the on-disk receipt YAML fields.

These are pinning tests — their purpose is to detect accidental drift in the
frozen constants, NOT to test the statistical correctness of the values.

kill_test_executed: false (no statistical computation performed here).
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
    / "r5_confirmatory_vol_target_carry_usdjpy.FREEZE-RECEIPT.yaml"
)


def _load_targets() -> dict:
    """Import _TARGETS from scripts/cut_freeze_receipt.py without executing main()."""
    spec = importlib.util.spec_from_file_location("cut_freeze_receipt", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, f"Could not locate script: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module._TARGETS  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Frozen expected values (sourced from confirmatory pre-reg PART II §2.5, §3.3, §4, §5)
# These are the canonical reference values against which both the script constants
# AND the on-disk receipt are pinned.
# ---------------------------------------------------------------------------

_EXPECTED_SR0_PP = 0.034921  # PART II §2.5: SR0_pp_conf at N_conf=6
_EXPECTED_SR0_ANN = 0.554361  # PART II §2.5: SR0_ann_conf at N_conf=6
_EXPECTED_N_CONF = 6  # PART II §2.4: elected N_conf
_EXPECTED_MASTER_SEED = 924033  # PART II §5 RULE: int('f2fb41', 16) mod 1_000_000 = 15924033 mod 1e6 (rule-exact; stated 924289 was hand-hex drift, corrected)
_EXPECTED_K = 10000  # PART II §1.4
_EXPECTED_Z1 = 2.537988  # PART II §3.3: interim OBF boundary
_EXPECTED_Z2 = 1.662107  # PART II §3.3: terminal OBF boundary (bivariate exact)
_EXPECTED_LOOK1 = "2028-10-06"  # PART II §3.2
_EXPECTED_LOOK2 = "2031-04-06"  # PART II §3.2
_EXPECTED_KST = 1.2906  # PART II §4: kill_switch_threshold
_EXPECTED_TRIAL_ID = "f2fb41fd"
_EXPECTED_DSR_THRESHOLD = 0.95
_EXPECTED_ALPHA = 0.05


# ---------------------------------------------------------------------------
# 1. Tests against the script's field-spec constants (_TARGETS["confirmatory"])
# ---------------------------------------------------------------------------


class TestConfirmatoryFieldSpecConstants:
    """Pin the frozen constants in cut_freeze_receipt._TARGETS['confirmatory'].

    These run regardless of whether the receipt file exists.
    """

    @pytest.fixture(scope="class")
    def conf_fields(self) -> dict:
        targets = _load_targets()
        assert "confirmatory" in targets, (
            "cut_freeze_receipt._TARGETS must have a 'confirmatory' key"
        )
        return targets["confirmatory"]["fields"]

    def test_sr0_pp_is_confirmatory_value(self, conf_fields: dict) -> None:
        """sr0_pp in the confirmatory field-spec must be 0.034921 (N_conf=6, PART II §2.5).

        This is NOT the R5-only SR0_PP=0.022906 (N=3).  A look-runner that reads
        sr0_pp from this receipt (not from r5_decision.SR0_PP) uses the correct benchmark.
        """
        assert conf_fields["sr0_pp"] == pytest.approx(_EXPECTED_SR0_PP, abs=1e-9), (
            f"confirmatory sr0_pp={conf_fields['sr0_pp']!r} != expected {_EXPECTED_SR0_PP}. "
            "Do NOT use r5_decision.SR0_PP (0.022906) for the confirmatory receipt — "
            "that is R5-only (N=3); confirmatory uses N_conf=6."
        )

    def test_scipy_required_is_true(self, conf_fields: dict) -> None:
        """scipy_required must be True — no approximation fallback (PART II §5 A-5 pin)."""
        assert conf_fields.get("scipy_required") is True, (
            f"confirmatory scipy_required={conf_fields.get('scipy_required')!r}; "
            "must be True (PART II §5: scipy.stats.norm.cdf REQUIRED, no approximation)."
        )

    def test_trial_id(self, conf_fields: dict) -> None:
        """trial_id must be 'f2fb41fd' (org-wide counter increment; NOT 576746aa)."""
        assert conf_fields.get("trial_id") == _EXPECTED_TRIAL_ID, (
            f"trial_id={conf_fields.get('trial_id')!r}; expected {_EXPECTED_TRIAL_ID!r}"
        )

    def test_master_seed(self, conf_fields: dict) -> None:
        """master_seed=924033: int('f2fb41',16) mod 1_000_000 = 15924033 mod 1e6 (PART II §5 rule, rule-exact)."""
        assert conf_fields.get("master_seed") == _EXPECTED_MASTER_SEED, (
            f"master_seed={conf_fields.get('master_seed')!r}; expected {_EXPECTED_MASTER_SEED}"
        )

    def test_master_seed_arithmetic_note(self) -> None:
        """Document the seed-arithmetic adjudication for audit transparency.

        History: the pre-reg PART II §5 originally stated FROZEN: master_seed=924289
        via the intermediate `f2fb41 (hex) = 15924289` — a hand-hex drift.  The frozen
        RULE is `int('f2fb41', 16) mod 1_000_000`, and the rule-exact value is
        int('f2fb41', 16) = 15924033 → 924033.  Per the rule-governs adjudication
        (QD flagged + orchestrator verified, logged in spawns.jsonl; PR cycle-2
        verifies), the doc, the receipt tool, and this test all carry the rule-exact
        924033.  The drift and its correction remain disclosed in the pre-reg §5
        FROZEN line for the audit trail.
        """
        stem_hex = "f2fb41"
        actual_hex_value = int(stem_hex, 16)
        actual_mod = actual_hex_value % 1_000_000
        assert actual_hex_value == 15924033, (
            f"int('{stem_hex}', 16) = {actual_hex_value}; expected 15924033 (arithmetic ground truth)."
        )
        assert actual_mod == 924033, "rule-exact master_seed must be 924033"
        # The receipt constant carries the rule-exact value.
        assert _EXPECTED_MASTER_SEED == 924033, "EXPECTED constant must match the rule-exact frozen value"

    def test_k_resamples(self, conf_fields: dict) -> None:
        """K must be 10000 (PART II §1.4; supersedes R5 B=5000 for single-series run)."""
        assert conf_fields.get("K") == _EXPECTED_K, (
            f"K={conf_fields.get('K')!r}; expected {_EXPECTED_K}"
        )

    def test_sr0_ann(self, conf_fields: dict) -> None:
        """sr0_ann must be 0.554361 (PART II §2.5)."""
        assert conf_fields.get("sr0_ann") == pytest.approx(_EXPECTED_SR0_ANN, abs=1e-6), (
            f"sr0_ann={conf_fields.get('sr0_ann')!r}; expected {_EXPECTED_SR0_ANN}"
        )

    def test_n_conf(self, conf_fields: dict) -> None:
        """n_conf must be 6 (PART II §2.4 frozen election)."""
        assert conf_fields.get("n_conf") == _EXPECTED_N_CONF, (
            f"n_conf={conf_fields.get('n_conf')!r}; expected {_EXPECTED_N_CONF}"
        )

    def test_z_boundaries(self, conf_fields: dict) -> None:
        """z1 and z2 must match frozen OBF boundaries (PART II §3.3)."""
        assert conf_fields.get("z1") == pytest.approx(_EXPECTED_Z1, abs=1e-6), (
            f"z1={conf_fields.get('z1')!r}; expected {_EXPECTED_Z1}"
        )
        assert conf_fields.get("z2") == pytest.approx(_EXPECTED_Z2, abs=1e-6), (
            f"z2={conf_fields.get('z2')!r}; expected {_EXPECTED_Z2}"
        )

    def test_look_dates(self, conf_fields: dict) -> None:
        """look1_date and look2_date must match frozen look schedule (PART II §3.2)."""
        assert conf_fields.get("look1_date") == _EXPECTED_LOOK1
        assert conf_fields.get("look2_date") == _EXPECTED_LOOK2

    def test_kill_switch_threshold(self, conf_fields: dict) -> None:
        """kill_switch_threshold must be 1.2906 (PART II §4)."""
        assert conf_fields.get("kill_switch_threshold") == pytest.approx(_EXPECTED_KST, abs=1e-4), (
            f"kill_switch_threshold={conf_fields.get('kill_switch_threshold')!r}; "
            f"expected {_EXPECTED_KST}"
        )

    def test_sr0_note_present_and_warns_against_r5_literal(self, conf_fields: dict) -> None:
        """sr0_note must be present and warn against reusing r5_decision.SR0_PP."""
        note = conf_fields.get("sr0_note", "")
        assert isinstance(note, str) and len(note) > 0, (
            "sr0_note must be a non-empty string in the confirmatory field-spec"
        )
        # Must reference the R5-only value so a reader is warned
        assert "0.022906" in note, (
            f"sr0_note must mention 0.022906 (the R5-only value to avoid); got: {note!r}"
        )

    def test_dsr_threshold(self, conf_fields: dict) -> None:
        """dsr_threshold must be 0.95."""
        assert conf_fields.get("dsr_threshold") == pytest.approx(_EXPECTED_DSR_THRESHOLD)

    def test_alpha(self, conf_fields: dict) -> None:
        """alpha must be 0.05."""
        assert conf_fields.get("alpha") == pytest.approx(_EXPECTED_ALPHA)


# ---------------------------------------------------------------------------
# 2. r5_decision module guard: SR0_PP is R5-only; docstring warns against reuse
# ---------------------------------------------------------------------------


class TestR5DecisionGuard:
    """Pin that r5_decision.SR0_PP is 0.022906 (R5-only) and the module warns
    against reusing it for the confirmatory test.
    """

    def test_r5_sr0_pp_is_r5_only_value(self) -> None:
        """r5_decision.SR0_PP must equal 0.022906 (elected N=3; R5-only)."""
        from forex_system.harness.r5_decision import SR0_PP

        assert SR0_PP == pytest.approx(0.022906, abs=1e-9), (
            f"r5_decision.SR0_PP={SR0_PP!r}; expected 0.022906. "
            "This is R5-only (N=3) and must not be changed."
        )

    def test_r5_sr0_pp_differs_from_confirmatory(self) -> None:
        """The R5 SR0_PP must differ from the confirmatory sr0_pp (0.034921).

        This is the key cross-contamination guard: if these were equal, a
        look-runner reusing r5_decision.SR0_PP would silently pass with the
        wrong (too-lenient) benchmark.
        """
        from forex_system.harness.r5_decision import SR0_PP

        assert abs(SR0_PP - _EXPECTED_SR0_PP) > 0.01, (
            f"r5_decision.SR0_PP={SR0_PP!r} is too close to confirmatory SR0_pp={_EXPECTED_SR0_PP}. "
            "These must be distinct values (R5: N=3; confirmatory: N_conf=6)."
        )

    def test_r5_decision_module_docstring_warns_about_reuse(self) -> None:
        """r5_decision module docstring must contain the reuse warning."""
        import forex_system.harness.r5_decision as r5mod

        doc = r5mod.__doc__ or ""
        assert "confirmatory" in doc.lower() or "f2fb41fd" in doc, (
            "r5_decision module docstring must warn against reusing SR0_PP for "
            "the confirmatory test. Add the cross-trial constant warning."
        )


# ---------------------------------------------------------------------------
# 3. On-disk receipt tests — run ONLY if the receipt has been cut
# ---------------------------------------------------------------------------


class TestConfirmatoryReceiptOnDisk:
    """Tests that read the on-disk receipt YAML once it has been cut.

    All tests in this class are skipped if the receipt file does not exist
    (i.e. before --target confirmatory --cut has been run).
    """

    @pytest.fixture(scope="class")
    def receipt(self):
        if not _RECEIPT_PATH.exists():
            pytest.skip(
                f"Confirmatory receipt not yet cut: {_RECEIPT_PATH}. "
                "These tests run after 'python scripts/cut_freeze_receipt.py "
                "--target confirmatory --cut'."
            )
        with open(_RECEIPT_PATH) as fh:
            return yaml.safe_load(fh)

    def test_receipt_sr0_pp(self, receipt: dict) -> None:
        """On-disk receipt sr0_pp must be 0.034921 (confirmatory, N_conf=6)."""
        assert receipt.get("sr0_pp") == pytest.approx(_EXPECTED_SR0_PP, abs=1e-9), (
            f"receipt sr0_pp={receipt.get('sr0_pp')!r}; expected {_EXPECTED_SR0_PP}. "
            "A look-runner MUST read sr0_pp from this receipt, not from r5_decision.SR0_PP."
        )

    def test_receipt_scipy_required(self, receipt: dict) -> None:
        """On-disk receipt scipy_required must be True."""
        assert receipt.get("scipy_required") is True, (
            f"receipt scipy_required={receipt.get('scipy_required')!r}; expected True"
        )

    def test_receipt_trial_id(self, receipt: dict) -> None:
        """On-disk receipt trial_id must be 'f2fb41fd'."""
        assert receipt.get("trial_id") == _EXPECTED_TRIAL_ID

    def test_receipt_master_seed(self, receipt: dict) -> None:
        """On-disk receipt master_seed must be 924033 (rule-exact)."""
        assert receipt.get("master_seed") == _EXPECTED_MASTER_SEED

    def test_receipt_kill_switch_threshold(self, receipt: dict) -> None:
        """On-disk receipt kill_switch_threshold must be 1.2906."""
        assert receipt.get("kill_switch_threshold") == pytest.approx(_EXPECTED_KST, abs=1e-4)

    def test_receipt_sr0_note_present(self, receipt: dict) -> None:
        """On-disk receipt sr0_note must be present and warn against reusing R5 literal."""
        note = receipt.get("sr0_note", "")
        assert isinstance(note, str) and "0.022906" in note, (
            f"receipt sr0_note={note!r}; must warn against reusing 0.022906 (R5-only)"
        )

    def test_receipt_prereg_sha256_present(self, receipt: dict) -> None:
        """On-disk receipt must have a non-empty prereg_sha256."""
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
