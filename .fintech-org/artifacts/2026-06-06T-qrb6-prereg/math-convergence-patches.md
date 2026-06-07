# math-convergence-patches.md — Mathematician Convergence Patch Set (trial fa0f982a)

**Track:** `qrb6-prereg-2026-06-06:phase1:task1.0`
**Trial:** `fa0f982a`
**Author role:** Quantitative Mathematician
**Date:** 2026-06-06
**Subtask ref:** `qrb6-prereg-math-convergence`
**Artifact:** `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/math-convergence-patches.md`

---

## Patch Provenance — Which Earlier Patches STAND and Which Are Superseded

### STANDS (unchanged, apply as written in math-rework1-patches.md)

**PATCH PR-04** — both sub-patches — the boundary precision fix in §4.2 and its companions (RULE 1/2/3/4 inequalities, exhaustiveness gloss, §4.3 table row split) are **UNAFFECTED** by the filtration convergence. They are a pure boundary-convention fix (strict vs non-strict inequality at 0.0478/0.0522) that is filtration-invariant. Apply PR-04 exactly as written in math-rework1-patches.md. Do NOT duplicate those patches here.

### SUPERSEDED (do NOT apply from math-rework1-patches.md)

**PATCH NHT-F5 COMPANION (the new §4.4 block in math-rework1-patches.md)** is entirely superseded before it was ever applied. That §4.4 text froze F_{D-1} filtration, excluded bar D from the sign, and pinned the degenerate convention as ret_{D-1}=0 → sign_align_e=+1. The DEBATE ROUND-1 CONVERGENCE (debate-r1-math.yaml) retracts that ruling: bar-D signed-product construction is the correct alignment for the registered hypothesis; F_{D-1} was considered and rejected. The **FINAL §4.4 text** is authored directly below as this file's primary output. No intermediate state of the old §4.4 should be applied.

---

## PATCH C-01 — PART II §1.1 sign_align_e description (supersede the "pre-decision drift direction" phrase)

### Problem

PART II §1.1 currently reads:

> `sign_align_e` is the a-priori directional hypothesis (**pre-decision drift direction** registered ex-ante per the QR hypothesis; NO data-driven sign fit).

The phrase "pre-decision drift direction" is ambiguous and was written when the F_{D-1} filtration was still the mathematician's provisional ruling. Under the converged bar-D construction, `sign_align_e = sign(close(D) − close(D−1))` — the post-announcement reaction direction. "Pre-decision drift direction" now points at the dead component (§2.3); the text must be corrected to "post-announcement reaction direction."

### ANCHOR (unique in the document)

```
`sign_align_e` is the a-priori directional hypothesis (pre-decision drift direction registered ex-ante per the QR hypothesis; NO data-driven sign fit). The **unit of observation is the deduped bank-event-day**
```

### REPLACEMENT

```
`sign_align_e` is the a-priori directional hypothesis (post-announcement reaction direction — specifically `sign(close(D) − close(D−1))` on the bank-event's mapped leg, as pinned in §4.4 and §5.0; NO data-driven sign fit). The **unit of observation is the deduped bank-event-day**
```

---

## PATCH C-02 — PART II §1.2 null statement (add the signed-product form of the estimand)

### Problem

PART II §1.2 currently states the null as `H0: E[r_e] ≤ 0` where `r_e` was defined in §1.1 as `sign_align_e · (cumulative net-of-cost return)`. The definition is correct in principle, but the footnote in §1.2 reads "direction fixed a-priori from the registered drift hypothesis" — a phrase that echoes the dead pre-drift component. Moreover, the converged position (debate-r1-math.yaml §step4_what_genuinely_changes) requires explicitly pinning that the null is UNCONDITIONAL on the signed product, not a conditional null: `H0: E[y_e] ≤ 0` where `y_e = sign(close(D) − close(D−1)) · R_post,e`. This phrasing must appear once in the hypothesis statement and be echoed identically in §4.4, per the converged design.

### ANCHOR (unique in the document)

```
> **H0:** `E[r_e] ≤ 0` (the event-window strategy has no positive net edge across deduped bank-events).
> **H1:** `E[r_e] > 0`.

One-sided, total `α = 0.05` (R5/confirmatory precedent; direction fixed a-priori from the registered drift hypothesis). The post-announcement reversal sub-test is framed per NHT C2 as "directional bias statistically distinguishable from BOTH 0% and 100%" — NO 65% point target enters any frozen field (no_65pct_point_target).
```

### REPLACEMENT

