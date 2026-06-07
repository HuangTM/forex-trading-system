"""QRB-6 CB-event-study decision module — pure, unit-testable functions.

Implements the frozen §4.2 / §5 / §6 specification from:
  references/pre-registrations/qrb6_cb_event_study.md  (trial fa0f982a)

All numeric thresholds are PARAMETERS sourced from the freeze-receipt at
runtime.  Module-level _EXPECTED_* constants are guards for the interlock
test ONLY — they mirror the frozen receipt values and raise if the receipt
disagrees with the embedded pre-reg.  These are QRB-6-ONLY constants
(clearly labelled); they MUST NOT be imported by any other trial module.

CROSS-TRIAL CONSTANT CONTAMINATION: this module MUST NOT import or reference:
  - r5_decision.SR0_PP  (0.022906 — R5-only; FORBIDDEN here)
  - confirmatory receipt sr0_pp (0.034921 — FORBIDDEN here)
Any such import voids the QRB-6 pre-registration (§1.4(4)).

scipy is REQUIRED (§3.3/§6 — A-5 pin).  Absence → ImportError at module load.
No approximation fallback is permitted (mirroring r5_decision.py convention).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

# scipy REQUIRED — no fallback (§3.3, §6 A-5 pin; mirrors r5_decision.py)
try:
    from scipy.stats import norm as _scipy_norm
except ImportError as _scipy_err:
    raise ImportError(
        "qrb6_decision: scipy.stats is required at run time (§3.3/§6 A-5 pin). "
        "Install scipy before running the QRB-6 runner.  Approximation fallbacks "
        "are explicitly forbidden by the pre-registration."
    ) from _scipy_err

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# _EXPECTED guard constants — QRB-6-ONLY; sourced from pre-reg §4.2/§5/§6.
# Used ONLY in the interlock check below.  DO NOT import these into any other
# trial module (cross-trial contamination, §1.4(4)).
# ---------------------------------------------------------------------------

# FROZEN QRB-6 thresholds (Mathematician §2.5, §4.2, §6)
_EXPECTED_SR0_PP_SEL: float = 0.026861     # QRB-6-ONLY; NOT the R5 value; NOT the confirmatory value
_EXPECTED_N_SEL: int = 3                    # QRB-6-ONLY paper-selection charge
_EXPECTED_DSR_THRESHOLD: float = 0.95      # firm-wide gate
_EXPECTED_KILL_SWITCH_A: float = 1.5883    # Scenario A (T=506); QRB-6-ONLY
_EXPECTED_KILL_SWITCH_B: float = 1.4029    # Scenario B (T=716); QRB-6-ONLY
_EXPECTED_ALPHA: float = 0.05              # one-sided total
_EXPECTED_MC_SE: float = 0.0022            # at K=10000; straddle half-width
# OBF 2-look extra-look penalty applied (look-1 = voided run; NHT remediation-ratification.yaml 2026-06-07):
#   p_reject = 0.05 − 0.01001 alpha-spend − 0.0022 MC-SE = 0.0378 (strict < for PASS)
#   p_straddle_hi = 0.039995 + 0.0022 = 0.0422 (strict > for KILL; closed band [0.0378, 0.0422])
# Former void-run values (now superseded): p_reject=0.0478, p_straddle_hi=0.0522.
_EXPECTED_P_REJECT: float = 0.0378        # OBF extra-look: = 0.05 − look-1-spend − MC-SE
_EXPECTED_P_STRADDLE_HI: float = 0.0422   # OBF extra-look: = look-2-boundary + MC-SE (KILL threshold)
_EXPECTED_MASTER_SEED: int = 387992        # int('fa0f98',16) mod 1e6; QRB-6-ONLY
_EXPECTED_K: int = 10000                   # bootstrap resamples
_EXPECTED_SPREAD_Z_THRESHOLD: float = 3.0  # QRB-2 overlay (§5.5)
_EXPECTED_POST_2015_CUTOFF: str = "2015-01-01"  # structural-break endpoint (§3.4)
_EXPECTED_SCENARIO_A_N: int = 506          # deduped event-days (NHT-verified)
_EXPECTED_POST_2015_A_N: int = 345         # post-2015 sub-window (NHT-verified)

# Scenario A banks (verified-official tier only; §3.1)
_SCENARIO_A_BANKS: frozenset[str] = frozenset({"FED", "BOJ", "RBA", "BOC"})

# Inadmissible verification grade (§3.1 — verbatim filter from pre-reg)
_INADMISSIBLE_VERIFICATION: str = "training-memory-unverified"

# Pair×bank map (frozen §3.2; verified data inventory)
_BANK_PAIR_MAP: dict[str, list[str]] = {
    "FED": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD"],
    "BOJ": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY"],
    "RBA": ["AUDUSD", "AUDJPY"],
    "BOC": ["USDCAD", "CADJPY"],
    # Scenario B extensions (activated only on C4 spot-check certified)
    "BOE": ["EURGBP", "GBPUSD", "GBPJPY"],
    "ECB": ["EURUSD", "EURJPY", "EURGBP"],
    "RBNZ": ["NZDUSD", "NZDJPY"],
}

# Post-2015 cutoff (§3.4; inclusive)
_POST_2015_CUTOFF = pd.Timestamp("2015-01-01")

# ---------------------------------------------------------------------------
# Decision outcome constants (§4.2 RULES)
# ---------------------------------------------------------------------------

RULE_0_TECHNICAL_FAILURE = "RULE_0_TECHNICAL_FAILURE"
RULE_1_KILL_POST2015 = "RULE_1_KILL_POST2015"
RULE_2_KILL_AGGREGATE = "RULE_2_KILL_AGGREGATE"
RULE_3_PASS = "RULE_3_PASS"
RULE_4_AMBIGUOUS = "RULE_4_AMBIGUOUS"


# ---------------------------------------------------------------------------
# Receipt interlock guard
# ---------------------------------------------------------------------------


def check_receipt_constants(receipt: dict) -> None:
    """Verify freeze-receipt constants match the embedded _EXPECTED guards.

    Called by the runner immediately after loading the receipt.  Any mismatch
    means the receipt was cut from a different pre-reg version and this run
    must HALT (RULE 0).

    Parameters
    ----------
    receipt:
        Parsed freeze-receipt dict.

    Raises
    ------
    SystemExit(1)
        On any mismatch (RULE 0 TECHNICAL_FAILURE).
    """
    import sys

    mismatches: list[str] = []

    def _check(field: str, expected: object, tol: float | None = None) -> None:
        val = receipt.get(field)
        if val is None:
            mismatches.append(f"  {field}: MISSING (expected {expected!r})")
            return
        if tol is not None:
            if abs(float(val) - float(expected)) > tol:  # type: ignore[arg-type]
                mismatches.append(
                    f"  {field}: receipt={val!r} vs expected={expected!r} (tol={tol})"
                )
        elif val != expected:
            mismatches.append(f"  {field}: receipt={val!r} vs expected={expected!r}")

    _check("sr0_pp", _EXPECTED_SR0_PP_SEL, tol=1e-8)
    _check("n_sel", _EXPECTED_N_SEL)
    _check("dsr_threshold", _EXPECTED_DSR_THRESHOLD, tol=1e-9)
    _check("kill_switch_threshold", _EXPECTED_KILL_SWITCH_A, tol=1e-4)
    _check("alpha", _EXPECTED_ALPHA, tol=1e-9)
    _check("master_seed", _EXPECTED_MASTER_SEED)
    _check("K", _EXPECTED_K)
    _check("spread_z_threshold", _EXPECTED_SPREAD_Z_THRESHOLD, tol=1e-9)
    _check("scenario_a_event_days", _EXPECTED_SCENARIO_A_N)
    _check("post_2015_a", _EXPECTED_POST_2015_A_N)
    # OBF extra-look p-gate thresholds (remediation v2): wire the guards into the
    # interlock so a receipt whose p-thresholds drift from the embedded constants
    # RULE-0s rather than silently executing a different gate.
    _check("p_reject_threshold", _EXPECTED_P_REJECT, tol=1e-9)
    _check("p_straddle_hi", _EXPECTED_P_STRADDLE_HI, tol=1e-9)
    _check("trial_id", "fa0f982a")

    if mismatches:
        print(
            "RULE_0_TECHNICAL_FAILURE: freeze-receipt constants mismatch the "
            "embedded pre-reg guards.  The receipt may have been cut from a "
            "different pre-reg version.  Halt — do not read any p-values.\n"
            + "\n".join(mismatches),
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Event-set construction (§3.1, §3.2, §3.4)
# ---------------------------------------------------------------------------


def build_scenario_a_event_set(
    calendar_path: str | None = None,
    calendar_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the Scenario A event set from the CB decision calendar.

    Applies the frozen filter chain:
      1. Exclude training-memory-unverified rows (§3.1 verbatim filter).
      2. Keep verified-official rows only (Scenario A = FED/BOJ/RBA/BOC).
      3. Keep Scenario A banks only.
      4. Deduplicate by market-day (date), preserving one row per date.
         When multiple banks decide on the same day, the row with the
         alphabetically-first bank (stable sort) is kept as the representative
         (block-day label); this is purely for block construction — each bank's
         pair-level returns are computed from the undeduped bank-event list.

    Parameters
    ----------
    calendar_path:
        Path to `data/rates/cb_decision_dates.parquet`.  Mutually exclusive
        with calendar_df.
    calendar_df:
        Pre-loaded DataFrame (for testing without file I/O).

    Returns
    -------
    pd.DataFrame
        Deduped Scenario A event set.  Columns include at minimum:
        ``bank``, ``currency``, ``date``, ``verification``.
        Index is reset (integer).

    Raises
    ------
    ValueError
        If neither or both of calendar_path / calendar_df are provided.
    ValueError
        If the deduped count does not match _EXPECTED_SCENARIO_A_N (506).
    """
    if calendar_path is None and calendar_df is None:
        raise ValueError("Provide exactly one of calendar_path or calendar_df.")
    if calendar_path is not None and calendar_df is not None:
        raise ValueError("Provide exactly one of calendar_path or calendar_df.")

    if calendar_df is None:
        df = pd.read_parquet(calendar_path)  # type: ignore[arg-type]
    else:
        df = calendar_df.copy()

    # Step 1: MANDATORY filter — verbatim from §3.1 pre-reg requirement.
    # "df = df[df['verification'] != 'training-memory-unverified']"  — verbatim.
    df = df[df["verification"] != _INADMISSIBLE_VERIFICATION]

    # Step 2: Keep verified-official only (Scenario A tier)
    df = df[df["verification"] == "verified-official"]

    # Step 3: Keep Scenario A banks
    df = df[df["bank"].isin(_SCENARIO_A_BANKS)]

    # Step 4: Deduplicate by market-day (date).
    # Sort by (date, bank) for deterministic representative selection.
    df = df.sort_values(["date", "bank"]).reset_index(drop=True)
    df_dedup = df.drop_duplicates(subset=["date"], keep="first").reset_index(drop=True)

    n_actual = len(df_dedup)
    if n_actual != _EXPECTED_SCENARIO_A_N:
        raise ValueError(
            f"Scenario A event set count mismatch: expected {_EXPECTED_SCENARIO_A_N} "
            f"deduped event-days, got {n_actual}.  Check the calendar parquet and "
            "filter chain (§3.1, §3.2).  If the calendar has changed, update the "
            "pre-registration (new trial required)."
        )

    return df_dedup


