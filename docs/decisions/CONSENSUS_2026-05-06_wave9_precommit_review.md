# Consensus on: Wave-9 Pre-Commit Review (Code/Test Review of Uncommitted Changes)

## Roles staffed

- **pm** — Wave-1 acceptance criteria authoring; Wave-4 synthesis and CONSENSUS drafting; dissent preservation routing; ratification artifact production
- **cto** — Architecture scope review: F-003 LoC-cap deviation, kill-switch property analysis, log-as-decision-trace rubric, Group C script classification, blast radius assessment
- **quant-developer** — Implementation correctness: F-001 USDJPY unit-conversion closure, F-002 USDJPY E2E test adequacy, F-005 pip_v heuristic, F-006 TotalValue double-counting, ruff and pytest gate verification
- **cro** — Risk gate review: BC-8 residual control presence/absence, cost-feedback-into-operational-equity architecture position, second-loop authorization status, forbidden-phrases scan, drawdown contract enforcement, kill-switch design rubric
- **null-hypothesis-tester** — Adversarial re-verification: F-001 fix claim falsification, F-002 USDJPY test theatre detection, NEW-2 architecture position verification, BC-8 cross-process race structural check, Group B test adequacy review
- **principal-reviewer** — Wave-3 synthesis: per-file-group verdict table, independent re-derivation of findings from source code (Wave-2 artifacts deliberately not read to preserve independence), sacred test and baseline gates verified by execution

---

## Acceptance criteria (from PM, Wave-1)

Source: `.fintech-org/artifacts/wave9-precommit-review/pm-acceptance-criteria.yaml`

**Hard constraints (binding gates):**

- **A-F001 (Group A — do-not-commit gate):** F-001 closed: vt.py and carry_fred.py must apply `_to_engine_units` JPY unit-conversion (divide USD-nominal by price) before computing cost_usd for USDJPY, eliminating the ~150× overstatement. Fail-condition: cost_usd = cost_pips * pip_v * target_units with no JPY price division → verdict do-not-commit for Group A.
- **B-F002 (Group B — commit-after-fixes gate):** test_wave8_high_remediation.py must contain at least one USDJPY E2E parity test (price≈150, JPY-pair convention), not EURUSD. Fail-condition: only EURUSD E2E test present → verdict commit-after-fixes.
- **A-F003 (Group A — CEO ratification gate):** LoC delta >50 with no CEO ratification → verdict commit-after-fixes pending CEO action.
- **A-BC8 (second-loop authorization gate):** carry_fred.py must have per-strategy 7.5% budget tickets OR cross-process advisory file-lock around [get_positions → compute_exposure → check_dispatch_allowed → execute_signal]; absent either → carry_fred may commit as engineering artifact but second-loop authorization remains BLOCKED.
- **NHT-cost-feedback (CROSS-cost-feedback-routing):** Cost-feedback architecture position must be explicitly documented by CRO and NHT; ambiguity → review incomplete.
- **Forbidden-phrases scan:** 0 matches across all Group A, B, C files.
- **Sacred test:** tests/backtest/test_engine.py::test_no_lookahead must PASS.
- **Ruff no-regression:** ruff check src/ ≤19 errors.
- **Pytest no-regression:** pytest ≥686 tests passing.

---

## Decision

Based on the 5 review artifacts (Wave-2: CTO, QD, CRO, NHT; Wave-3: Principal Reviewer), all independently re-verifying source code, the synthesized verdict is:

**Group A (production scripts — scripts/run_paper_trading_vt.py, scripts/run_paper_trading_carry_fred.py, scripts/monitor_regime_triggers.py, tests/scripts/test_cf_t9_monitor.py): DO-NOT-COMMIT.** F-001 (USDJPY cost-formula 150× overstatement) is unfixed in both paper-loop scripts. `_to_engine_units` is not called anywhere in either script (independently confirmed by CTO at engine.py:544-573 analysis, QD at carry_fred.py:648 and vt.py:689, NHT via grep returning zero matches, and PR via spec-to-implementation trace). The PM AC hard gate A-F001 fail-condition is met; verdict is do-not-commit. Note: monitor_regime_triggers.py and test_cf_t9_monitor.py changes are independently sound (PR F-012-PR: no observed defects) but they are bundled in Group A and share the do-not-commit verdict; they may be split into a separate commit if Group A blockers cause extended delay.

**Group B (test file — tests/scripts/test_wave8_high_remediation.py): DO-NOT-COMMIT** (NHT verdict) **/ COMMIT-AFTER-FIXES** (CTO, QD, PR verdicts). The majority verdict among roles with code-correctness authority (CTO, QD, PR) is commit-after-fixes. NHT escalates to do-not-commit because two tests at lines 540-562 and 564-611 assert F-001-buggy values (USDJPY cost computed on USD-nominal units, not engine-units), which would FAIL if F-001 were truly fixed — these tests enshrine the bug. Both verdicts are preserved; **CEO must decide**: commit-after-fixes (fix only F-002 USDJPY E2E test, leave test_rebalance/test_full_entry to be fixed when F-001 lands) OR do-not-commit (fix F-001 + F-002 + F-008 together before any commit). The Wave-10 fix scope below covers both paths.

**Group C (8 untracked diagnostic scripts): COMMIT-AS-IS.** All 8 scripts (buy_and_hold_baseline.py, buy_and_hold_sharpe.py, characterize_drawdowns.py, diagnose_carry_momentum.py, long_only_carry_redesign.py, run_phase1_revalidate.py, vol_target_portfolio.py, vol_targeting.py) classified diagnostic/research by CTO, QD, and PR. Zero Saxo execution imports. Forbidden-phrases scan: 0 matches. No Group A-level gates required. Subject to operator confirmation that no credentials exist in data/ files.

