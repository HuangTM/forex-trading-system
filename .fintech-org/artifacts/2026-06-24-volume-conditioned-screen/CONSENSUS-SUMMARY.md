# CONSENSUS SUMMARY: Volume-Conditioned Screen — 2026-06-24

**Status: ratified_with_dissent** (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Full audit:** `.fintech-org/artifacts/2026-06-24-volume-conditioned-screen/CONSENSUS.md`
**Date:** 2026-06-24 | **Honest-N:** 30 (unchanged)

---

## Decision

NO-SPEND. Volume-conditioned family RETIRE / FAMILY-CLOSED. Honest-N stays 30; no trial-counter increment. OPEN-ITEM-C2COST CLOSED. All four IC roles (HoQR, CRO, NHT, PR) converged independently: broker tick-volume on the existing 9-pair 1h parquet is mechanically collinear with realized range (Spearman 0.69–0.74) and carries no directional information orthogonal to volatility. The conjunctive gate (cost-pass AND vol-control t≥2.00) is EMPTY across all 8 pair-candidate cells — USDJPY's nominally large gross (+3.30 pips) lives entirely in the high-relvol × high-range cell (+6.03 pips), with the volume-without-volatility cell at −0.45 pips. Both V1 (relvol-continuation) and V2 (relvol∧low-spread mean-reversion) are killed on pre-registered, machine-checkable triggers. No re-parameterization on this data class can rescue the family.

---

## Top-3 risks

1. **Strategic drift:** Treating this screen's null result as independent justification for a data-capability spend would repeat the 2026-05-31 "more-data = progress" failure mode. Any data-acquisition spend requires its own pre-registered, falsifiable, data-REQUIRING hypothesis — the volume null does not supply one.

2. **Conjunctive-gate misread:** The two V1 cost-PASS labels (EURUSD +0.14, USDJPY +1.18) must not be read as partial success. Both fail the vol-control gate (t=0.45 and t=−0.33); they are selection artifacts of 8 cells screened across tight-spread majors. The PASS labels are correct and transparent; the risk is over-reading them.

3. **Idea-generation treadmill:** HoQR rates further existing-data generation as EV-negative. Continuing to screen new families on the same 9-pair 1h store is expected to reproduce the same four structural walls (cost-dominance, USD concentration, regime-dependence, absent true volume/flow). The correct response is a posture change, not a new candidate.

---

## Dissents

**NHT (structural skeptic — verbatim, append-only, non-blocking):** Concurs with the kill. Dissents against any "progress" framing and against inferring a data-capability spend from this null. The screen showed that THIS broker tick-volume proxy on THIS data is collinear with range — it is NOT evidence that true traded-volume or L2 depth would carry alpha. "The firm ran a cheap screen and correctly spent nothing — that is the win, and the only win."

**CRO (veto, size 0.0):** The apparent payoff is volatility-harvesting in a volume costume — the carry-trade/short-vol failure shape. Advancing a counted trial would be a governance blowup-analog, not just a P&L one.

---

## Open items

1. **(PRIMARY) THE STRATEGIC FORK — requires CEO decision:** Option 1: data-capability acquisition (hard precondition: a written, falsifiable, data-REQUIRING hypothesis BEFORE any spend). Option 2: wind down to observe-only / maintenance (the honest default if the precondition cannot be met). Options 3 and 4 (carry on longer history; more existing-data generation) are low-priority / EV-negative per HoQR.

2. **PR Forward condition F-002:** Any future committed CPCV backtest using a volume-relative signal must replace the full-sample seasonal norm with a rolling/expanding past-only norm. No action required until a future volume-class candidate is commissioned.

3. **PR Forward condition F-004:** If the volume lever is revisited on intraday data, the V2 session-open anchor must be a genuine trading-session open (not UTC calendar-date midnight bar). No action required until a future intraday volume-class hypothesis is commissioned.

4. **OPEN-ITEM-C1FILTER (carried forward):** C1 surprise filter non-binding; requires verified ECB/BOE release timestamps. Held pending strategic fork decision.

---

## Skill gaps

**Installable-skill-gap count N = 0.** All gaps are data-acquisition or commercial-scoping gaps (true volume/order-flow data class; vendor due diligence). No skill installation required.

---

## Ratification prompt

The Board (CEO) is requested to ratify or veto this consensus. Please respond with one of:

- **RATIFIED** — accept the NO-SPEND / FAMILY-CLOSED / honest-N=30 verdict; acknowledge the strategic fork (Option 1 or Option 2); forward conditions F-002 / F-004 noted.
- **RATIFIED WITH RESERVATIONS** — accept the verdict; state reservations verbatim for the record.
- **VETOED** — state the specific ground; the PM will route for re-deliberation.

This consensus will be written to the ratification record in `.fintech-org/artifacts/2026-06-24-volume-conditioned-screen/` upon receipt of an unambiguous response. An ambiguous response (e.g., a follow-up question, "interesting") will be treated as a re-prompt, not an approval.
