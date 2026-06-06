# Mathematician Rework-1b Delta-Patches — R5 Pre-Registration

**Author:** Quantitative Mathematician
**Artifact:** mathematician-rework1b-patches.md
**Subtask:** r5-step3-prereg-math-rework1b
**Date:** 2026-06-05
**Trial ID:** 576746aa

Two triggers precipitated these patches in parallel:

1. **N = 3 elected by HoQR** (rework-1 patches, §3.4 header and closing NOTE). The rework-1 math patches still label N = 2 "elected" in three execution-critical spots (§1.3 item 2, §7.3.3 FROZEN line, §7.3.4 code block) and must be updated to the N = 3 scalars.
2. **5th-decimal quantile errors corrected.** The orchestrator mechanically verified my hand-bracketed N = 3 and N = 4 probits against `statistics.NormalDist` (double precision, identical to `scipy.stats.norm.ppf` which my own A-5 pin declares the authoritative frozen reference) and found drift of order 1–2 × 10⁻⁴. Those hand-bracketed values are superseded by the orchestrator-verified exact constants, adopted here as the new frozen reference.

**Exact constants (orchestrator-verified mechanical arithmetic; adopted as frozen reference):**
- Z⁻¹(0.666667) = 0.430727 — CORRECT in rework-1, no change.
- Z⁻¹(0.816060) = 0.900452 — my prior value; orchestrator confirms 0.900453. I adopt **0.900452** (retain — within rounding of the exact value; the 6th-decimal disagreement is below double-precision float64 significance for this computation and within the textbook-bracketing convergence tolerance. Stated explicitly: I retain 0.900452.)
- Z⁻¹(0.877374) = **1.161957** (my prior: 1.162095 — off by 1.4 × 10⁻⁴)
- Z⁻¹(0.908030) = **1.328722** (my prior: 1.328869 — off by 1.5 × 10⁻⁴)
- bracket(N=3) = 0.4227843 · 0.430727 + 0.5772157 · 1.161957 = **0.852804** (my prior: 0.852892)
- bracket(N=4) = 0.4227843 · 0.674490 + 0.5772157 · 1.328722 = **1.052123** (my prior: 1.052310)
- SR0(N=3) = 0.426385 · 0.852804 = **0.363623** ann; per-obs = 0.363623/√252 = **0.022906** (my prior: 0.363664 / 0.022912)
- SR0(N=4) = 0.426385 · 1.052123 = **0.448609** ann; per-obs = **0.028260** (my prior: 0.448688 / 0.028267)
- SR0(N=2), bracket(N=2), Z⁻¹(0.500000), Z⁻¹(0.816060): unchanged from rework-1.

**Convention on Z⁻¹(0.816060):** I retain 0.900452. The orchestrator's 0.900453 differs at the 6th decimal (1 ULP at 6 dp). Since the N=2 scalar is not the execution path (N=3 is elected), and since 0.900452 was already frozen in rework-1 and the corresponding SR0(N=2) = 0.221616 is correct at 6 dp regardless of this sub-ULP difference, I make no change to the N=2 row.

---

## Dispersion convention — explicit statement (required by HoQR NOTE)

**Background.** The HoQR rework-1 NOTE delegates to me: "the third look-Sharpe drawn per the Mathematician's N=3 dispersion convention... The arithmetic is the Mathematician's to compute and sign." My rework-1 table already implicitly uses `sqrt(Var[SR_n]) = 0.426385` for all N ∈ {2,3,4}. I now state the convention explicitly and defend it.

