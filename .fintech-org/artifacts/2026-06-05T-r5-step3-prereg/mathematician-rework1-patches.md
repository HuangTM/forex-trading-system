# R5 STEP-3 Pre-Reg — Mathematician REWORK CYCLE 1 — Exact-Replacement Patches

**Role:** Quantitative Mathematician
**Target file:** `references/pre-registrations/r5_carry_universe_kill_test.md` (PART II — Mathematician sections)
**Subtask:** r5-step3-prereg-2026-06-05:phase1:task1.0 / trial 576746aa
**Findings closed:** F-001, F-002, F-004, F-005, A-2, A-5
**Convention:** Each PATCH block has an ANCHOR (exact text in the current doc, to be replaced) and a REPLACEMENT (new text). Apply in order. No code is written or run; all source claims are verified against `dsr.py` and `reality_check.py` at the lines cited.

---

## PATCH 1 — F-001 election (§7.3.3 rewrite) + §1.3 permitted-change-set expansion

**ELECTION: Option (b) — SPEC CHANGE, NO CODE CHANGE to `compute_dsr`.** The DSR gate is computed at STEP 4 directly from the fully-specified frozen formula in the STEP-4 runner; `compute_dsr` is pinned only as the CONVENTIONS reference (units, kurtosis term, degenerate paths), not as the execution path. Rationale for (b) over (a): see the YAML `alternative-methods`. In one line: option (b) needs ZERO edit to the audited `dsr.py` (its frozen `expected_max_sr` internal-benchmark behavior is left bit-for-bit untouched and still serves every other caller), whereas option (a) would re-open and re-review a file the firm already corrected on 2026-05-31. The STEP-4 runner is new pre-freeze code regardless — STEP 4 needs an invocation script — so it is pinned by the freeze commit, and the marginal new surface of (b) is therefore zero. The empirical-dispersion `SR0` is genuinely uninjectable into the current `compute_dsr` signature (verified: `compute_dsr(sharpe_ratio, n_observations, skewness, excess_kurtosis, n_trials, periods_per_year)` at `dsr.py:107-114` has no benchmark parameter and computes `expected_max_sr(n_trials, n_observations)` internally at `dsr.py:198`, whose null-theoretical dispersion `1/sqrt(T-1)` cannot reproduce the frozen empirical-dispersion `SR0` for any integer `n_trials` — `expected_max_sr(2,4186)=0.008034` per-obs vs the frozen target `0.013961` per-obs; closest integer `n_trials=3 → 0.013183`), so "pass the scalar through `compute_dsr`" was never mechanically possible. Option (b) removes that impossibility by moving the arithmetic into the runner.

### PATCH 1a — §1.3 permitted-pre-freeze-change set (must state the runner explicitly)

**ANCHOR:**
```
Once this document is ratified and the freeze-receipt (SHA-256 of this file + git commit hash of the pinned code state: `carry_universe_matrix.py` and `reality_check.py` after the permitted N1 fix) is committed, the specification is immutable. **Any post-freeze change to the universe, window, statistic, K, threshold, or code — other than the N1 hardening fix, which must land BEFORE freeze — VOIDS this pre-registration** and forces a re-freeze (and, if a draw has already run, retirement of the contaminated result). STEP 4 is a one-shot run: the test is computed once against the frozen spec; there is no "re-run with a tweak" path that preserves the pre-registration.
```

**REPLACEMENT:**
```
Once this document is ratified and the freeze-receipt (SHA-256 of this file + git commit hash of the pinned code state: `carry_universe_matrix.py`, `reality_check.py` after the permitted N1 fix, and the STEP-4 DSR-gate runner described below) is committed, the specification is immutable. **Any post-freeze change to the universe, window, statistic, K, threshold, or code — other than the two permitted pre-freeze changes enumerated below, which must land BEFORE freeze — VOIDS this pre-registration** and forces a re-freeze (and, if a draw has already run, retirement of the contaminated result). STEP 4 is a one-shot run: the test is computed once against the frozen spec; there is no "re-run with a tweak" path that preserves the pre-registration.

> **PERMITTED PRE-FREEZE CHANGES (exhaustive — both land BEFORE the freeze-receipt; both are pinned by it):**
> 1. **The N1 hardening fix** to `reality_check.py` (the floor/guard hardening already adjudicated).
> 2. **The STEP-4 DSR-gate runner** — a new, single-purpose invocation script that (a) calls `r5c_hansen_spa` to obtain `p_SPA`, `p_RC`, and the winning cell `k*`; (b) computes the §7.3.4 DSR statistic for cell `k*` **directly from the frozen formula** `Φ((SR_pp − SR0_pp)·sqrt(T−1)/sqrt(var_term))`, using the §7.3.4 conventions, with the **frozen** `SR0_pp = 0.013961` (per-obs) injected as a literal; and (c) evaluates the §7.3.6 decision functional. This runner does **not** modify `dsr.py`, `reality_check.py`, or `carry_universe_matrix.py`. The canonical `dsr.py:compute_dsr` is unchanged and is pinned only as the CONVENTIONS reference (§7.3.3, §7.3.4) — its internal `expected_max_sr` benchmark is NOT the frozen execution path. No other code change is permitted; any post-freeze edit to any of these four code objects voids the pre-reg.
```

