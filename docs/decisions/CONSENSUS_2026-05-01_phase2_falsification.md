# CONSENSUS — Phase 2: Operational Falsification Trials
**Date:** 2026-05-01
**Parent:** docs/decisions/CONSENSUS_2026-04-28.md (Direction v1)
**Sub-track:** Phase 2 Wave 2 — falsification specs
**Status:** Draft — awaiting CEO ratification
**Roles signed:** HoQR, NHT, QD, PM (this draft). CTO + CRO absent (Phase 1 closed; risk envelope inherited).

---

## 1. North-star

"Make money" — operationalized as Sharpe ≥ 0.5 OOS paper-traded. Phase 2 sub-track focuses on producing ≥10 OOS rejections (CONDITION-1) and ≥5 by 2026-05-15 (NHT discipline window) — gating Phase 2 paper launch authorization. Current status: 22 trials logged, 0 rejections. This wave fixes that.

---

## 2. The signed Phase 2 plan

Wave 2 produced three specs (HoQR prioritization + NHT frozen thresholds + QD harness extension). Wave 3 implements and runs. No new alpha research; no modifications to validated strategies.

**Carry-family thesis remains untouchable.** vol_target_carry (Sharpe 0.76) and FRED-carry Bet #1 (Sharpe 0.80) are immutable. They are NOT rejection candidates.

**Falsification queue (7 candidates):** Phase 0 archived baselines (ma_crossover, momentum, bollinger_rsi, carry, carry_momentum) queued for explicit OOS falsification, plus two novel items: FRED-carry stripped (no regime filter) and Bet #2 tas_ceiling_4h.

**Critical caveat — sample overlap (Conflict 2):** Multiple archived-baseline candidates share USDJPY post-2024 OOS data already consumed by validated strategies. NHT's append-only protection reclassifies those as sensitivity analyses, not independent falsification. CONDITION-1's ≥10 rejection count may not be reachable from this queue alone. CEO decision required (Section 10).

**Highest-value item:** FRED-carry stripped (Candidate 6) — directly tests whether the BoJ-divergence flag is the load-bearing source of Bet #1's 0.80 Sharpe. A rejection here confirms regime conditioning is real. A fail-to-falsify requires Bet #1 re-review before paper launch.

**Trial budget:** 22 existing + 7 new = 29, inside CRO ceiling of 36.

---

## 3. Reconciled Wave 3 dispatch sequencing

**Sub-wave 3a — Foundation (BLOCKS 3b/3c):**
- QD implements DSR per Bailey & Lopez de Prado (2014) eq. 10; N used = `n_trials_at_spawn` from trial record, not a fixed value
- QD backfills `dsr` field for existing 22 trials (all currently null)
- QD implements pre-reg parser (`preregistration.py`) — sidecar YAML approach per QD spec
- QD implements falsification evaluator (`falsification_evaluator.py`) — pure function on metrics dict
- QD wires `.fintech-org/nht-rubric.yaml` from NHT artifact's R1–R6 thresholds verbatim

**Sub-wave 3b — Pre-reg authoring (parallel with 3a, gated on parser design):**
- HoQR + QD coauthor pre-reg markdowns: R3 (ma_crossover), R4 (momentum), R5 (bollinger_rsi), R6a (carry), R6b (carry_momentum) — split per Conflict 1 — plus R7 (FRED-carry stripped)
- Each pre-reg includes `kill_switch_threshold:` field per Gate 3; each flags `oos_overlap` explicitly per NHT sample-overlap protection
- Pre-regs must be filed and frozen BEFORE the corresponding backtest runs — no exceptions