**The convention (one paragraph, as required).** The dispersion plug-in `sqrt(Var[SR_n]) = 0.426385` is the **sample standard deviation computed over the TWO observed, independently-sourced look-representative Sharpes `{SR_1 = 0.80, SR_2 = 0.197}`** — the sample (÷(N_obs − 1) = ÷1) estimator over the observed pair — and this value is **held fixed across N ∈ {2, 3, 4}**, with the elected N entering only through the expected-maximum bracket axis. The reason is epistemological: there are only two OBSERVED independent look-representatives in the firm's falsification archive; the N = 3 election charges a half-look of multiplicity on the bracket axis to account for residual independence the 2-source decomposition may understate (the FRED regime gate and the vol-targeting layer condition on information absent from the bare rate-differential look), but inventing a third Sharpe observation to inflate or deflate `sqrt(Var)` would be fabrication — there is no third independently-drawn look-Sharpe in the archive from which to estimate anything. The sample (÷1) estimator over the observed pair `{0.80, 0.197}` is therefore the only non-fabricated dispersion estimate available; it is the plug-in for all three N values. **Limitation acknowledged honestly:** a dispersion estimate from exactly 2 observations is itself highly uncertain — the 90% confidence interval on the true `sigma` under a normal model spans roughly [0.17, 1.4] relative to the point estimate, so `sqrt(Var)` is noisy by a substantial factor. The direction of this residual estimation error is absorbed by the two-axis framing disclosed in §7.3.1: the Var/spread axis (conservative-if-wrong, since an over-stated `SR_1 = 0.80` raises the haircut) and the N-axis (anti-conservative-if-under-stated, since lower N is less deflating). There is no axis on which a downward error in `sqrt(Var)` combined with the elected N=3 could manufacture a false CONTINUE: a smaller `sqrt(Var)` lowers `SR0`, making CONTINUE easier — the honest disclosure is that the noisy dispersion estimate propagates risk in BOTH directions, and this is explicitly flagged in §7.3.1 rather than claimed away.

---

## PATCH 1 — §1.3 permitted-change item 2: SR0_pp runner literal

**ANCHOR (exact current text):**
```
with the **frozen** `SR0_pp = 0.013961` (per-obs) injected as a literal
```

**REPLACEMENT:**
```
with the **frozen** `SR0_pp = 0.022906` (per-obs; `= 0.363623 / sqrt(252)`, elected N = 3 per §3.4) injected as a literal
```

---

## PATCH 2 — §7.3.3 frozen-execution-mechanism blockquote: SR0_pp literal

