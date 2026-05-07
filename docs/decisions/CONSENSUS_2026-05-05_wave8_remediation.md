# CONSENSUS 2026-05-05: Wave-8 High-Priority Remediation

**Date:** 2026-05-05
**Status:** NEEDS CEO RATIFICATION — auto-ratification BLOCKED by NHT `material_concern` (`does_block: true`) AND Principal Reviewer blocking findings (F-001, F-002, F-003)
**Track ID:** `wave8-high-remediation:phase1:task1.0`
**Produced by:** PM (Product Manager) role, Wave-8 synthesis (Wave-4 of dispatch)
**Wave structure:** PM-first (Wave-1) → 3-role fan-out QD + CRO + NHT parallel (Wave-2) → Principal Reviewer alone (Wave-3) → PM CONSENSUS (Wave-4)

---

## 1. Summary

Wave-8 is a targeted engineering remediation dispatch against two HIGH-severity pre-first-bar items from `ASSESSMENT_2026-05-03.md`: wiring `RealisticCostModel` into both paper-loop equity-write paths (HIGH-1) and adding a startup `account_key` parity assertion (HIGH-2). The dispatch ran two attempts: QD attempt 1 addressed the cost-wiring skeleton and the lock-file mechanism; NHT adversarial review (attempt 1) found five material concerns and one rule violation; QD attempt 2 remediated four of the five material concerns and the rule violation; NHT reverification (attempt 2) confirmed those four closed but surfaced two new blocking findings (USDJPY 150× cost overstatement, cost-feedback into operational equity gap). CRO BC-8 reverification (attempt 2) returned a formal **VETO** on multi-strategy-on-one-account aggregation, confirming that the account-key parity gate does not close BC-8's cross-process race window.

**Recommended disposition:** vt-only single-loop authorization path available if CEO explicitly accepts the documented gaps (Section 9). Carry_fred regime-conditional second-loop authorization remains **BLOCKED** per CRO veto on BC-8 multi-strategy aggregation until Wave-9 residual control lands. This document does NOT start the paper loop. Auto-ratification is blocked; CEO sign-off is required.

---

## 2. Per-Item Terminal-State Table

| Criterion | Status | Owner | Evidence Pointer |
|-----------|--------|-------|-----------------|
| HIGH-1a: RealisticCostModel wired in vt.py equity-write path | verified-wired-and-tested (EURUSD) / partially-closed (USDJPY 150× gap deferred) | QD | `qd-implementation.yaml` Fix 1+2; `vt.py:678-710`; NHT attempt-2 finding-1/finding-2 closed |
| HIGH-1b: RealisticCostModel wired in carry_fred.py equity-write path | verified-wired-and-tested (EURUSD) / partially-closed (USDJPY 150× gap deferred) | QD | `qd-implementation.yaml` Fix 1+2; `carry_fred.py:638-665`; NHT attempt-2 finding-1/finding-2 closed |
| HIGH-1c: end-to-end parity test with concrete numeric assertion | partially-closed — TestE2EParity exists and passes but runs on EURUSD only; USDJPY (spec instrument) lacks end-to-end parity test | QD | `tests/scripts/test_wave8_high_remediation.py::TestE2EParity`; PR F-002; NHT NEW-1 |
| HIGH-2a: startup account_key parity assertion, atomic O_CREAT\|O_EXCL | verified-wired-and-tested | QD | `vt.py:106-157` and `carry_fred.py:121-172` — atomic O_EXCL; fires before any order dispatch |
| HIGH-2b: divergent-key TOCTOU race test + exit-code test + reset-CLI test | verified-wired-and-tested | QD | `TestAtomicLockAndReset`, `TestAccountKeyParity` in test file; 686 passing |
| QUALITY-1: 686 tests pass (≥666); sacred test PASS | verified | QD + PR | `pytest --no-header -q: 686 passed`; PR artifact verification-results |
| QUALITY-2: ruff baseline 19 errors (no regression) | verified | QD + PR | `ruff check src/: 19 errors`; PR independently confirmed |
| QUALITY-3: forbidden-phrases scan clean on all 3 modified files | verified | QD | `qd-implementation.yaml` spec-to-impl-trace QUALITY-3 |

