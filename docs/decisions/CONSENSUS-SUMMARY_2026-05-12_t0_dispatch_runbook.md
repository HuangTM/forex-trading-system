# Consensus on: T=0 Dispatch Runbook (SD-3 + SD-5 + SD-6 + Persistent Paper-Loop Runner)

**Status:** cycle-2-closed-ready-for-final-ratification
**Full audit:** see `docs/decisions/CONSENSUS_2026-05-12_t0_dispatch_runbook.md` § "Cycle-2 Closure"
**Session:** `.fintech-org/artifacts/2026-05-12T-t0-dispatch-runbook/`

## Decision (one paragraph)

CEO ratified Option A at 2026-05-12T18:30:00Z. Ops-engineer v2 (773 lines, version-bumped) applied all 8 BLOCKING + 11 CONCERN amendments. Cycle-2 verification: **CRO approve** (3/3 blocking closed, 0 new blocking) + **NHT survives** (7/7 blocking closed, 0 new blocking; 1 non-blocking tmux-idempotency gap). Runbook v2 is now safe to execute at T=0 subject to three operator preconditions: SAXO_TOKEN in env, CRO trading-day calendar definition ratified before SD-5, and kill-switch audit-log files clean. Cycle-1 dissents persist append-only across both dissent artifacts.

## Top-3 Risks the CEO Should Know

1. **Scripts never start (F-01); severity: high; source: NHT gap G-1 + CRO AMENDMENT-1.** The tmux commands omit `--token` and `--loop`. Scripts hard-exit within seconds. SAXO_TOKEN is not in env. Phase-3 silently reports "launch succeeded" on a dead session. Knight Capital analog cited by CRO.
2. **Silence-is-success (F-03, F-04, F-05); severity: high; source: NHT G-5/G-13/G-14 + CRO check_id 2.** Three Phase-3 verification predicates (parity gate, dispatch lock, log growth) all accept absence as confirmation. Combined with Risk 1, the most likely real outcome at T=0 (nothing running) is observationally identical to the runbook's definition of success.
3. **SD-5 pre-warning fires on Sunday, 4 days late (F-02); severity: high; source: NHT G-3.** 2026-07-26 is a Sunday; the actual 9-trading-days-remaining mark is 2026-07-22 (Wed). CF-T9 Clause C ratification reminder will fire on a non-working day and leave only ~6 trading days for action instead of 9. "Trading day" definition is unratified.

## Dissents (one-liner each; full text in CONSENSUS.md)

- **NHT (severity: material_concern; does_block: false — no pre-declared block condition):** DISSENT — 7 blocking gaps; scripts never start + 3 silence-is-success verifications + Sunday date math + SHA-256 hash check omitted post-signing; NHT recommends runbook NOT be ratified for T=0; this dissent is append-only. *(See CONSENSUS.md § "Null-Hypothesis Tester Dissent")*
- **CRO (severity: material_concern; does_block: false):** approve-with-binding-conditions; 3 blocking findings (--loop missing defeats supervisor, parity gate silent, kill-switch audit pre-check absent); 5 concern findings; CRO states "CEO should not execute Phase 2" without amendments. *(See CONSENSUS.md § "CRO Blocking Findings")*

## Open Items Requiring CEO Acknowledgment

- **OPTION SELECTION (blocking):** Choose Option A (re-dispatch ops-engineer), B (manual amendments), or C (CEO self-applies before execution); see CONSENSUS.md § "Decision Posture"
- **Trading-day definition (blocking for SD-5):** CRO must ratify whether 60 trading days = 60 weekdays (naive) or holiday-adjusted; affects SD-5 pre-warning and hard-deadline dates; see F-02
- **SAXO_TOKEN status (blocking):** Token not in env as of NHT audit; CEO must set before any execution; see KG-8
- **Kill-switch audit state (blocking):** CEO must inspect `data/kill_switch_audit.log` and `data/kill_switch_audit_cf.log` for stale HALTED entries before T=0; see F-07

## Ratification Prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise \<X\>)**

*Suggested revise targets: `revise option-b`, `revise option-c`, `revise amendment-list`, `revise nht-block`*

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS.md` for substance. The full doc is the audit-trail source-of-truth; the SUMMARY is convenience.*
