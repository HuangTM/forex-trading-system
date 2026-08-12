# Consensus on: Research-design package for intraday-classical strategy #3 — session-boundary opening-range breakout (ORB) on FX majors

**Status:** RATIFIED — distributed quorum, ratified_with_dissent (PR + CRO + ET approve; NHT dissent preserved). DESIGN-stage only; NOT authorization to backtest/paper/deploy.
**Session:** /fintech-org "continue" → P3, 2026-05-30
**Track:** p3-intraday-orb-2026-05-30
**Mode:** autonomous default (no --require-ceo)

## Roles staffed
- **pm** (sonnet) — acceptance-criteria authoring, consensus drafting
- **quant-researcher** (opus → sonnet rework) — hypothesis, pre-registration, declarative TradeIntent spec
- **execution-trader** (sonnet) — intraday TCA / realized-slippage budget (dominant kill-risk)
- **cro** (opus, disjoint evidence) — independent position-sizing & tail-risk assessment
- **null-hypothesis-tester** (opus) — structural skeptic; multiple-testing, regime, lookahead traps
- **principal-reviewer** (opus) — independent design review (review wave); cycle-1 BLOCK, cycle-2 verification unobtainable

## Acceptance criteria (from PM)
Research-DESIGN only (no production code, no live capital, no ML). Deliverable = hypothesis + pre-registered falsification criteria + declarative TradeIntent spec + harness/validation design + TCA budget. Success metrics: pre-registration completeness (numeric, pre-data); net-of-cost OOS Sharpe gate; realized-slippage budget in pips per pair; bounded trade frequency; Execution-Researcher Firewall compliance (zero executable code); no-lookahead (entry_delay_bars≥1) preserved; NHT skepticism addressed; data feasibility confirmed.

## Decision
The org produced a complete, internally-consistent **research-design package** for an intraday session-boundary ORB strategy on FX majors (primary arm: EUR/USD + USD/JPY evaluated **per-pair**, not pooled; stretch arm: GBP/USD with a higher cost-aware bar, never pooled). After a Principal-Reviewer **cycle-1 BLOCK** (5 blocking findings), the Quant Researcher's **v2** package closes every blocking and spec-drift finding by encoding the owning roles' resolutions as binding declarative fields: sizing pinned to CRO's 0.25%/trade unconditional cap with full aggregate caps; fill model pinned to stop-limit/limit-on-retest at bid/ask (mid-price fills forbidden); session-aware entry-delay + signal-voiding rule for session/weekend/DST/17:00-ET-rollover boundaries; per-regime fat-tailed slippage distribution; and a **frozen** Deflated-Sharpe gate (N_total = N_org 35 + N_candidate 1 = 36, p≤0.05) with regime stratification (ADX-14 >25/≤25), jackknife floor (drop top-5 sessions, OOS Sharpe ≥0.15), and two negative controls — all frozen before any backtest.