**Deferred / blocked items:**

| Criterion | Status | Reason |
|-----------|--------|--------|
| BC-8 multi-strategy aggregation | BLOCKED — CRO VETO | Cross-process [read→check→dispatch] race; see Section 4 |
| USDJPY unit-convention parity | deferred Wave-9 | 150× cost overstatement; parity test on EURUSD only; see Section 7 |
| Cost feedback into operational equity (dd_contract / kill_switch) | deferred — PM/CRO routing required | Section 10 disagreement; see Section 7 |

---

## 3. NHT Dissent — Append-Only per Rule 6

**This section is append-only and must never be paraphrased, edited, summarized, or erased.** Both dissent texts are reproduced verbatim from the respective NHT artifacts.

### NHT Attempt 1 — Verbatim `dissent-statement` from `nht-adversarial-review.yaml`

> NHT registers MATERIAL_CONCERN (multiple) on Wave-8 closure.
>
> The Wave-8 implementation as written and submitted does NOT satisfy the PM
> HIGH-1 / HIGH-2 acceptance criteria as a strict reading would require, and
> the identified gaps include at least one rule_violation severity item
> (swap accrual is omitted from "backtest-equivalent" cost deduction despite
> being explicitly enumerated in HIGH-1c).
>
> Specific dissent items, append-only and non-amendable:
>
>     HIGH-1 (cost-model parity) gaps:
>       (a) Swap (holding_cost) is never invoked. The paper-loop "backtest-
>           equivalent" equity log records only entry/exit cost on action
>           cycles. For a 60-day USDJPY long-carry hold at 10,000 units the
>           omitted swap is ~$4,800 — material to the very thesis being
>           paper-validated. RULE_VIOLATION on PM HIGH-1c verbatim text
>           ("spread, slippage, commission, AND swap").
>       (b) The cost-deducted value is logged but NOT fed back into the
>           operational equity used for sizing, drawdown contract assessment
>           (DD-1/DD-2/DD-3), kill-switch, or target_units. The paper
>           equity curve in the LOG is backtest-equivalent (modulo (a));
>           the paper TRADING DECISIONS still use raw Saxo equity. The
>           divergence the closure claims to close remains in the control
>           loop. MATERIAL_CONCERN.
>       (c) The QD HIGH-1c test is a syntactic mirror that cannot
>           distinguish a correctly-wired implementation from a
>           superficially-wired one (formula match, not behavior match).
>           MATERIAL_CONCERN.
>       (d) Cost is computed on full target_units rather than on |delta|
>           on rebalance cycles (engine engine.py:331-332 charges on |delta|).
>           CONCERN.
>
>     HIGH-2 (account-key parity gate) gaps:
>       (e) TOCTOU race: Path.exists() + Path.write_text() is not atomic;
>           two simultaneous launches with divergent keys can both pass.
>           The codebase has the atomic write-then-rename pattern in the
>           same file (heartbeat) but assert_account_key_parity does not
>           use it. MATERIAL_CONCERN.
>       (f) Stale-lock semantics: the documented operator recovery path
>           ("delete the file") makes the gate effectively advisory under
>           operational stress. MATERIAL_CONCERN.
>       (g) Account-key parity does NOT close the BC-8 ~15x over-exposure
>           concern in the multi-strategy-on-one-account case. The gate
>           addresses only the multi-account case. MATERIAL_CONCERN.
>           CRO must re-verify whether the original BC-8 closure claim
>           can stand on this gate alone.
>
>   Recommended remediation summary:
>     1. Add swap accrual to the equity log path (HIGH-1c rule violation).
>     2. Either deduct cost from operational equity, or amend the PM
>        HIGH-1 criterion to "log parity only" and document the residual
>        divergence explicitly. (HIGH-1a/b material concern.)
>     3. Replace HIGH-1c syntactic-mirror test with an end-to-end
>        parity-curve test (HIGH-1c material concern).
>     4. Replace lock-file Path.write_text with O_CREAT|O_EXCL atomic
>        acquire (HIGH-2 race material concern).
>     5. Replace "delete the file to reset" with explicit reset CLI flag
>        requiring operator confirmation (HIGH-2 stale-lock material concern).
>     6. CRO re-verifies BC-8 closure under multi-strategy-on-one-account
>        mode; account-key parity alone does not close it.
>
>   Per Rule 6 this dissent is append-only into CONSENSUS_2026-05-05_wave8.md
>   if Wave-8 proceeds to closure. Per protocols/full-auto.md severity is
>   mapped to does_block deterministically; with two RULE_VIOLATION-adjacent
>   items and four MATERIAL_CONCERN items, the orchestrator should treat
>   Wave-8 as does_block until at least items (1), (2)-with-explicit-criterion-
>   amendment-or-fix, (3), and (4) are remediated. Items (5) and (6) can
>   optionally be deferred to Wave-9 with explicit CEO acknowledgment.

