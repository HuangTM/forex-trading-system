# math-rework1-patches.md — Mathematician PART II Rework, Batch 1

**Track:** `qrb6-prereg-2026-06-06:phase1:task1.0`
**Trial:** `fa0f982a`
**Author role:** Quantitative Mathematician
**Date:** 2026-06-06
**Subtask ref:** `qrb6-prereg-math-rework1`

Two patches follow. Each patch states: (1) anchor — the EXACT text being replaced (unique in the document); (2) replacement — the exact text that goes in; (3) justification.

---

## PATCH PR-04 — Boundary Precision Fix in §4.2

### Problem Statement

The current §4.2 text contains a three-way inconsistency at the exact boundary p = 0.0478:

- The inequality in RULE 1/2 firing conditions is `p > 0.0478` (strict greater-than).
- The §1.3 gloss on the straddle band lists p ∈ [0.0478, 0.0522] as ambiguous.
- RULE 3 PASS requires "p ≤ 0.0478" (the §4.3 table).

At exactly p = 0.0478: RULE 1 does NOT fire (p is not > 0.0478); RULE 2 does NOT fire; RULE 3 DOES fire (p ≤ 0.0478 and DSR may pass). But the straddle band [0.0478, 0.0522] says this value is MC-indistinguishable from 0.05 and must NOT buy PASS. The rules are simultaneously exhaustive-in-intent but contradictory-in-boundary: p = 0.0478 both "buys PASS" (RULE 3) and "must not buy PASS" (straddle semantics).

### Convention Frozen (R5 precedent: boundary → never-PASS)

- The straddle band is the **CLOSED** interval [0.0478, 0.0522].
- KILL fires iff p **strictly exceeds** 0.0522 (p > 0.0522).
- PASS requires p **strictly less than** 0.0478 (p < 0.0478).
- Any p in [0.0478, 0.0522] — including the exact boundaries — routes to RULE 4 (AMBIGUOUS/catch-all).
- The inequalities are stated once in the rule bodies and echoed identically in the gloss and the §4.3 table. No other representation of thresholds appears anywhere.

### ANCHOR (exact text to be replaced in §4.2)

```
> **RULE 1 — KILL (post-2015 structural-break fail)** (→ the mandatory NHT kill; overrides any aggregate pass). Fires iff RULE 0 did not, AND **`p_post2015 ≥ 0.05 − MC-SE` (i.e. `p_post2015 > 0.0478`)** — the post-2015 sub-window does NOT cleanly reject H0. This is evaluated **BEFORE** any aggregate-pass test, so a strategy alive only pre-2015 is KILLED **regardless of `p_agg` or `DSR`** (NHT: pre-2015-only drift = dead alpha in the current regime; post_2015_subwindow_kill overrides_aggregate_pass: true). Archive QRB-6 RETIRED/FALSIFIED.
>
> **RULE 2 — KILL (aggregate fail)** (→ wind-down). Fires iff RULES 0–1 did not (so post-2015 cleanly passes), AND **`p_agg ≥ 0.05 − MC-SE` (i.e. `p_agg > 0.0478`)** — the full event set does not reject H0. Statistically indistinguishable from chance at the pooled level. Archive RETIRED.
>
> **RULE 3 — PASS** (→ §-action: graduate to a fresh, separately-pre-registered observe-only paper canary; NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification). Fires iff RULES 0–2 did not (so `p_post2015 ≤ 0.0478` AND `p_agg ≤ 0.0478`, BOTH cleanly reject outside the straddle band), AND **`DSR ≥ 0.95`** (selection-deflation gate cleared at `SR0_pp_sel=0.026861`, equivalently aggregate-set ann Sharpe ≥ kill_switch_threshold=1.5883, §2/§6). PASS is NECESSARY-BUT-NOT-SUFFICIENT and authorizes only a confirmatory/observe-only next step.
>
> **RULE 4 — AMBIGUOUS / gate-fail (catch-all, guarantees exhaustiveness)** (→ no-PASS; default to wind-down under full-auto, or a fresh single-structure confirmatory pre-reg if HoQR elects). Fires iff RULES 0–3 did not — i.e. both p's are clean rejections (`< 0.0478`) BUT `DSR < 0.95` (the rejection cannot clear the selection-deflation charge), OR either p sits in the straddle band `[0.0478, 0.0522]` (a boundary p indistinguishable from 0.05 at K=10000 must NOT buy PASS and must NOT be read as a clean KILL). A bare bootstrap rejection that cannot survive deflation, or a straddle, maps here — NEVER to PASS.
```