### PATCH 1b — §7.3.3 body rewrite (the false "parameter pin, not a code change" claim)

**ANCHOR:**
```
**Units reconciliation (must hold at run time).** The canonical `compute_dsr` operates in
**per-observation** units: it converts the input annualized Sharpe via `SR_pp = SR_ann / sqrt(252)`
and computes its own per-obs expected-max benchmark `expected_max_sr(N, T) = bracket / sqrt(T−1)`.
The §7.2 Var-plug-in `SR0` above is the *annualized* analogue of that benchmark, with the empirical
cross-trial dispersion `sqrt(Var[SR_n])` substituted for the null-theoretical per-obs dispersion
`1/sqrt(T−1)`. The two renderings are the same BLP quantity under two dispersion estimators; on this
matrix (`T = 4186`) they agree in order of magnitude and the elected (sample) rendering is the more
conservative (`SR0_ann = 0.2216` vs the code's null-dispersion `bracket/sqrt(T−1)·sqrt(252) = 0.1275`).
**Frozen run-time rule:** the gate is evaluated with `compute_dsr` (canonical code) but the deflation
benchmark used inside it is overridden to the **frozen `SR0 = 0.221616` annualized
(`= 0.013961` per-obs after `÷sqrt(252)`)**, NOT the code's default `expected_max_sr`. This is a
parameter pin, not a code change: `expected_max_sr`/`compute_dsr` are unchanged; the frozen `SR0`
scalar is passed as the benchmark. If the harness cannot accept an externally-pinned `SR0`, that is a
TECHNICAL FAILURE (§5 outcome 5), not a license to substitute the code default.
```

