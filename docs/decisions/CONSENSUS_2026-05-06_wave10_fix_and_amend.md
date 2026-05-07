# Consensus on: Wave-10 Fix and Amend (closure of Wave-9 blocking findings)

## Roles staffed

- **pm** — Wave-1 acceptance criteria authoring; Wave-4 synthesis and CONSENSUS drafting; dissent preservation routing; ratification artifact production. Does not make technical decisions; routes technical adjudication to named roles.
- **quant-developer (W2)** — Implementation of all four scope items: F-001 JPY unit-conversion fix, F-002/F-008 test rewrites, BC-8 fcntl file-lock wiring, D-AMEND-LADDER code-comment updates. The only role writing production code in Wave-10. Produced: `qd-implementation-report.yaml`.
- **null-hypothesis-tester (W3)** — Adversarial re-verification of all 7 Wave-10 closure claims using smoking-gun grep and direct file reads (not QD narrative). Produced: `nht-reverification.yaml`. No new dissent emitted; all 7 claims survive.
- **cro (W3)** — BC-8 lock acquisition timing audit (clock-and-ordering rubric); lock placement and concurrent-process test verification; drawdown ladder amendment review; BC-8 veto liftability determination. Produced: `cro-reverification.yaml`. No new dissent emitted; BC-8 veto LIFTABLE.
- **principal-reviewer (W3)** — Independent 8-rubric staff re-review of all modified files. Produced: `principal-reviewer-reverification.yaml`. Decision: approve-with-conditions. Four non-blocking findings (F-100 through F-103) raised; zero blocking findings.

---

## Acceptance criteria (from PM, Wave-1)

Source: `.fintech-org/artifacts/wave10-fix-and-amend/pm-acceptance-criteria.yaml`

**Hard constraints (all must pass):**

- **HC-1 (F-001):** Both paper-loop scripts must apply JPY unit-conversion (`_engine_units = USD-nominal / mid` for JPY pairs) at the sizer-output boundary BEFORE cost-compute lines. Numeric oracle: USDJPY 100k USD-nominal at price ~150 → cost_usd ∈ [4.95, 5.05] USD (not ~750 USD).
- **HC-2 (F-002):** `test_wave8_high_remediation.py` must contain a USDJPY E2E parity test calling `run_backtest` with USDJPY at price ~150 AND driving the paper-loop equity-write path AND asserting engine/paper equity parity within ≤0.1%. No SHARED_SIZE bypass.
- **HC-3 (F-008):** The two rebalance/entry tests in `test_wave8_high_remediation.py` must be rewritten to derive expected cost from engine-units arithmetic (delta/price × cost_pips × pip_v), not from USD-nominal. Oracle: delta=1500 → expected_cost ≈ 0.075 USD (not 11.25); entry=5000 → expected_cost ≈ 0.25 USD (not 37.5).
- **HC-4 (BC-8 option-B):** Both scripts must acquire `fcntl.flock(LOCK_EX | LOCK_NB)` on `data/dispatch_lock.flock` BEFORE `get_positions` and hold through `execute_signal` reconciliation. On LOCK_NB failure: skip with `SKIP_DISPATCH_LOCK_BUSY` logged as structured WS01/WS02 line.
- **HC-5 (BC-8 concurrent test):** `tests/scripts/test_wave10_dispatch_lock.py` must exist and contain a test spawning TWO actual subprocesses (not in-process mocks) and asserting: (a) exactly one acquires the lock, (b) the other emits `SKIP_DISPATCH_LOCK_BUSY`, (c) aggregate JPY-correlated exposure peak ≤15%.
- **HC-6 (ladder amendment doc):** `docs/specs/drawdown_ladder_amendment_2026-05-06.md` must contain all five required sections including verbatim NHT NEW-2 dissent under "preserved-not-resolved" header and CEO ruling citation.
- **HC-7 (commit message):** Git commit message must cite F-003 ratification, Wave-11 binding, and F-001/F-002/F-008/BC-8/NEW-2 closure summary. (Pending — enforced at commit-creation time.)
- **HC-8 (baselines):** Sacred test passes; ruff ≤19 errors; pytest ≥686 + new Wave-10 tests passing.

---

## Decision

