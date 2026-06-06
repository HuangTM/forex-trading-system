"""Tests for harness/r5_decision.py — DSR gate and decision functional.

Covers (per Item 3 / dispatch spec):
  1. DSR gate — synthetic values; both degenerate pins; one hand-computed
     reference value with SR0_PP=0.022906 pinned to ~1e-6.
  2. Decision functional — all 5 rules; boundary case p_spa=0.048,dsr=0.96,
     p_rc=0.01 -> AMBIGUOUS_STRADDLE; rule-order precedence; parametrized
     exhaustiveness sweep.
  3. Runner refusal path — missing --i-am-step4 flag; wrong receipt SHA-256;
     no real run executed.

All tests use synthetic inputs only.  The real joint matrix is NEVER computed
here (kill_test_executed=false invariant).
"""

from __future__ import annotations

import hashlib
import math
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
import yaml

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------

import numpy as np

from forex_system.harness.r5_decision import (
    AMBIGUOUS_GATE_FAIL,
    AMBIGUOUS_STRADDLE,
    CONTINUE,
    DSR_THRESHOLD,
    SR0_PP,
    TECHNICAL_FAILURE,
    WIND_DOWN,
    compute_dsr_gate,
    evaluate_decision,
    select_k_star_studentized,
)


# ---------------------------------------------------------------------------
# Constants (mirroring frozen pre-reg values for clarity)
# ---------------------------------------------------------------------------

_SR0_PP_FROZEN = 0.022906  # must equal r5_decision.SR0_PP; pre-reg §7.3.3 N=3
_DSR_THRESHOLD = 0.95      # pre-reg §7.3.5
_ALPHA = 0.05
_MC_SE = 0.0031


# ---------------------------------------------------------------------------
# Helper: hand-compute DSR for reference value tests
# ---------------------------------------------------------------------------

def _ref_dsr(sr_ann: float, skew: float, ek: float, T: int) -> float:
    """Reproduce §7.3.4 formula in plain Python for test reference."""
    import scipy.stats as sp
    if sr_ann <= 0.0:
        return 0.0
    sr_pp = sr_ann / math.sqrt(252.0)
    var_term = 1.0 - skew * sr_pp + ((ek + 2.0) / 4.0) * sr_pp ** 2
    if var_term <= 0.0:
        return 0.0
    z = (sr_pp - _SR0_PP_FROZEN) * math.sqrt(T - 1) / math.sqrt(var_term)
    return max(0.0, min(1.0, float(sp.norm.cdf(z))))


# ---------------------------------------------------------------------------
# 1. DSR gate tests
# ---------------------------------------------------------------------------