**REPLACEMENT:**
```
**Units reconciliation (must hold at run time).** The canonical `compute_dsr` (`dsr.py:107-207`)
operates in **per-observation** units: it converts the input annualized Sharpe via
`SR_pp = SR_ann / sqrt(252)` (`dsr.py:180`) and computes its own per-obs expected-max benchmark
`expected_max_sr(n_trials, T) = bracket / sqrt(T−1)` *internally* (`dsr.py:198`, `expected_max_sr` at
`dsr.py:46-104`). The §7.2 Var-plug-in `SR0` above is the *annualized* analogue of that benchmark,
with the empirical cross-trial dispersion `sqrt(Var[SR_n]) = 0.426385` substituted for the
null-theoretical per-obs dispersion `1/sqrt(T−1)`. The two renderings are the same BLP quantity under
two dispersion estimators; on this matrix (`T = 4186`) the elected (sample) rendering is the more
conservative (`SR0_ann = 0.221616` → per-obs `0.013961`, vs the code's internal null-dispersion
benchmark `expected_max_sr(2, 4186) = 0.008034` per-obs).

**Why the frozen `SR0` is NOT injectable into `compute_dsr` — and the execution mechanism that
resolves it (election: SPEC CHANGE, no code change).** `compute_dsr(sharpe_ratio, n_observations,
skewness, excess_kurtosis, n_trials, periods_per_year)` (`dsr.py:107-114`) has **no benchmark
parameter**. It computes its deflation benchmark *internally* from `expected_max_sr(n_trials, T)`
(`dsr.py:198`), whose dispersion is the null-theoretical `1/sqrt(T−1)` (`dsr.py:103`), NOT the
empirical cross-trial `sqrt(Var[SR_n])`. There is **no integer `n_trials`** for which
`expected_max_sr(n_trials, 4186)` equals the frozen per-obs target `0.013961`:
`expected_max_sr(2, 4186) = 0.008034`, and the nearest integer `n_trials = 3` gives `0.013183` —
neither reproduces `0.013961`. The earlier "pass the frozen `SR0` as the benchmark — a parameter pin,
not a code change" claim was therefore **factually wrong**: the signature admits no such argument, so
the only ways to use `compute_dsr` as the execution path would be to **edit `dsr.py` post-freeze
(forbidden)** or to mis-set `n_trials` to a value that does not reproduce the frozen benchmark (which
silently changes the test). Accordingly:

> **FROZEN EXECUTION MECHANISM (spec change, no code change to `dsr.py`).** The DSR gate is computed
> at STEP 4 by the dedicated **STEP-4 DSR-gate runner** (§1.3 permitted-change item 2), **directly
> from the frozen formula**
> `DSR = Φ( (SR_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )` with the §7.3.4 conventions and the
> **frozen literal** `SR0_pp = 0.013961` (per-obs; `= 0.221616 / sqrt(252)`). `compute_dsr` is the
> **CONVENTIONS reference only** — it pins (i) the per-obs unit convention `SR_pp = SR_ann/sqrt(252)`
> (`dsr.py:180`), (ii) the corrected variance-of-Sharpe kurtosis term `(γ4_excess + 2)/4`
> (`dsr.py:184`), (iii) the two degenerate early-return paths (§7.3.4: `var_term ≤ 0 → 0.0` at
> `dsr.py:187-195`, and `sharpe_ratio ≤ 0 → 0.0` at `dsr.py:168-169`), and (iv) the final
> `Φ(z)` clip to `[0,1]` (`dsr.py:205-207`). `compute_dsr` is **NOT** the execution path: its internal
> `expected_max_sr` benchmark is bypassed entirely because the frozen `SR0_pp` is supplied directly.
> The runner MUST reproduce these four conventions exactly; any divergence between the runner's
> arithmetic and the `compute_dsr` conventions it references is a TECHNICAL FAILURE (§5 outcome 5),
> not a license to fall back to the code's internal benchmark. `dsr.py`, `reality_check.py`, and
> `carry_universe_matrix.py` are bit-for-bit unchanged for this gate; the runner is the only new code
> and is pinned by the freeze-receipt commit.
```

---

## PATCH 2 — F-002 (§7.3.6 mutually-exclusive, exhaustive branches + boundary ruling)

**ANCHOR:**
```
> **CONTINUE** (→ §5 outcome 1: confirmatory-only pre-reg, never trade/re-open) **iff BOTH**
> **(i) `p_SPA < 0.05`** (SPA-consistent significant) **AND (ii) `DSR ≥ 0.95`** (deflation gate
> cleared) **AND (iii) White-RC concordant (`p_RC < 0.05`)**.
>
> **AMBIGUOUS** (→ §5 outcome 4: confirmatory-pre-reg gate ONLY; NEVER CONTINUE on the family) **iff**
> the SPA p clears but a higher-order check does not — explicitly, **`p_SPA < 0.05` AND
> (`DSR < 0.95` OR `p_RC ≥ 0.05`)**, OR the family p straddles `0.05` within one MC-SE
> (`|p_SPA − 0.05| ≤ MC-SE = 0.0031`, §4), OR only an isolated subset / a normalization-driven
> distortion (N2 carry_momentum near-null artifact) produces the apparent rejection.
>
> **WIND-DOWN** (→ §5 outcomes 2 & 3, binding regardless of power) **iff `p_SPA ≥ 0.05`** (outside the
> MC-SE straddle band).
>
> **TECHNICAL FAILURE** (→ §5 outcome 5: HALT, root-cause, re-freeze, re-run; no p-value read) iff a
> code error, data-integrity fault, unlogged cell drop (`K ≠ 36` with a null/empty reason), or a
> freeze-receipt mismatch is detected — including the harness being unable to accept the pinned `SR0`
> (§7.3.3).
```

**REPLACEMENT:**
```
The functional is defined as an **ordered, mutually-exclusive, exhaustive** evaluation: the FIRST
matching rule fires and STOPS evaluation. The order is chosen so that no boundary case can buy
CONTINUE — every tie resolves toward the more conservative (non-CONTINUE) branch. Inputs are
`p_SPA`, `p_RC`, `DSR` (cell `k*`), and the run-integrity flags. Evaluate top to bottom:

> **RULE 0 — TECHNICAL FAILURE** (→ §5 outcome 5: HALT, root-cause, re-freeze, re-run; NO p-value is
> read). Fires iff a code error, data-integrity fault, unlogged cell drop (`K ≠ 36` with a null/empty
> reason), freeze-receipt mismatch, or any divergence of the STEP-4 runner from the §7.3.4 `compute_dsr`
> conventions (§7.3.3) is detected. If RULE 0 fires, RULES 1–4 are NOT evaluated.
>
> **RULE 1 — AMBIGUOUS (straddle)** (→ §5 outcome 4). Fires iff RULE 0 did not, AND the family p
> straddles the threshold within one MC-SE: **`|p_SPA − 0.05| ≤ MC-SE = 0.0031`** (§4). This rule is
> evaluated **before** any CONTINUE/WIND-DOWN test, so a result whose `p_SPA` sits in
> `[0.0469, 0.0531]` is AMBIGUOUS **regardless of `DSR` or `p_RC`** — a boundary p is not
> distinguishable from noise and must NOT buy CONTINUE and must NOT be read as a clean WIND-DOWN.
>
> **RULE 2 — WIND-DOWN** (→ §5 outcomes 2 & 3, binding regardless of power). Fires iff RULES 0–1 did
> not, AND **`p_SPA ≥ 0.05`** (i.e. `p_SPA ≥ 0.05` and outside the straddle band, so
> `p_SPA > 0.0531`). The carry family is statistically indistinguishable from chance at the class
> level.
>
> **RULE 3 — CONTINUE** (→ §5 outcome 1: confirmatory-only pre-reg, never trade/re-open). Fires iff
> RULES 0–2 did not (so `p_SPA < 0.05` AND outside the straddle band, i.e. `p_SPA < 0.0469`), AND
> **BOTH (ii) `DSR ≥ 0.95`** (deflation gate cleared) **AND (iii) `p_RC < 0.05`** (White-RC
> concordant). CONTINUE is NECESSARY-BUT-NOT-SUFFICIENT and only authorizes a confirmatory-only
> pre-reg.
>
> **RULE 4 — AMBIGUOUS (gate-fail / anomalous)** (→ §5 outcome 4; the catch-all, guaranteeing
> exhaustiveness). Fires iff RULES 0–3 did not — i.e. `p_SPA < 0.0469` (a genuine, non-straddle SPA
> rejection) BUT **(`DSR < 0.95` OR `p_RC ≥ 0.05`)**, OR only an isolated subset / a
> normalization-driven distortion (N2 carry_momentum near-null artifact) produced the apparent
> rejection. A bare SPA rejection that cannot clear the selection-deflation charge or is not
> White-RC-concordant maps here, NEVER to CONTINUE.

**Exhaustiveness and mutual-exclusivity (proof).** The rules partition the joint outcome space on
the disjoint, ordered conditions {technical-fail} → {straddle} → {`p_SPA ≥ 0.05` ∧ ¬straddle} →
{`p_SPA < 0.05` ∧ ¬straddle ∧ all-gates} → {else}. Because evaluation stops at the first match, the
bands are disjoint by construction; because RULE 4 is the unconditional else, every non-technical-fail
outcome lands in exactly one of RULES 1–4. The previously-overlapping instance — `p_SPA = 0.048`,
`DSR = 0.96`, `p_RC = 0.01` — now resolves **unambiguously to RULE 1 (AMBIGUOUS, straddle)**, because
`|0.048 − 0.05| = 0.002 ≤ 0.0031` is tested before the CONTINUE rule; the prior text let this same
instance match both CONTINUE and AMBIGUOUS.

> **Boundary-case ruling (binding, restated for emphasis):** when a result lands on or within the
> MC-SE straddle band of `0.05`, **AMBIGUOUS wins** (RULE 1), never CONTINUE. The document's posture
> (§1.2, §4) is that a boundary result must NOT buy CONTINUE: a p indistinguishable from 0.05 at the
> frozen `K = 5000` resolution is, by the firm's own error budget, not a clean class-level rejection.
> The straddle check is therefore positioned ahead of both the WIND-DOWN and CONTINUE tests so that
> the tie can resolve to neither a false CONTINUE nor a falsely-clean WIND-DOWN.
```

---

## PATCH 3 — F-004 (§7.3.4 — pin the second `compute_dsr` early-return: `sharpe_ratio ≤ 0 → 0.0`)

**ANCHOR:**
```
`T = 4186`
(the frozen common-index length). `Φ` is the standard-normal CDF. If `var_term ≤ 0`, `compute_dsr`
returns `0.0` (cannot certify) and the gate FAILS — this is the documented degenerate path
(`dsr.py:187-195`), not a TECHNICAL FAILURE.
```

**REPLACEMENT:**
```
`T = 4186`
(the frozen common-index length). `Φ` is the standard-normal CDF. **Two degenerate paths are pinned,
both reference-matched to `compute_dsr` and both resolving to `DSR = 0.0` so the gate FAILS (neither
is a TECHNICAL FAILURE):**
1. **`var_term ≤ 0 → DSR = 0.0`** (cannot certify the variance of the Sharpe estimator;
   `dsr.py:187-195`). The STEP-4 runner reproduces this guard before taking `sqrt(var_term)`.
2. **`SR_hat ≤ 0 → DSR = 0.0`** (a non-positive winning Sharpe cannot exceed the positive deflated
   benchmark; `dsr.py:168-169`, the early return `if sharpe_ratio <= 0.0: return 0.0`). This is a
   **defensive pin, not an expected path**: under the §7.3.6 ordering the DSR gate is only consulted
   when `p_SPA < 0.0469` (a genuine SPA rejection), and a genuine rejection against a zero benchmark
   with a non-positive best-cell Sharpe is essentially impossible — the studentized family max `T_SPA`
   is driven by the cell with the largest positive t-ratio, so its annualized Sharpe is positive
   whenever the SPA null is rejected. The pin exists so that, in the pathological event of a
   sign/units mishandling upstream, the gate fails closed (`DSR = 0.0 → not CONTINUE`) rather than
   silently certifying.
```

---

## PATCH 4 — F-005 (§2.3 — fix BOTH 1e-12 floor citations to their true lines and quantities)

### PATCH 4a — §2.3 item 1 citation (`:868` is the omega floor, not the s2 clamp)

**ANCHOR:**
```
1. **HAC-SE floor (`reality_check.py:868`):** after computing all `omega_hat_k`, any
   `omega_hat_k < 1e-12` is set to `1e-12` before the division `T_k = sqrt(n)·mean_hat/omega_hat_k`.
```

**REPLACEMENT:**
```
1. **HAC-SE (omega) floor (`reality_check.py:868`):** after computing all `omega_hat_k`, the guard
   `omegas = np.where(omegas < 1e-12, 1e-12, omegas)` (`reality_check.py:868`) sets any
   `omega_hat_k < 1e-12` to `1e-12` before the division `T_k = sqrt(n)·mean_hat/omega_hat_k`. This is
   the *omega* floor — distinct from the *internal* long-run-variance clamp `s2 = max(s2, 1e-12)` at
   `reality_check.py:863` (inside `_hac_se`), which guards a single column's `s2` against a negative
   small-sample value before `omega_hat_k = sqrt(s2/n)` is returned. Both floors are `1e-12`; they
   act at different points (the `:863` clamp on each `s2`; the `:868` floor on the vector of returned
   `omega_hat_k`).
```

### PATCH 4b — §2.3 caveat-discharge text (the ":867" mis-citation)

**ANCHOR:**
```
> finite-precision arithmetic could break that invariance is if the absolute HAC-SE floor `1e-12`
> (`reality_check.py:867`) clipped a genuine `omega_hat_k`, which would spuriously null the affected
```

**REPLACEMENT:**
```
> finite-precision arithmetic could break that invariance is if the absolute HAC-SE (omega) floor
> `1e-12` (`reality_check.py:868`, `np.where(omegas < 1e-12, 1e-12, omegas)`; the related internal
> `s2 = max(s2, 1e-12)` clamp sits at `reality_check.py:863`) clipped a genuine `omega_hat_k`, which
> would spuriously null the affected
```

---

## PATCH 5 — A-2 (§7.3.1 framing correction: conservatism restricted to the Var axis; N-axis anti-conservatism disclosed; frozen SR0 table for N ∈ {2,3,4})

**ANCHOR:**
```
- **Sharpe table `{SR_1 = 0.80, SR_2 = 0.197}` — ACCEPTED, with the provenance caution explicitly
  weighed and neutralized by monotonicity.** `SR_1 = 0.80` is registry-unverified (pre-reg-documented
  at `carry_fred.md:16`, `fred_carry_stripped.md:18,66`, with no `trials.jsonl` row) and its "Bet #1 =
  carry_fred" label repeats the labeling that the 2026-06-02 adjudication flagged (Bet #1 / trial
  `87fa1d23` was a momentum portfolio, not carry_fred). The Mathematician records this as a genuine
  provenance weakness. **It does not block the freeze, because the DSR gate is conservative in the
  direction of the weakness:** `SR0` is strictly increasing in `Var[SR_n]`, which is strictly
  increasing in the spread `|SR_1 − SR_2|`. An *over*-stated `SR_1` therefore *raises* the haircut
  (makes CONTINUE harder), so it can only cause a false WIND-DOWN, never a false CONTINUE. Since the
  firm's pre-committed most-likely action is WIND-DOWN regardless (§5/§6), an input that is
  conservative-if-wrong is signable. The election below leans further into this conservatism.
```

**REPLACEMENT:**
```
- **Sharpe table `{SR_1 = 0.80, SR_2 = 0.197}` — ACCEPTED, with the provenance caution weighed; the
  conservatism claim is restricted to the Var/spread axis ONLY.** `SR_1 = 0.80` is registry-unverified
  (pre-reg-documented at `carry_fred.md:16`, `fred_carry_stripped.md:18,66`, with no `trials.jsonl`
  row) and its "Bet #1 = carry_fred" label repeats the labeling that the 2026-06-02 adjudication
  flagged (Bet #1 / trial `87fa1d23` was a momentum portfolio, not carry_fred). The Mathematician
  records this as a genuine provenance weakness.

  **The two axes of `SR0` run in OPPOSITE directions — this must be stated honestly:**
  - **Var/spread axis (conservative-if-wrong).** `SR0` is strictly increasing in `Var[SR_n]`, which
    is strictly increasing in the spread `|SR_1 − SR_2|`. An *over*-stated `SR_1` therefore *raises*
    the haircut (makes CONTINUE harder); on this axis the input error can only cause a false
    WIND-DOWN, never a false CONTINUE. This is the only axis on which the "conservative-if-wrong"
    defense holds.
  - **N axis (ANTI-conservative — disclosed, NOT defended).** `SR0` is strictly **increasing in `N`**
    (the bracket `(1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne))` grows with `N`, since both quantile arguments
    increase toward 1). At the elected sample dispersion `sqrt(Var) = 0.426385`, the verified scalars
    are `SR0(N=2) = 0.221616`, `SR0(N=3) = 0.363664`, `SR0(N=4) = 0.448688` (table below). Pinning `N`
    at the **floor** of the credible range (HoQR 1–2 / NHT 2–4) is therefore the **LEAST-deflating
    admissible choice** — it gives the *smallest* `SR0` and is **biased toward a false CONTINUE**, the
    opposite direction from the Var-axis conservatism. I do **not** describe the `N = 2` election as
    conservative. It is the smallest defensible `N` (top of HoQR's range, bottom of NHT's), and on the
    N axis a smaller `N` makes the gate *easier*, not harder. The N VALUE is HoQR's pin and is being
    re-adjudicated in parallel; whatever HoQR pins maps to a frozen scalar via the table below with no
    recompute.

  **Net.** The Var-axis conservatism and the N-axis anti-conservatism are not netted into a single
  "conservative" claim. The honest statement is: the gate is conservative against `SR_1`-provenance
  error and anti-conservative against under-estimation of `N`. The mitigation is that `N` is bounded
  above by NHT's own ceiling (4), so the worst-case under-deflation is bounded — `SR0` cannot fall
  below `0.221616` for any admissible `N ≥ 2`, and the table makes the gate-strength consequence of
  each candidate `N` explicit so the choice is not hidden.

  **Frozen SR0 table at the elected sample `sqrt(Var[SR_n]) = 0.426385` (§7.3.2), for the credible
  `N ∈ {2, 3, 4}`** (derivations in §7.3.3; quantiles to 6 decimals):

  | N | Z⁻¹(1−1/N) | Z⁻¹(1−1/(N·e)) | bracket = (1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e)) | **SR0 (annualized)** | per-obs SR0_pp (÷√252) | Best-cell annualized SR needed to clear DSR ≥ 0.95 |
  |---|---|---|---|---|---|---|
  | **2** (elected) | Z⁻¹(0.500000) = 0.000000 | Z⁻¹(0.816060) = 0.900452 | 0.519756 | **0.221616** | 0.013961 | ≈ **0.625** |
  | **3** | Z⁻¹(0.666667) = 0.430727 | Z⁻¹(0.877374) = 1.162095 | 0.852892 | **0.363664** | 0.022912 | ≈ **0.767** |
  | **4** | Z⁻¹(0.750000) = 0.674490 | Z⁻¹(0.908030) = 1.328869 | 1.052310 | **0.448688** | 0.028267 | ≈ **0.852** |

  (γ = 0.5772156649; e = 2.718281828; 1−γ = 0.4227843351. The "needed annualized SR" column is the
  smallest annualized best-cell Sharpe that yields `DSR ≥ 0.95`, i.e. `z ≥ Φ⁻¹(0.95) = 1.644854`,
  under `var_term ≈ 1` and `T = 4186` (`sqrt(T−1) = 64.691`): `SR_pp ≥ SR0_pp + 1.644854/64.691 =
  SR0_pp + 0.025427`, annualized `SR_ann ≥ SR0_ann + 0.025427·sqrt(252) = SR0_ann + 0.403642`. The
  `var_term ≈ 1` approximation holds to the displayed precision for the small per-obs Sharpes here;
  the runner uses the cell's actual skew/kurtosis at STEP 4.)
```

