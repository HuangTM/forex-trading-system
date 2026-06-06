# R5 Kill Test — Frozen Statistical Specification (Mathematician-owned sections)

> **Status:** FREEZABLE. Every parameter below is a final value. No "to be decided" clauses.
> **Authored by:** Quantitative Mathematician. Trial family: 576746aa.
> **Pins implementation:** `src/forex_system/harness/reality_check.py` (`r5c_hansen_spa`,
> `politis_white_block_length`, `politis_white_block_length_multivariate`) and
> `src/forex_system/harness/carry_universe_matrix.py` (`build_joint_return_matrix`,
> `run_r5_on_carry_universe`), at the git commit recorded in the freeze-receipt.
> Sections 4 and 7 are co-signed: block-length with quant-developer; power with NHT; OOS
> window with HoQR (HoQR proposes the window, the mathematician signs the snooping method).

---

## 1. Null Hypothesis

Let the universe `U` be the `K = 36` cells indexed `k = 1..36`: the 6 carry variants
`{carry, carry_fred, fred_carry_stripped, vol_target_carry, vol_target_carry_no_vol_scaling, carry_momentum}`
crossed with the 6 JPY pairs `{USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY}`.

For cell `k` and bar `t = 1..n`, define `f_{k,t}` as the **net-of-cost, post-entry-delay,
benchmark-relative per-bar return** of cell `k`. Concretely, `f_{k,t}` is the bar-`t` simple
return of that cell's backtest equity curve: `f_{k,t} = EC_{k,t}/EC_{k,t-1} - 1`, taken from
`equity_curve.pct_change()` of a `run_backtest` whose signals were already shifted by
`entry_delay_bars = 1` (no-lookahead invariant) and whose equity is already net of the
RealisticCostModel (spread + slippage + commission + direction-dependent swap).

**Benchmark = ZERO.** The benchmark-relative return equals the raw cell return:
`d_{k,t} := f_{k,t} - b_t = f_{k,t}` because `b_t = 0`. Rationale (double-counting): for a carry
strategy the cost-of-carry is already realized inside the swap leg, which is part of the
net-of-cost equity curve. Subtracting an external cost-of-carry benchmark would deduct the carry
return a second time. Zero is therefore the correct, non-double-counting benchmark.

Define the cell expectation `d_k := E[f_{k,t}]` (stationary mean of the benchmark-relative return).

**Frozen null hypothesis (verbatim):**

> **H0: max over cells k of the expected net-of-cost, post-entry-delay, benchmark-relative
> (benchmark = ZERO) per-bar performance d_k ≤ 0**, i.e. `H0: max_{k=1..36} E[d_k] ≤ 0`,
> against `H1: max_{k=1..36} E[d_k] > 0`.

Type discipline: `d_k` is a population parameter (an expectation), not the sample mean. The
test statistic in §2 is the studentized sample estimator of the family maximum. Rejection of H0
means at least one cell has positive expected benchmark-relative performance that the joint null
distribution cannot explain as the maximum of 36 correlated mean-zero series.

---

## 2. Test Statistic and Method

### 2.1 N2 normalization decision (the mathematician owns this)

**DECISION: studentize uniformly.** The per-cell statistic is

```
T_k = sqrt(n) * mean_hat(f_k) / omega_hat_k
```

and the family statistic is the maximum over cells, `T_SPA = max_{k=1..36} T_k`. Raw-mean SPA
is **rejected**.

**Rationale (this is the binding answer to finding N2).** The carry_momentum variant's per-bar
return std is ~1000× smaller than the other five variants (a correct consequence of its
config `risk_per_trade = 0.007` plus fixed pip-cost drag, pinned at
`carry_universe_matrix.py:284-293,429-437`). Under a **raw** mean statistic `max_k sqrt(n)·mean(f_k)`,
that scale disparity makes every carry_momentum cell a near-null column: its mean is ~1000× smaller
in absolute terms, so it can never be the family argmax and contributes nothing — the cell is silently
neutralized, which is a multiplicity/representation defect, not a design choice.

