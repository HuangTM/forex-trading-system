# CONSENSUS SUMMARY — QRB-6 Pre-Registration Package
**Track:** qrb6-prereg-2026-06-06 | **Trial:** fa0f982a | **Status:** AWAITING-CEO-FREEZE-ACK

---

## Decision (≤5 sentences)

The QRB-6 central-bank event study pre-registration package (trial fa0f982a, BC-1 — the firm's single authorized trial) is ratified as **freeze-ready**. All six acceptance criteria (AC-1 through AC-6) are satisfied after two NHT audit cycles, two PR review cycles, one real cross-role debate (QR-vs-Math on sign source, converged round 1), and a full rework pass. The Null-Hypothesis Tester SURVIVES (advisory severity, does not block) with two pre-flight reconciliation items that must be completed before the freeze-receipt cut. Honest power is 13–18% — **the expected outcome at run time is KILL**; this is a kill test by design. The freeze-receipt cut, the one-shot run, and the push are **CEO-reserved actions not authorized by this consensus**.

---

## Top-3 Risks

1. **Near-certain KILL (13–18% power) spends the firm's last authorized trial.** The design is adversarially conservative by intent — the expected outcome is KILL, not PASS. This is known and accepted; the pre-reg design errs toward over-deflation (harder PASS), which is the correct direction. QRB-3 (runner-up) advances only in a future wave with a future trial.

2. **BOC gap asymmetry confounds the post-2015 sub-window kill.** BOC data covers only 2019–2026 (2010–2018 entirely absent); this gap is structurally concentrated in the pre-2019 portion of the post-2015 sub-window, reducing the effective BOC contribution to that window's power and creating asymmetric bank coverage. Disclosed in §3.4b of the pre-registration.

3. **Aggregator-grade BoE dates carry residual 7-day-shift risk if Scenario B ever certifies.** Scenario B is DORMANT at freeze (spotcheck_certification=PARTIAL; NHT C4 requires "certified"). If C4 is ever cleared and Scenario B activates, the BoE aggregator dates carry a known date-alignment uncertainty not present in the verified-official Scenario A tier. Disclosed in the pre-registration provenance; Scenario B dormancy is the operative mitigation.

---

## Dissents

**NHT (advisory — does not block):**
> "UPDATED VERDICT: SURVIVES. [...] The assembled pre-registration is now a coherent, one-shot-testable specification with all internal contradictions resolved. [...] MANDATORY PRE-FREEZE PRE-FLIGHT ITEMS (not blockers, but required before receipt cut): 1. Runner script (scripts/run_qrb6.py) must be authored, committed, and its commit hash pinned in the freeze-receipt. 2. §3.5 doc prose should be reconciled to match the sidecar's artifact path (qd-spotcheck-sidecar.yaml) and should add 'with verdict == certified' to the activation condition. 3. Zero return data may be examined before the freeze-receipt is committed."

Full cycle-1 material_concern dissent preserved verbatim (append-only) in: `.agent-accountability/dissents/qrb6-prereg-2026-06-06:phase1:task1.0:null-hypothesis-tester.yaml`

---

## Open Items for CEO

| Item | Action Required |
|---|---|
| **Freeze-receipt cut** | Authorize `cut_freeze_receipt.py --target qrb6 --cut` after runner authored/committed and §3.5 prose reconciled |
| **Push authorization** | HEAD is 1 ahead of origin; explicit CEO authorization needed |
| **One-shot run** | `run_qrb6.py --ceo-ack` — separate later ack; not scheduled; requires freeze-receipt on disk |

---

## Ratification Prompt

CEO: if you approve the above, please authorize the freeze-receipt cut. This is the irrevocable action that registers trial fa0f982a and seals the pre-registration SHA. Confirm with: "authorize freeze-receipt cut for qrb6 / fa0f982a."
