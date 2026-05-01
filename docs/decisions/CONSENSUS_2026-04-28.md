# CONSENSUS — Trading System Direction v1
**Date:** 2026-04-28
**Horizon:** 12 weeks → 2026-07-21
**Status:** Draft — awaiting CEO ratification
**Roles signed:** CTO, Head of Quant Research, CRO, Null-Hypothesis Tester, PM (this draft)

---

## 1. North-star

"Make money." Operationalized as: paper-traded Sharpe ≥ 0.5 OOS within 12 weeks on the EURUSD/USDJPY/GBPUSD universe, paper-only, no live capital. Cull authority granted to CTO for in-flight architecture items. Alpha cull authority retained by HoQR. Risk envelope set by CRO unconditionally. NHT dissent is structurally append-only and survives this consensus.

---

## 2. The signed direction

The load-bearing alpha thesis is carry-family: vol_target_carry (OOS Sharpe 0.7594, engine-validated 2026-04-25) and FRED-carry Bet #1 (OOS Sharpe 0.80, BoJ-divergence-conditional). Both strategies demonstrate interest-rate differential persistence amplified by central-bank policy divergence. Signal diversity should come from regime conditioning on FRED macro data, not new indicator families.

**Per-item verdicts:**
- **vol_target_carry:** KEEP — anchor strategy, cleared gate-chain, promoted to paper pending Phase 1 completion.
- **FRED-carry Bet #1:** PROMOTE-TO-PAPER — conditional on CF-T9 monitor active and HoQR sign-off documented in trials.jsonl (CTO CONDITION-5).
- **Trial factory:** KEEP — but falsification-logging path must be verified; factory must be able to emit `status: rejected` entries before next trial.
- **Bet #2 (tas_ceiling_4h):** BLOCKED — hard gate on R2 pre-registration. No backtest executes before R2 is timestamped.
- **Path B paper competition:** DEFERRED — A4/H1/R1-signoff/N1-N3 governance gates not cleared; architectural prerequisite is ≥1 complete paper-trading cycle with equity curve.
- **ma_crossover / bollinger_rsi / momentum:** ARCHIVE — no independent alpha thesis versus validated carry strategies.
- **carry / carry_momentum:** ARCHIVE — subsumed or pending FRED-carry dominance confirmation.
- **8 exploratory scripts (commit 60875e1):** BULK-ARCHIVE — backfilled to trials.jsonl for DSR accounting; treated as hypothesis-generation, not validated alpha.
- **CONSENSUS docs at root:** MIGRATE to `docs/decisions/` per CTO CONDITION-3 (Wave 3 action).

---

## 3. Reconciled 12-week sequencing

**Phase 1 (weeks 1–4) — Falsification pipe + risk plumbing prerequisites:**
Close the falsification-logging gap: trial factory must emit `status: rejected`; achieve ≥3 OOS rejections in trials.jsonl. Verify policy-violations.jsonl write path end-to-end via canary test within 3 days. Build CRO cross-strategy aggregated-exposure gate (JPY-correlated notional ≤15% of book). Deploy heartbeat/dead-man watchdog with ≤5min timeout on paper-trading loop. Clear remaining governance gates (A4/H1/R1-signoff/N1-N3). Migrate CONSENSUS docs to `docs/decisions/`.

**Phase 2 (weeks 5–8 — earlier if Phase 1 complete by week 3):**
Paper launch vol_target_carry + FRED-carry Bet #1 (conditional on CF-T9 monitor active and HoQR sign-off in trials.jsonl). Bet #2 backtest IF R2 pre-reg cleared. KillSwitch halt path must fire at least once (synthetic or real) to prove halt path. Run paper competition between ≥2 strategies.

**Phase 3 (weeks 9–12):**
Culling cycle. Retire any strategy that has not beaten vol_target_carry Sharpe in paper over ≥30 days. Regime-filter extension on vol_target_carry (FRED JPY policy-rate differential conditioning). Path B competition only if ≥2 surviving strategies. No new strategies without a complete prior-cycle rejection logged in trials.jsonl.

**Note:** HoQR's week 1–2 paper-launch sequencing is reconciled to week 3–5 or later, pending CRO binding constraints, CTO Phase 1 conditions, and NHT's falsification-discipline gate (2-week window, ≥5 logged rejections).

---

## 4. CRO binding constraints (unconditional)

From `cro-risk-assessment.yaml` — these are non-negotiable prerequisites for all paper-trading dispatch:

1. **Cross-strategy JPY-correlated notional must not exceed 15% of paper book at any bar before any new trial dispatches.**
2. **No paper-trading dispatch unless a heartbeat/dead-man watchdog with ≤5min timeout exists on the paper-trading loop.**
3. **Every pre-registered trial must declare its kill-switch threshold verbatim in trials.jsonl pre-reg entry before first bar executes.**

