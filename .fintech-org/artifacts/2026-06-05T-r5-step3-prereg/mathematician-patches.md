# R5 STEP 3 — Mathematician section patches (wave 2d)

> Apply mechanically, verbatim, to `references/pre-registrations/r5_carry_universe_kill_test.md`.
> Two blocks. PATCH-1 replaces the PART II §2.3 caveat paragraph (the block-quote beginning
> "> **Caveat (typed as numerical, routed to quant-developer):**"). PATCH-2 is a NEW §7.3 inserted
> in PART II immediately after §7.2 (before the "*Mathematician sign-off applies to…*" closing line).
> Trial family: 576746aa. Author: Quantitative Mathematician.

---

## PATCH-1 (replaces PART II §2.3 caveat paragraph)

> **Caveat — DISCHARGED (floor-safe; resolved before freeze).** The studentized statistic
> `T_k = sqrt(n)·mean_hat_k / omega_hat_k` is scale-invariant *in exact arithmetic*; the only way
> finite-precision arithmetic could break that invariance is if the absolute HAC-SE floor `1e-12`
> (`reality_check.py:867`) clipped a genuine `omega_hat_k`, which would spuriously null the affected
> cell. The routed numerical check has been executed on the realized joint matrix and the floor does
> **not** activate for any cell. On the frozen matrix (`2010-03-15 → 2026-04-06`, `T = 4186`, `0`
> dropped — identical to the STEP 2b build), `L_max = 21.330121 → actual_block_length = 22 →`
> Bartlett bandwidth `h = 21`. The carry_momentum cells — the only ones at risk, with ~1000× smaller
> return std — have `omega_hat_k ∈ [6.472882e-08 (GBPJPY, the minimum over ALL 36 cells), 1.811096e-07
> (NZDJPY)]`. The minimum-to-floor ratio is `6.472882e-08 / 1e-12 = 6.47e+04` — **~4.8 orders of
> magnitude above the floor**, far exceeding the "≥ 3 orders" floor-safe criterion this caveat
> pre-committed. The absolute floor `1e-12` therefore **never clips** any carry_momentum cell (nor
> any other), scale-invariance of `T_k` is preserved exactly, and **no relative-floor substitution is
> required**. The absolute floor stands UNCHANGED at `1e-12`; no pre-freeze code change is made on this
> account. *(No p-value was computed in this check; the diagnostic `T_k` range `[−22.8, +67.0]` for
> carry_momentum and `max_all36 = 200.9` for vol_target_carry:USDJPY are informational only — STEP 4
> remains the one-shot run.)* **Evidence:**
> `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/qd-omega-floor-check.yaml` (decision
> `implemented-and-verified`, verdict `floor-safe`), pinning `reality_check.py:850-867` (`_hac_se`,
> floor) and `carry_universe_matrix.py:546-820` (joint matrix build).

---

## PATCH-2 (new §7.3 — Frozen DSR gate and integrated decision functional)

### 7.3 Frozen DSR gate and integrated decision functional (Mathematician — finalizes Method B)

This section freezes the Method-B (§3.2, §3.4) deflation gate and binds it to the SPA decision of
§4/§5. It is the load-bearing numerical freeze: after this is ratified, `SR0`, the DSR statistic, the
threshold, and the integrated CONTINUE/AMBIGUOUS/WIND-DOWN rule are immutable. All quantities below
are pinned to the canonical firm implementation `src/forex_system/harness/dsr.py`
(`compute_dsr`, `expected_max_sr`) — the Mathematician-corrected (2026-05-31) BLP (2014)
implementation, NOT a hand-rolled variant.

#### 7.3.1 Adjudication of the §3.4 inputs (HoQR-supplied, Mathematician-signed)