Wave-10 closes the 3 Wave-9 blocking code findings (F-001, F-002, F-008) and the BC-8 residual control gap, and produces the Decision-5 drawdown ladder amendment. Independent re-verification by NHT (smoking-gun grep), CRO (BC-8 lock placement and concurrent test execution), and PR (8-rubric staff review) all confirm the closures are GENUINE this time: the Wave-9 failure mode (code unchanged while closure claimed) does NOT recur. The QD-reported "forbidden-phrases scan clean" claim is technically inaccurate — "fidelity" at `docs/specs/drawdown_ladder_amendment_2026-05-06.md:92` is a false positive (dictionary sense "faithfulness," not the Fidelity Investments broker) but requires a 1-word substitution before commit to satisfy the scanner. All groups are cleared for commit once that substitution lands: **Group A (vt.py, carry_fred.py, monitor, test_cf_t9_monitor) — COMMIT-AS-IS** (F-001 verified closed at cost ≈5.0 USD vs prior buggy 750 USD for USDJPY 100k at price 150; BC-8 lock correctly placed before `get_positions`; sacred test passes; ruff = 19; pytest = 700); **Group B (test_wave8_high_remediation.py, test_wave10_dispatch_lock.py) — COMMIT-AS-IS** (F-002 USDJPY E2E parity test exists with no SHARED_SIZE bypass; F-008 tests derive expected from arithmetic; 11 dispatch-lock tests pass); **Groups C/D/E — COMMIT-AS-IS** (unchanged from Wave-9 ratification). The BC-8 second-loop authorization veto is **LIFTABLE** — CEO can authorize concurrent vt and carry_fred against the same paper account. Kill-switch live-promotion blockers (Properties 2/3/4) persist unchanged from Wave-9 and are explicitly out of Wave-10 scope. Four non-blocking findings (F-100 through F-103) are routed to Wave-11.

**CEO actions required to ratify Wave-10:**
1. **Ratify this CONSENSUS** (authorizes Group A + B commit once `fidelity` fix lands).
2. **Authorize the `fidelity` substitution** — recommended: replace `"fidelity"` with `"accuracy"` at `docs/specs/drawdown_ladder_amendment_2026-05-06.md:92` (1-word change, minimal scope, no charter touch). Alternative: extend `forbidden-phrases.json` with a quote-context exemption, but this requires a separate CEO ratification of the charter-touch.
3. **Decide BC-8 second-loop authorization** — CRO confirms veto LIFTABLE. Do you authorize concurrent vt + carry_fred against the same paper account, or keep single-loop only?
4. **Authorize Wave-11 routing** of F-100/F-101/F-102/F-103 (and the existing Wave-11 binding for shared-module refactor per `wave9-substeps:phase2:task2.0.yaml` Decision 4).
5. **Authorize commit dispatch** (with the HC-7 commit-message gate enforced at commit-creation per the three required citations).

---

## Evidence supporting the decision

- **W1 — PM acceptance criteria:** `.fintech-org/artifacts/wave10-fix-and-amend/pm-acceptance-criteria.yaml` — 8 HC gates, QD success gate, review-wave success gate, out-of-scope list, Wave-11 binding ticket.
- **W2 — QD implementation report:** `.fintech-org/artifacts/wave10-fix-and-amend/qd-implementation-report.yaml` — All 8 HC verdicts (HC-1 through HC-8; HC-7 PENDING at commit time); numeric closure oracle (5.000 USD ∈ [4.95, 5.05]); 700 tests passing; forbidden-phrase scan noting "fidelity" false positive.
- **W3 — NHT re-verification:** `.fintech-org/artifacts/wave10-fix-and-amend/nht-reverification.yaml` — 7 claims tested by smoking-gun grep; all survive; aggregate verdict COMMIT-AFTER-MINOR-FIX (the "fidelity" scan discrepancy). W10-7 notes QD's "scan clean" claim is technically false; discrepancy is a false positive.
- **W3 — CRO re-verification:** `.fintech-org/artifacts/wave10-fix-and-amend/cro-reverification.yaml` — BC-8 lock acquisition timing audit (both scripts); ordering invariants PASS (acquire line < get_positions line in both scripts); concurrent-process test 11/11 PASS; ladder amendment all 5 sections PASS; BC-8 veto LIFTABLE determination.
- **W3 — Principal Reviewer re-verification:** `.fintech-org/artifacts/wave10-fix-and-amend/principal-reviewer-reverification.yaml` — HC-1 through HC-6 and HC-8 PASS on independent re-derivation; HC-5 PASS-WITH-OBSERVATION (F-102); HC-7 N/A (no commit yet); 4 non-blocking findings (F-100, F-101, F-102, F-103); 5 Wave-9 blocking findings confirmed closed; reviewer self-check passes all 6 anti-patterns.
- **Wave-9 parent CONSENSUS:** `docs/decisions/CONSENSUS_2026-05-06_wave9_precommit_review.md` — originating DO-NOT-COMMIT verdicts and 6 CEO action list for Wave-10 scope.
- **Wave-9 CEO sub-decisions:** `.agent-accountability/ratifications/wave9-substeps:phase2:task2.0.yaml` — Decisions 2/4/5 (combined-fix, LoC-cap ratification, amend-ladder) that scoped Wave-10.

