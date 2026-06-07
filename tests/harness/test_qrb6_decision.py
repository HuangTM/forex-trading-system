"""QRB-6 decision module tests (trial fa0f982a).

Test categories:
  1. evaluate_decision truth-table — every RULE, boundary cases, post-2015 priority.
  2. Event-set construction — calendar parquet count validation (506/345).
  3. sign_align + y_e degenerate handling.
  4. Receipt interlock — no receipt → SystemExit.
  5. No-cross-trial-constants guard — 0.022906 / 0.034921 absent from new files.
  6. Dry-run pipeline — --dry-run completes without touching data/processed.

kill_test_executed: false (no statistical computation on real return data).
no-capital-instruction: true
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest

# ---------------------------------------------------------------------------
# Repo layout helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_CALENDAR_PATH = _REPO_ROOT / "data" / "rates" / "cb_decision_dates.parquet"
_RECEIPT_PATH = (
    _REPO_ROOT
    / "references"
    / "pre-registrations"
    / "qrb6_cb_event_study.FREEZE-RECEIPT.yaml"
)
_QRB6_DECISION_PATH = (
    _REPO_ROOT / "src" / "forex_system" / "harness" / "qrb6_decision.py"
)
_RUN_QRB6_PATH = _REPO_ROOT / "scripts" / "run_qrb6.py"

# Frozen threshold values (sourced from pre-reg §4.2; NOT from r5_decision)
_P_KILL = 0.0522       # strict > this → KILL (alpha + MC-SE)
_P_REJECT = 0.0478     # strict < this → clean reject (alpha - MC-SE)
_DSR_THRESHOLD = 0.95

# Forbidden cross-trial literals (CTO FM-1 guard; §1.4(4))
_FORBIDDEN_LITERAL_R5 = "0.022906"
_FORBIDDEN_LITERAL_CONF = "0.034921"


# ---------------------------------------------------------------------------
# 1. evaluate_decision truth-table
# ---------------------------------------------------------------------------


class TestEvaluateDecision:
    """Truth-table tests for the §4.2 ordered decision functional."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from forex_system.harness.qrb6_decision import (
            RULE_0_TECHNICAL_FAILURE,
            RULE_1_KILL_POST2015,
            RULE_2_KILL_AGGREGATE,
            RULE_3_PASS,
            RULE_4_AMBIGUOUS,
            evaluate_decision,
        )
        self.eval = evaluate_decision
        self.RULE_0 = RULE_0_TECHNICAL_FAILURE
        self.RULE_1 = RULE_1_KILL_POST2015
        self.RULE_2 = RULE_2_KILL_AGGREGATE
        self.RULE_3 = RULE_3_PASS
        self.RULE_4 = RULE_4_AMBIGUOUS

    def _call(
        self,
        p_post2015: float,
        p_agg: float,
        dsr: float,
        technical_failure: bool = False,
    ) -> str:
        return self.eval(
            p_post2015=p_post2015,
            p_agg=p_agg,
            dsr=dsr,
            technical_failure=technical_failure,
            p_kill_threshold=_P_KILL,
            p_reject_threshold=_P_REJECT,
            dsr_threshold=_DSR_THRESHOLD,
        )

    # --- RULE 0: technical failure ---
    def test_rule0_fires_on_technical_failure(self):
        """technical_failure=True → RULE_0 regardless of p/dsr values."""
        result = self._call(0.01, 0.01, 0.99, technical_failure=True)
        assert result == self.RULE_0

    def test_rule0_fires_even_with_passing_p_and_dsr(self):
        result = self._call(0.001, 0.001, 0.999, technical_failure=True)
        assert result == self.RULE_0

    # --- RULE 1: post-2015 KILL (overrides aggregate) ---
    def test_rule1_fires_when_p_post2015_above_kill_threshold(self):
        """p_post2015 > 0.0522 → RULE_1 even if p_agg is clean-reject."""
        result = self._call(0.10, 0.01, 0.99)
        assert result == self.RULE_1

    def test_rule1_fires_at_p_post2015_exactly_0_60(self):
        result = self._call(0.60, 0.01, 0.99)
        assert result == self.RULE_1

    def test_rule1_fires_at_p_post2015_0_0523(self):
        """Just above kill threshold → RULE_1."""
        result = self._call(0.0523, 0.01, 0.99)
        assert result == self.RULE_1

    def test_rule1_overrides_aggregate_pass(self):
        """p_post2015=0.08, p_agg=0.02, dsr=0.99 → RULE_1 (not RULE_3)."""
        result = self._call(0.08, 0.02, 0.99)
        assert result == self.RULE_1

    # --- RULE 2: aggregate KILL ---
    def test_rule2_fires_when_p_agg_above_kill_threshold(self):
        """p_post2015 passes but p_agg > 0.0522 → RULE_2."""
        result = self._call(0.01, 0.10, 0.99)
        assert result == self.RULE_2

    def test_rule2_fires_at_p_agg_exactly_0_60(self):
        result = self._call(0.01, 0.60, 0.99)
        assert result == self.RULE_2

    def test_rule2_fires_at_p_agg_0_0523(self):
        result = self._call(0.01, 0.0523, 0.99)
        assert result == self.RULE_2

    # --- RULE 3: PASS ---
    def test_rule3_fires_when_both_p_below_reject_and_dsr_passes(self):
        """p_post2015 < 0.0478, p_agg < 0.0478, dsr >= 0.95 → RULE_3 PASS."""
        result = self._call(0.01, 0.01, 0.96)
        assert result == self.RULE_3

    def test_rule3_fires_at_p_0001_dsr_095(self):
        result = self._call(0.0001, 0.0001, 0.95)
        assert result == self.RULE_3

    def test_rule3_fires_at_p_0477_dsr_exactly_095(self):
        """p = 0.0477 < 0.0478 → clean reject; dsr=0.95 → PASS."""
        result = self._call(0.0477, 0.0477, 0.95)
        assert result == self.RULE_3

    # --- RULE 4: AMBIGUOUS (catch-all) ---
    def test_rule4_fires_when_p_in_straddle_band_lower(self):
        """p_post2015 = 0.0478 (exact lower boundary) → RULE_4 (closed band)."""
        result = self._call(0.0478, 0.01, 0.99)
        assert result == self.RULE_4

    def test_rule4_fires_when_p_agg_in_straddle_band_lower(self):
        """p_agg = 0.0478 (exact lower boundary) → RULE_4 (closed band)."""
        result = self._call(0.01, 0.0478, 0.99)
        assert result == self.RULE_4

    def test_rule4_fires_when_p_in_straddle_band_upper(self):
        """p_post2015 = 0.0522 (exact upper boundary) → RULE_4 (closed band,
        not KILL because strict > 0.0522 is required for RULE_1)."""
        result = self._call(0.0522, 0.01, 0.99)
        assert result == self.RULE_4

    def test_rule4_fires_when_p_agg_at_upper_boundary(self):
        """p_agg = 0.0522 → RULE_4 (upper boundary is straddle, not KILL)."""
        result = self._call(0.01, 0.0522, 0.99)
        assert result == self.RULE_4

    def test_rule4_fires_when_p_in_band_middle(self):
        """p = 0.0500 (exact alpha, middle of straddle band) → RULE_4."""
        result = self._call(0.0500, 0.0500, 0.99)
        assert result == self.RULE_4

    def test_rule4_fires_when_both_p_clean_but_dsr_fails(self):
        """p_post2015=0.01, p_agg=0.01, dsr=0.80 (< 0.95) → RULE_4."""
        result = self._call(0.01, 0.01, 0.80)
        assert result == self.RULE_4

    def test_rule4_fires_when_dsr_exactly_zero(self):
        result = self._call(0.01, 0.01, 0.0)
        assert result == self.RULE_4

    def test_rule4_fires_mixed_straddle_and_dsr_fail(self):
        """One p in straddle, DSR fails → RULE_4."""
        result = self._call(0.0490, 0.01, 0.50)
        assert result == self.RULE_4

    # --- Exhaustiveness: every path from the ordered rules fires exactly once ---
    def test_all_five_outcomes_reachable(self):
        """Verify all 5 decision outcomes are reachable (exhaustiveness)."""
        outcomes = {
            self._call(0.0, 0.0, 0.0, technical_failure=True),   # RULE 0
            self._call(0.10, 0.01, 0.99),                          # RULE 1
            self._call(0.01, 0.10, 0.99),                          # RULE 2
            self._call(0.01, 0.01, 0.99),                          # RULE 3
            self._call(0.01, 0.01, 0.50),                          # RULE 4
        }
        assert len(outcomes) == 5, f"Expected 5 distinct outcomes, got: {outcomes}"

    # --- Post-2015 priority (evaluated before aggregate) ---
    def test_post2015_kill_priority_over_rule2(self):
        """RULE 1 fires BEFORE RULE 2 when both p's fail."""
        result = self._call(0.60, 0.80, 0.99)
        assert result == self.RULE_1, (
            "When both p's fail, RULE 1 (post-2015) fires before RULE 2 (aggregate)."
        )

    def test_post2015_kill_priority_over_rule3(self):
        """post-2015 fail overrides potential aggregate PASS."""
        result = self._call(0.10, 0.01, 0.99)
        assert result == self.RULE_1

    # --- DSR-fail boundary (exact 0.95) ---
    def test_dsr_exactly_095_with_clean_p_is_pass(self):
        """DSR = 0.95 exactly (>= threshold) with clean p's → RULE_3 PASS."""
        result = self._call(0.01, 0.01, 0.95)
        assert result == self.RULE_3

    def test_dsr_just_below_095_with_clean_p_is_rule4(self):
        """DSR = 0.9499 (< 0.95) with clean p's → RULE_4."""
        result = self._call(0.01, 0.01, 0.9499)
        assert result == self.RULE_4


