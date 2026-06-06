# R5-CONFIRMATORY PRE-REGISTRATION — Single-Structure Confirmatory Kill Test

**Document status:** HoQR DRAFT v1 (2026-06-06) — HoQR-owned sections authored in full; Mathematician-owned statistics sections are `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]` placeholders. Becomes BINDING and FROZEN only on consensus ratification (HoQR + Mathematician + NHT + principal-reviewer) + CEO sign-off + an EXTERNAL write-once freeze-receipt (SHA-256 of this file as committed + pinned code-commit hash). No hold-out data may be accessed and no metric computed on post-2026-04-06 data before the freeze-receipt is committed.

**Track:** r5-confirmatory-2026-06-06 / Phase 1 / Task 1.0
**New Trial ID:** `f2fb41fd` (org-wide counter increment; registered in `.fintech-org/trials.jsonl`. This trial NEVER reuses the R5 family id `576746aa`.)
**Spawned by:** R5 terminal kill-test outcome AMBIGUOUS_GATE_FAIL (2026-06-06), per the frozen R5 §5 outcome 4 / §7.3.6 RULE 4 confirmatory-only gate.
**Authoritative parent:** `references/pre-registrations/r5_carry_universe_kill_test.md` (IMMUTABLE — this document references it and never edits it) and its result `references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml`.
**Acceptance criteria:** `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pm-acceptance-criteria.yaml`

---

## 1. Preamble & Confirmatory Contract (HoQR) — criterion CONF-structure / CONF-decision-map context

### 1.1 What this pre-registration IS

This document is a **confirmatory-only statistical test of ONE pre-specified structure** — `vol_target_carry:USDJPY` — on **unsnoopable future data that does not yet exist at freeze time** (post-2026-04-06 daily bars). It is spawned by the R5 terminal kill test's AMBIGUOUS_GATE_FAIL outcome (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:2` `decision: AMBIGUOUS_GATE_FAIL`), which under the frozen R5 decision functional (§7.3.6 RULE 4 → §5 outcome 4) maps to **exactly one permitted forward action: a fresh, separately-pre-registered confirmatory test of the single surviving structure**, with no free exploration and no capital.

The R5 family p was discordant: `p_SPA = 0.0162` (class-level rejection at the consistent estimate) but `p_RC = 0.0588 > 0.05` (White Reality Check did NOT concur), with `DSR = 0.9503` clearing the ≥0.95 gate by +0.0003 (`STEP4-RESULT.yaml:3,7,8`). A boundary/discordant family result is precisely the artifact R5 was built to refuse to over-interpret. This confirmatory test exists to convert that ambiguity into a clean binary on the ONE cell that won the family max-statistic — on data the firm cannot have snooped, because it has not happened yet.

This pre-registration freezes — before any future bar is accessed — every degree of freedom: the exact structure and its config (Section 2), the hold-out window rule and look-date governance (Section 3), the null/statistic/honest-N/selection-absorption and the alpha-spending look design (Mathematician sections), the decision map under every outcome at every look (Section 4), the interim observe-only state (Section 5), and the kill-switch threshold (Section 6). Freezing these on not-yet-existing data is what makes the resulting p face-valid.

### 1.2 What this pre-registration is NOT

- **NOT a family re-open.** The R5 36-cell carry family is closed. No variant search, no pair search, no re-parameterization of any of the 36 cells is authorized by this document. (R5 §5 outcome 4: "the 36-cell family research is not re-opened.")
- **NOT exploration.** No new hypotheses are generated here. Genuinely-new alpha tracks require their own fresh pre-registrations (Section 5 capacity redirect).
- **NOT a validation shortcut or rescue attempt.** A confirmatory PASS does NOT itself authorize capital. It authorizes only a named, governance-gated next step (Section 4). The base-rate honest expectation, given the power reality (Mathematician section), is that a single ~0.77-Sharpe monthly-stale series will take years to confirm and may well fail — wind-down remains the most-likely terminal state of the carry program.
- **NOT a re-run of R5.** This document never edits, re-runs, or re-interprets the R5 SPA/White-RC test on any window. R5 is frozen and immutable.

### 1.3 VOID conditions (the confirmatory contract)

This pre-registration's result is **VOID and not face-valid** if any of the following occur:

