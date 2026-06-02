# Consensus on: Honest System Review — 8-Week Audit

**Status:** awaiting-ratification (CEO)
**Session:** honest-system-review-2026-05-31
**Deliverable type:** audit
**Escalation reason:** PR BLOCKING finding (F-001: DSR degenerate) + NHT structural dissent → distributed-ratification auto-quorum rule NOT met; escalates to CEO per protocol.

---

## Decision

**The system has NOT demonstrated a validated edge. The governance apparatus has outrun the shippable product.**

After 8 weeks, zero claims survive rigorous scrutiny as validated alpha:
- vol_target_carry USDJPY is in-sample, below the minimum trade count, and its DSR score is a degenerate computation.
- carry_fred OOS Sharpe is a regime-conditional artifact for JPY pairs only; the multiplicity-adjusted test (block permutation / Reality Check) has never been run.
- momentum EURUSD marginally clears R1 (0.31 vs 0.30 threshold) on a broken DSR gate and unverified net-of-cost basis.

The DSR computation (F-001) is a BLOCKING defect confirmed by the Principal Reviewer via execution: `dsr.py::compute_dsr` divides an annualized Sharpe numerator by a per-observation standard error, producing z-scores of 10–30 and `norm.cdf→1.0`. A correctly-scaled DSR would score the "passing" trials at 0.02–0.27, all BELOW the 0.50 gate. All prior trial "pass" designations are invalidated.

Two paper-equity series diverge without reconciliation. The authoritative drawdown-contract series carries zero cost accrual (swap_usd=0.0 confirmed). All paper "edge" figures are non-evidentiary until BC-COST-RECON is resolved.

57 commits unpushed to origin/main constitute a business-continuity risk (total-loss-on-hardware-failure). Push is blocked pending secrets purge of 4 historic commits containing Saxo account-key literals.

The NHT structural dissent (Section 7) is preserved verbatim and must not be softened.

---

## DIM-1: Implemented vs Claimed

**Verdict: MIXED — infrastructure substantially complete; claims overstated**

The CTO confirmed all major modules as implemented-and-tested: core engine, data pipeline, features, costs (RealisticCostModel), backtest engine, walkforward, sizing, harness (run_trial / sweep / preregistration / DSR / falsification_evaluator), analysis, paper/base_runner (7 COND guards extracted and tested), risk (kill_switch, drawdown_contract, exposure_aggregator, heartbeat_watchdog, account_key_parity), saxo (auth/client/execution/history), ops.

Two modules have no dedicated tests: `analysis/reports|visualization|comparison` and `saxo/history` (thin coverage).

The TasCeiling4hStrategy is a daily-bar strategy, NOT the P3 intraday ORB. P3 still requires 3 infra builds not yet completed: 15-minute data pipeline, session-calendar module, intrabar engine. The naming is confusing and the claim of P3 readiness is premature.

The paper log is contaminated: 485/607 entries show equity=100,000 (test mock value) versus 39 entries at 1,000,000 (real Saxo notional). These are indistinguishable without filtering, undermining paper-trading observability.

**Execution-Firewall finding (CTO):** `RealisticCostModel()` is instantiated at module level using the default constructor with no config reference. This is a firewall PASS with finding — costs are computed, but the instantiation pattern decouples cost configuration from the config-driven architecture.

---

## DIM-2: Alpha Evidence

**Verdict: NO VALIDATED EDGE — all claims rejected or marginal-on-broken-gate**

### CLAIM A: vol_target_carry USDJPY — Sharpe 0.7594
- **Head of Quant Research verdict: RETIRE**
- In-sample (oos=false), n_trades=23 (fails R6 minimum of 30).
- Same config produced 0.065 / -0.076 / 0.598 / 0.759 across re-runs — parameter instability, a Lopez-de-Prado overfitting tell.
- DSR=1.0 is a degenerate computation (confirmed F-001, see DIM-5 / Principal Reviewer section).
- This claim must not be characterized as a validated edge.