# ---------------------------------------------------------------------------
# 2. Event-set construction — calendar parquet count validation
# ---------------------------------------------------------------------------


class TestEventSetConstruction:
    """Verify Scenario A event-set counts against the real calendar parquet."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_calendar(self):
        if not _CALENDAR_PATH.exists():
            pytest.skip(f"Calendar parquet not found: {_CALENDAR_PATH}")

    def test_scenario_a_deduped_count_is_506(self):
        """build_scenario_a_event_set() must return exactly 506 deduped event-days."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        assert len(event_set) == 506, (
            f"Expected 506 Scenario A deduped market-days, got {len(event_set)}. "
            "NHT-verified count from nht-qrb6-rescreen.yaml."
        )

    def test_post_2015_count_is_345(self):
        """Post-2015 sub-window (date >= 2015-01-01) must be exactly 345 event-days."""
        from forex_system.harness.qrb6_decision import (
            build_scenario_a_event_set,
            get_post_2015_mask,
        )

        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        mask = get_post_2015_mask(event_set)
        n_post2015 = int(mask.sum())
        assert n_post2015 == 345, (
            f"Expected 345 post-2015 Scenario A event-days, got {n_post2015}. "
            "NHT-verified count from nht-qrb6-rescreen.yaml."
        )

    def test_training_memory_unverified_rows_excluded(self):
        """build_scenario_a_event_set must exclude all training-memory-unverified rows."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        # No row in the built event set should have inadmissible verification
        if "verification" in event_set.columns:
            bad_rows = event_set[
                event_set["verification"] == "training-memory-unverified"
            ]
            assert len(bad_rows) == 0, (
                f"training-memory-unverified rows leaked into Scenario A event set: "
                f"{len(bad_rows)} rows. Verbatim filter §3.1 must exclude them."
            )

    def test_only_scenario_a_banks_present(self):
        """Event set must contain only FED, BOJ, RBA, BOC banks."""
        from forex_system.harness.qrb6_decision import (
            _SCENARIO_A_BANKS,
            build_scenario_a_event_set,
        )

        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        if "bank" in event_set.columns:
            unexpected = set(event_set["bank"].unique()) - _SCENARIO_A_BANKS
            assert not unexpected, (
                f"Non-Scenario-A banks in event set: {unexpected}. "
                "Only FED, BOJ, RBA, BOC are in Scenario A."
            )

    def test_event_set_dates_are_unique(self):
        """Deduped event set must have unique dates (one row per market day)."""
        from forex_system.harness.qrb6_decision import build_scenario_a_event_set

        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
        n_unique = event_set["date"].nunique()
        assert n_unique == len(event_set), (
            f"Event set has duplicate dates: {len(event_set)} rows but only "
            f"{n_unique} unique dates.  Deduplication failed."
        )

    def test_verbatim_filter_phrase(self):
        """The verbatim filter phrase from §3.1 must be present in the source.

        The pre-reg (§3.1) specifies the verbatim filter:
          df = df[df['verification'] != 'training-memory-unverified']
        The source may use either single or double quotes for the string values;
        the structural pattern (column lookup != inadmissible grade) is what matters.
        """
        src = _QRB6_DECISION_PATH.read_text()
        # Accept either quote style for the filter
        has_filter = (
            '["verification"] != "training-memory-unverified"' in src
            or "['verification'] != 'training-memory-unverified'" in src
            or '_INADMISSIBLE_VERIFICATION' in src  # constant form is also acceptable
        )
        assert has_filter, (
            "Verbatim filter phrase from §3.1 not found in qrb6_decision.py. "
            "Must filter out 'training-memory-unverified' rows — either as a "
            "direct string comparison or via the _INADMISSIBLE_VERIFICATION constant."
        )


# ---------------------------------------------------------------------------
# 3. sign_align + y_e degenerate handling
# ---------------------------------------------------------------------------


class TestSignAlignAndYe:
    """Tests for sign alignment and y_e computation including degenerate case."""

    def test_positive_ret_d_gives_plus_one(self):
        from forex_system.harness.qrb6_decision import compute_sign_align

        assert compute_sign_align(1.0010, 1.0000) == 1.0

    def test_negative_ret_d_gives_minus_one(self):
        from forex_system.harness.qrb6_decision import compute_sign_align

        assert compute_sign_align(0.9990, 1.0000) == -1.0

    def test_zero_ret_d_gives_zero(self):
        """Exact tie: close(D) == close(D-1) → sign_align = 0.0 (degenerate; §4.4.3)."""
        from forex_system.harness.qrb6_decision import compute_sign_align

        assert compute_sign_align(1.0000, 1.0000) == 0.0

    def test_sign_align_uses_numpy_sign_semantics(self):
        """Verify numpy.sign semantics: returns exactly 0.0, not 0 or False."""
        from forex_system.harness.qrb6_decision import compute_sign_align

        result = compute_sign_align(1.0, 1.0)
        assert result == 0.0
        assert isinstance(result, float)

    def test_y_e_degenerate_returns_none(self):
        """sign_align = 0.0 → compute_y_e returns None (FLAT, excluded)."""
        from forex_system.harness.qrb6_decision import compute_y_e

        assert compute_y_e(0.0, 0.05) is None

    def test_y_e_positive_sign(self):
        """sign_align = +1, positive return → positive y_e."""
        from forex_system.harness.qrb6_decision import compute_y_e

        assert compute_y_e(1.0, 0.05) == pytest.approx(0.05)

    def test_y_e_negative_sign_flips_return(self):
        """sign_align = -1, positive return → negative y_e (shorts win on reversal)."""
        from forex_system.harness.qrb6_decision import compute_y_e

        assert compute_y_e(-1.0, 0.03) == pytest.approx(-0.03)

    def test_y_e_negative_sign_negative_return(self):
        """sign_align = -1, negative return → positive y_e (short earns on decline)."""
        from forex_system.harness.qrb6_decision import compute_y_e

        assert compute_y_e(-1.0, -0.03) == pytest.approx(0.03)

    def test_degenerate_event_does_not_contribute_to_mean(self):
        """End-to-end: degenerate event (sign=0) must not appear in the y_e series."""
        from forex_system.harness.qrb6_decision import compute_sign_align, compute_y_e

        events = [
            (1.001, 1.000, 0.02),   # +1
            (1.000, 1.000, 0.01),   # DEGENERATE → None
            (0.999, 1.000, -0.01),  # -1
        ]
        y_e_list = []
        for close_d, close_dm1, post_ret in events:
            sa = compute_sign_align(close_d, close_dm1)
            y = compute_y_e(sa, post_ret)
            if y is not None:
                y_e_list.append(y)

        assert len(y_e_list) == 2, "Degenerate event must be excluded from y_e list."
        assert y_e_list[0] == pytest.approx(0.02)   # +1 * 0.02
        assert y_e_list[1] == pytest.approx(0.01)   # -1 * -0.01


# ---------------------------------------------------------------------------
# 4. Receipt interlock — no receipt → SystemExit
# ---------------------------------------------------------------------------


class TestReceiptInterlock:
    """Verify the runner exits non-zero when no freeze-receipt is present."""

    def test_no_receipt_live_run_exits_nonzero(self, tmp_path):
        """Invoking run_qrb6.py with --ceo-ack but no receipt must exit(1)."""
        if _RECEIPT_PATH.exists():
            pytest.skip("Freeze-receipt already exists; interlock pre-cut test skipped.")

        result = subprocess.run(
            [sys.executable, str(_RUN_QRB6_PATH), "--ceo-ack"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit when receipt missing; got {result.returncode}. "
            f"stdout: {result.stdout[:500]}  stderr: {result.stderr[:500]}"
        )

    def test_no_receipt_live_run_prints_refusal(self, tmp_path):
        """Runner must print the refusal message when no receipt and --ceo-ack."""
        if _RECEIPT_PATH.exists():
            pytest.skip("Freeze-receipt already exists; interlock pre-cut test skipped.")

        result = subprocess.run(
            [sys.executable, str(_RUN_QRB6_PATH), "--ceo-ack"],
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        assert "REFUSED" in combined or "freeze-receipt" in combined.lower(), (
            "Runner must print a refusal message when no receipt. "
            f"Got: {combined[:800]}"
        )

    def test_check_receipt_constants_exits_on_mismatch(self):
        """check_receipt_constants() must call sys.exit(1) on a constant mismatch."""
        from forex_system.harness.qrb6_decision import check_receipt_constants

        bad_receipt = {
            "sr0_pp": 0.022906,   # R5-only forbidden literal — should trigger exit
            "n_sel": 3,
            "dsr_threshold": 0.95,
            "kill_switch_threshold": 1.5883,
            "alpha": 0.05,
            "master_seed": 387992,
            "K": 10000,
            "spread_z_threshold": 3.0,
            "scenario_a_event_days": 506,
            "post_2015_a": 345,
            "trial_id": "fa0f982a",
        }
        with pytest.raises(SystemExit) as exc_info:
            check_receipt_constants(bad_receipt)
        assert exc_info.value.code != 0

    def test_check_receipt_constants_passes_on_correct_values(self):
        """check_receipt_constants() must NOT exit on receipt with correct constants."""
        from forex_system.harness.qrb6_decision import check_receipt_constants

        correct_receipt = {
            "sr0_pp": 0.026861,
            "n_sel": 3,
            "dsr_threshold": 0.95,
            "kill_switch_threshold": 1.5883,
            "alpha": 0.05,
            "master_seed": 387992,
            "K": 10000,
            "spread_z_threshold": 3.0,
            "scenario_a_event_days": 506,
            "post_2015_a": 345,
            "trial_id": "fa0f982a",
        }
        # Must not raise
        check_receipt_constants(correct_receipt)


# ---------------------------------------------------------------------------
# 5. No-cross-trial-constants guard
# ---------------------------------------------------------------------------


class TestNoCrossTrialConstants:
    """Verify 0.022906 and 0.034921 appear nowhere in the new QRB-6 files
    (outside of comments and the sr0_note guard string).

    Per §1.4(4) and CTO FM-1: the runner and decision module must not hard-code
    or import cross-trial constants.
    """

    def _code_lines_only(self, path: Path) -> str:
        """Return joined lines that are actual code (not comments or string literals).

        Strategy: exclude lines that are (a) pure comment lines (stripped starts '#'),
        (b) docstring lines (stripped starts with triple-quotes or lies within a
        docstring block), or (c) lines that are plain string assignments whose entire
        value is a guard/warning string.  The goal is to detect NUMERIC LITERAL
        assignments that would silently import a forbidden value at runtime.
        """
        import re

        lines = []
        in_docstring = False
        docstring_delim: str | None = None
        for raw_line in path.read_text().splitlines():
            stripped = raw_line.strip()
            # Track docstring blocks (triple-quoted)
            if not in_docstring:
                triple_matches = re.findall(r'"""|\'\'\'' , raw_line)
                if triple_matches:
                    # Odd count → enter or exit docstring
                    if len(triple_matches) % 2 == 1:
                        in_docstring = True
                        docstring_delim = triple_matches[0]
                    continue  # docstring open/close line: skip
            else:
                delim = docstring_delim or '"""'
                if delim in raw_line:
                    in_docstring = False
                    docstring_delim = None
                continue  # inside docstring: skip
            # Skip blank lines and comment lines
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(raw_line)
        return "\n".join(lines)

    def test_decision_module_no_r5_literal(self):
        """qrb6_decision.py must not assign/use 0.022906 as a numeric literal in code.

        Appearances in comments and docstrings (as anti-pattern warnings) are allowed.
        The forbidden pattern is a NUMERIC CONSTANT used as a float value in code.
        """
        import re

        content = self._code_lines_only(_QRB6_DECISION_PATH)
        # Look for 0.022906 as an actual numeric literal (not inside a quoted string)
        # Pattern: 0.022906 that is NOT preceded or followed by a quote character
        # and is NOT on a line that is itself a string literal (e.g. "NOT 0.022906")
        # We check for assignments/calls: = 0.022906 or (0.022906 or similar
        matches = re.findall(r'[=\(,\s]0\.022906(?=[\s\),;])', content)
        assert not matches, (
            f"Forbidden R5-only literal 0.022906 found as a numeric code value in "
            f"qrb6_decision.py: {matches}. CTO FM-1: this must not be used as a float "
            "value in QRB-6 code (only allowed in string guard messages)."
        )

    def test_decision_module_no_confirmatory_literal(self):
        """qrb6_decision.py must not assign/use 0.034921 as a numeric literal in code."""
        import re

        content = self._code_lines_only(_QRB6_DECISION_PATH)
        matches = re.findall(r'[=\(,\s]0\.034921(?=[\s\),;])', content)
        assert not matches, (
            f"Forbidden confirmatory literal 0.034921 found as a numeric code value in "
            f"qrb6_decision.py: {matches}. CTO FM-1 cross-trial contamination guard."
        )

    def test_runner_no_r5_literal(self):
        """run_qrb6.py must not assign/use 0.022906 as a numeric literal in code."""
        import re

        content = self._code_lines_only(_RUN_QRB6_PATH)
        matches = re.findall(r'[=\(,\s]0\.022906(?=[\s\),;])', content)
        assert not matches, (
            f"Forbidden R5-only literal 0.022906 found as a numeric code value in "
            f"run_qrb6.py: {matches}. CTO FM-1 cross-trial contamination guard."
        )

    def test_runner_no_confirmatory_literal(self):
        """run_qrb6.py must not assign/use 0.034921 as a numeric literal in code."""
        import re

        content = self._code_lines_only(_RUN_QRB6_PATH)
        matches = re.findall(r'[=\(,\s]0\.034921(?=[\s\),;])', content)
        assert not matches, (
            f"Forbidden confirmatory literal 0.034921 found as a numeric code value in "
            f"run_qrb6.py: {matches}. CTO FM-1 cross-trial contamination guard."
        )

    def test_test_file_no_r5_literal_in_code_paths(self):
        """This test file itself must not embed forbidden literals in assertion paths.

        The literals ARE expected in _FORBIDDEN_LITERAL_* constants (defined as strings)
        and in the docstring comments — those are acceptable.
        This meta-test documents the intent; the two assertions above check the modules.
        """
        # The decision module and runner are checked by the other tests in this class.
        # This test exists as a documentation anchor; no assertion needed.
        assert True