---

### NHT Attempt 2 — Verbatim `dissent-statement` from `nht-reverification.yaml` (append-only continuation)

> NHT attempt-2 re-verification: dissent REDUCED from attempt-1 but NOT lifted.
>
>   Closed by QD attempt 2 (no residual): finding 1 (swap accrual), finding 2
>   (|delta| rebalance cost), finding 3 (end-to-end parity test), finding 4
>   (atomic O_EXCL lock).
>
>   Reduced to non-blocking concern: finding 5 (stale-lock — advisory replaced
>   with --reset-account-key-lock + --confirm-account-reset double-flag CLI gate;
>   TTL detection deferred Wave-9; OS-level rm bypass remains but is not what
>   the finding addressed).
>
>   STILL BLOCKING (material_concern, append-only, non-amendable):
>
>     Finding-K (BC-8 multi-strategy aggregation): CRO attempt-2 returns VETO.
>     Account-key parity does NOT close BC-8; cross-process race [read → check
>     → dispatch] permits transient ~24-30% aggregate exposure when both loops
>     target one account. CRO recommends per-strategy budget tickets (7.5%
>     each) or cross-process file-lock as Wave-9 residual control. Until
>     either lands, second-loop authorization remains BLOCKED.
>
>     NEW-1 (USDJPY unit-convention 150× cost overstatement): The end-to-end
>     parity test (Fix 3) runs on EURUSD, not Bet #1's actual pair USDJPY.
>     QD documents a 150× cost overstatement on USDJPY between paper loop
>     and engine and defers fix to Wave-9. The PM HIGH-1 acceptance "cost
>     deducted is bt-equivalent for any trade tuple" is NOT satisfied for
>     USDJPY. Bet #1 paper-launch cost-parity claim is structurally not
>     verified.
>
>     NEW-2 (cost feedback into operational equity): dd_contract,
>     kill_switch, and sizer continue to consume raw broker equity. The
>     "backtest-equivalent" claim holds for the equity LOG only; control-
>     loop decisions diverge by accumulated cost+swap. QD explicitly defers
>     closure to PM/CRO routing.
>
>   Per protocols/full-auto.md: overall_severity material_concern →
>   does_block: true.  Wave-8 cannot auto-ratify.  Escalation to CEO is
>   required.  Acceptable closure paths:
>     (i)  Wave-9 implements per-strategy budget tickets (7.5% each), USDJPY
>          unit-convention fix, and either cost-feedback-into-equity OR a PM
>          amendment to HIGH-1 carving out operational-equity-feedback as
>          log-only.  Then Wave-8 closes via Wave-9 follow-on.
>     (ii) CEO explicitly accepts (a) BC-8 transient overshoot risk by
>          authorizing only ONE paper loop (vt only OR carry_fred only, not
>          both); (b) USDJPY parity gap as documented;
>          (c) operational-equity-feedback gap as documented.  Then Wave-8
>          closes for the single-loop scope only.
>
>   Items 1, 2, 3, 4, 5 are NHT-validated as engineering-closed (or
>   reduced to concern). The blocking surface is now finding-K + NEW-1 +
>   NEW-2.