Additional risk envelope:
- `size_multiplier`: 0.5 (effective risk_per_trade_pct = 1%)
- `max_active_paper_strategies`: 4
- `max_trial_budget_12wk`: 36 (current 22 + 14 new ceiling; ~1.2/week)
- `max_concurrent_open_positions`: 6 (2 per pair max)
- JPY-correlated notional ≤15% of book
- Leverage ladder: 1.0x (low-vol), 0.75x (medium-vol), 0.25x (high-vol)
- Drawdown contract: paper-equity DD ≥10% → halt new trial dispatch | DD ≥15% → reduce all sizing to 0.5x | DD ≥20% → full halt pending CRO review

---

## 5. CTO conditions (must be met before gated items proceed)

From `cto-architecture-review.yaml`:

- **CONDITION-1:** Falsified-hypothesis log must reach ≥10 OOS-rejection entries in trials.jsonl before any new strategy enters paper trading.
- **CONDITION-2:** policy-violations.jsonl logging path verified end-to-end (canary violation + confirm appears) within 3 days.
- **CONDITION-3:** CONSENSUS docs migrated to `docs/decisions/` and root cleaned within current sprint.
- **CONDITION-4:** Bet #2 backtest pre-reg (R2) submitted and timestamped before any backtest run executes.
- **CONDITION-5:** HoQR sign-off on Bet #1 regime-concentration risk documented in trials.jsonl before Bet #1 enters paper competition.

---

## 6. HoQR retirement criteria (per surviving strategy)

From `hoqr-prioritization.yaml`:

- **vol_target_carry:** retire if rolling 60-bar OOS Sharpe < 0.30 OR max drawdown > 25% in paper trading.
- **FRED-carry Bet #1:** retire if CF-T9 monitor triggers OR BoJ-divergence regime flag inactive > 30 consecutive trading days with Sharpe < 0.40.
- **Bet #2 (tas_ceiling_4h):** retire-before-launch if R2 pre-reg not cleared within 2 weeks of queue activation; retire post-launch if OOS Sharpe < 0.30 at 6-week mark.
- **ma_crossover / bollinger_rsi / momentum:** archive on paper-trading launch date — no incremental alpha thesis versus validated strategies.

---

## 7. Disagreement matrix

**Conflict 1 — paper-launch timing:** HoQR sequenced vol_target_carry and Bet #1 at weeks 1–2. CTO placed paper launch in Phase 2 (weeks 5–8), contingent on falsification pipe being proven in Phase 1. NHT dissented on proceeding without 2-week falsification-logging discipline and ≥5 logged rejections. CRO added unconditional binding constraints (aggregation gate, heartbeat watchdog) that must precede any dispatch. **Reconciliation by stacking:** CRO constraints + CTO Phase 1 conditions + NHT pre-launch discipline gate push HoQR's week 1–2 sequencing to week 3–5 at earliest, conditional on all gates met.

**Conflict 2 — kill date scope:** CTO's kill date 2026-07-21 is a project-halt trigger (end of 12-week horizon). HoQR's kill date 2026-06-23 is an alpha-thesis pivot trigger (mid-horizon). These are different scopes and not in conflict. Both are preserved: Tier-1 (alpha-thesis pivot, HoQR, 2026-06-23) and Tier-2 (project halt, CTO, 2026-07-21). See Section 9.

**Conflict 3 — Bet #1 authorization path:** HoQR holds lane authority over alpha promotion decisions. NHT's dissent on DSR distinguishability of FRED-carry Bet #1 is preserved verbatim (Section 8). CTO routed the Bet #1 alpha question to HoQR. No role-hybridization conflict; dissent is structural, not a veto.

---

## 8. NHT dissent (VERBATIM — APPEND-ONLY — DO NOT EDIT)

Per fintech-org rule 6, the following dissent is structurally preserved and survives consensus regardless of others' agreement. The CEO is required to read this verbatim before ratifying.

---

> DISSENT (append-only; survives regardless of CTO/HoQR/CRO agreement):
>
> The skill's own kill criterion requires BOTH a paper-traded PnL curve AND >=20
> falsifications logged after 8 weeks. This project fails BOTH conditions after ~4 days
> of intensive activity: (a) No paper-traded PnL curve exists - the three log files total
> 14.3KB and are smoke tests, not longitudinal P&L records. (b) Of 22 trials, approximately
> 1 mentions retire/falsif/kill. This is not a minor shortfall. It is a categorical failure
> of the falsification-archive hypothesis itself.
>
> The meta-observation is damning: 22 trials WITHOUT falsifications is itself a falsification
> of the claim that this org falsifies. An org that runs 22 trials and records 0 rejections
> is not testing hypotheses - it is accumulating candidates. Candidate accumulation without
> rejection logging IS the multiple-comparisons problem in organizational form.
>
> The two validated strategies (Sharpe 0.7594, 0.80) survive DSR sketch ranges of 0.4-0.6
> and 0.5-0.7 respectively - both at the edge of distinguishability from noise, not
> comfortably above it. With >20 sweep configs executed, the effective trial count for
> multiple-comparisons purposes likely exceeds 22, further deflating these estimates.
>
> RECOMMENDATION: Before any new strategy enters the queue, a falsification-logging gate
> must be enforced. Specifically: each trial must conclude with an explicit PASS or FAIL
> verdict logged with the falsification criterion that was evaluated. Absence of
> falsification logging is not evidence of a clean record - it is evidence of an
> unaccountable process. The 12-week continuation cannot be justified on INSIGHT grounds
> until this discipline is demonstrated for at least a 2-week window with >=5 logged
> rejections.