Studentization removes this by construction. `T_k` is **scale-invariant**: replacing
`f_{k,t} → c·f_{k,t}` for any constant `c > 0` multiplies both `mean_hat(f_k)` and `omega_hat_k`
by `c`, leaving `T_k` unchanged. (Type note: this is exact for any positive scalar rescaling of a
single column, because `omega_hat_k` is a positive-homogeneous-degree-1 functional of the column —
a HAC standard error.) Therefore the 1000× std gap does **not** distort the family maximum after
studentization: carry_momentum competes on its t-ratio, the same currency as every other cell. This
is also the standard Hansen (2005) SPA specification (Hansen 2005, §2-3: statistic
`T^SPA = max_l sqrt(n)·d_bar_l / omega_hat_l`), so studentizing is both the scale-correct and the
canonical choice. No separate treatment of carry_momentum is needed; the normalization handles it
by design.

### 2.2 The variance estimator ω̂_k (specified exactly)

`omega_hat_k` is the **heteroskedasticity-and-autocorrelation-consistent (HAC) Newey–West standard
error of the cell mean**, with a **Bartlett (triangular) kernel** and bandwidth tied to the
bootstrap block length. Verified at `reality_check.py:850-864` (`_hac_se`):

```
gamma_0       = (1/n) * sum_t (x_t - x_bar)^2
gamma_lag     = (1/n) * sum_t (x_t - x_bar)(x_{t-lag} - x_bar)
h             = max(L - 1, 1)                     # Bartlett bandwidth = block_length - 1
s2            = gamma_0 + 2 * sum_{lag=1..h} (1 - lag/(h+1)) * gamma_lag
s2            = max(s2, 1e-12)                     # negative-variance clamp (small-sample guard)
omega_hat_k   = sqrt(s2 / n)
```

where `L` is the Politis–White block length of §3. The Bartlett weights `w_lag = 1 - lag/(h+1)`
guarantee a positive-semidefinite long-run variance (Newey–West 1987), so `s2 ≥ 0` up to the
finite-sample correction; the `max(s2, 1e-12)` clamp is the documented small-sample fail-safe, not
a routine path.

### 2.3 Zero / near-zero-variance column guard (frozen)

Two guards are frozen, both already implemented:

1. **HAC-SE floor (`reality_check.py:868`):** after computing all `omega_hat_k`, any
   `omega_hat_k < 1e-12` is set to `1e-12` before the division `T_k = sqrt(n)·mean_hat/omega_hat_k`.
   This makes `T_k` finite for any column whose long-run variance underflows (e.g. a cell with no
   trades → constant equity → `mean_hat ≈ 0` and `omega_hat ≈ 0`): such a column resolves to a
   bounded, effectively-null `T_k` rather than `0/0 = NaN` or `+Inf`. The same floor is applied to
   every bootstrap-replicate SE (`reality_check.py:918,924,930`), so the null distribution is
   computed consistently.
2. **No-trade / data-insufficiency cells never reach the statistic silently.** A cell that produces
   `< 2` equity-curve points, mid-series NaN, or a hard rate-data failure is dropped *before*
   matrix assembly with a **structured logged reason** (`carry_universe_matrix.py:519-530,680-715`),
   and a code error (KeyError/TypeError/ConfigError) is re-raised loud — never silently dropped.
   Any drop is recorded; per the no-silent-exclusion constraint, an unlogged drop voids the FWER
   guarantee. **Frozen rule:** the realized `K` entering the max-statistic is whatever survives this
   logged filter; if `K < 36` the dropped cells and reasons are part of the result record.

