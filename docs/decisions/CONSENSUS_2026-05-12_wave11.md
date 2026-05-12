# Consensus on: Wave-11 — shared-module extract + 4 deferred binding tickets

**Date:** 2026-05-12
**Session:** `wave11-2026-05-11`
**Status:** awaiting-ratification — CEO action required
**Prior consensus:** `CONSENSUS_2026-05-06_wave10_fix_and_amend.md` (commit 747a6ad)
**Deferred-decisions entry:** `.fintech-org/deferred-decisions.jsonl` (reason: breaker:pr-blocking)

---

## Roles staffed

| Role | Artifact | Decision |
|------|----------|----------|
| PM | `.fintech-org/artifacts/2026-05-11T-wave11/pm-acceptance-criteria.yaml` | approve (AC authoring) |
| CTO | `.fintech-org/artifacts/2026-05-11T-wave11/cto-architecture-review.yaml` | approve (claimed_domains: architecture, shared-module-extraction, tech-debt-tracking) |
| QD | implementation evidence: git diff HEAD + 5 new files on disk | approve (implementation) |
| CRO | `.fintech-org/artifacts/2026-05-11T-wave11/cro-risk-review.yaml` | approve (size_multiplier 1.0, 7 binding constraints for W11-2 + W11-3) |
| NHT | `.fintech-org/artifacts/2026-05-11T-wave11/nht-adversarial-verification.yaml` | dissent (severity: concern, does_block: false) |
| Principal Reviewer | `.fintech-org/artifacts/2026-05-11T-wave11/principal-reviewer-review.yaml` | **STALLED — skeleton-only artifact** (decision=needs-revision is a placeholder; findings list empty; rubric_applied_summary empty; two re-spawn attempts both timed out on watchdog) |

---

## Acceptance criteria (from PM)

Source: `.fintech-org/artifacts/2026-05-11T-wave11/pm-acceptance-criteria.yaml`

| Item | Ticket | Done-when predicate | Verified |
|------|--------|---------------------|----------|
| W11-1 | shared-module extraction | New module `src/forex_system/risk/account_key_parity.py` exists; byte-identical behavioral assertion proven; both scripts import from shared module; existing regression gates pass (test_no_lookahead, ruff, pytest count ≥ baseline) | Yes — 8 tests in `tests/risk/test_account_key_parity.py` |
| W11-2 | F-100 JPY mid<=0 guard | Guard fires BEFORE cost computation; structured log emitted per log-as-decision-trace items 1-10 with event `SKIP_INVALID_MID`; symmetric in both paper scripts; no silent USD-nominal fallback on mid<=0 | Yes — 6 tests in `tests/scripts/test_wave11_f100_jpy_guard.py` |
| W11-3 | F-101 OSError dispatch-lock catch | `except BlockingIOError` preserved verbatim; distinct `except OSError as exc` clause added; emits `SKIP_DISPATCH_LOCK_FS_ERROR` with errno+strerror; triggers `kill_switch` with `TriggerReason.INFRASTRUCTURE`; fd closed inline; symmetric in both scripts; `BlockingIOError` appears before `OSError` in the except chain | Yes — tests in `tests/scripts/test_wave11_f101_oserror_dispatch_lock.py`; `TriggerReason.INFRASTRUCTURE` added to `src/forex_system/risk/kill_switch.py` |
| W11-4 | F-102 real-cycle subprocess test | At least one test invokes `run_cycle` directly (not `_WORKER_SCRIPT`); asserts fcntl.flock called, WS01 sentinel on busy path, return action matches `SKIP_DISPATCH_LOCK_BUSY`; materially extends coverage beyond OS-primitive theatre | Yes — 6 tests in `tests/scripts/test_wave11_real_cycle_dispatch_lock.py` |
| W11-5 | F-103 ladder doc clarification | PM clarification addendum appended to `docs/specs/drawdown_ladder_amendment_2026-05-06.md`; records authoritative HC-6 completion semantics; records that CRO reverification yaml (wave10 artifact) satisfies the "before Wave-10 commit" clause; no code change | Yes |

Total: 84 tests passing (23 W11-specific + baseline), sacred test passing, ruff clean.

Hard constraints per PM AC (all met): `paper_only: true`, `no_live_capital: true`, `no_paper_loop_start_by_orchestrator: true`.

---

## Decision

Wave-11 code and documentation are complete on disk. All five deferred Wave-10 binding tickets are closed per PM acceptance criteria. QD implementation evidence is direct (5 new files + 4 modified files visible in working tree at HEAD 747a6ad). CTO and CRO have issued quorum-signatures with approve verdicts. NHT issued a concern-dissent (does_block: false) that was factually corrected in-session. The PR review agent stalled twice on infrastructure watchdog timeout; only a skeleton artifact landed with an empty findings list and an empty rubric_applied_summary. The skeleton's `decision: needs-revision` is a placeholder, not a substantive verdict.