def get_post_2015_mask(event_set: pd.DataFrame) -> pd.Series:
    """Return a boolean mask for the post-2015 sub-window (date >= 2015-01-01).

    §3.4 pin: post_2015_cutoff = 2015-01-01 (inclusive; structural-break endpoint).

    Parameters
    ----------
    event_set:
        DataFrame with a ``date`` column (datetime-like).

    Returns
    -------
    pd.Series of bool, same index as event_set.
    """
    return event_set["date"] >= _POST_2015_CUTOFF


def get_bank_event_pairs(bank: str, scenario_b: bool = False) -> list[str]:
    """Return the frozen list of FX pairs for a given bank (§3.2).

    Parameters
    ----------
    bank:
        One of FED, BOJ, RBA, BOC (Scenario A) or additionally BOE, ECB,
        RBNZ (Scenario B, activated on C4).
    scenario_b:
        If True, Scenario B banks are accepted; otherwise only Scenario A banks
        are valid.

    Returns
    -------
    list[str]
        Sorted list of pair names (uppercase).

    Raises
    ------
    KeyError
        If the bank is not in the frozen map or is a Scenario B bank when
        scenario_b=False.
    """
    if bank not in _BANK_PAIR_MAP:
        raise KeyError(f"Bank {bank!r} not in frozen pair×bank map (§3.2).")
    if not scenario_b and bank not in _SCENARIO_A_BANKS:
        raise KeyError(
            f"Bank {bank!r} is a Scenario B bank; set scenario_b=True to access."
        )
    return list(_BANK_PAIR_MAP[bank])


