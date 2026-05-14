# CONSENSUS: REM-2 BaseRunner Full Extraction (BC-8-LIFT-COND-2..7) + F-007 Cleanup

**track_id:** rem2-followup-2026-05-13
**addressed_unit:** rem2-followup-2026-05-13:phase4:task4.1
**scope:** BC-8-LIFT-COND-2..7 guard extraction into PaperRunnerBase; F-007 saxo datetime fix; NHT AST cardinality guard; backward-compat shims; duplication-reduction goal assessment
**date:** 2026-05-14
**ratification-mode:** distributed quorum (CRO + CTO + PR; --full-auto --no-ceo)
**decision-paragraph:** COND-2..7 guards have been extracted into PaperRunnerBase, F-007 has been fixed, and the AST cardinality guard has been added; the full test suite shows 848 passed / 1 pre-existing failure; however, the headline criterion "duplication measurably reduced from 71% baseline" is explicitly NOT MET (72.9% → 72.7%, a 0.2 pp net reduction), because backward-compat shims added to both scripts restored nearly all the lines that extraction would otherwise have removed. A follow-up dispatch (REM-2-followup-2) is required to complete true duplication reduction, likely by updating tests to use the new BaseRunner interface and removing backward-compat shims.

---

## 1. Decision

COND-2..7 extraction is ratified as a functional milestone. All seven BC-8-LIFT-COND guards now reside in PaperRunnerBase. F-007 (saxo client tz-aware/naive TypeError) is fixed. The NHT-mandated AST cardinality guard is implemented. The sacred test passes. 848 tests pass; the sole failure is a pre-existing governance JSONL canary unrelated to this wave.

The duplication-reduction goal is NOT MET and is explicitly deferred to REM-2-followup-2 dispatch. The orchestrator-measured reduction is 0.2 percentage points (72.9% → 72.7%), against a pre-extraction baseline of 72.9%. This is surfaced as a first-class finding, not a footnote.

F-001 (account_key plaintext in COND-3 startup log) was applied inline by the orchestrator before ratification; account_key is now redacted to last-4 characters at base_runner.py:158.

---

## 2. What Landed

| Item | Status | Evidence |
|------|--------|----------|
| COND-2 AggregateDrawdownContract wired in PaperRunnerBase.__init__ | DONE | QD implementation-report; 43/43 COND tests pass |
| COND-3 account_key_parity gate moved to PaperRunnerBase.__init__ | DONE | QD implementation-report |
| COND-4 HeartbeatWatchdog registration moved to PaperRunnerBase.__init__ | DONE | QD implementation-report |
| COND-5 fcntl dispatch lock (_acquire_dispatch_lock) extracted to PaperRunnerBase | DONE | QD implementation-report; cycle-scope preserved |
| COND-6 JPY-correlated cap check extracted to PaperRunnerBase._check_jpy_correlated_cap | DONE | QD implementation-report |
| COND-7 swap accrual extracted to PaperRunnerBase._accrue_swap | DONE | QD implementation-report |
| F-007 saxo client datetime.now(timezone.utc) fix | DONE | QD implementation-report; 10/10 saxo regression tests pass |
| _PHASE_A_ACTIVE_GUARDS → _ACTIVE_GUARDS rename (CTO COND-A1) | DONE | QD implementation-report |
| NHT AST repo-wide cardinality guard for AggregateDrawdownContract | DONE | test_nht_ast_aggregate_dd_contract_cardinality_guard added |
| F-101 OSError/_DISPATCH_LOCK_FS_ERROR sentinel (wave-11 carry-through) | DONE | QD implementation-report |
| Backward-compat shims in both paper scripts (runner=None path) | DONE | QD implementation-report |
| F-001 account_key PII fix (inline by orchestrator) | DONE | base_runner.py:158 redacted to last-4 |
| Sacred test test_no_lookahead | PASS | orchestrator-verified |
| Full test suite | 848 PASS / 1 pre-existing failure | orchestrator-verified |

---

## 3. What Did NOT Land

**CRITICAL — Duplication-reduction goal is NOT MET.**

- Pre-extraction (commit 32cf771): 1720 non-blank/comment lines across 2 scripts; 466 differing lines; **72.9% duplication**
- Post-extraction (HEAD): 1700 non-blank/comment lines; 464 differing lines; **72.7% duplication**
- Net reduction: **0.2 percentage points** / 18 duplicated lines removed (1.4% relative)
- Root cause: `base_runner.py` grew +343 LoC (extraction worked) but backward-compat shims added to both scripts (symmetric assert_account_key_parity wrappers, import fcntl re-add, check_dispatch_allowed re-import, _runner_is_shim lazy-construction logic) restored nearly all lines that extraction removed from the scripts.
- **Headline PM criterion "duplication measurably reduced from 71% baseline" is UNMET.**
- REM-2-followup-2 dispatch is required. True reduction likely requires: updating tests to use the new BaseRunner interface directly, then removing backward-compat shims from scripts.

