"""R5 STEP-4 DSR-gate and decision functional — pure, unit-testable functions.

Implements the frozen §7.3.3 / §7.3.4 / §7.3.5 / §7.3.6 specification from
references/pre-registrations/r5_carry_universe_kill_test.md.

This module contains NO research decisions.  Every numeric literal is frozen
by the pre-registration.  Do NOT import or call compute_dsr from dsr.py as
the execution path — the signature has no benchmark parameter and its internal
expected_max_sr benchmark differs from the frozen SR0_PP literal here.
compute_dsr is used ONLY as a conventions reference (§1.3, §7.3.3, §7.3.4).

scipy is REQUIRED (§7.3.4 A-5 pin).  If scipy is absent, TECHNICAL FAILURE
is raised immediately; approximation fallbacks are forbidden.
"""

from __future__ import annotations

import math

import numpy as np

# scipy is REQUIRED — no fallback approximation (§7.3.4 A-5 pin)
try:
    from scipy.stats import norm as _scipy_norm
except ImportError as _scipy_err:
    raise ImportError(
        "r5_decision: scipy.stats is required at run time (§7.3.4 A-5 pin). "
        "Install scipy before running STEP 4.  Approximation fallbacks are "
        "explicitly forbidden by the pre-registration."
    ) from _scipy_err

# ---------------------------------------------------------------------------
# Frozen constants (pre-registration §7.3.3, elected N = 3)
# ---------------------------------------------------------------------------

# Elected N = 3 scalar: SR0 = 0.363623 (annualized); SR0_pp = 0.363623 / sqrt(252)
# Source: §7.3.3 — "FROZEN (elected, N=3): SR0 = 0.363623 (annualized Sharpe units),
#   per-obs SR0_pp = 0.363623 / sqrt(252) = 0.022906."
# This literal is injected directly as the frozen benchmark; compute_dsr's internal
# expected_max_sr is NOT the execution path (§7.3.3, §7.3.4, §1.3 item 2).
SR0_PP: float = 0.022906  # per-obs benchmark; = 0.363623 / sqrt(252); elected N=3

# DSR threshold: §7.3.5 — "FROZEN: the DSR gate is cleared iff DSR >= 0.95"
DSR_THRESHOLD: float = 0.95

# MC-SE straddle band: §7.3.6 RULE 1 — "|p_SPA - 0.05| <= MC-SE = 0.0031"
_MC_SE: float = 0.0031

# Alpha: §4 / §7.3.5
_ALPHA: float = 0.05


def select_k_star_studentized(
    R: np.ndarray,
    block_length: int,
) -> tuple[int, float, float]:
    """Identify the best cell k* via the §7.3.4 studentized T_k statistic.

    Implements the exact §7.3.4 k* selection rule::

        omega_hat_k = hac_se_nw(R[:, k], bandwidth=max(block_length - 1, 1))
        T_k = sqrt(T) * mean(R[:, k]) / omega_hat_k
        k* = argmax_k T_k

    The HAC SE uses the Newey-West Bartlett kernel with bandwidth
    ``h = max(block_length - 1, 1)`` and a 1e-12 floor, mirroring
    :func:`~forex_system.harness.reality_check.r5c_hansen_spa` exactly.

    The annualized Sharpe fed to the DSR gate is computed from k* only
    (``mean / std(ddof=1) * sqrt(252)``) — the DSR gate input does not change
    (§7.3.4).  Only the SELECTION of k* changes vs. the plain-Sharpe argmax.

    Parameters
    ----------
    R:
        2-D float array of shape ``(T, k)``: per-bar return for each cell.
    block_length:
        The block length used by ``r5c_hansen_spa`` for the same matrix — MUST
        be the same value that was passed to the SPA call (or auto-selected by
        Politis-White).  The bandwidth used here is ``max(block_length - 1, 1)``.

    Returns
    -------
    k_star_idx: int
        Column index of the argmax cell.
    t_k_star: float
        T_k value of the selected cell (``sqrt(T) * mean / omega_hat``).
    sr_ann_kstar: float
        Annualized Sharpe of the selected cell (``mean / std(ddof=1) * sqrt(252)``);
        this is the value to pass to ``compute_dsr_gate``.

    Raises
    ------
    ValueError
        If ``R`` is not 2-D with at least 2 rows.
    """
    from forex_system.harness.reality_check import hac_se_nw  # avoid circular at module level

    if R.ndim != 2 or R.shape[0] < 2:
        raise ValueError(
            f"select_k_star_studentized: R must be 2-D with >= 2 rows, got shape {R.shape}"
        )
    T, k = R.shape
    bandwidth = max(block_length - 1, 1)
    means = np.mean(R, axis=0)
    omegas = np.array([hac_se_nw(R[:, j], bandwidth=bandwidth) for j in range(k)])
    # Floor at 1e-12 (mirrors the guard in r5c_hansen_spa)
    omegas = np.where(omegas < 1e-12, 1e-12, omegas)
    t_k = math.sqrt(T) * means / omegas  # shape (k,)
    k_star_idx = int(np.argmax(t_k))
    t_k_star = float(t_k[k_star_idx])
    # Annualized Sharpe of k* (the DSR gate input — §7.3.4)
    std_kstar = float(np.std(R[:, k_star_idx], ddof=1))
    sr_ann_kstar = (
        float(means[k_star_idx]) / std_kstar * math.sqrt(252.0)
        if std_kstar > 0.0
        else 0.0
    )
    return k_star_idx, t_k_star, sr_ann_kstar


