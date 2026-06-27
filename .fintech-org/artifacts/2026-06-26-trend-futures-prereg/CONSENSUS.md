# Consensus on: Trend-on-Futures Pre-Registration — Terminal Closure

**Status:** ratified_with_dissent (distributed quorum: head-of-quant-research + principal-reviewer, 2026-06-26; F7 DO-NOT-RUN; honest-N=30 never spent; surfaced to Board, non-blocking)
**Session artifacts:** `.fintech-org/artifacts/2026-06-26-trend-futures-prereg/`
**Date:** 2026-06-26
**honest-N:** 30 (UNCHANGED — no trial spent; trial counter does not increment at design freeze)

---

## Roles staffed

| Role | Contribution |
|------|-------------|
| Quant Developer (QD) | $0 cost-hurdle probe: confirmed cost is NOT the binding constraint; residual net Sharpe ~0.40 vs 0.20 gate, non-knife-edge across full plausible parameter grid. |
| Quant Researcher (QR, v2) | Authored the FROZEN multi-pair cross-asset pre-registration; self-corrected v1's false breadth-compresses-horizon claim; pinned F7 to published-decayed s=0.20 (non-circular); froze three DOFs (F3 regime-dating, F4 episode boundaries, F5 estimator). |
| Null-Hypothesis Tester (NHT) | Rigorous audit; issued needs-revision dissent on the v1 prose (breadth claim arithmetically false by 1-2 orders of magnitude); v2 applied the surgical fix; dissent preserved verbatim below. |
| Principal Reviewer (PR) | approve-with-conditions; independently re-computed years-to-validate; 0 findings blocking the frozen design; 3 findings blocking-for-committed-backtest (F-001 threshold reconciliation, F-002 holdout-seam purge, F-006 freeze roll/back-adjust). |
| PM | Sequenced phases; enforced execution firewall; preserved NHT dissent verbatim; confirmed trial counter unchanged; made no technical or strategy calls. |

---

## Decision

**FREEZE the pre-registration as a model artifact; its F7 power gate FIRES DO-NOT-RUN; the committed backtest is NOT AUTHORIZED; honest-N stays 30; the firm returns to observe-only — now with the deepest finding of the research arc, established at $0.**

The chain that produced this decision:

1. The firm exhausted existing-data alpha (4 families, net SR < 0 across all 84 pair×family combos on retail OHLCV).
2. A 21-direction generation cycle ranked Trend-on-Futures #1 (the only candidate that structurally attacks all four binding walls).
3. The $0 cost-hurdle probe PASSED: CME round-trip cost drag ~0.002 Sharpe at TSMOM turnover; residual net Sharpe ~0.40 >> 0.20 gate; non-knife-edge across the full plausible grid.
4. A FROZEN multi-pair cross-asset pre-registration was authored and independently verified by NHT and PR.
5. The pre-registration's OWN F7 confirmability power gate, computed honestly at $0 on published-decayed inputs, returns years-to-validate ~37-92 years. F7 fires DO-NOT-RUN.

No code was written. No data was purchased. No honest-N unit was spent.

---

## § The Profound Conclusion

**THE FIRM'S BINDING CONSTRAINT IS NOT DATA CLASS. IT IS THE STATISTICAL CONFIRMABILITY OF ANY MODEST-SHARPE EDGE AT THIS SCALE.**

This is the central finding of the arc, and it is arithmetic:

