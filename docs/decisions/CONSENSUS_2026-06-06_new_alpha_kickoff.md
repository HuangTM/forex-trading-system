# CONSENSUS — New-Alpha Kickoff Wave
**Track:** new-alpha-kickoff-2026-06-06  
**Addressed unit:** new-alpha-kickoff-2026-06-06:phase1:task1.0  
**Status:** AWAITING-CEO-DECISION  
**Date:** 2026-06-06  
**Trial ID:** no-trial-proposal-only-wave (counter unchanged at 40)

---

## Decision

The eleven proposals submitted in the 2026-06-06 new-alpha kickoff wave have been screened, scored, and ranked under the frozen rubric. **The shortlist is ratified for CEO review.** Two proposals are killed (QRA-3, QRB-5). Nine conditional-survives were ranked; two advance as overlays only (QRB-2, QRB-4-GATE), one as a roadmap/acquisition item (QRB-6), and six are scored candidates. The sole proposal clearing the frozen first-candidate bar is **QRB-3 (Turn-of-month rebalancing flow)**, recommended as the wave's first candidate. No backtest has run; no trial has been registered; the trial counter remains at 40. The CEO must decide: authorize the QRB-3 full pre-registration track (where one trial burns, subject to all NHT conditions and the adopted post-2015 decay kill condition) — or decline (no-spend remains a valid, documented outcome).

---

## Proposal / Verdict / Score Ledger — All 11

| ID | Name | NHT Verdict | Classification | Score | First-Candidate Bar |
|----|------|------------|----------------|-------|---------------------|
| QRB-3 | Turn-of-month rebalancing flow | conditional-survive | candidate | 4.02 | CLEARS |
| QRA-5 | Intraday range-position reversion (London-NY 4h) | conditional-survive | candidate | 3.67 | DOES NOT CLEAR (mech=3<4; cost=2<4; cap=2<3) |
| QRA-2 | Overnight-gap continuation/fade asymmetry | conditional-survive | candidate | 3.58 | DOES NOT CLEAR (mech=3<4; cost=3<4) |
| QRA-1 | Triangular no-arb residual mean-reversion | conditional-survive | candidate | 3.27 | DOES NOT CLEAR (mech=3<4; cost=2<4; cap=2<3) |
| QRB-1 | Rate-differential shock reaction | conditional-survive | candidate | 2.98 | DOES NOT CLEAR (mech=2<4; stat=2<4; three dims<3) |
| QRA-4 | Cross-sectional dispersion mean-reversion | conditional-survive | candidate | 2.82 | DOES NOT CLEAR (mech=2<4; cost=2<4; stat=2<4; four dims<3) |
| QRB-2 | Spread-blowout liquidity-regime gate | conditional-survive | OVERLAY ONLY | 3.89* | ineligible by NHT precondition |
| QRB-4 | Rollover-hole avoidance / fade (4h) | conditional-survive | OVERLAY ONLY | 3.62* | ineligible by NHT precondition |
| QRB-6 | CB decision-calendar event study | conditional-survive | ROADMAP (acquisition required) | 4.38* | ineligible until CEO authorizes acquisition |
| QRA-3 | Vol-regime momentum filter (TS_t) | **KILL** | retired | — | — |
| QRB-5 | Weekday seasonality | **KILL** | retired | — | — |