def compute_dsr_gate(
    sr_ann_best_cell: float,
    skew: float,
    excess_kurtosis: float,
    T: int,
) -> float:
    """Compute the frozen DSR statistic for the best cell k*.

    Implements §7.3.4 EXACTLY with the frozen literal SR0_PP = 0.022906 (N=3).
    Conventions are pinned to compute_dsr in dsr.py (§7.3.3, §7.3.4):
      - Per-obs conversion: SR_pp = SR_ann / sqrt(252)  (dsr.py:180)
      - Variance term: 1 - skew*SR_pp + ((excess_kurtosis+2)/4)*SR_pp^2  (dsr.py:184)
      - Degenerate pin 1: sr_ann <= 0 -> DSR = 0.0  (dsr.py:168-169)
      - Degenerate pin 2: var_term <= 0 -> DSR = 0.0  (dsr.py:187-195)
      - CDF: scipy.stats.norm.cdf (required — no approximation)  (dsr.py:205-207)
      - Final clip to [0, 1]  (dsr.py:205-207)

    Both degenerate-path outcomes are gate-FAIL (DSR = 0.0), NOT technical failures.

    Parameters
    ----------
    sr_ann_best_cell:
        Annualized Sharpe of cell k* (the argmax of the SPA family statistic).
        Same scale as calculate_metrics() output.
    skew:
        scipy.stats.skew(x, bias=True) of cell k*'s return series (§7.3.4 A-5).
    excess_kurtosis:
        scipy.stats.kurtosis(x, fisher=True, bias=True) of cell k*'s return series
        (Fisher convention, i.e. kurtosis - 3; §7.3.4 A-5).
    T:
        Number of observations (bars) in cell k*'s return series (length of
        the frozen common index = 4186 in the real run; any value in tests).

    Returns
    -------
    float
        DSR in [0, 1].  DSR >= 0.95 means the gate is cleared (§7.3.5).
        DSR = 0.0 for both degenerate paths (gate FAIL).

    Raises
    ------
    ImportError
        If scipy is not importable (TECHNICAL FAILURE path — raised at module import).
    """
    # Degenerate pin 1: non-positive Sharpe cannot exceed the positive deflated benchmark.
    # Reference: dsr.py:168-169 (early return `if sharpe_ratio <= 0.0: return 0.0`)
    # §7.3.4: "SR_hat <= 0 -> DSR = 0.0 ... gate FAIL, not technical failure"
    if sr_ann_best_cell <= 0.0:
        return 0.0

    # §7.3.4: SR_pp = SR_hat_ann / sqrt(252)  (per-observation units; dsr.py:180)
    sr_pp = sr_ann_best_cell / math.sqrt(252.0)

    # §7.3.4: var_term = 1 - gamma3*SR_pp + ((gamma4_excess+2)/4)*SR_pp^2
    # Kurtosis coefficient: (excess_kurtosis+2)/4 — the corrected BLP(2014) form (dsr.py:184)
    # NOT (+3)/4, NOT (+1)/4 — derivation: V[SR] ∝ gamma4_nonexcess-1)/4 = (excess+3-1)/4
    kurtosis_coeff = (excess_kurtosis + 2.0) / 4.0
    var_term = 1.0 - skew * sr_pp + kurtosis_coeff * sr_pp ** 2

    # Degenerate pin 2: cannot certify when variance term is non-positive.
    # Reference: dsr.py:187-195 ("return 0.0 and emit structured warning")
    # §7.3.4: "var_term <= 0 -> DSR = 0.0 ... gate FAIL, not technical failure"
    if var_term <= 0.0:
        return 0.0

    # §7.3.4: DSR = Phi( (SR_pp - SR0_pp) * sqrt(T-1) / sqrt(var_term) )
    # SR0_pp = 0.022906 is the frozen literal (elected N=3 per §7.3.3)
    z = (sr_pp - SR0_PP) * math.sqrt(T - 1) / math.sqrt(var_term)

    # §7.3.4: Phi = scipy.stats.norm.cdf (required; approximations forbidden)
    # Final clip to [0, 1] per dsr.py:205-207
    dsr = float(_scipy_norm.cdf(z))
    return max(0.0, min(1.0, dsr))