Under `--no-ceo` distributed-ratification (protocols/distributed-ratification.md), the PR-clean precondition is unsatisfied because no substantive review findings list was produced. Under `--full-auto` composition, auto-ratification is blocked (consensus.md Rule 4: PR-blocking breaker). CEO ratification on the basis of CTO/CRO quorum + test evidence is required.

W11-1 extracts `assert_account_key_parity`, `reset_account_key_lock`, and `ACCOUNT_KEY_LOCK_PATH` into `src/forex_system/risk/account_key_parity.py` with a keyword-only `loop_name` parameter (per CTO recommendation F-W11-1-B) and an explicit `__all__` (per F-W11-1-A). W11-2 inserts a halt-cycle guard immediately after mid is computed in both paper scripts, emitting structured log event `SKIP_INVALID_MID` per CRO Decision A (7 required fields including `mid`, `bid`, `ask`, `mid_source`, `cro_decision_artifact`). W11-3 splits the `except BlockingIOError` clause into two: the original clause preserved verbatim, plus a new `except OSError as exc` clause that closes the fd inline, emits `SKIP_DISPATCH_LOCK_FS_ERROR`, and triggers `kill_switch.trigger(TriggerReason.INFRASTRUCTURE, ...)` per CRO Decision B. W11-4 adds real-cycle dispatch-lock tests that call `run_cycle` directly, closing the coverage gap NHT identified. W11-5 appends a PM clarification addendum to the drawdown ladder amendment doc resolving the HC-6/Section-2 line 46 contradiction.

---

## Evidence supporting the decision

- PM AC: all W11-1 through W11-5 done_when predicates verified by QD implementation + NHT adversarial verification (W11-2 and W11-4 claims confirmed real)
- CTO architecture review: approve; evidence at `scripts/run_paper_trading_vt.py:114-165`, `scripts/run_paper_trading_carry_fred.py:131-182`, CRO Wave-2 byte-identity diff; 5 existing risk/ modules as precedent
- CRO risk review: approve; size_multiplier 1.0; 7 binding constraints confirmed for W11-2 (Decision A: halt-cycle) and W11-3 (Decision B: split-clause + kill-switch); dispatch-lock-invariant-verified: true
- NHT adversarial verification: both W11-2-CLAIM-A (mid<=0 silent fallback real defect at 4 call sites) and W11-4-CLAIM-B (coverage gap real) confirmed; concern-dissent on file-pointer error in upstream planning artifact (corrected in-session)
- PR skeleton: `.fintech-org/artifacts/2026-05-11T-wave11/principal-reviewer-review.yaml` — empty findings list, empty rubric_applied_summary, decision=needs-revision placeholder; NOT a substantive verdict
- Deferred-decisions queue entry: `.fintech-org/deferred-decisions.jsonl` (reason: breaker:pr-blocking)
- **Test evidence:** `pytest` — 84 tests pass; sacred test `test_no_lookahead` passes; `ruff check src/` clean
- **File inventory (Wave-11 working tree):**
  - New: `src/forex_system/risk/account_key_parity.py` (W11-1 shared module)
  - New: `tests/risk/test_account_key_parity.py` (8 tests, W11-1)
  - New: `tests/scripts/test_wave11_f100_jpy_guard.py` (6 tests, W11-2)
  - New: `tests/scripts/test_wave11_f101_oserror_dispatch_lock.py` (W11-3)
  - New: `tests/scripts/test_wave11_real_cycle_dispatch_lock.py` (6 tests, W11-4)
  - Modified: `scripts/run_paper_trading_vt.py` (W11-1 import, W11-2 guard, W11-3 split-catch)
  - Modified: `scripts/run_paper_trading_carry_fred.py` (W11-1 import, W11-2 guard, W11-3 split-catch)
  - Modified: `src/forex_system/risk/kill_switch.py` (1-line addition: `INFRASTRUCTURE` enum value)
  - Modified: `docs/specs/drawdown_ladder_amendment_2026-05-06.md` (W11-5 PM clarification addendum)

---

## Decisions NOT made (deferred, out of scope)

- **PR formal review of W11 implementation** — deferred to CEO decision (re-spawn PR or accept current state)
- **Commit of Wave-11 working-tree changes** — CEO decision; 5 new files + 4 modified files remain uncommitted at HEAD 747a6ad
- **Push to origin/main** — existing deferred backlog (main is 51 commits ahead of origin/main as of Wave-10)
- **Kill-switch Properties 2/3/4** — Wave-9 CRO dissent, preserved append-only; live-promotion blocker; out of Wave-11 scope
- **Saxo token revocation** — 24h TTL self-expire; 8 expired tokens scrubbed via filter-branch in Wave-10; no new tokens issued this wave
- **KG-1: _JPY_CORRELATED frozenset expansion** — Phase-1 USDJPY-only; expanding instrument scope requires CEO-authorized trade-scope amendment; deferred
- **KG-2: fcntl.flock cross-host caveat** — documentation-only; single-host architecture in force; deferred