**The org's overall posture is: this design is sound and implementation-ready in spec, BUT three blocking *implementation prerequisites* (KG-1/2/3) must be cleared before any backtest, and NHT's prior probability of a durable post-cost edge here is LOW.** No backtest was run this wave; org-wide trial count remains 35 (the candidate's trial is counted when the backtest actually runs).

**Ratification status: RATIFIED by distributed quorum (ratified_with_dissent).** PR **cycle-2 focused verification = APPROVE** (3 independent reproductions: opus + sonnet + sonnet; the opus run re-verified `engine.py:135/263` bar-index shift and `trials.jsonl`=35 against source). CRO quality-gate-review = APPROVE (`size_multiplier 1.0`; all unconditional caps respected; 11 binding constraints carried). ET quality-gate-review = APPROVE (cost treatment honest/adequate; 5 non-blocking impl-wave flags). Quorum checks all pass: 3 senior approvals; CRO present (risk domains); PR present (design artifact); no architecture *decision* made (engine-path deferred → CTO not required); forbidden-interim clean (design-only, no live capital); override breaker not fired (PR block→approve was the bounded rework loop); cross-session clean. Ratification artifact: `.agent-accountability/ratifications/p3-intraday-orb-2026-05-30:phase1:task1.0.yaml`. (NOTE: an earlier `review-budget-exceeded` artifact was a false alarm from a dropped display channel — superseded by `principal-reviewer-cycle2-review-report.yaml`.) **This ratifies the DESIGN only; the three blocking implementation prerequisites KG-1/2/3 and the CRO post-cost-expectancy kill-condition remain in force before any backtest.**

## Evidence supporting the decision
- PM acceptance-criteria: `.fintech-org/artifacts/2026-05-30T-p3-intraday-orb/` (task_id p3-intraday-orb-2026-05-30)
- QR v2 pre-registration + trade-intent (subtask_id p3-intraday-orb-2026-05-30-qr-rework): frozen params, FC-1..FC-10, per-regime slippage distribution
- ET TCA budget: round-trip cost EUR/USD 3.6 / GBP/USD 4.75 / USD/JPY 3.9 pips (session-open elevated); min gross edge 7.2 / 9.5 / 7.8 pips; verdict CONCERN (GBP/USD leaning FAIL); flagged config cost model 58–62% understated for session-open entries
- CRO risk-assessment (disjoint evidence): 0.25%/trade hard cap, 2.5% aggregate, EUR+GBP ≤1.5% (one correlated unit), effective independent bets ~1.5, leverage ≤3:1, 15% DD kill, 4% daily breaker; estimated DD 15–25% caged / 40–60% uncaged
- NHT review: effective trial estimate ~100–300 for this candidate alone; DSR must use org-wide N; demands regime-stratified + jackknifed OOS + negative controls
- PR cycle-1 review-report: decision BLOCK, 5 blocking findings (sizing self-veto, unspecified fill model, session-boundary lookahead, exit-vs-engine mismatch, spec incompleteness)
- org-wide trial count: `.fintech-org/trials.jsonl` = 35

## Orchestrator closure read of PR cycle-1 findings vs QR v2 (NOT an independent PR sign-off — surfaced transparently per cycle-2 fallback)
| Finding | Orchestrator read | Basis |
|---|---|---|
| B-1 sizing self-veto | closed | v2 per_trade_risk = 0.25%; all 0.5% refs removed; CRO aggregate caps enumerated |
| B-2 fill model | closed | stop-limit/limit-on-retest, NEVER market; bid/ask not mid (mid forbidden) |
| B-3 session-boundary lookahead | closed-as-design | session-aware delay + void-if-next-bar-outside-session declared; DST precedence; required tests; (implementation = KG-2/3) |
| B-4 exit vs engine | closed-as-design | intrabar-engine requirement declared as handoff; CTO owns engine path; (implementation = KG-3) |
| B-5 spec incompleteness | closed | per-regime slippage distribution declared; DSR N frozen at 36 before results |
| S-1..S-8 spec-drift | closed | ATR(14)/15m/OR-close/frozen; buffer price-units conservative tick; OR=min3–30; tie-break by construction; incomplete-OR skip; time-exit anchored to opening session; per-pair vs separate-stretch universe; hard freq cap |
| PR-PREREG binding | closed | N frozen=36; regime/jackknife/negative-controls frozen; universe resolved |

Orchestrator read = all 14 findings closed for the **design** deliverable, with KG-1/2/3 as **implementation** prerequisites (not design-stage blockers). **This read does not satisfy the structural-independence requirement** — a fresh PR cycle-2 (or CEO ratification) is needed to ratify.

## Decisions NOT made (deferred / out of scope)
- No backtest executed; no Sharpe claimed. No implementation code (firewall preserved).
- Engine-path decision (intrabar-capable engine) deferred to CTO + implementation wave.
- GBP/USD inclusion in production deferred to its separate higher-bar evaluation.
- Live capital: never in scope (Phase-0).

## Assumptions we're betting on
- Clean 15m intraday OHLCV for the three majors (2015–2024) is obtainable (KG-1, UNCONFIRMED — current pipeline is daily).
- A session-calendar module (IANA tz/DST/holiday) is buildable (KG-2).
- An intrabar-capable engine path is buildable without breaking the sacred `test_no_lookahead` (KG-3).
- ET session-open cost anchors and GBP/USD ~9.5-pip breakeven are representative (KG-4, unverified vs Saxo live data).

## Pre-registered falsification (verbatim from QR v2 pre-registration)
- FC-1 DSR p ≤ 0.05 at N_total = 36 (binding gate).
- FC-2 net-of-cost OOS Sharpe ≥ 0.30 (necessary-not-sufficient pre-filter).
- FC-3 per-pair admissibility: EUR/USD AND USD/JPY each independently pass; pooling forbidden; GBP/USD separate.
- FC-4 ≥ 200 OOS trades per claimed arm.
- FC-5 OOS Sharpe positive in ≥ 3 of 5 walk-forward folds.
- FC-6 regime stratification ADX(14) >25 trend / ≤25 chop, frozen; reported separately; must not collapse to top-5% vol sessions.
- FC-7 jackknife: drop top-5 sessions → OOS Sharpe ≥ 0.15.
- FC-8 two negative controls (random-timestamp session + non-universe pair); reject if either ≥ 80% of primary Sharpe.
- FC-9 no post-data parameter edits (resets holdout).
- FC-10 15% drawdown hard-stop.

## Dissent (preserved verbatim)

### Null-Hypothesis Tester dissent
> No blocking dissent at the design stage; design is the correct place to bind this candidate and I do not veto running the wave. However, I record the following structural dissent to be preserved verbatim in CONSENSUS and carried into any later ratification: (1) Intraday session-boundary ORB is a member of the most over-fit, most-arbitraged strategy family in retail FX; the prior probability that a durable post-cost edge exists here is LOW, and the org-wide accumulated trial count means the multiple-testing penalty against this candidate is SEVERE. (2) This candidate must NOT be evaluated against the legacy 0.30 carry threshold or any pooled single-Sharpe gate; it must clear a Deflated-Sharpe bar computed against the documented firm-wide N, on locked pre-registered parameters, with regime-stratified and jackknifed OOS. (3) If the pre-registration is not committed and parameter-frozen BEFORE the first backtest run, I treat any subsequent positive result as data-snooped and will not withdraw the null hypothesis regardless of consensus. (4) Even a passing result is only a green light to PAPER, never to live capital (Phase-0 invariant); event-exposure overlap with the existing carry/FRED book must be checked before this is counted as independent alpha. This dissent cannot be overridden by consensus and must travel with the artifact.

### CRO (no formal dissent artifact; risk-assessment binding constraints carried into spec)
CRO's caps are encoded as binding spec fields; CRO veto conditions remain in force (any path exceeding 0.25%/trade, 2.5% aggregate, EUR+GBP 1.5%, 3:1 leverage, or omitting the cost model → HALT; negative measured post-cost expectancy → no size is safe).

## Independent review findings (Principal Reviewer)
**Cycle 1 (verbatim, decision = BLOCK):** 5 blocking findings — (1) sizing self-veto (QR 0.5% vs CRO 0.25% cap+veto); (2) thesis-critical unspecified fill model (QR next-bar/market vs ET no-market-orders, mid-price fills make edge an artifact); (3) session-boundary lookahead gap (engine shifts by bar-index `engine.py:135/263`, no session awareness); (4) per-trade ATR bracket + time exits not satisfiable by sign-based discrete engine; (5) spec incompleteness (no per-regime slippage distribution; DSR N not frozen). Plus spec-drift S-1..S-8 and pre-registration-binding concerns routed to NHT.

**Cycle 2 (focused verification): APPROVE — 14/14 findings closed, reproduced across 3 independent dispatches** (opus `a982e24625248e7fc` source-verified; sonnet `a3e284cf567fa9479`; sonnet `ab426eaae2e8b2227`). Report: `.fintech-org/artifacts/2026-05-30T-p3-intraday-orb/principal-reviewer-cycle2-review-report.yaml`. B-3/B-4 closed-as-design (declarative handoff forbidding silent implementer drift); KG-1/2/3 confirmed as implementation prerequisites, not design-stage blockers. The orchestrator closure-read table above was independently confirmed by PR. (The earlier `review-budget-exceeded` note was a false alarm from a dropped display channel — VOID/superseded.)

Plus quality-gate-review approvals on the v2 package: **CRO** (`cro-quality-gate-review-v2.yaml`, approve, size_multiplier 1.0, 11 binding constraints) and **ET** (`execution-trader-quality-gate-review-v2.yaml`, approve, 5 non-blocking flags).

## Knowledge gaps surfaced (routed to skill-gap loop)
- KG-1 (quant-researcher): intraday 15m OHLCV for EUR/USD, USD/JPY, GBP/USD 2015–2024 not confirmed in pipeline (daily only) — **blocking prerequisite**.
- KG-2 (quant-researcher): no session-calendar module (IANA tz/DST/holiday) in codebase — blocking-for-implementation.
- KG-3 (quant-researcher): no intrabar-capable engine path (current engine sign-based discrete) — blocking-for-implementation.
- KG-4 (execution-trader/quant-researcher): Saxo session-open spread + commission + GBP/USD breakeven not verified against live data.
- (execution-trader): fat-tailed slippage distribution parameters need tick-level fill data.

## Signatures
- pm: @a734dcf0cc22e4105 (acceptance-criteria)
- quant-researcher: @a5bca75fb48fb4b5b (cycle-1) / @a3c22aa7bccd12a34 (v2 rework)
- execution-trader: @ad09e92a9740d239b
- cro: @a05b5f7c1e33a341d
- null-hypothesis-tester: @a5209f011674452d1 (dissent preserved verbatim above)
- principal-reviewer: @a7be3f799bcae49d7 (cycle-1 BLOCK) → cycle-2 APPROVE @a982e24625248e7fc / @a3e284cf567fa9479 / @ab426eaae2e8b2227 (3 independent reproductions)
- cro: @a8dc1034a63d25c41 (v2 quality-gate-review: approve, size_multiplier 1.0)
- execution-trader: @af004478e15a5cedc (v2 quality-gate-review: approve)
- **Ratification: RATIFIED by distributed quorum (ratified_with_dissent)** — signers: principal-reviewer, cro, execution-trader. Artifact: `.agent-accountability/ratifications/p3-intraday-orb-2026-05-30:phase1:task1.0.yaml`. DESIGN-stage only.