# ---------------------------------------------------------------------------
# Possible decision outcomes (§7.3.6)
# ---------------------------------------------------------------------------

WIND_DOWN = "WIND_DOWN"
CONTINUE = "CONTINUE"
AMBIGUOUS_STRADDLE = "AMBIGUOUS_STRADDLE"
AMBIGUOUS_GATE_FAIL = "AMBIGUOUS_GATE_FAIL"
TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


def evaluate_decision(
    p_spa: float,
    p_rc: float,
    dsr: float,
    technical_failure: bool,
) -> str:
    """Apply the §7.3.6 ordered decision functional.

    The functional is ordered and mutually exclusive: the FIRST matching rule
    fires and evaluation stops.  No boundary case can buy CONTINUE.

    Rules (§7.3.6):
      RULE 0 — TECHNICAL_FAILURE: technical_failure is True.
               Fires unconditionally if set; all other rules are skipped.
      RULE 1 — AMBIGUOUS_STRADDLE: |p_spa - 0.05| <= 0.0031.
               Evaluated BEFORE CONTINUE/WIND-DOWN so a straddle p can buy
               neither a false CONTINUE nor a falsely-clean WIND-DOWN.
      RULE 2 — WIND_DOWN: p_spa >= 0.05 (and not in straddle band).
               The carry family is statistically indistinguishable from chance.
      RULE 3 — CONTINUE: p_spa < 0.05 AND outside straddle band (i.e.
               p_spa < 0.0469) AND dsr >= 0.95 AND p_rc < 0.05.
               CONTINUE is necessary-but-not-sufficient (§3.2, §4).
      RULE 4 — AMBIGUOUS_GATE_FAIL: catch-all ensuring exhaustiveness.
               Fires when p_spa < 0.0469 but DSR or RC gate fails.

    Boundary ruling (§7.3.6, restated): p_spa = 0.048, dsr = 0.96, p_rc = 0.01
    -> AMBIGUOUS_STRADDLE (|0.048 - 0.05| = 0.002 <= 0.0031; RULE 1 fires first).

    Parameters
    ----------
    p_spa:
        Hansen-SPA "consistent" p-value (primary decision statistic; §2.4).
    p_rc:
        White Reality-Check cross-check p-value.
    dsr:
        DSR statistic from compute_dsr_gate() for the best cell k*.
    technical_failure:
        True if a code error, data-integrity fault, unlogged cell drop,
        freeze-receipt mismatch, or §7.3.4 convention divergence was detected.

    Returns
    -------
    str
        One of: TECHNICAL_FAILURE, AMBIGUOUS_STRADDLE, WIND_DOWN, CONTINUE,
        AMBIGUOUS_GATE_FAIL.
    """
    # RULE 0 — TECHNICAL FAILURE (§7.3.6: fires iff technical_failure flag set)
    if technical_failure:
        return TECHNICAL_FAILURE

    # RULE 1 — AMBIGUOUS STRADDLE (§7.3.6: |p_SPA - 0.05| <= MC-SE = 0.0031)
    # Evaluated BEFORE RULE 2/3 so a straddle result resolves here, never to
    # CONTINUE or clean WIND-DOWN.
    if abs(p_spa - _ALPHA) <= _MC_SE:
        return AMBIGUOUS_STRADDLE

    # RULE 2 — WIND DOWN (§7.3.6: p_SPA >= 0.05 and outside straddle band)
    # At this point we know |p_spa - 0.05| > 0.0031, so p_spa > 0.0531 here.
    if p_spa >= _ALPHA:
        return WIND_DOWN

    # At this point: p_spa < 0.05 AND p_spa < 0.0469 (outside straddle band).

    # RULE 3 — CONTINUE (§7.3.6: dsr >= 0.95 AND p_rc < 0.05)
    if dsr >= DSR_THRESHOLD and p_rc < _ALPHA:
        return CONTINUE

    # RULE 4 — AMBIGUOUS GATE FAIL (catch-all; §7.3.6 guarantees exhaustiveness)
    # Fires when p_spa < 0.0469 but (DSR < 0.95 OR p_rc >= 0.05).
    return AMBIGUOUS_GATE_FAIL