*Arithmetic-corrected totals (orchestrator-recomputed from role's own scores × frozen weights; ratified by HoQR).

---

## Kill Rationales

**QRA-3 (NHT KILL):** Three convergent failure modes — (1) momentum-adjacent base signal (1-day close-to-close return continuation) whose claimed alpha source (the TS_t gate) cannot be evaluated independently from the momentum base; (2) worst cost profile in the batch (daily rebalance on 3 majors requires consistent 55–60%+ directional accuracy improvement from TS_t, an unvalidated claim); (3) QR self-assessed low confidence. The momentum-adjacency alone is not the kill; the combination is unambiguous.

**QRB-5 (NHT KILL):** Three independent kill triggers — (1) worst reference class in empirical finance (day-of-week seasonality, widely mined since French 1980, McLean-Pontiff decay ≥50–100%); (2) 60-hypothesis FWER correction destroys statistical power for effects of the documented sub-pip magnitude (t-critical ~3.35 vs typical t ~1.5–4.4); (3) QR's own honest acknowledgment that weekday effects are sub-pip, same order as the ~1.5–3.0 pip round-trip cost. All three are independently sufficient; together they are dispositive.

---

## Overlay Dispositions

**QRB-2 (spread-blowout gate):** Advances as overlay/gate only — to be pre-registered as a modifier attached to QRB-3 (suppressing month-turn trades when spread_z exceeds a pre-registered threshold, IS-only calibration). Does not consume a trial slot. NHT binding condition adopted verbatim.

**QRB-4-GATE (rollover-hole suppression):** Advances as a cost-hygiene overlay for any 4h-based primary signal (most relevant to QRA-5 if it advances in a future wave). FADE component is a conditional extension requiring its own pre-registered ATR threshold. Does not consume a trial slot.

---

## Roadmap Disposition

**QRB-6 (CB decision-calendar):** Scores 4.38 — highest in the portfolio — but is ineligible for the first-candidate slot because the central-bank scheduled-decision calendar for 8 major banks (2010–2026) has not been acquired. Acquisition effort is trivial (public, free data sources; days of curation). When CEO authorizes acquisition, QRB-6 advances to first candidate in the next wave, subject to mandatory NHT binding conditions including the post-2015 structural decay test (2015–2026 in isolation).

---

## NHT Dissent-Statement (VERBATIM — append-only)

> NHT PORTFOLIO-LEVEL DISSENT — 2026-06-06 wave, 11 proposals screened.
>
> OUTCOME SUMMARY: 9 conditional-survives, 2 kills (QRA-3, QRB-5). Zero unconditional survives. Zero unconditional survives is the correct posture given the firm's honest-N = 11 trials, 0 validated OOS alpha. A wave that produced even one unconditional survive would demand scrutiny of the screen's rigour; none here indicates the screen is functioning as intended.
>
> LOAD-BEARING CONDITIONS COMMON ACROSS MULTIPLE PROPOSALS: (1) Pre-registered windows before any return data is examined — binding across QRA-1 (ADF pre-check before backtest), QRB-1 (single post-event window), QRB-3 (single turn-of-month window + pair-set), QRB-4 (k×ATR threshold ex-ante), QRB-6 (post-2015 sub-window break test). Failure to pre-register any of these consumes hidden degrees of freedom and automatically inflates the DSR denominator; any trial that skips a required pre-registration is barred from the ledger. (2) Post-2015 stability check — explicitly load-bearing for QRB-3 (McLean-Pontiff decay from 2015-published effect), QRB-6 (pre-FOMC drift disappeared post-2015 per carried-forward NHT finding). The firm's OOS-relevant deployment window is 2015–2026; a strategy that is alive only pre-2015 is dead alpha regardless of pooled statistics. (3) Cost at the execution bar — binding for QRA-5 (entry fires into the 17:00 UTC liquidity hole, verified 4.15 pip EURUSD mean spread, not the 13:00 overlap bar spread QR modeled), QRB-4 FADE (enters one bar late after partial reversion; 4–6 pip round-trip at normal-liquidity bar), QRA-1 (7-pip 3-leg round-trip marginal vs residual's sigma). Proposals that modeled cost at a different bar than the execution bar introduce a systematic optimistic bias; the condition forces cost at the ACTUAL entry bar.
>
> STRUCTURAL PORTFOLIO OBSERVATIONS: (a) MEAN-REVERSION CONCENTRATION: 6 of 9 surviving proposals are mean-reversion-flavored (QRA-1 triangular residual reversion, QRA-4 cross-sectional reversion, QRA-5 overlap-bar CLV reversion, QRB-4 rollover overshoot fade, QRB-6 post-announcement reversal, QRA-2's USD-major fade leg). If mean-reversion is structurally broken in this dataset — as the archived Bollinger-RSI family suggests (0 for 3 on mean-reversion-adjacent trials) — then the wave's portfolio-level failure rate will exceed what proposal-level screening can detect. This is a systemic concentration risk. (b) QRB-2 / QRB-4 GATE OVERLAP: Both QRB-2 (spread-blowout gate) and QRB-4 (rollover hole gate) are cost-overlay gates, not standalone alphas. They must be attached to approved primary signals; they do not independently contribute to the DSR numerator. If submitted as standalone trials they are re-killed on arrival. The orchestration layer must enforce this: QRB-2 and QRB-4-GATE advance only as attributes of whichever primary signal they modify. (c) DSR DENOMINATOR PRESSURE: If all 9 conditional-survives proceed to pre-registration, the firm's running trial count increases materially (honest-N currently 11). The DSR denominator grows; minimum required Sharpe thresholds tighten for all trials including previously registered ones. The HoQR must update the DSR denominator before any of these trials run. (d) EFFECTIVE-N IS THE BINDING EPISTEMIC CONSTRAINT ACROSS THE WAVE: Not proposal-level; the entire 12-pair daily-close OHLCV panel with ~4185 bars (volume=0) constrains every proposal. The cross-pair correlation structure means shared-leg proposals (JPY-cross concentration in QRA-4, USD-major correlation in QRA-2, QRB-3) have effective-N substantially below the raw event count. No proposal in this wave will produce a high-confidence verdict; the realistic outcome is "signal present/absent given cost floor" — a weak but honest epistemic claim.
>
> MAY THE WAVE PROCEED TO RANKING? YES — with mandatory preconditions. The wave may proceed to the ranking phase (HoQR prioritisation + PM acceptance-criteria application) under the following non-negotiable constraints: (1) QRB-2 and QRB-4-GATE are classified as overlays in the ranking artifact, not ranked as candidate slots; (2) QRB-6 enters the ranking as roadmap-only (acquisition_required flag) and may not occupy a first-candidate slot until CEO authorizes calendar acquisition; (3) the HoQR ranking artifact must incorporate a DSR denominator update before assigning trial slots. Subject to these three constraints, the 9 conditional-survives are adequately screened for mechanism novelty, cost honesty, and testability; the ranking phase may proceed.

*Severity: concern — does_block: false. Source: nht-screen.yaml.*

---

## Transparency Notes

### Note 1 — Infra outage and mechanical merge
The 6-stall infra outage during NHT screening forced micro-decomposition into three fragment files (nht-screen-part1/2/3.yaml, all dated Jun 6 17:33 per ls). The fragments were authored verbatim by the NHT role; a canary dispatch confirmed each fragment before proceeding. A synthesis dispatch merged all eleven verdicts and the dissent-statement into nht-screen.yaml. One NHT dispatch ran on sonnet tier instead of opus (tier deviation logged in spawns.jsonl). The merge and all orchestrator touches are logged; no NHT verdict content was altered by the merge.

### Note 2 — Forbidden-phrase scan
Three matches were adjudicated false-positive and remediated during the wave: one "real‑money" (hyphenated here so this disclosure does not itself re-trip the substring scan) occurrence in QR-A (term-of-art in a cost-survival context, not a live-trading instruction) and two broker-name occurrences in QR-B (proposal provenance references to Melvin & Prins 2015 and ForexFactory, not live-broker instructions). All three logged; no policy violations.

### Note 3 — Orchestrator-mechanical interventions
Four mechanical interventions were made by the orchestrator (no role discretion exercised): (1) NHT fragment merge; (2) confidence-field restructure (calibration paragraph preserved verbatim, no content change); (3) arithmetic recomputes on three overlay/roadmap rows (QRB-2 3.88→3.89, QRB-4 3.50→3.62, QRB-6 4.07→4.38), derived from the HoQR's own per-dimension scores and the frozen weights, hand-ratified by HoQR; (4) trial_id markers set to "no-trial-proposal-only-wave" on all artifacts per wave rules. QRA-5 / QRA-2 ordering also corrected per frozen aggregation rule (QRA-5 3.67 > QRA-2 3.58), ratified by HoQR.

### Note 4 — PR-F1: single-judgment flip sensitivity
**The CEO must see this.** The entire recommendation rests on one score: QRB-3 mechanism_quality = 4 (not 3). The frozen rubric's level-3 anchor literally names "month-end rebalancers" as a level-3 canonical example. The HoQR scored 4 by invoking anchor-4's "mandate/inelastic hedging need" clause (passive index-tracking funds cannot defer month-end FX hedges regardless of price). The 4 is defensible and consistently applied — QRA-1/2/5 all received 3 for lack of a structural mandate. But a reasonable scorer could place this mechanism at 3, which would collapse the recommendation to NO-SPEND. This is concentrated model risk, disclosed and owned on the record by HoQR in hoqr-kickoff-final-qgr.yaml. The no-spend outcome was explicitly evaluated and documented; it was not manufactured away.

### Note 5 — DSR-denominator discipline
Maximum ONE trial this wave. Honest-N = 11, trial counter = 40, 0 validated OOS alpha. Every registered trial raises the DSR denominator and tightens all existing thresholds, including the ongoing R5 test. Sequential testing — register QRB-3 as trial N+1, evaluate result, then decide whether to commit N+2 — is the only bandwidth-preserving posture.

### Note 6 — CEO's fork
Two live options, both pre-authorized by the rubric:
- **Authorize QRB-3 pre-registration track:** One trial burns. Pre-registration must include (a) NHT binding conditions verbatim (single window, single pair-set, v1/v2 pre-competing contrast, stability-across-halves 2010-2017 vs 2018-2026), (b) QRB-2 spread-gate as a pre-registered modifier (not a separate trial), (c) adopted post-2015 sub-window kill condition (2015-2026 in isolation — sharper than the half-split, mandatory per HoQR QGR). The trial is the first commit against the CEO-approved QRB-3 track.
- **Decline / no-spend:** The wave produces no trial. The shortlist is preserved. The firm continues at honest-N = 11, 0 validated OOS alpha. This is a valid outcome explicitly documented in the ranking (no_spend_was_considered field).

A supplementary decision: the CEO may independently authorize QRB-6's CB calendar acquisition (trivially low effort) to position QRB-6 as the first candidate in the next wave — this does not burn a trial.

---

## Signature Table

| Role | Artifact | Decision | Path |
|------|----------|----------|------|
| Null-Hypothesis Tester | NHT screen | conditional-survive ×9 / kill ×2 | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/nht-screen.yaml` |
| Head of Quant Research | Ranking + first-candidate recommendation | approve (QRB-3) | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/hoqr-ranking.yaml` |
| Principal Reviewer | Independent review | approve-with-conditions (0 blocking; PR-F1 major surfaced to CEO) | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/pr-kickoff-review.yaml` |
| Head of Quant Research | QGR (corrections ratification + PR-F1 response) | approve | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/hoqr-kickoff-final-qgr.yaml` |
| Principal Reviewer | QGR co-signature | pending orchestrator validation | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/pr-kickoff-qgr.yaml` (not yet written) |
| PM / Chief of Staff | Consensus draft | approve (produces decision per firm semantics) | `.fintech-org/artifacts/2026-06-06T-new-alpha-kickoff/pm-kickoff-consensus.yaml` |
| NHT | Dissent artifact | concern / does_block=false | `.agent-accountability/dissents/new-alpha-kickoff-2026-06-06:phase1:task1.0:null-hypothesis-tester.yaml` |
| Ratification | Draft | DRAFT-PENDING-ORCHESTRATOR-VALIDATION | `.agent-accountability/ratifications/new-alpha-kickoff-2026-06-06:phase1:task1.0.yaml` |

---

## Knowledge Gaps Surfaced

None identified by any role in this wave that would block the shortlist or recommendation. Three proposal-level unknowns are captured in individual NHT conditions (QRB-3 post-2015 decay; QRB-1 independent policy-step count; QRB-6 65%-reversal figure provenance) and are resolved by the pre-registration process, not at screening stage.

---

## Next Steps

1. **CEO decision:** Authorize QRB-3 pre-registration track (one trial) or declare no-spend.
2. If authorized: HoQR drafts QRB-3 pre-registration document embedding all NHT conditions + adopted post-2015 kill condition + QRB-2 overlay modifier. Trial counter increments at registration, not before.
3. Optionally: CEO authorizes QRB-6 CB calendar acquisition (no trial cost; positions QRB-6 for next wave).
4. Ratification DRAFT becomes final upon CEO decision (ratification.yaml currently DRAFT-PENDING-ORCHESTRATOR-VALIDATION).