**Sub-wave 3c — Trial execution (gated on 3a complete + 3b complete + CEO Conflict 2 decision):**
- Candidates 1–5 (archived baselines) each tagged with `oos_overlap: true/false` per pair/window audit
- Candidate 6 (FRED-carry stripped): NHT must approve independent OOS window before execution
- Candidate 7 (Bet #2 tas_ceiling_4h): blocked until R2 pre-reg finalized (CTO CONDITION-4)
- Rejections logged via `record_trial_rejection()`; completions via `_append_trial()`

**Sub-wave 3d — Tier verification:**
- Tier A: `status=rejected` count ≥5 by 2026-05-15 (hard deadline)
- Tier B / CONDITION-1: ≥10 rejections by 2026-06-23 (HoQR alpha-pivot kill date)

---

## 4. Frozen falsification rubric (verbatim from NHT)

*Source: `nht-frozen-thresholds.yaml`, frozen 2026-05-01. Any threshold change requires new pre-registration + new CONSENSUS.*

### R1 — Naive OOS Sharpe
threshold: oos_sharpe < 0.30
rationale: Anchored above zero to exclude strategies that technically beat zero but sit within estimation noise on a daily-bar sample. Set below the validated baselines (0.76, 0.80) — using the validated bar as universal bar would be circular; not every strategy needs to match vol_target_carry to be a valid candidate. 0.30 represents real but minimal evidence. If the strategy's own pre-registration states a higher kill_switch_threshold, THAT threshold supersedes R1 (more conservative wins).
override_rule: "max(0.30, strategy_pre_reg.kill_switch_threshold)"

### R2 — Deflated Sharpe
threshold: dsr < 0.50
formula: Bailey & Lopez de Prado (2014): DSR corrects the observed Sharpe for the number of trials N at spawn time, return distribution skewness, and excess kurtosis. N used MUST be n_trials_at_spawn from the trial record, not a fixed value. Deflation factor range for N=22: 0.5–0.7x raw OOS Sharpe.
route_to: QD — implement DSR computation; `dsr` field is schema-present but null
note: Until QD implements DSR computation, R2 is a BLOCKING GATE that cannot be cleared. Strategies may not be promoted to paper trading with dsr=null.

### R3 — Max Drawdown
threshold: max_dd > 0.25
rationale: Inherited from VTC-T2 (the only existing machine-checkable drawdown criterion). 25% is the current firm anchor. CRO may tighten to 20% before 2026-05-01 freeze; after that date this value is frozen.

### R4 — Capacity
threshold: ROUTE_TO HoQR
rationale: NHT does not have position-sizing models to estimate notional capacity from backtest output alone. HoQR must provide a capacity_estimate field in the pre-registration. Heuristic floor suggested: capacity_estimate < $100k USD notional is a rejection candidate on cost-efficiency grounds, but this is advisory only until HoQR defines the firm minimum. QD should add `capacity_estimate` as a nullable field to trial schema.

### R5 — Permutation test
threshold: permutation_pvalue > 0.05
k_permutations: 200
status: aspirational
rationale: K=200 matches VTC-T8 precedent. Permutation test shuffles feature labels (not time labels) and recomputes OOS Sharpe. p-value is fraction of permuted Sharpes >= observed. Standard alpha 0.05. ASPIRATIONAL: harness does not currently emit permutation fields. QD must implement before R5 becomes a hard gate. Until then, R5 is noted in trial record as "pending."

### R6 — Sample size
threshold: n_trades < 30 OR n_oos_bars < 252
rationale: n_trades < 30: detecting Sharpe=0.5 vs 0 at 80% power requires ~64 independent observations; 30 is the floor below which annual Sharpe estimates are dominated by endpoint luck. Rejecting at 30 is lenient; raising to 50 is defensible if QD confirms typical trade counts. n_oos_bars < 252: one year of daily bars is the minimum for an annual Sharpe estimate to have any interpretive value. Sub-annual OOS is not OOS.

### Special clauses

GOALPOST-STUFFING PROPHYLACTIC: Any Phase 2 evaluation of an archived Phase 0 baseline (ma_crossover, bollinger_rsi, momentum, carry_momentum) MUST have a strategy-specific pre-registration filed BEFORE the backtest runs. The pre-reg must state a positive threshold on a held-out OOS window not used in the original archival decision. "Strategy is archived" is not a falsification criterion. Evaluations without compliant pre-regs will be recorded as invalid trials.

SAMPLE-OVERLAP PROTECTION: Any new strategy sharing pair and date-range overlap with vol_target_carry (USDJPY, OOS post-2024) or FRED-carry Bet #1 (multi-pair, OOS post-2024) must be flagged in the trial record with `oos_overlap: true`. Overlapping OOS is not independent evidence. Overlapping trials are not falsification trials — they are sensitivity analyses and must be labeled as such. QD must enforce at trial-spawn time.

---

## 5. Falsification queue (from HoQR, ranked by expected-falsification-rate-per-research-cost)

| Rank | Candidate | Type | OOS Overlap? | Expected completion |
|------|-----------|------|-------------|-------------------|
| 1 | ma_crossover — trend-following OOS falsification | ARCHIVED BASELINE (box-check) | Yes — USDJPY | Week 1 |
| 2 | momentum — pure momentum OOS falsification | ARCHIVED BASELINE (box-check) | Yes — USDJPY | Week 1 |
| 3 | bollinger_rsi — mean-reversion OOS falsification | ARCHIVED BASELINE (partial novel; may fail-to-reject) | Yes — USDJPY | Week 1 |
| 4 | carry (unaugmented) — dominance vs carry_fred | ARCHIVED BASELINE (genuine falsification) | Yes — USDJPY | Week 2 |
| 5 | carry_momentum — dominance pending confirmation | ARCHIVED BASELINE (decision node) | Yes — USDJPY | Week 2 |
| 6 | FRED-carry stripped (no regime filter) | NOVEL — highest value; tests BoJ-flag load-bearing claim | No — independent window required | Week 3–4 |
| 7 | tas_ceiling_4h (Bet #2) | NOVEL — pre-reg R2 must finalize first | No | Week 3–4 |

**Sensitivity-analysis flag (per Conflict 2):** Candidates 1–5 share USDJPY post-2024 OOS data with validated strategies. Under NHT's append-only sample-overlap protection, these trials will be tagged `oos_overlap: true` and classified as **sensitivity analyses, NOT independent falsification trials**. They do NOT count toward CONDITION-1's ≥10 rejection target unless a non-overlapping window is carved (see Section 10).

**Candidates 6 and 7** remain independent and count toward CONDITION-1 if they reject.

---

## 6. Harness-extension spec (from QD)

**A. Parser:** `src/forex_system/harness/preregistration.py`. Sidecar YAML approach (`{strategy_id}.triggers.yaml`) — not auto-parsed prose. Missing sidecar raises `ConfigError`. Emits structured log at parse time.

**B. Evaluator:** `src/forex_system/harness/falsification_evaluator.py`. Pure function on `dict[str, float]`. Exhaustive trigger evaluation (no short-circuit). `falsification_criterion` = largest relative violation. Consumes `.fintech-org/nht-rubric.yaml` as constructor argument (injectable for tests).

**C. Wrapper:** Injected into `src/forex_system/harness/run_trial.py` after `_append_trial(complete_entry)`. Calls `record_trial_rejection()` on failed verdict. No new entry-point scripts.

**D. Tests:** 8 cases across `test_preregistration.py` and `test_falsification_evaluator.py` — valid parse, missing kill_switch_threshold, missing sidecar, pass/reject/multi-trigger verdicts, missing rubric error, no-sidecar backward-compat.

**E. LOC estimate (revised for DSR, per Conflict 3):**

| Component | LOC |
|-----------|-----|
| preregistration.py | ~120 |
| falsification_evaluator.py | ~100 |
| run_trial.py injection + helper | ~50 |
| DSR formula implementation + backfill script | ~150 |
| vol_target_carry.triggers.yaml + nht-rubric.yaml | ~30 |
| test_preregistration.py + test_falsification_evaluator.py | ~220 |
| **Total** | **~670** |

**Estimate:** ~1.5 dev-days (up from 1.0 before Conflict 3 sequencing fix).

---

## 7. Disagreement matrix

**Conflict 1 — Joint vs per-strategy pre-regs (R6):**
HoQR proposed a single joint pre-reg covering carry + carry_momentum to reduce overhead. NHT's goalpost-stuffing prophylactic (append-only) requires strategy-specific pre-regs. **NHT wins (append-only).** R6 split into R6a (carry) + R6b (carry_momentum).

**Conflict 2 — Sample-overlap with validated strategies (MATERIAL — CEO decision required):**
HoQR planned to use the post-2024 holdout for all 5 archived baselines including USDJPY. NHT's sample-overlap protection (append-only) prohibits treating overlapping OOS as independent evidence. **NHT wins (append-only).** Candidates 1–5 are reclassified as sensitivity analyses. This materially reduces Phase 2 yield below HoQR's projection. See Section 10 for CEO options.

**Conflict 3 — DSR computation as Wave 3 prerequisite:**
NHT made R2 a blocking gate (dsr=null for all 22 trials). QD's spec did not sequence DSR as the first Wave 3 task. **Reconciled:** Wave 3 sequencing is fixed — DSR implementation + backfill is the first task in sub-wave 3a, before pre-reg parser or evaluator.

**Conflict 4 — R6 label collision (mechanical):**
QD spec referenced "R6 cost-stressed Sharpe" (from parallel drafting without NHT visibility). NHT R6 is sample-size (n_trades < 30 OR n_oos_bars < 252). **Reconciled mechanically.** Wave 3 wires NHT's R6 verbatim. QD updates `NhtRubric` field names accordingly.

---

## 8. NHT dissent (VERBATIM — APPEND-ONLY — DO NOT EDIT)

Per fintech-org rule 6, the following dissent is structurally preserved. It cannot be edited, condensed, or overridden by any subsequent consensus. CEO acknowledges it in writing at ratification.

---

This dissent is append-only. CEO sees it verbatim.

(a) GOALPOST-STUFFING PROPHYLACTIC — ARCHIVED BASELINES:
If HoQR's Phase 2 queue includes any of the four archived Phase 0 strategies
(ma_crossover, bollinger_rsi, momentum, carry_momentum), the following applies
WITHOUT EXCEPTION: each must have a strategy-specific pre-registration filed
BEFORE its Phase 2 backtest is run, containing falsification criteria that go
BEYOND "the strategy is in the archive." Specifically, the pre-reg must state
(i) what would constitute SURPRISING evidence that the archived conclusion was
wrong, and (ii) a positive threshold the strategy must clear on a HELD-OUT OOS
window not used in the original archival decision. Archival status is not
falsification. Checking a box labeled "already retired" is not NHT work.
If this condition is not met, I will veto the evaluation as non-falsifiable.

(b) SAMPLE-OVERLAP PROTECTION:
The OOS holdout windows for vol_target_carry (validated 2026-04-25) and
FRED-carry Bet #1 (validated 2026-04-27) must be treated as contaminated for
any new strategy that shares the same pair(s) and overlapping date range.
Specifically: USDJPY OOS data already consumed. Any new USDJPY strategy that
draws on the same post-2024 window has NOT produced independent OOS evidence.
QD must enforce non-overlapping OOS splits at trial-spawn time and flag
overlapping windows in the trial record. Without this, the family-wise false
discovery rate is unconstrained.

(c) THRESHOLD CHOICE RATIONALE:
R1 (0.30): Set above zero to exclude strategies that technically beat zero but
are within noise. Anchored below the validated baselines (0.76, 0.80) to
avoid treating the VALIDATED bar as the universal bar — that would be circular.
0.30 is a real but minimal evidence threshold for a daily-bar forex system.

R2 (0.50): A DSR below 0.50 means the observed Sharpe is indistinguishable
from what a random sweep of N=22 trials would produce by chance. This is
not conservative — it is the minimum for non-noise. Could argue for 0.65;
leaving at 0.50 because DSR computation has never been run on this harness
and calibration risk is high.

R3 (25%): Inherited from VTC-T2 (the only existing machine-checkable
drawdown criterion). I accept this anchor but note it is generous — 25% is
a severe drawdown for a daily-bar system. CRO may tighten to 20% at their
discretion before 2026-05-01; after that date it is frozen.

R4: Routed to HoQR — NHT does not have position-sizing models to estimate
capacity independently. This is a known gap, not an oversight.

R5 (p > 0.05): Standard alpha. K=200 permutations matches VTC-T8's precedent
(200 shuffled-vol signals). Aspirational only because the harness currently
emits null for permutation fields.

R6 (n_trades < 30, n_oos_bars < 252): Back-of-envelope: detecting Sharpe=0.5
vs 0 at 80% power requires ~64 independent trades; 30 is the floor below which
the test is essentially uninterpretable. 252 OOS bars = 1 year of daily data;
below this, annual Sharpe estimates are dominated by the start/end dates.

OVERALL: Phase 1 closed with ~0 falsifications across 22 trials. Phase 2 is
only meaningful if these criteria are applied mechanically and rejections are
recorded as rejections, not as "exploratory findings." The prior is that
every proposed strategy is noise. This rubric is the minimum evidentiary
bar for shifting that prior.

---

## 9. Tier A/B success criteria (verbatim from PM acceptance-criteria)

**Tier A — NHT discipline window (hard deadline 2026-05-15):**
- TIER-A-1: ≥5 trials.jsonl entries with status=rejected logged by 2026-05-15
- TIER-A-2: Each rejection references a pre-registered falsification criterion (field: falsification_criterion) declared BEFORE evaluation run
- TIER-A-3: NHT artifact (null-test-report) delivered and frozen before any Wave-3 QD evaluation begins
- TIER-A-4: HoQR prioritization artifact delivered listing ≥5 ranked candidate hypotheses with falsification criterion sketches

**Tier B — CONDITION-1 (gates paper launch):**
- TIER-B-1: ≥10 trials.jsonl entries with status=rejected
- TIER-B-2: Archived Phase 0 baselines (ma_crossover, bollinger_rsi, momentum, carry, carry_momentum) are IN-SCOPE as low-cost explicit-falsification candidates — HoQR decides whether to include; PM does not prejudge
- TIER-B-3: Each rejection record includes: trial_id, strategy, rejection_reason, falsification_criterion (all fields per commit b56bd1a API)
- TIER-B-4: Sacred no_lookahead test continues passing after any QD harness changes
- TIER-B-5: QD harness-extension spec (implementation-report) delivered before Wave 3 execution begins

---

## 10. Conflict 2 decision required from CEO

**The problem:** Candidates 1–5 (archived baselines) share USDJPY post-2024 OOS data with vol_target_carry and FRED-carry Bet #1. Under NHT's append-only sample-overlap protection, these produce sensitivity analyses — not independent OOS evidence. Candidates 6 and 7 are the only queue items that count toward CONDITION-1. Maximum independent rejections from current queue: 2 (not 7). CONDITION-1 requires 10.

**CEO must pick at ratification:**

**(a) Accept reduced yield** — proceed as-is; `oos_overlap=true` trials logged as sensitivity analyses; CONDITION-1 target likely unreachable by 2026-06-23 → triggers HoQR alpha-thesis pivot Tier 1 kill. Fast but undermines CONDITION-1's evidentiary value.

**(b) Carve a new OOS window** — QD reserves a holdout window not consumed by any validated strategy (e.g., a pre-2022 block, or a EURUSD/GBPUSD-only sub-universe). Slows execution 1–2 weeks but preserves independence. Archived baseline rejections on that window count toward CONDITION-1.

**(c) Re-scope queue to non-USDJPY pairs** — HoQR drops USDJPY-only candidates; runs EURUSD-only and GBPUSD-only baselines + FRED-carry stripped + Bet #2. Produces independent rejections; reduces queue from 7 to ~4–5 effective items.

**PM recommends (b).** Preserves NHT's independence requirement without discarding the archived-baseline falsification work. Option (a) is fast but converts CONDITION-1 into a lower-integrity gate. Option (c) discards USDJPY signal that is already partly computed.

---

## 11. Wave-3 dispatch readiness

**Immediately unblocked after CEO ratification:** QD sub-wave 3a — DSR implementation + backfill + pre-reg parser + evaluator. No other role needed for 3a.

**Blocked until 3a complete:** Pre-reg authoring (3b) waits on parser design confirmation.

**Blocked until 3a + 3b + Conflict 2 CEO decision:** Trial execution (3c). Candidates 6 and 7 additionally need NHT window approval and R2 finalization respectively.

**Automatic:** Tier A/B verification (3d) runs as trials complete; no separate dispatch.

**Phase 2 ran clean.** No new policy violations in Wave 2. Phase 1's retail FX paper venue violation was surfaced in CONSENSUS_2026-04-28.md Section 10 and is not re-surfaced here.

---

## 12. Signatures

- **HoQR** — `prioritization` artifact, decision: `approve-with-capacity-limit`
- **NHT** — `null-test-report` (frozen-rubric), decision: `pre-registered-frozen`; DISSENT preserved Section 8
- **QD** — `implementation-report` (spec-completion), decision: `spec-completion`
- **PM** — drafted this consensus
- **CTO** — absent; Phase 1 architecture closed; no re-decisions in scope
- **CRO** — absent; risk envelope inherited immutably from CONSENSUS_2026-04-28.md

---

## 13. CEO ratification

Must:
1. Acknowledge NHT dissent in writing (Section 8)
2. Pick (a), (b), or (c) on Conflict 2 (Section 10) — this gates trial execution
3. Authorize Wave 3 sub-wave 3a dispatch (QD-only at first; no other roles unblocked yet)

---
**File path:** `docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md`