---

## Decisions NOT made (deferred, out of scope)

- Paper-loop launch authorization (separate CEO decision after Wave-10 closure and BC-8 second-loop decision).
- Saxo token rotation (manual user action; orchestrator cannot perform).
- Kill-switch Properties 2/3/4 remediation for live promotion (persists from Wave-9; out of Wave-10 scope).
- Wave-11 shared-module refactor execution (binding ticket at `pm-acceptance-criteria.yaml#wave11-binding`; blocked on Wave-10 closure; not in Wave-10 scope).
- F-006 equity-log shared-path race (major, non-blocking per Wave-9 PR verdict; deferred Wave-11 or standalone fix).
- F-007 carry_fred regime-inactive decision-trace gap (major, non-blocking; deferred).
- F-009 JPY pip heuristic vs PairInfo lookup (minor; deferred Wave-11).
- F-010 equity-fetch schema-mismatch log clarity (minor; deferred).
- Groups C/D/E commit authorization (authorized under `wave9-substeps:phase2:task2.0.yaml` Decision 3; not re-decided in Wave-10).
- Any modification to `kill_switch.check_and_trigger()` input semantics (CEO Decision 5 settled — raw broker equity remains the input).
- `forbidden-phrases.json` charter-touch for "fidelity" quote-context exemption (requires separate CEO ratification if the CEO prefers that path over the 1-word substitution).
- Re-adjudication of any NHT dissent already recorded as append-only in prior CONSENSUS docs.
- Trial counter increments (Wave-10 is code-fix and review dispatch, not a research trial).

---

## Apparent role disagreement

NONE for Wave-10. All three W3 reviewers (NHT, CRO, PR) converge on closure with non-blocking notes. The sole discrepancy is QD's "forbidden-phrases scan clean" claim vs NHT's W10-7 and CRO's POLICY_VIOLATION_FALSE_POSITIVE finding on the "fidelity" match — both reviewers agree it is a false positive in semantic terms and recommend a pre-commit fix (1-word substitution) rather than a blocking veto. CRO assigns size_multiplier=0.95 (5% scope reserve) and classifies it as a Wave-11 cleanup item with a commit-shippable pre-fix option. NHT characterizes it as a "minor discrepancy" that does not block commit. This is convergent, not divergent: all three reviewers independently agree on the same resolution path.

Wave-9's true role disagreement (CRO "commit-as-is" from a risk-architecture lens vs CTO/QD/NHT/PR do-not-commit from a code-correctness lens) does NOT recur in Wave-10 because the code-correctness defects are genuinely remediated.

---

## Assumptions we're betting on

- The uncommitted diff (verified by NHT and CRO via direct file:line reads) matches the source code in the working directory at the time of W3 review. No staging-area discrepancy.
- `engine.py:_to_engine_units` (at `engine.py:544-573`) remains the canonical unit-conversion path defining "backtest-equivalent cost" for JPY pairs. Wave-10 code changes did not touch `engine.py`.
- `fcntl.flock` advisory locking on macOS local filesystem is the deployment target. flock semantics are well-defined on macOS local FS; NFS/SMB portability is a known limitation surfaced as F-101 (deferred Wave-11).
- The W3 NHT smoking-gun grep results are representative of the current working-tree state (NHT executed `pytest`, `ruff`, and forbidden-phrase scan directly and reported actual outputs, not estimates).
- The "fidelity" match at `docs/specs/drawdown_ladder_amendment_2026-05-06.md:92` is a dictionary-sense English word ("faithfulness") inside verbatim CEO ruling text, not a reference to the Fidelity Investments brokerage. CRO classification: false positive.
- The BC-8 second-loop authorization is a CEO decision (not PM authority); this CONSENSUS records it as liftable and presents the decision for CEO. CRO's technical determination is input, not the output.
- `test_wave10_dispatch_lock.py`'s inline `_WORKER_SCRIPT` (lines 38-67) correctly exercises the `fcntl.flock` primitive cross-process even though it does not invoke the full `run_cycle` path (acknowledged by all three W3 reviewers as a coverage spirit-gap, compensated by HC-4 file:line audit; deferred to Wave-11 as F-102).