A systematic edge with a net annual Sharpe of ~0.2-0.5 (the honest post-decay range for documented trend premia) requires decades of data to distinguish from zero under honest deflation. The formula is transparent: years-to-validate at 80% power = (z_power + z_alpha)² / S_prog², where S_prog = s × sqrt(B) and z_alpha is set by the compound deflation against 37 effective trials. At s=0.20 (published ~0.40 FX-sleeve gross × 50% McLean-Pontiff decay) and B=4-10 effective bets (the cross-asset program's most-generous plausible range), this gives:

- **37 years** at B=10 (most generous, fully-diversified construction)
- **61 years** at B=6
- **92 years** at B=4

To validate in ≤3 years at the deflated alpha would require a net annual program Sharpe of **~2.2** — roughly **4-5× the highest gross, undecayed diversified-trend Sharpe ever published** in the academic literature (~1.0, Hurst-Ooi-Pedersen 2017 over 100 years of multi-asset data). This is not a practical shortcoming to be corrected by better data or cleverer engineering. It is an arithmetic limit.

**Trend-on-futures ESCAPED cost (W1) and the no-volume wall (W4) — and STILL hit this wall.** The data class changed; the events/yr × per-event-Sharpe arithmetic that killed QRB-6 did not. Cross-asset breadth helps: it lifts B from ~2-4 (FX-only, USD-loaded) toward ~4-10 (cross-asset), shortening the horizon from centuries toward decades. Decades is not 3 years.

**There is no retail-accessible, modest-Sharpe systematic edge the firm can confirm at power within a reasonable horizon.** This is not a failure of the research program. It is the research program delivering its most important result: proving the un-confirmability of a class of edges before spending a single honest-N trial. The F7 gate, designed for exactly this purpose (QRB-6 lesson: power 9% at the 2030 look), worked as designed. The firm proved this for **$0**, at the design stage, with zero irreversible spend.

**The validated harness and the falsification corpus are the firm's real assets.** The harness (CPCV + Deflated Sharpe + confirmability rubric + honest-N + execution firewall) has now correctly rejected or frozen four families of candidates. It is a functioning anti-p-hacking instrument. The corpus of ratified, frozen pre-registrations — each a documented falsifiable design — is a durable institutional record of what was tested, under what assumptions, and why it was declined.

---

## § The Pre-Registration as a Model Artifact

The quant-researcher-prereg.yaml (v2, FROZEN) is a model example of the QRB-6 discipline mechanized. Its four key properties, affirmed by NHT and PR independently:

**1. Frozen falsification machinery.** Seven falsification criteria (F1-F7) carry fixed numeric thresholds, named inputs, and single-shot evaluation rules committed before any data is seen. F1-F5 are evaluated exactly once on the committed backtest; F6 and F7 are $0 pre-gates that block the backtest before it can run. No threshold may be moved after data is seen.

**2. Single-program accounting.** The 24-contract cross-asset universe is explicitly ONE strategy = ONE honest-N unit = ONE program-level risk limit. Cross-asset trend correlations converge toward 1 in liquidation regimes (2009 post-GFC reversal, March-2020 COVID spike); breadth that helps confirmability in normal regimes does NOT diversify the tail. The committed backtest would spend exactly ONE honest-N unit (30→31), never one-per-sleeve. Cross-lens convergence (trend surfaced via three generation lenses) is discounted to one mechanism — NHT's dissent #1 from the exploration cycle, honored without softening.

**3. Compound 37-trial deflation.** The DSR denominator deflates against honest-N=30 AND the 21-direction generation surface (~7 distinct mechanisms, not naive-21 which over-corrects, not +1 which under-corrects and repeats the 2026-05-31 reset failure). Frozen effective trial count = 37; NHT owns final ratification; revisable only upward. NHT confirmed the deflation is second-order here (the BLdP expected-max-Sharpe hurdle rises only ~0.13 sigma_SR from 7 mechanisms to the full 21) — honest, not a defect; cost is not the binding gate.

**4. F7: a gate that refuses to run itself.** The confirmability power gate (F7) is pinned to published-decayed inputs (s=0.20) that are computable at $0 TODAY, before any data spend. It is explicitly non-circular: it does not depend on the backtest it gates. On its own honest inputs it fires DO-NOT-RUN. The value of this pre-registration is precisely the rigorous, frozen, $0 rejection — the firm recognizing an un-confirmable edge and declining to spend on it, rather than a path to a committed trial.

**The v1→v2 self-correction.** The quant-researcher issued a v1 pre-registration that contained a material prose error: it asserted that cross-asset breadth compresses years-to-validate below the firm's ≤2-3yr bar. NHT demonstrated this claim to be arithmetically false by 1-2 orders of magnitude under the pre-registration's own F7 formula. The quant-researcher acknowledged the error and issued v2 with a surgical correction: the prose now honestly states the expected F7 disposition (DO-NOT-RUN), pins s=0.20 as the non-circular published-decayed input, removes every assertion of ≤2-3yr as achievable, and freezes the three secondary DOFs NHT identified (F3 regime-dating source, F4 episode calendar boundaries, F5 estimator formula). This v1→v2 self-correction is itself a model of how the firm's peer-review process is supposed to work.

---

## § The F7 Power Arithmetic

The confirmability precheck is not a hypothetical future computation. It is fully specified, non-circular, and already resolved.

**Inputs (frozen, published-literature, non-circular):**
- Per-bet annual Sharpe: s = 0.20 (published FX-sleeve gross ~0.40 after 50% McLean-Pontiff post-publication decay haircut — a published-literature value, not a backtest-realized number)
- Effective bets: B ∈ [4, 10] (the most-generous plausible cross-asset band; AMP-2013 / Hurst-2017 published correlation tables)
- Deflated one-sided alpha = 0.05/37 → z_alpha ≈ 3.00 (compound 37-trial denominator)
- Power: 80%, z_power = 0.842

**Formula:** years-to-validate = (z_power + z_alpha)² / (s × sqrt(B))²

**Computed results:**
- B=10 (most generous): ~37 years
- B=6: ~61 years
- B=4: ~92 years
- Most generous direct construction (Hurst diversified gross ~1.0 × 0.50 decay = 0.50 taken as direct net program Sharpe): ~59 years

**Required program Sharpe to clear the ≤3.0yr bar:** S_prog ≥ 1.44 (~4-5× the best honest decayed number ~0.35-0.50)

**Required program Sharpe to clear the canonical ≤2.0yr G1 bar:** S_prog ≥ 1.76

**F7 verdict: DO-NOT-RUN.** This is not a close call. Every plausible input leaves years-to-validate 10-30× above the bar.

**Lineage to the QRB-6/R5 arc.** This is the same confirmability arithmetic that killed QRB-6 (power 9% at the 2030 look; 80% power would require 28-256 years; firm correctly did not run). It is consistent with the R5 precedent (true ~0.30 annual Sharpe → only 20-35% power over the whole carry-universe history; a ~0.77 series "will take years"). The data class changed from retail spot OHLCV to real-volume CME futures. The events/yr × per-event-Sharpe arithmetic that determined the result did not.

---

## § Dissent (NHT) — Verbatim, Append-Only

> DISSENT (append-only, verbatim for CONSENSUS.md). The rigor MACHINERY of this pre-registration is excellent and I affirm it: all seven falsification criteria carry fixed numeric thresholds and named inputs, are single-shot, and the HOLDOUT is touched exactly once; the single-program accounting (one honest-N unit, one risk limit, cross-lens convergence discounted to one mechanism) is correct and does not smuggle breadth as independent confirmation; the compound deflation to 37 effective trials honors the ratified F-008 ruling. I dissent on ONE load-bearing point that blocks freezing the prose as the firm's standing spec. The artifact's CENTRAL THESIS — that cross-asset breadth compresses years-to-validate below the firm's <=2-3yr confirmability bar — is ARITHMETICALLY FALSE under the pre-registration's OWN F7 formula. Evaluating that formula on the artifact's own honest inputs (published FX-sleeve gross 0.40 x a pinned 0.50 McLean-Pontiff decay = 0.20 per-bet; effective bets B=4..10; deflated one-sided alpha at 37 trials -> z~3.0), years-to-validate at 80% power is 37 to 92 YEARS, not 2-3. The single most generous construction I could honestly build (Hurst diversified gross ~1.0 x 0.5 decay = 0.50 taken as the DIRECT net program Sharpe) still gives ~59 years. To validate in <=3yr at the deflated alpha the program would need a net ANNUAL Sharpe of ~2.2 — about 4-5x the highest gross-undecayed diversified trend Sharpe ever published. Breadth multiplies S_prog by sqrt(B) (~2-3x); the bar demands ~7-11x. This is the QRB-6 power-infeasible trap wearing new clothes: the data class changed but the events/yr x per-event-Sharpe arithmetic that killed QRB-6 is intact. Because F7's inputs (decayed per-bet Sharpe from published literature; effective B from published correlation tables) are BOTH computable for $0 TODAY, F7 is not a hypothetical gate — on every plausible input it is a DO-NOT-RUN verdict that can and should be evaluated BEFORE any data spend. Two consequences I require before this freezes as the standing spec: (1) the prose (hypothesis, universe 'WHY THIS GIVES BREADTH', confirmability-precheck PASS BAND, body) must be corrected to state HONESTLY that the most likely F7 outcome is a do-not-run, and must STOP asserting <=2-3yr as achievable — the honest posture is 'this is probably the firm's next honest do-not-run, and F7 is the mechanism that proves it cheaply,' not 'breadth gets us inside the bar'; (2) F7's 'decayed per-bet Sharpe s' input must be pinned to the PUBLISHED-AND-DECAYED number (0.20), NOT a backtest-realized quantity — otherwise F7 is circular (it needs the backtest it is meant to gate) and silently ceases to be a pre-backtest gate. Secondary, non-blocking: pin the regime-bucket dating source (F3), the exact 2011-2015 / March-2020 episode calendar boundaries (F4), and the eff-independent-bet estimator formula (F5/G5), each of which is a small post-hoc lever if left unfrozen. I also record that the deflation denominator is second-order here (the BLdP expected-max-Sharpe hurdle rises only ~0.13 sigma_SR going from 7 mechanisms/N=37 to the full 21/N=51), so the '37 is honest, 21 over-corrects' framing overstates the cost of conservatism; I exercise my upward-revision authority only to record that N=51 is equally defensible and nearly free, not to mandate it. NET DISPOSITION: do NOT freeze the prose as the firm's standing spec as-is. The criteria and accounting are sound; the confirmability NARRATIVE is not. Revise the prose to the honest do-not-run posture and resolve the F7 input scope, THEN freeze. The corrected artifact would be a model pre-registration: it would correctly spend ZERO honest-N by firing F7 at $0 before any data purchase — which is exactly the QRB-6 discipline the firm earned.

**NHT disposition on v2:** The NHT dissent above was issued against v1. The quant-researcher authored v2 applying the two required changes: (1) prose corrected throughout to the honest do-not-run posture, removing all assertions of ≤2-3yr as achievable; (2) F7's s=0.20 pinned explicitly to the published-decayed value (non-circular). The three secondary DOFs (F3 regime-dating, F4 episode boundaries, F5 estimator) are addressed in v2. The NHT machinery critique — falsification criteria, single-program accounting, compound deflation — survives intact and is affirmed. The v1 confirmability narrative defect has been corrected. The dissent is preserved verbatim as required; the revision was surgical, not a redesign.

---

## § Principal Reviewer Findings

**PR verdict: approve-with-conditions.** 0 findings block the frozen design. 3 findings are blocking-for-the-committed-backtest and must be addressed before any Board-authorized honest-N spend.

| Finding ID | Severity | What It Is | Status |
|-----------|---------|-----------|--------|
| **F-001** | **Major / blocking-for-committed-backtest** | F7 threshold (>3.0yr) is LOOSER than the firm's canonical G1 bar (≤2.0yr; 2-3yr is only "STRETCH"). F7 as written would admit a STRETCH direction the canonical gate denies. Reconcile the two thresholds before the committed step. Also: the honest expectation must be stated — F7 on its own inputs is a near-certain DO-NOT-RUN. | Addressed in v2 prose (honest posture stated); threshold reconciliation is a forward condition for any future committed-backtest authorization. |
| **F-002** | **Minor / blocking-for-committed-backtest** | CPCV TRAIN+TEST↔HOLDOUT seam at 2021-12-31 / 2022-01-01 is not stated to carry a 13-month purge; a late-2021 label's 12-month lookback window can read 2022 holdout prices. Leakage lives precisely at this boundary. | Forward condition: specify symmetric purge+embargo at the holdout seam before the committed step. |
| **F-003** | Minor / observation | eff-trials=37 does not explicitly book the within-direction parameter surface (lookback=12mo, vol-target=15%, risk-parity weighting — all pre-committed single-shot, which mitigates). Second-order; upward-only NHT revision lever covers it. | Non-blocking for design. Noted for NHT ratification at committed step. |
| **F-004** | Minor / observation | F6 hard-blocks only on the 2009 episode + ≥20yr; the 2011-15 "long winter" and Mar-2020 are mandated in prose but have no independent coverage gate. | Addressed in v2 (to-the-day episode boundaries frozen in F4). Recommend adding per-episode date-range assertions to F6 at committed step. |
| **F-005** | Minor / blocking-for-committed-backtest | F3 regime concentration criterion does not bind to the pre-declared 6-cell {hiking/easing/on-hold}×{risk-on/risk-off} grid and does not name the edge-attribution metric (Sharpe vs return vs risk-adjusted PnL). | Addressed in v2 (F3 now references the pre-declared grid and frozen dating source). |
| **F-006** | Minor / blocking-for-committed-backtest | Roll/back-adjust convention (Panama/ratio/none; roll trigger = OI-cross vs N-days-pre-expiry) deferred to acquisition rather than frozen now. For a TREND backtest the back-adjust choice is first-order (additive Panama distorts long energy histories). | Forward condition: freeze back-adjust method and roll trigger before acquisition, not at acquisition. |
| **F-007** | Observation / strength | The artifact honestly identifies that the same cross-asset correlation that delivers confirmability breadth in normal regimes collapses to ~1 in liquidation — breadth helps the denominator (years-to-validate) in exactly the regimes where it does NOT help the tail. The honest-N=1 single-program accounting is the correct response. | No action — affirmed as a design strength. Board should read F5 (breadth) and F4 (crash survival) as a coupled pair. |

**PR blocking count for frozen design: 0.** The design is methodologically sound and honest. All forward conditions are pre-registered; they gate the committed backtest, not the design freeze.

---

## § What This Means for the Firm

**Observe-only posture stands.** The firm's posture is: no live capital, no paper capital, no committed backtest, honest-N=30. This is not a temporary hold pending better data. It is the correct standing posture given the arithmetic established here.

**The harness and falsification corpus are the assets.** The firm's validated research harness (CPCV, Deflated Sharpe ≥0.95, confirmability rubric, honest-N accounting, execution firewall) has now correctly evaluated five research directions across four data families and produced a rigorous, auditable record of each. That record is durable value — it is what prevents the next cycle from re-discovering the same walls.

**Reactivation conditions.** The trend-on-futures pre-registration is a re-activatable spec IF AND ONLY IF the power gate ever becomes feasible. The F7 gate would clear under one or more of the following (none of which is plausible on current evidence):
- A substantially higher net program Sharpe than published/decayed numbers support (would need ~2.2 annual; no documented trend program at this scale approaches it)
- A much larger effective-bet count than cross-asset diversification can honestly deliver (B would need to be ~100+)
- A substantially looser deflation bar (would require the firm to abandon its ratified 37-trial compound denominator, which was itself a correction of a prior under-deflation failure)

The honest conclusion is that no plausible improvement on current evidence clears the gate. **The next investment of research bandwidth should target a FUNDAMENTALLY different regime**: a high-Sharpe edge (e.g., genuine execution alpha at institutional latency), a much-longer-history edge (e.g., century-scale data reducing the deflated alpha), or a non-modest-edge regime structurally out of reach of retail-systematic approaches. Not another modest-Sharpe systematic idea on any data class.

---

## § Signatures

| Role | Verdict | Condition |
|------|---------|-----------|
| Quant Developer | implement (cost probe PASS, non-knife-edge, honest-N unchanged) | Cost is not the binding constraint; confirmability is |
| Quant Researcher (v2) | implement (FROZEN pre-registration, honest do-not-run posture, F7 fires, v1 error self-corrected) | Honest-N stays 30; committed backtest NOT authorized |
| Null-Hypothesis Tester | needs-revision (v1); DISSENT preserved verbatim; revision applied in v2; machinery affirmed | Dissent is append-only; v2 surgical fix addresses both required changes |
| Principal Reviewer | approve-with-conditions (0 blocking-for-frozen-design; 3 blocking-for-committed-backtest: F-001 threshold reconcile, F-002 holdout-seam purge, F-006 freeze roll/back-adjust) | Design frozen; forward conditions gate the committed step |
| PM | implement (consensus synthesized; NHT dissent verbatim-preserved; trial counter confirmed unchanged; no technical calls made) | — |

---

## § Knowledge Gaps

**Installable skill gaps: N = 0.**

All gaps that exist are either Board inputs (capital base, Saxo CME access) or pre-computable research tasks (realized effective-bet count from published correlation tables) that do not require new skill installation. No skill gap impaired the review.

Non-installable gaps carried forward (for any future reactivation):

| Gap | Owner | Status |
|-----|-------|--------|
| Realized effective independent-bet count B for the 24-contract program — computable from AMP-2013/Hurst-2017 published correlation tables before any spend | Quant Developer | On hold; moot while F7 fires on s=0.20 alone |
| Whether Saxo Bank provides CME futures access or only CFDs-on-futures | Board / CEO | Board input; no action pending while posture is observe-only |
| Deployable capital base figure (whether one 6E contract is risk-acceptable) | Board / CEO | Board input; research-only designation stands |
| F7 z_alpha mapping (Bonferroni 0.05/37 → z~3.00 vs DSR-internal; every mapping leaves years >> 3.0) | NHT | Second-order; pin at committed step if ever reached |

---

## § Open Items Requiring Board Acknowledgment

**No items require Board spend authorization.** The standing observe-only posture is the correct and honest disposition.

Two items are informational for Board awareness:

1. **The frozen pre-registration is a re-activatable spec.** `quant-researcher-prereg.yaml` (v2, FROZEN) is on file as a machine-checkable design. If the firm ever operates in a regime where the power gate is feasible (see reactivation conditions above), the spec is the authorized starting point. It does NOT require re-authoring.

2. **The firm has now decisively answered its own strategic question.** The 2026-06-07 DATA-CAPABILITY finding (dataset wall, not idea wall) is correct but incomplete. This arc adds the deeper finding: the confirmability wall is ARITHMETIC, not data-class. Moving to a real-volume futures venue was the correct structural move; it cleared cost (W1) and volume (W4). The confirmability wall (modest-Sharpe × finite-breadth-and-horizon under honest deflation) remained. This finding is not reversible by acquiring better data. It is reversed only by a fundamentally different class of edge.

---

*Consensus is append-only. Dissents are preserved verbatim. No technical calls were made by the PM.*
