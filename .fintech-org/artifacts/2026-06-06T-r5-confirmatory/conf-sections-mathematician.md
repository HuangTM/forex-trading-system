# Confirmatory Pre-Registration — Mathematician-Owned Sections (FROZEN)

**Track:** `r5-confirmatory-2026-06-06:phase1:task1.0`
**Trial:** `f2fb41fd` (new org-counter trial; NOT a reuse of R5's `576746aa`)
**Author role:** Quantitative Mathematician
**Status:** FROZEN at authoring; numbers below are the pre-registered contract.
**Source anchors (verified, this session):**
- R5 result: `references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml:1-19` (decision `AMBIGUOUS_GATE_FAIL`; `k_star_label=vol_target_carry:USDJPY`, `k_star_idx=18`; `sr_ann_kstar=0.7672287`, `skew_kstar=0.1962855`, `excess_kurtosis_kstar=8.2782585`; `T=4186`, `k=36`; `p_spa_consistent=0.0161968`, `p_rc=0.0587882`, `dsr=0.9502875`; `SR0_PP_frozen=0.022906`; `block_length_used=21`; `B=5000`; `master_seed=576746`).
- R5 SR0 derivation: `r5_carry_universe_kill_test.md:288-320` (dispersion `sqrt(Var[SR_n])=0.426385` over `{0.80, 0.197}`; `bracket(N=3)=0.852804`; `SR0(N=3)=0.363623` ann `=0.022906` per-obs).
- R5 kill-switch: `r5_carry_universe_kill_test.md:399-406` (`0.767` = ann Sharpe to clear DSR≥0.95 at N=3, T=4186).
- Selection-absorption binding rule: `r5_carry_universe_kill_test.md:343,365,385` (confirmatory test MUST absorb the R5 36-cell selection in its own honest-N / SR0).
- Effective independent dimension of the carry family: `r5_carry_universe_kill_test.md:215` (≈1–2 HoQR / 2–4 NHT; joint bootstrap reality ≈1–4).
- DSR conventions pinned: `src/forex_system/harness/dsr.py:179-207`; `src/forex_system/harness/r5_decision.py:122-194`.
- HAC SE + Politis-White: `src/forex_system/harness/reality_check.py:58-88,152-343`.

---

## 1. Null Hypothesis & Test Statistic (CONF-statistic) — FROZEN

### 1.1 Series under test (single, pre-specified)

The confirmatory test evaluates **exactly one** return series:

> `r_t` = net-of-cost, post-`entry_delay_bars=1` daily portfolio returns of the **`vol_target_carry:USDJPY`** structure (R5 cell `k_star_idx=18`), computed on the **hold-out window only** (post-2026-04-06; window rule in CONF-holdout). Same `config/default.yaml` risk/cost params and `RealisticCostModel` as the R5 frozen run. No re-parameterization, no variant or pair substitution.

The 36-cell SPA family is **closed**. This is a single-series test; the family multiplicity is not re-run — it is **absorbed as a selection charge** (Section 2).

### 1.2 Null and alternative

> **H0:** `E[r_t] ≤ 0` (the structure has no positive net edge on unseen data).
> **H1:** `E[r_t] > 0`.

One-sided, `α = 0.05` total (spent across looks per Section 3). Direction is fixed a-priori (the structure was selected as a positive-Sharpe argmax in R5); a two-sided test would waste half the α on an irrelevant tail.

### 1.3 Frozen statistic — studentized mean with HAC SE

At each look with `n` hold-out bars:

```
t_stat = sqrt(n) * mean(r) / omega_hat
```

where `omega_hat` is the **Newey–West (Bartlett-kernel) HAC standard error of the mean**, computed by `reality_check.hac_se_nw(r, bandwidth = max(L - 1, 1))` (pinned: `reality_check.py:58-88`), and `L` is the **Politis–White (2004) + PPW (2009)** automatic mean block length computed **on the hold-out series itself** via `reality_check.politis_white_block_length(r)`, then `L = max(1, ceil(L_pw))`.

**Guard (FROZEN):** `L ≥ 1` always (the PW routine already clamps `L_opt` into `[1, b_max]` and returns `1.0` on constant/near-iid series, `reality_check.py:316-324`). The bandwidth into `hac_se_nw` is `max(L − 1, 1) ≥ 1`. This mirrors the R5 SPA studentization (`r5c_hansen_spa`/`select_k_star_studentized`, `r5_decision.py:104-109`) bit-for-bit, so the confirmatory `t` is the single-cell restriction of the R5 family statistic — the same `T_k` machinery, evaluated on one column on clean data.

### 1.4 p-value mechanism — FROZEN: stationary block bootstrap (NOT asymptotic normal)

**Election: circular/stationary block bootstrap**, not the asymptotic-normal reference.

**Justification.** At the looks the sample is small-ish and serially dependent: `n ≈ 625` bars at +2.5yr, `n ≈ 1255` at +5yr (252 trading days/yr). The selected cell's R5 in-sample return distribution has **excess kurtosis 8.28** and mild positive skew (0.196) — heavy tails. Under fat tails and autocorrelation at `n` in the hundreds, the `t`-statistic's null distribution is NOT well-approximated by N(0,1): the asymptotic-normal p-value is anti-conservative (over-rejects). The stationary bootstrap (Politis–Romano 1994) resamples geometric-length blocks, preserving the serial-dependence and tail structure of the empirical series, and is the same null-generation mechanism R5 used. Consistency demands the confirmatory test use the same falsifier family.

**Mechanism (FROZEN):**
1. Compute observed `t_obs = sqrt(n)*mean(r)/omega_hat` on the hold-out series.
2. Impose H0 by de-meaning: `d = r − mean(r)` (zero-mean null, autocorrelation/variance preserved — identical convention to `r5a` and to R5c's recentering, `reality_check.py:534-535`).
3. For `b = 1..K`: draw a stationary circular block resample `d*_b` (block length `L` as in §1.3, geometric block lengths), recompute `t*_b = sqrt(n)*mean(d*_b)/omega_hat(d*_b)` (HAC SE recomputed on each resample, mirroring R5c, `reality_check.py:938`).
4. `p = (1 + #{ t*_b ≥ t_obs }) / (K + 1)` — the +1/+1 convention avoids `p=0` (matches `reality_check.py:557,962`).

**FROZEN bootstrap parameters:** `K = 10000` resamples (the module default `_B`, `reality_check.py:49`; supersedes the R5 STEP-4 `B=5000` — the single-series confirmatory test is cheap enough to run the full `K`, tightening the bootstrap MC-SE). Block length `L` = Politis–White auto on the hold-out series, `L ≥ 1` guard. Seed = the confirmatory master seed (Section 5); the bootstrap child seed follows the R5a convention (uses `master_seed` directly for the single-series block bootstrap, `reality_check.py:527`).

This `p` is the look-level evidence compared against the alpha-spending boundary (Section 3). The DSR/selection gate (Section 2) is a **separate, additional** hurdle that must ALSO clear at the final look.

---

## 2. Selection-Absorption Mechanism (the load-bearing freeze) — FROZEN

### 2.1 What must be absorbed and why the clean hold-out does NOT erase it

The candidate `vol_target_carry:USDJPY` was chosen as **`argmax` of 36 studentized `T_k`** in R5 (`r5_decision.select_k_star_studentized`). The data is clean (post-2026-04-06, unseen), but **the hypothesis is selected**. The garden-of-forking-paths charge attaches to *how the hypothesis was chosen*, not to *which data tests it*: had a different cell won the R5 argmax, a different confirmatory hypothesis would now be frozen. Clean hold-out data removes the **in-sample overfit** of the point estimate; it does **not** remove the **multiplicity** of the selection event. R5 §4/§5 makes this BINDING (`...md:343,385`): a confirmatory test that omits the R5 selection burden is VOID and its p is not face-valid.

### 2.2 Alternative rejected (stated and defended-against)

> **Rejected alternative — "no charge, the data is unsnooped, so a plain single-series test suffices."**

Steelman: the hold-out is genuinely out-of-sample; conditional on the hypothesis, the single-series `t`/bootstrap p is an honest frequentist statement about *this* series. **Why rejected:** the firm does not get to condition away the selection for free. The relevant error rate is the *family-wise* probability that the firm declares a winner when none exists — and the firm reached this single hypothesis by maximizing over 36 correlated cells in R5. A plain single-series α=0.05 test, applied to the best-of-36 survivor, has an *actual* type-I rate well above 0.05 because the candidate was pre-filtered for apparent strength. Charging the selection in the DSR `N` restores face-validity. (The bootstrap p in Section 1 is the *clean-data* evidence; the DSR gate in §2.3 is where the selection charge is paid.)

### 2.3 The mechanism: a BLdP DSR gate on the hold-out Sharpe with absorbed `N_conf`

The selection enters through the **Deflated Sharpe Ratio benchmark `SR0`**, exactly as in R5 (Method B, BLdP 2014), but with `N` raised to absorb the R5 selection. The DSR gate is computed on the **hold-out cell's own metrics** (its own ann Sharpe, skew, excess kurtosis, and `T_holdout`) — the R5 in-sample `0.767/0.196/8.28` are **prior-look anchors only**, never the hold-out inputs (per CONF-statistic done_when).

**DSR formula (pinned conventions, `dsr.py:179-203` / `r5_decision.py:172-193`):**
```
SR_pp        = SR_ann_holdout / sqrt(252)
var_term     = 1 − skew_holdout * SR_pp + ((xkurt_holdout + 2)/4) * SR_pp^2
z_dsr        = (SR_pp − SR0_pp_conf) * sqrt(T_holdout − 1) / sqrt(var_term)
DSR          = Phi(z_dsr),  clipped to [0,1]
```
Degenerate pins carried forward verbatim: `SR_ann_holdout ≤ 0 → DSR=0`; `var_term ≤ 0 → DSR=0` (gate FAIL, not technical failure). `Phi = scipy.stats.norm.cdf` (required; no approximation — A-5 pin). DSR gate cleared iff **`DSR ≥ 0.95`**.

**BLdP `SR0` benchmark (pinned form, `...md:121,737`):**
```
SR0_ann = sqrt(Var[SR_n]) * [ (1 − γ)·Z⁻¹(1 − 1/N_conf) + γ·Z⁻¹(1 − 1/(N_conf·e)) ]
SR0_pp  = SR0_ann / sqrt(252)
```
with `γ = 0.5772156649`, `e = 2.718281828`, `Z⁻¹ = norm.ppf`.

### 2.4 Election of `N_conf` (the selection charge) — FROZEN

The confirmatory `N` must carry **both** charges the binding rule names:
- the **R5 best-of-36-on-correlated-cells** selection, whose *effective independent dimension* the R5 joint bootstrap and scope analysis put at **≈1–4** (`...md:215`: HoQR ≈1–2, NHT ≈2–4), and
- the **prior honest-N ≈ 3** carry looks already charged in R5 (the family had spent ~3 effectively-independent looks before R5).

These are **not additive in the naive sense** (the 36 cells ARE the carry family — charging 3 prior looks AND 36 raw cells double-counts, exactly the error R5 §7.2 warns against, `...md:243`). The principled construction: the confirmatory selection event is "the firm picked the single best effectively-independent carry look, having already spent the family's effective looks." The effective independent dimension of the *selection pool* is the R5 joint-bootstrap figure (1–4), and the firm's prior carry multiplicity is the elected R5 `N=3`. I elect the confirmatory charge at the **conservative end of the union**:

> **FROZEN: `N_conf = 6`.**

Derivation of the election (anti-survivorship / conservative-for-a-kill-test direction, mirroring R5 §3.4's "elect off the floor that raises the bar" logic — note BLdP `SR0` is strictly INCREASING in `N`, so a HIGHER `N` is the STRICTER, more skeptical gate):
- R5 effective selection dimension upper end (NHT): `≈4`.
- Prior carry honest-N already spent (R5 elected): `3`.
- The confirmatory event spends *one new effective look* (the confirmatory hold-out test itself) on top of the selection pool.
- A defensible conservative union: `N_conf = max(effective_selection_dim_upper, prior_honest_N) + (prior_honest_N − 1)` is one heuristic, but I avoid arithmetic theater. I elect `N_conf = 6` as the smallest integer that (a) strictly exceeds both the R5 effective-dimension ceiling (4) and the R5 prior honest-N (3), and (b) sits at roughly their sum-minus-overlap (`4 + 3 − 1 = 6`), charging the selection-from-pool AND the prior family spend while removing the one-look double-count of the shared rate-differential idea. `N_conf ∈ [2,6]` is the admissible band the prompt names; I freeze the **ceiling (6)** because this is a KILL test and over-deflation is the safe-if-wrong direction (a structure that clears DSR≥0.95 at `N=6` is genuinely hard to explain by selection luck).

**Dispersion convention (FROZEN, carried from R5 unchanged):** `sqrt(Var[SR_n]) = 0.426385` — the sample (÷1) standard deviation over the two observed independently-sourced look-Sharpes `{0.80, 0.197}` (`...md:315`). No third look-Sharpe exists in the archive; inventing one would be fabrication. `Var[SR_n]` is held FIXED across `N`; `N_conf` enters ONLY the expected-maximum bracket axis (R5's frozen two-axis convention, `...md:294-301`).

### 2.5 Derived `SR0_conf` (shown arithmetic)

Bracket at `N_conf = 6`:
```
Z⁻¹(1 − 1/6)        = Z⁻¹(0.833333)            = 0.967422
Z⁻¹(1 − 1/(6e))     = Z⁻¹(1 − 0.061313)
                    = Z⁻¹(0.938687)            = 1.543843
bracket(N=6)        = (1−γ)·0.967422 + γ·1.542968
                    = 0.4227843·0.967422 + 0.5772157·1.543843
                    = 0.409013 + 0.891141
                    = 1.300141
SR0_ann_conf        = 0.426385 · 1.300141      = 0.554361   (annualized)
SR0_pp_conf         = 0.554361 / sqrt(252)
                    = 0.554361 / 15.874508     = 0.034921   (per-obs)
```

> **FROZEN: `SR0_ann_conf = 0.554361`, `SR0_pp_conf = 0.034921` (per-obs), `N_conf = 6`.**

Sanity vs R5: R5 used `N=3 → SR0_ann=0.363623`. Raising `N` to 6 raises the deflation benchmark from 0.3636 to 0.5542 ann (≈+52%), exactly the stricter-gate direction the selection charge requires. (Z⁻¹ values above are standard normal quantiles to 6 dp; QD to confirm via `scipy.stats.norm.ppf` — see Section 5 routed question.)

---

## 3. Look Schedule + Alpha-Spending (CONF-interim) — FROZEN

### 3.1 Planning Sharpe (the shrinkage freeze — read first)

Power must be planned at a **deflated/shrunk** Sharpe, NOT the selection-biased in-sample `0.767`. The `0.767` is the argmax of 36 studentized statistics on snooped data — it is upward-biased by exactly the selection the DSR gate deflates. **FROZEN planning SR:**

> **`SR_plan = SR0_ann_conf = 0.554`** (annualized).

Rationale: `SR0_conf` is the firm's pre-registered benchmark for "what a non-lucky structure must beat." It is the honest, selection-deflated location at which the firm should plan power — equivalently, the smallest true ann Sharpe at which a pass is *meaningful* rather than noise. Planning at the snooped `0.767` would over-state power (claim the test is more sensitive than it is); planning at `SR0_net`≈0.55 is the conservative, defensible choice. (A posterior-shrunk alternative — e.g. James–Stein toward 0 from 0.767 — would land in a similar 0.5–0.6 band; I freeze the pre-registered `SR0_conf` as the single auditable number rather than introduce a second free parameter.)

### 3.2 Look schedule — FROZEN

Hold-out starts **2026-04-07** (first bar strictly after the R5 common-index terminus 2026-04-06).

| Look | Calendar date | Years of hold-out | Approx `n` (daily, 252/yr) | Information fraction `t` |
|------|---------------|-------------------|-----------------------------|---------------------------|
| 1 (interim) | **2028-10-06** | +2.5 yr | ≈ 630 | 0.50 |
| 2 (final, terminal) | **2031-04-06** | +5.0 yr | ≈ 1260 | 1.00 |

Information fraction is taken proportional to elapsed hold-out calendar time (equivalently bar count), `t₁ = 2.5/5.0 = 0.5`. **The final look is TERMINAL — no extension, no third look** (CONF-decision-map outcome 2/3 fires at look 2 regardless). Minimum-bar guard for bootstrap validity (CONF-holdout co-sign): the interim look requires `n ≥ 504` bars (~2 yr) before it may fire; if the data pipeline yields fewer bars than the +2.5yr schedule implies at the frozen date, the interim is SKIPPED (its α is rolled into the final via the spending function — the Lan-DeMets property permits this) and only the terminal look runs. The terminal look requires `n ≥ 756` bars (~3 yr) to be valid; below that → TECHNICAL_FAILURE (re-freeze), never a pass.

### 3.3 Alpha-spending function + boundaries — FROZEN

**Spending function: Lan–DeMets O'Brien–Fleming-type (`sfLDOF`), one-sided, total `α = 0.05`.** OBF is elected over Pocock because it spends almost no α early (preserves power at the terminal look — the firm wants the 5-yr look to retain near-full sensitivity) while still permitting an overwhelming-evidence early stop.

Spending function (gsDesign `sfLDOF` canonical convention; the `α/2` plug-in is the SHAPE parameter, the spend total is the one-sided `α=0.05`):
```
α*(t) = 2·(1 − Φ( Z⁻¹(1 − α/2) / sqrt(t) )) = 2·(1 − Φ( 1.959964 / sqrt(t) ))
```
Cumulative α spent, and incremental per-look spend:
```
α*(0.5) = 2·(1 − Φ(1.959964/0.707107)) = 2·(1 − Φ(2.771808)) = 2·(1 − 0.997213) = 0.005575   →  spend₁ = 0.005575
α*(1.0) = 2·(1 − Φ(1.959964))          = 2·(1 − 0.975000) = 0.050000                          →  spend₂ ≈ 0.04442
```
(I report the directly-derived one-sided OBF spend; the widely-tabulated `≈0.0084 / 0.0416` split corresponds to the t-fraction reported at slightly different look timing — the gsDesign `sfLDOF` at exactly `t=0.5` gives the `0.0056/0.0444` split above; QD pins the exact split via gsDesign at the frozen `t`.)

**One-sided nominal z-boundaries (FROZEN, to be reproduced exactly by QD via gsDesign `sfLDOF`):**

| Look | `t` | incremental α | nominal one-sided z-boundary | reject H0 if |
|------|-----|---------------|------------------------------|--------------|
| 1 | 0.50 | 0.005575 | **z₁ = 2.537988** (one-sided p ≤ 0.005575) | bootstrap-`t` look-1 p ≤ 0.005575 |
| 2 | 1.00 | 0.044425 | **z₂ = 1.662107** (bivariate joint, scipy-exact) | bootstrap-`t` look-2 p ≤ 0.044425 |

The boundaries are applied **on the bootstrap p-value scale** (Section 1.4): reject at look `j` iff the look-`j` bootstrap p ≤ the incremental spend `α*(t_j) − α*(t_{j-1})`. (Equivalently, on the z-scale: `t_obs ≥ z_j`. The z₂=1.662107 is the bivariate joint-exact final critical value — derived by solving P(Z1≥z1 OR Z2≥z2|H0)=0.05 exactly via scipy.stats.multivariate_normal.cdf; confirmed by independent dblquad quadrature and 5 M-sample MC. **The bootstrap p is the operative test; the z-boundaries are the equivalent reference.**

### 3.4 Futility (optional binding early-KILL) — FROZEN as NON-binding advisory

I freeze a **non-binding** futility advisory, not a binding boundary: at the interim look, if the hold-out ann Sharpe is **negative** (point estimate `< 0`), the firm MAY early-KILL (it cannot clear a positive-edge H1 by the terminal look without a regime reversal that itself would void confirmatory logic). It is NON-binding to avoid the NHT objection that a binding futility boundary not symmetric with the efficacy spend can inflate error in the wrong direction; the firm retains discretion to run to the terminal look. No α is recovered from futility (one-sided efficacy spend is unaffected). The terminal look remains the only **binding** decision.

### 3.5 Power at the terminal look — FROZEN (shown work)

Single-series power, daily returns, annualized planning `SR_plan = 0.554`. The horizon-`Y`-years single-series `t`-statistic location under H1 is `λ = SR_true · sqrt(Y)` (annualized-Sharpe convention: over `Y` years the cumulative-mean t-stat scales as `√(years)`; verified against the orchestrator anchor `Y₅₀=(z_α/SR)²`).

At the **terminal look (Y=5)** with the bivariate joint-exact final boundary `z₂ = 1.662107`:
```
λ = SR_plan · sqrt(Y) = 0.554 · sqrt(5) = 0.554 · 2.236068 = 1.238826
power = P(Z + λ ≥ z₂) = Φ(λ − z₂) = Φ(1.239588 − 1.662107) = Φ(−0.422519) = 0.336 (single-look); two-look joint power = 0.340
```
> **Terminal-look power ≈ 0.34 (34%) at `SR_plan = 0.554361` (two-look joint; single-look 0.336).**

This is LOW and is disclosed as such. Cross-check against the orchestrator anchors at the fixed-sample boundary `z=1.645`, `SR=0.767`: `Y₅₀=(1.645/0.767)²=4.60 yr`, `Y₈₀=((1.645+0.8416)/0.767)²=10.5 yr` — i.e. even at the *snooped* 0.767, 5 yr gives ~52% power; at the honest `SR_plan=0.554361`, `Y₅₀=(1.645/0.554361)²=8.81 yr` and `Y₈₀=((1.645+0.8416)/0.554361)²=20.1 yr`. So a 5-yr terminal look at the honest planning SR is **underpowered (~33%)**. This is the explicitly-disclosed power reality (CONF-interim done_when) and is the reason the decision map treats a non-rejection at the terminal look as a KILL with the honest acknowledgment that low power makes non-rejection uninformative as *evidence of no edge* — but it does NOT license continued spend (CONF-decision-map outcome 3). NHT reviews this statement.

The "monthly-stale signal" concern (≈1 effective obs/month) would FURTHER reduce effective `n` and power if the carry signal autocorrelation is high; the Politis–White block length on the hold-out series will surface this empirically (a large `L` ⇒ few effective independent blocks ⇒ wider HAC SE ⇒ lower realized power than the iid-daily calc above). The iid-daily power (~33%) is therefore an UPPER bound; realized power may be lower. Disclosed.

---

## 4. `kill_switch_threshold` Derivation — FROZEN (verbatim pre-reg field)

The `kill_switch_threshold` is the **minimum hold-out annualized Sharpe** the structure must achieve **at the terminal look** to clear the DSR gate (`DSR ≥ 0.95`) at `SR0_pp_conf = 0.034921`, `T_holdout = 1260` (the +5yr terminal `n`), carrying the hold-out cell's own higher-moment plug-ins.

DSR=0.95 ⇒ `z_dsr = Φ⁻¹(0.95) = 1.644854`. Solve the DSR z-equation for `SR_pp`:
```
z_dsr = (SR_pp − SR0_pp_conf) · sqrt(T−1) / sqrt(var_term) = 1.644854
```
`var_term` depends on `SR_pp` and the hold-out skew/kurtosis (unknown until the run). For the FROZEN threshold I plug the R5 prior-look higher moments as the pre-registered placeholder (`skew=0.196`, `xkurt=8.28`) — these are the only pre-registered moment anchors; the runner recomputes `var_term` with the hold-out's OWN moments at evaluation (the threshold is a function, evaluated at run time, but I freeze its value at the anchor moments for the verbatim field). Two-pass solve (var_term is near 1 because `SR_pp` is small):

Pass 0 (var_term = 1):
```
SR_pp ≈ SR0_pp_conf + z_dsr / sqrt(T−1) = 0.034921 + 1.644854/sqrt(1259)
      = 0.034921 + 1.644854/35.482 = 0.034921 + 0.046357 = 0.081278
```
Pass 1 (recompute var_term at SR_pp=0.081265, skew=0.196, xkurt=8.28):
```
kurt_coeff = (8.28 + 2)/4 = 2.570
var_term   = 1 − 0.196·0.081278 + 2.570·0.081278² = 1 − 0.015930 + 2.570·0.006606
           = 1 − 0.015930 + 0.016977 = 1.001047
sqrt(var_term) = 1.000523
SR_pp = 0.034921 + 1.644854·1.000523/35.482 = 0.034921 + 0.046381 = 0.081302   (converged; brentq exact: 0.081303)
```
Annualize:
```
SR_ann = SR_pp · sqrt(252) = 0.081303 · 15.874508 = 1.290641
```

> **FROZEN: `kill_switch_threshold: 1.2906`** (annualized hold-out Sharpe required at the terminal look to clear DSR ≥ 0.95 at `SR0_pp_conf=0.034921`, `N_conf=6`, `T_holdout=1260`; brentq-exact 1.290641).

Interpretation: any terminal-look hold-out ann Sharpe **below 1.291 fails the DSR gate and cannot pass the confirmatory test** (it maps to a KILL branch). This is far stricter than R5's `0.767`, for two compounding reasons: (i) `N_conf=6` raises `SR0` vs R5's `N=3`; (ii) `T_holdout≈1260` is far smaller than R5's `4186`, so the `sqrt(T−1)` lever is weaker and a higher Sharpe is needed to reach the same DSR. Both are correct and intended: a 5-yr clean-data confirmation of a selected structure SHOULD demand a high realized Sharpe. NOT copied from R5 (per CONF-kill-switch-threshold).

(QD numerical-confirmation routed in Section 5: the two `Z⁻¹` quantiles in §2.5, the OBF boundaries in §3.3, and this two-pass solve. All are standard `scipy.stats.norm` evaluations; values shown are my hand-work to 3–6 dp.)

---

## 5. Run Mechanics to Freeze — FROZEN

**Master seed (FROZEN, derived from trial stem `f2fb41fd`, mirroring R5's rule `master_seed=576746` from stem `576746aa`):**
R5 took the first 6 hex of the trial stem and read them as base-10-of-decimal-digits... no — R5's `576746` is the leading numeric run of `576746aa`. The confirmatory stem `f2fb41fd` has no leading decimal digits, so I freeze the rule: **`master_seed = int(first 6 hex chars of trial stem, base 16) mod 1_000_000`**. `f2fb41` (hex) = 15924289; `15924289 mod 1_000_000 = 924289`.
> **FROZEN: `master_seed = 924289`.** Child seeds follow the R5 convention (single-series block bootstrap uses `master_seed` directly, `reality_check.py:527`).

**Bootstrap:** `K = 10000` (Section 1.4). Stationary circular block bootstrap, Politis–White auto block length on the hold-out series, `L ≥ 1` guard. RNG = `numpy.PCG64` seeded by `master_seed` (R5 convention, `reality_check.py:528`).

**Estimator conventions (mirror R5 A-5 pins):**
- Sharpe: `mean / std(ddof=1) · sqrt(252)`, `rf=0` (`reality_check.py:91-104`).
- Skew: `scipy.stats.skew(x, bias=True)`; excess kurtosis: `scipy.stats.kurtosis(x, fisher=True, bias=True)` (`r5_decision.py:147-150`).
- HAC SE: `reality_check.hac_se_nw(x, bandwidth=max(L−1,1))`, Bartlett kernel, `s2 ≥ 1e-12` floor (`reality_check.py:58-88`).
- DSR: `dsr.py`/`r5_decision.py` conventions verbatim (§2.3); `Phi = scipy.stats.norm.cdf`; `Z⁻¹ = scipy.stats.norm.ppf`. **scipy is REQUIRED — no approximation fallback** (A-5 pin, `r5_decision.py:22-30`).
- `periods_per_year = 252`.

**scipy pin:** scipy REQUIRED at run time; absence ⇒ TECHNICAL_FAILURE (re-freeze), never a silent approximation (`r5_decision.py:22-30`).

**Evaluation command contract (math contract; QD owns implementation):**
- The runner is **refuse-without-receipt**: it MUST verify the committed freeze-receipt (SHA-256 of this confirmatory pre-reg + pinned code commit) before touching any hold-out bar, mirroring `scripts/cut_freeze_receipt.py` / the R5 STEP-4 runner pattern. No metric is computed on post-2026-04-06 data before the receipt is committed.
- It runs **only at the two frozen look dates** (2028-10-06, 2031-04-06). No unscheduled peeks.
- At each look it emits: `n`, `L_pw`, `t_obs`, look-level bootstrap p, cumulative α spent, the look-`j` boundary, the DSR (with hold-out moments), and the §7.3.6-style decision-functional verdict mapped to the CONF-decision-map branch.
- Whether this reuses the existing harness (`carry_universe_matrix.py` single-column + `reality_check` single-series path) or needs a thin new single-series runner is QD's implementation question — the math contract above is what must be satisfied.

`numerical-question-routed:` " " (QD confirmation received; all constants corrected per mathematician-z2-election.yaml — scipy-exact set: bracket(6)=1.300141, SR0_ann=0.554361, SR0_pp=0.034921, z1=2.537988, z2=1.662107, kill_switch_threshold=1.2906, two-look power=0.340)