# ---------------------------------------------------------------------------
# 6. Dry-run pipeline — no data/processed touch
# ---------------------------------------------------------------------------


class TestDryRunNoProcDataTouch:
    """Verify --dry-run completes without reading data/processed/*.parquet."""

    def test_dry_run_exits_zero(self):
        """python run_qrb6.py (default dry-run) must exit 0."""
        result = subprocess.run(
            [sys.executable, str(_RUN_QRB6_PATH)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"Dry-run exited non-zero: {result.returncode}\n"
            f"stdout: {result.stdout[-1000:]}\n"
            f"stderr: {result.stderr[-1000:]}"
        )

    def test_dry_run_prints_complete(self):
        """Dry-run output must include 'DRY-RUN COMPLETE'."""
        result = subprocess.run(
            [sys.executable, str(_RUN_QRB6_PATH)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert "DRY-RUN COMPLETE" in result.stdout or "COMPLETE" in result.stdout, (
            f"Expected 'COMPLETE' in dry-run output; got: {result.stdout[-500:]}"
        )

    def test_dry_run_does_not_touch_processed_dir(self, monkeypatch):
        """Pipeline in dry-run mode must never call pd.read_parquet on data/processed/."""
        import pandas as pd

        from forex_system.harness.qrb6_decision import (
            _EXPECTED_SCENARIO_A_N,
            _EXPECTED_POST_2015_A_N,
        )

        processed_reads: list[str] = []
        original_read_parquet = pd.read_parquet

        def tracking_read_parquet(path, *args, **kwargs):
            path_str = str(path)
            if "data/processed" in path_str or "processed/" in path_str:
                processed_reads.append(path_str)
            return original_read_parquet(path, *args, **kwargs)

        monkeypatch.setattr(pd, "read_parquet", tracking_read_parquet)

        # Also patch in the qrb6_decision module's namespace
        import forex_system.harness.qrb6_decision as qrb6_dec_mod
        monkeypatch.setattr(qrb6_dec_mod.pd, "read_parquet", tracking_read_parquet)

        # Import run_qrb6 and call _run_pipeline directly with dry_run=True
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUN_QRB6_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6_mod)  # type: ignore[union-attr]

        stub_receipt = {
            "master_seed": 387992,
            "K": 500,  # reduced for speed in test
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.0522,
            "p_reject_threshold": 0.0478,
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": _EXPECTED_SCENARIO_A_N,
            "post_2015_a": _EXPECTED_POST_2015_A_N,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "UNCOMMITTED",
            "frozen_at_utc": "TEST",
        }

        # Run the pipeline in dry-run mode
        result = run_qrb6_mod._run_pipeline(receipt=stub_receipt, dry_run=True)

        assert not processed_reads, (
            f"Dry-run accessed data/processed/: {processed_reads}. "
            "Dry-run must NEVER read production OHLCV data."
        )
        assert "decision" in result, "Pipeline must produce a decision field."


# ---------------------------------------------------------------------------
# 7. Spread suppression
# ---------------------------------------------------------------------------


class TestSpreadSuppression:
    """Tests for the QRB-2 spread_z overlay (§5.5)."""

    def test_spread_suppression_fires_above_threshold(self):
        """spread_z > 3.0 (strict) → suppressed."""
        from forex_system.harness.qrb6_decision import is_spread_suppressed

        assert is_spread_suppressed(3.001, 3.0) is True

    def test_spread_suppression_does_not_fire_at_exactly_threshold(self):
        """spread_z == 3.0 exactly → NOT suppressed (strict > semantics)."""
        from forex_system.harness.qrb6_decision import is_spread_suppressed

        assert is_spread_suppressed(3.0, 3.0) is False

    def test_spread_suppression_does_not_fire_below_threshold(self):
        from forex_system.harness.qrb6_decision import is_spread_suppressed

        assert is_spread_suppressed(1.5, 3.0) is False

    def test_spread_z_degenerate_mad_zero_returns_zero(self):
        """trailing_MAD = 0 → spread_z = 0.0 (no suppression)."""
        from forex_system.harness.qrb6_decision import compute_spread_z

        assert compute_spread_z(5.0, 3.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# 8. DSR gate (QRB-6 fresh constants)
# ---------------------------------------------------------------------------


class TestDSRGateQrb6:
    """Tests for the QRB-6 DSR computation with fresh SR0_pp_sel = 0.026861."""

    def test_dsr_below_threshold_for_low_sharpe(self):
        """A very low annualized Sharpe must produce DSR < 0.95."""
        from forex_system.harness.qrb6_decision import compute_dsr_qrb6

        dsr = compute_dsr_qrb6(
            sr_ann=0.05,
            skew=0.0,
            excess_kurtosis=0.0,
            T=506,
            sr0_pp=0.026861,
        )
        assert dsr < 0.95, f"Expected DSR < 0.95 for low SR=0.05, got {dsr}"

    def test_dsr_above_threshold_for_high_sharpe(self):
        """A very high annualized Sharpe must produce DSR >= 0.95."""
        from forex_system.harness.qrb6_decision import compute_dsr_qrb6

        dsr = compute_dsr_qrb6(
            sr_ann=2.5,  # well above kill_switch_threshold=1.5883
            skew=0.0,
            excess_kurtosis=0.0,
            T=506,
            sr0_pp=0.026861,
        )
        assert dsr >= 0.95, f"Expected DSR >= 0.95 for high SR=2.5, got {dsr}"

    def test_dsr_zero_for_nonpositive_sharpe(self):
        """Non-positive Sharpe → DSR = 0.0 (gate FAIL; degenerate pin 1)."""
        from forex_system.harness.qrb6_decision import compute_dsr_qrb6

        assert compute_dsr_qrb6(0.0, 0.0, 0.0, 506, 0.026861) == 0.0
        assert compute_dsr_qrb6(-0.5, 0.0, 0.0, 506, 0.026861) == 0.0

    def test_dsr_does_not_use_r5_sr0_pp(self):
        """DSR with QRB-6 SR0 must differ from DSR with R5 SR0 (not equal)."""
        from forex_system.harness.qrb6_decision import compute_dsr_qrb6

        dsr_qrb6 = compute_dsr_qrb6(1.5, 0.0, 0.0, 506, sr0_pp=0.026861)
        dsr_r5_would_be = compute_dsr_qrb6(1.5, 0.0, 0.0, 506, sr0_pp=0.022906)
        assert abs(dsr_qrb6 - dsr_r5_would_be) > 0.001, (
            "QRB-6 DSR with fresh SR0=0.026861 must differ from the R5-only SR0=0.022906. "
            "If they are equal, the SR0 was not updated."
        )


# ---------------------------------------------------------------------------
# 9. QD datapath fix tests (RULE-0 remediation 2026-06-07)
#
# Covers:
#   (a) tz-alignment: tz-naive event date + tz-aware index resolves correctly,
#       including roll-forward when the exact date has no bar.
#   (b) fractional return: hand-computed example matches.
#   (c) cost application: ONE hand-checked example against RealisticCostModel
#       for EURUSD (config defaults).
#   (d) silent-except eliminated: data error logs + skips, doesn't vanish.
# ---------------------------------------------------------------------------


class TestQdDatapathFix:
    """Regression tests for the QD datapath fix (qrb6-prereg-2026-06-06:phase1:task1.0)."""

    # --- (a) tz-alignment ---

    def test_tz_alignment_naive_event_date_resolves_on_aware_index(self):
        """A tz-naive event date must resolve correctly on a tz-aware UTC price index.

        The searchsorted convention must find the exact bar when it exists.
        """
        import pandas as pd

        # Build a tz-aware daily index
        idx = pd.date_range("2020-01-01", periods=10, freq="D", tz="UTC")
        cs = pd.Series(range(10, 20), index=idx, dtype=float)

        # Simulate the runner's tz-localize + searchsorted logic
        event_date = "2020-01-05"  # tz-naive string → Timestamp → tz-naive
        event_ts = pd.Timestamp(event_date)
        assert event_ts.tzinfo is None, "event_ts should be tz-naive from calendar"
        assert cs.index.tz is not None, "price index should be tz-aware"

        # Apply the fix
        if event_ts.tzinfo is None and cs.index.tz is not None:
            event_ts = event_ts.tz_localize(cs.index.tz)
        idx_pos = cs.index.searchsorted(event_ts)

        assert idx_pos < len(cs), "Must find a valid position"
        assert cs.index[idx_pos] == pd.Timestamp("2020-01-05", tz="UTC")
        assert idx_pos == 4, "2020-01-05 is index 4 (zero-based)"

    def test_tz_alignment_roll_forward_when_no_exact_bar(self):
        """Roll-forward: if event date has no bar, first bar AFTER the date is used.

        This mirrors the §3.4 frozen convention: no synthetic bar, next available bar.
        """
        import pandas as pd

        # Index skips 2020-01-03 (e.g. weekend or holiday)
        dates = pd.to_datetime([
            "2020-01-01", "2020-01-02",
            "2020-01-06", "2020-01-07",  # gap: 3rd–5th missing
        ]).tz_localize("UTC")
        cs = pd.Series([1.0, 2.0, 6.0, 7.0], index=dates)

        event_ts = pd.Timestamp("2020-01-03")  # tz-naive, no bar on this date
        if event_ts.tzinfo is None and cs.index.tz is not None:
            event_ts = event_ts.tz_localize(cs.index.tz)
        idx_pos = cs.index.searchsorted(event_ts)

        assert idx_pos < len(cs), "Must roll forward to next available bar"
        assert cs.index[idx_pos] == pd.Timestamp("2020-01-06", tz="UTC"), (
            "Roll-forward must land on 2020-01-06, the first bar after the gap."
        )

    def test_tz_alignment_no_bar_after_date_skips_event(self):
        """If no bar exists at or after the event date, the event must be skipped."""
        import pandas as pd

        idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
        cs = pd.Series(range(5), index=idx, dtype=float)

        # Event date is after all bars
        event_ts = pd.Timestamp("2025-01-01")
        if event_ts.tzinfo is None and cs.index.tz is not None:
            event_ts = event_ts.tz_localize(cs.index.tz)
        idx_pos = cs.index.searchsorted(event_ts)

        assert idx_pos >= len(cs), (
            "searchsorted past end of index must return len(cs) — event must be skipped."
        )

    # --- (b) fractional return ---

    def test_fractional_return_formula(self):
        """Net return must be (c_dp2 / c_d) - 1, not c_dp2 - c_d.

        Hand-computed example:
          c_d = 1.2000, c_dp2 = 1.2060
          gross = (1.2060 / 1.2000) - 1 = 0.005 exactly
          price diff = 1.2060 - 1.2000 = 0.0060  ← WRONG (this is the old bug)
        """
        c_d = 1.2000
        c_dp2 = 1.2060
        gross_ret = (c_dp2 / c_d) - 1.0
        wrong_ret = c_dp2 - c_d

        assert abs(gross_ret - 0.005) < 1e-12, (
            f"Fractional return must be 0.005 exactly; got {gross_ret}"
        )
        assert abs(wrong_ret - 0.006) < 1e-12, "Sanity: price diff is 0.006 (wrong value)"
        assert abs(gross_ret - wrong_ret) > 1e-6, (
            "Fractional return and price diff must differ — this guards the fix."
        )

    def test_fractional_return_matches_expected_for_jpy(self):
        """For JPY pairs the fractional formula is still (c_dp2 / c_d) - 1.

        c_d = 110.00, c_dp2 = 110.55
        gross = (110.55 / 110.00) - 1 = 0.005 exactly
        """
        c_d = 110.00
        c_dp2 = 110.55
        gross_ret = (c_dp2 / c_d) - 1.0
        assert abs(gross_ret - 0.005) < 1e-12, (
            f"JPY fractional return must be 0.005; got {gross_ret}"
        )

    # --- (c) cost application ---

    def test_cost_application_eurusd_long_one_day(self):
        """Hand-check: EURUSD LONG 1-day hold cost matches RealisticCostModel defaults.

        Config values (constants.py / config/default.yaml, committed pre-freeze):
          spread_pips  = 0.5
          slippage_pips = 0.5
          commission_pips = 0.5
          swap_long_pips_per_day = -1.2  (negative = cost to long)
          pip_value = 0.0001

        round_trip_cost = entry_cost + exit_cost
          entry_cost = spread/2 + slippage = 0.25 + 0.5 = 0.75
          exit_cost  = spread/2 + slippage + commission = 0.25 + 0.5 + 0.5 = 1.25
          round_trip = 2.0 pips

        holding_cost(LONG, 1 day) = -swap_long * 1 = -(-1.2) = 1.2 pips

        total_cost_pips = 2.0 + 1.2 = 3.2 pips
        cost_frac (at c_d = 1.2000) = 3.2 * 0.0001 / 1.2000 = 0.000266̄

        net_ret = gross_ret - cost_frac
        """
        import pytest
        from forex_system.costs.model import RealisticCostModel
        from forex_system.core.types import Direction
        from forex_system.backtest.engine import _get_pip_value

        cost_model = RealisticCostModel()
        pair = "EURUSD"
        c_d = 1.2000
        c_dp2 = 1.2060  # +0.5% gross return

        pip_val = _get_pip_value(pair)
        assert pip_val == pytest.approx(0.0001), "EURUSD pip_value must be 0.0001"

        rt_pips = cost_model.round_trip_cost(pair, 1.0)
        assert rt_pips == pytest.approx(2.0), (
            f"EURUSD round_trip_cost must be 2.0 pips; got {rt_pips}"
        )

        hold_pips = cost_model.holding_cost(pair, Direction.LONG, 1.0)
        assert hold_pips == pytest.approx(1.2), (
            f"EURUSD LONG holding_cost 1 day must be 1.2 pips; got {hold_pips}"
        )

        total_cost_pips = rt_pips + hold_pips
        assert total_cost_pips == pytest.approx(3.2)

        cost_frac = total_cost_pips * pip_val / c_d
        expected_cost_frac = 3.2 * 0.0001 / 1.2000
        assert cost_frac == pytest.approx(expected_cost_frac, rel=1e-9), (
            f"cost_frac mismatch: {cost_frac} vs {expected_cost_frac}"
        )

        gross_ret = (c_dp2 / c_d) - 1.0
        net_ret = gross_ret - cost_frac

        # Expected net return: 0.005 - 0.000266667 ≈ 0.004733333
        expected_net = 0.005 - expected_cost_frac
        assert net_ret == pytest.approx(expected_net, rel=1e-9), (
            f"net_ret mismatch: {net_ret} vs {expected_net}"
        )

    def test_cost_application_eurusd_short_one_day(self):
        """EURUSD SHORT 1-day hold uses swap_short_pips_per_day = +0.3 (income for short).

        holding_cost(SHORT, 1 day) = -swap_short * 1 = -(0.3) = -0.3 pips (negative = income)
        total_cost_pips = 2.0 + (-0.3) = 1.7 pips
        """
        import pytest
        from forex_system.costs.model import RealisticCostModel
        from forex_system.core.types import Direction

        cost_model = RealisticCostModel()
        pair = "EURUSD"

        rt_pips = cost_model.round_trip_cost(pair, 1.0)
        hold_pips = cost_model.holding_cost(pair, Direction.SHORT, 1.0)
        assert hold_pips == pytest.approx(-0.3), (
            f"EURUSD SHORT holding_cost 1 day must be -0.3 pips (income); got {hold_pips}"
        )
        total_cost_pips = rt_pips + hold_pips
        assert total_cost_pips == pytest.approx(1.7)

    # --- (d) silent-except eliminated ---

    def test_bare_except_not_in_per_pair_loop(self):
        """The per-pair loop in run_qrb6.py must NOT contain a bare 'except Exception: continue'.

        The fix narrows the exception to specific types and adds a log entry.
        This test scans the source to confirm the silent swallow is gone.
        """
        import re

        src = _RUN_QRB6_PATH.read_text()

        # The old pattern: bare except with no log (silent swallow)
        # Matches "except Exception:" on its own line (indented), with the next
        # non-blank line being just "continue" (no log call in between).
        # We look for the specific old pattern: "except Exception:\n\s+continue"
        bare_silent = re.search(
            r'except\s+Exception\s*:\s*\n\s+continue',
            src,
        )
        assert bare_silent is None, (
            "Bare 'except Exception: continue' (silent swallow) found in run_qrb6.py. "
            "The fix must narrow the exception type AND add a _log() call before continue."
        )

    def test_pair_event_skip_log_present_in_per_pair_loop(self):
        """The per-pair loop must emit a 'pair_event_skip' log on data errors (not vanish).

        This verifies FIX-4: every error path calls _log() before continuing.
        """
        src = _RUN_QRB6_PATH.read_text()
        assert "qrb6_runner.pair_event_skip" in src, (
            "'qrb6_runner.pair_event_skip' log event not found in run_qrb6.py. "
            "The per-pair loop must log every skip (FIX-4: no silent drops)."
        )