```
> **H0:** `E[y_e] ≤ 0` (the signed-product event strategy earns no positive net edge on average across deduped bank-events — an UNCONDITIONAL null on the per-event signed-product scalar, not a conditional null conditioned on the direction of bar D).
> **H1:** `E[y_e] > 0` (the post-announcement reaction continues through the K_post=2 window on average, net of costs).

where the tested quantity is the **signed-product event return**:

> `y_e = sign(close(D,e) − close(D−1,e)) · R_post,e`

and `R_post,e` = the bank-event equal-weight net-of-cost cumulative return **close(D) → close(D+2)** — i.e. the post-decision return on the responsive pairs (§3.2), entered at bar D+1 under `entry_delay_bars=1`, position held during bars D+1 and D+2. The symbol `r_e` used in §1.3–§1.4 is `y_e` under this definition; notation is unified here from §1.2 forward. For the degenerate case `close(D) = close(D−1)` exactly: `sign_align_e = 0`, position FLAT, event EXCLUDED from the realized return (its event-day still counts as a block-day for bootstrap block construction; see §4.4.3).

One-sided, total `α = 0.05` (R5/confirmatory precedent; direction fixed a-priori from the post-announcement continuation hypothesis; §4.4 pins the signal/execution separation). The post-announcement reversal sub-test is framed per NHT C2 as "directional bias statistically distinguishable from BOTH 0% and 100%" — NO 65% point target enters any frozen field (no_65pct_point_target).
```

---

## PATCH C-03 — FINAL §4.4 insertion (Signal/Execution Separation Contract — supersedes the NHT-F5 block in math-rework1-patches.md entirely)

### Placement

Insert as a new section **§4.4** immediately after the existing §4.3 ("Scenario-B auto-activation arithmetic") in PART II, at the same location as the original NHT-F5 patch specified. The ANCHOR below is the text AFTER which §4.4 is inserted; the `---` separator and `## 5.` heading remain; the new section is inserted between them, exactly as the original NHT-F5 patch specified.

### ANCHOR (insertion point — the text AFTER which §4.4 is inserted; identical to the NHT-F5 patch anchor)

```
The DSR benchmark `SR0_pp_sel` and `N_sel` are n-INVARIANT (selection charge does not depend on the event count). ONLY `kill_switch_threshold` moves with n (Section 6 derivation for both). Activation = swap the n-pair and read the pre-frozen threshold; nothing is recomputed live.

---

## 5. Power — FROZEN (shown work)
```

### REPLACEMENT (the ANCHOR is kept; the new §4.4 is inserted between the `---` separator and the `## 5.` heading)