---

## Pre-registered falsification

N/A — Wave-10 is a code-fix and review dispatch, not a strategy or model proposal. No pre-registered falsification conditions apply. Stated explicitly to satisfy the CONSENSUS structure requirement.

---

## Dissent (preserved verbatim)

### Wave-9 CRO dissent

**STATUS: BC-8 SECTION RESOLVED BY WAVE-10; KILL-SWITCH SECTIONS PERSIST AS LIVE-PROMOTION BLOCKERS.**

Source: `.agent-accountability/dissents/wave9-precommit-review:cro.yaml`, field `dissent_text`. Severity: `strong_objection`. `does_block: false`. Per agent-accountability rule: this dissent is append-only across waves; reproduced verbatim below.

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

---

### Wave-9 Null-Hypothesis Tester dissent

**STATUS: ADDRESSED-BY-WAVE-10.** Items (1) F-001, (2) F-002, (4) BC-8, and (5) Group-B test adequacy have been remediated by Wave-10 code and verified by NHT W3 smoking-gun re-verification. Item (3) NEW-2 is addressed by the Decision-5 ladder amendment (CEO Decision 5 from `wave9-substeps:phase2:task2.0.yaml`). NHT did NOT emit a new Wave-10 dissent — all 7 Wave-10 closure claims survive adversarial verification. Per agent-accountability rule: this dissent is append-only; reproduced verbatim below and must travel with all downstream artifacts.

Source: `.agent-accountability/dissents/wave9-precommit-review:nht.yaml`, field `dissent_text`. Severity: `block-threshold`. `does_block: true`. **THIS FLAG IS PRESERVED FROM WAVE-9: NHT does_block = true on the Wave-9 pre-commit review unit. Wave-10 addresses the blocking conditions; the historical record is immutable.**