> **Caveat (typed as numerical, routed to quant-developer):** the studentized statistic is
> scale-invariant *in exact arithmetic*. The HAC-SE clamp `1e-12` is an absolute floor, not a
> relative one. For carry_momentum, `omega_hat_k` is ~1000× smaller than for the other variants but
> is expected to remain well above `1e-12` (its returns are tiny but non-degenerate). If any
> carry_momentum cell's `omega_hat_k` actually approaches `1e-12`, the floor would clip it and break
> scale-invariance for that cell — turning it spuriously null. This must be confirmed numerically
> before the run (see routed question). The fix, if needed, is a relative floor
> (`omega_hat_k = max(omega_hat_k, eps_rel * |mean_hat_k|)` or a per-column relative epsilon), which
> would be a pre-freeze code change, not a post-freeze one.

### 2.4 Method, recentering, and the two p-values

**Primary statistic and decision p-value: Hansen (2005) SPA "consistent".** Implemented in
`r5c_hansen_spa` (`reality_check.py:755-974`). The joint null is imposed by **recentering each
column by its thresholded mean** `mu_bar_k = max(0, mean_hat(f_k))` (`reality_check.py:895`): only
cells with apparent positive performance are recentered to their mean, poor cells are left at their
(negative) sample mean — Hansen's consistent recentering, which removes spurious near-positive
winners from the least-favourable configuration and is strictly more powerful than White's RC when
the universe is dominated by near-zero/negative cells (Hansen 2005, §3.2). The SPA lower
(recenter all by `mean_hat`) and upper (recenter none) bounds are also emitted
(`reality_check.py:898-901,921-931`) but are diagnostic, not the decision statistic.

**Conservative cross-check p-value: White (2000) Reality Check**, computed off the **same**
bootstrap draws (`reality_check.py:874-877,938-939`). RC is recentered by the full sample mean
(`boot - means`, White 2000 eq. 3.7 stationary-bootstrap variant) and is **not** studentized
(`t_rc_obs = max_k sqrt(n)·mean_hat(f_k)`). It is expected and documented that
`white_rc_pvalue ≥ pvalue_consistent`; that ordering is a property of the two nulls, not a
contradiction. RC is reported for transparency; **the pre-registered decision rule is SPA-consistent
primary.**

**Resampling: JOINT same-block stationary bootstrap.** Each replicate resamples the full
36-dimensional per-bar return *vector* in lockstep — the same block draw selects the same time
indices across all cells (`reality_check.py:882-890`, `_joint_bootstrap_once` stacks
`pair_returns[(start+j) % T]`, i.e. whole rows). This preserves the **cross-sectional dependence**,
which is the dominant dependence in this universe (the 36 cells are re-parameterizations/ablations of
ONE rate-differential idea; effective independent dimension ≈ 1-4). Cells are **never** bootstrapped
independently. The bootstrap is the stationary bootstrap of Politis–Romano (1994): block start
uniform on `[0, T)`, block length `Geometric(p = 1/L)`, circular wrap-around.

**p-value formula (both tests):** `p = (1 + #{S_b ≥ S_obs}) / (B + 1)` (`reality_check.py:941-945`),
the +1/+1 convention that prevents the `p = 0` artifact.

---

## 3. Block Length

**Frozen rule: Politis–White (2004) + Patton–Politis–White (2009) automatic data-driven selection,
applied to the joint matrix via `politis_white_block_length_multivariate`, aggregated as the MAX
across the 36 columns, with guard `L ≥ 1`.** Verified at `reality_check.py:313-351`: the multivariate
function computes `politis_white_block_length(X[:, j])` for every column `j` and returns
`L_max = max_j L_j`, then `r5c_hansen_spa` takes `actual_block_length = max(1, ceil(L_max))`
(`reality_check.py:829-835`). The max-across-cells aggregation is the conservative choice: it guarantees
**every** cell's serial dependence is covered by a block at least as long as its own optimal block, so
no cell is under-blocked. `L` is computed from the actual realized series at run time — it is **not**
assumed from the prior near-white ACF proxy finding (which was a single-series proxy and may not hold
for the vol-targeted or FRED-conditioned variants).