```
The DSR benchmark `SR0_pp_sel` and `N_sel` are n-INVARIANT (selection charge does not depend on the event count). ONLY `kill_switch_threshold` moves with n (Section 6 derivation for both). Activation = swap the n-pair and read the pre-frozen threshold; nothing is recomputed live.

---

## 4.4 Signal/Execution Separation Contract (NHT-F5 companion) — FROZEN

This section pins the signal/P&L boundary for the `sign_align_e` rule. It is the **mathematician's contract for the NHT-F5 companion**: the QR pins the sign-alignment rule in §5.0; I state what that rule must satisfy to preserve the hypothesis stated in §1.2 and the filtration this statistic assumes. **This section was authored after DEBATE ROUND-1 CONVERGENCE (artifact: `debate-r1-math.yaml`); it replaces the earlier NHT-F5 companion block from math-rework1-patches.md (the F_{D-1} ruling), which is SUPERSEDED and was never applied.**

### 4.4.1 Filtration assumption and signal/execution boundary (FINAL, bar-D)

The no-lookahead invariant (§4.3, `entry_delay_bars = 1`) and the daily-bar timestamp convention (§4.1) jointly fix the signal/execution boundary.

**FROZEN filtration ruling (bar-D signed product):**

> `sign_align_e = sign(close(D) − close(D−1))` where `D` is the decision-reflecting bar (§4.1). The signal is determined from the CLOSE of bar D — F_D-measurable. Entry executes at bar D+1 under `entry_delay_bars=1`. The post-window cumulative return (the P&L) runs from D+1 forward: bars D+1 and D+2 (K_post=2). No bar is simultaneously a sign-input and a realized-return bar without the mandatory `entry_delay_bars` shift.

**Why the bar-D return is the SIGNAL, not the P&L:** bar D's close-to-close return `close(D)−close(D−1)` captures the initial post-announcement market reaction. This return is consumed at signal-formation time — it is the input to `sign_align_e`. The firm's engine records P&L only from the entry bar D+1 onward; bar D's own return is therefore a signal variable, not a P&L variable. The signal/execution separation is enforced by `entry_delay_bars=1` and is auditable via the sacred `test_no_lookahead` test (§4.3).

**Engine semantics (single authoritative phrasing, echoed identically in §5.0 and §1.2):** signal computed at bar D (F_D-measurable, no look-ahead into future bars); entry at D+1; position held during bars D+1 and D+2; exit at close of D+2. The K_post=2 net-of-cost cumulative return from close(D) to close(D+2) is the P&L window. This phrasing supersedes any alternative window description (e.g., "[D+1 close … D+K_post close]") that might appear in earlier draft artifacts; the engine executes the entry_delay_bars=1 shift mechanically, and the return is close(D)→close(D+2) as a result.

**Entry bar information check:** at entry bar D+1, close(D) is observable. The signal `sign_align_e` uses only data available through close(D) — strictly in the past relative to the entry. No future bar (D+1, D+2) is accessed during signal formation. No firm data-access command examines return data before the freeze-receipt is cut (§1.4(1)); once the runner executes, it uses only the frozen signal rule and the engine's entry_delay_bars shift.

### 4.4.2 Why F_{D-1} was CONSIDERED and REJECTED

The alternative filtration — `sign_align_e = sign(ret_{D−1})`, i.e., the direction of bar D−1's return (F_{D-1}-measurable) — was the mathematician's initial ruling (math-rework1.yaml) and was RETRACTED after full economic and statistical review in debate-r1-math.yaml. It is documented here for intellectual honesty and auditability.

**Economic rejection (the decisive reason):** F_{D-1} filtration makes the sign input the direction of the pre-decision drift component — the component §2.3 explicitly declares DEAD post-2015. Using the dead component as the alignment signal would mean the pre-registration tests "the pre-event trend direction (documented essentially disappeared post-2015) predicts post-announcement returns." This is not the hypothesis §2.1 registers (which is "post-decision reaction/reversal structure"). Adopting F_{D-1} would have embedded a ghost signal into the pre-reg while claiming to test the alive post-announcement component.

**Statistical consequence (secondary):** under F_{D-1}, the signed product `y_e = sign(ret_{D−1}) · R_post,e` tests a different economic object — whether the pre-event drift direction predicts post-announcement continuation. The HAC/bootstrap machinery is unchanged between the two filtrations (PW adapts to whichever y_e series is presented; recentering d_e = y_e − mean(y) correctly imposes H0 for either). The statistical mechanics do NOT mandate rejection of bar-D filtration; the economic incoherence does.

**F_{D-1} is not a backup option.** If bar-D reaction data is unavailable (e.g., index lookup failure), the correct action is RULE 0 TECHNICAL_FAILURE — not silent fallback to F_{D-1}, which would silently change the registered hypothesis. The runner must implement the bar-D rule exactly and halt if it cannot be computed.

### 4.4.3 Degenerate-case handling — close(D) = close(D−1) exactly

If bar D's return is exactly zero — i.e., `close(D) = close(D−1)` within floating-point equality — there is no initial reaction to continue or fade. The direction is undefined.

**FROZEN degenerate-case convention:**

> If `ret_D = close(D) − close(D−1) = 0` (floating-point equality), `sign_align_e = 0`, position = FLAT (excluded from the realized return average). The event-day STILL COUNTS as a block-day for bootstrap block construction — it is included in the bank-group's event sequence and contributes to the block structure. It is excluded only from the numerator of the pooled mean (the return series used in `mean(y)` and the bootstrap).

Justification: the frequency of exact-zero daily returns in liquid FX OHLCV data is near-negligible; the convention has no material effect on the statistic. The FLAT/exclusion convention is chosen over +1 (the earlier F_{D-1} ruling's convention) because: (a) a zero reaction on decision day carries no directional information — assigning +1 would introduce an arbitrary long bias; (b) the QR's §5.0 explicitly specifies this FLAT/exclusion convention; (c) the block-day inclusion preserves the block structure's calendar integrity. The convention is frozen ex-ante and may not be changed post-hoc once any event-day data are examined (VOID §1.4(2)).

**Runner implementation requirement:** the runner MUST implement `sign_align_e = numpy.sign(ret_D)` (which returns 0.0 when ret_D = 0.0 exactly), with a branch: if `sign_align_e == 0.0` → position = 0 (FLAT), event-day included in block count but excluded from return average. A unit test on a **synthetic zero-ret_D event** is REQUIRED before the freeze-receipt is cut. (This requirement carries forward from the original §4.4.3; the trigger condition is updated from `ret_{D−1}=0` to `ret_D=0`.)

### 4.4.4 Contract summary (machine-readable)

```yaml
signal_execution_separation_contract:
  filtration: F_D                          # sign_align_e uses information through close of bar D
  bar_D_excluded_from_sign: false          # bar D's own return IS the sign input
  bar_D_is_signal_not_PnL: true            # bar D return consumed as signal; P&L from D+1
  hypothesis_type: unconditional_signed_product_continuation
  H0: "E[y_e] <= 0 where y_e = sign(close(D)-close(D-1)) * R_post,e (unconditional expectation of signed product)"
  H1: "E[y_e] > 0 (post-announcement reaction continues through K_post=2)"
  window_engine_semantics: "signal at bar D (F_D-measurable); entry D+1 (entry_delay_bars=1); P&L bars D+1,D+2; exit close(D+2)"
  degenerate_case_ret_D_eq_zero: position_FLAT_return_excluded_block_included
  degenerate_case_convention: "numpy.sign(ret_D); zero->0.0->FLAT; event in block count, excluded from return average"
  runner_unit_test_required: true          # synthetic zero-ret_D event required pre-freeze
  F_D1_considered_and_rejected: true       # bar D-1 sign rejected: tests dead pre-drift (§2.3); not the registered H1
  supersedes: "math-rework1-patches.md NHT-F5 COMPANION §4.4 block (F_{D-1} ruling, never applied)"