class TestComputeDsrGate:
    """Tests for compute_dsr_gate (§7.3.4)."""

    def test_frozen_sr0_pp_matches_preregistration(self) -> None:
        """SR0_PP literal must equal 0.022906 (= 0.363623/sqrt(252); elected N=3; §7.3.3)."""
        assert SR0_PP == pytest.approx(0.022906, abs=1e-9), (
            f"SR0_PP = {SR0_PP!r} does not match frozen value 0.022906. "
            "Do NOT change this literal — it is pinned by the pre-registration."
        )
        # Cross-check: verify it equals 0.363623/sqrt(252)
        expected_from_formula = 0.363623 / math.sqrt(252.0)
        assert SR0_PP == pytest.approx(expected_from_formula, abs=1e-6)

    def test_dsr_threshold_matches_preregistration(self) -> None:
        """DSR_THRESHOLD must equal 0.95 (§7.3.5)."""
        assert DSR_THRESHOLD == pytest.approx(0.95)

    # --- Degenerate pin 1: sr_ann <= 0 -> DSR = 0.0 ---

    def test_degenerate_zero_sharpe_returns_zero(self) -> None:
        """Degenerate pin 1: sr_ann = 0.0 -> DSR = 0.0 (§7.3.4 / dsr.py:168-169)."""
        dsr = compute_dsr_gate(sr_ann_best_cell=0.0, skew=0.0, excess_kurtosis=0.0, T=1000)
        assert dsr == pytest.approx(0.0)

    def test_degenerate_negative_sharpe_returns_zero(self) -> None:
        """Degenerate pin 1: sr_ann < 0 -> DSR = 0.0 (gate FAIL, not technical failure)."""
        dsr = compute_dsr_gate(sr_ann_best_cell=-0.5, skew=0.0, excess_kurtosis=0.0, T=1000)
        assert dsr == pytest.approx(0.0)

    def test_degenerate_very_negative_sharpe_returns_zero(self) -> None:
        """Degenerate pin 1: sr_ann = -5.0 -> DSR = 0.0."""
        dsr = compute_dsr_gate(sr_ann_best_cell=-5.0, skew=0.5, excess_kurtosis=1.0, T=500)
        assert dsr == pytest.approx(0.0)

    # --- Degenerate pin 2: var_term <= 0 -> DSR = 0.0 ---

    def test_degenerate_negative_var_term_returns_zero(self) -> None:
        """Degenerate pin 2: huge positive skew drives var_term negative -> DSR = 0.0.

        With sr_ann=0.5, skew=100 (extreme): sr_pp≈0.0315; skew*sr_pp≈3.15 >> 1,
        so var_term = 1 - 3.15 + ... << 0.
        """
        dsr = compute_dsr_gate(
            sr_ann_best_cell=0.5,
            skew=100.0,  # pathologically large: makes var_term negative
            excess_kurtosis=0.0,
            T=1000,
        )
        assert dsr == pytest.approx(0.0), (
            "Degenerate pin 2 failed: var_term<=0 must return DSR=0.0 (gate FAIL)."
        )

    def test_degenerate_var_term_at_zero_boundary_returns_zero(self) -> None:
        """Degenerate pin 2: var_term driven to non-positive by extreme skew -> DSR = 0.0.

        Rather than constructing exactly var_term=0 (which has floating-point
        precision issues), we use a large enough skew to make var_term clearly
        negative.  The guard is var_term <= 0.0; any negative value triggers it.
        """
        # Use a skew value that makes var_term clearly negative (well beyond the boundary)
        # var_term = 1 - skew*sr_pp + kc*sr_pp^2; with skew = 1.1 * (1/sr_pp) the term
        # 1 - skew*sr_pp = 1 - 1.1 = -0.1, safely negative regardless of the quadratic term.
        sr_ann = 1.0
        T = 1000
        ek = 0.0
        sr_pp = sr_ann / math.sqrt(252.0)
        # skew set so that skew*sr_pp = 1.1 -> var_term ≈ 1 - 1.1 + small = negative
        skew_neg_var = 1.1 / sr_pp
        var_term_check = 1.0 - skew_neg_var * sr_pp + ((ek + 2.0) / 4.0) * sr_pp ** 2
        assert var_term_check < 0.0, (
            f"Test setup error: var_term={var_term_check!r} must be negative"
        )
        dsr = compute_dsr_gate(sr_ann_best_cell=sr_ann, skew=skew_neg_var, excess_kurtosis=ek, T=T)
        assert dsr == pytest.approx(0.0)

    # --- Hand-computed reference value ---

    def test_reference_value_sr1_t1000_skew0_ek0(self) -> None:
        """Pinned reference: SR_ann=1.0, T=1000, skew=0, ek=0.

        Hand computation (§7.3.4):
          sr_pp = 1.0/sqrt(252) ≈ 0.063008
          var_term = 1 - 0*sr_pp + ((0+2)/4)*sr_pp^2 = 1 + 0.5*0.003970 ≈ 1.001985
          z = (0.063008 - 0.022906) * sqrt(999) / sqrt(1.001985)
            = 0.040102 * 31.6069 / 1.000992 ≈ 1.26581
          DSR = Φ(1.26581) ≈ 0.8972
        Tolerance: 1e-6 (scipy.stats.norm.cdf grade exact).
        """
        sr_ann = 1.0
        T = 1000
        skew = 0.0
        ek = 0.0

        dsr = compute_dsr_gate(sr_ann_best_cell=sr_ann, skew=skew, excess_kurtosis=ek, T=T)
        ref = _ref_dsr(sr_ann, skew, ek, T)

        assert dsr == pytest.approx(ref, abs=1e-6), (
            f"DSR={dsr!r} differs from reference {ref!r} by more than 1e-6. "
            "The frozen formula may have been modified."
        )
        # Confirm the reference itself is in the expected ballpark (~0.897)
        assert 0.89 < ref < 0.91, (
            f"Reference DSR={ref!r} is outside expected range [0.89, 0.91] — "
            "check hand computation."
        )

    def test_reference_value_matches_scipy_directly(self) -> None:
        """The computed DSR equals the direct scipy.stats.norm.cdf value."""
        sr_ann = 1.5
        T = 500
        skew = 0.3
        ek = 1.0

        dsr = compute_dsr_gate(sr_ann_best_cell=sr_ann, skew=skew, excess_kurtosis=ek, T=T)
        ref = _ref_dsr(sr_ann, skew, ek, T)
        assert dsr == pytest.approx(ref, abs=1e-10)

    def test_dsr_in_unit_interval(self) -> None:
        """DSR must always be clipped to [0, 1]."""
        for sr_ann in (0.1, 0.5, 1.0, 2.0, 5.0):
            for skew in (-1.0, 0.0, 1.0):
                for ek in (-1.0, 0.0, 2.0):
                    dsr = compute_dsr_gate(
                        sr_ann_best_cell=sr_ann,
                        skew=skew,
                        excess_kurtosis=ek,
                        T=1000,
                    )
                    assert 0.0 <= dsr <= 1.0, (
                        f"DSR={dsr!r} out of [0,1] for sr_ann={sr_ann}, "
                        f"skew={skew}, ek={ek}"
                    )

    def test_higher_sr_gives_higher_dsr(self) -> None:
        """Monotonicity: higher SR_ann -> higher DSR (all else equal, normal regime)."""
        T = 1000
        dsrs = [
            compute_dsr_gate(sr_ann_best_cell=sr, skew=0.0, excess_kurtosis=0.0, T=T)
            for sr in [0.1, 0.5, 1.0, 2.0]
        ]
        for i in range(len(dsrs) - 1):
            assert dsrs[i] < dsrs[i + 1], (
                f"DSR not monotone: dsrs[{i}]={dsrs[i]!r} >= dsrs[{i+1}]={dsrs[i+1]!r}"
            )

    def test_larger_T_gives_higher_dsr_for_positive_sr(self) -> None:
        """Larger T -> tighter z-score -> higher DSR for SR > SR0_PP (normal regime)."""
        sr_ann = 0.8  # above SR0_ann=0.363623
        dsrs = [
            compute_dsr_gate(sr_ann_best_cell=sr_ann, skew=0.0, excess_kurtosis=0.0, T=T)
            for T in [100, 500, 1000, 4186]
        ]
        for i in range(len(dsrs) - 1):
            assert dsrs[i] < dsrs[i + 1], (
                f"DSR not increasing in T: dsrs[{i}]={dsrs[i]!r} >= dsrs[{i+1}]={dsrs[i+1]!r}"
            )