---

## Debate history

No bounded-round debate. All wave-2 role artifacts converged on approve verdicts. NHT concern-dissent preserved verbatim (see section below). CRO issued 7 binding constraints for QD implementation; no role contested the constraints. PR review wave stalled twice on infrastructure watchdog timeout; deferred to CEO per consensus.md Rule 4 (--no-ceo branch, PR-clean precondition unsatisfied). Three total agent stalls this session: NHT-respawn, CRO-substitution/W11-3, PR-first, PR-respawn. No new dissent from CTO, CRO, or QD.

---

## Assumptions we're betting on

Synthesized from CTO, CRO, NHT, and PM AC assumption fields:

1. HEAD is at commit 747a6ad (Wave-10 closure); F-001/F-002/F-008/BC-8/NEW-2 remediations from that commit are in effect and are not reopened by Wave-11.
2. The test environment is stable; 84 tests pass means the implementation is behaviorally sound at HEAD+W11 working tree.
3. `--no-ceo` distributed-ratification mode is in force per CEO direction 2026-05-11.
4. Paper-only mode: no production-account capital at risk during Wave-11 execution.
5. CRO Wave-2 byte-identity claim (Section A.3 of `cro-reverification.yaml`) is accurate — exactly one differing line between the two `assert_account_key_parity` bodies (loop-name discriminator). CTO did not re-run `/usr/bin/diff`; PM relies on CRO evidence.
6. `mid<=0` is a data-quality / feed-corruption event, not a market condition. Probability near-zero in normal operation (no legitimate FX quote produces mid<=0).
7. `TriggerReason.INFRASTRUCTURE` enum value was not pre-existing; QD added it as a 1-line addition to `src/forex_system/risk/kill_switch.py` with no other behavior change.
8. Dispatch-lock fd-lease invariant (lock-acquired-then-released-on-all-paths) is preserved after W11-3 split-catch, as verified by CRO structural analysis of the outer-try / inner-try / finally regions.
9. `BlockingIOError` appears before `OSError` in the W11-3 split-catch chain (Python catches the first matching clause; `BlockingIOError IS-A OSError`; ordering is critical).
10. Wave-11 is backtest-and-paper-loop governance only; no production-account capital is involved at any stage.

---

## Pre-registered falsification

N/A — Wave-11 is a code refactor + bug-fix dispatch targeting paper-loop governance, not a strategy proposal. No alpha hypothesis is being tested. Pre-registered falsification applies to Bet-class dispatches only.

---

## Dissent (preserved verbatim)

Source: `.fintech-org/artifacts/2026-05-11T-wave11/nht-adversarial-verification.yaml`, field `dissent-statement`

> NHT structural dissent — Wave-11 Phase 1 Task 2.4 (append-only):
>
> Both adversarial claims (W11-2-CLAIM-A silent JPY mid<=0 fallback,
> W11-4-CLAIM-B real-cycle dispatch-lock test) are CONFIRMED REAL by
> independent code reading. However, the prompt's source-line references
> for W11-2 are factually incorrect:
>
> - Prompt states F-001 unit conversion logic is at
>   src/forex_system/strategies/vol_target_carry.py:700-760
>   → Actual file is 94 lines total; F-001 logic is not in this file.
> - Prompt states symmetric path in
>   src/forex_system/strategies/carry_fred.py:648
>   → Actual file is 226 lines; F-001 logic is not in this file.
>
> The actual F-001 fix sites (four occurrences total) are:
>   - scripts/run_paper_trading_vt.py:738 (trade engine_units)
>   - scripts/run_paper_trading_vt.py:745 (held engine_units for swap)
>   - scripts/run_paper_trading_carry_fred.py:700 (trade engine_units)
>   - scripts/run_paper_trading_carry_fred.py:704 (held engine_units)
>
> If the implementation engineer follows the prompt's file:line pointers
> literally, they will look in strategies/ and find no defect. This is
> a documentation defect in the upstream planning artifact.
>
> Severity: concern (not strong_objection) because the defects themselves
> are real and the fix is straightforward once the actual sites are
> located. NHT recommends that PM correct the file:line references in
> W11-2 acceptance criteria BEFORE implementation begins.
>
> Additionally, NHT records that the existing tests/scripts/
> test_wave8_high_remediation.py tests F-001 only at price=150 (happy
> path). The W11-2 remediation MUST add at minimum one test case at
> mid=0, mid<0, and mid=NaN to lock down the four call sites against
> regression — without this, the fix is unverified for the actual
> failure mode being claimed.