The univariate Politis–White estimator (`reality_check.py:119-310`) implements the canonical PW2004/PPW2009
algorithm and has been adjudicated against the R `blocklength::pwsd` reference to <0.5% (WN → 2.392,
AR(0.5) → 7.164, AR(0.9) → 19.963): de-mean; biased autocovariances `R(k)`; data-driven lag cut-off
`m_hat` via the PPW2009 consecutive-lags flat-top threshold `c·sqrt(log10(T)/T)` with
`c = qnorm(0.975) = 1.959963984540054` and `K_N = max(5, ceil(log10(T)))`; band `M = min(2·m_hat,
ceil(sqrt(T)) + K_N, T-1)`; flat-top window `lambda(u)`; `L_opt = (2·G_hat^2 / D_SB)^(1/3)·T^(1/3)`;
upper cap `b_max = ceil(min(3·sqrt(T), T/3))`; lower guard `L ≥ 1`. Degenerate guards: constant column
(`R0 < 1e-14`) → `L = 1`; near-zero `g_hat`/`d_hat` → `L = 1`. **A near-zero-variance carry_momentum
column therefore returns `L = 1` and cannot inflate `L_max`** — it is dominated by the
genuinely-autocorrelated variants, which is correct.

**Why temporal `L` is second-order here (frozen rationale).** The prior materiality sweep over
`L ∈ {1, 2, 3, 5}` produced **0/10 verdict flips** — the SPA decision is insensitive to the temporal
block length over the plausible range. The reason is structural: in this universe the **cross-sectional**
dependence dominates the **temporal** dependence (carry strategy *returns* are near-white despite
persistent positions; ACF lag-1 ≈ -0.003, `|ACF| < 0.017` to lag 60). The joint same-block resampling
captures the dominant (cross-sectional) dependence regardless of `L`; `L` only tunes the second-order
temporal correction. We still compute `L` from the data (no hardcoded value) for correctness and
auditability, but the decision does not hinge on it.

---

## 4. Bootstrap Parameters

**Frozen `K = 5000` bootstrap resamples.** (The implementation default is `B = _B = 10_000`,
`reality_check.py:49`; the frozen run passes `B = 5000` explicitly — comfortably above the `K ≥ 2000`
minimum and within the scope's preferred `5000-10000` band, while keeping the joint
36-column × 5000-replicate × per-replicate-HAC cost bounded for a one-shot run.)

**Monte-Carlo standard error of a bootstrap p-value:** `MC-SE = sqrt(p(1-p)/K)`. At the decision
boundary `p = 0.05`:

| K | MC-SE at p=0.05 | Verdict |
|---|---|---|
| 200 | `sqrt(0.05·0.95/200) = 0.0154` | **PROHIBITED** — straddles the 0.05 threshold; the decision would flip on bootstrap noise alone |
| 2000 | `sqrt(0.05·0.95/2000) = 0.0049` | minimum acceptable |
| **5000 (frozen)** | `sqrt(0.05·0.95/5000) = 0.0031` | **frozen** |
| 10000 | `sqrt(0.05·0.95/10000) = 0.0022` | acceptable upper |

`K = 200` is **explicitly ruled out**: its MC-SE (0.0154) is larger than a third of the entire
distance from `p = 0.05` to `p = 0`, so a borderline result could not be distinguished from noise.
`K` controls p-value *resolution* (Monte-Carlo precision), **not** statistical power; power is set by
`n` and the true effect (see §6).

**RNG seeding (frozen, deterministic, logged).** RNG = `numpy.PCG64` (`reality_check.py:825`).
Child seeds are derived from a single `master_seed`: R5c uses `master_seed + 2`
(`reality_check.py:824`). **Frozen `master_seed = 576746` (the trial-id numeric stem).** The seed,
RNG identifier (`"numpy.PCG64"`), and numpy version are logged on every invocation
(`reality_check.py:359-367`, `_log_seed_info`). The run is fully reproducible from the frozen seed +
the frozen code commit; both go in the freeze-receipt.

---

## 5. Error Control

