# CONSENSUS SUMMARY: Paper Launch Acceleration — Fastest Legitimate Path to First Real Paper Bar

**Status:** awaiting-ratification (deferred to CEO)
**Track:** paper-launch-acceleration-2026-06-01 | Phase 1 / Task 1.0
**Timestamp:** 2026-06-02T00:00:00Z

---

## Decision

The CEO's "speed it up" directive rests on a false premise: the firm has zero validated OOS
alpha and a tripped kill-criterion (infrastructure not insight). The only legitimate near-term
paper action is an **observe-only momentum-EURUSD canary** — zero capital, routes no orders,
no edge metric, trial count frozen at 35. It is a plumbing smoke-test, not progress toward
validated alpha. Two preconditions are BLOCKING even to start (P1 secrets-purge, P4
mock-sentinel-fix); two are advisory at zero capital (P2 Saxo marking, P3 calibration — the
latter is the canary's output, not its gate). Fastest time-to-first-bar: 3-5h if operator
provisions the Saxo SIM token immediately; 18-32h if token requires next business day.

---

## Top-3 Risks

1. **Knight-class kill-switch gap (HIGH).** Kill-switch properties 3 (known SLA) and 4 (tested
   in prod-equivalent conditions) are unmet. Not a blocker at zero capital, but a HARD required
   precondition before any sizing>0. Must be drilled and recorded before canary graduates.

2. **Bet#1 auto-retire 2026-07-01 (TIME-CRITICAL).** Trial 87fa1d23 (momentum-EURUSD, the
   only OOS trial in 35) has its equity parquet missing. Without regeneration and re-adjudication
   under corrected DSR/effective-N, the firm has zero verified OOS candidates after 2026-07-01.

3. **Operator-bottlenecked critical path.** The 24h Saxo SIM token is the single wall-clock
   blocker for first real bar. It requires operator action on the Saxo developer portal and
   cannot be automated. 24h TTL means timing issuance to the run window is required.

---

## Dissents

**NHT (null-hypothesis-tester) — severity: material_concern — does_block: false**

The consensus ADOPTS NHT's position. The canary is a plumbing smoke-test. It does NOT count
as evidence of edge, an OOS test, a falsification-log entry, progress on N, or progress toward
validated alpha. The kill-criterion remains tripped on both conjuncts. Any communication
presenting the canary otherwise is a policy violation.

---

## Open Items Requiring CEO Acknowledgment

- **OA-1 DSR re-adjudication incomplete (FACTUAL CORRECTION).** "All trials sub-gate" is
  incorrect. Two carry trials (d572999d, f66dd64c) show bar-count DSR 0.938 / 0.847 — both
  above 0.50 but optimistic upper bounds (excess-kurtosis 385-688 violates DSR's Gaussian-tail
  assumption). The T_eff re-run under effective independent samples has NOT been done. The
  momentum OOS candidate (87fa1d23) is new_dsr=null (missing equity, uncomputable). Correct
  framing: no trial is unconditionally above gate.

- **OA-2 Saxo SIM token (TIME-SENSITIVE operator action).** Provisions first real bar;
  24h TTL; must be issued within 2h of run window. CEO/operator must act to unblock.

- **OA-3 Kill-switch drill required before sizing>0.** Properties 3+4 unmet. Must be drilled
  and recorded to .fintech-org/kill-switch-tests.jsonl before any sizing>0 is ever proposed.

- **OA-4 Bet#1 regeneration deadline 2026-07-01.** Equity parquet for 87fa1d23 genuinely
  missing. Deterministic re-run from git_hash 54df16a. Highest-priority research item.
  Auto-retires if not done by 2026-07-01.

---

## Skill Gaps Logged This Session

N=0 — no new skill-creation requests were emitted. Knowledge gaps were identified and are
routed to the skill-gap loop (see full CONSENSUS doc §Knowledge Gaps Surfaced).

---

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise \<X\>)**
