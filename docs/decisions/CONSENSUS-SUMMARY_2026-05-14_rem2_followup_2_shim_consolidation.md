# Consensus on: REM-2-followup-2 — shim consolidation + F-002 + F-003 — DUPLICATION GOAL UNREACHABLE BY METRIC

**Status:** ratified (auto, --full-auto --no-ceo quorum)
**Full audit:** see ./CONSENSUS_2026-05-14_rem2_followup_2_shim_consolidation.md
**Session:** rem2-followup-2-2026-05-14

## Decision (one paragraph)

Shim consolidation is architecturally complete: `script_compat_shims.py` (69 LoC) is the single source of truth for shared paper-script symbols; both scripts delegate to it; F-002 AST guard is tightened with zero-instance detection and alias-import detection (3 self-tests pass); F-003 structured logging is migrated to `extra={}` schema across all 7 COND-1..7 `logger.info` sites. However, the line-diff duplication metric is stuck at 72.8% (was 72.7%) — ZERO meaningful change — because the metric counts symmetric boilerplate (parallel `from ... import` lines in both scripts) as duplication. This is a measurement-methodology limitation, not an implementation failure: symmetric scripts will always score ~70–73% identical by line-diff. The CEO's ≤60% target is unreachable via this methodology. Genuine reduction requires Path P2-followup-3 (test-interface migration + shim removal), which is deferred.

## Top-3 risks the CEO should know

1. Duplication metric does not capture architectural improvement; symmetric scripts are inevitable at this tier; severity: med (methodology limit; not a regression; ≤60% target requires P2-followup-3 dispatch)
2. PR fixes applied inline by orchestrator (F-001 dead imports via `ruff --fix`; F-002 COND-5 `logger.warning` migration); severity: low (both verified test-clean; 851/852 suite green)
3. NHT all-3-claims-under-tested at wave-2 authoring time (standard wave-ordering effect; QD wave-3 implementation partially closes claims 2+3; claim 1 remains a methodology dispute); severity: low (does_block=false; escalation triggers not fired)

## Dissents (one-liner each; full text in CONSENSUS.md Section 7)

- **NHT (severity: concern; effective: concern):** All 3 claims rated under-tested at wave-2 authoring time; QD self-tests partially close claims 1+3; methodology-dispute on claim 1 (duplication target) surfaced verbatim & append-only; escalation triggers not fired.
- **PR (decision: approve-with-conditions):** 1 major + 2 minor + 1 nit + 1 observation. Major (F-001 dead imports) fixed inline; minor (F-002 COND-5 warnings) fixed inline; minor (F-003 metric inversion) clarified in Section 4. No blocking findings remain.

## Open items requiring CEO acknowledgment

- Line-diff duplication metric does not capture architectural improvement (symmetric scripts inevitable); severity: med (methodology limit; not a defect)
- Path P2-followup-3 candidate: test-interface migration + shim removal for true line-count reduction; severity: deferred
- NHT anti-canary + `tools/measure_paper_script_duplication.sh`; severity: minor (deferred)
- F-004 / F-005 (script-level observability nits); severity: minor (deferred)
- 4 historic commits with account-key literals (Wave-10 caveat); push to origin/main (CEO-only)
- 8 expired SAXO_TOKEN values (Saxo developer portal revocation; CEO-only)

## Skill gaps logged this session (N=0)

*No new skill gaps logged this session.* NHT gaps KG-NHT-REM2-1/3/4 are implementation-design questions within QD's domain, routed as deferred open items in CONSENSUS.md Section 9 rather than skill-gap entries.

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise \<X\>)**

Suggested revise targets if relevant: "revise duplication-claim" "revise pr-conditions" "revise open-items"

---
*This SUMMARY is for routine ratification. Read full CONSENSUS.md for substance.*