# ---------------------------------------------------------------------------
# Sign alignment and y_e assembly (§1.2, §5.0, §4.4.1-§4.4.3)
# ---------------------------------------------------------------------------


def compute_sign_align(close_d: float, close_d_minus_1: float) -> float:
    """Compute sign_align_e = sign(close(D) - close(D-1)).

    Frozen rule (§5.0 / §4.4.1):
      - sign_align_e = +1.0 if close(D) > close(D-1)
      - sign_align_e = -1.0 if close(D) < close(D-1)
      - sign_align_e =  0.0 if close(D) == close(D-1) exactly (degenerate; §4.4.3)

    Uses numpy.sign semantics (returns 0.0 for zero input).

    Parameters
    ----------
    close_d:
        Close price of the decision-reflecting bar D.
    close_d_minus_1:
        Close price of bar D-1.

    Returns
    -------
    float
        One of {-1.0, 0.0, +1.0}.
    """
    # §4.4.3 requirement: use numpy.sign (returns 0.0 when ret_D = 0.0 exactly)
    ret_d = close_d - close_d_minus_1
    return float(np.sign(ret_d))


def compute_y_e(
    sign_align: float,
    post_window_net_return: float,
) -> float | None:
    """Compute the signed-product event return y_e for one bank-event.

    y_e = sign_align_e * R_post,e  (§1.2)

    If sign_align == 0.0 (degenerate; §4.4.3): returns None (event EXCLUDED from
    the return series; the event-day still counts as a block-day).

    Parameters
    ----------
    sign_align:
        Result of compute_sign_align() for this bank-event.
    post_window_net_return:
        Equal-weight net-of-cost cumulative return over the K_post=2 window for
        this bank-event's mapped pairs (close(D) → close(D+2), entered at D+1
        under entry_delay_bars=1).

    Returns
    -------
    float or None
        y_e scalar, or None for the FLAT degenerate case.
    """
    if sign_align == 0.0:
        # Degenerate: no direction, FLAT; excluded from return average (§4.4.3)
        return None
    return sign_align * post_window_net_return


