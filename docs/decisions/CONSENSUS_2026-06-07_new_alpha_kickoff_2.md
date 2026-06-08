# CONSENSUS — New-Alpha Kickoff-2
**Date:** 2026-06-07 | **Status:** RATIFIED | **Trial ID:** no-trial-proposal-only-wave
**Trial counter:** 42 (unchanged — no trial authorized this wave)

---

## Decision

The new-alpha kickoff-2 wave ran a full 14-proposal cycle (7 Slice-A, 7 Slice-B) against a CONFIRMABILITY-gated rubric (8 dimensions, 4 hard gates, frozen 2026-06-07T23:30:00Z before any proposal existed). After NHT-independent recompute of all years_to_validate values, **zero proposals clear the first-candidate bar (confirmability ≥ 4, i.e. years_to_validate ≤ ~2 yr).** The wave terminates at **NO-SPEND**: no trial is authorized, the trial counter stays at 42, and the ranked shortlist of 9 STRETCH survivors is queued for a future refinement wave. NO-SPEND is the deliberate, calibrated outcome of the rubric working as designed — not a failure. The firm correctly spent nothing.

---

## Transparency Notes

**T1 — NO-SPEND is the intended outcome, not a failure.**
The rubric's `no_spend_valid: true` clause (hoqr-rubric.yaml:324) exists precisely for this case. A full 14-proposal cycle was run, all arithmetic reproduced independently by the PR to 2 decimal places, and the honest answer is that no proposal can be validated out-of-sample fast enough to justify the next trial. Preserving the trial is more valuable than forcing a spend on a 3–5 year forward commitment.

**T2 — The confirmability gate did real work at THREE layers.**
- *Generation:* QRA2-4 was first drafted as a per-pair weekly signal (years = 5.50 yr GATE_FAIL); the QR lifted the run-rate to the cross-pair pooled version (2.75 yr) — the gate forcing the discipline intended. Slice-B was built per-pair-daily by construction to avoid the QRB-6-class weekly-rebalance trap.
- *Screening:* 3 of 5 NHT kills were confirmability (QRA2-4, QRB2-3, QRB2-7); 1 was a dedup that also failed confirmability (QRB2-6); 1 was a pure dedup (QRA2-6).
- *Ranking:* ALL 9 survivors land in the 3–5 yr STRETCH band under NHT-verified inputs. None clears ≤2 yr. The gate alone causes NO-SPEND.

**T3 — The 9 STRETCH survivors are REAL ideas held back only by forward horizon.**
Four are queued for a refinement wave with honest frequency-lift paths; two (QRA2-2, QRA2-7) are cost-binding as well as STRETCH and are not worth queuing; three are dead (gate kills).

*Refinement queue (honest lift paths):*
- **QRB2-2 (3.44 yr):** Lower channel-N (e.g. 20d not 55d) and/or relax vol-expansion threshold so real breaches fire ~40–60/yr/pair instead of 10–30 — at SR~0.30 that reaches ~2 yr. Best lift candidate.
- **QRB2-1 (3.05 yr):** No duty-cycle debit (carry-tier is a per-pair label). Gap to 2 yr is small. Tighten to extreme carry tiers only if per-event SR can be lifted; or accept as a ≤3 yr idea in a future wave with a relaxed bar.
- **QRB2-4 (3.32 yr):** No gate suppression; epy near-maximal. Honest lever is a sharper bloc-factor model raising per-event SR ~0.27 → ~0.33.
- **QRA2-5 (3.87 yr):** Best Slice-A survivor. Gap to 2 yr is large; an honest lift requires a higher qualifying-wick frequency AND sustained per-event SR — but loosening the filter dilutes the stop-cascade specificity. Queue low.