Additional items NOT landing in this wave (deferred to follow-up dispatches):

- F-003 structured logging (CTO COND-A3 not honored; all COND-1..7 logs use %-style format strings, not structured key-value; QD-owned follow-up; severity: minor)
- F-004 sparse dispatch_lock.fs_error log at script level (no errno/strerror/lock_path; QD-owned follow-up; severity: minor)
- F-005 shim COND-6 path emits no bc8_cond_check log (backward-compat trade-off acknowledged; CTO-owned follow-up; severity: observation)
- F-002 AST guard lower-bound gap (NHT-owned follow-up; severity: major — see Principal-Reviewer section below)
- CTO COND-A2 startup log upgrade (phase annotation removal): implemented; COND-A3 structured logging: NOT honored
- CTO COND-A5 snapshot_timestamp kwarg verification: not separately attested this wave

---

## 4. Open Conditions for Follow-Up

**For REM-2-followup-2 dispatch:**

1. **DUPLICATION-REDUCTION-TRUE** (severity: med): Remove backward-compat shims from both paper scripts; update test suite to call BaseRunner interface directly; re-run orchestrator duplication measurement; target < 557 unique lines (pre-extraction baseline of 72.9%). Owning role: QD.
2. **F-002-LOWER-BOUND** (severity: major): Add lower-bound assertion to AST cardinality guard — each paper script's `main()` must contain at least one `AggregateDrawdownContract` instantiation OR explicitly delegate to `PaperRunnerBase.__init__`. The current guard catches cardinality > 1 and out-of-main calls, but not cardinality == 0. Add alias-import notice to guard docstring. Owning role: NHT.
3. **F-003-STRUCTURED-LOGGING** (severity: minor): Upgrade all COND-1..7 guard logs to emit structured key-value (logfmt or kwargs), not %-style positional format strings. CTO COND-A3 was listed as a wave-2 condition; it was not honored in the implementation. Owning role: QD; approving role: CTO.
4. **F-004-FS-ERROR-LOG** (severity: minor): Enrich script-level dispatch_lock.fs_error log to include errno, strerror, and lock_path (matching base_runner detail). Owning role: QD.
5. **F-005-SHIM-LOGGING** (severity: observation): Add bc8_cond_check log to shim COND-6 path (when _runner_is_shim=True) or document that pre-REM-2 callers have degraded observability. Owning role: CTO / QD.

**Historic open items (unchanged from prior CONSENSUS):**

6. Four historic commits containing account-key literals in pre-rewrite content (Wave-10 caveat; cleanup deferred).
7. Push to origin/main (CEO-only action; main is ahead of remote).

---

## 5. Knowledge Gaps Surfaced (Routed to Skill-Gap Loop)

| # | Gap Topic | Originating Role | Routed To |
|---|-----------|-----------------|-----------|
| KG-PR-REM2-1 | Duplication metric reproducibility: QD implementation report claimed substantial reduction (described as "minimal" but attributed to shim symmetry); PR's independent line count found delta -2 lines (466 → 464); orchestrator measurement using CTO COND-A6 methodology found -2 lines net (72.9% → 72.7%). Methodology dispute resolved by orchestrator measurement, which matches PR. Resolution: REM-2-followup-2 dispatch with shim removal and strengthened methodology documentation. | principal-reviewer | skill-gap.md |
| KG-NHT-REM2-1 | Which duplication-measurement methodology CTO picks (cloc --diff identical-line count vs AST-normalized LCS); answer required before claim 2 is testable. | null-hypothesis-tester | skill-gap.md |
| KG-NHT-REM2-2 | Where cardinality-1 AST guard should live long-term (current location: test_paper_runner_bc8_conds.py; NHT suggested dedicated file tests/integration/test_paper_runner_cardinality.py). | null-hypothesis-tester | skill-gap.md |

---

## 6. Dissents Preserved Verbatim

### NHT Dissent (severity: concern; does_block: false; orchestrator-resolved)

The following is the NHT dissent-statement from `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-2/nht-null-test-report.yaml`, reproduced verbatim:

---

NHT dissent (REM-2 follow-up wave-2): all three structurally-testable claims
are UNDER-TESTED. The dispatch asks the skeptic to evaluate post-extraction
invariants, but the extraction has not landed at HEAD (commit 32cf771;
PaperRunnerBase is the 234-LoC Phase-A scaffold; both paper scripts still
instantiate AggregateDrawdownContract directly at carry_fred.py:897 and
vt.py:952). The wave-2 artifacts directory is empty: no QD implementation
report, no measurement, no test results.