### CLAIM B: carry_fred portfolio — OOS Sharpe 0.7964
- **Head of Quant Research verdict: RETIRE unconditional claim**
- Edge exists only in OOS window; full-period and in-sample Sharpes are approximately zero or negative for JPY pairs.
- Non-JPY pairs show no edge even OOS.
- Median 6 trades per pair (73 total across 12 pairs); selecting across 12 pairs in a single OOS window is the expected source of an inflated portfolio Sharpe.
- Block-permutation / matched-random Reality Check (R5) has NEVER been run.
- **PR correction (CLAIM-5):** Audit originally overstated that ALL pairs were ~0/negative. CADJPY is a counterexample: full-period Sharpe 0.305, in-sample 0.196 (both positive). The thesis holds for 4/5 JPY-adjacent pairs. This correction is recorded; it does not alter the HoQR or NHT verdict on CLAIM B.

### CLAIM C: momentum EURUSD — Sharpe 0.31 (n=126, oos=TRUE)
- **Head of Quant Research verdict: KEEP as paper canary only; not a validated edge**
- Clears R1 (0.30) by one basis point on a saturated DSR and unverified net-of-cost basis.
- A marginal pass on a broken deflation gate is not robust alpha.
- This is the ONLY honest survivor in the candidate set.

### Baselines (ma_crossover, bollinger_rsi)
- **DEAD.** ma_crossover EURUSD: Sharpe -0.31, return -39%, max drawdown 49%.
- Correctly rejected; no further analysis warranted.

### Falsification Archive
- **UNHEALTHY.** CONDITION-1 (≥10 STRONG OOS rejections) at 2/10.
- Tier-A deadline (≥5 STRONG rejections by 2026-05-15) has PASSED without being met.
- Zero new STRONG-rejection trials scheduled.
- Falsified-hypothesis log holds 12 entries (< 20 required by kill criterion).

---

## DIM-3: Risk Posture

**Verdict: YELLOW — safety scaffolding wired to wrong signal; tail risk unmeasured; kill-switch drill not executed**

CRO decision: size-reduced (audit context). Blowup analog: Knight Capital + LTCM. Contamination check: clean.

### Five binding constraints (CRO):

**BC-COST-RECON (CRITICAL):** Two divergent equity series exist. `equity` (broker snapshot, flat) feeds the drawdown contract. `paper_equity_bt_equiv` (cost-adjusted) feeds nothing. Costs ARE computed (CRO notes up to 9,034.94 in cost_usd) but never reconciled into the authoritative series. The drawdown contract triggers on cost-free equity. All paper "edge" figures are NON-EVIDENTIARY until this is resolved.

Note: the CRO corrects an earlier formulation — cost_usd is NOT approximately zero; it IS computed. The defect is that the cost-adjusted series does not feed the authoritative risk control.

**BC-ES (HIGH):** No Expected Shortfall / CVaR anywhere in `src/`. Grep confirms zero hits. Tail risk is measured VaR-style only. This is the LTCM failure mode — the system is blind to tail events the variance doesn't capture.

**BC-KILLSWITCH-PROD-TEST (HIGH):** kill_switch and flatten audit trail are present and structurally wired. However, no timed in-production drill has been executed. kill-switch-design Properties 3 and 4 are unmet. A kill switch that has never been drilled under pressure is an untested assumption.

**BC-SECRETS-PURGE (BLOCKING for push):** 4 historic commits retain Saxo account-key literals in pre-rewrite content. Push-before-purge would publish them. The binding order is purge-then-push.

**BC-ACCOUNT-KEY-PARITY (MEDIUM):** Mitigation exists (`account_key_parity.py` with O_EXCL atomic lock — confirmed by PR). However, the reject-path has never been adversarially tested. The drawdown contract is present and wired but fed the cost-free series (see BC-COST-RECON).

---

## DIM-4: Infrastructure vs Insight (Kill Criterion)

**Verdict: INFRASTRUCTURE — kill criterion is met; system has produced infrastructure, not validated insight**

The kill criterion (verbatim from NHT, Section 7): "if after 8 weeks of use there is no paper-traded P&L curve AND no falsified-hypothesis log with >= 20 entries, the skill is producing infrastructure, not insight."

**Both conjuncts are met:**

1. No paper-traded P&L curve: paper log shows flat equity (~100,000 mock values dominating), single notional jump on 2026-05-31 attributable to real Saxo session. No accumulated P&L curve from live paper trading.

2. Falsified-hypothesis log: 12 entries (< 20 required); 0 STRONG OOS rejections (< 10 required by CONDITION-1); Tier-A deadline 2026-05-15 passed without being met.