# ---------------------------------------------------------------------------
# Studentized statistic (§1.3)
# ---------------------------------------------------------------------------


def compute_t_stat(
    y_e_series: np.ndarray,
    block_length: int,
) -> float:
    """Compute the studentized mean event-window return (§1.3).

    t_stat = sqrt(n) * mean(y) / omega_hat

    omega_hat = Newey-West HAC SE with bandwidth = max(L - 1, 1), where L is
    the Politis-White auto block-length on the event-day-ordered series.

    The HAC is computed on the EVENT-DAY INDEX ordering (not calendar-day lags;
    §1.3 event-study HAC note).

    Parameters
    ----------
    y_e_series:
        1-D array of y_e scalars (non-None observations only; degenerate events
        excluded).  Must be ordered ascending by decision date.
    block_length:
        L (the Politis-White block length for this series); must be >= 1.

    Returns
    -------
    float
        Studentized t-statistic.  Returns 0.0 if n < 2 (degenerate series).

    Raises
    ------
    ValueError
        If y_e_series is not 1-D.
    """
    from forex_system.harness.reality_check import hac_se_nw

    y = np.asarray(y_e_series, dtype=float)
    if y.ndim != 1:
        raise ValueError(f"compute_t_stat: y_e_series must be 1-D, got shape {y.shape}")
    n = len(y)
    if n < 2:
        return 0.0
    bandwidth = max(block_length - 1, 1)
    omega_hat = hac_se_nw(y, bandwidth=bandwidth)
    return float(math.sqrt(n) * np.mean(y) / omega_hat)