> NHT DISSENT — Wave-9 pre-commit review (verbatim, append-only, must be
> preserved in CONSENSUS.md if Wave-9 attempts closure):
>
> Four of the five substantive Wave-8 remediation claims FAIL adversarial
> re-verification at the code-inspection level (no execution required):
>
> (1) F-001 (USDJPY cost-formula fix) is FALSE. _to_engine_units is not
>     called anywhere in either run_paper_trading_carry_fred.py or
>     run_paper_trading_vt.py. The cost-deduction lines (vt.py:689,
>     carry_fred.py:648) compute _cost_pips * _pip_v * _trade_units where
>     _trade_units is the raw USD-nominal output of
>     VolTargetSizer.calculate_size — NOT the engine-converted units. For
>     USDJPY at price ~150, the paper-loop cost is therefore ~150x larger
>     than the engine cost. The 150x overstatement bug from
>     CONSENSUS_2026-05-05 Finding-J PERSISTS unchanged.
>
> (2) F-002 (E2E parity test) is THEATRE. TestCostModelParity asserts
>     equality between two hand-rolled formulas that share the same input
>     self.SIZE=10_000 and apply mathematically identical multiplications
>     — by construction they can never disagree. TestE2EParity is the
>     only run_backtest-exercising test and it explicitly chooses EURUSD
>     over USDJPY in lines 339-342 to AVOID the conversion that F-001
>     was supposed to fix. The test that would have caught F-001 — engine
>     USDJPY equity_curve == paper-loop USDJPY paper_equity_bt_equiv at
>     the entry bar — does not exist.
>
> (3) NEW-2 (cost-feedback architecture). The code implements log-only:
>     drawdown_contract.assess() and kill_switch.check_and_trigger() both
>     consume raw broker TotalValue (carry_fred:455+481+473;
>     vt:466+498+484); the cost-adjusted paper_equity_bt_equiv is written
>     to disk but never read back into either contract. CRO's position
>     is that log-only is correct. NHT's prior material_concern (Wave-8)
>     — that operational equity must include cost-feedback for the
>     contract's threshold semantics to match the pre-registered
>     drawdown ladder — is unaddressed by code and unaddressed by any PM
>     spec amendment in the changeset. The material_concern PERSISTS.
>
> (4) BC-8 (cross-process race) is structurally UNCLOSED. Neither
>     file-lock (fcntl/flock/LOCK_EX) nor per-strategy 7.5% budget
>     tickets are implemented anywhere in the changeset. The
>     TestAtomicLockAndReset suite tests the ACCOUNT-KEY parity lock,
>     not the BC-8 dispatch race. CRO's BC-8 veto in
>     CONSENSUS_2026-05-05 Section 4 explicitly named these two
>     acceptable residual controls; neither has landed. Multi-strategy
>     paper authorization remains contraindicated until either residual
>     control is wired and tested under a concurrent-process test (two
>     simultaneous run_cycle calls reading stale exposure must NOT both
>     pass check_dispatch_allowed).
>
> (5) Group-B test adequacy is INADEQUATE.
>     test_rebalance_cost_charged_on_delta_not_full_target asserts
>     cost == 0.75 * 0.01 * 1500 = 11.25 USD on a USDJPY rebalance,
>     which is the BUGGY formula's output. If F-001 were truly fixed
>     (engine-units used), this test would compute cost on engine-units
>     = 1500/150 = 10 units and assert ~0.075 USD — failing the
>     existing assertion. The test ENSHRINES the bug it was supposed to
>     detect. This is the canonical anti-pattern: a regression test that
>     locks in the wrong behavior because it was written against the
>     broken implementation, not against an independent oracle.
>
> Recommended Wave-9 closure path (NOT in scope of this dissent,
> surfaced for CEO/PM):
>   - Apply _to_engine_units conversion at the paper-loop sizer-output
>     boundary so target_units sent to backend.execute_signal are in
>     engine-units for JPY pairs. Update the equity-write cost formula
>     to use the same engine-units.
>   - Replace TestCostModelParity SHARED_SIZE assertions with a true
>     E2E test that calls run_backtest on USDJPY with
>     rebalance_mode="continuous" and compares its equity_curve.iloc[1]
>     to a paper-loop run_cycle's paper_equity_bt_equiv at the same
>     entry event.
>   - Either implement fcntl advisory file-lock around the
>     [get_positions -> check_dispatch_allowed -> execute_signal]
>     sequence in both loops (lock acquired BEFORE get_positions and
>     held through execute_signal — a lock acquired after position-read
>     still permits the race), OR wire per-strategy budget tickets at
>     7.5% each in check_dispatch_allowed config.
>   - Either land cost-adjusted equity feedback into
>     dd_contract/kill_switch, OR produce a PM spec amendment that
>     explicitly downgrades operational equity to broker TotalValue and
>     accepts the resulting threshold drift.
>   - Fix test_rebalance_cost_charged_on_delta_not_full_target to assert
>     against the engine's USDJPY cost (engine-units), not the
>     paper-loop's USD-nominal cost.
>
> Until items (1)-(4) are remediated by code and item (5) is remediated
> by test, NHT does NOT co-sign Wave-9 closure of F-001, F-002, NEW-2,
> or BC-8.

**Wave-10 NHT new dissent: NONE.** NHT did not emit a new dissent for Wave-10. All 7 claims survive adversarial re-verification (see `nht-reverification.yaml`). W10-7 surfaces a minor inaccuracy in QD's "scan clean" claim (false positive on "fidelity") — characterized as a recommended pre-commit fix, not a blocking dissent.

---

## Independent review findings (Principal Reviewer)

Source: `.fintech-org/artifacts/wave10-fix-and-amend/principal-reviewer-reverification.yaml`, field `findings`. Decision: `approve-with-conditions`. Per consensus.md rule 2: findings are append-only; PM has not paraphrased, softened, reordered, or omitted any entry. All findings reproduced verbatim including PASS confirmations.

---

**F-001-PR-W10**
- severity: closed
- category: correctness
- location: `scripts/run_paper_trading_vt.py:737-739`; `scripts/run_paper_trading_carry_fred.py:699-701`; Wave-9 PR finding F-001-PR (cost formula 150x overstatement for JPY pairs).
- observation: Wave-9 finding: paper-loop charged cost_pips * pip_v * USD_nominal for JPY pairs, where engine charges cost_pips * pip_value * engine_units (delta in _to_engine_units convention). Result: paper-loop charged 750 USD vs engine's 5 USD for 100k USDJPY at price 150 (150x).
- inference: Wave-10 fix at vt.py:738 and carry_fred.py:700 inserts the JPY conversion: `_engine_units = (_trade_units_nom / mid) if ("JPY" in pair.upper() and mid > 0) else _trade_units_nom`; `_cost_usd = _cost_pips * _pip_v * _engine_units`. Numeric oracle (HC-1) verified: 100_000/150 = 666.667; 0.75 * 0.01 * 666.667 = 5.000 ∈ [4.95, 5.05]. Pre-fix would have produced 750 USD. CLOSED.
- evidence: vt.py:738 inline conversion at sizer-output boundary BEFORE cost-compute; carry_fred.py:700 mirror conversion; engine.py:299 _to_engine_units called by engine; engine.py:331 cost on engine-units delta; test_usdjpy_entry_cost_oracle PASS confirms numeric oracle.
- recommended-action-class: closed-no-action
- owning-role: quant-developer