**By its own declared kill criterion, after 8 weeks this system has produced INFRASTRUCTURE, NOT VALIDATED INSIGHT.**

The infrastructure is substantial and genuinely useful: no-lookahead sacred test confirmed genuine (PR CLAIM-7), backtest engine vectorized and correct, walk-forward implemented, DSR gate exists (defective computation, but architecturally present), kill switch wired. This infrastructure is the right foundation. The insight has not followed.

---

## DIM-5: Gaps / Tech-Debt

**Verdict: SIGNIFICANT — one SEV-1 business-continuity risk; three SEV-2/3 correctness risks; DSR gate broken**

CTO severity classification:

| ID | Severity | Description |
|----|----------|-------------|
| SEV-1 | BLOCKING for push | 57 commits unpushed to origin/main — total-loss-on-hardware-failure risk |
| SEV-2 | HIGH | swap_usd=0.0 on all paper cycles (base_runner.py:577-581 + run_paper_trading_vt.py:121, `_last_cycle_ts` resets per process). Carry strategies' paper edge systematically overstated. |
| SEV-3 | HIGH | watchdog observer loop (heartbeat_watchdog.py:172-199) has no outer exception guard — dead-man switch can silently die. Known since 2026-05-03, still open. |
| SEV-4 | MED | TasCeiling4hStrategy is a daily-bar strategy, not the P3 intraday ORB. P3 requires 3 additional infra builds. Naming confusion. |
| SEV-5 | MED | Paper log contaminated — 485/607 entries equity=100,000 (test mock) vs 39 at 1,000,000 (real Saxo); indistinguishable without filtering. |
| SEV-6 | LOW | ruff ~59 errors (unverified current count per CTO) |
| SEV-7 | LOW | 768 sweep configs in working tree; should be gitignored |

**F-001 (BLOCKING):** DSR computation is degenerate. See Principal Reviewer section below for full root-cause. This invalidates all prior trial pass/fail designations.

**pytest result:** 851 passed, 1 FAILED (9m47s). The failure is `tests/governance/test_policy_violations_canary.py` — line 5 of `.fintech-org/policy-violations.jsonl` is missing the required `action` field (governance-log schema drift; an NHT false-positive entry from 2026-05-11). Core trading and backtest-engine tests pass; the failure is in the self-governance layer only.

---

## Section 6: Principal Reviewer Findings

**Decision: approve-with-conditions (contamination check: clean)**

The Principal Reviewer independently verified 7 claims by reading AND executing source code.

### F-001 (BLOCKING): DSR computation degenerate — root-caused

**CLAIM-1 CONFIRMED + ROOT-CAUSED.**

`dsr.py::compute_dsr` (the function that `run_trial` actually calls) divides an ANNUALIZED Sharpe numerator by a PER-OBSERVATION standard error. This produces z-scores of approximately 10–30 regardless of Sharpe ratio, causing `norm.cdf → 1.0`. The function behaves as a sign function, not a probabilistic deflator.

Executed verification: SR 0.31 → DSR 0.999; SR 0.598/0.759 → DSR 1.0.

A correctly-scaled DSR would score these 0.02–0.27 — ALL BELOW the 0.50 gate. Trials currently characterized as "passing" would FAIL under a correct implementation.

Two duplicate DSR implementations exist: `deflated_sharpe.py` (unused) and `dsr.py` (active). Both contain the same defect.

**Routes to: Mathematician for correct implementation.** This is a BLOCKING finding. No trial result produced under the current DSR implementation is reliable as a pass/fail signal.

### Correction of CLAIM-2: DSR uses per-trial not org-wide N — REFUTED (audit overstatement)

The audit claimed the DSR uses a per-trial N rather than the org-wide cumulative count. The Principal Reviewer confirms this is an OVERSTATEMENT: the DSR does use the org-wide cumulative count; the field is misleadingly named but the value is correct. **This portion of the original audit claim is retracted.** F-001 stands on the scaling defect alone, not on the N-source defect.

### CLAIM-3: swap_usd=0.0 — CONFIRMED
Paper cycle swap accrual is zero. Confirmed at base_runner.py:577-581 and run_paper_trading_vt.py:121.