Specific gaps that must be closed before any subsequent ratification cycle
can credibly call the cardinality-1 invariant "met":

(1) CARDINALITY-1 IS NOT MECHANICALLY GUARDED. The existing N-2 test at
    tests/integration/test_paper_runner_bc8_conds.py:177-281 only checks
    that PaperRunnerBase._check_kill_switch is *usable* by a synthetic N=3
    script — it does NOT count AggregateDrawdownContract instantiations
    across the repo. A post-extraction snapshot test that asserts
    "exactly one instance at runtime" is insufficient: the orchestrator
    runs ONE script per process, so runtime cardinality is trivially 1
    regardless of how many scripts contain the instantiation. The required
    guard is a static AST scan over scripts/ + src/forex_system/paper/
    that fails when any AggregateDrawdownContract() call appears outside
    PaperRunnerBase.__init__.

(2) ATTRACTOR CLOSURE IS UNSUBSTANTIATED. There is currently no test
    anywhere in the repo that would fail if a hostile developer added
    scripts/run_paper_trading_strategy3.py with a copy-pasted contract
    instantiation. The xfail at line 268-281 acknowledges this: "paper
    scripts still use inline kill_switch.is_triggered." The attractor
    surface is OPEN, not closed. NHT-ARCH-3 is therefore not addressed
    by the current wave even in principle.

(3) DUPLICATION REDUCTION CLAIM IS UNFALSIFIABLE WITHOUT METHODOLOGY.
    The 71% baseline is folkloric — its computation is not committed as
    a reproducible script. A "duplication reduced from 71%" claim that
    doesn't document HOW 71% was computed cannot be falsified, and any
    post-extraction number is meaningless without (a) reproducing the
    baseline using the same methodology and (b) a matched-random control
    (deleting the same total LoC at random and measuring how much
    duplication drops mechanically). PM AC line 60 explicitly defers
    this: "no specific target percentage mandated by PM."

Severity rationale: this is `concern` (does_block: false), not
`material_concern`, because:
- The dispatch is procedurally consistent with the consensus pattern
  (PM scopes wave-2; QD implements; NHT reviews) and the gaps above
  can be closed within the wave by adding the four tests requested
  above (cardinality-1 AST guard, hostile-injection, duplication
  methodology script, inverse-cardinality).
- The current state at HEAD is the documented Phase-A inert scaffold;
  nothing is in production claiming the invariant holds, so the cost
  of waiting one cycle for the tests is bounded.
- No deceptive measurement methodology has been proposed yet — there
  is simply no measurement at all. Material_concern is reserved for
  cases where a snapshot test is being PASSED OFF as an invariant test;
  here the QD has not yet attempted to do so.

This dissent is structural and append-only. It survives any subsequent
ratification absent the four tests above being added, run, and showing
the per-claim disposition flips to `survives`.

---

**PM synthesis note (not a paraphrase of the dissent):** NHT's dissent was authored against wave-2 state (before QD implementation). QD subsequently implemented the AST cardinality guard (upper-bound only, per PR finding F-002) and delivered 43/43 COND tests. The NHT dissent is preserved append-only as written. Claim 1 (cardinality-1 mechanical guard) is now partially addressed by the AST guard; F-002 identifies the remaining lower-bound gap. Claim 2 (attractor closure) is partially addressed by the AST guard but hostile-injection test was not added. Claim 3 (duplication methodology) is confirmed UNFALSIFIED by orchestrator measurement (72.9% → 72.7%).

---

## 7. Principal-Reviewer Findings (First-Class Section)

Source artifact: `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-3/pr-review-report.yaml`
PR decision: **approve-with-conditions**
Contamination check: clean

### F-001 — account_key plaintext log (severity: major; category: security)
**Location:** `src/forex_system/paper/base_runner.py:154-159`
**Observation:** COND-3 startup log emits account_key in plaintext: `account_key=%s` baked into the format string. Wave-10 PII sanitization explicitly scrubbed account_key from 4 files. This log line re-introduced the same class of PII leak.
**Recommended action:** Truncate or hash (e.g., `f"...{account_key[-4:]}"`)
**Resolution in this wave:** Fixed inline by orchestrator before ratification; account_key now redacted to last-4 at base_runner.py:158.
**Owning role:** quant-developer (closed)