# ---------------------------------------------------------------------------
# Banks-as-blocks bootstrap spec hooks (§3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BankBlockBootstrapResult:
    """Result of the banks-as-blocks stationary block bootstrap.

    Attributes
    ----------
    pvalue:
        One-sided p-value = (1 + #{t*_b >= t_obs}) / (K + 1).
    t_obs:
        Observed t-statistic on the full event series.
    K:
        Number of bootstrap resamples.
    master_seed:
        RNG seed used.
    n_included:
        Number of non-degenerate events included in the return average.
    n_total:
        Total number of event-days (including degenerate FLAT events).
    block_lengths_per_bank:
        Dict mapping bank → block-length used.
    """

    pvalue: float
    t_obs: float
    K: int
    master_seed: int
    n_included: int
    n_total: int
    block_lengths_per_bank: dict[str, int]


def run_bank_blocked_bootstrap(
    y_e_by_bank: dict[str, np.ndarray],
    master_seed: int,
    K: int,
) -> BankBlockBootstrapResult:
    """Run the banks-as-blocks stationary block bootstrap (§3.1–§3.4).

    Scheme:
      - Partition y_e observations by bank label (event-day ordered).
      - Compute per-bank Politis-White block length L_group.
      - Compute pooled HAC bandwidth = max(L_group) across banks (§3.2).
      - Compute t_obs on the full pooled series (event-day ordered).
      - Impose H0 by de-meaning: d_e = y_e - mean(y_e) (§1.4 step 2).
      - For b = 1..K: resample each bank group independently via the
        stationary circular block bootstrap with its per-bank L_group,
        concatenate to form the resample, recompute t*_b (HAC SE recomputed
        per resample; §1.4 step 3).
      - p = (1 + #{t*_b >= t_obs}) / (K + 1)  (§3.3; +1/+1 formula).

    Parameters
    ----------
    y_e_by_bank:
        Dict mapping bank name → 1-D numpy array of y_e values for that bank's
        events (ordered ascending by decision date; None/degenerate events
        already EXCLUDED — the input arrays contain only non-None y_e).
    master_seed:
        RNG seed (from receipt); numpy.PCG64 (§3.4).
    K:
        Number of bootstrap resamples (from receipt; typically 10000).

    Returns
    -------
    BankBlockBootstrapResult
    """
    from forex_system.harness.reality_check import (
        _circular_block_bootstrap,
        hac_se_nw,
        politis_white_block_length,
    )

    # Per-bank block lengths (§3.2)
    bank_block_lengths: dict[str, int] = {}
    for bank, y_bank in y_e_by_bank.items():
        if len(y_bank) < 2:
            # Near-empty group: use L=1
            bank_block_lengths[bank] = 1
        else:
            L_pw = politis_white_block_length(y_bank)
            bank_block_lengths[bank] = max(1, math.ceil(L_pw))

    # Pooled L for HAC (max across banks; §3.2)
    L_pool = max(bank_block_lengths.values()) if bank_block_lengths else 1

    # Pooled y_e (concatenate all banks in sorted bank order for reproducibility)
    banks_sorted = sorted(y_e_by_bank.keys())
    y_all = np.concatenate([y_e_by_bank[b] for b in banks_sorted])
    n_included = len(y_all)
    n_total = n_included  # caller is responsible for passing non-None arrays

    # Observed statistic (§1.3)
    bandwidth = max(L_pool - 1, 1)
    omega_hat_obs = hac_se_nw(y_all, bandwidth=bandwidth)
    t_obs = float(math.sqrt(n_included) * np.mean(y_all) / omega_hat_obs)

    # De-mean to impose H0 (§1.4 step 2)
    d_all_by_bank: dict[str, np.ndarray] = {}
    mean_all = float(np.mean(y_all))
    for bank in banks_sorted:
        d_all_by_bank[bank] = y_e_by_bank[bank] - mean_all

    # Bootstrap (§1.4 step 3)
    rng = np.random.default_rng(np.random.PCG64(master_seed))
    t_boot = np.empty(K, dtype=float)

    for b in range(K):
        # Resample each bank group independently, then concatenate
        parts: list[np.ndarray] = []
        for bank in banks_sorted:
            d_bank = d_all_by_bank[bank]
            n_bank = len(d_bank)
            if n_bank == 0:
                continue
            L_bank = bank_block_lengths[bank]
            # _circular_block_bootstrap returns shape (1, n_bank)
            resampled = _circular_block_bootstrap(d_bank, L_bank, 1, rng)
            parts.append(resampled[0])
        d_boot = np.concatenate(parts)
        n_boot = len(d_boot)
        # Recompute HAC SE on the resample (§1.4 step 3)
        omega_hat_boot = hac_se_nw(d_boot, bandwidth=bandwidth)
        if omega_hat_boot < 1e-12:
            omega_hat_boot = 1e-12
        t_boot[b] = math.sqrt(n_boot) * float(np.mean(d_boot)) / omega_hat_boot

    # p-value (+1/+1 formula; §3.3, §1.4 step 4)
    pvalue = float((1 + np.sum(t_boot >= t_obs)) / (K + 1))

    return BankBlockBootstrapResult(
        pvalue=pvalue,
        t_obs=t_obs,
        K=K,
        master_seed=master_seed,
        n_included=n_included,
        n_total=n_total,
        block_lengths_per_bank=bank_block_lengths,
    )


