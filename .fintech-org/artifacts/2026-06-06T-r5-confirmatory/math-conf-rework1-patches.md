# Mathematician Rework 1 — ANCHOR/REPLACEMENT Patches
# Document: `references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md` (PART II)
# Subtask: r5-confirmatory-math-rework1 / r5-confirmatory-2026-06-06:phase1:task1.0
# Author: Quantitative Mathematician
# Date: 2026-06-06
# Findings addressed: F-002 (major — operative look-rule stated two non-equivalent ways), F-008 (observation — wording)

---

## Arithmetic establishing the operative look-2 threshold (F-002)

The operative look-j rule elected is:

> **Reject H0 at look j iff the look-j bootstrap p ≤ Φ(−z_j)**

Two-line arithmetic:

```
Look 1:  Φ(−z₁) = Φ(−2.537988) = 0.005575   [≡ incremental spend₁; the two agree at look 1]
Look 2:  Φ(−z₂) = Φ(−1.662107) = 0.048246   [NOT equal to incremental spend₂ = 0.044425]
```

The look-1 threshold happens to coincide numerically with the incremental spend (0.005575 in both
cases) because at look 1 the OBF cumulative spend IS Φ(−z₁) by construction. At look 2 these
diverge: the incremental spend 0.044425 corresponds to the NOMINAL conditional boundary
Φ⁻¹(1 − 0.044425) = 1.701 — a different object from the bivariate-joint z₂ = 1.662107. The
alpha-exact operative threshold at look 2 is Φ(−1.662107) = 0.048246 (scipy-exact).

The incremental-spend framing is retained ONLY at look 1 (where it is numerically correct) and
is REPLACED at look 2 by the Φ(−z₂) formulation.

---

## PATCH F-002-A — Boundary table: look-2 `reject H0 if` column

**Location:** PART II §3.3, boundary table, look-2 row

**ANCHOR (verbatim):**
```
| 2 | 1.00 | 0.044425 | **z₂ = 1.662107** (bivariate joint, scipy-exact) | bootstrap-`t` look-2 p ≤ 0.044425 |
```

**REPLACEMENT:**
```
| 2 | 1.00 | 0.044425 | **z₂ = 1.662107** (bivariate joint, scipy-exact) | bootstrap-`t` look-2 p ≤ **0.048246** (= Φ(−1.662107); see §3.3 note) |
```

**Correction:** The `reject H0 if` column for look 2 must use Φ(−z₂) = 0.048246, not the
incremental spend 0.044425. These are not equivalent: 0.044425 is the incremental alpha-budget
spent by the look-2 marginal; 0.048246 = Φ(−1.662107) is the actual one-sided p-value
corresponding to the bivariate-joint critical value z₂. Applying 0.044425 as the bootstrap-p
threshold is equivalent to using the nominal conditional boundary z = Φ⁻¹(1 − 0.044425) = 1.701,
which is stricter than the joint-design z₂ = 1.662107 and is NOT alpha-exact for the joint design.

---

## PATCH F-002-B — Operative-rule prose: replace "incremental spend" framing with Φ(−z_j)

**Location:** PART II §3.3, paragraph immediately following the boundary table (the closing
parenthetical sentence beginning "The boundaries are applied…")

**ANCHOR (verbatim):**
```
The boundaries are applied **on the bootstrap p-value scale** (Section 1.4): reject at look `j` iff the look-`j` bootstrap p ≤ the incremental spend `α*(t_j) − α*(t_{j-1})`. (Equivalently, on the z-scale: `t_obs ≥ z_j`. The z₂=1.662107 is the bivariate joint-exact final critical value — derived by solving P(Z1≥z1 OR Z2≥z2|H0)=0.05 exactly via scipy.stats.multivariate_normal.cdf; confirmed by independent dblquad quadrature and 5 M-sample MC. **The bootstrap p is the operative test; the z-boundaries are the equivalent reference.**
```

**REPLACEMENT:**
```
The boundaries are applied **on the bootstrap p-value scale** (Section 1.4): reject at look `j` iff the look-`j` bootstrap p ≤ **Φ(−z_j)** — i.e. look-1 threshold Φ(−2.537988) = 0.005575 and look-2 threshold Φ(−1.662107) = 0.048246. (Equivalently, on the z-scale: `t_obs ≥ z_j`.) **The z-boundaries z₁, z₂ are the PRIMARY operative reference; the bootstrap p ≤ Φ(−z_j) formulation is the p-scale equivalent.**

> **Note (F-002 correction):** The incremental spend at look 2 is 0.044425 (= α*(1.0) − α*(0.5) = 0.050000 − 0.005575). This is the alpha-BUDGET consumed by look 2, not the look-2 p-threshold. The p-threshold Φ(−z₂) = Φ(−1.662107) = 0.048246 corresponds to the bivariate joint-exact critical value and is the correct operative threshold. Comparing the look-2 bootstrap p against 0.044425 would correspond to using the nominal conditional boundary Φ⁻¹(1 − 0.044425) = 1.701, which is strictly MORE conservative than z₂ = 1.662107 and is not alpha-exact for this joint group-sequential design. The two formulations are equivalent ONLY at look 1, where Φ(−z₁) = Φ(−2.537988) = 0.005575 = spend₁ by construction.
```

---

## PATCH F-008-A — §1.3 wording: soften "bit-for-bit" mirrors R5 SPA studentization

**Location:** PART II §1.3, sentence beginning "This mirrors the R5 SPA studentization…"

**ANCHOR (verbatim):**
```
This mirrors the R5 SPA studentization (`r5c_hansen_spa`/`select_k_star_studentized`, `r5_decision.py:104-109`) bit-for-bit, so the confirmatory `t` is the single-cell restriction of the R5 family statistic — the same `T_k` machinery, evaluated on one column on clean data.
```

**REPLACEMENT:**
```
This uses the same statistic family and HAC conventions as the R5 SPA studentization (`r5c_hansen_spa`/`select_k_star_studentized`, `r5_decision.py:104-109`) — the same `T_k` machinery, evaluated on one column on clean data — but with **univariate** Politis–White block-length selection (`reality_check.politis_white_block_length` applied to the single hold-out series), whereas R5 used multivariate PW across 36 columns; the confirmatory is single-series.
```

**Correction (F-008):** R5's `politis_white_block_length` was applied across the 36-column carry
matrix (multivariate context). The confirmatory applies the same function to a single hold-out
series (univariate context). The statistic form, HAC kernel, and recentering convention are
identical; only the dimensionality of the block-length input differs. "Bit-for-bit" is inaccurate
for this reason and is replaced with a one-sentence honest statement of the relationship.

---

## Summary

| Patch ID | Finding | Location | Nature |
|----------|---------|----------|--------|
| F-002-A | F-002 | PART II §3.3 boundary table, look-2 row | Fix `reject H0 if` column: 0.044425 → 0.048246 = Φ(−1.662107) |
| F-002-B | F-002 | PART II §3.3 operative-rule prose paragraph | Replace incremental-spend operative framing with Φ(−z_j) election + note |
| F-008-A | F-008 | PART II §1.3 last sentence of Guard block | Soften "bit-for-bit" to "same statistic family and HAC conventions … univariate block-length" |

**Total patches: 3**

---

*Authored by: Quantitative Mathematician*
*Trial: f2fb41fd / r5-confirmatory-2026-06-06:phase1:task1.0*