1. **Parameter change / structure drift.** Any change to the pinned `vol_target_carry:USDJPY` config (Section 2) — any of `target_vol`, `vol_window`, `leverage_cap`, `min_carry`, `rebalance_threshold`, `entry_delay_bars`, cost params, sizer type — between freeze and evaluation voids confirmatory status. The structure is tested AS-IS.
2. **Early peek.** Any computation of strategy performance on any post-2026-04-06 bar before a frozen look date (Section 3) voids the test. The interim monitoring state (Section 5) records data accrual and mechanical data-integrity only — NEVER strategy P&L or any test statistic.
3. **Missing selection-absorption.** If the frozen honest-N / SR0 deflation inputs (Mathematician section) do NOT charge the R5 36-cell argmax selection as a spent look, the confirmatory p is a garden-of-forking-paths violation and is VOID. (R5 §4 / §5 outcome 4, BINDING: "MUST absorb the R5 36-cell selection burden in its own honest-N / deflation inputs.")
4. **Missing new trial_id.** If the run registers under `576746aa` or fails to increment the org-wide counter, it is VOID. (This document's trial is `f2fb41fd`.)
5. **Freeze mismatch.** If `receipt.prereg_sha256 != sha256(this file as committed)` or `receipt.code_commit != pinned commit` (Section 2 / freeze block), the run executed against an unfrozen or drifted spec and is VOID.

### 1.4 Lineage

```
R5 family trial 576746aa  (36-cell SPA/White-RC kill test, AMBIGUOUS_GATE_FAIL 2026-06-06)
        │  k* = vol_target_carry:USDJPY selected as family argmax max-statistic
        │  (selection is a SPENT LOOK — charged in this test's honest-N, NOT free)
        ▼
Confirmatory trial f2fb41fd  (THIS document — single-cell, post-2026-04-06, no capital)
```

`f2fb41fd` is a distinct child trial, not a continuation of `576746aa`. The R5 documents and freeze-receipt are immutable; this document only references them.

---

## 2. The Structure Under Test (HoQR) — criterion CONF-structure

### 2.1 The single locked structure

The ONLY structure this confirmatory test may evaluate is the R5 family argmax:

> **`k* = vol_target_carry:USDJPY`** — selected as `k_star_idx: 18`, `k_star_label: vol_target_carry:USDJPY` in the R5 result (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:9-10`), at in-sample annualized Sharpe `0.7672`, skew `0.1963`, excess kurtosis `8.2783`, over `T = 4186` common-index bars (`STEP4-RESULT.yaml:11-13,17`).

No other cell of the 36-cell R5 universe is in scope. No pair other than USDJPY. No variant other than `vol_target_carry`.

### 2.2 Verbatim config pin

The structure is pinned to the committed config file `config/vol_target_carry.yaml` and to the R5 matrix builder's `_VARIANT_EXEC["vol_target_carry"]` execution config (`src/forex_system/harness/carry_universe_matrix.py:266-274`). The two are consistent; both are pinned. Verbatim values:

| Parameter | Value | Source |
|---|---|---|
| variant | `vol_target_carry` | `config/vol_target_carry.yaml:33`; `carry_universe_matrix.py:266` |
| pair | `USDJPY` | `config/vol_target_carry.yaml:20-26` |
| `target_vol` | `0.10` (annualized 10%) | `config/vol_target_carry.yaml:33` |
| `vol_window` | `252` daily bars | `config/vol_target_carry.yaml:34` |
| `leverage_cap` | `2.0` | `config/vol_target_carry.yaml:35,44`; `carry_universe_matrix.py:271` |
| `min_carry` | `-0.10` (no carry filter — vol-targeting does the work) | `config/vol_target_carry.yaml:36` |
| `rebalance_threshold` | `0.20` | `config/vol_target_carry.yaml:37,51`; `carry_universe_matrix.py:268` |
| `rebalance_mode` | `continuous` | `config/vol_target_carry.yaml:50`; `carry_universe_matrix.py:267` |
| sizer | `VolTargetSizer` | `carry_universe_matrix.py:270` (`sizer_type="vol_target"`) |
| `max_order_units` | `5_000_000.0` | `config/vol_target_carry.yaml:46`; `carry_universe_matrix.py:272` |
| `min_order_size` | `100.0` | `config/vol_target_carry.yaml:45`; `carry_universe_matrix.py:273` |
| `entry_delay_bars` | `1` (no-lookahead sacred invariant) | `config/vol_target_carry.yaml:49`; `carry_universe_matrix.py:587-589` |
| cost model | `RealisticCostModel`, USDJPY `PairInfo` (spread 1.0 / slippage 0.5 / commission 0.5 / swap_long 0.8 / swap_short -1.5 pips) | `config/vol_target_carry.yaml:21-26`; `carry_universe_matrix.py:108-116` |
| `initial_capital` | `1_000_000.0` | `config/vol_target_carry.yaml:40`; `carry_universe_matrix.py:554` |
| return convention | `equity_curve.pct_change()` net-of-cost simple returns | `carry_universe_matrix.py:522-528` |

### 2.3 Code commit lineage

The R5 freeze pinned the matrix builder at code commit **`350cbd4b592485f3bd935ec414ee007e63879de5`** (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:62`). The confirmatory run MUST execute `vol_target_carry:USDJPY` under either:

- (a) the **same exec config at commit `350cbd4`** (`carry_universe_matrix._build_cell` / `_build_sizer` / `_VARIANT_EXEC["vol_target_carry"]`), OR
- (b) a **future-frozen successor commit verified behavior-equivalent** for this single cell — equivalence meaning byte-identical return series on a fixed shared sub-window, demonstrated and recorded in the freeze-receipt. Any non-equivalent code change to the execution path voids confirmatory status (Section 1.3 condition 1 + 5).

The current working HEAD at draft time is `1c533e8` (informational only; the binding pin is set at freeze).

### 2.4 Single-cell hypothesis H1

The confirmatory alternative is: **`vol_target_carry:USDJPY` has positive expected net-of-cost return / annualized Sharpe strictly greater than zero, net of the confirmatory deflation charge** on the post-2026-04-06 hold-out. The exact null/statistic/deflation formulation is the Mathematician's:

> `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
> CONF-statistic: frozen null H0 for the single-series confirmatory test; the test statistic and method (single-series studentized t / single-cell SPA); the selection-absorption mechanism (how the R5 36-cell argmax is charged as a spent look in the confirmatory honest-N and SR0); the DSR formula inputs for the confirmatory cell, with R5 k* statistics (SR_ann=0.767, skew=0.196, xkurt=8.28) as prior-look anchors only — the confirmatory run uses the hold-out cell's own metrics.

---

## 3. Hold-Out & Calendar Governance (HoQR; co-signed Mathematician) — criterion CONF-holdout

### 3.1 The hold-out window rule (a RULE, not a single date)

> **HOLD-OUT RULE.** The confirmatory return series is computed ONLY from USDJPY daily bars dated **strictly after 2026-04-06** — the R5 common-index terminus (`r5_carry_universe_kill_test.STEP4-RESULT.yaml`; R5 common index ran 2010-03-15 → 2026-04-06, T=4186). There is **zero overlap** with any bar R5 saw. No bar on or before 2026-04-06 enters the confirmatory test under any circumstance.

This is a forward rule over data that does not exist at freeze: the hold-out is unsnoopable by construction because it has not yet been generated.

### 3.2 Data-accrual expectation

USDJPY daily bars accrue at ~250 trading-day bars/year. The signal feed is the cross-currency rate differential (`data/rates/rate_differentials.parquet`), which is **monthly forward-filled** — so the EFFECTIVE information arrival is ~12 fresh rate observations/year (~1 effective obs/month). Calendar-time hold-out length therefore vastly overstates statistical information; the Mathematician converts calendar time to effective observations in the power section. The R5 doc's own power statement (§6) anchors the order of magnitude: at true ann Sharpe ~0.77, ~4.6 years of hold-out for ~50% power, ~10 years for ~80%.

> `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
> CONF-holdout (Math co-sign): minimum T_holdout for block-bootstrap validity; the effective-observation conversion; the exact bar-count gate below which a look is statistically void.

### 3.3 Look-date governance (the calendar discipline I own)

The CALENDAR governance around the looks is HoQR-frozen here; the look SCHEDULE itself (how many looks, at what effective-observation milestones, under which alpha-spending function) is the Mathematician's to freeze (CONF-interim). Binding governance:

1. **Evaluations occur ONLY at the Mathematician's frozen look dates.** No evaluation — no statistic, no Sharpe, no P&L — is computed on the hold-out outside a frozen look date. (R5-pattern; pm-acceptance-criteria `no_evaluation_before_frozen_dates: true`.)
2. **Each look is a logged one-shot against the frozen receipt.** At each look date a single evaluation is run against the frozen spec and freeze-receipt, its inputs and outputs recorded to the decision-trace and to a per-look result artifact. No "re-run with a tweak" path preserves the pre-registration (R5 §1.3 pattern).
3. **No one reads interim performance outside look dates.** The interim monitoring state (Section 5) is data-and-integrity only. Reading interim performance is an early-peek VOID (Section 1.3 condition 2).
4. **Alpha-spending governs multiplicity across looks.** Because the design is multi-look (the power reality forces interim looks rather than a single ~5–10yr wait), every look spends part of the family-wise α under a pre-registered alpha-spending function. Unplanned peeks are prohibited (pm-acceptance-criteria `alpha_spending_required_if_interim_looks: true`).
5. **The final look is terminal.** There is no "inconclusive, keep waiting past the final look" branch (Section 4).

### 3.4 Data-quality / provenance gate

Before any look computes a statistic, the hold-out USDJPY series must pass the existing provenance gate: `data/storage.py::_assert_price_range` requires USDJPY daily closes to lie within economically plausible bounds **`[20.0, 245.0]`** (`src/forex_system/data/storage.py:54`), and the loader is hardcoded to the real `.../processed/...` directory (quarantining the corrupted synthetic series). If the hold-out data fails the provenance gate at a look date, that look is a **TECHNICAL FAILURE** (Section 4 outcome 5: HALT / re-freeze), NOT a confirmatory fail — a data fault must never be read as a strategy verdict.

> `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
> CONF-interim: the alpha-spending function (e.g. O'Brien-Fleming), the frozen look schedule (in effective observations / calendar dates), the power curve at each planned look, and the optional pre-registered futility boundary. NHT reviews the power statements.

---

## 4. Decision Map (HoQR) — criterion CONF-decision-map

Every outcome at every look maps to a NAMED firm action. There is **no "inconclusive, keep waiting beyond the final look" branch** — the final look is terminal.

| # | Outcome (at a look) | Condition | Named firm action |
|---|---|---|---|
| **1** | **PASS at a look** | Single-cell confirmatory statistic crosses the alpha-spending **efficacy** boundary at this look AND the confirmatory DSR gate clears (≥ the frozen kill-switch threshold, Section 6) AND, where R5's discordance is relevant, the confirmatory single-series test resolves it (a single-series test has no SPA-vs-RC family discordance — see §4.2) | **GRADUATE to the firm's next validation stage — NO CAPITAL on this path.** Concretely: author a FURTHER, separately-pre-registered **observe-only paper canary** (a forward live-data paper run with no capital at risk), governed by its own fresh HoQR+Math+NHT ratification and its own trial_id. PASS here does NOT authorize capital, does NOT re-open the carry family, and does NOT license exploration. The named gate is: *confirmatory-PASS → fresh paper-canary pre-reg*. Any capital decision is a separate, later governance step explicitly out of scope for trial `f2fb41fd`. |
| **2** | **FAIL at the final look** | Final look reached; efficacy boundary never crossed (statistic fails to reject H0 at the terminal cumulative α) | **KILL the structure.** Archive `vol_target_carry:USDJPY` as RETIRED/FALSIFIED in the falsification archive (pointer to this pre-reg, the freeze-receipt, and the per-look result artifacts). The carry program winds down fully per R5 §5.1. This fires whether the final look was adequately powered or not — low terminal power makes the non-rejection uninformative *as evidence of no edge* but does NOT change the action (binding, mirrors R5 §5 outcomes 2 & 3). |
| **3** | **FAIL at an interim look (futility)** | An interim look crosses a pre-registered **futility** boundary downward (only if the Mathematician freezes a futility boundary in CONF-interim) | **Early KILL.** Same archival + wind-down as outcome 2, stopped early. If the Mathematician freezes NO futility boundary, this outcome does not exist and the test runs to the final look regardless. |
| **4** | **CONTINUE-to-next-look** | An interim look crosses neither the efficacy nor (if present) the futility boundary | **Accrue data to the next frozen look.** This is NOT "inconclusive, keep spending" — it is the pre-registered alpha-spending design proceeding to its NEXT pre-frozen look. No new research spend, no capital, no re-parameterization (Section 5). This branch is only available at interim looks; it is unavailable at the final look (outcome 2 is forced there). |
| **5** | **TECHNICAL FAILURE** | Code error, data-integrity / provenance fault (Section 3.4), freeze mismatch (Section 1.3 condition 5), or unexplained data gap at a look | **HALT, root-cause, re-freeze, re-run.** No confirmatory statistic is read or reported for that look. The trial counter is NOT incremented (the confirmatory test remains ONE trial, `f2fb41fd`). After root-cause and a new freeze-receipt, the look is repeated. A masked bug presented as a fail is itself a VOID. |

### 4.1 No keep-spending escape

There is no decision branch anywhere in this document that results in "the structure is inconclusive, so keep researching / keep deferring indefinitely." The only terminal states are GRADUATE-to-paper-canary (outcome 1) and KILL (outcomes 2/3). Outcome 4 is bounded by the frozen look schedule and terminates at the final look. Outcome 5 returns to a re-frozen re-run, never to free exploration.

### 4.2 R5 discordance handling

R5's family discordance (`p_SPA = 0.0162` vs `p_RC = 0.0588`; `STEP4-RESULT.yaml:3,5`) arose from a 36-cell max-statistic family where SPA and White-RC weight the benchmark differently across cells. The confirmatory test is a **single-series** test on one cell — there is no 36-cell family and therefore no SPA-vs-RC max-statistic discordance to reconcile *at the family level*. The confirmatory test's own concordance requirement (a single-series efficacy crossing plus the DSR gate clearing) is the Mathematician's to specify; the decision map above requires BOTH to hold for outcome 1 (PASS). This is how the confirmatory design "handles concordance/discordance" as required by `pm-acceptance-criteria` `r5_discordance_condition_documented: true`.

---

## 5. Interim Monitoring State (HoQR) — criterion CONF-monitoring

Between the freeze date and each look date, the carry family is in **observe-only** state.

1. **No new research spend on the carry family.** No new variant, no new pair, no parameter search, no re-test of the 36-cell R5 family on any dataset. (R5 §5.1; pm-acceptance-criteria `no_pair_or_variant_search: true`.)
2. **Data pipeline keeps accruing bars.** The existing daily USDJPY ingestion continues; the rate-differential feed continues. This is passive accrual — NOT evaluation.
3. **Quarterly mechanical data-integrity checks WITHOUT computing strategy performance.** Each quarter, run the `data/storage.py` provenance/bounds check (`_assert_price_range`, USDJPY bounds `[20.0, 245.0]`, real-directory loader) and log the result. This records DATA health only. It does NOT compute the strategy's return series, Sharpe, P&L, or any test statistic — doing so would be an early-peek VOID (Section 1.3 condition 2).
4. **Falsification-archive entry for the R5 outcome.** The R5 AMBIGUOUS_GATE_FAIL result is recorded in the falsification archive (curated record of what was tested and the outcome): pointer to `r5_carry_universe_kill_test.md`, its FREEZE-RECEIPT, and `STEP4-RESULT.yaml`. This confirmatory test's own per-look outcomes append to that archive as they occur.
5. **Capacity redirect.** Active research capacity is redirected to genuinely-new alpha hypotheses. Those are SEPARATE tracks, out of scope for `f2fb41fd`, and each requires its own fresh pre-registration — nothing is unfrozen by default under the firm's zero-validated-alpha posture.

---

## 6. Kill-Switch Threshold (HoQR adopts; Mathematician derives) — criterion CONF-kill-switch-threshold

The repo pre-commit hook requires every new pre-reg file to contain the literal `kill_switch_threshold:` field. The confirmatory threshold is **NOT** R5's `0.767` — absorbing the R5 36-cell argmax selection into the confirmatory honest-N raises the deflation charge, so the minimum hold-out annualized Sharpe required to clear DSR ≥ 0.95 at the confirmatory `SR0_pp` is higher than R5's. The Mathematician derives the exact value; HoQR adopts it verbatim.

```yaml
kill_switch_threshold: [VALUE FROM MATHEMATICIAN]
```

Semantics: `[VALUE FROM MATHEMATICIAN]` is the minimum annualized Sharpe of `vol_target_carry:USDJPY` on the hold-out that clears the frozen confirmatory DSR ≥ 0.95 gate at the post-absorption honest-N. Any hold-out Sharpe below it fails the gate and cannot produce a PASS (Section 4 outcome 1). No bar executes outside the historical/forward backtest; the threshold governs the confirmatory decision functional, not a live trading loop.

> `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
> CONF-kill-switch-threshold derivation: the confirmatory honest-N (R5 36-cell selection absorbed), the frozen confirmatory `SR0_pp`, and the mechanical derivation of `kill_switch_threshold` from the single-series DSR formula. Mathematician signs the derivation.

---

## 7. Retirement Criteria (HoQR) — machine-checkable

Machine-checkable triggers a downstream gate evaluates against each per-look result artifact and the freeze-receipt:

- `look.is_final == true AND look.efficacy_crossed == false` → **KILL** `vol_target_carry:USDJPY` (archive FALSIFIED; carry program full wind-down per R5 §5.1). Power level does NOT gate this trigger.
- `look.futility_boundary_exists == true AND look.futility_crossed == true` → **EARLY KILL** (same archival, stopped early).
- `look.efficacy_crossed == true AND look.dsr >= kill_switch_threshold_cleared` → **GRADUATE to fresh paper-canary pre-reg** (NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification).
- `look.is_interim == true AND look.efficacy_crossed == false AND look.futility_crossed == false` → **CONTINUE to next frozen look** (bounded; unavailable at final look).
- **VOID-on-freeze-mismatch:** `receipt.prereg_sha256 != sha256(this file as committed) OR receipt.code_commit != pinned_commit` → **VOID** (Section 1.3 condition 5).
- **VOID-on-early-peek:** any strategy-performance computation on a post-2026-04-06 bar with `timestamp < frozen_look_date` → **VOID** (Section 1.3 condition 2).
- **VOID-on-parameter-drift:** any executed config field for `vol_target_carry:USDJPY` differs from the Section 2.2 verbatim pin (or code path not behavior-equivalent to commit `350cbd4` per Section 2.3) → **VOID** (Section 1.3 condition 1).
- **VOID-on-missing-selection-absorption:** confirmatory honest-N / SR0 does not charge the R5 36-cell argmax as a spent look → **VOID** (Section 1.3 condition 3; R5 §4/§5 outcome 4 BINDING).
- **VOID-on-wrong-trial-id:** run registers under `576746aa` or omits the org-counter increment → **VOID** (Section 1.3 condition 4; trial is `f2fb41fd`).
- `look.code_error == true OR look.data_integrity_fault == true OR holdout fails storage.py bounds [20.0, 245.0]` → **HALT** (Section 4 outcome 5); trial counter NOT incremented.

A non-pass at the final look at any power level is a KILL trigger. There is no machine-checkable path from this test to "keep researching the carry family as-is."

---

## FREEZE BLOCK — criterion CONF-freeze (mechanics owned jointly; receipt is EXTERNAL)

The freeze-receipt is an EXTERNAL write-once file (pattern of `scripts/cut_freeze_receipt.py`) recording: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the `vol_target_carry:USDJPY` execution path (commit `350cbd4` or a verified-equivalent successor per Section 2.3) and any new evaluation/look runner; (c) the new trial_id `f2fb41fd`; (d) the frozen look schedule (Mathematician). This file does NOT embed its own hash (F-003 pattern — embedding makes verification circular). The receipt is committed to git BEFORE any post-2026-04-06 hold-out data is accessed or any metric computed.

---

*Mathematician-owned sections (CONF-statistic, CONF-interim, CONF-holdout co-sign, CONF-kill-switch-threshold derivation) are merged at assembly. NHT audit and principal-reviewer review precede CONSENSUS; CEO ratification precedes the freeze-receipt cut.*