---

## PATCH 6 — A-2 (§7.3.3 — replace single-N derivation with the N ∈ {2,3,4} quantile derivations)

**ANCHOR:**
```
With the elected inputs (`N = 2`, sample `sqrt(Var[SR_n]) = 0.426385`, `γ = 0.5772156649`,
`e = 2.718281828`):
- `Z⁻¹(1 − 1/N) = Z⁻¹(0.5) = 0` (zeroes the `(1−γ)` leg — a property of `N = 2`).
- `Z⁻¹(1 − 1/(N·e)) = Z⁻¹(0.8160603) = 0.900452` (inverse standard-normal CDF; verified).
- bracket `= (1−γ)·0 + γ·0.900452 = 0.5772156649 · 0.900452 = 0.519756`.

> **FROZEN: `SR0 = 0.221616` (annualized Sharpe units).** *(Population-var alternative, recorded
> not elected: `SR0 = 0.156706`.)* `SR0` is in the same **annualized** units as `SR_1`, `SR_2`, and
> the firm's `calculate_metrics` Sharpe.
```

**REPLACEMENT:**
```
With the elected sample dispersion `sqrt(Var[SR_n]) = 0.426385`, `γ = 0.5772156649`,
`1−γ = 0.4227843351`, `e = 2.718281828`, the bracket and `SR0` are derived for each credible
`N ∈ {2, 3, 4}` (the elected pin is `N = 2`; `N = 3, 4` are frozen here so HoQR's parallel
re-adjudication maps to a scalar with no recompute). The two quantile arguments per `N` are
`a1 = 1 − 1/N` and `a2 = 1 − 1/(N·e)`.

**N = 2 (elected):**
- `a1 = 1 − 1/2 = 0.500000`; `Z⁻¹(0.500000) = 0.000000` (median; zeroes the `(1−γ)` leg).
- `a2 = 1 − 1/(2e) = 1 − 0.183940 = 0.816060`; `Z⁻¹(0.816060) = 0.900452`.
- bracket `= 0.4227843·0.000000 + 0.5772157·0.900452 = 0.519756`.
- `SR0 = 0.426385 · 0.519756 = 0.221616`.

**N = 3:**
- `a1 = 1 − 1/3 = 0.666667`; `Z⁻¹(0.666667) = 0.430727`. *(Derivation: standard-normal quantile;
  bracketed by the textbook table values Z⁻¹(0.66)=0.412463 and Z⁻¹(0.67)=0.439913, interpolating to
  p=0.666667 gives 0.43073; the 6-dp value 0.430727 is the converged probit. Independent anchor:
  Φ(0.430727) ≈ 0.66667.)*
- `a2 = 1 − 1/(3e) = 1 − 1/8.154845 = 1 − 0.122626 = 0.877374`; `Z⁻¹(0.877374) = 1.162095`.
  *(Derivation: bracketed by Z⁻¹(0.875)=1.150349 and Z⁻¹(0.88)=1.174987; the convex probit at
  p=0.877374 converges to 1.16210 (6-dp 1.162095). Anchor: Φ(1.162095) ≈ 0.87737.)*
- bracket `= 0.4227843·0.430727 + 0.5772157·1.162095 = 0.182103 + 0.670789 = 0.852892`.
- `SR0 = 0.426385 · 0.852892 = 0.363664`.

**N = 4:**
- `a1 = 1 − 1/4 = 0.750000`; `Z⁻¹(0.750000) = 0.674490` (the canonical upper-quartile probit).
- `a2 = 1 − 1/(4e) = 1 − 1/10.873127 = 1 − 0.091970 = 0.908030`; `Z⁻¹(0.908030) = 1.328869`.
  *(Derivation: bracketed by Z⁻¹(0.905)=1.310579 and Z⁻¹(0.91)=1.340755; the probit at p=0.908030
  converges to 1.32887 (6-dp 1.328869). Anchor: Φ(1.328869) ≈ 0.90803.)*
- bracket `= 0.4227843·0.674490 + 0.5772157·1.328869 = 0.285167 + 0.767143 = 1.052310`.
- `SR0 = 0.426385 · 1.052310 = 0.448688`.

> **FROZEN (elected, `N = 2`): `SR0 = 0.221616` (annualized Sharpe units), per-obs
> `SR0_pp = 0.221616 / sqrt(252) = 0.013961`.** *(Population-var alternative at `N = 2`, recorded not
> elected: `SR0 = 0.156706`.)* **Frozen contingency scalars (whichever `N` HoQR pins): `SR0(N=3) =
> 0.363664`, `SR0(N=4) = 0.448688`** at the elected sample dispersion — see the §7.3.1 table for the
> per-obs values and the best-cell annualized Sharpe each `N` requires to clear `DSR ≥ 0.95`. `SR0` is
> in the same **annualized** units as `SR_1`, `SR_2`, and the firm's `calculate_metrics` Sharpe.
>
> The 6-dp normal-quantile values above are standard-normal probits; the `N = 2` value
> `Z⁻¹(0.816060) = 0.900452` is the value already carried in the prior draft. The `N = 3` and `N = 4`
> quantiles are derived by bracketing between textbook z-table anchors and converging the probit (work
> shown inline); they are reproduced by `scipy.stats.norm.ppf` at run time (the runner's required
> scipy path, §7.3.4 / A-5 pin) and are the frozen reference values.
```

