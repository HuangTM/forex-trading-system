# CONSENSUS: REM Arch-Review Execute — 2026-05-13

**Status:** awaiting-CEO-ratification — auto-ratify BLOCKED (NHT material_concern: does_block=true per full-auto.md deterministic lookup; 3 unclosed BC-9-N4-CONDs in deferred-decisions queue: severity high)
**Track:** `rem-arch-review-execute-2026-05-13`
**Addressed unit:** `rem-arch-review-execute-2026-05-13:phase1:task1.0`
**Authored:** 2026-05-13T14:00:00Z
**Produces decision:** true — this consensus authorizes commits of the wave-2b + rework1 changeset (27 source files + 7 test files); commit and push deferred to CEO per hard-constraint 10
**Ratification artifact target:** `.agent-accountability/ratifications/rem-arch-review-execute-2026-05-13:phase1:task1.0.yaml`

---

## Task statement

Implement REM-1 Liskov fix, REM-2 BaseRunner extraction (phase-A), REM-4 stagger config, REM-5 per-strategy allocation rule, REM-6 Saxo 429 hardening, REM-7 drawdown dual-layer — closing the remediation backlog from the CEO-ratified 2026-05-12 multi-strategy architecture review (Option B, Strangler-Fig).

---

## Roles and decisions

| Role | Decision | Confidence | Does-block auto-ratify |
|---|---|---|---|
| PM | acceptance-criteria-authored | high | n/a |
| CTO | approve-with-conditions (D-1.1..D-7.2 all issued) | high | no |
| CRO | approve (R-5.1 + R-7.1 + R-COV.1 issued; 3 CONDs deferred) | high | no |
| Quant Developer | implemented-and-verified (wave-2b: 798 passed / 8 pre-existing failed / 7 skipped; rework1: F-006 exec-namespace fix) | high | no |
| NHT | material_concern dissent (append-only; does_block=true deterministic) | high | YES |
| Principal Reviewer | approve at cycle-2 (10/10 findings closed; one non-blocking F-007 observation) | high | no |

---

## Per-REM closure status

| REM | Title | Status | Files touched | Tests added |
|---|---|---|---|---|
| REM-1 | Strategy ABC Liskov fix — keyword-only rate_data | CLOSED | src/forex_system/core/interfaces.py; src/forex_system/core/types.py; src/forex_system/strategies/registry.py; src/forex_system/strategies/carry.py; src/forex_system/strategies/carry_fred.py; src/forex_system/strategies/carry_momentum.py; src/forex_system/strategies/fred_carry_stripped.py; src/forex_system/strategies/vol_target_carry.py; src/forex_system/strategies/vol_target_carry_no_vol_scaling.py; scripts/run_falsification_trial.py | tests/strategies/test_rem1_liskov_fix.py (20 tests: REM-1-T1/T2/T3 + N-1-a/b/c relocation defenses) |
| REM-2 | PaperRunnerBase extraction — phase-A scaffold (COND-1 only) | PHASE-A-CLOSED | src/forex_system/paper/__init__.py; src/forex_system/paper/base_runner.py | tests/integration/test_paper_runner_bc8_conds.py (8 passing + 7 skipped COND-2..7 markers; N=3 stub test un-skipped in rework1) |
| REM-4 | Config dispatch-stagger offsets | CLOSED | config/default.yaml | tests/core/test_rem4_stagger_config.py (5 tests) |
| REM-5 | Per-strategy allocation rule in exposure_aggregator | CLOSED | src/forex_system/risk/exposure_aggregator.py | tests/risk/test_rem5_per_strategy_allocation.py (11 tests + INV-R5-1/2/3; rework: tie-contention test F-008; aggregate-sum conjunct F-003) |
| REM-6 | Saxo 429 hardening — token bucket + retry | CLOSED | src/forex_system/saxo/client.py | tests/saxo/test_rem6_429_hardening.py (8 tests; rework: contention test F-009; HTTP-date branch F-007) |
| REM-7 | AggregateDrawdownContract — LTCM-class dual-instance defense | CLOSED | src/forex_system/risk/drawdown_contract.py; src/forex_system/risk/kill_switch.py | tests/risk/test_rem7_aggregate_drawdown.py (25 tests + SHUFFLE-CONTROL; rework: compose_dispatch_decision production function F-010; trajectory-fragile counter-example F-002) |