---

**F-002-PR-W10**
- severity: closed
- category: test-coverage-gap
- location: `tests/scripts/test_wave8_high_remediation.py:669-844` (TestUSDJPYE2EParity); Wave-9 PR finding F-002-PR (USDJPY E2E parity test absent).
- observation: Wave-9 finding: the existing TestE2EParity used EURUSD explicitly to avoid the JPY conversion path. No USDJPY E2E parity test existed. The cost-formula bug (F-001) was therefore untestable end-to-end against the engine reference.
- inference: Wave-10 adds TestUSDJPYE2EParity class with 3 tests including test_entry_cost_parity_engine_vs_paper_loop_usdjpy that calls run_backtest with USDJPY at price 150 (line 779-786) AND drives vt_mod.run_cycle with the same trade tuple (line 818-823) AND asserts equity parity within 0.1% of capital (line 832). No SHARED_SIZE bypass — engine constructs real VolTargetSizer; the F-001 conversion path is exercised on the paper-loop side independently. CLOSED.
- evidence: test_wave8_high_remediation.py:779-786 (engine call); test_wave8_high_remediation.py:818-823 (paper-loop call); test_wave8_high_remediation.py:832 (parity assertion); pytest run confirms PASS.
- recommended-action-class: closed-no-action
- owning-role: quant-developer

---

**F-008-PR-W10**
- severity: closed
- category: test-coverage-gap
- location: `tests/scripts/test_wave8_high_remediation.py:527-661`; Wave-9 PR finding F-008-PR (rewritten tests assert pre-F-001 buggy values).
- observation: Wave-9 finding: tests at lines 540-562 and 564-611 (Wave-9 numbering) asserted cost_usd ≈ 11.25 USD (delta=1500) and ≈ 37.5 USD (entry=5000) for USDJPY at price 150. These match the F-001-buggy formula (USD-nominal * pip_v * cost_pips) not the engine-parity formula.
- inference: Wave-10 rewrite derives expected from explicit engine-units arithmetic shown in-test: 0.75 * 0.01 * (1500/150) = 0.075 USD; 0.75 * 0.01 * (5000/150) ≈ 0.25 USD. Tests also assert cost_usd != pre-F-001 wrong values (11.25 / 37.5 USD). Swap test similarly rewritten to expect ~0.267 USD, not the buggy 40 USD. All values derived in-test from arithmetic, not hardcoded. CLOSED.
- evidence: test_wave8_high_remediation.py:573-577 (in-test arithmetic for delta case); test_wave8_high_remediation.py:648-651 (in-test arithmetic for full-entry case); test_wave8_high_remediation.py:583-584 (assert NOT 11.25); test_wave8_high_remediation.py:657-658 (assert NOT 37.5).
- recommended-action-class: closed-no-action
- owning-role: quant-developer

---

**F-004-PR-W10**
- severity: closed
- category: invariant-violation
- location: `scripts/run_paper_trading_vt.py:548-869`; `scripts/run_paper_trading_carry_fred.py:529-818`; Wave-9 PR finding F-004-PR (no cross-process per-cycle file lock).
- observation: Wave-9 finding: aggregation gate single-loop; two simultaneous loops can both pass check_dispatch_allowed and double JPY exposure to ~30%.
- inference: Wave-10 adds fcntl.LOCK_EX|LOCK_NB advisory file-lock acquired BEFORE get_positions (vt.py:553 < 588; carry_fred.py:534 < 565), held through execute_signal + reconciliation, released in finally on all exit paths. Lock file shared at data/dispatch_lock.flock. Subprocess test confirms mutual exclusion (test_exactly_one_acquires_not_both PASS). CLOSED.
- evidence: vt.py:550 os.open with O_CREAT|O_WRONLY; vt.py:553 fcntl.flock(LOCK_EX|LOCK_NB); vt.py:856-869 finally block (release + close); carry_fred.py:531/534/805-818 mirror pattern; test_wave10_dispatch_lock.py concurrent tests PASS.
- recommended-action-class: closed-no-action
- owning-role: quant-developer + cro