*Dead (not refinement targets):*
- **QRA2-4** (5.73 yr): events_per_year inflation was the mechanism; not refinable without a different mechanism.
- **QRA2-6** (HG-1 dedup of archived QRB-4): merge into the QRB-4 line if pursued; do not spawn a duplicate trial.
- **QRB2-3** (5.09 yr): duty-cycle debit is intrinsic to the correlation-gate thesis; cannot honestly raise epy without breaking the mechanism.
- **QRB2-6** (11.89 yr, DOUBLE-DEAD: HG-1 canonical-carry re-skin AND HG-4): permanently dead.
- **QRB2-7** (6.87 yr): dominated by sibling QRB2-2 (cleaner gate, better confirmability). If breakout+vol-gate is pursued, pursue QRB2-2 only.

*Survivors with converging failure modes (not queued):*
- **QRA2-2** (4.95 yr STRETCH + cost=2/HG-2-adjacent, high turnover): two failure modes converging.
- **QRA2-7** (4.83 yr STRETCH + cost=2, double-sided straddle): same convergence.

**T4 — PR-1 history correction applied.**
The meta-finding's initial narrative compressed the kickoff-1 history incorrectly. The corrected record (PR-1, closed): in kickoff-1 the first candidate was **QRB-3** (turn-of-month flow, 4.02 weighted total). QRB-6 scored highest (4.38) but was **data_readiness-INELIGIBLE** (acquisition required) and ranked roadmap-only. QRB-6 was pursued only later, after the CB-calendar was acquired, under separate CEO authorization — and only then did its run (exploratory fa0f982a: AMBIGUOUS; confirmatory 53981a4a: withdrawn pre-freeze) lead to the wind-down. The orchestrator's earlier verbal framing in this wave compressed the same history. The record is now accurate.

**T5 — Counter integrity.**
Counter stays 42. No trial was authorized, no trial ID was burned. The `no-trial-proposal-only-wave` trial ID is a paper-wave designator, not a counter increment.

---

## The 5 Kills

