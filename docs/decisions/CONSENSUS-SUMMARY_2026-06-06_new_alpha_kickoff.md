# CONSENSUS SUMMARY — New-Alpha Kickoff Wave
**Track:** new-alpha-kickoff-2026-06-06 | **Status:** AWAITING-CEO-DECISION | **Date:** 2026-06-06

---

## Decision

Eleven proposals screened, scored, and ranked under a frozen rubric (no backtests, no trial spend, trial counter unchanged at 40). Two proposals killed (QRA-3 momentum-regime re-skin: cost-kill + momentum-adjacent + QR self-assessed low confidence; QRB-5 weekday seasonality: worst reference class + 60-hypothesis FWER destroys power + sub-pip effect vs 1.5–3 pip round-trip). Nine conditional-survive; one — QRB-3 (Turn-of-month rebalancing flow, score 4.02) — is the sole clearer of the frozen first-candidate bar and the recommended first candidate. Two advance as overlays only (QRB-2 spread-gate, QRB-4-GATE rollover suppression). One is roadmap-only pending CEO acquisition authorization (QRB-6 CB-calendar, score 4.38, highest in portfolio). The CEO must now choose: authorize the QRB-3 full pre-registration track (one trial burns) or decline (no-spend, valid and documented).

---

## Top-3 Risks

1. **PR-F1 flip-sensitivity:** The entire recommendation rests on one 3-vs-4 judgment — QRB-3's mechanism_quality. The frozen rubric's level-3 anchor literally names "month-end rebalancers" as a level-3 example; the 4 is awarded via the anchor-4 "mandate/inelastic hedging need" clause. A reasonable scorer at 3 collapses the wave to NO-SPEND. This is concentrated model risk, owned on record by HoQR; not an error. The adopted post-2015 kill condition is the best procedural hedge.

2. **Published-anomaly decay (McLean-Pontiff) on the sole bar-clearer:** QRB-3 cites Melvin & Prins (2015) — the effect was documented 11 years ago and is partially pre-traded by FX desks. Estimated ~35% post-publication decay (potentially higher for calendar effects). The mandatory stability-across-halves test (2010-2017 vs 2018-2026) and the adopted post-2015 isolation test (2015-2026 in isolation) are the pre-registered kill conditions; if the effect flips or vanishes post-2015, the trial is killed regardless of pooled result.

3. **Mean-reversion concentration:** 6 of 9 surviving proposals are mean-reversion-flavored, against a firm history where the Bollinger-RSI (mean-reversion-adjacent) family went 0-for-3. If mean-reversion is structurally absent in this dataset, the wave's portfolio-level failure rate will exceed what per-proposal screening can detect. QRB-3 (the recommended candidate) is directional calendar-flow — drawn from the non-concentrated minority — but the CEO should be aware that the remaining shortlist is heavily mean-reversion-weighted.

---

## Dissents

NHT: concern, does_block=false. Portfolio-level dissent (3 portfolio preconditions, mean-reversion concentration, DSR-denominator pressure) adopted verbatim and honored in the ranking. No mandatory block.

---

## Open Items for CEO

- **Primary fork:** Authorize QRB-3 pre-registration track (max 1 trial this wave) or no-spend.
- **Supplementary:** Authorize QRB-6 CB calendar acquisition (trivially low effort; public free data; no trial cost; positions QRB-6 as first candidate in the next wave).
- Ratification (`.agent-accountability/ratifications/new-alpha-kickoff-2026-06-06:phase1:task1.0.yaml`) is DRAFT-PENDING-ORCHESTRATOR-VALIDATION; becomes final upon CEO decision and PR co-signature.

---

## Skill Gaps

N=0 — all required roles dispatched and artifacts produced.

---

## Ratification Prompt

> CEO: Do you authorize the QRB-3 pre-registration track (one trial) — or decline (no-spend)?  
> Optional: Do you authorize the QRB-6 CB calendar acquisition?  
> Full detail: `docs/decisions/CONSENSUS_2026-06-06_new_alpha_kickoff.md`