---

## 9. Kill criteria

**Tier 1 — Alpha-thesis pivot (HoQR authority)**
- `kill_date`: 2026-06-23
- `kill_metric`: If neither vol_target_carry nor FRED-carry Bet #1 achieves paper-trading Sharpe ≥ 0.50 over rolling 60 trading days by 2026-06-23, AND Bet #2 has not cleared pre-reg with OOS Sharpe ≥ 0.50, then: halt all new pre-registrations, convene pivot review, consider universe expansion or strategy-class change outside carry family.

**Tier 2 — Project halt (CTO authority)**
- `kill_date`: 2026-07-21
- `kill_metric`: By 2026-07-21, if NOT (paper-traded equity curve exists with ≥30 trading days of bars AND trials.jsonl contains ≥10 entries with `status: rejected` AND at least 1 strategy has paper Sharpe ≥ 0.5 OOS) — then recommend project halt and full post-mortem. Sharpe alone is insufficient. ≥10 rejections is the architectural proof the falsification pipe runs.

---

## 10. Policy-violation log (first-class finding)

**This is a first-class governance finding, not a footnote.**

HoQR's original Wave-2 artifact (timestamp 2026-04-28T02:00:00Z) contained a broker name from the `broker_names` forbidden list (variant patterns matched twice — see `.fintech-org/policy-violations.jsonl` for the verbatim record) in the `body` and `assumptions` fields, in violation of fintech-org rule 1. The orchestrator rejected and respawned the artifact (attempt 2), then sanitized in-place: all references replaced with "retail FX paper venue (generic)." The substance of HoQR's prioritization was preserved unchanged.

**Logged to:** `.fintech-org/policy-violations.jsonl` at 2026-04-28T02:30:00Z and 2026-04-28T02:35:00Z.

**Implication:** Research-role artifacts must not reference broker names at any stage. Future CONSENSUS drafts and all Wave-N artifacts must use generic venue language only. The PM acceptance-criteria explicitly listed broker integration as out-of-scope; this violation occurred in the research body, not in a live-capital context, but the rule applies regardless. Orchestrator authority to sanitize in-place (step 9b) was correctly invoked.

---

## 11. Wave-3 dispatch readiness

**Unblocked after CEO ratifies this consensus:**
- QD can begin Phase 1 infrastructure work: falsification-logging verification, policy-violations canary test, CONSENSUS doc migration.

**Blocked until specific gates close:**
- Phase 2 paper launch (vol_target_carry + Bet #1): blocked on all CRO binding constraints + CTO CONDITION-1/2/5 + NHT 2-week falsification-discipline window (≥5 logged rejections).
- Bet #2 backtest: blocked on R2 pre-registration (CTO CONDITION-4).
- Path B competition: blocked on ≥1 complete paper-trading cycle with equity curve + remaining governance gates.
- New strategy pre-registrations: blocked until NHT gate is cleared (≥5 logged rejections in 2-week window).

**Dependency tree summary:** CRO binding constraints → all paper trading. NHT falsification-discipline window → new pre-registrations. R2 pre-reg → Bet #2. Phase 1 completion → Phase 2 launch.

---

## 12. Signatures

- **CTO** — signed via `cto-architecture-review.yaml` | decision: `approve-with-conditions`
- **Head of Quant Research** — signed via `hoqr-prioritization.yaml` | decision: `approve-with-capacity-limit`
- **CRO** — signed via `cro-risk-assessment.yaml` | decision: `size-reduced` (size_multiplier=0.5)
- **Null-Hypothesis Tester** — DISSENT | decision: `noise-indistinguishable` | structurally append-only; see Section 8
- **PM** — drafted this consensus

---

## 13. CEO ratification

Final approval or veto required from CEO. Before ratifying, the CEO must:
1. Read NHT dissent in Section 8 verbatim and acknowledge it in writing.
2. Confirm awareness that DSR-adjusted Sharpe estimates for both validated strategies (0.4–0.6 range) place them at the edge of noise distinguishability, not comfortably above it.
3. Authorize Wave-3 QD dispatch for Phase 1 infrastructure work only — no paper trading, no new backtests, until Phase 1 gates are confirmed closed.

---

**File path:** `CONSENSUS_2026-04-28.md` (repo root for now; will migrate to `docs/decisions/` per CTO CONDITION-3)
