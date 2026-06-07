# CONSENSUS SUMMARY: QRB-6 Wind-Down

**Status:** RATIFIED (wind-down)
**Track:** qrb6-winddown-2026-06-07:phase1:task1.0
**Full consensus:** `docs/decisions/CONSENSUS_2026-06-07_qrb6_winddown.md`
**Ratification:** `.agent-accountability/ratifications/qrb6-winddown-2026-06-07:phase1:task1.0.yaml`

---

## Decision

QRB-6 (CB-decision event study, {FED, BOJ, RBA, BOC}) is wound down and archived as a documented
near-miss. The exploratory (fa0f982a) found a real in-sample edge that fails only the conservative
deflation bar; the confirmatory (53981a4a) was correctly designed to clear that bar at N_sel=1 but
reaches only 9% power at the 2030 terminal look — independently verified to zero delta by both
ratifiers — making forward confirmation infeasible on any tradeable horizon. Trial 53981a4a is
retired as "withdrawn, pre-freeze (never tested)" and does not count toward the deflation
denominator; fa0f982a remains in the denominator unchanged. QRB-3 is unchanged (its advance
condition never fired). The confirmability lesson — (events/yr × per-event Sharpe) must reach
≥80% power within ≤3 years — is adopted into the HoQR screening rubric for the next new-alpha wave.

---

## Top-3 Takeaways

1. **Real-but-unconfirmable edge.** QRB-6 has genuine in-sample signal (p_post2015=0.0027) but a
   per-event Sharpe of ~0.085 on a sparse series (~30 events/yr) means 80% confirmatory power needs
   28–256 years. This is not a falsification — it is a structural ceiling on a low-frequency, modest
   edge. The firm is not burying a validated strategy; it is being precise about what "real" means
   versus what "confirmable" means.

2. **Diagnostic-inertness barrier (NHT refinement — adopted).** The precise objection to the
   low-power freeze option is not "unfalsifiability" (the QR-authored draft does carry a KILL branch)
   but **diagnostic inertness**: at ≤9% power, both a non-rejection and a rejection are
   near-uninformative about the underlying edge, making the test unable to teach the firm anything
   either way. This framing is sounder and is now the org's canonical basis for declining low-power
   freeze options when no adequate-power horizon exists.

3. **Confirmability lesson for future waves.** Rare-event studies of modest edges are structurally
   unconfirmable on a tradeable horizon regardless of in-sample significance, because in-sample power
   was bought by a many-year accumulation that cannot be reconstituted forward. The pre-screen —
   estimate (events/yr × haircut effect) → compute n*(power) and years → drop if years > 3 at 50%
   power — would have caught QRB-6 at generation and is now mandated in the HoQR new-alpha rubric.

---

## Dissents

**None.** NHT concurs with the wind-down (survives verdict). NHT's methodological refinements
(diagnostic inertness framing; 53981a4a must be logged "withdrawn, never tested" not "falsified")
are adopted into the consensus, not registered as dissents. No dissent artifact.

---

## Open Items for CEO

- **Push authorization:** HEAD is 1 commit ahead of origin (62421b6); push of the committed QD
  runner and confirmatory design artifacts is CEO-reserved.
- **Confirmability rubric adoption timing:** Adopt the pre-screen rubric into the HoQR new-alpha
  checklist now or defer to the next wave kickoff — CEO's call.

---

## Ratification Note

Quorum: HoQR (strategy-kill domain) + NHT (structural-skepticism/honesty domain). No CRO trigger
(no sizing or capital decision). No CTO trigger (no architecture change). Both ratifiers
independently reproduced all power numbers to zero delta. No dissent artifact. Status: RATIFIED.