### CLAIM-4: Trial figures — CONFIRMED
Trial performance figures match source output.

### CLAIM-5: carry_fred ALL pairs ~0/negative — PARTIALLY-CONFIRMED (audit overstatement, corrected)

The original audit stated ALL pairs show ~zero or negative full-period and in-sample Sharpes. This is an OVERSTATEMENT. CADJPY is a confirmed counterexample: full-period Sharpe 0.305, in-sample Sharpe 0.196 (both positive). The broader thesis (most JPY-adjacent pairs lack durable edge; non-JPY pairs no edge OOS) holds for 4/5 pairs. **The overstatement is retracted; the thesis is narrowed but not overturned.**

### CLAIM-6: No ES/CVaR; O_EXCL lock; drawdown wired — CONFIRMED
- No Expected Shortfall / CVaR in src/ (grep zero hits). Confirmed.
- account_key_parity.py uses O_EXCL atomic lock. Confirmed.
- Drawdown contract present and wired. Confirmed (wired to cost-free equity series per BC-COST-RECON).

### CLAIM-7: No-lookahead sacred test genuine — CONFIRMED with caveat
Sacred test `test_no_lookahead` confirmed genuine — the guard is conditional on Sharpe < 3.0. The threshold is loose; a strategy with SR > 3.0 would bypass the lookahead check. This is a low-severity finding and does not invalidate the test for the current strategy universe (all strategies fall well below SR 3.0).

---

## Section 7: NHT Structural Dissent

**Dissenter:** null-hypothesis-tester
**Severity:** block-threshold
**does_block:** true (escalation condition met: no STRONG OOS rejections, kill criterion both conjuncts met)
**Append-only: this text is preserved verbatim and must not be edited, summarized, or softened.**

---

"I dissent. As Null-Hypothesis Tester I find that NONE of CLAIM A, B, or C constitutes a validated edge distinguishable from noise, and META-CLAIM D is FALSE by the skill's own verbatim kill criterion. Specifically: - CLAIM A is in-sample (oos=false), rests on 23 trades (fails R6 n_trades>=30), and its dsr=1.0 is a degenerate computation, not evidence. It must not be characterized as a validated edge. - CLAIM B's portfolio Sharpe 0.7964 is the expected artifact of selecting across 12 pairs (median 6 trades each, 73 total) in a single OOS window where full-period and in-sample Sharpes are ~zero or negative. The mandatory falsification test (block-permutation / matched-random Reality Check) has NEVER been run. An OOS-only effect that disappears in-sample, untested against multiplicity, is noise until proven otherwise. I withhold any 'passing' characterization. - CLAIM C narrowly clears R1 (0.31 vs 0.30, one basis point) on a saturated DSR and an unverified net-of-cost basis. This is a marginal pass on a broken deflation gate, not robust alpha. - META-CLAIM D: by the kill criterion verbatim — 'if after 8 weeks of use there is no paper-traded P&L curve AND no falsified-hypothesis log with >= 20 entries, the skill is producing infrastructure, not insight' — the system FAILS BOTH conjuncts: the paper log shows no accumulated P&L curve (flat equity, ~zero cost, single notional jump on 2026-05-31), and the falsified-hypothesis log holds 12 entries (< 20) with 0 STRONG OOS rejections (< 10, CONDITION-1 unmet, Tier-A deadline 2026-05-15 already passed). By its own definition, after 8 weeks this system has produced INFRASTRUCTURE, NOT VALIDATED INSIGHT. This dissent is to be preserved verbatim in CONSENSUS.md and not softened."

---

**NHT additional flags (outside verbatim dissent):**
- R2/DSR gate non-functional (confirmed by F-001).
- R5 permutation test never operationalized.

---

## Section 8: Risk Binding Constraints (full)

| Constraint | Status | Priority |
|------------|--------|----------|
| BC-SECRETS-PURGE | OPEN — 4 historic commits; push blocked | BLOCKING for push |
| BC-COST-RECON | OPEN — drawdown fed cost-free series; all paper figures non-evidentiary | CRITICAL |
| BC-ES | OPEN — no ES/CVaR in src/ | HIGH |
| BC-KILLSWITCH-PROD-TEST | OPEN — no timed in-prod drill executed | HIGH |
| BC-ACCOUNT-KEY-PARITY | PARTIAL — O_EXCL present; reject-path not adversarially tested | MEDIUM |

