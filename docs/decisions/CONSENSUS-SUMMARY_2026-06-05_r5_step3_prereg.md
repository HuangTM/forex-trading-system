# CONSENSUS SUMMARY: R5 STEP 3 — Carry-Universe Kill Test Pre-Registration
**Track:** r5-step3-prereg-2026-06-05 | **Date:** 2026-06-06 | **Status:** AWAITING-CEO-RATIFICATION

---

## Decision

The R5 carry-universe kill test pre-registration is RATIFIED-FOR-FREEZE by distributed quorum (HoQR + Mathematician, with PR cycle-2 APPROVE and NHT delta-audit SURVIVES severity=note). The frozen spec covers the joint Hansen-SPA + White-RC kill test of all 36 carry-universe cells (6 variants × 6 JPY crosses), window 2010-03-15 to 2026-04-06 (T=4186), K=5000 seed 576746, elected N=3 SR0=0.363623. Every outcome maps to a named firm action; underpowered non-rejection (most likely outcome, power ~20-35%) maps irreversibly to WIND-DOWN, not "inconclusive, keep spending." STEP-4 execution authorization is deferred to the CEO — wind-down is irreversible firm policy outside the autonomous quorum's authority.

---

## Top-3 Risks

1. **Test is underpowered (~20-35%) and wind-down is binding on non-rejection.** The firm has pre-committed WIND-DOWN regardless of power. The most likely outcome is a non-rejection that the test cannot distinguish from a true null vs. insufficient power. This was known at scope ratification and accepted: the kill decision is based on the absence of detectable signal, not absence of signal. CEO should confirm the firm is prepared to execute the wind-down action map on the most likely outcome.

2. **DSR gate inputs rest on registry-unverified SR_1=0.80 and a judgment-call N=3.** SR_1=0.80 has no trials.jsonl row; the Bet#1=carry_fred label is contradicted by the registry (Bet#1 is momentum, retired). The monotonicity defense is valid on the Var/spread axis (over-stated SR_1 can only produce false WIND-DOWN, never false CONTINUE) but the N=3 election retains a residual anti-conservative bias on the multiplicity axis (true N=4 would make DSR harder by 0.085 ann). Both are disclosed and analyzed; neither has a capital path; direction is documented. The gate is harder at N=3 (best-cell SR ~0.767 required) than at the prior N=2 (~0.625).

3. **AMBIGUOUS/confirmatory branch is the residual forking-paths surface.** The CONTINUE and AMBIGUOUS outcomes (outcomes 1 and 4) route to a fresh confirmatory pre-reg. The A-4 counter-discipline is now binding (new trial_id + R5 36-cell selection absorption into honest-N; omitting either VOIDS). This closes the back-door at the spec level but the counter discipline has not been exercised in a real confirmatory run. A future confirmatory tester must be required to read and comply with §4/§5/§6 of the frozen pre-reg.

---

## Dissents (One-liners)

- **NHT original (nht-audit.yaml):** SURVIVES; severity concern (agent-calibrated), orchestrator-escalated to material_concern by keyword scan ("garden of forking paths"); four reservations recorded verbatim; does_block=false. SUPERSEDED by delta-audit.
- **NHT delta (nht-delta-audit.yaml):** SURVIVES; severity note; all A-1..A-6 reservations resolved; four D-findings none blocking; does_block=false.

---

## Open Items Requiring CEO Acknowledgment

1. **STEP-4 authorization.** The one-shot bootstrap run requires CEO sign-off. Freeze sequence follows: code+doc commit → `cut_freeze_receipt.py --cut` → receipt commit → run. Authorize or defer.
2. **Trial-counter ruling.** PM's acceptance criteria said no increment; charter protocol mandated one. Orchestrator followed charter (trial 576746aa, line 37). STEP 4 reuses the same trial_id. CEO should acknowledge the conflict record.
3. **Forbidden-phrase scan-match adjudication.** A broker name in a data-provenance citation was adjudicated as a false positive (no capital-routing semantics; reworded to neutral citation). No policy-violations.jsonl entry written. CEO sees this here.

---

## Skill Gaps Logged This Session (N=0)

No skill gaps were surfaced or escalated to the skill-gap loop this session.

---

## Ratification Prompt

The quorum has ratified the frozen spec. To authorize STEP-4 execution, the CEO responds with an unambiguous instruction such as: "Approved — proceed with freeze sequence and STEP-4 run." An ambiguous response will be re-prompted rather than promoted to authorization.

> Distributed-ratification artifact (DRAFT, pending orchestrator hash fill):
> `.agent-accountability/ratifications/r5-step3-prereg-2026-06-05:phase1:task1.0.yaml`
>
> Full consensus:
> `docs/decisions/CONSENSUS_2026-06-05_r5_step3_prereg.md`
>
> Dissent artifacts:
> `.agent-accountability/dissents/r5-step3-prereg-2026-06-05:phase1:task1.0:null-hypothesis-tester.yaml`
> `.agent-accountability/dissents/r5-step3-prereg-2026-06-05:phase1:task1.0:null-hypothesis-tester-delta.yaml`