| # | ID | Gate | NHT years | Kill reason |
|---|-----|------|-----------|-------------|
| 1 | QRA2-4 | HG-4 (confirmability) | 5.73 yr | events_per_year inflation: 52 Mondays × 12 correlated pairs declared as 624 independent signals at the full pre-filter rate, while the QR's own cost profile concedes the quiet-Friday filter "roughly halves it." At the QR's own SR=0.18 with honest effective epy ~300 → 5.73 yr. Robust from either lever. Worst base-rate (calendar axis on which QRB-5 was killed). |
| 2 | QRA2-6 | HG-1 (dedup) | 3.48 yr (moot) | Re-skin of archived QRB-4 (NY-afternoon rollover liquidity-hole fade): same 16:00–20:00 UTC thin-liquidity window (verified spread mean ~4.15 at hour 17), same fade-the-overshoot mechanism, same sign, same 3 pairs — differing only in whether the hole is defined by spread-state (QRB-4) or a same-stamp vol-z (QRA2-6). "Same flow/behavior, new indicator name" = HG-1 definition. Merge into QRB-4 line; do not spawn a duplicate. |
| 3 | QRB2-3 | HG-4 (confirmability) | 5.09 yr | The correlation gate is flat in high-correlation states by its own thesis. Declaring the un-gated daily rate (180/yr) for a gate whose duty cycle the proposer admits suppresses many days is inconsistent. Honest duty-cycle debit (180 → 150) + SR 0.33 → 0.27 → 5.09 yr. Compounded by weakest base-rate prior (stacked trend + correlation + bloc-proxy DOF). |
| 4 | QRB2-6 | HG-1 + HG-4 (DOUBLE) | 11.89 yr | DOUBLE KILL, self-flagged. HG-1: a dollar-neutral long-top-carry/short-bottom-carry basket IS canonical cross-sectional carry (Lustig-Verdelhan HML-FX) — "rank not level" does not rescue it. HG-4: weekly rebalance → events_per_year = 52 → 8.26 yr (rubric's own anchor), 11.89 yr on NHT SR haircut. The deliberate QRB-6-in-new-guise trap exemplar. |
| 5 | QRB2-7 | HG-4 (confirmability) | 6.87 yr | Under-debited duty cycle: declared epy=120 while own cost profile says post-squeeze breaks fire only ~6–15/yr/pair. Honest debit (→ 90) + SR 0.36 → 0.30 → 6.87 yr. Also dominated by sibling QRB2-2 (cleaner gate, better confirmability). |

---

## Meta-Finding: The Confirmability Gate is Load-Bearing (Corrected, PR-Verified)

The rubric's 4th hard gate (confirmability > 5 yr → TOTAL = 0, anchored to years_to_validate from the frozen formula) is not decorative.

**Counterfactual (the load-bearing, PR-verified claim):** WITHOUT the confirmability gate, the best kickoff-2 idea on the other seven dimensions is **QRB2-2** (4.09 weighted total; strong named mechanism, novel, sharply falsifiable, cost anchor 5, stat anchor 4, data_readiness 5 — data-ready on pure OHLC, unlike QRB-6). On the OLD confirmability-free kickoff-1 first-candidate bar, QRB2-2 clears every clause and, as the top scorer, would have been selected and pursued — and its honest forward horizon is **3.44 yr** (NHT), beyond the ≤2 yr standard. That is the QRB-6 shape: in-sample attractive, forward-unconfirmable. Three further proposals (QRB2-3 5.09 yr, QRB2-7 6.87 yr, QRA2-4 5.73 yr) are outright >5 yr QRB-6-class traps killed at generation; QRB2-6 is both a carry re-skin and an 8–12 yr trap. WITH the gate the wave terminates at NO-SPEND — trial preserved, no void-and-wind-down cycle. The gate converted a confident-looking shortlist into an honest non-spend; its cost is one wave without a new trial, the cost it avoided is another QRB-6.

*Note on kickoff-1 history (corrected per PR-1):* The gate's value does not depend on QRB-6 having been the kickoff-1 pick. The kickoff-1 first candidate was QRB-3; QRB-6 was data-ineligible and roadmap-only at that ranking. The QRB2-2 counterfactual (data-ready now, would have cleared the old bar) carries the argument independently and completely.

---

## Full Proposal / Verdict / Score Ledger

### Slice A — Intraday / Microstructure / Volatility-State (QRA2-1 through QRA2-7)

| ID | Name | NHT years | Verdict | Total | mech | nov | fals | cost | stat | conf | data | cap |
|----|------|-----------|---------|-------|------|-----|------|------|------|------|------|-----|
| QRA2-1 | 4h overnight-range-compression breakout-fade | 3.26 | STRETCH | 3.72 | 4 | 4 | 5 | 3 | 4 | 2 | 4 | 3 |
| QRA2-2 | Intrabar CLV-momentum continuation (4h) | 4.95 | STRETCH (cost-binding) | 3.36 | 3 | 4 | 5 | 2 | 4 | 2 | 5 | 3 |
| QRA2-3 | Daily vol-regime-conditioned range reversion | 3.55 | STRETCH | 3.58 | 4 | 3 | 5 | 3 | 4 | 2 | 4 | 4 |
| **QRA2-4** | **Monday-open-gap-reversion after quiet Friday** | **5.73** | **HG-4 KILL** | **0** | — | — | — | — | — | — | — | — |
| QRA2-5 | Wick-rejection asymmetric stop-cascade (daily) | 3.87 | STRETCH | 3.75 | 4 | 4 | 5 | 3 | 4 | 2 | 4 | 4 |
| **QRA2-6** | **4h session-handoff air-pocket reversion** | *3.48 (moot)* | **HG-1 KILL (dedup QRB-4)** | **0** | — | — | — | — | — | — | — | — |
| QRA2-7 | Daily range-expansion vol-clustering straddle | 4.83 | STRETCH (cost-binding) | 3.04 | 3 | 3 | 4 | 2 | 4 | 2 | 4 | 4 |

### Slice B — Novel Carry-Conditioning / Trend-Breakout / Regime-Gated / Cross-Sectional (QRB2-1 through QRB2-7)

| ID | Name | NHT years | Verdict | Total | mech | nov | fals | cost | stat | conf | data | cap |
|----|------|-----------|---------|-------|------|-----|------|------|------|------|------|-----|
| QRB2-1 | Carry-rank momentum CONFIRMATION gate (per-pair trend) | 3.05 | STRETCH | 3.90 | 4 | 4 | 5 | 4 | 4 | 2 | 4 | 4 |
| QRB2-2 | Donchian breakout + realized-vol-EXPANSION gate (per-pair) | 3.44 | STRETCH | 4.09 | 4 | 4 | 5 | 5 | 4 | 2 | 5 | 4 |
| **QRB2-3** | **Correlation-regime gate on per-pair trend** | **5.09** | **HG-4 KILL** | **0** | — | — | — | — | — | — | — | — |
| QRB2-4 | Per-pair idiosyncratic bloc-residual continuation | 3.32 | STRETCH | 3.79 | 4 | 4 | 5 | 3 | 4 | 2 | 5 | 4 |
| QRB2-5 | Efficiency-ratio / vol-persistence adaptive trend gate | 3.87 | STRETCH | 3.77 | 4 | 3 | 5 | 4 | 4 | 2 | 5 | 4 |
| **QRB2-6** | **Cross-sectional carry-rank dispersion basket** | **11.89** | **HG-1+HG-4 DOUBLE KILL** | **0** | — | — | — | — | — | — | — | — |
| **QRB2-7** | **Range-compression breakout-anticipation (post-squeeze)** | **6.87** | **HG-4 KILL** | **0** | — | — | — | — | — | — | — | — |

*Weights: mechanism 0.25 / novelty 0.17 / falsifiability 0.14 / cost 0.15 / stat 0.10 / confirmability 0.12 / data 0.04 / capacity 0.03. All 9 weighted totals reproduced exactly to 2dp by the PR (pr-review.yaml:148–158).*

---

## Ranked Shortlist (NO-SPEND — none first-candidate-eligible)

| Rank | ID | Name | Total | NHT years | Gate verdict | Disposition |
|------|----|------|-------|-----------|--------------|-------------|
| 1 | QRB2-2 | Donchian + vol-expansion gate | 4.09 | 3.44 yr | STRETCH | QUEUE (lead refinement candidate; honest frequency-lift path exists) |
| 2 | QRB2-1 | Carry-rank momentum gate | 3.90 | 3.05 yr | STRETCH | QUEUE (runner-up; most novel carry-conditioning; closest to bar) |
| 3 | QRB2-4 | Bloc-residual continuation | 3.79 | 3.32 yr | STRETCH | QUEUE (single-leg, clean trapdoor) |
| 4 | QRB2-5 | Efficiency-ratio trend gate | 3.77 | 3.87 yr | STRETCH | QUEUE (low priority; firm-novel only) |
| 5 | QRA2-5 | Wick-rejection stop-cascade | 3.75 | 3.87 yr | STRETCH | QUEUE (best Slice-A survivor; large gap to ≤2 yr) |
| 6 | QRA2-1 | 4h compression-fade | 3.72 | 3.26 yr | STRETCH | QUEUE (4h only; thin cross-section) |
| 7 | QRA2-3 | Vol-regime range reversion | 3.58 | 3.55 yr | STRETCH | QUEUE (cleanest Slice-A mechanism) |
| 8 | QRA2-2 | 4h CLV-momentum continuation | 3.36 | 4.95 yr | STRETCH (cost=2) | DEAD as candidate (cost-binding + knife-edge STRETCH) |
| 9 | QRA2-7 | Vol-clustering straddle | 3.04 | 4.83 yr | STRETCH (cost=2) | DEAD as candidate (cost-binding + double-sided) |

**QRB2-2 bar-check summary:** clears mechanism≥4, novelty≥4, cost≥4, stat≥4, falsifiability≥3, data∈{4,5}, no dimension below 3, NHT-survive — and fails ONLY on confirmability (anchor 2, 3.44 yr vs ≤2 yr floor). This is the confirmability gate doing exactly its job.

**max_trials_this_wave: 0**

---

## Knowledge Gaps Surfaced

1. **Correlated-pair effective-N methodology:** NHT applied a structural 0.45–0.55 haircut to events_per_year for pooled cross-pair signals based on ~6–7 effective currencies among the 12 daily pairs. This methodology is judgment-based (MEDIUM confidence per NHT-A); a formal cross-pair correlation study would sharpen it and reduce the uncertainty on STRETCH/GATE_FAIL boundary cases (QRB2-3 at 5.09 yr sits on the boundary).

2. **Gate duty-cycle estimation for regime-switching strategies:** For strategies with an ON/OFF regime gate, the honest active-event stream is the gate's duty cycle × daily rate, not the un-gated daily rate. Quantifying typical duty cycles in advance (before proposals are written) would reduce NHT recompute variance in future waves.

3. **Per-event SR prior calibration:** All per_event_SR_estimate_IS values are a-priori unmeasured guesses deflated by the frozen 1/3 haircut. The 1/3 is a selection-bias standard; actual OOS shrinkage for never-tested sub-pip microstructure fades on OHLC-only zero-volume data may be larger. A calibration study against existing Slice-A results (QRA-1..5) would anchor future SR priors more tightly.

4. **QRB-3 status:** QRB-3 (turn-of-month flow) remains queued and independent from this wave. Its advance condition (a QRB-6 post-2015 sub-window KILL) never fired; it requires its own fresh pre-registration. This wave does not resolve its status.

---

## Next Steps for CEO

1. **Option A — Refinement wave:** Authorize a focused refinement wave on the STRETCH queue (QRB2-2 first, QRB2-1 second). Each refinement target has a specific, honest frequency-lift path stated above. A refined QRB2-2 at ~40–60 breaches/yr/pair would re-enter the rubric at ~2 yr and become first-candidate-eligible.

2. **Option B — Pursue QRB-3:** QRB-3 (turn-of-month intrabar flow, kickoff-1 queued runner-up, 4.02 on the old rubric) has never been re-screened under the CONFIRMABILITY gate. Its events_per_year as a monthly flow would need NHT recompute before it could be confirmed eligible. Requires fresh pre-registration.

3. **Option C — Different research direction:** Redirect research bandwidth toward a genuinely different alpha family that is structurally more confirmable (e.g. higher-frequency per-pair signals with documented, non-OHLC triggers). The Slice-A concentration finding (effective diversification ~2–3 of 7 proposals, all "OHLC extreme reverts net of ~1.5 pip") is an input to this consideration.

4. **Option D — Wait:** Hold at NO-SPEND and apply bandwidth to the ongoing R5 research track. No capital, no counter increment, no action required.

---

## Signature Table

| Role | Artifact | Decision | Notes |
|------|---------|----------|-------|
| Head of Quant Research (ranking) | `.fintech-org/artifacts/2026-06-07T-new-alpha-kickoff-2/hoqr-ranking.yaml` | approve (NO-SPEND) | Ranked shortlist; max_trials=0; PR-1 correction applied |
| NHT (Slice A) | `.fintech-org/artifacts/2026-06-07T-new-alpha-kickoff-2/nht-screen-a.yaml` | 2 kills + 5 conditional-survive | HG-4: QRA2-4; HG-1: QRA2-6; systemic confirmability optimism finding |
| NHT (Slice B) | `.fintech-org/artifacts/2026-06-07T-new-alpha-kickoff-2/nht-screen-b.yaml` | 3 kills + 4 conditional-survive | HG-4: QRB2-3, QRB2-7; HG-1+HG-4: QRB2-6; gate duty-cycle systemic finding |
| Principal Reviewer | `.fintech-org/artifacts/2026-06-07T-new-alpha-kickoff-2/pr-review.yaml` | APPROVE-WITH-CONDITIONS | All arithmetic verified 14/14; PR-1 (major, documentation-accuracy) **CLOSED**; NO-SPEND verified honest |

*Quorum basis: research-direction / prioritization → HoQR; design-review → PR; kill-layer → NHT screens. No CRO trigger (no capital, no sizing). No CTO trigger (no architecture). Proposal-only wave.*
