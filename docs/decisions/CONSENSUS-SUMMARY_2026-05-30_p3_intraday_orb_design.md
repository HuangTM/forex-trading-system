# Consensus on: P3 intraday-classical ORB strategy #3 — research-design package (session-boundary opening-range breakout, FX majors)

**Status:** RATIFIED — distributed quorum (ratified_with_dissent: PR + CRO + ET approve; NHT dissent preserved). DESIGN-stage only — NOT authorization to backtest/paper/deploy.
**Full audit:** see `./CONSENSUS_2026-05-30_p3_intraday_orb_design.md`
**Session:** /fintech-org "continue" → P3, 2026-05-30 (autonomous default)

## Decision (one paragraph)

The org produced a complete, internally-consistent research-design package for an intraday session-boundary opening-range breakout strategy on FX majors (primary: EUR/USD + USD/JPY per-pair; stretch: GBP/USD, separate higher bar). After a Principal-Reviewer cycle-1 BLOCK (5 findings), the Quant Researcher's v2 rework closes all 5 blocking + 8 spec-drift findings by binding CRO's 0.25%/trade sizing cap, ET's stop-limit/no-mid fill model, a session-aware entry-delay + signal-voiding rule, a per-regime fat-tailed slippage distribution, and a frozen Deflated-Sharpe gate (N_total=36, p≤0.05) with regime/jackknife/negative-control falsification pre-registered. PR cycle-2 = APPROVE (3 independent reproductions); CRO + ET quality-gate-reviews = APPROVE. **RATIFIED by distributed quorum (ratified_with_dissent).** No backtest was run (design-only); org trial count stays 35; no live capital.

## Top-3 risks the CEO should know

1. **Edge prior is LOW + costs are brutal** (severity: high) — NHT: ORB is among the most over-fit FX families; ET: session-open round-trip cost 3.6–4.75 pips, GBP/USD likely net-negative → moved to a separate non-gating stretch arm (execution-trader + null-hypothesis-tester).
2. **Three blocking implementation prerequisites** (severity: high) — KG-1 no intraday data in pipeline (daily only), KG-2 no session-calendar module, KG-3 no intrabar engine; backtest cannot start until cleared (quant-researcher).
3. **Ratification is DESIGN-stage only** (severity: med) — quorum ratified the spec, NOT permission to backtest/paper/deploy; CRO's post-cost-expectancy kill-condition (reject if ≤0) and the DSR gate remain in force for the future backtest wave.

## Dissents (one-liner each; full text in CONSENSUS.md)

- **NHT (severity: material_concern; does_block: false):** Design-stage non-blocking, but prior of durable post-cost edge is LOW; must clear DSR vs org-wide N on frozen params with regime+jackknife+negative-controls; a passing result is paper-only, never live.
- **CRO (does_block: false):** Caps binding; veto fires on any sizing/leverage/cost-model breach or negative measured post-cost expectancy.

## Open items requiring CEO acknowledgment

- **Authorize the implementation wave?** Design is quorum-ratified; the next wave (build harness + backtest) is gated on clearing KG-1/2/3 first — this is a CEO go/no-go.
- Decide KG-1 first: confirm/acquire intraday 15m OHLCV for the three majors (current pipeline is daily-only) — nothing downstream can proceed without it.
- Decide engine-path (KG-3) ownership/approach with CTO (intrabar-capable engine) before any backtest.

## Skill gaps logged this session (N=5)

- quant-researcher: KG-1 intraday 15m OHLCV not in pipeline (blocking)
- quant-researcher: KG-2 no session-calendar module (blocking-impl)
- quant-researcher: KG-3 no intrabar-capable engine path (blocking-impl)
- execution-trader: KG-4 Saxo session-open spread/commission/GBP breakeven unverified
- execution-trader: fat-tailed slippage params need tick-level fill data

## Ratification status

> **RATIFIED by distributed quorum (ratified_with_dissent).** Signers: principal-reviewer, cro, execution-trader. Design-stage only.

CEO decision still open: **authorize the implementation/backtest wave?** (yes → clear KG-1/2/3 then build; no; revise <X>). Suggested revise targets: "revise universe" (drop GBP/USD entirely), "revise data-first" (acquire intraday data before anything else).

---
*This SUMMARY is for routine review. Read full CONSENSUS for substance. The design package is quorum-ratified; backtest/paper/deploy authorization is a separate CEO decision gated on KG-1/2/3.*