---

## Section 9: Open Items / CEO Decisions Required

1. **PUSH COMMITS** — 57 commits unpushed; BC-SECRETS-PURGE must complete first (git history rewrite to scrub 4 commits with account-key literals). CEO must authorize the history rewrite + force-push, or direct an alternative. Blocking for business continuity.

2. **FIX DSR (F-001)** — Route to Mathematician for correct deflated Sharpe implementation. Until fixed, all trial pass/fail designations are unreliable. This invalidates the gate chain. Does CEO authorize a dedicated DSR fix dispatch?

3. **OPERATIONALIZE R5 PERMUTATION TEST** — Block-permutation / matched-random Reality Check has never been run. CLAIM B cannot be adjudicated without it. Does CEO authorize a dispatch to operationalize R5?

4. **FIX SWAP ACCRUAL (SEV-2)** — swap_usd=0.0 on all paper cycles; carry strategies' paper edge systematically overstated. Does CEO authorize a fix dispatch (base_runner.py:577-581 + run_paper_trading_vt.py:121)?

5. **GITIGNORE SWEEP CONFIGS (SEV-7)** — 768 sweep configs in working tree. Does CEO authorize adding sweep_configs/ to .gitignore?

6. **FIX GOVERNANCE CANARY** — `tests/governance/test_policy_violations_canary.py` fails due to missing `action` field in line 5 of `.fintech-org/policy-violations.jsonl`. Low-severity; schema drift from 2026-05-11. Does CEO authorize the schema fix?

7. **WATCHDOG EXCEPTION GUARD (SEV-3)** — heartbeat_watchdog.py:172-199 has no outer exception guard; dead-man switch can silently die. Known since 2026-05-03. Does CEO authorize fix?

8. **BC-COST-RECON** — Two equity series diverge without reconciliation; authoritative series carries no costs. Does CEO authorize the reconciliation work?

9. **NEXT RESEARCH DIRECTION** — Given NHT kill criterion fired and HoQR reject, does CEO authorize: (a) momentum EURUSD as sole paper canary, pending DSR fix? (b) new alpha search dispatch? (c) pause paper trading pending cost-reconciliation?

10. **SAXO_TOKEN REVOCATION** — 8 expired SAXO_TOKEN values remain in developer portal. CEO manual action required at Saxo developer portal.

---

## Signatures

| Role | Decision | Notes |
|------|----------|-------|
| CTO | approve-with-conditions | SEV-1..7 filed; governance apparatus outrun product; firewall PASS with finding on RealisticCostModel instantiation |
| Head of Quant Research | REJECT | No validated edge; all claims rejected or marginal-on-broken-gate; CONDITION-1 unmet; kill criterion fired |
| CRO | size-reduced (audit) | YELLOW posture; 5 binding constraints; blowup analogs: Knight Capital + LTCM |
| NHT | DISSENT (block-threshold) | Verbatim preserved in Section 7; does_block=true |
| Principal Reviewer | approve-with-conditions | F-001 BLOCKING confirmed by execution; 2 audit overstatements corrected (CLAIM-2, CLAIM-5 partial) |
| PM | author | Faithfully recorded; no adjudication; escalation to CEO per distributed-ratification protocol |

---

## Knowledge Gaps

- **DSR correct implementation** — The correct scaling for the Lopez-de-Prado deflated Sharpe ratio in this context (daily returns, varying n_obs) is a domain-specific mathematical question. Routes to Mathematician role.
- **Block-permutation / Reality Check operationalization** — R5 permutation test design for this strategy/pair universe has not been scoped. Routes to HoQR for specification before QD implementation.
- **Carry edge decomposition** — Whether CADJPY's positive full-period Sharpe is structural or regime-coincident is unresolved. Routes to future alpha-research dispatch.
- **Paper log filtering convention** — No documented convention for distinguishing mock (equity=100,000) from real (equity=1,000,000) entries in paper_trading_session.log. Routes to CTO for ops spec.

---

*This document is the authoritative source of truth for the 2026-05-31 honest system review. Produced by PM / Chief of Staff. All role findings recorded faithfully; no findings re-adjudicated.*
