# CONSENSUS SUMMARY — New-Alpha Kickoff-2
**Date:** 2026-06-07 | **Status:** RATIFIED | **Trial counter:** 42 (unchanged)

---

## Status
RATIFIED — NO-SPEND.

## Decision
The new-alpha kickoff-2 wave completed a full 14-proposal cycle (7 Slice-A, 7 Slice-B) against a CONFIRMABILITY-gated rubric (8 dimensions, 4 hard gates). After NHT-independent recompute of all years_to_validate values under attestation A4, zero proposals clear the first-candidate bar (confirmability ≥ 4, i.e. ≤ ~2 yr). Five proposals are killed outright by hard gates: QRA2-4 (HG-4, 5.73 yr), QRA2-6 (HG-1 dedup of archived QRB-4), QRB2-3 (HG-4, 5.09 yr), QRB2-6 (HG-1 canonical-carry re-skin + HG-4, 11.89 yr), QRB2-7 (HG-4, 6.87 yr). All 9 remaining survivors land in the 3–5 yr STRETCH band. NO-SPEND is the calibrated, defensible terminal outcome — the rubric working as designed. max_trials_this_wave = 0. No trial is authorized.

## Top-3 Takeaways

**1. The confirmability gate is load-bearing — it prevented a QRB-6 repeat.**
WITHOUT the gate, the best kickoff-2 idea (QRB2-2, 4.09 weighted total) clears every other first-candidate clause — mechanism 4, novelty 4, cost 5, stat 4, falsifiability 5, data 5 — and would have been selected. Its honest forward horizon is 3.44 yr (NHT): in-sample attractive, forward-unconfirmable. Three further proposals are outright >5 yr traps killed at generation. The gate cost one trial-free wave; it avoided another void-and-wind-down cycle.

**2. Zero ideas clear the ≤2 yr first-candidate bar under honest correlated-pair effective-N.**
The QR's self-scores claimed 5 of 14 proposals at ≤2 yr (confirmability anchor 4). NHT independently recomputed all 14, debiting (a) correlated-pair effective-N for Slice-A pooled proposals and (b) gate duty-cycle for Slice-B regime-gating strategies, plus a modest a-priori SR haircut. Result: every survivor lands at confirmability anchor 2 (3–5 yr STRETCH). The systemic over-claim — counting un-gated daily frequencies for day-suppressing regime gates — is the structural pattern HG-4 was written to catch.

**3. The refinement queue is the path forward.**
Four STRETCH survivors have specific, honest frequency-lift paths: QRB2-2 (lead; lower channel-N raises real breach count toward 2 yr), QRB2-1 (closest to bar at 3.05 yr, no duty-cycle debit), QRB2-4 (sharper bloc-factor model), QRA2-5 (best Slice-A survivor, larger gap). A targeted refinement wave on QRB2-2/QRB2-1 is the highest-bandwidth-to-confirmability path.

## Dissents
None. NHT screens and HoQR ranking are concordant. PR approved-with-conditions; PR-1 (major, documentation-accuracy) is CLOSED (meta-finding narrative corrected: kickoff-1 first candidate was QRB-3, not QRB-6; QRB-6 was roadmap-ineligible at ranking and pursued only later via separate CEO auth).

## Open Items for CEO
1. **Authorize a refinement wave** on the STRETCH queue (QRB2-2 first, QRB2-1 second) — each has a stated honest frequency-lift path.
2. **Or pursue QRB-3** (kickoff-1 queued runner-up) — needs fresh pre-registration and NHT recompute under the confirmability gate.
3. **Or redirect** to a genuinely different alpha family with structurally higher confirmability.
4. **Push authorization** — HEAD=`62421b6`, 1 commit ahead of origin; no code changes in this wave (proposal-only); push is a git housekeeping action only.

---

*Ratified by quorum: HoQR (ranking/approve) + PR (design-review/approve-with-conditions[closed]) + NHT-A + NHT-B (kill-layer). No CRO/CTO trigger. No capital action. Counter stays 42.*