---

## 4. CRO Veto — BC-8 Closure

**CRO artifact:** `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/cro-bc8-reverify.yaml`
**Decision: VETO**
**`bc8_closure_status`: `not-closed-additional-control-needed`**

### Recommended Residual Control (verbatim from `cro-bc8-reverify.yaml`)

> Cross-process exposure-budget primitive. Two viable shapes:
> (a) Pre-dispatch advisory file-lock (fcntl LOCK_EX, atomic O_CREAT|O_EXCL) around
>     [backend.get_positions → compute_exposure → check_dispatch_allowed → execute_signal].
>     Holds for the duration of one dispatch only; serializes two loops on one account.
> (b) Per-strategy budget tickets summing to BC-8 cap: each loop allocated a static
>     half (7.5%); each loop self-enforces its own budget; portfolio aggregate ≤15%
>     by construction. Simpler, more conservative, no cross-process synchronization.
>     Recommended for Wave-9 if cross-process locking is not implemented immediately.
> Until either is in place: BC-8 closure should NOT be claimed on the basis of
> Wave-8 account-key parity alone, and second-loop authorization (carry_fred regime-
> conditional) should remain BLOCKED.

### CRO Four Forward-Looking Risk Questions and Answers (from `cro-bc8-reverify.yaml` body)

**Q1 — get_positions scope:** Account-level. `/port/v1/netpositions` with ClientKey returns all positions on the account. Each loop, when pointed at the same account, sees the other's settled positions.

**Q2 — exposure_aggregator scope:** Portfolio-wide as wired. `compute_exposure` is a pure aggregator over the passed list; the paper-loop scripts pass the full account-level position list. So in steady state with no race, the 15% cap is enforced portfolio-wide.

**Q3 — Saxo /netpositions docs:** Do not explicitly disambiguate cross-token isolation, but state position visibility is governed by token-account access. Codebase comment plus standard retail semantics support account-level scope.

**Q4 — BC-8 contract framing:** The BC-8 clause requires "at any bar before any new trial dispatches" — strict, not amortized. Transient overshoot during a dispatch race window is a contract violation.

**CRO structural conclusion (verbatim excerpt from body):** "The wired control sequence is read → check → dispatch with no cross-process lock. A loop A dispatch in flight is invisible to loop B on its read. Loop B can pass check_dispatch_allowed on stale aggregate and dispatch its own size, transiently breaching BC-8. The parity gate does nothing to address this — it only ensures both loops are pointed at the same account."

**Knight Capital analog (verbatim from `cro-bc8-reverify.yaml` blowup-analog):** "independently-correct local guards do not enforce portfolio-level invariants under concurrent dispatch."

---

## 5. Principal Reviewer Findings

**PR artifact:** `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/principal-reviewer-review.yaml`
**PR decision: REJECT**

### Blocking Findings

**F-001** | severity: blocking | rubric: execution-firewall-review (Section A)
- File: `scripts/run_paper_trading_vt.py:684-689` (and mirror `carry_fred.py:643-648`)
- Description: The paper-loop cost formula computes `cost_usd = cost_pips * pip_v * target_units` where `target_units` is a USD-nominal quantity from `VolTargetSizer`. For USDJPY the backtest engine converts USD-nominal to engine-units via `_to_engine_units` (divides by price; `engine.py:544-573`), then computes cost on the converted quantity. At USDJPY price 150 with a $100,000 USD-nominal position, the engine deducts ~$5.00; the paper loop deducts ~$750 — a ~150× divergence. This is the opposite of "backtest-equivalent paper equity" stated in HIGH-1a/1b. The swap accrual path at `vt.py:697-702` has the same defect.
- Recommended action class: clarify-spec
- Owning role: PM (spec resolution needed before re-implementation)