- **α = 0.05** (one-sided; H1 is `max_k E[d_k] > 0`). `_ALPHA = 0.05`, `reality_check.py:48`.
- **Family-wise error rate (FWER), strong control, via the max-statistic** over the single pooled
  family of (up to) 36 cells. The max-statistic SPA construction controls
  `P(reject H0 | H0 true) ≤ α` jointly over all 36 cells — the joint same-block bootstrap null *is*
  the distribution of `max_k T_k` under the least-favourable configuration, so no separate Bonferroni
  or Romano–Wolf step is layered on top. One pooled family ⇒ one p-value ⇒ one decision.
- **FWER, not FDR (frozen rationale).** The firm decision is a **single binary** CONTINUE/WIND-DOWN.
  The cost object is therefore `P(any false CONTINUE) = P(at least one false rejection) = FWER`. FDR
  controls the *expected proportion* of false discoveries — the right object when you will act on a
  *set* of discoveries (e.g. sizing a portfolio of many strategies), which is not the case here. A
  single false "this family has alpha" rejection is the entire harm, so FWER is the correct control.

---

## 6. Power and Limitations

**Class-level power estimate: ≈ 20–35%** at a true per-cell **annualized** Sharpe of ≈ **0.30**, over
the available daily sample, under FWER control across the 36 cross-correlated cells.

**Derivation / source and its assumptions.** The figure originates from the ratified scope
(`CONSENSUS_2026-06-02_r5_scope.md` §R5 test design and the NHT dissent §1) and is confirmed here.
The ~0.30 Sharpe is **annualized** (confirmed: the only economically plausible reading — a per-bar
daily 0.30 would be a trivially-significant ~4.8 annualized Sharpe and the framing would be wrong).
Sketch of the back-of-envelope that yields it: a per-cell annualized Sharpe of 0.30 over `n ≈ 4186`
daily bars (the joint inner-join index length; confirm exact `n` against the realized matrix at run
time) implies a single-cell t-statistic of order `t ≈ SR_annual · sqrt(n / 252) ≈ 0.30 · sqrt(4186/252)
≈ 0.30 · 4.08 ≈ 1.22` — already **below** the ordinary 1.96 two-sided threshold *before* any
multiplicity correction. Imposing FWER over ~36 cross-correlated cells (effective independent
dimension ≈ 1-4) raises the rejection bar further, leaving rejection probability in the ~20-35% band.
**Assumptions this rests on:** (i) the true edge, if any, is ~0.30 annualized and roughly constant
across the OOS window; (ii) returns are approximately stationary so the block bootstrap null is valid;
(iii) effective independent dimension 1-4 (cross-sectional correlation is high). The number is a
class-level order-of-magnitude, not a precise operating characteristic; an exact power curve would
require a Monte-Carlo under an assumed alternative (routed to quant-developer if the firm wants it,
but **not required** for the decision).

**Binding statement (frozen).** Low power makes a **non-rejection (`p ≥ 0.05`) UNINFORMATIVE as
evidence of no-edge** — it is *not* proof that carry alpha is zero. **However, the firm action under
non-rejection is WIND-DOWN regardless.** Power does *not* license a third "inconclusive, keep
spending" outcome. The honest reading of an underpowered non-rejection is "no *distinguishable*
class-level alpha at the achievable power," and combined with the firm's zero validated OOS survivors,
that maps to **WIND-DOWN**. This is pre-committed before any draw.

---

## 7. Snooping Treatment (method requirements — co-signed with HoQR)

These are the firm's longest-studied strategies on the 2010–2026 data; that spent selection is sunk
and is **not** retroactively controlled by a prospective Reality Check on the same data (the SPA/RC
null controls only the 36 looks pre-registered here, not the prior trial history). A face-valid clean
`p` therefore requires **one** of the two admissible methods below. The mathematician signs the method;
HoQR proposes the concrete window/inputs.

### 7.1 Admissible Method A — genuine post-development hold-out (preferred)