# ---------------------------------------------------------------------------
# 2. Decision functional tests
# ---------------------------------------------------------------------------

class TestEvaluateDecision:
    """Tests for evaluate_decision (§7.3.6 ordered rules)."""

    # --- RULE 0: TECHNICAL_FAILURE ---

    def test_rule0_technical_failure_fires_first(self) -> None:
        """RULE 0: technical_failure=True -> TECHNICAL_FAILURE regardless of p/dsr."""
        result = evaluate_decision(p_spa=0.01, p_rc=0.01, dsr=0.99, technical_failure=True)
        assert result == TECHNICAL_FAILURE

    def test_rule0_fires_even_with_continue_conditions(self) -> None:
        """RULE 0 beats RULE 3: technical_failure overrides even a CONTINUE setup."""
        result = evaluate_decision(p_spa=0.01, p_rc=0.01, dsr=0.99, technical_failure=True)
        assert result == TECHNICAL_FAILURE

    def test_rule0_fires_even_with_windown_conditions(self) -> None:
        """RULE 0 beats RULE 2: technical_failure overrides even a clear WIND_DOWN."""
        result = evaluate_decision(p_spa=0.8, p_rc=0.8, dsr=0.0, technical_failure=True)
        assert result == TECHNICAL_FAILURE

    # --- RULE 1: AMBIGUOUS_STRADDLE ---

    def test_rule1_straddle_p_exactly_alpha(self) -> None:
        """RULE 1: p_spa = 0.05 exactly -> AMBIGUOUS_STRADDLE (|0.05-0.05|=0 <= 0.0031)."""
        result = evaluate_decision(p_spa=0.05, p_rc=0.01, dsr=0.99, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE

    def test_rule1_straddle_p_spa_0_048(self) -> None:
        """RULE 1 boundary case: p_spa=0.048, dsr=0.96, p_rc=0.01 -> AMBIGUOUS_STRADDLE.

        §7.3.6 explicit boundary-case ruling: |0.048-0.05|=0.002 <= 0.0031.
        RULE 1 fires before RULE 3 (CONTINUE), so AMBIGUOUS_STRADDLE wins.
        """
        result = evaluate_decision(p_spa=0.048, p_rc=0.01, dsr=0.96, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE, (
            f"Expected AMBIGUOUS_STRADDLE for p_spa=0.048 (straddle); got {result!r}. "
            "§7.3.6 boundary ruling: RULE 1 fires before RULE 3."
        )

    def test_rule1_upper_edge_of_straddle_band(self) -> None:
        """RULE 1: p_spa = 0.05 + 0.0031 = 0.0531 is exactly at the upper straddle edge.

        |0.0531 - 0.05| = 0.0031 <= 0.0031 -> AMBIGUOUS_STRADDLE.
        """
        result = evaluate_decision(p_spa=0.0531, p_rc=0.01, dsr=0.99, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE

    def test_rule1_lower_edge_of_straddle_band(self) -> None:
        """RULE 1: p_spa just above the lower straddle edge is AMBIGUOUS_STRADDLE.

        The theoretical lower edge is 0.05 - 0.0031 = 0.0469.  Due to floating-point
        precision, abs(0.0469 - 0.05) evaluates as 0.0031000...0055 (> 0.0031), so the
        literal 0.0469 sits just outside the straddle band in IEEE 754 arithmetic.
        We test with 0.047 (safely inside the band: |0.047-0.05|=0.003 < 0.0031).
        """
        # 0.047: |0.047 - 0.05| = 0.003 <= 0.0031 -> AMBIGUOUS_STRADDLE
        result = evaluate_decision(p_spa=0.047, p_rc=0.01, dsr=0.99, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE

    def test_rule1_just_inside_lower_straddle(self) -> None:
        """RULE 1: p_spa just inside lower straddle band -> AMBIGUOUS_STRADDLE."""
        result = evaluate_decision(p_spa=0.0469 + 1e-6, p_rc=0.01, dsr=0.99, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE

    # --- RULE 2: WIND_DOWN ---

    def test_rule2_wind_down_clear_rejection_failure(self) -> None:
        """RULE 2: p_spa = 0.20 (>> 0.0531, outside straddle) -> WIND_DOWN."""
        result = evaluate_decision(p_spa=0.20, p_rc=0.20, dsr=0.0, technical_failure=False)
        assert result == WIND_DOWN

    def test_rule2_wind_down_just_above_straddle(self) -> None:
        """RULE 2: p_spa just above the straddle upper band -> WIND_DOWN."""
        result = evaluate_decision(
            p_spa=0.0531 + 1e-6, p_rc=0.5, dsr=0.0, technical_failure=False
        )
        assert result == WIND_DOWN

    def test_rule2_wind_down_p_spa_1_0(self) -> None:
        """RULE 2: p_spa = 1.0 -> WIND_DOWN (maximum p-value)."""
        result = evaluate_decision(p_spa=1.0, p_rc=1.0, dsr=0.0, technical_failure=False)
        assert result == WIND_DOWN

    # --- RULE 3: CONTINUE ---

    def test_rule3_continue_all_gates_clear(self) -> None:
        """RULE 3: p_spa < 0.0469, dsr >= 0.95, p_rc < 0.05 -> CONTINUE."""
        result = evaluate_decision(
            p_spa=0.01, p_rc=0.01, dsr=0.97, technical_failure=False
        )
        assert result == CONTINUE

    def test_rule3_continue_boundary_dsr_exactly_threshold(self) -> None:
        """RULE 3: dsr = 0.95 exactly (threshold) -> CONTINUE (>= is inclusive)."""
        result = evaluate_decision(
            p_spa=0.02, p_rc=0.02, dsr=0.95, technical_failure=False
        )
        assert result == CONTINUE

    def test_rule3_continue_p_rc_just_below_alpha(self) -> None:
        """RULE 3: p_rc just below 0.05 -> CONTINUE."""
        result = evaluate_decision(
            p_spa=0.01, p_rc=_ALPHA - 1e-9, dsr=0.96, technical_failure=False
        )
        assert result == CONTINUE

    # --- RULE 4: AMBIGUOUS_GATE_FAIL ---

    def test_rule4_spa_rejects_but_dsr_fails(self) -> None:
        """RULE 4: p_spa < 0.0469 but DSR < 0.95 -> AMBIGUOUS_GATE_FAIL."""
        result = evaluate_decision(
            p_spa=0.01, p_rc=0.01, dsr=0.90, technical_failure=False
        )
        assert result == AMBIGUOUS_GATE_FAIL

    def test_rule4_spa_rejects_but_rc_fails(self) -> None:
        """RULE 4: p_spa < 0.0469 and DSR >= 0.95 but p_rc >= 0.05 -> AMBIGUOUS_GATE_FAIL."""
        result = evaluate_decision(
            p_spa=0.01, p_rc=0.06, dsr=0.97, technical_failure=False
        )
        assert result == AMBIGUOUS_GATE_FAIL

    def test_rule4_spa_rejects_dsr_and_rc_both_fail(self) -> None:
        """RULE 4: p_spa < 0.0469 but both DSR and RC gates fail -> AMBIGUOUS_GATE_FAIL."""
        result = evaluate_decision(
            p_spa=0.02, p_rc=0.10, dsr=0.50, technical_failure=False
        )
        assert result == AMBIGUOUS_GATE_FAIL

    def test_rule4_dsr_exactly_below_threshold(self) -> None:
        """RULE 4: dsr = 0.95 - 1e-9 (just below threshold) -> AMBIGUOUS_GATE_FAIL."""
        result = evaluate_decision(
            p_spa=0.02, p_rc=0.01, dsr=_DSR_THRESHOLD - 1e-9, technical_failure=False
        )
        assert result == AMBIGUOUS_GATE_FAIL

    def test_rule4_p_rc_exactly_alpha(self) -> None:
        """RULE 4: p_rc = 0.05 exactly (not strictly less) -> AMBIGUOUS_GATE_FAIL."""
        result = evaluate_decision(
            p_spa=0.02, p_rc=0.05, dsr=0.97, technical_failure=False
        )
        assert result == AMBIGUOUS_GATE_FAIL

    # --- Rule-order precedence ---

    def test_rule_order_rule0_beats_rule1(self) -> None:
        """RULE 0 (technical_failure) fires before RULE 1 (straddle)."""
        # p_spa in straddle band, but technical_failure=True -> RULE 0 wins
        result = evaluate_decision(p_spa=0.05, p_rc=0.01, dsr=0.99, technical_failure=True)
        assert result == TECHNICAL_FAILURE

    def test_rule_order_rule1_beats_rule2(self) -> None:
        """RULE 1 (straddle) fires before RULE 2 (wind-down).

        p_spa = 0.053 is in straddle band (|0.053-0.05|=0.003 <= 0.0031)
        and also >= 0.05.  RULE 1 must fire before RULE 2.
        """
        result = evaluate_decision(p_spa=0.053, p_rc=0.9, dsr=0.0, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE, (
            f"Expected AMBIGUOUS_STRADDLE (RULE 1 before RULE 2) for p_spa=0.053; got {result!r}"
        )

    def test_rule_order_rule1_beats_rule3(self) -> None:
        """RULE 1 (straddle) fires before RULE 3 (CONTINUE): the §7.3.6 boundary case."""
        # p_spa=0.048 is in straddle; dsr=0.96; p_rc=0.01 — would satisfy RULE 3 if straddle not checked
        result = evaluate_decision(p_spa=0.048, p_rc=0.01, dsr=0.96, technical_failure=False)
        assert result == AMBIGUOUS_STRADDLE, (
            f"Expected AMBIGUOUS_STRADDLE (RULE 1 fires before RULE 3); got {result!r}"
        )

    def test_rule_order_rule2_before_rule3(self) -> None:
        """RULE 2 (wind-down) fires before RULE 3 (CONTINUE) via strict ordering.

        p_spa=0.06 is outside straddle (0.06-0.05=0.01 > 0.0031) and >= 0.05.
        RULE 2 -> WIND_DOWN.  RULE 3 is never evaluated.
        """
        # Even with dsr=0.99 and p_rc=0.01, p_spa=0.06 goes WIND_DOWN via RULE 2
        result = evaluate_decision(p_spa=0.06, p_rc=0.01, dsr=0.99, technical_failure=False)
        assert result == WIND_DOWN

    # --- Exhaustiveness sweep ---

    @pytest.mark.parametrize("p_spa,p_rc,dsr,technical_failure,expected", [
        # RULE 0: technical_failure=True always wins
        (0.01, 0.01, 0.99, True, TECHNICAL_FAILURE),
        (0.05, 0.01, 0.99, True, TECHNICAL_FAILURE),
        (0.90, 0.90, 0.0, True, TECHNICAL_FAILURE),
        # RULE 1: straddle band [0.0469, 0.0531] (approx; 0.0469 has float precision issue)
        (0.047, 0.01, 0.99, False, AMBIGUOUS_STRADDLE),    # safely inside lower band
        (0.05, 0.01, 0.99, False, AMBIGUOUS_STRADDLE),     # exact alpha
        (0.0531, 0.01, 0.99, False, AMBIGUOUS_STRADDLE),   # upper edge
        (0.048, 0.01, 0.96, False, AMBIGUOUS_STRADDLE),    # §7.3.6 explicit case
        (0.052, 0.01, 0.99, False, AMBIGUOUS_STRADDLE),    # just inside upper
        # RULE 2: p_spa > 0.0531 (outside straddle, >= alpha)
        (0.0532, 0.01, 0.99, False, WIND_DOWN),
        (0.10, 0.10, 0.0, False, WIND_DOWN),
        (1.00, 1.00, 0.0, False, WIND_DOWN),
        # RULE 3: p_spa < 0.0469, dsr >= 0.95, p_rc < 0.05
        (0.01, 0.01, 0.95, False, CONTINUE),               # dsr exactly at threshold
        (0.01, 0.01, 0.99, False, CONTINUE),
        (0.04, 0.04, 0.96, False, CONTINUE),
        (0.04, 0.049, 0.96, False, CONTINUE),              # p_rc just below 0.05
        # RULE 4: p_spa < 0.0469 but DSR or RC fails
        (0.01, 0.01, 0.94, False, AMBIGUOUS_GATE_FAIL),   # dsr just below threshold
        (0.01, 0.05, 0.99, False, AMBIGUOUS_GATE_FAIL),   # p_rc exactly 0.05 (not <)
        (0.01, 0.06, 0.99, False, AMBIGUOUS_GATE_FAIL),   # p_rc above alpha
        (0.02, 0.10, 0.50, False, AMBIGUOUS_GATE_FAIL),   # both gates fail
        (0.04, 0.01, 0.0, False, AMBIGUOUS_GATE_FAIL),    # dsr = 0 (degenerate)
    ])
    def test_exhaustiveness_sweep(
        self,
        p_spa: float,
        p_rc: float,
        dsr: float,
        technical_failure: bool,
        expected: str,
    ) -> None:
        """Parametrized exhaustiveness sweep covers all 5 outcomes and boundary cases."""
        result = evaluate_decision(
            p_spa=p_spa,
            p_rc=p_rc,
            dsr=dsr,
            technical_failure=technical_failure,
        )
        assert result == expected, (
            f"evaluate_decision(p_spa={p_spa}, p_rc={p_rc}, dsr={dsr}, "
            f"technical_failure={technical_failure}) -> {result!r}; "
            f"expected {expected!r}"
        )

    def test_all_outcomes_reachable(self) -> None:
        """All 5 decision outcomes must be reachable — no dead code in the functional."""
        all_outcomes = {TECHNICAL_FAILURE, AMBIGUOUS_STRADDLE, WIND_DOWN, CONTINUE, AMBIGUOUS_GATE_FAIL}
        reached = set()

        test_cases = [
            dict(p_spa=0.01, p_rc=0.01, dsr=0.99, technical_failure=True),   # TECHNICAL_FAILURE
            dict(p_spa=0.05, p_rc=0.01, dsr=0.99, technical_failure=False),  # AMBIGUOUS_STRADDLE
            dict(p_spa=0.90, p_rc=0.90, dsr=0.0, technical_failure=False),   # WIND_DOWN
            dict(p_spa=0.01, p_rc=0.01, dsr=0.97, technical_failure=False),  # CONTINUE
            dict(p_spa=0.01, p_rc=0.06, dsr=0.99, technical_failure=False),  # AMBIGUOUS_GATE_FAIL
        ]
        for kwargs in test_cases:
            reached.add(evaluate_decision(**kwargs))  # type: ignore[arg-type]

        assert reached == all_outcomes, (
            f"Not all outcomes were reached. Missing: {all_outcomes - reached}"
        )


# ---------------------------------------------------------------------------
# 3. Runner refusal path tests
# ---------------------------------------------------------------------------

class TestRunnerRefusal:
    """Tests that run_r5_step4.py refuses without valid flags and receipt.

    Uses subprocess so main() itself is exercised.  No real statistical run
    is ever performed here — kill_test_executed=false invariant.
    """

    @staticmethod
    def _runner_path() -> Path:
        """Resolve path to scripts/run_r5_step4.py from the repo root."""
        # Locate repo root (where pyproject.toml lives) relative to this test file
        here = Path(__file__).parent
        root = here.parent.parent
        runner = root / "scripts" / "run_r5_step4.py"
        assert runner.exists(), f"Runner not found: {runner}"
        return runner

    def test_missing_flag_exits_nonzero(self) -> None:
        """Missing --i-am-step4 flag must cause a non-zero exit (refusal)."""
        runner = self._runner_path()
        result = subprocess.run(
            [sys.executable, str(runner)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Runner must exit non-zero when --i-am-step4 is absent. "
            f"Got returncode={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_missing_freeze_receipt_arg_exits_nonzero(self) -> None:
        """--i-am-step4 alone (without --freeze-receipt) must exit non-zero."""
        runner = self._runner_path()
        result = subprocess.run(
            [sys.executable, str(runner), "--i-am-step4"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Runner must exit non-zero when --freeze-receipt is absent. "
            f"Got returncode={result.returncode}."
        )

    def test_wrong_receipt_hash_exits_nonzero(self) -> None:
        """A receipt with a wrong prereg_sha256 must cause a non-zero exit.

        The runner checks sha256(prereg_file) == receipt.prereg_sha256 before
        proceeding.  A mismatch must be a hard refusal (TECHNICAL FAILURE path).
        """
        runner = self._runner_path()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Create a fake pre-reg file
            fake_prereg = tmp / "r5_carry_universe_kill_test.md"
            fake_prereg.write_text("# Fake pre-reg for test\n")

            # Compute the WRONG sha256 (deliberate mismatch)
            wrong_sha = hashlib.sha256(b"intentionally wrong content").hexdigest()
            correct_sha = hashlib.sha256(fake_prereg.read_bytes()).hexdigest()
            assert wrong_sha != correct_sha, "Test setup error: hashes must differ"

            # Write a receipt with the WRONG hash
            receipt = {
                "prereg_path": str(fake_prereg),
                "prereg_sha256": wrong_sha,  # deliberate mismatch
                "code_commit": "0" * 40,
                "frozen_at_utc": "2026-06-05T00:00:00+00:00",
                "master_seed": 576746,
                "K": 5000,
                "sr0_pp": 0.022906,
                "n_elected": 3,
                "dsr_threshold": 0.95,
                "alpha": 0.05,
            }
            receipt_path = tmp / "test_receipt.yaml"
            with open(receipt_path, "w") as fh:
                yaml.dump(receipt, fh)

            result = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--i-am-step4",
                    "--freeze-receipt",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0, (
                f"Runner must exit non-zero when receipt SHA-256 is wrong. "
                f"Got returncode={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )
            # The error output should mention mismatch
            combined = result.stdout + result.stderr
            assert "mismatch" in combined.lower() or "sha" in combined.lower() or "sha256" in combined.lower(), (
                f"Expected 'mismatch' or 'sha' in output; got:\n{combined}"
            )

    def test_help_flag_exits_zero_without_running(self) -> None:
        """--help must work (exits 0) without triggering any computation."""
        runner = self._runner_path()
        result = subprocess.run(
            [sys.executable, str(runner), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"--help must exit 0; got returncode={result.returncode}.\n{result.stderr}"
        )

    def test_no_real_run_in_this_dispatch(self) -> None:
        """Meta-test: confirm kill_test_executed=false in this dispatch.

        No real p-value is computed in this test file.  This test always passes
        and exists to document the invariant explicitly in the test suite.
        """
        kill_test_executed = False
        assert not kill_test_executed, (
            "FATAL: kill_test_executed must be False in STEP 3. "
            "STEP 4 runs only after the freeze-receipt is committed."
        )


# ---------------------------------------------------------------------------
# 4. select_k_star_studentized — plain-Sharpe vs T_k ranking divergence
# ---------------------------------------------------------------------------


class TestSelectKStarStudentized:
    """Tests for select_k_star_studentized (§7.3.4 k* selection).

    The key invariant: when columns differ in autocorrelation structure, the
    T_k argmax can differ from the plain-Sharpe argmax.  These tests verify
    that the implementation picks the T_k argmax, not the plain-Sharpe argmax.
    """

    @staticmethod
    def _make_divergence_matrix(
        rng: np.random.Generator,
        T: int = 2000,
        block_length: int = 10,
    ) -> tuple[np.ndarray, int]:
        """Construct a (T, 2) synthetic matrix where plain-Sharpe and T_k rankings DIVERGE.

        Construction:
          Column A — higher plain Sharpe, strong AR(1) autocorrelation (rho=0.7):
            noise_A is AR(1), demeaned so its sample mean is exactly 0, then
            shifted by mu_A.  Plain SR_A > SR_B because mu_A > mu_B with nearly
            equal sample std.  HAC inflates omega_hat_A (AR(1) autocorrelation
            increases Newey-West variance), so T_k_A < T_k_B.

          Column B — slightly lower plain Sharpe, i.i.d. white noise:
            noise_B is i.i.d. normal, demeaned so sample mean = 0, shifted by
            mu_B < mu_A.  HAC omega_hat_B ≈ std/sqrt(T) (no inflation) ->
            T_k_B > T_k_A despite SR_B < SR_A.

        Both noises are demeaned before adding the target mean, so the SAMPLE
        means are exactly mu_A and mu_B regardless of random draws.  This makes
        the divergence deterministic (not seed-sensitive).

        Returns the matrix and the expected k* index (column B = 1).
        """
        # Column A: demeaned AR(1) noise + constant positive mean
        rho = 0.7
        sigma_eps = 0.01
        eps_A = rng.normal(0.0, sigma_eps, size=T)
        ar_A = np.empty(T)
        ar_A[0] = 0.0
        for t in range(1, T):
            ar_A[t] = rho * ar_A[t - 1] + eps_A[t]
        ar_A -= np.mean(ar_A)  # demean: sample mean of noise is exactly 0
        mu_A = 1.5e-4  # larger mean -> higher plain Sharpe
        col_A = mu_A + ar_A

        # Column B: demeaned i.i.d. noise + slightly smaller positive mean
        sigma_B = 0.01
        eps_B = rng.normal(0.0, sigma_B, size=T)
        eps_B -= np.mean(eps_B)  # demean
        mu_B = 1.0e-4  # smaller mean -> lower plain Sharpe; but no HAC inflation
        col_B = mu_B + eps_B

        R = np.column_stack([col_A, col_B])
        expected_k_star = 1  # column B: T_k_B > T_k_A despite SR_B < SR_A
        return R, expected_k_star

    def test_plain_sharpe_and_tk_rankings_diverge(self) -> None:
        """Verify the synthetic matrix actually has divergent rankings.

        This is a sanity check on the test construction itself: column A must
        have a higher plain Sharpe, but column B must have a higher T_k.
        """
        from forex_system.harness.reality_check import hac_se_nw

        rng = np.random.default_rng(42)
        R, _ = self._make_divergence_matrix(rng)
        T, k = R.shape
        block_length = 10
        bandwidth = max(block_length - 1, 1)

        # Plain annualized Sharpes
        sharpes = np.array([
            np.mean(R[:, j]) / np.std(R[:, j], ddof=1) * math.sqrt(252.0)
            for j in range(k)
        ])
        plain_argmax = int(np.argmax(sharpes))

        # Studentized T_k
        omegas = np.array([hac_se_nw(R[:, j], bandwidth=bandwidth) for j in range(k)])
        omegas = np.where(omegas < 1e-12, 1e-12, omegas)
        t_k = math.sqrt(T) * np.mean(R, axis=0) / omegas
        tk_argmax = int(np.argmax(t_k))

        assert plain_argmax == 0, (
            f"Test construction error: expected plain-Sharpe argmax = 0 (column A); "
            f"got {plain_argmax}.  Sharpes: {sharpes}"
        )
        assert tk_argmax == 1, (
            f"Test construction error: expected T_k argmax = 1 (column B); "
            f"got {tk_argmax}.  T_k values: {t_k}"
        )

    def test_select_k_star_picks_tk_argmax_not_plain_sharpe(self) -> None:
        """select_k_star_studentized must pick column B (T_k argmax), not column A.

        This is the core divergence test.  Column A has a higher plain Sharpe
        but strong positive autocorrelation; the HAC SE inflates omega_hat_A,
        reducing T_k_A below T_k_B.  The §7.3.4 contract requires k* = argmax T_k,
        so the correct answer is column B (index 1), not column A (index 0).
        """
        rng = np.random.default_rng(42)
        R, expected_k_star = self._make_divergence_matrix(rng)
        block_length = 10

        k_star_idx, t_k_star, sr_ann_kstar = select_k_star_studentized(
            R=R,
            block_length=block_length,
        )

        assert k_star_idx == expected_k_star, (
            f"select_k_star_studentized returned k*={k_star_idx} (plain-Sharpe argmax), "
            f"but §7.3.4 requires k*={expected_k_star} (T_k argmax).  "
            f"t_k_star={t_k_star!r}, sr_ann_kstar={sr_ann_kstar!r}"
        )

    def test_sr_ann_kstar_is_annualized_sharpe_of_selected_column(self) -> None:
        """sr_ann_kstar must equal mean/std(ddof=1)*sqrt(252) of the selected column."""
        rng = np.random.default_rng(7)
        R, _ = self._make_divergence_matrix(rng)
        block_length = 10

        k_star_idx, _t_k, sr_ann_kstar = select_k_star_studentized(R=R, block_length=block_length)

        col = R[:, k_star_idx]
        expected_sr = float(np.mean(col) / np.std(col, ddof=1) * math.sqrt(252.0))
        assert sr_ann_kstar == pytest.approx(expected_sr, rel=1e-9), (
            f"sr_ann_kstar={sr_ann_kstar!r} does not match hand-computed "
            f"annualized Sharpe {expected_sr!r} of column {k_star_idx}"
        )

    def test_t_k_star_is_studentized_statistic_of_selected_column(self) -> None:
        """t_k_star must equal sqrt(T)*mean/omega_hat for the selected column."""
        from forex_system.harness.reality_check import hac_se_nw

        rng = np.random.default_rng(99)
        R, _ = self._make_divergence_matrix(rng)
        T = R.shape[0]
        block_length = 10
        bandwidth = max(block_length - 1, 1)

        k_star_idx, t_k_star, _ = select_k_star_studentized(R=R, block_length=block_length)

        col = R[:, k_star_idx]
        omega = max(hac_se_nw(col, bandwidth=bandwidth), 1e-12)
        expected_t_k = math.sqrt(T) * float(np.mean(col)) / omega

        assert t_k_star == pytest.approx(expected_t_k, rel=1e-9), (
            f"t_k_star={t_k_star!r} does not match hand-computed T_k={expected_t_k!r} "
            f"for column {k_star_idx}"
        )

    def test_raises_on_bad_input(self) -> None:
        """select_k_star_studentized raises ValueError for bad R shape."""
        import pytest as _pytest

        with _pytest.raises(ValueError, match="2-D"):
            select_k_star_studentized(R=np.array([1.0, 2.0, 3.0]), block_length=5)

    def test_single_column_selects_index_zero(self) -> None:
        """With a single column, k* must always be index 0."""
        rng = np.random.default_rng(123)
        col = rng.normal(0.01, 0.01, size=500).reshape(-1, 1)
        k_star_idx, _, _ = select_k_star_studentized(R=col, block_length=5)
        assert k_star_idx == 0
