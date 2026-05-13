# Consensus on: Implement REM-1..7 remediation from 2026-05-12 multi-strategy arch review (Option B, Strangler-Fig).

**Status:** awaiting-CEO-ratification (NHT material_concern: does_block=true blocks auto-ratify; PR cycle-2 approve)
**Full audit:** see `./CONSENSUS_2026-05-13_rem_arch_review_execute.md`
**Session:** `rem-arch-review-execute-2026-05-13`

## Decision (one paragraph)

The org implemented REM-1 (Liskov fix), REM-2 phase-A (PaperRunnerBase scaffold + COND-1), REM-4 (dispatch stagger config), REM-5 (per-strategy allocation fairness rule), REM-6 (Saxo 429 hardening), and REM-7 (AggregateDrawdownContract dual-instance defense) against the 2026-05-12 ratified remediation backlog. Wave-2b produced 798 passing tests; wave-3 PR cycle-1 raised 10 findings (2 blocking); rework-1 closed all 10 and PR cycle-2 verified mechanical closure (focused-verification template per select-roles.md v0.4.10 — closure-only, NOT full re-review of cycle-1 rubrics). Sacred test test_no_lookahead passes throughout (necessary but scenario-specific; not invariant-comprehensive — see CONSENSUS.md § Assumptions we are betting on). The 27-file + 7-test-file changeset is staged for CEO commit; no push has been performed.

## Top-3 risks the CEO should know

1. NHT relocation-pattern vigilance (severity: high; source: nht-null-test-report wave-2a) — REM-1/2/7 relocation patterns (reflection-bypass re-emergence, _v2 fork, trajectory-fragile aggregate ladder) are now test-detected, but each test's coverage boundary is finite; the next strategy added exercises those boundaries.
2. 3 unclosed BC-9-N4-CONDs routed to deferred-decisions queue (severity: high; source: cro-risk-assessment wave-2a) — COND-4 (ML model-risk SR 11-7), COND-5 (live kill-switch test at N=2 before N=3), COND-6 (strategy_type field for ML) are all blocking for their respective transitions and require CEO acknowledgment.
3. REM-2 phase-A inertness + duplication-attractor dynamic (severity: high; source: pr-review-report wave-3 + NHT-ARCH-3 attractor language) — AggregateDrawdownContract is wired directly in BOTH paper scripts (F-001 closed) but no BaseRunner enforcement exists yet; the 71% duplication reduction (AGG-2 / NHT-ARCH-3) and COND-2..7 integration tests remain pending a follow-up 5–10 day dispatch. **Attractor risk:** if a 3rd paper script (Path P3 strategy #3) is added before that dispatch lands, the path of least resistance is copy-paste — F-001 will re-emerge identically. Schedule the REM-2-followup BEFORE any N=3 work to neutralize the attractor.

## Dissents

- **NHT (severity: material_concern; does_block: true — deterministic per full-auto.md):** "Refactors without invariant tests do not close failure modes; they relocate them." [Dissent preserved append-only — see CONSENSUS.md § NHT dissent for verbatim text. PR cycle-2 verified mechanical presence of the 7 NHT-routed tests and 9 relocation defenses in the v2 codebase; NHT severity classification stands per fintech-org rule 6 append-only.]
- **CRO (severity: no dissent this wave; does_block: false):** Approved. R-COV.1 flags 3 unclosed CONDs (COND-4/5/6) routed to deferred-decisions queue as severity:high; these are not dissents but mandatory queue entries.

## Open items requiring CEO acknowledgment

- Commit wave-2b + rework1 changeset (27 source files + 7 test files) — severity: action-required; see CONSENSUS.md § Decision posture (a)
- 3 deferred-decisions queue entries (COND-4/5/6) — severity: high; must be individually acknowledged per deferred-decisions.md hard-acknowledge gate; see CONSENSUS.md § 3 unclosed BC-9-N4-CONDs
- Follow-up dispatch for full REM-2 BaseRunner extraction (COND-2..7), 5–10 days — severity: med; see CONSENSUS.md § Decision posture (b); blocks N=3 transition
- F-007 HTTP-date arithmetic cleanup (saxo/client.py:251 tz-mixing bug) — severity: low; minor cleanup; see CONSENSUS.md § PR rework loop summary residual

## Skill gaps logged this session (N=9)

- pm: KG-QD-1 — Position.strategy_id field existence (CLOSED wave-2b)
- pm: KG-QD-2 — create_strategy() call-sites beyond run_falsification_trial.py (CLOSED wave-2b)
- pm: KG-QD-3 — CRO per-strategy fairness rule needed before REM-5 (CLOSED wave-2a)
- pm: KG-QD-4 — BaseRunner canonical module path ambiguous (CLOSED wave-2a)
- cto: KG-D6-1 — Saxo steady-state request rate per-process empirically unverified (OPEN)
... and 4 more — see CONSENSUS.md § Knowledge gaps surfaced

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS_2026-05-13_rem_arch_review_execute.md` for substance. The full doc is the audit-trail source-of-truth; the SUMMARY is convenience.*