A window qualifies as a genuine hold-out **iff all** of the following hold:
1. The window's bars were **generated after** the last development/parameter-selection touch of **every
   one of the 6 variants** (no variant's design, parameters, or feature choices were informed by any bar
   in the window). HoQR must attest this per-variant with dates.
2. The window was **never** used in any prior carry trial, plot, or metric the firm acted on.
3. The window is frozen in the pre-reg **before** any R5 draw, by date range and bar count.
4. The window has `n ≥` enough bars for the block bootstrap to be valid (`n` comfortably exceeds
   `L_max`; in practice `n` in the hundreds+).

If a window meeting (1)-(4) exists, R5 runs on that window **only**, and no haircut is required because
the snooping is genuinely escaped. **I will co-sign HoQR's window proposal exactly when HoQR provides
the per-variant last-development-date attestation establishing (1) and the never-used attestation
establishing (2).** Absent that attestation, Method A is not available and Method B applies.

### 7.2 Admissible Method B — deflated-Sharpe-style haircut (fallback when no clean hold-out exists)

If R5 must run on the full snooped sample, the cell Sharpe must clear a **selection-deflated**
threshold before its `p` is treated as face-valid. Use the Bailey–López de Prado (2014) Deflated
Sharpe Ratio. The frozen benchmark (expected maximum Sharpe under the null of zero true skill across
`N` trials) is:

> `SR0 = sqrt(Var[SR_n]) · [ (1 - euler_gamma) · Z^{-1}(1 - 1/N) + euler_gamma · Z^{-1}(1 - 1/(N·e)) ]`

where `Z^{-1}` is the inverse standard-normal CDF, `euler_gamma ≈ 0.5772` is the Euler–Mascheroni
constant, `Var[SR_n]` is the **variance of the Sharpe estimates across the `N` trials**, and `N` is the
number of **independent** trials. The Deflated Sharpe Ratio then evaluates the observed best Sharpe
against `SR0` using the DSR test statistic that incorporates the return series' **skewness and excess
kurtosis** and sample length (Bailey–López de Prado 2014, eqs. for `SR0` and `DSR`).

**Frozen inputs — the `N` decision (this is the load-bearing call).** `N` must be the **honest
effective number of independent trials**, and the two candidate sources are explicitly distinguished:
- **Org-wide `trials.jsonl` count (currently 37):** this is the *total* trial count and **overstates**
  the independent looks on the carry family specifically — it includes non-carry trials and counts
  correlated re-parameterizations as if independent.
- **Honest-N registry (the correct input):** `N` = the number of **effectively independent** carry
  looks. Given the scope finding that the 36 cells have effective independent dimension ≈ 1-4 and that
  the 6 variants are re-parameterizations/ablations of ONE rate-differential idea, the honest `N` for
  the carry family is **small** (single-digit), not 36 and not the org-wide total.

> **Frozen rule:** if Method B is used, `N` is taken from the **honest-N registry of independent carry
> looks**, NOT the raw `trials.jsonl` line count. `Var[SR_n]` is computed over those same independent
> looks' Sharpe estimates. Using the inflated raw trial count would *over*-deflate (too conservative,
> understating any real edge); using `N = 1` would *under*-deflate (snooping uncontrolled). The
> honest-N registry is the pre-committed source. The exact `N` value and `Var[SR_n]` are an input HoQR
> supplies and the mathematician signs; they are frozen in the pre-reg before any draw.

**Condition under which I co-sign HoQR's window proposal:** I co-sign when HoQR's proposal specifies,
in frozen form, **either** (A) a window with the per-variant post-development + never-used attestation
of §7.1, **or** (B) the full-sample run *plus* the honest-`N` value, its `Var[SR_n]`, and the DSR
threshold computed from the formula above. "We used all available data" with no hold-out and no haircut
is **not** signable.

---

*Mathematician sign-off applies to §1, §2, §3 (co-signed: quant-developer), §4, §5, §6 (co-signed: NHT),
§7 (co-signed: HoQR). Pinned to the freeze-receipt git commit of reality_check.py and
carry_universe_matrix.py.*