```

---

## 5. Power — FROZEN (shown work)
```

---

## PATCH C-04 — §4.2 "Compatibility flag" marker in §5.0 (close the PENDING sign-off)

### Context

The QR's PATCH A4 in qr-rework1-patches.md introduced §5.0, which includes the following PENDING marker at its end:

> **Compatibility flag (Mathematician sign-off, running in parallel).** … MATH compatibility status: PENDING parallel sign-off.

With the convergence now complete and §4.4 authored above, this PENDING marker must be resolved to CONFIRMED. The patch is against the §5.0 text that PATCH A4 will have inserted.

### ANCHOR (the compatibility-flag sentence at the end of §5.0; unique after A4 is applied)

```
**Compatibility flag (Mathematician sign-off, running in parallel).** This sign rule pins PART II §1.1's `sign_align_e` ("a-priori directional hypothesis, NO data-driven sign fit") to the realized-initial-reaction-continuation function above. It is **NOT** a data-driven *fit* (no free parameter is estimated from returns; the sign is a deterministic function of two adjacent closes), but it IS a function of price, so it is flagged for the Mathematician's compatibility sign-off that (a) the HAC/block-bootstrap studentization in PART II §1.3–§1.4 is unaffected (the bootstrap resamples the already-signed scalar `r_e`), and (b) the one-sided `H1: E[r_e] > 0` remains correct under continuation (a true continuation edge makes the signed return positive in expectation). MATH compatibility status: PENDING parallel sign-off.
```

### REPLACEMENT

```
**Compatibility flag (Mathematician sign-off — CONFIRMED).** This sign rule pins PART II §1.1's `sign_align_e` to the realized-initial-reaction-continuation function `sign(close(D)−close(D−1))`. Mathematician sign-off granted (debate-r1-math.yaml + math-convergence-patches.md §4.4): (a) the HAC/block-bootstrap studentization in PART II §1.3–§1.4 is UNAFFECTED — the bootstrap resamples the already-signed scalar `y_e`; PW adapts to the observed autocorrelation of the y_e series regardless of which sign definition is used; recentering `d_e = y_e − mean(y)` correctly imposes H0: E[y_e]=0 on the bootstrap distribution for any stationary series; (b) the one-sided H1: E[y_e] > 0 is correct under the continuation hypothesis — a true post-announcement continuation edge makes the signed product positive in expectation; (c) the unconditional null H0: E[y_e] ≤ 0 is the correct null on the signed product (not a conditional null conditional on the direction of bar D); the bootstrap recentering imposes it correctly. No change to any frozen constant (N_sel, SR0_pp_sel, DSR gate, kill_switch_threshold, master_seed, K, straddle band) follows from the filtration convergence. MATH compatibility: CONFIRMED (§4.4).
```

---

## Summary of Patches in This File

| Patch | Target | Change |
|-------|--------|--------|
| C-01 | PART II §1.1 `sign_align_e` description | "pre-decision drift direction" → "post-announcement reaction direction (sign(close(D)−close(D−1)))" |
| C-02 | PART II §1.2 null/alternative statement | Rewrite to signed-product form y_e; explicit unconditional null; engine-semantics window pinned; degenerate case stated |
| C-03 | PART II §4.4 (new section insertion) | FINAL §4.4 Signal/Execution Separation Contract — bar-D filtration; F_{D-1} rejection documented; degenerate FLAT/exclusion; machine-readable YAML contract |
| C-04 | §5.0 compatibility flag (after QR PATCH A4) | PENDING → CONFIRMED; full mathematician sign-off on HAC/bootstrap/unconditional-null validity |

**Total patches in this file: 4.**

**Patches from math-rework1-patches.md that STAND (apply unchanged): PR-04 (all sub-patches — §4.2 RULE inequalities, exhaustiveness gloss, §4.3 table row). Do NOT re-apply from this file.**

**Patches from math-rework1-patches.md that are SUPERSEDED (do NOT apply): NHT-F5 COMPANION §4.4 block.**