---

**F-005-PR-W10**
- severity: closed
- category: spec-drift
- location: `docs/specs/drawdown_ladder_amendment_2026-05-06.md`; Wave-9 PR finding F-005-PR (no PM amendment for log-only architecture).
- observation: Wave-9 finding: code feeds raw broker equity to risk primitives without a PM-authored spec amendment confirming this position. NHT NEW-2 dissent orphaned without explicit documentation.
- inference: Wave-10 adds 142-line PM-authored amendment covering all 5 required sections including verbatim NHT NEW-2 dissent, CEO Decision 5 ruling verbatim, and code-comment updates citing the spec at vt.py:99-105 + carry_fred.py:115-121. NHT dissent preserved-not-resolved per spec requirement. CLOSED.
- evidence: docs/specs/drawdown_ladder_amendment_2026-05-06.md (lines 10-31, 34-46, 50-75, 79-105, 109-132); vt.py:99-105 cite block; carry_fred.py:115-121 cite block.
- recommended-action-class: closed-no-action
- owning-role: pm + ceo

---

**F-100-PR-W10**
- severity: minor
- category: edge-case
- location: `scripts/run_paper_trading_vt.py:738`; `scripts/run_paper_trading_carry_fred.py:700`
- observation: The F-001 fix uses a guarded division: `(_trade_units_nom / mid) if ("JPY" in pair.upper() and mid > 0) else _trade_units_nom`. For JPY pairs, if mid is exactly 0 (or numerically <= 0 from arithmetic), the fallback silently returns USD-nominal — re-introducing the F-001-buggy behavior WITHOUT raising or logging an error.
- inference: Reachability: mid is computed at vt.py:641 / carry_fred.py:622 as (bid+ask)/2 with fallback to ohlcv["close"].iloc[-1]. For mid to be <=0, either both bid/ask are 0/negative AND the close is <=0 (data corruption), OR an exception in client.get_info_price plus close<=0. Practically rare on USDJPY (price ~150) but the silent fallback is a latent footgun: a future regression in data-fetch could silently revert F-001 for that cycle.
- evidence: vt.py:641 mid fallback to close; vt.py:738 silent fallback to USD-nominal when mid<=0; no structured log emitted in the mid<=0 branch.
- recommended-action-class: defensive-hardening
- owning-role: quant-developer
- severity-justification: NOT a Wave-9 finding; introduced by F-001 fix structure. Non-blocking because no realistic path exercises mid<=0 for USDJPY (price ~150 in live + tests). Routes naturally to Wave-11 shared-module refactor where the conversion can be centralized with explicit error handling.

---

