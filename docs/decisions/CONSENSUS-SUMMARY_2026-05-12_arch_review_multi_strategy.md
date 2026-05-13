# Consensus on: Assess existing system architecture for suitability to expand from 2 validated strategies to 4 (adding intraday-classical + ML) via Strangler-Fig vs rewrite.

**Status:** ratified (CEO huangtm@gmail.com 2026-05-13T00:30:00Z; Option B authorized; both dissents preserved append-only)
**Full audit:** see `./CONSENSUS_2026-05-12_arch_review_multi_strategy.md`
**Session:** `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/`

## Decision (one paragraph)

The existing system CAN absorb ONE additional intraday-classical strategy via Strangler-Fig,
but ONLY after completing 4 prerequisite remediations (Liskov fix, BaseRunner extraction,
Position.strategy_id field, drawdown-ladder semantics pinned). An ML strategy is DEFERRED —
it requires greenfield src/forex_system/ml/ infrastructure that does not exist and is
multi-month work. The full rewrite is NOT recommended (6 days of targeted fixes vs 3-4 months
of rewrite risk). T=0 paper trading for the existing two strategies is unaffected by this
review. No live-capital authorization.

## Top-3 risks the CEO should know

1. Liskov violation in Strategy ABC (6 of 10 overrides leak construction contract): severity high; surfaces from NHT + PR-F-001
2. 71% paper-script duplication means a single CRO-constant amendment applied to N-1 of N scripts creates Knight-Capital-class silent drift; severity high; surfaces from NHT + PR-F-002 + CRO
3. Correlated drawdown across strategies bypasses per-strategy ladder — LTCM-class aggregate-DD blind spot at N≥3; severity high; surfaces from CRO Q4

## Dissents (one-liner each; full text in CONSENSUS.md)

- **NHT (severity: material_concern; does_block: true):** Dissents from "system is robust/flexible/scalable enough to absorb 2→4 via Strangler-Fig without rework" — 3 blocking findings (Liskov, 71% duplication, ML infrastructure absent); narrows acceptable claim to ONE classical strategy conditional on 4 remediations; ML DEFERRED. See § NHT dissent verbatim.
- **CRO (severity: material_concern; does_block: true):** BC-8-LIFT-COND-1..7 cannot absorb N≥3 as-is; 6 new binding constraints (BC-9-N4-COND-1..6) required; ML strategy additionally blocked pending SR 11-7 model-risk gate. See § CRO blocking findings verbatim.

## Open items requiring CEO acknowledgment

- Strangler-Fig conditional-yes decision: authorize only intraday-classical (#3), AFTER 4 prerequisite remediations complete; severity: high; see § Decision posture Option B
- ML strategy (#4) DEFERRED pending greenfield ml/ design review; no timeline set; severity: high; see § Acceptable narrowed scope
- 6 new CRO binding constraints (BC-9-N4-COND-1..6) require explicit CEO ratification before N≥3 paper deployment; severity: high; see § CRO blocking findings verbatim
- PR-F-005 orchestrator process gap (on-disk artifacts not redacted before principal-reviewer wave-3); severity: concern; see § PR adjudication

## Skill gaps logged this session (N=13)

- cto: walkforward.py multi-strategy portfolio-level evaluation support unknown
- cto: strategy #3 specific algorithm class and pair universe unknown
- cto: cross-host flock caveat (NFS silent failure) — scaling boundary
- cto: quantified lock contention probability at 4H frequency with 4 strategies
- cro: Saxo session boundary definition (one bearer = one bucket vs per-IP/per-process)
- ... and 8 more — see CONSENSUS.md § Knowledge gaps surfaced

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets: "revise nht-block" "revise cro-bc9" "revise decision-posture"

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS.md` for substance. The full doc is the audit-trail source-of-truth; the SUMMARY is convenience.*