**F-002** | severity: blocking | rubric: review-plan (Testing dimension)
- File: `tests/scripts/test_wave8_high_remediation.py:57-118`
- Description: The HIGH-1c spec requires "identical numeric result … on a concrete USDJPY trade tuple." `TestCostModelParity::test_paper_loop_entry_cost_equals_engine_entry_cost` fabricates a shared `SIZE = 10_000.0` input that bypasses `_to_engine_units`, preventing detection of the F-001 unit mismatch. `TestE2EParity` explicitly uses EURUSD (per its own docstring) to avoid the JPY unit-conversion, leaving the spec's `instrument-universe: [USDJPY]` without end-to-end parity coverage.
- Recommended action class: add-test
- Owning role: QD

**F-003** | severity: blocking | rubric: review-plan (Completeness dimension)
- File: `scripts/run_paper_trading_vt.py` + `scripts/run_paper_trading_carry_fred.py`
- Description: `pm-acceptance-criteria.yaml` declares `hard-constraints.production_loc_budget_total: 50`. `git diff --shortstat` returns 330 insertions, 2 deletions — net production LoC delta of 328 lines, 6.6× the hard-constraint ceiling. vt.py grew by 172 insertions; carry_fred.py grew by 158 insertions. The constraint was declared "hard" in the PM artifact, not a soft target.
- Recommended action class: clarify-spec (PM AC was unrealistic for the actual rework scope; see Section 7 for PM's documented deviation acknowledgment)
- Owning role: PM

### Material Findings

**F-004** | severity: material | rubric: log-as-decision-trace (Item 2 + Item 10)
- File: `scripts/run_paper_trading_vt.py:658-711`
- Description: The `_emit_ws01` decision trace does not include `cost_pips`, `cost_usd`, `swap_usd`, or `paper_equity_bt_equiv`. These are written to a separate `EQUITY_LOG_PATH` file with no `decision_ts`, no `cycle_id`, and no `strategy_params`. Reconstructing "why did paper equity diverge from backtest equity at cycle N" requires JOINing two log sinks.
- Recommended action class: add-log

**F-005** | severity: material | rubric: execution-firewall-review (Section A2, silent default)
- File: `scripts/run_paper_trading_vt.py:674` (and `carry_fred.py:634`)
- Description: `_pip_v = 0.01 if "JPY" in pair.upper() else 0.0001` — string-substring heuristic instead of canonical `PairInfo.pip_value` lookup. Silent default pattern; breaks silently for future pairs.
- Recommended action class: tighten-invariant

**F-006** | severity: material | rubric: execution-firewall-review (Section A2, semantic undefined)
- File: `scripts/run_paper_trading_vt.py:710`
- Description: `paper_equity_bt_equiv = equity - _cost_usd + _swap_usd`. Saxo TotalValue (`equity`) already reflects broker-side fill costs. Subtracting separately-computed model cost yields double-counting. The semantic choice of which cost convention achieves "backtest-equivalent" is a research-class judgment that appears in implementation code without spec citation.
- Recommended action class: escalate-to-owning-role (Head of Quant Research)

**F-007** | severity: material | rubric: kill-switch-design (Property 4)
- File: `scripts/run_paper_trading_vt.py:106-157`
- Description: `assert_account_key_parity` satisfies kill-switch Properties 1, 2, 3, 5 but not Property 4 (testable in prod without staging the failure mode). No read-only "verify the gate fires" probe exists; no `.fintech-org/kill-switch-tests.jsonl` entry.
- Recommended action class: add-edge-case-handling

**F-008** | severity: material (note in PR artifact, but classified material here due to log-reconstruction impact)
- File: `scripts/run_paper_trading_vt.py:686-711`
- Description: HOLD-FLAT branch writes the equity log; however, early-return skip branches (KILL_HALTED, SKIP_EQUITY_FETCH_FAIL, SKIP_DD_FULL_HALT, SKIP_DD_HALT_NEW, SKIP_AGGREGATION_GATE) emit ws01 but do NOT write to EQUITY_LOG_PATH. Missing entry is ambiguous: "cycle ran but skipped" vs "process was down."
- Recommended action class: add-log

### Note Findings

**F-009** | severity: note | rubric: review-plan (Risk dimension)
- File: `scripts/run_paper_trading_vt.py:841-842`
- Description: `assert_account_key_parity(backend.account_key)` triggers a Saxo API network call (lazy property). If Saxo is unreachable at startup, the parity gate fails via uncaught exception, not via the logged `logger.critical` path. Different audit trail for the same outcome.

**F-010** | severity: note | rubric: review-plan (Clarity dimension)
- File: `scripts/run_paper_trading_vt.py:441-533`
- Description: `run_cycle` accepts `dd_contract: DrawdownContract | None = None` but no test exercises the `None` branch explicitly. The asymmetry with `carry_fred.py` (which requires non-None) is unmotivated.

---

## 6. What Wave-8 Closed

The following items are engineering-closed per QD attempt 2 + NHT attempt-2 re-verification + PR independent confirmation:

- **HIGH-1a/1b (cost-deduction wired):** `RealisticCostModel` singleton wired into equity-write paths at `vt.py:678-710` and `carry_fred.py:638-665`. Swap accrual (Fix 1) and `|delta|` rebalance cost (Fix 2) both wired and NHT-verified closed (findings 1 and 2).
- **HIGH-1c (end-to-end parity test):** `TestE2EParity::test_entry_cost_parity_engine_vs_paper_loop` exists, drives both engine and paper loop end-to-end, asserts `paper_equity_bt_equiv == 99_992.5` (EURUSD, 5-bar). NHT finding-3 closed; PR notes residual gap (EURUSD only — see Section 7).
- **HIGH-2a (atomic O_CREAT|O_EXCL lock acquire):** Both scripts use `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. NHT finding-4 closed.
- **HIGH-2b (TOCTOU race test, exit-code test, reset-CLI test):** `TestAtomicLockAndReset::test_toctou_concurrent_different_keys_one_exits` (threading.Barrier-synchronized), `test_reset_without_confirm_flag_exits_nonzero` (vt + carry_fred), `TestAccountKeyParity` (6 tests).
- **HIGH-2 reset CLI:** `--reset-account-key-lock NEW_KEY --confirm-account-reset` double-flag gate in both scripts; missing `--confirm-account-reset` exits 1.
- **QUALITY-1:** 686 tests pass (686/686); sacred test `tests/backtest/test_engine.py::test_no_lookahead` confirmed PASSED by PR.
- **QUALITY-2:** `ruff check src/`: 19 errors — unchanged from pre-Wave-8 baseline. No regression.
- **QUALITY-3:** Forbidden-phrases scan: 0 matches on all 3 modified/created files.

---

## 7. Wave-9+ Deferred Scope (Open Gaps)

| Gap | Severity | Origin |
|-----|----------|--------|
| BC-8 multi-strategy-on-one-account aggregation — cross-process [read→check→dispatch] race permits transient ~24-30% exposure; CRO veto; recommended residual: per-strategy 7.5% budget tickets OR cross-process advisory file-lock | HIGH | CRO veto (cro-bc8-reverify.yaml), NHT finding-K, NHT attempt-2 STILL BLOCKING |
| USDJPY unit-convention 150× cost overstatement — paper loop uses USD-nominal directly as `_trade_units`; engine divides by price for JPY pairs (`_to_engine_units`); parity test runs on EURUSD to avoid this gap | HIGH | NHT NEW-1 + PR F-001 (confluent independent finding) |
| Cost-feedback into operational equity — `dd_contract.assess(equity)`, `kill_switch.check_and_trigger(equity)`, and sizer all consume raw broker equity; `paper_equity_bt_equiv` is log-only; CRO recommends log-only as the correct architecture; NHT calls log-only a material_concern — **REQUIRES PM SPEC AMENDMENT OR CEO RULING** before re-dispatch | HIGH | NHT NEW-2 + CRO cost_model_wiring_risk_assessment (design conflict; see Section 10) |
| Stale-lock TTL detection — no freshness check on lock file; 6-month-old lock can block legitimate restart | MEDIUM | NHT finding-5 (reduced to concern, non-blocking) |
| `--self-test` CLI flag for in-prod gate verification (kill-switch Property 4) | MEDIUM | NHT finding-J + PR F-007 |
| SHORT-path swap accrual direction-dispatch — vt.py is long-only by clamp; carry_fred does not currently take SHORT signals; symmetric handling unverified | LOW | NHT finding-C |
| Production LoC budget exceeded 6.6× — PM AC specified `production_loc_budget_total: 50`; actual combined production delta is 330 lines. **PM AC was unrealistic for the scope of the rework required (two scripts, atomic lock pattern, reset CLI, swap accrual, delta rebalance, five NHT findings).** Wave-9 should update the PM AC baseline budget for any follow-on dispatch. | DEVIATION | PR F-003 |

---

## 8. What This Consensus Does NOT Do

- Does **NOT** start the paper loop. `no_paper_loop_start_by_orchestrator: true` remains in force. CEO retains exclusive authority to start the first paper bar.
- Does **NOT** modify ratified consensus documents (`CONSENSUS_2026-05-02_paper_launch_authorization.md`, `CONSENSUS_2026-05-03_preflight_closure.md`, `CONSENSUS_2026-05-03_wave7_closure.md`). Those documents are ratified append-only history.
- Does **NOT** modify any NHT dissent artifact. All NHT dissent artifacts are append-only per Rule 6.
- Does **NOT** auto-ratify. NHT `does_block: true` (overall_severity `material_concern`) plus PR blocking findings F-001, F-002, F-003 jointly block auto-ratification under `protocols/full-auto.md`. Fallback path: CEO sign-off.
- Does **NOT** authorize the second paper loop (carry_fred regime-conditional). Per CRO VETO: blocked until Wave-9 residual BC-8 control lands (per-strategy 7.5% budget tickets OR cross-process advisory file-lock).
- Does **NOT** modify the firm risk contract.
- Does **NOT** register strategies, run backtests, or pre-register trials.
- Does **NOT** resolve the CRO ↔ NHT disagreement on cost-feedback into operational equity (Section 10). That is a CEO decision requiring either a PM spec amendment or a QD dispatch to feed cost-adjusted equity into `dd_contract`.

---

## 9. CEO Ratification Gate (CEO-action required)

Auto-ratification under `--full-auto` is **BLOCKED** per `protocols/full-auto.md`:

- **Row 1:** NHT severity `material_concern` → `does_block: true` (Wave-8 attempt-2 reverification)
- **Row 3:** Principal Reviewer review-report contains 3 blocking findings (F-001, F-002, F-003)

CEO must perform the following actions in sequence to close Wave-8:

**(a)** Acknowledge the NHT attempt-1 dissent verbatim (Section 3, first block).

**(b)** Acknowledge the NHT attempt-2 reduced-but-not-lifted dissent verbatim (Section 3, second block).

**(c)** Acknowledge CRO BC-8 VETO and decide: defer second-loop authorization to Wave-9 with residual control (recommended path: per-strategy 7.5% budget tickets) OR authorize residual control implementation now as part of an expanded Wave-8 scope.

**(d)** Acknowledge PR F-001 (USDJPY 150× cost overstatement; paper loop does not mirror `_to_engine_units` conversion) and decide: dispatch QD on a Wave-9 unit-convention fix and accept that HIGH-1a/1b are log-parity-only for USDJPY until fixed, OR explicitly accept the gap with documented scope limitation.

**(e)** Acknowledge PR F-002 (HIGH-1c test bypasses unit-conversion semantics; runs on EURUSD only, not USDJPY per spec instrument-universe) — same disposition as (d).

**(f)** Acknowledge PR F-003 (LoC budget hard-constraint exceeded 6.6×: 330 lines vs. 50-line budget) and decide: ratify the deviation as PM AC underspecified for actual rework scope, OR re-scope Wave-9 PM AC to a realistic budget.

**(g)** Decide on cost-feedback gap (NHT NEW-2 vs. CRO recommendation): amend HIGH-1 acceptance criterion to specify "log-only parity, operational equity remains broker-reported" (CRO-recommended architecture per `cro-risk-assessment.yaml`) OR dispatch QD to feed cost-adjusted equity into `dd_contract` (NHT-preferred path). These two positions are structurally incompatible; PM cannot resolve without CEO direction.

**(h)** Decide closure scope: (i) single-loop authorization (vt-only, with NHT NEW-1 + NEW-2 + F-003 gap explicitly accepted and documented) OR (ii) full Wave-9 dispatch before any closure (resolves all blocking gaps before first paper bar).

---

## 10. Disagreement Matrix

| Disagreement | CRO Position | NHT Position | Cause | Resolution |
|---|---|---|---|---|
| Cost-feedback into operational equity (HIGH-1 gap) | Log-only is the **correct architecture**: `paper_equity_bt_equiv` is research instrumentation; dd_contract + kill_switch MUST see raw Saxo TotalValue to avoid double-counting costs already embedded in fill prices | Log-only is `material_concern`: control-loop decisions (DD-1/DD-2/DD-3 ladder, kill-switch) diverge from the cost+swap-adjusted equity the CF-T9 Clause C comparison will use | Ambiguous PM HIGH-1 spec text — "backtest-equivalent" does not specify whether it means the equity LOG value or the equity value passed to risk primitives | **Requires PM spec amendment OR CEO ruling.** Round-1 role debate was NOT triggered because the disagreement surfaced via NHT attempt-2 only after Wave-2 had completed. |

All other findings are confluent (PR independently confirmed NHT NEW-1; no other role-vs-role structural disagreement). F-006 (PR) adds a further dimension to the cost-feedback question by noting that Saxo TotalValue already embeds broker-side costs, which would cause double-counting if model costs are subtracted from it — this supports CRO's log-only position and should factor into CEO's decision on (g).

---

## 11. Signatures

| Role | Decision | Artifact Path |
|------|----------|--------------|
| PM | propose-acceptance-criteria → consensus-author | `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/pm-acceptance-criteria.yaml` + this CONSENSUS doc |
| QD | implemented-and-verified (with documented Wave-9 deferrals; attempt 2) | `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/qd-implementation.yaml` |
| CRO | size-reduced (attempt 1) + **veto on BC-8 closure** (attempt 2) | `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/cro-risk-assessment.yaml` + `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/cro-bc8-reverify.yaml` |
| NHT | dissent (attempt 1: rule_violation + material_concern) → dissent-reduced (attempt 2: material_concern still blocking) | `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/nht-adversarial-review.yaml` + `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/nht-reverification.yaml` |
| Principal Reviewer | reject (3 blocking findings F-001, F-002, F-003) | `.fintech-org/artifacts/2026-05-05T-wave8-high-remediation/principal-reviewer-review.yaml` |

**NHT dissent artifacts (append-only, preserved unmodified):**
- `.agent-accountability/dissents/wave8-high-remediation:phase1:task1.0:null-hypothesis-tester.yaml` — produced by PM consensus-authoring wave (schema per `agent-accountability/templates/dissent.md`). Contains verbatim concatenation of NHT attempt-1 and attempt-2 dissent statements.

---

## 12. Auto-Ratification Record

| Field | Value |
|-------|-------|
| NHT overall_severity | `material_concern` |
| NHT does_block | `true` (orchestrator-computed per `protocols/full-auto.md`) |
| PR blocking findings count | 3 (F-001, F-002, F-003) |
| Auto-ratification gate result | **BLOCKED** |
| Blocking signals | NHT does_block: true + PR blocking findings count: 3 |
| Fallback path | CEO sign-off (per `protocols/full-auto.md`) |
| CEO veto authority | Full; CEO may also expand the accepted scope, amend acceptance criteria, or dispatch Wave-9 before closure |

---

*This document was produced by the PM role in Wave-4 of the Wave-8 fan-out. It synthesizes all 7 Wave-8 artifacts without introducing new domain-technical judgments. For domain-technical questions, route to the originating role (QD for implementation, CRO for risk, NHT for structural critique, PR for code review). The cost-feedback architectural question (Section 10) requires PM spec amendment or CEO ruling before re-dispatch.*