**F-101-PR-W10**
- severity: minor
- category: failure-mode-handling
- location: `scripts/run_paper_trading_vt.py:550-578`; `scripts/run_paper_trading_carry_fred.py:531-560`
- observation: The lock-acquire try/except at vt.py:552-578 catches ONLY BlockingIOError. If fcntl.flock raises any other OSError (e.g., ENOLCK on overloaded kernel, EBADF on invalid fd, EINVAL on FS that doesn't support flock), the exception propagates out of the outer try (no finally) — leaking _dl_fd. The inner critical-section try/finally (vt.py:581/856) is never entered.
- inference: Per Rubric 7 (failure mode reasoning): the failure is named in code via the BlockingIOError catch but the alternative OSError class is unhandled. On macOS/Linux local FS this is rare; on NFS or SMB mounts flock semantics are non-portable. fd leak per cycle on a long-running loop could exhaust file descriptors over weeks. The behavior on filesystem flock-not-supported is ambiguous and untested. The PM HC-4 spec does not require handling all OSError subclasses, but Rubric-7 surfacing is required.
- evidence: vt.py:552-578 only catches BlockingIOError; no outer finally to close _dl_fd if flock raises non-BlockingIOError; Rubric 7 specifically flags "failure named and handled? Is there a retry policy?"
- recommended-action-class: defensive-hardening
- owning-role: quant-developer
- severity-justification: Non-blocking because (a) macOS local FS is the deployment target and flock works natively, (b) no Wave-9 finding flagged this, (c) the run_cycle exception would propagate to the loop driver which would catch it via top-level error handling. But the fd leak is real if it happens. Defer to Wave-11 shared-module refactor which can add blanket OSError handling.

---

**F-102-PR-W10**
- severity: minor
- category: test-design
- location: `tests/scripts/test_wave10_dispatch_lock.py:38-67` (inline worker); `tests/scripts/test_wave10_dispatch_lock.py:196-230` (test_no_double_dispatch_jpy_exposure)
- observation: The TestDispatchLockConcurrentProcesses tests spawn subprocess.Popen but execute an INLINE _WORKER_SCRIPT that re-implements the fcntl.flock pattern directly. They do NOT invoke vt_mod.run_cycle or cf_mod.run_cycle under contention. Per Rubric 6 test-inversion: "Does the BC-8 concurrent test assert exposure ≤15% across BOTH subprocesses, or only the one that acquired the lock?" Answer: exposure is SIMULATED (line 226: simulated_jpy_pct = dispatched * 0.10), not measured from actual paper-loop execution. The test validates the lock primitive but not the lock-in-context.
- inference: An implementation regression where the lock is moved AFTER get_positions in the paper loop (re-introducing the race window) would NOT fail this test, because the test doesn't run get_positions. The HC-4 lock-before-get_positions invariant is verified only by static review (Rubric 1 file:line) — not by automated test. PM HC-5 fail-condition reads "test uses in-process mocks instead of actual subprocesses" — actual subprocesses ARE used, so the spec letter is met. But the spec spirit ("spawns TWO simultaneous subprocess run_cycle calls" per pm-acceptance-criteria.yaml:99-108) implies the worker should call run_cycle.
- evidence: test_wave10_dispatch_lock.py:38-67 inline worker re-implements lock; test_wave10_dispatch_lock.py:226 simulated_jpy_pct (not measured); PM HC-5 spec language "subprocess run_cycle calls" suggests run_cycle invocation.
- recommended-action-class: test-strengthening
- owning-role: quant-developer
- severity-justification: Non-blocking because (a) Rubric 1 confirms lock IS before get_positions via direct file:line audit, (b) the inline worker exactly mirrors the paper-loop's lock pattern (open + flock_ex_nb + finally release), (c) a real-run_cycle subprocess test would require live or mocked Saxo backend setup that's outside Wave-10 scope. Recommend Wave-11 add run_cycle-invoking subprocess test once the shared-module refactor makes the lock primitive importable.

---

**F-103-PR-W10**
- severity: observation
- category: doc-amendment
- location: `docs/specs/drawdown_ladder_amendment_2026-05-06.md:46`; `docs/specs/drawdown_ladder_amendment_2026-05-06.md:141` (Amendment History)
- observation: Section 2 line 46 states: "The CRO's determination must be appended to this document before Wave-10 commit." The Amendment History at line 141 shows "PENDING | CRO" entry. The PM HC-6 fail-condition does not include the CRO appendment as required content (only the 5 sections).
- inference: The PM AC and the doc text disagree on the gating semantics: PM AC says structural skeleton is sufficient; doc text says CRO append is required pre-commit. Rubric 5 (invariant search): if "ladder values must be validated by CRO before commit" is a hard invariant, then the CRO pending entry is a violation. If it's not a hard invariant (PM AC perspective), then it's documentation flagging future work. Per task brief, role is to enforce HC-6 strictly; HC-6 fail-condition doesn't list this. Routing to CRO for closure scoping.
- evidence: amendment doc line 46 "must be appended before Wave-10 commit"; PM HC-6 fail-condition omits this from the 5 required elements; amendment history line 141 "PENDING | CRO".
- recommended-action-class: clarify-gating-semantics
- owning-role: pm + cro
- severity-justification: Observation only, not blocking. PM AC is the binding spec; HC-6 letter is satisfied. The doc-internal contradiction should be resolved by PM either appending the CRO determination or relaxing the doc-internal gate language to match HC-6.

---

## Signatures

- pm: @wave10-w4-pm-consensus-draft (this document)
- quant-developer: @wave10-w2-qd (qd-implementation-report.yaml)
- null-hypothesis-tester: @wave10-w3-nht (nht-reverification.yaml; no new dissent emitted)
- cro: @wave10-w3-cro (cro-reverification.yaml; BC-8 veto LIFTABLE; no new dissent emitted)
- principal-reviewer: @wave10-w3-pr (principal-reviewer-reverification.yaml; decision: approve-with-conditions; 4 non-blocking findings F-100 through F-103)