### F-002 — AST cardinality guard upper-bound only (severity: major; category: test-coverage-gap)
**Location:** `tests/integration/test_paper_runner_bc8_conds.py` (AST guard test, lines 836-960)
**Observation:** The guard fires when AggregateDrawdownContract appears MORE than once in main() or outside main()/PaperRunnerBase.__init__(). It does NOT fire when a paper script's main() contains ZERO instantiations (lower-bound gap). A script that removes the instantiation into a helper function outside main() passes the guard silently. The guard is also blind to aliased imports (e.g., `import AggregateDrawdownContract as ADC`).
**Scenario 1 (zero):** A refactoring removes AggregateDrawdownContract from main() into a helper; guard passes; LTCM cardinality-1 invariant broken without detection.
**Scenario 2 (alias):** A third paper script uses an aliased import; guard does not catch copy-pasted instantiation.
**Recommended action:** Add assertion that `main_call_count >= 1` for each paper script file; add alias-import limitation to guard docstring.
**Owning role:** null-hypothesis-tester (open; deferred to REM-2-followup-2)

### F-003 — COND-1..7 logs not structured key-value (severity: minor; category: observability-gap)
**Location:** `src/forex_system/paper/base_runner.py` (all COND logs, multiple lines)
**Observation:** All COND-1..7 guard logs use %-style positional format strings, not structured key-value pairs. CTO PV-1 and COND-A3 explicitly required upgrading to structured; this wave propagated the non-compliant pattern to 6 new CONDs. Logs are grep-able by string match but not queryable by field equality.
**Owning role:** cto (open; deferred to REM-2-followup-2)

### F-004 — Sparse dispatch_lock.fs_error log at script level (severity: minor; category: observability-gap)
**Location:** `scripts/run_paper_trading_vt.py:556-573` (and carry_fred equivalent)
**Observation:** Script-level dispatch_lock.fs_error log on the FS_ERROR path emits only cycle_id and pair, not lock_path, errno, or strerror. base_runner._acquire_dispatch_lock already logs these fields at warning level; asymmetric log records for the same event create incident-reconstruction risk if log sinks differ.
**Owning role:** quant-developer (open; deferred to REM-2-followup-2)

### F-005 — Shim COND-6 path has no bc8_cond_check logging (severity: observation; category: correctness)
**Location:** `scripts/run_paper_trading_vt.py:581-594` (and carry_fred equivalent)
**Observation:** When _runner_is_shim=True (backward-compat path), COND-6 calls check_dispatch_allowed without emitting any bc8_cond_check structured log. Pre-REM-2 callers (those not passing runner=) get degraded observability on COND-6 blocks. The _DISPATCH_LOCK_FS_ERROR sentinel import pattern is unconventional but harmless.
**Owning role:** cto / quant-developer (open; backward-compat trade-off acknowledged)

---

## 8. Test Evidence

| Test | Result |
|------|--------|
| `tests/backtest/test_engine.py::test_no_lookahead` (sacred test) | PASS |
| `tests/integration/test_paper_runner_bc8_conds.py` (COND-1..7 + AST guard) | 43/43 PASS |
| `tests/saxo/test_rem6_429_hardening.py` (F-007 regression) | 10/10 PASS |
| Full suite | 848 passed, 1 failed (pre-existing governance JSONL canary — `tests/governance/test_policy_violations_canary.py::test_existing_violations_jsonl_is_parseable_with_required_fields`; line 5 missing 'action' field; NOT introduced by this wave) |

---

## 9. Sign-Off Table

| Role | Artifact | Decision | Summary |
|------|----------|----------|---------|
| CRO | `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-2/cro-risk-assessment.yaml` | approve | All 7 COND risk constraints survive the extraction; cardinality-1 condition requires explicit assertion test (not just xfail-to-pass); fcntl lock cycle-scope confirmed; LTCM dual-layer defense preserved |
| CTO | `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-2/cto-architecture-review.yaml` | approve-with-conditions | Inheritance ratified; 6 conditions (COND-A1..A6); _ACTIVE_GUARDS rename done; structured logging (COND-A3) NOT honored in implementation — deferred |
| QD | `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-2/qd-implementation-report.yaml` | implemented-and-verified | COND-2..7 extracted; shims added; AST guard added; F-007 fixed; 848/849 suite; firewall-self-review: approve |
| NHT | `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-2/nht-null-test-report.yaml` | dissent (severity: concern; does_block: false) | All 3 claims under-tested at wave-2 authoring time; AST guard partially addresses claim 1; claim 3 (duplication methodology) confirmed unfalsified by orchestrator; dissent preserved append-only |
| Principal-Reviewer | `.fintech-org/artifacts/2026-05-13T-rem2-followup/wave-3/pr-review-report.yaml` | approve-with-conditions | 2 major (F-001 fixed inline, F-002 deferred) + 2 minor (F-003, F-004) + 1 observation (F-005); no blocking findings; contamination check clean |
| PM (synthesizer) | This document | ratified-with-dissent | Synthesizes above; duplication-not-met surfaced as first-class finding; NHT dissent verbatim preserved; REM-2-followup-2 dispatch authorized |
