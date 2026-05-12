# Consensus on: Paper-Launch Authorization — Phase-2 carry-bet stack, 6 deferred governance sub-decisions

**Status:** ratified (CEO huangtm@gmail.com, 2026-05-11T04:05:00Z, "yes")
**Full audit:** see `./CONSENSUS_2026-05-10_paper_launch_authorization.md`
**Session:** `paper-launch-auth-2026-05-10` | `.agent-accountability/ratifications/paper-launch-auth-2026-05-10:phase1:task4.0.yaml`

## Decision

All five staffed roles confirm no capital-loss blocker for paper-loop operation at HEAD `747a6ad`. SD-2 (BC-8) is framed as carry-through confirmation of the 2026-05-06 ratification (not a fresh decision), with all seven CRO BC-8-LIFT-COND-1..7 constraints attaching as the paper-launch-specific binding set. The org recommends CEO authorize paper launch by answering SD-1 through SD-6 below.

## Top-3 risks the CEO should know

1. SD-2 decision-trace duality (severity: major; from PR F-001 + NHT Dissent A): two ratifications for BC-8 without explicit subordination breaks future audit reconstruction — resolved by carry-through framing in this CONSENSUS, but CEO must confirm that framing is the intent.
2. CRO frozenset gap — KG-1 (severity: med; from CRO KG-1): cross-JPY pairs in PM universe bypass 15% JPY-correlated cap if traded; not active for USDJPY-only Phase 1, but auto-trips on any scope expansion.
3. SD-5 calendar reminder is a commitment-only gate (severity: low; from PR F-004): reminder existence is not verifiable at CONSENSUS-sign time; risk is paper launch without 60-day CF-T9 reminder set if T=0 action is missed.

## Dissents

- **NHT (severity: concern; effective: does_block=false):** (A) SD-2 was already decided 2026-05-06 — CEO is being asked to re-decide without being told; (B) SD-6 "verbatim CF-T9 clause" is PM-authored, not NHT-authored verbatim. Full text in CONSENSUS.md Section "Dissent (preserved verbatim)".
- **CRO:** No dissent emitted (decision: approve, size_multiplier 1.0; prior Wave-9 CRO dissent on kill-switch Properties 2/3/4 persists append-only as live-promotion blocker).

## Open items requiring CEO acknowledgment

- **SD-1** (major): Acknowledge NHT BC-4 dissent verbatim (source: CONSENSUS_2026-05-03 Section 3; Wave-7 item 2 closed the engineering gap).
- **SD-2** (major + F-001 + F-002): Confirm 2026-05-06 BC-8 lift carries through to paper launch under 7 CRO BC-8-LIFT-COND-1..7 constraints; OR explicitly decline (reversing 2026-05-06).
- **SD-3** (operational): Choose stale-log disposition for `data/paper_trading_session.log` (269 lines, mtime 2026-05-06): truncate / verify-startup-clears / accept-merged.
- **SD-4** (acknowledgment): Acknowledge frozenset `{USDJPY, GBPUSD}` scope gap (KG-1) and single-account requirement.
- **SD-5** (commitment): Commit to setting 60-trading-day calendar reminder at T=0 (mechanisms: crontab, calendar, at — confirmed by ops-engineer).
- **SD-6** (authoring + F-003 + F-005): Author/approve launch communication with firm-adopted CF-T9 clause; ops-engineer is designated confirming reviewer; confirmation artifact: `docs/launch/sd6-launch-comm-verbatim-check.yaml`.

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets if relevant: `revise sd-2` `revise sd-3` `revise sd-6` `revise nht-dissent-a`

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS.md` for substance. The full doc is the audit-trail source-of-truth; the SUMMARY is convenience.*