### REPLACEMENT (exact text to insert in place of the ANCHOR above)

```
> **RULE 1 — KILL (post-2015 structural-break fail)** (→ the mandatory NHT kill; overrides any aggregate pass). Fires iff RULE 0 did not, AND **`p_post2015 > 0.0522`** — the post-2015 sub-window does NOT cleanly reject H0, with the p-value sitting above the MC-indistinguishability straddle band. This is evaluated **BEFORE** any aggregate-pass test, so a strategy alive only pre-2015 is KILLED **regardless of `p_agg` or `DSR`** (NHT: pre-2015-only drift = dead alpha in the current regime; post_2015_subwindow_kill overrides_aggregate_pass: true). Archive QRB-6 RETIRED/FALSIFIED.
>
> **RULE 2 — KILL (aggregate fail)** (→ wind-down). Fires iff RULES 0–1 did not (so post-2015 cleanly rejects), AND **`p_agg > 0.0522`** — the full event set does not reject H0, above the straddle band. Statistically indistinguishable from chance at the pooled level (above even the MC uncertainty envelope). Archive RETIRED.
>
> **RULE 3 — PASS** (→ §-action: graduate to a fresh, separately-pre-registered observe-only paper canary; NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification). Fires iff RULES 0–2 did not, AND **`p_post2015 < 0.0478`** AND **`p_agg < 0.0478`** (BOTH strictly below the straddle band's lower edge — clean rejections with no MC-ambiguity), AND **`DSR ≥ 0.95`** (selection-deflation gate cleared at `SR0_pp_sel=0.026861`, equivalently aggregate-set ann Sharpe ≥ kill_switch_threshold=1.5883, §2/§6). PASS is NECESSARY-BUT-NOT-SUFFICIENT and authorizes only a confirmatory/observe-only next step.
>
> **RULE 4 — AMBIGUOUS / gate-fail (catch-all, guarantees exhaustiveness)** (→ no-PASS; default to wind-down under full-auto, or a fresh single-structure confirmatory pre-reg if HoQR elects). Fires iff RULES 0–3 did not. This catches three disjoint sub-cases, all non-PASS: (a) either p sits in the **CLOSED** straddle band `[0.0478, 0.0522]` — MC-indistinguishable from 0.05 at K=10000; boundary p **never** buys PASS and **never** reads as clean KILL; (b) both p's are strict clean rejections (`p_post2015 < 0.0478` AND `p_agg < 0.0478`) but `DSR < 0.95` — the rejection cannot clear the selection-deflation charge; (c) any combination not covered by RULES 0–3. A bare bootstrap rejection that cannot survive deflation, or any p in the straddle band (including exact boundary values 0.0478 and 0.0522), maps here — NEVER to PASS.
```

### Exhaustiveness and Mutual-Exclusivity Verification

After the replacement, the five rules partition every possible outcome:

| Outcome | Rule |
|---------|------|
| Code / data / freeze fault | RULE 0 — HALT |
| `p_post2015 > 0.0522` | RULE 1 — KILL |
| `p_post2015 ≤ 0.0522` AND `p_agg > 0.0522` | RULE 2 — KILL |
| `p_post2015 < 0.0478` AND `p_agg < 0.0478` AND `DSR ≥ 0.95` | RULE 3 — PASS |
| Everything else (straddle; DSR-fail on clean p's) | RULE 4 — AMBIGUOUS |

At exactly p = 0.0478 on either gate: RULES 1–2 do not fire (not > 0.0522); RULE 3 does not fire (not < 0.0478); RULE 4 fires. Boundary buys neither PASS nor KILL — routes to AMBIGUOUS. Confirmed: no overlap, no gap.

### Companion gloss update — §4.2 exhaustiveness paragraph

The sentence "Fires iff RULES 0–1 did not (so post-2015 cleanly passes)" in RULE 2 must be updated to match. Already incorporated in the REPLACEMENT above.

The sentence in the exhaustiveness paragraph following the rules block:

**ANCHOR (gloss paragraph first sentence):**
```
**Exhaustiveness & mutual-exclusivity.** Ordered disjoint conditions: {technical-fail} → {post-2015 not-clean-reject} → {agg not-clean-reject} → {both clean-reject ∧ DSR≥0.95} → {else}. Evaluation stops at first match ⇒ disjoint by construction; RULE 4 is the unconditional else ⇒ every non-technical-fail outcome lands in exactly one of RULES 1–4. No overlap between the post-2015 gate and the aggregate gate: post-2015 is tested FIRST and its failure short-circuits before the aggregate is consulted (the both-must-pass semantics — post-2015 fail KILLS even when aggregate passes; aggregate is only reached if post-2015 is clean).
```

**REPLACEMENT (gloss paragraph):**
```
**Exhaustiveness & mutual-exclusivity.** Ordered disjoint conditions: {technical-fail} → {p_post2015 > 0.0522: KILL} → {p_agg > 0.0522: KILL} → {both p's < 0.0478 ∧ DSR≥0.95: PASS} → {else: AMBIGUOUS}. Evaluation stops at first match ⇒ disjoint by construction; RULE 4 is the unconditional else ⇒ every non-technical-fail outcome lands in exactly one of RULES 1–4. No overlap between the post-2015 gate and the aggregate gate: post-2015 is tested FIRST and its failure (p > 0.0522) short-circuits before the aggregate is consulted (the both-must-pass semantics — post-2015 fail KILLS even when aggregate passes; aggregate is only reached if post-2015 cleanly rejects). **Boundary convention (frozen):** the straddle band `[0.0478, 0.0522]` is CLOSED; both endpoints and all interior values route to RULE 4 (AMBIGUOUS). PASS requires strict `< 0.0478`; KILL requires strict `> 0.0522`. This inequality appears once per rule body — no other representation of the threshold exists in this document.
```

### Companion fix — §4.3 table row

In the §4.3 table, the column "p-reject threshold (both gates)" currently reads `p ≤ 0.0478 (clean)`. This must be updated to match.

**ANCHOR:**
```
| p-reject threshold (both gates) | p ≤ 0.0478 (clean) | p ≤ 0.0478 (clean) |
```

**REPLACEMENT:**
```
| p-reject threshold (PASS, strict) | p < 0.0478 (strict, both gates) | p < 0.0478 (strict, both gates) |
| p-KILL threshold (strict) | p > 0.0522 (strict, either gate) | p > 0.0522 (strict, either gate) |
| straddle band (AMBIGUOUS, CLOSED) | [0.0478, 0.0522] → RULE 4 | [0.0478, 0.0522] → RULE 4 |
```

---

## PATCH NHT-F5 COMPANION — New §4.4 Sign-Mapping Compatibility Contract

### Placement

Insert as a new section **§4.4** immediately after the existing §4.3 ("Scenario-B auto-activation arithmetic") in PART II of the pre-registration, before the separator line leading to Section 5.

### ANCHOR (insertion point — the text AFTER which §4.4 is inserted)

```
The DSR benchmark `SR0_pp_sel` and `N_sel` are n-INVARIANT (selection charge does not depend on the event count). ONLY `kill_switch_threshold` moves with n (Section 6 derivation for both). Activation = swap the n-pair and read the pre-frozen threshold; nothing is recomputed live.

---

## 5. Power — FROZEN (shown work)
```

### REPLACEMENT (the ANCHOR is kept; this text is inserted between the `---` separator and the `## 5.` heading — i.e. the `---` and `## 5.` heading remain; add the new section between them)

```
## 4.4 Sign-Mapping Compatibility Contract (NHT-F5 companion) — FROZEN

This section pins the compatibility requirements that any QR-authored sign-mapping rule (the decision→trade-direction rule determining `sign_align_e` at the entry bar) must satisfy for the frozen statistic in §1–3 to remain valid. This is the **mathematician's contract for the NHT-F5 companion**: the QR pins the sign-mapping rule in parallel; I state what that rule must satisfy to preserve the hypothesis I am testing and the filtration my statistic assumes.

### 4.4.1 Filtration assumption (what information set is available at the entry bar)

The no-lookahead invariant (§4.3, `entry_delay_bars = 1`) and the daily-bar timestamp convention (§4.1) jointly fix the information set at the entry bar.

**Frozen filtration ruling:**

> `sign_align_e` is determined from the **information set available at the CLOSE of bar D-1** — i.e. the filtration F_{D-1}. Specifically, it is the direction of bar D-1's return (the K_pre=1 pre-window bar), as stated in §1.1: "the a-priori directional hypothesis (pre-decision drift direction registered ex-ante per the QR hypothesis)." Bar D's own OHLC is NOT used in computing `sign_align_e`.

**Why bar D is excluded:** bar D is the first bar whose CLOSE reflects the central-bank decision (§4.1). Using bar D's return sign in `sign_align_e` would mean the position sign is determined by the decision-reaction itself — see §4.4.2 for the hypothesis change this would cause. The frozen statistic in §§1–3 assumes F_{D-1}: the sign is formed from pre-event trend, and the tested quantity is the unconditional post-event continuation of a pre-event directional signal.

**Entry bar (D+1) information check:** at entry bar D+1, the close of D (and therefore the entire OHLC of bar D) is observable data. The entry bar is thus in F_D, which is a superset of F_{D-1}. Any sign-mapping rule that uses only data available through and including F_{D-1} is compatible. A rule that reads bar D's own return sign is NOT compatible with the frozen statistic's hypothesis (see §4.4.2), even though bar D's data is technically available at D+1.

**K_post window confirmation:** the post-window cumulative return covers bars D+1 and D+2 (entry at D+1 open / D close proxy, exit at D+2 close — two holding bars per §4.2 K_post=2). This return is measured on F_{D+2} and contains no decision-day information as a signal input; it is the outcome variable only.

### 4.4.2 Hypothesis change if bar D's return sign is used (disallowed, stated for clarity)

If the QR's sign-mapping rule were to use bar D's OWN return as the sign-alignment input, the tested statistic `r_e = sign(ret_D) · cumulative_net_return(D+1..D+2)` would measure a **conditional continuation effect**: does the K_post-bar window continue in the direction of the decision-day reaction?

This is a materially different hypothesis from the frozen H0/H1 in §1.2:
- **Frozen H0/H1 (F_{D-1} filtration):** unconditional post-event edge, sign-aligned to the pre-event drift direction. The null is `E[r_e] ≤ 0` where the sign is determined without observing bar D.
- **Alternative (F_D filtration, disallowed):** conditional continuation given the direction of the decision-day reaction. The null would be `E[r_e | sign(ret_D)] ≤ 0`. The studentized statistic's sampling distribution differs: conditioning on a function of the return series changes the bias properties of the HAC SE and the bootstrap recentering. In particular, the de-meaned recentering `d_e = r_e − mean(r)` in step 2 of §1.4 is correct under the unconditional H0 but needs to be re-examined under a conditional hypothesis.

**The pre-reg freezes the F_{D-1} filtration and the unconditional hypothesis.** The QR's sign-mapping rule MUST use only information from F_{D-1}. If the rule is discovered to incorporate bar D's return sign, the pre-registration must be re-opened before the freeze-receipt is cut — this is not a runner-level parameter but a hypothesis-level commitment (VOID §1.4(2): parameter drift from the frozen statistic).

### 4.4.3 Degenerate-case handling — bar D-1 return exactly zero

If the K_pre=1 pre-window bar (bar D-1) registers a net return of exactly zero (open equals close, or the pair is effectively unchanged on that bar), `sign_align_e` is undefined under a pure-sign rule.

**Frozen degenerate-case convention:**

> If `ret_{D-1} = 0` (within floating-point equality), `sign_align_e = +1` (long bias — the convention assigns the positive direction in the degenerate case). The event-day return `r_e` is included in the pooled series with this sign. No event-day is excluded solely on the basis of a zero pre-window return.

Justification: the frequency of exact-zero daily returns in the firm's OHLCV data is near-negligible (log-returns on liquid FX pairs essentially never hit exactly zero at daily close precision); the convention has no material effect on the statistic. The +1 convention is chosen over 0 (exclude) to avoid sample-size noise and over −1 (short bias) because the hypothesis is directionally positive. The choice is frozen ex-ante; it may not be changed post-hoc once any event-day data are examined (VOID §1.4(2)).

**Runner implementation requirement:** the runner MUST implement `sign_align_e = +1 if ret_{D-1} >= 0 else -1` (equivalently: `numpy.sign(ret_{D-1})` with the zero case mapped to +1 by clipping or explicit branch), and this must be tested with a synthetic zero-return event-day in the runner's unit tests before the freeze-receipt is cut.

### 4.4.4 Contract summary (machine-readable)

```yaml
sign_mapping_compatibility_contract:
  filtration: F_{D-1}  # sign_align_e uses information through close of bar D-1 only
  bar_D_excluded_from_sign: true  # bar D's own return MUST NOT enter sign_align_e
  hypothesis_type: unconditional_post_event_continuation  # NOT conditional on bar D's sign
  H0: "E[r_e] <= 0, sign_align_e in F_{D-1}"
  H1: "E[r_e] > 0, sign_align_e in F_{D-1}"
  statistic_unchanged_by_filtration_choice: false  # filtration change → hypothesis change → reopen pre-reg
  degenerate_case_ret_D1_eq_zero: sign_align_e_eq_plus_1
  degenerate_case_convention: "numpy.sign with zero→+1 mapping; event included, not excluded"
  runner_unit_test_required: true  # synthetic zero-return event-day must be tested pre-freeze
```
```

---

## Summary of Changes

| Item | Section | Change |
|------|---------|--------|
| PR-04 RULE 1 inequality | §4.2 | `p_post2015 > 0.0478` → `p_post2015 > 0.0522` |
| PR-04 RULE 2 inequality | §4.2 | `p_agg > 0.0478` → `p_agg > 0.0522` |
| PR-04 RULE 3 PASS condition | §4.2 | `p ≤ 0.0478` → `p < 0.0478` (strict) for both gates |
| PR-04 RULE 4 straddle language | §4.2 | Straddle [0.0478,0.0522] stated as CLOSED; boundary values explicit in RULE 4 |
| PR-04 exhaustiveness gloss | §4.2 | Updated to use exact inequalities matching rule bodies |
| PR-04 §4.3 table row | §4.3 | Split into three rows: PASS strict threshold, KILL strict threshold, straddle AMBIGUOUS |
| NHT-F5 filtration contract | new §4.4 | F_{D-1} filtration frozen; bar D excluded; hypothesis stated as unconditional |
| NHT-F5 hypothesis change | new §4.4.2 | F_D use explicitly disallowed; hypothesis change spelled out |
| NHT-F5 degenerate case | new §4.4.3 | Zero return → sign_align_e = +1; event included; runner unit test required |
| NHT-F5 machine-readable | new §4.4.4 | YAML contract block for runner implementer |