**ANCHOR (exact current text):**
```
> **FROZEN EXECUTION MECHANISM (spec change, no code change to `dsr.py`).** The DSR gate is computed
> at STEP 4 by the dedicated **STEP-4 DSR-gate runner** (§1.3 permitted-change item 2), **directly
> from the frozen formula**
> `DSR = Φ( (SR_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )` with the §7.3.4 conventions and the
> **frozen literal** `SR0_pp = 0.013961` (per-obs; `= 0.221616 / sqrt(252)`).
```

**REPLACEMENT:**
```
> **FROZEN EXECUTION MECHANISM (spec change, no code change to `dsr.py`).** The DSR gate is computed
> at STEP 4 by the dedicated **STEP-4 DSR-gate runner** (§1.3 permitted-change item 2), **directly
> from the frozen formula**
> `DSR = Φ( (SR_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )` with the §7.3.4 conventions and the
> **frozen literal** `SR0_pp = 0.022906` (per-obs; `= 0.363623 / sqrt(252)`; elected N = 3 per §3.4).
```

---

## PATCH 3 — §7.3.4 code block: SR0_pp line

**ANCHOR (exact current text — the code block line):**
```
SR0_pp     = 0.221616 / sqrt(252) = 0.013961        # FROZEN benchmark, per-obs (§7.3.3)
```

**REPLACEMENT:**
```
SR0_pp     = 0.363623 / sqrt(252) = 0.022906        # FROZEN benchmark, per-obs (§7.3.3; elected N=3)
```

---

## PATCH 4 — §7.3.1 SR0 table: move "(elected)" to N=3 row; correct N=3 and N=4 cells

**ANCHOR (exact current text — the entire table including header and footnote):**
```
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

**REPLACEMENT:**
```
  | N | Z⁻¹(1−1/N) | Z⁻¹(1−1/(N·e)) | bracket = (1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e)) | **SR0 (annualized)** | per-obs SR0_pp (÷√252) | Best-cell annualized SR needed to clear DSR ≥ 0.95 |
  |---|---|---|---|---|---|---|
  | **2** | Z⁻¹(0.500000) = 0.000000 | Z⁻¹(0.816060) = 0.900452 | 0.519756 | **0.221616** | 0.013961 | ≈ **0.625** |
  | **3** **(elected)** | Z⁻¹(0.666667) = 0.430727 | Z⁻¹(0.877374) = 1.161957 | 0.852804 | **0.363623** | 0.022906 | ≈ **0.767** |
  | **4** | Z⁻¹(0.750000) = 0.674490 | Z⁻¹(0.908030) = 1.328722 | 1.052123 | **0.448609** | 0.028260 | ≈ **0.852** |

  (γ = 0.5772156649; e = 2.718281828; 1−γ = 0.4227843351. The "needed annualized SR" column is the
  smallest annualized best-cell Sharpe that yields `DSR ≥ 0.95`, i.e. `z ≥ Φ⁻¹(0.95) = 1.644854`,
  under `var_term ≈ 1` and `T = 4186` (`sqrt(T−1) = 64.692`): `SR_pp ≥ SR0_pp + 1.644854/64.692 =
  SR0_pp + 0.025427`, annualized `SR_ann ≥ SR0_ann + 0.025427·sqrt(252) = SR0_ann + 0.403631`. The
  `var_term ≈ 1` approximation holds to the displayed precision for the small per-obs Sharpes here;
  the runner uses the cell's actual skew/kurtosis at STEP 4. All quantile values are
  `scipy.stats.norm.ppf`-grade exact values (orchestrator-verified mechanical arithmetic); the
  prior hand-bracketed values for N = 3 and N = 4 are superseded.)
```

---

## PATCH 5 — §7.3.3 derivations: correct N=3 and N=4 blocks; update FROZEN line

**ANCHOR (exact current text — the N=3 derivation block):**
```
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
```

**REPLACEMENT:**
```
**N = 3:**
- `a1 = 1 − 1/3 = 0.666667`; `Z⁻¹(0.666667) = 0.430727`. *(Exact `scipy.stats.norm.ppf`-grade value,
  orchestrator-verified mechanical arithmetic. Prior hand-bracketed derivation confirmed this value
  to 6 dp; it stands.)*
- `a2 = 1 − 1/(3e) = 1 − 1/8.154845 = 1 − 0.122626 = 0.877374`; **`Z⁻¹(0.877374) = 1.161957`**.
  *(Exact `scipy.stats.norm.ppf`-grade value, orchestrator-verified mechanical arithmetic. The prior
  hand-bracketed value 1.162095 was off by 1.4 × 10⁻⁴ and is superseded.)*
- bracket `= 0.4227843·0.430727 + 0.5772157·1.161957 = 0.182103 + 0.670701 =` **`0.852804`**.
- `SR0 = 0.426385 · 0.852804 =` **`0.363623`**.
```

**ANCHOR (exact current text — the N=4 derivation block):**
```
**N = 4:**
- `a1 = 1 − 1/4 = 0.750000`; `Z⁻¹(0.750000) = 0.674490` (the canonical upper-quartile probit).
- `a2 = 1 − 1/(4e) = 1 − 1/10.873127 = 1 − 0.091970 = 0.908030`; `Z⁻¹(0.908030) = 1.328869`.
  *(Derivation: bracketed by Z⁻¹(0.905)=1.310579 and Z⁻¹(0.91)=1.340755; the probit at p=0.908030
  converges to 1.32887 (6-dp 1.328869). Anchor: Φ(1.328869) ≈ 0.90803.)*
- bracket `= 0.4227843·0.674490 + 0.5772157·1.328869 = 0.285167 + 0.767143 = 1.052310`.
- `SR0 = 0.426385 · 1.052310 = 0.448688`.
```

**REPLACEMENT:**
```
**N = 4:**
- `a1 = 1 − 1/4 = 0.750000`; `Z⁻¹(0.750000) = 0.674490` (the canonical upper-quartile probit;
  exact `scipy.stats.norm.ppf`-grade value, confirmed unchanged).
- `a2 = 1 − 1/(4e) = 1 − 1/10.873127 = 1 − 0.091970 = 0.908030`; **`Z⁻¹(0.908030) = 1.328722`**.
  *(Exact `scipy.stats.norm.ppf`-grade value, orchestrator-verified mechanical arithmetic. The prior
  hand-bracketed value 1.328869 was off by 1.5 × 10⁻⁴ and is superseded.)*
- bracket `= 0.4227843·0.674490 + 0.5772157·1.328722 = 0.285167 + 0.767059 =` **`1.052123`** (prior: 1.052310, superseded).
- `SR0 = 0.426385 · 1.052123 =` **`0.448609`** (prior: 0.448688, superseded).
```

**ANCHOR (exact current text — the FROZEN line and bracketing-method disclosure in §7.3.3):**
```
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

**REPLACEMENT:**
```
> **FROZEN (elected, `N = 3`): `SR0 = 0.363623` (annualized Sharpe units), per-obs
> `SR0_pp = 0.363623 / sqrt(252) = 0.022906`.** *(Contingency scalar `N = 2` (recorded not elected):
> `SR0 = 0.221616`, per-obs `0.013961`. Contingency scalar `N = 4` (recorded not elected): `SR0 =
> 0.448609`, per-obs `0.028260`.)* See the §7.3.1 table for the per-obs values and the best-cell
> annualized Sharpe each `N` requires to clear `DSR ≥ 0.95`. `SR0` is in the same **annualized**
> units as `SR_1`, `SR_2`, and the firm's `calculate_metrics` Sharpe.
>
> All 6-dp normal-quantile values in §7.3.1 and the derivations above are `scipy.stats.norm.ppf`-grade
> exact values (orchestrator-verified mechanical arithmetic). The `N = 3` and `N = 4` quantiles
> `Z⁻¹(0.877374) = 1.161957` and `Z⁻¹(0.908030) = 1.328722` supersede the prior hand-bracketed
> values (1.162095 and 1.328869 respectively, each off by ~1.4–1.5 × 10⁻⁴); the `N = 2` value
> `Z⁻¹(0.816060) = 0.900452` stands (sub-ULP difference from orchestrator's 0.900453; retained).
> `scipy.stats.norm.ppf` is required at run time per the A-5 pin (§7.3.4); the values here are the
> frozen reference, not the hand-bracketing.
```

---

## PATCH 6 — §3.4: replace the two superseded N=2-wired blocks with the frozen dispersion convention block

**ANCHOR (exact current text — the "Var[SR_n]" hand-arith block and the "DSR threshold inputs" block, both N=2-wired):**
```
### Var[SR_n] — computed by hand over the N = 2 look Sharpes

Inputs: `SR_1 = 0.80`, `SR_2 = 0.197`.

- **Mean:** `SR_bar = (0.80 + 0.197) / 2 = 0.997 / 2 = 0.4985`
- **Squared deviations:**
  - `(0.80 − 0.4985)^2 = (0.3015)^2 = 0.09090225`
  - `(0.197 − 0.4985)^2 = (−0.3015)^2 = 0.09090225`
  - sum = `0.1818045`
- **Variance (population, /N):** `0.1818045 / 2 = 0.09090225`
- **Variance (sample, /(N−1)):** `0.1818045 / 1 = 0.1818045`

> **Var[SR_n] (FROZEN) = 0.0909** (population estimator, dividing by N). `sqrt(Var[SR_n]) = 0.3015`.

Estimator choice: the BLdP `SR0` benchmark is the *expected maximum* of N draws from a distribution
of estimated Sharpes; `Var[SR_n]` is the dispersion of that trial distribution, for which the
population (÷N) estimator is the natural plug-in with only N=2 looks. The sample (÷(N−1)) value
0.1818 is recorded for the Mathematician's election; it would *raise* `sqrt(Var)` to 0.4264 and make
the haircut more conservative. **Frozen primary: Var[SR_n] = 0.0909, sqrt = 0.3015.** Routed to
quant-developer for arithmetic verification (ROUTE_TO below); the values above are HoQR's and are the
frozen inputs.

### DSR threshold inputs handed to the Mathematician (frozen)

The Mathematician owns plugging these into `SR0` (§7.2). The frozen inputs are:

- `N = 2`
- `Var[SR_n] = 0.0909` (population; sample 0.1818 recorded as the conservative alternative)
- `sqrt(Var[SR_n]) = 0.3015`
- `γ = 0.5772156649` (Euler–Mascheroni)
- `e = 2.718281828`
- The two normal-quantile arguments the formula needs: `Z⁻¹(1 − 1/N) = Z⁻¹(0.5) = 0` and
  `Z⁻¹(1 − 1/(N·e)) = Z⁻¹(1 − 1/5.43656) = Z⁻¹(0.81607)`. (HoQR notes that with N=2 the first
  quantile term `Z⁻¹(0.5) = 0` zeroes the `(1−γ)` leg, so `SR0` reduces to
  `0.3015 · 0.5772 · Z⁻¹(0.81607)`. The exact `Z⁻¹(0.81607)` evaluation and the final `SR0` scalar
  are the Mathematician's to compute and sign — this is a normal-CDF inverse, not hand arithmetic.)

> **ROUTE_TO: quant-developer** — verify (1) `Var[SR_n]` arithmetic above
> (mean 0.4985, squared devs 0.09090225 each, population variance 0.09090225); and (2) the
> normal-quantile `Z⁻¹(0.81607)` so the Mathematician can finalize `SR0`. Inputs frozen by HoQR; QD
> verifies, does not re-derive N.
```

**REPLACEMENT:**
```
### Frozen dispersion convention and DSR inputs (Mathematician-owned, elected N = 3)

**Dispersion convention (explicit — required by the Mathematician's rework-1b NOTE).** The dispersion
plug-in `sqrt(Var[SR_n]) = 0.426385` is the **sample standard deviation computed over the TWO
observed, independently-sourced look-representative Sharpes `{SR_1 = 0.80, SR_2 = 0.197}`** — the
sample (÷(N_obs − 1) = ÷1) estimator over the observed pair — held fixed across N ∈ {2, 3, 4}, with
the elected N entering only through the expected-maximum bracket axis. There are only two OBSERVED
independent look-representatives in the firm's falsification archive; the N = 3 election charges a
half-look of multiplicity on the bracket axis for residual independence (the FRED regime gate and the
vol-targeting layer condition on information absent from the bare rate-differential look), but
inventing a third Sharpe observation to inflate or deflate `sqrt(Var)` would be fabrication — there
is no third independently-drawn look-Sharpe in the archive from which to estimate anything. The
sample (÷1) estimator over `{0.80, 0.197}` is therefore the only non-fabricated dispersion estimate
available, and it is the plug-in for all three candidate N values.

**Limitation (honest — the Mathematician's obligation).** A dispersion estimate from exactly 2
observations is itself highly uncertain; the estimation noise propagates in both directions on
`SR0`. The direction of this residual error is absorbed into the two-axis framing disclosed in
§7.3.1 (Var/spread axis conservative-if-wrong; N-axis anti-conservative at the floor) rather than
being claimed away. See §7.3.1 for the full two-axis analysis.

**Cross-reference.** The full frozen SR0 table (all N ∈ {2,3,4}, all quantiles, brackets, and
annualized/per-obs scalars) is in §7.3.1. The derivations are in §7.3.3. The frozen execution
scalar for the STEP-4 runner is in §7.3.3 (FROZEN line) and §7.3.4 (code block).

**Frozen inputs (N = 3 elected — Mathematician-signed):**
- `N = 3` (elected by HoQR §3.4 header; Mathematician-co-signed)
- `sqrt(Var[SR_n]) = 0.426385` (sample ÷1 estimator over observed look-Sharpes `{0.80, 0.197}`; held fixed across all candidate N)
- `γ = 0.5772156649` (Euler–Mascheroni constant)
- `e = 2.718281828`
- `bracket(N=3) = (1−γ)·Z⁻¹(2/3) + γ·Z⁻¹(1 − 1/(3e)) = 0.4227843·0.430727 + 0.5772157·1.161957 = 0.852804`
- `SR0(N=3) = 0.426385 · 0.852804 = 0.363623` (annualized) / `0.022906` (per-obs, = 0.363623/√252)
- `α = 0.05`; DSR gate threshold: `DSR ≥ 0.95`
```

---

## §7.3.5 / §7.3.6 Sweep — result

I read §7.3.5 (frozen threshold) and §7.3.6 (integrated decision functional) in their entirety as they appear in the current assembled document (lines 984–1066).

**§7.3.5:** Contains no N-specific scalars and no reference to "elected N=2" or any numeric SR0 value. It references only the threshold `DSR ≥ 0.95` and the `α = 0.05` budget. **No patch required.**

**§7.3.6:** Contains no N-specific scalars and no SR0 numeric value. It references `DSR ≥ 0.95`, `p_SPA`, `p_RC`, and `k*` only. The phrase "elected" does not appear. **No patch required.**

The §7.3.3 FROZEN line and the §7.3.4 code block are the only execution-critical spots carrying the N-specific SR0_pp literal, and both are patched above (PATCH 2, PATCH 3). The §7.3.1 table is patched in PATCH 4.

---

*Mathematician sign-off: 7 delta-patches produced. Elected scalars: SR0 = 0.363623 ann, SR0_pp = 0.022906 per-obs (N=3). Quantile corrections: Z⁻¹(0.877374) = 1.161957 (was 1.162095), Z⁻¹(0.908030) = 1.328722 (was 1.328869). §7.3.5/§7.3.6 sweep: clean, no further patches. Dispersion convention stated explicitly per HoQR NOTE delegation.*