**Group D (decision/governance docs — docs/decisions/*.md): COMMIT-AS-IS.** Forbidden-phrases scan clean (CRO confirms Group A and Group C; QD confirms no forbidden phrases across 13 files; PM AC D-commit-policy gate met). These are governance artifacts.

**Group E (audit/governance data — .fintech-org/, .agent-accountability/, data/): COMMIT-AS-IS.** Session artifacts. Subject to operator confirmation that no live API tokens or credentials are in any data/ file (CRO PM AC gate E-commit-policy).

**BC-8 second-loop authorization: REMAINS BLOCKED.** Neither residual control is implemented: (a) per-strategy 7.5% budget tickets — absent; (b) cross-process advisory file-lock (fcntl O_CREAT|O_EXCL or flock) around [get_positions → compute_exposure → check_dispatch_allowed → execute_signal] — absent. The existing O_CREAT|O_EXCL lock at carry_fred.py:121-172 and vt.py:106-157 is a startup-time account-key parity gate only, not a per-cycle dispatch lock. CRO veto on concurrent operation of both loops persists. Single-loop (vt alone) authorization from Wave-5 CONSENSUS stands.

**NHT NEW-2 (cost-feedback architecture): MATERIAL CONCERN PERSISTS.** The submitted code implements the CRO-recommended log-only architecture (raw broker TotalValue feeds dd_contract/kill_switch; paper_equity_bt_equiv is written to equity log only, never fed back into risk primitives). CRO concurs this is correct. NHT's prior material_concern — that operational equity must include cost-feedback for the drawdown ladder threshold semantics to match the pre-registered ladder — is unaddressed by code and unaddressed by any PM spec amendment. No CEO ruling on this architectural question exists. The material_concern persists structurally and requires CEO ruling or PM spec amendment to formally close.

**CEO actions required before any further wave dispatch:**
1. Ratify or reject the do-not-commit verdict on Group A. If ratified: authorize Wave-10 to fix F-001 (apply `_to_engine_units` at the paper-loop sizer-output boundary in vt.py and carry_fred.py).
2. Decide Group B scope for Wave-10: (a) commit-after-fixes path — fix F-002 (USDJPY E2E parity test) + F-008 (rewrite tests at lines 540-562 / 564-611 to assert engine-parity values, not F-001-buggy values) together with the F-001 fix; OR (b) do-not-commit path — same combined fix. Either way, tests at lines 540-562 and 564-611 must be rewritten to assert correct engine-parity values before commit.
3. Authorize commit of Groups C, D, and E (subject to operator confirmation that no credentials are in data/ files).
4. Decide F-003 LoC-cap deviation: net Group A production delta is 351 lines added / 2 removed vs. the original 50-line hard constraint (7× overage). Ratify the deviation with the rationale provided by CTO (scope expanded by NHT-mandated closures: atomic lock, reset CLI, cost-model block) OR direct re-shrink before commit.
5. Resolve NEW-2 cost-feedback architecture: confirm CRO log-only is the firm binding position (close NEW-2 as accepted architectural decision) OR direct PM spec amendment that explicitly downgrades operational equity to broker TotalValue and accepts the resulting threshold drift, OR direct implementation of cost-adjusted equity into dd_contract/kill_switch.
6. Authorize Wave-10 to implement BC-8 residual control: either option-A (per-strategy 7.5% budget tickets) or option-B (fcntl advisory file-lock around the per-cycle critical section) — CRO recommends option-B as the lower-friction path (~30 lines, no shared-state dependency, testable with two pytest subprocesses).

---

## Evidence supporting the decision

- **F-001 independently confirmed by 4 roles:** CTO at `engine.py:544-573` and `carry_fred.py:634-648` / `vt.py:674-689`; QD at `carry_fred.py:648` (`_cost_usd = _cost_pips * _pip_v * _trade_units`, no price division) and `vt.py:689` (identical); NHT via grep confirming zero `_to_engine_units` matches in either paper-loop script; PR via numerical re-derivation (target=20,000 USD-nominal at 0.75 pips: engine cost ~1.00 USD, paper cost ~150.00 USD).
- **F-002 independently confirmed by QD and PR:** `test_wave8_high_remediation.py:337-340` admits EURUSD chosen "to avoid the engine's JPY unit-convention conversion"; `test_wave8_high_remediation.py:53` PAIR="USDJPY" with SIZE=10_000 hardcoded (not derived from sizer), making TestCostModelParity tautological.
- **F-008 identified by NHT and PR:** `test_wave8_high_remediation.py:540-562` asserts `expected_cost = 0.75 * 0.01 * 1500 = 11.25` for USDJPY at price=150; engine-equivalent is `0.75 * 0.01 * (1500/150) = 0.075`. These tests would fail if F-001 were fixed.
- **BC-8 residual control absence confirmed by QD, NHT, CRO, PR:** grep for fcntl/flock/LOCK_EX/budget_ticket/7.5%/0.075 returns zero matches. `carry_fred.py:515-539` and `vt.py:535-566` dispatch critical sections have no cross-process lock.
- **Baseline gates PASS (confirmed by QD and PR via shell execution):** Sacred test: 1 passed; ruff: 19 errors (no regression); pytest: 686 passed.
- **Forbidden-phrases scan: PASS (confirmed by QD and CRO):** 0 matches across all Group A (4 files), Group B (1 file), Group C (8 files) — 13 files total.
- **Group C safe to commit:** CTO via file read and grep (0 Saxo execution imports across all 8 scripts); QD via grep (0 matches for execute_signal/SaxoClient/live=); CRO via forbidden-phrases scan.
- **NHT NEW-2 code position documented:** QD at `carry_fred.py:473, 481, 665` and `vt.py:484, 498, 704-711` confirms log-only architecture; CRO concurs.
- **Source artifacts:**
  - `.fintech-org/artifacts/wave9-precommit-review/pm-acceptance-criteria.yaml`
  - `.fintech-org/artifacts/wave9-precommit-review/cto-architecture-review.yaml`
  - `.fintech-org/artifacts/wave9-precommit-review/qd-implementation-review.yaml`
  - `.fintech-org/artifacts/wave9-precommit-review/cro-risk-review.yaml`
  - `.fintech-org/artifacts/wave9-precommit-review/nht-adversarial-review.yaml`
  - `.fintech-org/artifacts/wave9-precommit-review/principal-reviewer-review.yaml`
  - `.agent-accountability/dissents/wave9-precommit-review:cro.yaml`
  - `.agent-accountability/dissents/wave9-precommit-review:nht.yaml`

---

## Decisions NOT made (deferred, out of scope per PM AC)

- Paper-loop launch authorization (separate CEO decision; no orchestrator authority)
- Saxo token rotation (separate runbook; not attempted in this dispatch)
- New backtest runs or strategy registrations
- Trial counter increments (Wave-9 is code-review, not a research trial)
- CRO _JPY_CORRELATED frozenset asymmetry fix (GBPUSD inclusion noted by PR F-004-PR as structurally questionable; PM-out-of-scope)
- Watchdog observer thread top-level exception handler (Wave-8+ hardening per CTO Wave-6 note)
- Stale-lock TTL detection (NHT finding-5 reduced to non-blocking concern; Wave-9+ scope)
- --self-test CLI flag for kill-switch Property 4 (PR F-007 medium; PM AC explicitly out-of-scope for this wave; tracked as Wave-10 hard gate before live-capital scope)
- SHORT-path swap accrual direction verification (NHT finding-C low severity; Wave-9+ scope)
- Re-adjudication of any NHT dissent already recorded as append-only in prior CONSENSUS docs
- CEO ratification of CONSENSUS_2026-05-05_wave8_remediation.md (separate CEO action; deferred-decisions.jsonl is empty per PM AC confirmation)
- Items 9 and 10 of the pre-flight checklist (BLOCKED-CEO-action; not addressable in code review)
- Shared equity log path split to per-strategy files (CTO design smell; PR F-006-PR major; not blocking for paper scope — tracked Wave-10)
- assert_account_key_parity / reset_account_key_lock extraction to shared module (CTO tech-debt item; PR F-011-PR nit; ~110 LoC extractable; not blocking here)
- RotatingFileHandler maxBytes / backupCount parameterization (CTO; not blocking)
- carry_fred regime-inactive equity-log gap (PR F-007-PR: EQUITY_LOG_PATH append unreachable on SKIP_REGIME_INACTIVE path; observability gap not correctness bug; Wave-10)
- equity log cycle_id and event fields (CTO log-as-decision-trace items 5 and 9; Wave-10 logging hardening)

---

## Apparent role-disagreement on Group A verdict (synthesis note, NOT a debate trigger)

CRO's risk-architecture verdict was "size-reduced (multiplier 0.5), Group A commit-as-is" — but this verdict is scoped to CRO's domain authority (risk architecture terms): forbidden-phrases clean, log-only architecture correctly implemented, drawdown contract machine-checkable and triggers on broker peak-to-trough, kill-switch property-5 PASS. CRO's "commit-as-is" reflects that the code is correct from a risk-architecture standpoint. CRO explicitly does not deep-verify F-001 cost-formula correctness because Python/code-correctness is outside CRO's authority (FORBIDDEN skills include python).

CTO, QD, NHT, and PR — all of whom DID verify F-001 directly via source code (their designated domains) — converge on do-not-commit for Group A. This is a domain-of-authority composition, not a true conflict: CRO's "commit-as-is" applies to the risk architecture properties CRO owns; the correctness blocker (F-001) overrides it for the overall commit decision because correctness is the domain of QD (primary) and CTO/NHT/PR (corroborating).

**No bounded-debate required.** This is a clean domain composition: four roles with code-correctness authority find the same blocking bug; one role reviewing only risk architecture does not see it because reading Python cost formulas is outside that role's scope. The synthesis is unambiguous.

---

## Assumptions we're betting on

- The uncommitted diff matches the git-status snapshot recorded at conversation start (Groups A-E as listed in the PM AC); all 4 Wave-2 reviewers and Wave-3 PR read the same uncommitted code.
- `engine.py:_to_engine_units` (at engine.py:544-573, confirmed by QD and CTO) is the canonical unit-conversion path that defines what "backtest-equivalent cost" means for JPY pairs.
- `test_wave8_high_remediation.py` was written to enshrine current paper-loop behavior (USD-nominal units), not to test correctness against an independent oracle — this is the NHT interpretation, confirmed by PR F-008-PR and QD F-001-TEST-BYPASS.
- The pytest 686/ruff 19 green status reflects what would be committed (QD and PR both ran the suite; the F-001-bugged code does not cause test failures because the tests assert the buggy values).
- `VolTargetSizer.calculate_size()` returns USD-nominal units (confirmed by PR via `sizing/vol_target.py:78`: `units = scale * leverage_cap * account_equity`); this is the value `_trade_units` in the paper-loop cost formula.
- deferred-decisions.jsonl being empty does NOT constitute CEO ratification of any Wave-8 closure path; the CEO dispatched Wave-9 code review before deciding closure scope.
- Group C scripts have never been connected to a live execution path (confirmed by CTO and QD via grep returning 0 matches for SaxoClient/execute_signal/live= across all 8 scripts).
- Saxo paper account is the only execution destination; no live-capital route is present in these scripts.

---

## Pre-registered falsification

N/A — this is a code-review dispatch, not a strategy or model proposal. No pre-registered falsification conditions apply. This is stated explicitly to satisfy the CONSENSUS structure requirement.

---

## Dissent (preserved verbatim)

### CRO dissent

Source: `.agent-accountability/dissents/wave9-precommit-review:cro.yaml`, field `dissent_text`. Severity: `strong_objection`. `does_block: false`.

> I dissent from any interpretation of the Wave-9 commit that lifts the BC-8 second-loop authorization veto.
>
> STRUCTURAL FINDING. The startup-time account_key parity gate at scripts/run_paper_trading_carry_fred.py:121-172 and scripts/run_paper_trading_vt.py:106-157 is a CORRECT control for the "two loops aimed at different accounts" failure mode. It is NOT a control for the "two loops aimed at the same account, racing on the per-cycle dispatch path" failure mode that BC-8 was specifically designed to address.
>
> The race window is concretely:
>
>   1. carry_fred run_cycle at T0 calls backend.get_positions() -> sees aggregate JPY exposure 14% -> compute_exposure -> check_dispatch_allowed(jpy_pct=14%, ...) returns OK -> proceeds to compute target_units.
>
>   2. vt run_cycle at T0 + 50ms (or any time before carry_fred's execute_signal lands and is reflected in get_positions) calls backend.get_positions() -> sees the SAME 14% JPY exposure -> check_dispatch_allowed returns OK -> proceeds to compute its own target_units.
>
>   3. Both loops call backend.execute_signal in rapid succession. Both fills land. Aggregate JPY-correlated transient exposure reaches the documented 24-30% peak — i.e. ~9-15 percentage points OVER the BC-8 cap of 15%.
>
> This is the residual control gap. The Wave-8 CONSENSUS pre-declared it as a blocker for second-loop authorization. The Wave-9 code does not implement option-A (per-strategy 7.5% budget tickets) and does not implement option-B (cross-process advisory file-lock around [get_positions -> compute_exposure -> check_dispatch_allowed -> execute_signal]). Therefore the gap persists. Therefore the veto on starting both loops concurrently against the same paper account PERSISTS.
>
> RECOMMENDATION NOT TAKEN: implement option-B before the second paper loop is started. Option-B is the lower-friction path: fcntl.flock(LOCK_EX | LOCK_NB) on a shared lock file (e.g. data/dispatch_lock.flock) acquired at the head of run_cycle, released after backend.execute_signal returns and reconciliation completes. If LOCK_NB fails to acquire, the cycle SKIPs with a new sentinel SKIP_DISPATCH_LOCK_BUSY. This is ~30 lines of code, has no shared-state dependency, and is testable with two pytest subprocesses racing on a temp lock file.
>
> KILL-SWITCH DESIGN GAPS (secondary structural finding). The current kill-switch design at src/forex_system/risk/kill_switch.py:94-403 fails three of the five kill-switch-design properties for any future live-capital path:
>
>   Property 2 (operable by the most junior person on the desk): FAIL. Halt is "find the PID, send SIGINT". No big-red-button, no shared-file flag, no API endpoint, no documented one-command halt flow.
>
>   Property 3 (killed within a known SLA): FAIL. No declared SLA, no measured p99 time-to-flatten.
>
>   Property 4 (tested in prod, on a schedule, against live sessions): FAIL. No record in .fintech-org/kill-switch-tests.jsonl (file does not exist). No --self-test flag. No scheduled test on the org calendar.
>
> These are ACCEPTABLE for paper-only operation (no real capital at risk). They are BLOCKERS for any live promotion. I record this here so the Wave-9 commit cannot later be cited as evidence that the kill-switch was reviewed and approved for general use. It was reviewed and approved for SINGLE-LOOP PAPER operation only.
>
> COST-FEEDBACK ARCHITECTURE position (CONCURRENCE not dissent). I CONCUR with the current implementation: risk primitives (KillSwitch.check_and_trigger, DrawdownContract.assess) operate on raw broker equity, and the cost-adjusted paper_equity_bt_equiv view is a log-only research artifact. This is the correct architecture. Feeding cost-adjusted equity into risk primitives would create a recursive trigger surface where cost-model bugs become risk-halt bugs and where the trigger point diverges from broker ground truth. NHT NEW-2 disagreement is informational and preserved separately; it does not modify this position.

### Null-Hypothesis Tester dissent

Source: `.agent-accountability/dissents/wave9-precommit-review:nht.yaml`, field `dissent_text`. Severity: `block-threshold`. `does_block: true`. **THIS FLAG IS PRESERVED: NHT does_block = true. CEO must see this verbatim.**

> NHT DISSENT — Wave-9 pre-commit review (verbatim, append-only, must be preserved in CONSENSUS.md if Wave-9 attempts closure):
>
> Four of the five substantive Wave-8 remediation claims FAIL adversarial re-verification at the code-inspection level (no execution required):
>
> (1) F-001 (USDJPY cost-formula fix) is FALSE. _to_engine_units is not called anywhere in either run_paper_trading_carry_fred.py or run_paper_trading_vt.py. The cost-deduction lines (vt.py:689, carry_fred.py:648) compute _cost_pips * _pip_v * _trade_units where _trade_units is the raw USD-nominal output of VolTargetSizer.calculate_size — NOT the engine-converted units. For USDJPY at price ~150, the paper-loop cost is therefore ~150x larger than the engine cost. The 150x overstatement bug from CONSENSUS_2026-05-05 Finding-J PERSISTS unchanged.
>
> (2) F-002 (E2E parity test) is THEATRE. TestCostModelParity asserts equality between two hand-rolled formulas that share the same input self.SIZE=10_000 and apply mathematically identical multiplications — by construction they can never disagree. TestE2EParity is the only run_backtest-exercising test and it explicitly chooses EURUSD over USDJPY in lines 339-342 to AVOID the conversion that F-001 was supposed to fix. The test that would have caught F-001 — engine USDJPY equity_curve == paper-loop USDJPY paper_equity_bt_equiv at the entry bar — does not exist.
>
> (3) NEW-2 (cost-feedback architecture). The code implements log-only: drawdown_contract.assess() and kill_switch.check_and_trigger() both consume raw broker TotalValue (carry_fred:455+481+473; vt:466+498+484); the cost-adjusted paper_equity_bt_equiv is written to disk but never read back into either contract. CRO's position is that log-only is correct. NHT's prior material_concern (Wave-8) — that operational equity must include cost-feedback for the contract's threshold semantics to match the pre-registered drawdown ladder — is unaddressed by code and unaddressed by any PM spec amendment in the changeset. The material_concern PERSISTS.
>
> (4) BC-8 (cross-process race) is structurally UNCLOSED. Neither file-lock (fcntl/flock/LOCK_EX) nor per-strategy 7.5% budget tickets are implemented anywhere in the changeset. The TestAtomicLockAndReset suite tests the ACCOUNT-KEY parity lock, not the BC-8 dispatch race. CRO's BC-8 veto in CONSENSUS_2026-05-05 Section 4 explicitly named these two acceptable residual controls; neither has landed. Multi-strategy paper authorization remains contraindicated until either residual control is wired and tested under a concurrent-process test (two simultaneous run_cycle calls reading stale exposure must NOT both pass check_dispatch_allowed).
>
> (5) Group-B test adequacy is INADEQUATE. test_rebalance_cost_charged_on_delta_not_full_target asserts cost == 0.75 * 0.01 * 1500 = 11.25 USD on a USDJPY rebalance, which is the BUGGY formula's output. If F-001 were truly fixed (engine-units used), this test would compute cost on engine-units = 1500/150 = 10 units and assert ~0.075 USD — failing the existing assertion. The test ENSHRINES the bug it was supposed to detect. This is the canonical anti-pattern: a regression test that locks in the wrong behavior because it was written against the broken implementation, not against an independent oracle.
>
> Recommended Wave-9 closure path (NOT in scope of this dissent, surfaced for CEO/PM):
>   - Apply _to_engine_units conversion at the paper-loop sizer-output boundary so target_units sent to backend.execute_signal are in engine-units for JPY pairs. Update the equity-write cost formula to use the same engine-units.
>   - Replace TestCostModelParity SHARED_SIZE assertions with a true E2E test that calls run_backtest on USDJPY with rebalance_mode="continuous" and compares its equity_curve.iloc[1] to a paper-loop run_cycle's paper_equity_bt_equiv at the same entry event.
>   - Either implement fcntl advisory file-lock around the [get_positions -> check_dispatch_allowed -> execute_signal] sequence in both loops (lock acquired BEFORE get_positions and held through execute_signal — a lock acquired after position-read still permits the race), OR wire per-strategy budget tickets at 7.5% each in check_dispatch_allowed config.
>   - Either land cost-adjusted equity feedback into dd_contract/kill_switch, OR produce a PM spec amendment that explicitly downgrades operational equity to broker TotalValue and accepts the resulting threshold drift.
>   - Fix test_rebalance_cost_charged_on_delta_not_full_target to assert against the engine's USDJPY cost (engine-units), not the paper-loop's USD-nominal cost.
>
> Until items (1)-(4) are remediated by code and item (5) is remediated by test, NHT does NOT co-sign Wave-9 closure of F-001, F-002, NEW-2, or BC-8.

---

## Independent review findings (Principal Reviewer)

PR `decision: reject`. Source: `.fintech-org/artifacts/wave9-precommit-review/principal-reviewer-review.yaml`. Per protocol rule 2: findings are append-only; PM has not paraphrased, softened, reordered, or omitted any entry. All findings reproduced verbatim from the `findings` list. The Decision paragraph above explicitly addresses each blocking finding (F-001-PR → Wave-10 fix; F-002-PR → Wave-10 fix; F-008-PR → Wave-10 rewrite; F-005-PR → CEO ruling required).

---

**F-001-PR**
- severity: blocking
- category: correctness
- location: `scripts/run_paper_trading_vt.py:689` (`_cost_usd = _cost_pips * _pip_v * _trade_units`); `scripts/run_paper_trading_carry_fred.py:648` (`_cost_usd = _cost_pips * _pip_v * _trade_units`)
- observation: Both paper loops compute per-trade cost as `_cost_usd = _cost_pips * _pip_v * _trade_units` where `_trade_units` is the USD-nominal target (e.g. 20,000 for a $10k-equity, 2x-leverage, signal=1 USDJPY position, returned by VolTargetSizer.calculate_size at `sizing/vol_target.py:78` — "units = scale * leverage_cap * account_equity"). The engine equivalent (`engine.py:331-332, 358`) uses delta in engine units, where engine units = `_to_engine_units(usd_nominal, pair, price)` = `usd_nominal/price` for JPY-quoted pairs (`engine.py:571-572`).
- inference: For USDJPY at price ≈150, the paper-loop cost is therefore 150x larger than the engine-equivalent cost. Concrete numerics: target=20,000 USD-nominal at 0.75 pips entry cost: engine: 0.75 * 0.01 * (20000/150) ≈ 1.00 USD (correct); paper: 0.75 * 0.01 * 20000 = 150.0 USD (overstated 150x). A fictitious -150 USD entry cost on $10k equity is -1.5% per cycle and will dominate paper_equity_bt_equiv, falsifying the equity-curve parity that the cost model is supposed to provide. This is exactly the bug F-001 was supposed to close per PM hard-constraint `pm-acceptance-criteria.yaml:56-58` and criterion A-F001 lines 69-79.
- evidence: `vt.py:605` `_raw_target_units = sizer.calculate_size(sig, equity, mid, 0.0, pair)`; `vt.py:609` `target_units = _raw_target_units * _dd_sizing_multiplier`; `vt.py:684-685` `_cost_pips=...; _trade_units = target_units (USD-nominal)`; `vt.py:689` `_cost_usd = _cost_pips * _pip_v * _trade_units (NO division by price)`; `carry_fred.py:577` `raw_target_units = sizer.calculate_size(sig, equity, mid, 0.0, pair)`; `carry_fred.py:581` `target_units = int(raw_target_units * size_multiplier * effective_dd_multiplier)`; `carry_fred.py:643-644` `_cost_pips=...; _trade_units = target_units`; `carry_fred.py:648` `_cost_usd = _cost_pips * _pip_v * _trade_units (NO division by price)`; `engine.py:299` `target_units = _to_engine_units(usd_nominal, pair, price)`; `engine.py:331-332` `cost_pips = cost_model.entry_cost(pair, abs(delta)); equity -= cost_pips * pip_value * abs(delta)`; `engine.py:544-573` `_to_engine_units`: returns `usd_nominal/price` for JPY-quoted pairs; `vol_target.py:78` `units = scale * leverage_cap * account_equity (USD nominal output)`.
- recommended-action-class: tighten-invariant
- owning-role: quant-developer
- notes: Recommended invariant (no implementation here): for any (pair, target_units, price) tuple the paper-loop equity-write must agree numerically with engine.run_backtest's equity reduction at the same trade event, INCLUDING for JPY pairs where unit convention diverges between USD-nominal and engine units. Fix is structural (route through `_to_engine_units` or PairInfo.pip_value) and outside reviewer scope.

---

**F-002-PR**
- severity: blocking
- category: test-coverage-gap
- location: `tests/scripts/test_wave8_high_remediation.py:334-446` (TestE2EParity uses EURUSD); `tests/scripts/test_wave8_high_remediation.py:38-149` (TestCostModelParity uses shared SIZE=10_000 short-circuiting the unit conversion)
- observation: The PM hard-constraint F-002 (`pm-acceptance-criteria.yaml:57`, criterion B-F002 lines 133-143) requires "at least one TestE2EParity or equivalent test that drives both the engine and the paper-loop cost path using a USDJPY trade tuple (price≈150, JPY-pair convention), not EURUSD." The submitted TestE2EParity at lines 334-446 explicitly states (lines 337-340): "Uses EURUSD (not USDJPY) to avoid the engine's JPY unit-convention conversion (_to_engine_units divides USD nominal by price for JPY pairs)." TestCostModelParity at lines 38-149 uses USDJPY but with SIZE=10_000 fed DIRECTLY to both `_engine_*_cost_dollars(self, model)` (line 60, 65) and to `_paper_loop_*_cost_dollars(self, model, pair, size)` (line 73, 81); both helpers reproduce the SAME local formula `cost_pips * pip_value * size` with no `_to_engine_units` conversion. They are therefore identical by construction and cannot detect the bug.
- inference: The single test that COULD have driven the unit-conversion path (TestE2EParity at line 374, `test_entry_cost_parity_engine_vs_paper_loop`) explicitly excludes the case where F-001 manifests. F-002 is not closed regardless of test pass/fail status. A correctly-shaped test would: (a) use USDJPY at price≈150, (b) run the engine via `run_backtest` (which applies `_to_engine_units`), (c) run `vt_mod.run_cycle` with the same USDJPY target, (d) assert equity-curve numerical parity between the two paths. The current TestE2EParity is structurally insufficient to satisfy F-002.
- evidence: `test_wave8_high_remediation.py:53` PAIR = "USDJPY" (TestCostModelParity); `test_wave8_high_remediation.py:60-65` `_engine_entry/exit_cost_dollars`: `cost_pips * 0.01 * 10000` directly; `test_wave8_high_remediation.py:73,81` `_paper_loop_entry/exit_cost_dollars`: identical formula; `test_wave8_high_remediation.py:117-118` paper == engine asserted (tautological); `test_wave8_high_remediation.py:337-340` TestE2EParity docstring explicitly avoids USDJPY; `test_wave8_high_remediation.py:346` PAIR = "EURUSD" (TestE2EParity); `test_wave8_high_remediation.py:402-403` only EURUSD bar 1 compared to engine equity_curve.
- recommended-action-class: add-test
- owning-role: quant-developer
- notes: Required test shape: drive both `run_cycle` (USDJPY, price=150, target=20000) and `run_backtest` (USDJPY, signal=1, entry_delay=1, constant_capital_sizing=True with VolTargetSizer at the same parameters). Assert `paper_equity_bt_equiv` after entry == `engine.equity_curve.iloc[1]` within ε. Per role contract no implementation provided; this is the failure pattern the test must catch.

---

**F-003-PR**
- severity: major
- category: spec-drift
- location: `scripts/run_paper_trading_vt.py` (+172 / -1); `scripts/run_paper_trading_carry_fred.py` (+158 / -1); `scripts/monitor_regime_triggers.py` (+21 / -0)
- observation: Net production-script LoC delta against HEAD is 351 added / 2 removed (verified with `git diff HEAD --numstat`). The original Wave-8 50-LoC hard constraint cited in `pm-acceptance-criteria.yaml:58` is exceeded by ~7x.
- inference: Per PM criterion A-F003 (lines 81-90) the verdict-if-fail is "commit-after-fixes (pending CEO ratification artifact)". I do not see CEO ratification in scope here. Independent of the cost-formula blocking finding, F-003 alone gates Group A from CEO-authorized paper-loop launch (which is out-of-scope for THIS review per `pm-acceptance-criteria.yaml:224`). The commit decision can proceed once F-001/F-002 are resolved, but the LoC-cap deviation must be surfaced explicitly to the CEO before any launch authorization.
- evidence: `git diff HEAD --numstat`: 21+0 `monitor_regime_triggers.py`, 158+1 `run_paper_trading_carry_fred.py`, 172+1 `run_paper_trading_vt.py`; `pm-acceptance-criteria.yaml:58` declares 50-LoC hard constraint; Decision-doc `CONSENSUS_2026-05-05_wave8_remediation.md` is referenced as evidence in PM AC; its CEO-ratification status not verifiable in this review scope.
- recommended-action-class: escalate-to-owning-role
- owning-role: ceo

---

**F-004-PR**
- severity: blocking
- category: invariant-violation
- location: `scripts/run_paper_trading_carry_fred.py:514-540` (aggregation gate); `scripts/run_paper_trading_carry_fred.py:701-716` (execute_signal calls); `scripts/run_paper_trading_vt.py:535-566` (aggregation gate); `scripts/run_paper_trading_vt.py:734-765` (execute_signal calls); (no per-cycle file lock anywhere)
- observation: The invariant "aggregate JPY-correlated notional ≤ CRO_MAX_CORRELATED_PCT across BOTH paper loops" is checked once per cycle in each loop independently. Concretely: carry_fred sequence: `backend.get_positions()` → `compute_exposure` → `check_dispatch_allowed` → `execute_signal`; vt sequence: `backend.get_positions()` → `compute_exposure` → `check_dispatch_allowed` → `execute_signal`. No cross-process serialization between [`check_dispatch_allowed` → `execute_signal`]. The startup-time `assert_account_key_parity` (`vt.py:106-157`, `carry_fred.py:121-172`) is an account-key consistency gate, NOT a per-cycle dispatch gate.
- inference: Two simultaneously-running paper loops both reading positions before either has dispatched can each see exposure within the 15% envelope, both pass `check_dispatch_allowed`, and both then dispatch — yielding brief aggregate exposure up to 30% (2x CRO_MAX_CORRELATED_PCT). Race window is the time between `get_positions()` and `execute_signal()` completion (≥1.5-2 s of explicit sleeps in the rebalance branch `vt.py:749`, plus broker latency). PM hard-constraint BC-8 (`pm-acceptance-criteria.yaml:59`) requires either per-strategy 7.5% budget tickets OR cross-process advisory file-lock. Neither is present in code. CRO Wave-8 BC-8 veto remains in effect; carry_fred second-loop cannot be authorized until this closes.
- evidence: `carry_fred.py:514-540` single-loop view of exposure at dispatch time; `vt.py:535-566` single-loop view of exposure at dispatch time; grep results: only ACCOUNT_KEY_LOCK_PATH lock exists; no cross-process per-cycle lock; no fcntl import; no advisory-lock primitive; `exposure_aggregator.py:46` `_JPY_CORRELATED: frozenset[str] = frozenset({"USDJPY", "GBPUSD"})` — note also that GBPUSD inclusion as JPY-correlated is structurally questionable but PM-out-of-scope.
- recommended-action-class: tighten-invariant
- owning-role: cro
- notes: Per PM AC criterion A-BC8 (lines 92-102) verdict-if-fail is "commit-as-is for Group A code; second-loop authorization remains BLOCKED." So this finding does not block COMMIT of Group A — but does block any CRO sign-off on running carry_fred concurrently with vt.

---

**F-005-PR**
- severity: blocking
- category: spec-drift
- location: `pm-acceptance-criteria.yaml:60` (NHT cost-feedback disagreement requirement); `scripts/run_paper_trading_vt.py:484, 498`; `scripts/run_paper_trading_carry_fred.py:473, 481`
- observation: Both paper loops feed RAW broker equity (return value of `fetch_account_equity` → `balance.TotalValue`) into: `kill_switch.check_and_trigger(equity)` — vt:484; carry_fred:473; `dd_contract.assess(equity)` — vt:498; carry_fred:481. The cost-adjusted equity (`paper_equity_bt_equiv = equity - _cost_usd + _swap_usd`) is computed AFTER these checks (vt:710; carry_fred:665) and only written to the equity log. It is not fed back into any risk primitive.
- inference: The submitted code therefore takes a definite position: cost-feedback into operational risk is LOG-ONLY. PM AC (lines 60, 207-220) requires this position to be EXPLICITLY documented and confirmed by either a PM spec amendment or a CEO ruling. I find no such amendment in scope. Per criterion CROSS-cost-feedback-routing (line 220), verdict-if-fail is "review is incomplete; re-dispatch required" — but the policy choice itself is also a substantive risk decision (NHT NEW-2 vs CRO-recommended architecture). The reviewer flags this for governance routing but does NOT take a stance on which architecture is correct; that is owned by CRO + NHT + CEO.
- evidence: `vt.py:484` `if kill_switch.check_and_trigger(equity)  # raw broker equity`; `vt.py:498` `_dd = dd_contract.assess(equity)          # raw broker equity`; `vt.py:710` `paper_equity_bt_equiv` computed but only written to log; `carry_fred.py:473` `if kill_switch.check_and_trigger(equity)`; `carry_fred.py:481` `_dd = dd_contract.assess(equity)`; `carry_fred.py:665` `paper_equity_bt_equiv` only written to log; `drawdown_contract.py:129` `def assess(self, current_equity: float)  # consumes raw float`; `kill_switch.py:208` `def check_and_trigger(self, current_equity: float)  # consumes raw float`.
- recommended-action-class: clarify-spec
- owning-role: ceo
- notes: Either route: PM amendment naming raw-broker-equity as the binding contract for risk primitives (closing NEW-2 as deferred), OR a CEO ruling that cost-adjusted equity must feed the risk primitives (re-opening implementation work). Either path resolves the gap; reviewer cannot resolve it unilaterally per PM AC line 60.

---

**F-006-PR**
- severity: major
- category: invariant-violation
- location: `scripts/run_paper_trading_vt.py:67` (EQUITY_LOG_PATH = "data/paper_trading_session.log"); `scripts/run_paper_trading_carry_fred.py:86` (EQUITY_LOG_PATH = "data/paper_trading_session.log"); `scripts/run_paper_trading_vt.py:704` (with open(EQUITY_LOG_PATH, "a") as _ef); `scripts/run_paper_trading_carry_fred.py:658` (with open(EQUITY_LOG_PATH, "a") as _ef)
- observation: Both paper loops define EQUITY_LOG_PATH with the same value "data/paper_trading_session.log" and both write append-only json-serialized records. The append uses plain Python `with open(..., "a")` — no fcntl.flock, no atomic-rename pattern, no per-record framing beyond a trailing newline.
- inference: POSIX guarantees atomic O_APPEND writes only for buffers ≤ PIPE_BUF (typically 4096 bytes Linux, 512 bytes macOS for FIFOs, larger for regular files but not formally guaranteed). The serialized record can exceed this threshold when strategy_params is non-trivial; the JSON dictionary written includes "ts", "strategy", "equity", "regime_active" (carry_fred only), "cost_pips", "cost_usd", "swap_usd", "paper_equity_bt_equiv". For a small dict this is well under 4KB, so race-induced line interleaving is unlikely with current schema — but the invariant "equity log lines are individually parseable JSON" is not enforced by code; it depends on dict-size discipline. Future schema additions (e.g. nested context, larger strategy_params) could silently break audit-log JSON parsing under concurrent writes.
- evidence: `vt.py:67`, `carry_fred.py:86` same path constant; `vt.py:704-711`, `carry_fred.py:658-666` same write pattern; no fcntl import in either file (verified by grep).
- recommended-action-class: tighten-invariant
- owning-role: quant-developer

---

**F-007-PR**
- severity: major
- category: observability-gap
- location: `scripts/run_paper_trading_carry_fred.py:447-452` (SKIP_REGIME_INACTIVE early return); `scripts/run_paper_trading_carry_fred.py:670-678` (HOLD path equity-write block bypassed)
- observation: In carry_fred, when `regime_active_status()` returns False, `run_cycle` returns at line 452 BEFORE any of the cycle's equity / cost / swap tracking runs. `_emit_ws02` is called (line 450-451), but the EQUITY_LOG_PATH append at line 658-666 is unreachable on this path. Compare to vt where the equity-write block runs on the no-action "HOLD FLAT" branch as well.
- inference: For multi-day periods of regime-inactive (the expected steady state per BC-1, "size_multiplier = 0.0 when regime flag is FALSE; zero positions permitted"), there is no per-cycle equity record from carry_fred. The audit reconstructibility principle (rubric 3) is that any decision boundary should be reproducible from the log alone. The ws02 trace captures regime_active=False, but the paper-equity time series for carry_fred has gaps during inactive regimes. This is not a correctness bug; it is a decision-trace completeness gap that will complicate post-mortem analysis if a kill-switch / drawdown event happens during a regime transition.
- evidence: `carry_fred.py:447-452` SKIP_REGIME_INACTIVE return; `carry_fred.py:658-666` equity-log append unreachable on this path; `vt.py:704-711` equity-log append always reached (no early-return before it).
- recommended-action-class: add-log
- owning-role: quant-developer

---

**F-008-PR**
- severity: blocking
- category: test-coverage-gap
- location: `tests/scripts/test_wave8_high_remediation.py:540-562` (test_rebalance_cost_charged_on_delta_not_full_target); `tests/scripts/test_wave8_high_remediation.py:564-611` (test_full_entry_cost_not_delta_when_opening)
- observation: `test_rebalance_cost_charged_on_delta_not_full_target` asserts at line 553-557: `delta = abs(6_500.0 - 5_000.0)  # = 1500`; `expected_cost = 0.75 * 0.01 * delta  # = 11.25`; `assert entry["cost_usd"] == pytest.approx(expected_cost, abs=1e-4)`. For pair=USDJPY at price=150, the engine-equivalent cost is `0.75 * 0.01 * (1500/150) = 0.075`. The test asserts 11.25 — the value produced by the F-001-bugged formula. `test_full_entry_cost_not_delta_when_opening` similarly asserts `0.75 * 0.01 * 5000 = 37.5` (line 607) where engine would compute `0.75 * 0.01 * (5000/150) ≈ 0.25`.
- inference: These tests would FAIL if F-001 were correctly fixed. They lock in the buggy paper-loop formula as the asserted contract, making the regression a red-test for any future fix attempt. This is a "test-asserts-the-bug" class of test-coverage-gap that PM would not classify as F-001 closure but as F-001 entrenchment. A test that should detect the bug instead enshrines it.
- evidence: `test_wave8_high_remediation.py:541-557` `expected_cost = 0.75 * 0.01 * delta` where delta=1500; `test_wave8_high_remediation.py:607-611` `expected_cost = 0.75 * 0.01 * 5_000` for USDJPY entry; `test_wave8_high_remediation.py:483` `entry_price=150.0` (so engine-equivalent units = nominal/150); engine.py:331-332 + `_to_engine_units` would produce `delta-engine-units = 1500/150 = 10` units, `cost = 0.75 * 0.01 * 10 = 0.075`.
- recommended-action-class: clarify-spec
- owning-role: quant-developer
- notes: Required: re-author these two tests to assert engine-equivalent cost values. Until F-001 fix lands, the same test must fail on current code; after fix, must pass on corrected code. Reviewer provides the failure mode, not the implementation.

---

**F-009-PR**
- severity: minor
- category: numerical
- location: `scripts/run_paper_trading_vt.py:674` (`_pip_v = 0.01 if "JPY" in pair.upper() else 0.0001`); `scripts/run_paper_trading_carry_fred.py:634` (same); `tests/scripts/test_wave8_high_remediation.py:71, 79` (same)
- observation: Both paper loops use a string-substring heuristic to assign pip value. "JPY" in "USDJPY".upper() is True (correct). But "JPY" in "JPYAUD".upper() is also True — this is correct only by coincidence for FX pairs that include JPY at all; the heuristic does not consult PairInfo.pip_value (which is the canonical source per CLAUDE.md "pair costs ... no hardcoded magic numbers"). A pair-symbol typo or extension to a synthetic cross would silently fall through.
- inference: Low-blast-radius today (only USDJPY in instrument-universe per `pm-acceptance-criteria.yaml:50-52`). But this same pattern is repeated in five places (vt cost, carry_fred cost, test_wave8 helper x2, ws02_emit literal in carry_fred line 634). The class-fix would route pip value through PairInfo. For now, observation only.
- evidence: `vt.py:674` `_pip_v = 0.01 if "JPY" in pair.upper() else 0.0001`; `carry_fred.py:634` same; `test_wave8_high_remediation.py:71, 79` same in helper functions; `engine.py:537-541` `_get_pip_value(pair)` implements identical heuristic — engine has same minor issue but is in src/, not in scope for this review.
- recommended-action-class: tighten-invariant
- owning-role: quant-developer

---

**F-010-PR**
- severity: minor
- category: edge-case
- location: `scripts/run_paper_trading_vt.py:467-481` (equity-fetch branch); `scripts/run_paper_trading_carry_fred.py:455-470` (equity-fetch branch)
- observation: `fetch_account_equity` returns `Optional[float]`; the only check on the successful-fetch path is `if equity > 0` (`vt:367`; `carry_fred:355`). Negative or NaN `balance.TotalValue` would coerce through the truthy check. `balance.get("TotalValue", 0.0)` without isinstance/type check means a malformed broker payload (string, dict, None) would raise TypeError on the comparison and fall to the `except Exception` at line 373 (vt) / 363 (carry_fred), which logs "Could not fetch ..." and returns None — i.e. the kill-switch fetch-fail counter increments and after N consecutive cycles the loop kills itself. This is the DESIRED fail-safe but the audit-log message would be misleading.
- inference: Failure mode is named ("equity unavailable") but the actual cause (broker schema mismatch) would not be in the log. Low-severity observability gap; the kill-switch ultimately fires correctly.
- evidence: `vt.py:362-375` `fetch_account_equity` error handling; `carry_fred.py:351-365` same.
- recommended-action-class: add-log
- owning-role: quant-developer

---

**F-011-PR**
- severity: nit
- category: maintainability
- location: `scripts/run_paper_trading_vt.py:215` `handler._ws01_marker = True  # type: ignore[attr-defined]`; `scripts/run_paper_trading_carry_fred.py:228` `handler._ws02_marker = True  # type: ignore[attr-defined]`
- observation: Idempotency guard for the file-handler attachment uses a private attribute on the logging.Handler instance with a type-ignore comment. Standard logging idiom.
- inference: No defect; flagged only to confirm reviewer noticed the type-ignore.
- evidence: `vt.py:215`; `carry_fred.py:228`.
- recommended-action-class: other
- owning-role: quant-developer

---

**F-012-PR**
- severity: observation
- category: other
- location: `scripts/monitor_regime_triggers.py` (full file); `tests/scripts/test_cf_t9_monitor.py` (BC-4 additions)
- observation: The CF-T9 monitor changes (+21 LoC: BC-4 persistent counter, seen_regime_active_true/false flags) and the matching test additions (+37 LoC) are independently sound: the read-modify-write state file is implemented with `state_path.write_text(...)`, the sticky flags and counter increment are tested via two-call sequence, and the file path is parameterizable for testability. No observed defects.
- inference: These changes are clean as a unit. Their commit verdict is blocked only by the Group A bundle verdict (because they live in Group A) and by the upstream F-001 / F-002 / F-008 blockers in sibling files. Suggest splitting if Group A blockers cause delay.
- evidence: `monitor_regime_triggers.py` git diff: +21/-0, BC-4 state plumbing only; `test_cf_t9_monitor.py` BC-4 test passes (validated).
- recommended-action-class: other
- owning-role: quant-developer

---

## Signatures

- pm: @wave4-pm-consensus-draft-2026-05-06 (this document)
- cto: @a245ade8b293bbe94 (cto-architecture-review.yaml)
- quant-developer: @a1501164af9f38199 (qd-implementation-review.yaml)
- cro: @a7da0c4532908fbd6 (cro-risk-review.yaml; dissent recorded at .agent-accountability/dissents/wave9-precommit-review:cro.yaml; does_block: false)
- null-hypothesis-tester: @aca42f117b4f99c4d (nht-adversarial-review.yaml; dissent appended at .agent-accountability/dissents/wave9-precommit-review:nht.yaml; does_block: true; block-threshold)
- principal-reviewer: @aa2ac439d6cb38a6c (principal-reviewer-review.yaml; decision: reject)