**Severity:** concern | **does_block:** false | **Effective outcome:** NHT dissent noted and preserved; file-pointer error was corrected in-session before QD implementation began. W11-2 tests cover mid=0, mid<0, mid=NaN per NHT requirement.

---

## Independent review findings (Principal Reviewer)

**PR REVIEW STALLED.**

Artifact at `.fintech-org/artifacts/2026-05-11T-wave11/principal-reviewer-review.yaml`:
- `decision: needs-revision` — this is a placeholder, not a substantive verdict
- `findings: []` — zero items; not zero blocking findings; the list was never populated
- `rubric_applied_summary: []` — empty; no rubric was applied
- `knowledge_gaps: []` — empty
- `sources: []` — empty

Two re-spawn attempts both stalled on watchdog timeout despite skeleton-first inversion. The skeleton artifact's body text references Wave-11 files and claims "All 23 W11 unit tests pass. Sacred test passes. ruff clean. Detailed findings below." but the `findings` field is empty — the review was not completed.

This is NOT a clean PR approve verdict. Under consensus.md Rule 4 --no-ceo + --full-auto composition, this fails the PR-clean precondition, blocking auto-ratification. Deferred to CEO.

---

## Knowledge gaps surfaced (routed to skill-gap loop)

- **CRO KG-1:** _JPY_CORRELATED frozenset gap — only USDJPY+GBPUSD currently; cross-JPY pairs bypass 15% cap if ever added; Phase-1 USDJPY-only means not blocking; expanding frozenset requires trade-scope CEO amendment. Already documented; deferred.
- **CRO KG-2:** fcntl.flock single-host caveat — cross-host deployment would require distributed advisory lock (e.g., Redis-based or NFS-safe); current architecture is single-host paper loop. Documentation-only; deferred.
- **CRO KG-A1 (Wave-11):** TriggerReason.INFRASTRUCTURE existence not verified before Wave-11 dispatch. QD added it as a 1-line enum addition; reported back. Resolved in-session.
- **CRO KG-A2 (Wave-11):** Rate-escalation policy for repeated Decision-A mid<=0 fires within a single session is not specified. Follow-up gap: track per-session counter and escalate to kill-switch on N fires within M minutes (M, N TBD). Out of scope for Wave-11; logged as follow-up.
- **CRO KG-A3 (Wave-11):** Decision A applies guard symmetrically to all pairs, not JPY-only. PM AC HC-W11-2 specifies JPY case; CRO extends to all pairs as binding ruling. Resolved by QD implementation of all-pairs guard.
- **NHT knowledge gaps (Wave-11 artifact):** (a) empirical rate of Saxo API returning zero/missing CloseBid/CloseAsk in production not measured; (b) whether account-equity rules short-circuit before cost-compute for pathological mid not confirmed; (c) W11-2 and W11-4 implementation plans not read (only claim statements reviewed per instruction).
- **PR review-incomplete (this dispatch):** formal staff-review gate did not close; two watchdog stalls; review evidence is test-suite pass + CTO/CRO quorum only.
- **Agent infrastructure watchdog stalls:** 3 stalls in this session (NHT-respawn, CRO-substitution, PR + PR-respawn). Meta-concern for future dispatches. Recommend pausing additional large fan-out dispatches until next session.

---

## Signatures

| Role | Source | Decision |
|------|--------|----------|
| pm | this CONSENSUS (PM authoring, 2026-05-12) | approve |
| cto | `.fintech-org/artifacts/2026-05-11T-wave11/cto-architecture-review.yaml` (claimed_domains: architecture, shared-module-extraction, tech-debt-tracking, cross-system-blast-radius, logging-and-observability-standards) | approve |
| qd | implementation evidence: 5 new files + 4 modified files on disk; 84 tests passing; ruff clean | approve |
| cro | `.fintech-org/artifacts/2026-05-11T-wave11/cro-risk-review.yaml` (claimed_domains: risk-budget-allocation, kill-switch-design-and-testing, market-access-controls, drawdown-contracts, correlation-and-concentration-limits; size_multiplier: 1.0) | approve |
| nht | `.fintech-org/artifacts/2026-05-11T-wave11/nht-adversarial-verification.yaml` (severity: concern, does_block: false; both W11-2 and W11-4 claims confirmed real; dissent on planning-artifact file-pointer error) | dissent |
| principal-reviewer | `.fintech-org/artifacts/2026-05-11T-wave11/principal-reviewer-review.yaml` (**decision: needs-revision PLACEHOLDER — review incomplete; findings list empty; rubric not applied; two watchdog stalls; defer to CEO**) | stalled |

---

*No production-account capital instruction is contained in this document. Paper-loop governance only.*