---

## PATCH 7 — A-5 (skew/kurtosis bias-flag convention + scipy-required pin)

**ANCHOR:**
```
Its skewness and excess kurtosis are that cell's
own (`γ3 = skew(f_{k*})`, `γ4 − 1 = excess_kurtosis(f_{k*})` in Fisher convention, i.e.
`kurtosis − 3`), computed on cell `k*`'s realized per-bar net-of-cost return series over the frozen
common index. **It is NOT computed on a pooled series and NOT on any other cell.**
```

**REPLACEMENT:**
```
Its skewness and excess kurtosis are that cell's
own (`γ3 = skew(f_{k*})`, `γ4_excess = excess_kurtosis(f_{k*})` in Fisher convention, i.e.
`kurtosis − 3`), computed on cell `k*`'s realized per-bar net-of-cost return series over the frozen
common index. **It is NOT computed on a pooled series and NOT on any other cell.**

> **Estimator-convention pins (frozen, A-5):**
> - **Sample-bias flag:** `γ3` and `γ4_excess` are computed with `scipy.stats.skew(...,
>   bias=True)` and `scipy.stats.kurtosis(..., fisher=True, bias=True)` — the **biased** (uncorrected,
>   maximum-likelihood) sample estimators, `bias=True` (scipy's default). With `T = 4186` the
>   bias correction is `O(1/T)` and changes `γ3, γ4` in the fourth+ decimal — immaterial to the gate —
>   but the convention is pinned so the STEP-4 runner is deterministic and not subject to a silent
>   `bias=False` substitution.
> - **scipy is REQUIRED at run time.** The STEP-4 runner MUST execute under an environment where
>   `scipy.stats` (`norm.ppf`, `norm.cdf`, `skew`, `kurtosis`) is importable. The `dsr.py` ImportError
>   fallbacks — the Beasley-Springer-Moro probit approximation (`dsr.py:72-90`) and the `math.erf`
>   CDF approximation (`dsr.py:176-177`) — are **NOT** the frozen path; if scipy is absent at run time
>   that is a TECHNICAL FAILURE (§5 outcome 5), not a license to certify on the approximation. The
>   frozen quantiles in §7.3.3 are the exact `scipy.stats.norm.ppf` values.
```