**REM-2 inertness note (severity: HIGH due to attractor dynamic):** Phase-A scaffold instantiates PaperRunnerBase and COND-1 only. Full extraction of COND-2..7 from the paper scripts is deferred to a follow-up dispatch (CTO D-2.3: 5–10 days). AggregateDrawdownContract IS wired in both paper scripts directly (F-001 closed in rework). The 71% duplication reduction (NHT-ARCH-3 / AGG-2) is not yet achieved. **Attractor dynamic (NHT-ARCH-3 framing, devils-advocate-confirmed):** there is no mechanical guard against a 3rd paper script being added (Path P3 strategy #3) before the REM-2-followup dispatch lands. The path of least resistance for the next developer is copy-paste, which would re-introduce F-001 in identical form (AggregateDrawdownContract instantiated 3× rather than once-in-BaseRunner). Mitigation: schedule the REM-2-followup BEFORE any N=3 dispatch is initiated.

---

## PR rework loop summary

**Cycle-1 (REJECT, 2 blocking + 4 major + 4 minor):** 10 findings.

| ID | Severity | Category | One-line description | Closure evidence |
|---|---|---|---|---|
| F-001 | blocking | spec-drift | AggregateDrawdownContract defined but never instantiated — LTCM defense inert | Wired in both paper scripts at startup (vt:952, carry_fred:897); update_equity per bar; force_flat triggers halt_paper_loop |
| F-002 | blocking | test-coverage-gap | N-3 SHUFFLE-CONTROL test tautological — always injects 18% DD by construction | _MockTrajectoryFragileContract counter-example added; real contract fires >=99%, fragile mock <50% on same randomized threshold-breaching trajectories |
| F-003 | major | invariant-violation | INV-R5-1 aggregate-sum conjunct not enforced inside check_per_strategy_allocation | Conjunct now enforced at exposure_aggregator.py:264-292; TestInvR5_1ProductionFunctionEnforcement asserts aggregate_sum_cap_exceeded blockage |
| F-004 | major | invariant-violation | update_equity accepts no timestamp; clock-and-ordering caller discipline only | update_equity now takes keyword-only snapshot_timestamp; monotonicity (drawdown_contract.py:447-452) and staleness check (line 454-462) enforced via StaleEquitySnapshotError |
| F-005 | major | spec-drift | dispatch_stagger_offsets_seconds config key added but no consuming code; CRITICAL validation absent | _validate_dispatch_stagger_config in PaperRunnerBase (base_runner.py:136-196); raises DispatchStaggerConfigError + CRITICAL log on len-mismatch |
| F-006 | major | test-coverage-gap | N=3 stub test @pytest.mark.skip — N-2 cardinality-1 invariant unenforced | @pytest.mark.skip removed; exec namespace supplies __file__+__builtins__ (rework-1); xfail for current-state; N=3 achievability proved |
| F-007 | minor | edge-case | 429 Retry-After HTTP-date parse falls through; missing jitter in malformed-header branch | HTTP-date branch via email.utils.parsedate_to_datetime added; except-fallthrough applies jittered backoff; storm-prevention property holds |
| F-008 | minor | test-coverage-gap | INV-R5-3 tie-break test never exercises a real tie condition | test_tie_break_under_concurrent_submission_at_same_instant: threading.Barrier + mocked time.monotonic + 10 threads forces real tie-condition contention |
| F-009 | minor | test-coverage-gap | Token bucket thread-safety test has no real lock contention (rate_per_min=10000) | Restructured: 50 threads × rate_per_min=10; Barrier; asserts no negative token count under real contention |
| F-010 | minor | test-coverage-gap | INV-R7-1 cross-action composition tested against inline reimplementation, not production code | compose_dispatch_decision production function added; TestInvR7_1CrossActionComposition imports and calls it; bugs in min/AND/OR composition are now caught |

**Residual non-blocking observation (PR cycle-2):** F-007 HTTP-date arithmetic: `retry_dt.utcnow()` is a tz-mixed self-subtraction (tz-aware retry_dt vs naive utcnow()) that **deterministically raises TypeError** on an HTTP-date Retry-After in CPython 3.11+ (devils-advocate-confirmed; not probabilistic). The bug is benign because the except-fallthrough at line 252 catches Exception and applies jittered backoff, preserving the storm-prevention property as a structural consequence of the exception path. Fix: use `datetime.now(timezone.utc)` instead of `retry_dt.utcnow()`. Minor cleanup item for follow-on dispatch; not a blocker.

**Process note (devils-advocate-surfaced):** QD's rework-1 `spec-to-impl-trace` field mis-labeled several finding IDs (e.g., F-008 transposed to a Liskov-related description, F-009 transposed to stagger-related). PR cycle-2 caught this by going to source-of-record (the cycle-1 review-report) for each finding rather than relying on the rework-1 trace. Future spawns inheriting the rework-1 artifact as context should treat the `spec-to-impl-trace` field with skepticism and verify against the cycle-1 finding IDs at `wave-3/principal-reviewer-review-report.yaml`. This is a quality-signal observation about QD spawn accuracy, not a closure issue.

---

## Wave-2b sacred-test status

`tests/backtest/test_engine.py::test_no_lookahead`: **PASS**

Verified after every individual REM (wave-2b QD artifact), after rework cycle-1 (rework-1 QD artifact), and independently by orchestrator. Backtest/ and features/ directories have zero diff vs HEAD; the no-lookahead guarantee is preserved.

---

## 3 unclosed BC-9-N4-CONDs — deferred-decisions queue

The following conditions from the 2026-05-12 architecture review were NOT closed in this wave. Each has been appended to `.fintech-org/deferred-decisions.jsonl` as a severity:high entry.

### BC-9-N4-COND-4 (ML model-risk envelope, SR 11-7)

**Why unclosed:** REM-3 (ML lifecycle interface, ModelServingInterface ABC) and REM-10 (ML kill-switch + risk plumbing greenfield) are explicitly deferred indefinitely per Option B (Strangler-Fig; ML strategy class deferred). No ML infrastructure exists at `src/forex_system/ml/`; implementing SR 11-7 model-risk gates requires a multi-month greenfield build.

**Disposition:** Re-opens when Strategy #4 (ML) work is dispatched. No ML strategy may be added to the paper loop until a model_card, drift_monitor, calibration_tracker, and version-hash gate exist in `src/forex_system/ml/risk/`.

### BC-9-N4-COND-5 (per-strategy kill-switch live-paper exercise at N=2 before N=3)

**Why unclosed:** REM-8 (kill-switch Property-4 live test at N=2) is operator-executed — it requires a running paper session and deliberate kill-switch trigger. This is not orchestrator-doable. Out of scope per PM acceptance-criteria.

**Disposition:** Blocks the transition from N=2 to N=3 paper deployment. Re-opens when ops engineer schedules the live test per the operator runbook. CRO oversight required at runbook close.

### BC-9-N4-COND-6 (strategy_type field for ML risk-routing)

**Why unclosed:** REM-1 adds `strategy_id: str` to Position (CTO D-1.2); it does NOT add `strategy_type`. The `strategy_type` field enabling ML vs classical risk-routing distinction was excluded from REM-1 scope per CTO-Major-1 wording in the 2026-05-12 CONSENSUS. The ML deferral (COND-4) makes this a coupled deferral.

**Disposition:** Re-opens when ML strategy work is dispatched. Coupled with COND-4; Position.strategy_type must exist before any strategy_type=ML registration.

---

## NHT dissent (verbatim, append-only)

Per fintech-org rule 6 and agent-accountability dissent-preservation rule 2, the following is the verbatim dissent text from the NHT wave-2a artifact. It may not be paraphrased, softened, or modified.

---

> STRUCTURAL DISSENT (append-only).
>
> REM-1 / REM-2 / REM-7 are scoped as refactors that REPLACE leaky machinery with
> cleaner machinery. None of the three, as currently scoped, includes a TEST that
> would catch the named failure mode RE-EMERGING under the next change. Refactors
> without invariant tests do not close failure modes; they relocate them.
>
> Specifically:
>
> (a) REM-1 swaps a reflection block for an ABC signature. The next strategy needing
>     a third kind of external artifact (model file, websocket subscription, FRED
>     series of arbitrary cardinality) is ONE new branch away from re-introducing
>     reflection or sentinel-magic somewhere ELSE in the dispatcher. Without the
>     AST-level "no reflection at construction" invariant test, REM-1 is cosmetic.
>
> (b) REM-2 extracts a BaseRunner from N=2. The architectural pattern under test is
>     "duplication is an attractor". The N=3 test (third paper script empirically
>     consuming BaseRunner without override) is the only way to detect the attractor
>     pulling the next change toward "_v2" forking. Without that test, REM-2 closes
>     F-001-class bugs at HEAD but leaves the next F-001-class bug a copy-paste away.
>
> (c) REM-7's aggregate ladder is the LAST line of defense against correlated DD.
>     It MUST be tested with the shuffle-control (N-3 test #2). A happy-path 4×8%
>     scenario that fires the aggregate halt does NOT prove the contract is
>     threshold-shaped vs. trajectory-shaped. Without the shuffle, the aggregate
>     ladder is a kill switch you have not actually tested.
>
> RECOMMENDATION (non-binding, consistent with err-toward-false-negatives):
> Wave-2a closure should require ALL SEVEN tests above as gating evidence.
> Without them, REM-1/2/7 ship as refactors without proof of failure-mode closure.
>
> No further dissent if all seven tests pass — relocation patterns become
> test-detected at the next change.

---

**Mechanical closure record (not a modification of the dissent; additive observational note only — the dissent itself is unmodified above and severity classification stands per fintech-org rule 6 append-only):** PR cycle-2 verified the following test artifacts exist in the v2 codebase: N-1-a/b/c (AST/grep no-reflection invariants in `tests/strategies/test_rem1_liskov_fix.py`), N-2 env-var kill-switch bypass grep in `tests/integration/test_paper_runner_bc8_conds.py`, N-3 SHUFFLE-CONTROL (Monte Carlo 1000 permutations with falsifiable mock-fragile contract, ≥99% halt fire rate threshold) in `tests/risk/test_rem7_aggregate_drawdown.py`, N-3 aggregate-equity no-double-counting test, N-3 LTCM aggregate-fires-before-per-strategy test. PR cycle-2 was a focused-verification pass per select-roles.md v0.4.10 (closure-only verification, NOT full re-application of cycle-1 rubrics). NHT's dissent severity is structurally preserved; whether the test boundaries are sufficient is NHT's call to make at any future re-evaluation, not the orchestrator's.

---

## CRO blocking findings and sign-off conditions

**R-5.1 per-strategy allocation rule (verbatim spec):**
Algorithm: equal-weight-cap-per-strategy. Per-strategy cap = max_correlated_pct / max_active_strategies = 0.15 / 4 = 0.0375 (3.75%) of book equity for JPY-correlated notional. Aggregate cap (15%) unchanged. On per-strategy cap breach: raise AllocationGateBlocked (distinct exception, NOT partial-allocation, NOT queue). Tie-break: strategy_id lexicographic, secondary by monotonic-clock receive-time — NOT lock-acquisition order. Historical analog: Knight Capital (SEC 34-70694) — N parallel components sharing infrastructure without per-component bookkeeping.

**R-7.1 aggregate drawdown contract thresholds (verbatim spec):**
Aggregate ladder: warn=4%, halve=8%, halt=12%, lockout=15%. Tighter-than-N×per-strategy assertion: per-strategy 10/15/20%; N=4 × per-strategy halt = 40% vs aggregate halt 12%; N=4 × lockout = 80% vs aggregate lockout 15%. Equity-snapshot protocol: single broker fetch per cycle, broker-response receive-time canonical timestamp, distributed synchronously to aggregate AND all per-strategy contracts — NOT event-driven on per-fill (avoids LTCM-class race). Cross-action composition: effective_sizing = min(per_strategy, aggregate); effective_dispatch_allowed = AND; effective_force_flat = OR. Historical analog: LTCM 1998 — correlated tail risk realized simultaneously while per-leg gates all passed.

**5 CRO sign-off conditions honored by QD:**

1. REM-5 raises AllocationGateBlocked on per-strategy cap breach — CONFIRMED (exposure_aggregator.py; BC-REM5-RULE-2)
2. REM-5 tie-break is deterministic per INV-R5-3 — CONFIRMED (test F-008: threading.Barrier + mocked time.monotonic; BC-REM5-RULE-3)
3. REM-7 AggregateDrawdownContract receives equity from single broker-fetch receive-time snapshot — CONFIRMED (update_equity now enforces snapshot_timestamp monotonicity + staleness gate; F-004 closure)
4. REM-7 cross-action composition is min/AND/OR — CONFIRMED (compose_dispatch_decision production function; test F-010 invokes production path; all 16 pairs parametrized; INV-R7-1)
5. REM-7 adds TriggerReason.DRAWDOWN_AGGREGATE_HALT and DRAWDOWN_AGGREGATE_LOCKOUT — CONFIRMED (kill_switch.py; BC-REM7-LADDER-5)

---

## Knowledge gaps surfaced (routed to skill-gap loop)

Knowledge-gap entries collected from all wave artifacts per pm.md v0.4.10 aggregation discipline. Routing appended to `.fintech-org/skill-gaps.jsonl` (this session).

| ID | Originating role | Gap topic | Resolution | Routing |
|---|---|---|---|---|
| KG-QD-1 | pm (wave-1) | Whether Position type has any strategy-identifying field at types.py:67-76 | CLOSED in wave-2b QD: confirmed 6-field enumeration; strategy_id added | skill-gap.md (wave 4) |
| KG-QD-2 | pm (wave-1) | Whether create_strategy() call-sites beyond run_falsification_trial.py exist | CLOSED in wave-2b QD: grep confirmed only one non-test call-site | skill-gap.md (wave 4) |
| KG-QD-3 | pm (wave-1) | Exact per-strategy fairness rule for REM-5 not yet authored by CRO | CLOSED in wave-2a: CRO sub-artifact issued R-5.1 equal-weight-cap rule | skill-gap.md (wave 4) |
| KG-QD-4 | pm (wave-1) | Target module path for BaseRunner ambiguous ("or similar") | CLOSED in wave-2a: CTO confirmed canonical path src/forex_system/paper/base_runner.py | skill-gap.md (wave 4) |
| KG-D6-1 | cto (wave-2a) | Per-process request rate to Saxo at steady state with 2 strategies — 30 req/min budget empirically unverified | OPEN: QD should measure actual request count per bar-close cycle in a paper session before setting per-process bucket size | skill-gap.md (wave 4) |
| KG-D27-1 | cto (wave-2a) | Whether AggregateDrawdownContract should be subclass of DrawdownContract or separate class with shared interface | CLOSED in wave-2b: implemented as separate class (not subclass); CRO thresholds authored in wave-2a R-7.1 | skill-gap.md (wave 4) |
| KG-NHT-1 | nht (wave-2a) | REM-1 final ABC signature shape (kw-arg name, default semantics) undecided in spec | CLOSED in wave-2a: CTO D-1.1 confirmed keyword-only `*, rate_data: Optional[pd.DataFrame] = None` | skill-gap.md (wave 4) |
| KG-NHT-2 | nht (wave-2a) | REM-2 BaseRunner consumption pattern (composition vs inheritance) unspecified | CLOSED in wave-2a: CTO D-2.2 confirmed PaperRunnerBase; inheritance pattern adopted in wave-2b | skill-gap.md (wave 4) |
| KG-NHT-3 | nht (wave-2a) | REM-7 aggregate-equity computation (whether it nets cash or sums NAVs) unspecified | CLOSED in wave-2a: CRO assumption confirmed single-currency USD paper account; equity = cash + sum(unrealized P&L) | skill-gap.md (wave 4) |

Session-scoped entries appended to skill-gaps.jsonl: 9

---

## Evidence supporting the decision

- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/pm-acceptance-criteria.yaml` — task scope, hard-constraints, criteria checklist
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-2a/cto-architecture-review.yaml` — 9 architectural decisions (D-1.1..D-7.2); approve-with-conditions
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-2a/cro-risk-assessment.yaml` — R-5.1, R-7.1, R-COV.1 (COND-1..3 closed, COND-4/5/6 deferred); approve
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-2a/nht-null-test-report.yaml` — N-1/N-2/N-3 claims; material_concern dissent; 7 tests requested
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-2b/qd-implementation-report.yaml` — 798 passed; 64 new tests; sacred test PASS; firewall PASS; no commit/push
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-3/principal-reviewer-review-report.yaml` — cycle-1 REJECT; 10 findings (F-001..F-010)
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-3-rework1/qd-implementation-report-rework1.yaml` — rework-1: F-006 exec-namespace fix; all 10 findings claimed closed
- `.fintech-org/artifacts/2026-05-13T-rem-arch-review-execute/wave-3-cycle2/principal-reviewer-cycle2-verification.yaml` — cycle-2 APPROVE; all 10/10 verified closed; F-007 observation flagged non-blocking
- `docs/decisions/CONSENSUS_2026-05-12_arch_review_multi_strategy.md` — source ratified CONSENSUS (CEO-ratified 2026-05-13T00:30:00Z, Option B)

---

## Decisions NOT made (deferred, out of scope)

- REM-3 (ML lifecycle interface, ModelServingInterface ABC) — deferred indefinitely per Option B
- REM-8 (kill-switch Property-4 live test at N=2) — operator-executed; not orchestrator-doable
- REM-9 (per-strategy no-lookahead probe) — gates strategy #3 paper deploy; separate dispatch
- REM-10 (ML kill-switch + risk plumbing greenfield) — deferred with REM-3
- Strategy #3 algorithm selection — separate research dispatch
- Strategy #4 (ML) any work — deferred per Option B
- Full REM-2 BaseRunner extraction (COND-2..7) — follow-up dispatch 5–10 days
- History rewrite of 4 historic commits with account-key literals — CEO decides timing
- Push to origin/main — CEO-only action
- F-007 HTTP-date arithmetic cleanup (retry_dt.utcnow() tz-mixing bug) — minor follow-on item

---

## Assumptions we are betting on

- CEO ratification of Option B at 2026-05-13T00:30:00Z is authoritative; this wave proceeds on that basis
- Pre-existing 8 test failures (test_wave8_high_remediation.py TestAccountKeyParity + governance canary) are unrelated to this wave; verified via git stash before/after by QD
- AggregateDrawdownContract wiring in paper scripts closes the F-001 LTCM defense gap; the 7 skipped COND-2..7 integration tests are acceptable at phase-A because AggregateDrawdownContract is directly wired in both scripts independently of the full BaseRunner extraction
- Per-process token bucket at 30 req/min is sufficient at N=2; KG-D6-1 (steady-state Saxo request rate) remains open and should be measured before N=3 paper deployment

---

## Decision posture

This consensus **produces a decision**: the org has completed wave-2b implementation + wave-3 PR rework cycle and all 10 PR cycle-1 findings are independently verified closed. The changeset is ready for CEO commit.

**Follow-on dispatches authorized:**

(a) CEO commits the wave-2b + rework1 changeset (27 source files + 7 new test files). No push is authorized by this consensus; push timing is CEO decision per Wave-10 history-rewrite caveat.

(b) Follow-up dispatch for full REM-2 BaseRunner extraction (COND-2..7): estimated 5–10 days per CTO D-2.3. This dispatch should be initiated before N=3 paper strategy deployment.

(c) Minor cleanup item: PR cycle-2 F-007 HTTP-date observation — replace `retry_dt.utcnow()` with `datetime.now(timezone.utc)` in `src/forex_system/saxo/client.py:251`. Can be bundled with the full REM-2 dispatch.

**What the orchestrator does NOT do:** no commit, no push, no paper loop start.

---

## Signatures

- pm: @pm-rem-arch-review-execute-2026-05-13
- cto: @cto-rem-arch-review-execute-2026-05-13 (approve-with-conditions; D-1.1..D-7.2 issued)
- cro: @cro-rem-arch-review-execute-2026-05-13 (approve; R-5.1/R-7.1/R-COV.1 issued; COND-4/5/6 deferred to queue)
- quant-developer: @qd-rem-arch-review-execute-2026-05-13 (implemented-and-verified; rework-1 applied)
- null-hypothesis-tester: @nht-rem-arch-review-execute-2026-05-13 (material_concern dissent; append-only; does_block=true)
- principal-reviewer: @pr-rem-arch-review-execute-2026-05-13 (approve at cycle-2; 10/10 closed; F-007 observation non-blocking)

---

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets if relevant: `revise nht-block` `revise cond-deferred` `revise rem2-phase-a` `revise f007-observation`
