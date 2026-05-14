# Consensus on: REM-2 BaseRunner full extraction (BC-8-LIFT-COND-2..7) + F-007 cleanup — DUPLICATION-REDUCTION GOAL UNMET

**Status:** ratified (auto, --full-auto --no-ceo quorum)
**Full audit:** see ./CONSENSUS_2026-05-14_rem2_full_extraction.md
**Session:** rem2-followup-2026-05-13

## Decision (one paragraph)

COND-2..7 guards are extracted into PaperRunnerBase, F-007 is fixed, the NHT AST cardinality guard is added, and 848/849 tests pass — but the headline duplication-reduction criterion is NOT MET: the orchestrator-measured baseline is 72.9% (466 differing lines / 1720 total) and post-extraction is 72.7% (464 / 1700), a net reduction of 0.2 percentage points, because backward-compat shims restored nearly all lines extraction removed from the scripts. REM-2-followup-2 dispatch is needed for true reduction (shim removal + test interface update). F-001 (account_key plaintext log) was fixed inline by orchestrator before ratification.

## Top-3 risks the CEO should know

1. Duplication-not-reduced: 72.9% → 72.7% (0.2 pp net); backward-compat shims are symmetric in both scripts; severity: med; source: orchestrator measurement + PR knowledge-gap
2. PII-fix applied inline by orchestrator: account_key redacted to last-4 at base_runner.py:158; severity: med; source: PR F-001 (major/security)
3. AST cardinality guard upper-bound only: zero AggregateDrawdownContract in a paper script's main() passes silently; lower-bound gap open; severity: med; source: PR F-002 (major/test-coverage-gap)

## Dissents (one-liner each; full text in CONSENSUS.md)

- **NHT (severity: concern; effective: concern):** All 3 claims rated under-tested at wave-2 authoring time; AST guard partially addresses claim 1; claim 3 (duplication methodology) confirmed unfalsified by orchestrator; dissent preserved append-only.
- **PR (decision: approve-with-conditions):** 2 major (F-001 fixed inline, F-002 deferred) + 2 minor (F-003 structured logging, F-004 sparse FS-error log) + 1 observation (F-005 shim COND-6 no-log); no blocking findings.

## Open items requiring CEO acknowledgment

- Duplication-reduction goal NOT MET (REM-2-followup-2 dispatch needed); severity: med
- F-002 AST guard lower-bound gap (NHT-owned follow-up); severity: major (deferred)
- F-003 logs not structured key-value (CTO COND-A3 not honored; QD-owned follow-up); severity: minor
- F-004/F-005 observability gaps (QD/CTO follow-up); severity: minor / observation
- 2 historic items unchanged: 4 historic commits with account-key literals (Wave-10 caveat); push to origin/main (CEO-only)

## Skill gaps logged this session (N=1)

- principal-reviewer: duplication metric reproducibility and methodology dispute (QD implementation report described reduction as "minimal" due to shim symmetry; PR's measurement found delta -2 lines; orchestrator's measurement matches PR; resolution: REM-2-followup-2 dispatch with shim removal and strengthened methodology documentation)

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets if relevant: "revise duplication-claim" "revise pr-conditions" "revise open-items"

---
*This SUMMARY is for routine ratification. Read full CONSENSUS.md for substance.*