- **`N = 2` — ACCEPTED.** Admissible under the §7.2 frozen rule ("`N` from the honest-N registry of
  independent carry looks, not the raw `trials.jsonl` count, not 1"). HoQR applied
  `honest_n.py:40-81` suffix-strip dedup (8 carry pre-regs → 5 keys), then collapsed the shared
  `rate_differentials.parquet` feed to **two genuinely distinct information sources** — (1) pure
  rate-differential carry, (2) the carry+momentum hybrid (which injects an SMA price-trend signal
  absent from the carry look). `N = 2` lies inside both ratified scope ranges (HoQR 1–2, NHT 2–4) and
  is neither the under-deflating `N = 1` nor the double-counting `N = 36/37`. Signed.

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

#### 7.3.2 Var[SR_n] estimator election — SAMPLE (÷(N−1)) = 0.1818

**ELECTED: the sample estimator `Var[SR_n] = 0.1818045`, `sqrt(Var[SR_n]) = 0.426385`.** (The
population/÷N value `0.0909` is recorded as the less-conservative alternative.)

Basis (three reasons, all pointing the same way):
1. **Definition.** BLP's `Var[SR_n]` is "the variance of the Sharpe estimates across the `N` trials" —
   a cross-trial sample variance. The unbiased estimator of a population variance from `N` draws is
   the `÷(N−1)` form; the `÷N` form is biased low, which would *under*-deflate.
2. **`N = 2` makes the bias maximal.** At the smallest possible `N`, the `÷N` vs `÷(N−1)` gap is a
   factor of 2 in variance (`0.0909` vs `0.1818`) — the regime where electing the biased-low estimator
   is least defensible.
3. **Provenance caution (§7.3.1).** With `SR_1 = 0.80` registry-unverified, the conservative
   (larger-`Var`, higher-`SR0`) election is the honest choice: if the 0.80 is genuine, the gate is
   correctly calibrated-to-conservative; if it is inflated, the larger spread is already absorbed into
   a higher bar rather than a falsely-easy one.

The cost of this conservatism is borne entirely by the (pre-committed, most-likely) WIND-DOWN posture;
over-deflation cannot manufacture a false CONTINUE. The asymmetry is therefore correct.

#### 7.3.3 The frozen SR0 benchmark scalar

`SR0` is the BLP (2014) expected-maximum-Sharpe benchmark under the null of zero true skill across `N`
trials, in the §7.2 Var-plug-in rendering:

> `SR0 = sqrt(Var[SR_n]) · [ (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e)) ]`

With the elected inputs (`N = 2`, sample `sqrt(Var[SR_n]) = 0.426385`, `γ = 0.5772156649`,
`e = 2.718281828`):
- `Z⁻¹(1 − 1/N) = Z⁻¹(0.5) = 0` (zeroes the `(1−γ)` leg — a property of `N = 2`).
- `Z⁻¹(1 − 1/(N·e)) = Z⁻¹(0.8160603) = 0.900452` (inverse standard-normal CDF; verified).
- bracket `= (1−γ)·0 + γ·0.900452 = 0.5772156649 · 0.900452 = 0.519756`.

> **FROZEN: `SR0 = 0.221616` (annualized Sharpe units).** *(Population-var alternative, recorded
> not elected: `SR0 = 0.156706`.)* `SR0` is in the same **annualized** units as `SR_1`, `SR_2`, and
> the firm's `calculate_metrics` Sharpe.

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

#### 7.3.4 The DSR statistic evaluated at run time (exact)

The DSR is evaluated on **the single best cell** — the cell `k*` that attains the family maximum
studentized statistic `T_SPA = max_k T_k` (§2.1). Its skewness and excess kurtosis are that cell's
own (`γ3 = skew(f_{k*})`, `γ4 − 1 = excess_kurtosis(f_{k*})` in Fisher convention, i.e.
`kurtosis − 3`), computed on cell `k*`'s realized per-bar net-of-cost return series over the frozen
common index. **It is NOT computed on a pooled series and NOT on any other cell.** The statistic
(Bailey–López de Prado 2014, eq. 10; pinned to `dsr.py:compute_dsr`):

```
SR_hat_pp  = SR_hat_ann / sqrt(252)                 # per-obs Sharpe of cell k* (annualized ÷ sqrt(252))
SR0_pp     = 0.221616 / sqrt(252) = 0.013961        # FROZEN benchmark, per-obs (§7.3.3)
var_term   = 1 − γ3·SR_hat_pp + ((γ4_excess + 2)/4)·SR_hat_pp²
DSR        = Φ( (SR_hat_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )
```

**Unit discipline (binding).** `SR_hat`, `SR0`, `γ3`, `γ4` ALL enter in **per-observation** units; the
annualized cell Sharpe is divided by `sqrt(252)` exactly once before entering, matching
`dsr.py:180`. The variance-of-Sharpe term uses **excess** kurtosis with the `+2` coefficient
(`(γ4_excess + 2)/4`, the corrected kurtosis convention, `dsr.py:184` — NOT `+3`, NOT `+1`), because
`var[SR] ∝ 1 − γ3·SR + (γ4_nonexcess − 1)/4·SR²` and `γ4_nonexcess − 1 = γ4_excess + 2`. `T = 4186`
(the frozen common-index length). `Φ` is the standard-normal CDF. If `var_term ≤ 0`, `compute_dsr`
returns `0.0` (cannot certify) and the gate FAILS — this is the documented degenerate path
(`dsr.py:187-195`), not a TECHNICAL FAILURE.

#### 7.3.5 Frozen threshold

> **FROZEN: the DSR gate is cleared iff `DSR ≥ 0.95`.**

Basis. `DSR = Φ(z)` is the probability that cell `k*`'s true Sharpe exceeds the selection-deflated
benchmark `SR0`; `DSR ≥ 0.95` is the one-sided 95% certainty that the best cell's edge survives the
snooping charge. The threshold is set **equal to `1 − α` with `α = 0.05`** (§5), so the DSR gate and
the SPA p-gate enforce the **same** 5% false-positive tolerance on the two distinct error channels
they each control (SPA: family-wise rejection error under the joint null; DSR: selection/overfit
inflation of the winning Sharpe). Matching them prevents one gate from being silently slacker than the
other. A laxer `0.90` would admit a 10% overfit-survival probability — inconsistent with `α = 0.05`;
a stricter `0.99` would over-charge beyond the firm's stated error budget. `0.95` is the
budget-consistent choice and is frozen.

#### 7.3.6 The integrated decision functional (binds §4 / §5)

Let `p_SPA` = the Hansen-SPA "consistent" p-value (§2.4, the primary decision p-value),
`p_RC` = the White-RC cross-check p-value, and `DSR` = the §7.3.4 statistic on cell `k*`. The frozen
firm decision is:

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

**The load-bearing branch ruling (made precise):** **`p_SPA < 0.05` but the DSR gate FAILS
(`DSR < 0.95`) → AMBIGUOUS, NOT CONTINUE and NOT WIND-DOWN.** Rationale: a bare SPA rejection that
cannot survive the selection-deflation charge is exactly the snooping artifact Method B exists to
catch — it is *necessary-but-not-sufficient* (§3.2, §4 CONTINUE clause). It does not license CONTINUE
on the family (the deflation says the winning Sharpe is consistent with selection luck), and it is not
a clean WIND-DOWN either (the SPA null *was* rejected, so "indistinguishable from chance" is not the
honest description). It maps to the confirmatory-only gate of §5 outcome 4: the specific surviving
structure may be carried into a fresh, separately-pre-registered confirmatory test with its own
freeze, treated as a brand-new hypothesis. No capital, no re-opening of the 36-cell family.

This functional is consistent with §4 (CONTINUE is necessary-but-not-sufficient and only ever buys a
confirmatory pre-reg) and §5 (the action map). Where §4/§5 said "post-deflation," §7.3.6 is the exact
operationalization of that phrase.
