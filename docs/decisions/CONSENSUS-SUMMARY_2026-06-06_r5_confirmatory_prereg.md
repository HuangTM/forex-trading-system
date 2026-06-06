# CONSENSUS SUMMARY: R5 Confirmatory Pre-Registration
**Track:** r5-confirmatory-2026-06-06 | **Status:** AWAITING-RATIFICATION (CEO required before freeze-receipt cut)

---

## Decision

The confirmatory pre-registration for vol_target_carry:USDJPY (trial f2fb41fd, NEW — never reusing 576746aa) is ratified-for-freeze by role quorum. It is an honest, binding, confirmatory-only kill test on unsnooped post-2026-04-06 data absorbing the R5 36-cell selection burden in N_conf=6. Two looks are scheduled (interim 2028-10-06, terminal 2031-04-06); the terminal look is forced KILL — outcome 4 (CONTINUE) does not exist at the final look. Two-look power ≈ 0.34 at SR_plan=0.554361; the expected terminal outcome is wind-down. No capital is authorized at any branch.

---

## Top-3 Risks

1. **Power 0.34 / expected kill.** Design is severely underpowered at the selection-deflated SR_plan=0.554361. A terminal non-rejection is KILL-with-caveat, not a license for continued spend. The design is explicitly structured for wind-down to be the most-likely outcome; a PASS is a cheap option, not an expected event.

2. **5-year runner-gap + governance-must-hold.** The look-time runner does not exist (deliberate). Governance integrity must hold from 2026 to 2028 (runner-receipt quorum) and 2031 (terminal look CEO ack). The freeze-receipt interlock is the primary containment; if that governance chain breaks, NHT F-1 becomes exploitable. The freeze-receipt MUST pin `sr0_pp_conf=0.034921` explicitly NOW so the 2028 QD cannot reach for r5_decision's R5-only literal `0.022906`.

3. **N_conf=6 judgment + SR_1 provenance lineage carried from R5.** N_conf=6 is a disclosed judgment (4 + 3 − 1 overlap), not a derivation. SR0_ann=0.554361 depends on the 2-observation dispersion 0.426385 frozen from R5 — any error in that estimate propagates to SR0 and kill_switch in both directions. The kill_switch_threshold=1.2906 is stricter than R5 on both axes (higher N_conf, smaller T_holdout) and is correctly NOT copied.

---

## Dissents

**NHT:** severity=concern, does_block=false. One material non-blocking finding (F-1): look-time runner does not yet exist; existing DSR code is a trap (hardcoded R5 SR0_PP=0.022906). Contained by receipt interlock and behavior-equivalence pin at freeze. NHT SIGNS SURVIVES.

---

## Open Items for CEO

- **Ratification required**: CEO must ratify this consensus before the freeze-receipt is cut (pre-authorized sequence: commit → `--target confirmatory --cut` → receipt commit → push).
- **Freeze-receipt pin obligation**: The receipt must explicitly pin `sr0_pp_conf=0.034921` as the runner-injected literal (per NHT F-1 recommendation) — not a blocking condition on consensus, but a required pin at the time of cut.
- **Look execution governance**: STEP/look execution in 2028/2031 requires fresh CEO acknowledgment + runner-receipt quorum at that time. Not pre-authorized by this session.

---

## Skill Gaps

N=0.

---

## Ratification Prompt

> CEO: The R5 confirmatory pre-registration for vol_target_carry:USDJPY (trial f2fb41fd) is assembled and role-quorum approved. Two looks: 2028-10-06 (interim) and 2031-04-06 (terminal, binding KILL). Expected outcome is wind-down (~66% chance of KILL given 34% power). No capital authorized. NHT survives at severity=concern, does_block=false. Ratification artifact at `.agent-accountability/ratifications/r5-confirmatory-2026-06-06:phase1:task1.0.yaml`. The next irreversible step is cutting the freeze-receipt. Do you ratify and authorize the freeze sequence?