# ---------------------------------------------------------------------------
# Annualized Sharpe for DSR input
# ---------------------------------------------------------------------------


def compute_event_sharpe_ann(y_e_series: np.ndarray) -> float:
    """Annualized Sharpe of the pooled signed-event-return series.

    Convention: mean / std(ddof=1) * sqrt(252).
    Returns 0.0 if std == 0 or n < 2.

    Parameters
    ----------
    y_e_series:
        1-D array of non-degenerate y_e values (ordered by event date).
    """
    y = np.asarray(y_e_series, dtype=float)
    if len(y) < 2:
        return 0.0
    std = float(np.std(y, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(y) / std * math.sqrt(252.0))


# ---------------------------------------------------------------------------
# DSR gate (§5.7; mirroring r5_decision.compute_dsr_gate with QRB-6 SR0)
# ---------------------------------------------------------------------------


def compute_dsr_qrb6(
    sr_ann: float,
    skew: float,
    excess_kurtosis: float,
    T: int,
    sr0_pp: float,
    dsr_threshold: float = _EXPECTED_DSR_THRESHOLD,
) -> float:
    """Compute the DSR for the QRB-6 event-study pooled series.

    Uses the FRESH QRB-6 SR0_pp (sr0_pp parameter from receipt) — NOT the R5-only
    value, NOT the confirmatory-only value.  The computation mirrors
    r5_decision.compute_dsr_gate exactly
    (dsr.py conventions §6).

    Parameters
    ----------
    sr_ann:
        Annualized Sharpe of the pooled event-return series (aggregate set).
    skew:
        scipy.stats.skew(y_e, bias=True) of the series.
    excess_kurtosis:
        scipy.stats.kurtosis(y_e, fisher=True, bias=True) of the series.
    T:
        Number of non-degenerate event observations (n_included).
    sr0_pp:
        Per-observation SR0 benchmark — MUST come from the freeze-receipt
        (expected: 0.026861; QRB-6-ONLY; §2.5).
    dsr_threshold:
        Gate threshold (expected: 0.95).

    Returns
    -------
    float
        DSR in [0, 1].  Returns 0.0 for degenerate cases (gate FAIL).
    """
    # Degenerate pin 1: non-positive Sharpe → DSR = 0.0 (gate FAIL)
    if sr_ann <= 0.0:
        return 0.0

    sr_pp = sr_ann / math.sqrt(252.0)

    # var_term = 1 - skew*SR_pp + ((excess_kurtosis+2)/4)*SR_pp^2  (dsr.py:184)
    kurtosis_coeff = (excess_kurtosis + 2.0) / 4.0
    var_term = 1.0 - skew * sr_pp + kurtosis_coeff * sr_pp**2

    # Degenerate pin 2: non-positive var_term → DSR = 0.0 (gate FAIL)
    if var_term <= 0.0:
        return 0.0

    # DSR = Phi((SR_pp - SR0_pp_sel) * sqrt(T-1) / sqrt(var_term))
    z = (sr_pp - sr0_pp) * math.sqrt(T - 1) / math.sqrt(var_term)
    dsr = float(_scipy_norm.cdf(z))
    return max(0.0, min(1.0, dsr))


# ---------------------------------------------------------------------------
# Decision functional — §4.2 RULES 0–4 (ordered, exhaustive, mutually exclusive)
# ---------------------------------------------------------------------------


def evaluate_decision(
    p_post2015: float,
    p_agg: float,
    dsr: float,
    technical_failure: bool,
    # Threshold parameters sourced from receipt (no hardcoded defaults that could
    # silently run unfrozen — all callers MUST pass receipt values explicitly)
    p_kill_threshold: float,       # strict > this → KILL (= 0.0422; OBF extra-look)
    p_reject_threshold: float,     # strict < this → clean reject (= 0.0378; OBF extra-look)
    dsr_threshold: float,          # >= this → DSR gate cleared (= 0.95)
) -> str:
    """Apply the §4.2 ordered decision functional.

    RULE 0 → RULE 1 → RULE 2 → RULE 3 → RULE 4 (first match fires, stops).

    Boundary convention (CLOSED straddle band, §4.2 + OBF extra-look penalty):
      - PASS requires STRICT p < p_reject_threshold (= 0.0378) for BOTH p's.
      - KILL requires STRICT p > p_kill_threshold (= 0.0422) for the triggering p.
      - p in [p_reject_threshold, p_kill_threshold] → RULE 4 AMBIGUOUS (closed band).
      - Exact boundary values 0.0378 and 0.0422 → RULE 4 (not PASS, not KILL).
      OBF extra-look penalty ratified 2026-06-07 (look-1 = voided run; former void-run
      values were 0.0478 / 0.0522; those are superseded and must not appear as active thresholds).

    Parameters
    ----------
    p_post2015:
        Post-2015 sub-window block-bootstrap p-value (n=345 Scenario A).
    p_agg:
        Full-window block-bootstrap p-value (n=506 Scenario A).
    dsr:
        DSR value from compute_dsr_qrb6().
    technical_failure:
        True if any data-integrity, provenance, or cross-trial-constant fault
        was detected.  RULE 0 fires unconditionally.
    p_kill_threshold:
        Strict KILL threshold (from receipt; expected 0.0422 = OBF look-2 boundary + MC-SE;
        former void-run value was 0.0522).
    p_reject_threshold:
        Strict clean-reject threshold (from receipt; expected 0.0378 = 0.05 − look-1-spend − MC-SE;
        former void-run value was 0.0478).
    dsr_threshold:
        DSR gate (from receipt; expected 0.95).

    Returns
    -------
    str
        One of: RULE_0_TECHNICAL_FAILURE, RULE_1_KILL_POST2015,
        RULE_2_KILL_AGGREGATE, RULE_3_PASS, RULE_4_AMBIGUOUS.
    """
    # RULE 0 — TECHNICAL FAILURE (§4.2; fires unconditionally; all other rules skipped)
    if technical_failure:
        return RULE_0_TECHNICAL_FAILURE

    # RULE 1 — KILL: post-2015 sub-window fails (overrides aggregate; §4.2, §5.2)
    # Fires iff p_post2015 > 0.0422 (strict; above straddle band; OBF extra-look penalty applied)
    if p_post2015 > p_kill_threshold:
        return RULE_1_KILL_POST2015

    # RULE 2 — KILL: aggregate fails (only reached if RULE 1 did not fire)
    # Fires iff p_agg > 0.0422 (strict; above straddle band; OBF extra-look penalty applied)
    if p_agg > p_kill_threshold:
        return RULE_2_KILL_AGGREGATE

    # At this point: both p's are <= 0.0422 (within or below the straddle band).

    # RULE 3 — PASS (§4.2): BOTH p's strictly < 0.0378 AND DSR >= 0.95 (OBF extra-look penalty applied)
    if p_post2015 < p_reject_threshold and p_agg < p_reject_threshold and dsr >= dsr_threshold:
        return RULE_3_PASS

    # RULE 4 — AMBIGUOUS / gate-fail (catch-all; §4.2)
    # Covers: any p in [0.0378, 0.0422] (straddle band, closed endpoints; OBF extra-look penalty),
    # OR both p's clean-reject but DSR < 0.95.
    return RULE_4_AMBIGUOUS


# ---------------------------------------------------------------------------
# Spread z-score computation (§5.5 QRB-2 overlay)
# ---------------------------------------------------------------------------


def compute_spread_z(
    spread_pips: float,
    trailing_median: float,
    trailing_mad: float,
) -> float:
    """Compute the QRB-2 spread z-score for a pair on an entry bar (§5.5).

    spread_z = (spread_pips - trailing_median_60) / trailing_MAD_60

    Parameters
    ----------
    spread_pips:
        Bid-ask spread in pips on the entry bar (D+1).
    trailing_median:
        Trailing 60-bar median of spread_pips (strictly causal; through bar t-1).
    trailing_mad:
        Trailing 60-bar MAD of spread_pips (strictly causal; through bar t-1).

    Returns
    -------
    float
        spread_z.  Returns 0.0 if trailing_mad == 0 (degenerate; no suppression).
    """
    if trailing_mad == 0.0:
        return 0.0
    return (spread_pips - trailing_median) / trailing_mad


def is_spread_suppressed(spread_z: float, spread_z_threshold: float) -> bool:
    """Return True if this pair-event should be suppressed (§5.5).

    Suppression fires if spread_z > spread_z_threshold (strict; §5.5).
    The frozen threshold is 3.0; caller passes it from the receipt.

    Parameters
    ----------
    spread_z:
        Computed spread z-score.
    spread_z_threshold:
        From receipt (expected: 3.0).

    Returns
    -------
    bool
    """
    return spread_z > spread_z_threshold
