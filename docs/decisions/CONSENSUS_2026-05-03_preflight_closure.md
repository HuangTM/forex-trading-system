# CONSENSUS 2026-05-03: Wave-6 Operational Pre-Flight Closure

**Date:** 2026-05-03
**Status:** NEEDS CEO RATIFICATION — blocked by NHT material_concern (does_block: true)
**Track ID:** wave6-preflight-closure:phase1:task1.0
**Produced by:** PM (Product Manager) role, Wave-6 fan-out synthesis

---

## 1. Summary

Wave-6 operational pre-flight closure is **incomplete**. Of the 10 Section-10 preflight items identified in `CONSENSUS_2026-05-02_paper_launch_authorization.md`, **6 are verified-wired-and-tested** by the Wave-6 fan-out (items 1, 3, 4, 5, 6, 7). **2 items are BLOCKED-engineering** and require a small-fix Wave-7 dispatch before they can close: item 2 (CF-T9 cold-start gate non-functional due to producer/consumer schema mismatch — NHT material_concern, does_block: true) and item 8 (equity-curve write to `data/paper_trading_session.log` is absent from the Python process; no RotatingFileHandler configured). **2 items are BLOCKED-CEO-action** and cannot be closed by engineering: item 9 (60-trading-day calendar reminder — requires a known paper-launch date) and item 10 (launch communication — CEO-authored disclosure). This document does NOT authorize starting the paper loop. It does NOT modify `CONSENSUS_2026-05-02`. It does NOT close items 2 or 8.

---

## 2. Per-Item Terminal-State Table

| Item | Description | Status | Owner | Evidence Pointer |
|------|-------------|--------|-------|-----------------|
| 1 | CF-T9 monitor (`scripts/monitor_regime_triggers.py`) running on cron; `data/cf_t9_status.json` updated within last 5 minutes | verified-wired-as-code (cron deferred to CEO) | QD + Ops | `qd-implementation-closure.yaml` item-1-status; `ops-engineer-verification.yaml` item-1-terminal-state |
| 2 | CF-T9 cold-start gate: ≥10 regime-flag readings logged, both TRUE and FALSE states observed at least once (BC-4) | **BLOCKED-engineering** (NHT material_concern, does_block: true) | QD (fix) + NHT (re-verify) | `nht-cold-start-gate-adversarial.yaml` dissent-statement, severity: material_concern |
| 3 | heartbeat_watchdog (300s timeout) starts cleanly in main(); on_timeout callback verified in tests | verified-wired-and-tested | QD + CTO | `qd-implementation-closure.yaml` item-3-status; `cto-architecture-review.yaml` decision-on-item-3 |
| 4 | exposure_aggregator.check_dispatch_allowed pre-trade gate active; JPY-correlated cap 15% enforced (BC-8) | verified-wired-and-tested | CRO + QD | `cro-bc-wiring-verification.yaml` BC-8: wired; `qd-implementation-closure.yaml` item-4-status |
| 5 | Bet #1 size_multiplier source verified to reach the actual trade-sizing code path (Gap C closure) | verified-wired-and-tested | QD + CRO | `qd-implementation-closure.yaml` item-5-status; `cro-bc-wiring-verification.yaml` BC-1/BC-2: wired |
| 6 | auto_retire_on_trigger.py running on cron; reads `data/cf_t9_status.json`; kill-switch wired end-to-end | verified-wired-as-code (cron deferred to CEO) | QD + Ops + CTO | `qd-implementation-closure.yaml` item-6-status; `cto-architecture-review.yaml` decision-on-item-6; `ops-engineer-verification.yaml` item-6-terminal-state |
| 7 | Drawdown contract triggers active: 10% halt-new / 15% reduce / 20% full halt (Gap B closure) | verified-wired-and-tested | QD | `qd-implementation-closure.yaml` item-7-status |
| 8 | Equity curve write enabled; `data/paper_trading_session.log` file rolling | **BLOCKED-engineering** (needs-implementation) | QD (fix) + Ops (flag) | `qd-implementation-closure.yaml` item-8-status: needs-implementation; `ops-engineer-verification.yaml` item-8-terminal-state: flag-for-ceo |
| 9 | CF-T9 Clause C 60-trading-day deadline logged; calendar reminder set (NHT binding condition 2) | BLOCKED-CEO-action (requires known paper-launch date) | CEO | `pm-acceptance-criteria.yaml` item 9; `ops-engineer-verification.yaml` item-9-terminal-state: verified-documented |
| 10 | Launch communication drafted; includes explicit statement that CF-T9 is A+B binding with Clause C pending | BLOCKED-CEO-action (CEO-authored disclosure) | CEO | `pm-acceptance-criteria.yaml` item 10 |

---

## 3. NHT Material Concern — Append-Only per Rule 6

**This section is append-only and must never be paraphrased, edited, summarized, or erased.** The following is the verbatim `dissent-statement` field from artifact `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/nht-cold-start-gate-adversarial.yaml`.

---

> The CF-T9 cold-start gate (BC-4) is half-implemented. The CONSUMER
> (src/forex_system/risk/bet1_sizing.py:101-232) correctly checks
> n_readings >= 10 AND both_states_observed. There is no bypass via
> env-var, config flag, or test mode in the consumer. The adversarial
> case "10 same-state readings silently pass" is correctly blocked by
> the consumer logic — IF the four required keys are present in
> data/cf_t9_status.json.
>
> However, the PRODUCER (scripts/monitor_regime_triggers.py) does NOT
> write the four keys the consumer reads. The producer writes
> monitor_id / triggered / clause_a / clause_b / data_freshness — but
> NOT regime_active, n_readings, seen_regime_active_true,
> seen_regime_active_false. The consumer therefore always reads the
> defaults (0, False, False) and BC-4 always trips at "n_readings < 10".
> The system fails safe (no trades dispatched), so this is not a
> capital-loss bypass — but it IS a structural failure: the cold-start
> gate as currently wired CANNOT be satisfied by shipping production
> code. The gate is not evaluating "have we observed both regime states
> ≥10 times"; it is evaluating "does the operator know to bypass the
> gate by hand-writing a JSON stub between cron ticks".
>
> Furthermore, NO module in src/ or scripts/ implements a regime-reading
> COUNTER. The increment-on-each-observation logic that BC-4 requires
> has no programmatic home. n_readings is conceptually undefined in the
> shipping codebase — neither incremented nor decremented nor reset.
> Consequently:
>
>   (1) The gate as written is unsatisfiable end-to-end through normal
>       cron operation — so paper-loop dispatch is permanently blocked,
>       which is the safe failure mode but also masks the absence of any
>       real cold-start tracking.
>   (2) A motivated operator who hand-writes a stub satisfies the gate
>       WITHOUT the stub reflecting any true observed regime history.
>       The adversarial scenario in the subtask spec ("all-TRUE 10
>       times") is not the threat — the actual threat is "operator
>       hand-fabricates 10 readings that never happened, the consumer
>       accepts the fabrication, and the next cron tick wipes the
>       evidence by overwriting the file".
>   (3) data/cf_t9_status.json does NOT EXIST on disk as of today
>       (verified via ls). The PM acceptance criterion that "the file is
>       updated within last 5 minutes" cannot be met until the producer
>       is run AND the producer is amended to emit the four BC-4 keys.
>
> Minimum fix (≤30 LoC, NOT to be written by NHT — route to QD):
>   - Amend evaluate_cf_t9() in monitor_regime_triggers.py to maintain
>     a persistent reading-counter (e.g., separate state file
>     data/cf_t9_state.json that is read-modify-write per invocation).
>   - On each invocation, increment n_readings; set
>     seen_regime_active_true=True if (clause_a_pass AND clause_b_pass)
>     this tick; set seen_regime_active_false=True if NOT (clause_a_pass
>     AND clause_b_pass) this tick. Persist counter and state-flags
>     across invocations.
>   - Emit regime_active = (clause_a_pass AND clause_b_pass) into the
>     output payload alongside the existing triggered envelope.
>   - Add a sacred test in tests/scripts/test_cf_t9_monitor.py that
>     runs the monitor twice and asserts n_readings increments
>     monotonically and seen_state flags are sticky.
>
> Until this is fixed, BC-4 is FORMALLY UNSATISFIABLE and any
> operator-mediated bypass to satisfy it is ungoverned. The cold-start
> gate provides no meaningful adversarial protection in its current
> wiring.

**NHT artifact metadata:**
- Severity: `material_concern`
- does_block: `true` (orchestrator-computed — severity material_concern is a deterministic blocking threshold per `protocols/full-auto.md`)
- Artifact path: `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/nht-cold-start-gate-adversarial.yaml`
- Dissent artifact path: `.agent-accountability/dissents/wave6-preflight-closure:phase1:task1.0:null-hypothesis-tester.yaml`

---

## 4. QD Needs-Implementation Finding — Item 8

**Source:** `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/qd-implementation-closure.yaml`, `item-8-status: needs-implementation`

**QD findings:**

- Finding A: `grep for "paper_trading_session.log" in scripts/run_paper_trading_vt.py: NO MATCH`. `grep for "paper_trading_session.log" in scripts/run_paper_trading_carry_fred.py: NO MATCH`. The only write path is an external shell `tee -a` (`.claude/settings.local.json:64` allowlist entry), meaning the file is populated by piping script stdout through `tee` at the CLI level, not by the Python process itself.

- Finding B: Both scripts use `logging.FileHandler` (plain), NOT `RotatingFileHandler`: `run_paper_trading_vt.py:107 — handler = logging.FileHandler(path)` and `run_paper_trading_carry_fred.py:121 — handler = logging.FileHandler(path)`. Targets are `data/ws01_trace.log` (vt) and `data/ws02_trace.log` (carry_fred). No `RotatingFileHandler` found anywhere in `scripts/` or `src/`.

**QD fix proposal (verbatim from artifact body, item 8):**

> FIX PROPOSAL for Item 8 (EXCEPTION: small wiring fix, ≤20 lines, ≤2 files,
> consistent with existing _attach_ws0N_file_handler pattern):
>
> In both scripts, replace logging.FileHandler with RotatingFileHandler and
> add a parallel equity-curve write. Specifically:
>
>   File 1: scripts/run_paper_trading_vt.py
>   - Line 107: replace
>       handler = logging.FileHandler(path)
>     with:
>       from logging.handlers import RotatingFileHandler
>       handler = RotatingFileHandler(path, maxBytes=10*1024*1024, backupCount=5)
>   - Add a new constant (alongside WS01_TRACE_PATH):
>       EQUITY_LOG_PATH = "data/paper_trading_session.log"
>   - In _emit_ws01() or the main loop, after computing equity each cycle,
>     append one JSON line to EQUITY_LOG_PATH via a RotatingFileHandler or
>     direct append using the existing structured-log pattern.
>
>   File 2: scripts/run_paper_trading_carry_fred.py
>   - Same substitution at line 121.
>   - Same EQUITY_LOG_PATH constant pointing to data/paper_trading_session.log.
>
> This ≤20-line fix closes item 8. It does NOT change any research decision,
> does NOT introduce new abstractions, and is consistent with the established
> _attach_ws0N pattern. Flagged per Wave-6 instructions.

---

## 5. Ops Engineer Flag-for-CEO — Item 8 Stale Log

**Source:** `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/ops-engineer-verification.yaml`, `item-8-terminal-state: flag-for-ceo`

**Ops Engineer verbatim flag (from `flags-for-ceo` field):**

> data/paper_trading_session.log exists from Apr 26 (6 days ago) with 122 lines. When first paper bar executes, equity-curve write will append to stale log. Recommend CEO either (a) truncate file before first bar, (b) verify logging code clears/rotates file on startup, or (c) accept the merged log (less clean but operationally safe if rotating handler prevents unbounded growth).

**Ops observed state:**
- File: `data/paper_trading_session.log`
- mtime: `2026-04-26T15:04:07Z` (6 days old as of 2026-05-03)
- Line count: 122 lines
- Interpretation: stale artifact from a prior development session, not a fresh run

**CEO must decide before first paper bar execution.** This decision is independent of whether Wave-7 completes the RotatingFileHandler fix — the stale file exists regardless. The three dispositions are: (a) truncate to 0 lines immediately before first paper bar; (b) verify that the logging code creates a fresh file on startup (not confirmed by any role's inspection); or (c) accept the merged log knowing the first 122 lines predate the paper launch.

---

## 6. CRO Two Forward-Looking Assumptions

**Source:** `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cro-bc-wiring-verification.yaml`, `assumptions` field

These are flagged as Wave-7 prerequisites and operational pre-flight items, **not Wave-6 blockers**. They are informational for the CEO and do not require Wave-7 action to resolve — they require operational awareness before first paper bar.

**Assumption 1 — _JPY_CORRELATED frozenset universe asymmetry:**
The `_JPY_CORRELATED` frozenset at `src/forex_system/risk/exposure_aggregator.py:46` contains only `{USDJPY, GBPUSD}`. The Wave-6 instrument universe listed in PM acceptance criteria includes EURJPY, GBPJPY, AUDJPY, NZDJPY — these are direct JPY pairs and would FAIL to register as JPY-correlated under the current `is_jpy_correlated()` implementation. For the paper-launch as currently authorized (vol_target_carry on USDJPY single-pair + carry_fred on USDJPY), the 15% JPY-correlated cap is correctly enforced. However, if any cross-JPY pair is added to the live paper book, the JPY cap will be silently ineffective. CRO flags this as a Wave-7 prerequisite, not a Wave-6 blocker.

**Assumption 2 — Cross-strategy aggregation requires same Saxo paper account:**
Both `run_paper_trading_vt.py` (vol_target_carry) and `run_paper_trading_carry_fred.py` (Bet #1 carry_fred) trade USDJPY exclusively per current configs. Concurrent paper books aggregate via `get_positions()` only if positions persist in the same Saxo paper account. If the operator runs the two loops in separate Saxo paper accounts, the JPY-correlated aggregation across strategies cannot see cross-account positions, and the BC-8 15% cap would be computed per-strategy rather than portfolio-wide. This is an operational pre-flight item requiring the operator to confirm a single shared paper account before first bar.

---

## 7. CTO Future-Hardening Note

**Source:** `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cto-architecture-review.yaml`, `failure-modes-considered` field, Failure Mode 1

**Non-blocking for paper launch.** The CTO notes that the `_observer_loop` daemon thread in `src/forex_system/risk/heartbeat_watchdog.py` is not wrapped in a top-level exception handler. The observer loop catches exceptions from the `on_timeout` callback (lines 196-199) but if the `_observer_loop` itself raises an unhandled exception before a timeout fires, the dead-man switch is silently dead and the paper loop continues without the watchdog active. This is not introduced by commit `ded1356` and is outside the scope of this architecture review. CTO categorizes it as an architecture-level observation for future hardening, non-blocking for paper launch at the current risk envelope.

---

## 8. What This Consensus Does NOT Do

- Does NOT authorize starting the paper loop. The hard constraint `no-paper-loop-start-by-orchestrator: true` remains in force.
- Does NOT modify or amend `CONSENSUS_2026-05-02_paper_launch_authorization.md`. That document is ratified and unmodified.
- Does NOT close item 2 (cold-start gate). Item 2 remains BLOCKED-engineering until QD implements the producer-side schema fix and NHT re-verifies.
- Does NOT close item 8 (equity-curve write / log rolling). Item 8 remains BLOCKED-engineering until QD implements the RotatingFileHandler fix.
- Does NOT close items 9 or 10. Those remain BLOCKED-CEO-action.
- Does NOT re-adjudicate any NHT dissent items from `CONSENSUS_2026-05-02` Sections 3 and 4.
- Does NOT ratify CF-T9 Clause C (deferred; 60-trading-day window post-launch).
- Does NOT perform any new backtest, sweep, strategy registration, or trial pre-registration.

---

## 9. Recommended Next Action

**Wave-7 dispatch is the recommended path.** Wave-7 scope is bounded at ≤30 LoC (item 2) + ≤20 LoC (item 8).

### Wave-7 task A — Close item 2: producer schema fix (≤30 LoC)

Route to QD. Amend `scripts/monitor_regime_triggers.py` `evaluate_cf_t9()` function to:
1. Maintain a persistent reading-counter in a separate state file (e.g., `data/cf_t9_state.json`) that is read-modify-write per invocation.
2. On each invocation, increment `n_readings`; set `seen_regime_active_true=True` if `(clause_a_pass AND clause_b_pass)` this tick; set `seen_regime_active_false=True` if NOT `(clause_a_pass AND clause_b_pass)` this tick. Persist counter and state-flags across invocations.
3. Emit `regime_active = (clause_a_pass AND clause_b_pass)` into the output payload of `data/cf_t9_status.json` alongside the existing `triggered` envelope.
4. Add a test in `tests/scripts/test_cf_t9_monitor.py` that runs the monitor twice and asserts `n_readings` increments monotonically and `seen_state` flags are sticky.

### Wave-7 task B — Close item 8: equity-curve write + RotatingFileHandler (≤20 LoC)

Route to QD. Implement the fix proposal verbatim from `qd-implementation-closure.yaml` item 8 body section (reproduced in Section 4 above): replace `logging.FileHandler` with `RotatingFileHandler` at `scripts/run_paper_trading_vt.py:107` and `scripts/run_paper_trading_carry_fred.py:121`; add `EQUITY_LOG_PATH` constant and equity-write call in both scripts.

### Wave-7 task C — Re-NHT-verify item 2 after the fix

NHT must re-verify that the producer schema now emits the four BC-4 keys (`regime_active`, `n_readings`, `seen_regime_active_true`, `seen_regime_active_false`) and that no ungoverned bypass path exists. NHT's re-verification closes the dissent.

### Wave-7 scope constraint

Wave-7 is a small-fix dispatch only. It does NOT open new strategies, run new backtests, modify CONSENSUS_2026-05-02, or expand instrument universe. Trial discipline does not apply.

### After Wave-7 completes

CEO issues final pre-flight gate ratification covering items 2 and 8 (newly closed) plus acknowledgment of items 9 and 10 (CEO-action items). That ratification, together with this document and CONSENSUS_2026-05-02, constitutes the complete paper-launch authorization chain.

---

## 10. Disagreement Matrix

There are no role-vs-role disagreements in this Wave-6 fan-out.

The NHT material_concern is a substantive technical finding, not a disagreement with other roles. CRO confirmed BC-4 as "wired" (`cro-bc-wiring-verification.yaml` BC-4: wired) based on reading the consumer-side gate logic at `src/forex_system/risk/bet1_sizing.py:197-222`, which is structurally correct. CTO did not test the producer-side schema. QD confirmed the consumer gate logic is present. None of CRO, CTO, or QD tested the producer-side schema explicitly against the consumer's key expectations.

NHT's adversarial scope — specifically directed at whether the gate can be satisfied with monoculture readings — led NHT to read both the consumer AND the producer schema. The producer/consumer mismatch is a finding CRO/CTO/QD would independently confirm given the same investigation scope. It is not a disagreement; it is a gap in what was tested by each role.

---

## 11. Signatures

Each role's artifact constitutes their sign-off for the items within their scope.

| Role | Decision | Artifact Path |
|------|----------|--------------|
| PM (Product Manager) | propose-acceptance-criteria | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/pm-acceptance-criteria.yaml` |
| CTO (Chief Technology Officer) | approve (items 3, 6) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cto-architecture-review.yaml` |
| CRO (Chief Risk Officer) | approve (BC-1 through BC-8; artifact_type: veto, no veto raised) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cro-bc-wiring-verification.yaml` |
| QD (Quant Developer) | needs-revision (items 1/3/4/5/6/7 verified; item 8 needs-implementation) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/qd-implementation-closure.yaml` |
| Ops Engineer | flag-for-ceo (items 1/6/9 clean; item 8 stale log) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/ops-engineer-verification.yaml` |
| NHT (Null-Hypothesis Tester) | dissent — material_concern, does_block: true (item 2) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/nht-cold-start-gate-adversarial.yaml` |

PM consensus draft artifact: `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/pm-consensus-draft.yaml`
NHT dissent artifact (append-only): `.agent-accountability/dissents/wave6-preflight-closure:phase1:task1.0:null-hypothesis-tester.yaml`

---

## 12. CEO Ratification Gate

Under `--full-auto`, auto-ratification is BLOCKED. NHT `does_block: true` at severity `material_concern` is a deterministic blocking threshold per `protocols/full-auto.md`. The orchestrator-computed outcome is `blocked_pending_gap` — falls back to the CEO sign-off path.

**CEO must perform the following actions in sequence before paper launch can proceed:**

### a. Acknowledge NHT material concern (item 2) verbatim

CEO must acknowledge the NHT dissent-statement reproduced verbatim in Section 3 of this document. Acknowledgment means: "I have read the verbatim dissent. I understand that BC-4 (CF-T9 cold-start gate) is formally unsatisfiable through shipping production code due to a producer/consumer schema mismatch in `scripts/monitor_regime_triggers.py`."

### b. Acknowledge QD needs-implementation finding (item 8) and authorize Wave-7

CEO must acknowledge that item 8 (equity-curve write to `data/paper_trading_session.log`, RotatingFileHandler) is not implemented in the Python process — the current write path is an external shell `tee -a` that silently fails without the pipe. CEO must decide: authorize Wave-7 to close items 2 + 8, or explicitly accept the gaps (see option B below, strongly not recommended).

### c. Acknowledge Ops flag (stale log) and choose disposition

CEO must choose one of three dispositions for `data/paper_trading_session.log` (122 lines, mtime 2026-04-26T15:04:07Z, 6 days old):
- **(a)** Truncate the file to 0 lines immediately before the first paper bar.
- **(b)** Verify that the logging code creates a fresh file on startup (no role has confirmed this behavior; Wave-7 fix, if authorized, should clarify).
- **(c)** Accept the merged log, understanding the first 122 lines predate the paper launch.

### d. Acknowledge CRO two forward-looking assumptions (informational; no Wave-6 action required)

CEO must acknowledge the two CRO pre-flight items documented in Section 6: (1) `_JPY_CORRELATED` frozenset only contains `{USDJPY, GBPUSD}` — cross-JPY pairs silently bypass the cap if added; (2) cross-strategy aggregation requires both paper loops running in the same Saxo paper account. No engineering action is required in Wave-7 for these items; they are operational pre-flight reminders.

### e. Acknowledge that items 9 and 10 remain BLOCKED-CEO-action

- Item 9 (60-trading-day calendar reminder): Cannot be set until paper loop start date (T=0) is known. CEO must set the calendar reminder on the day of first paper bar.
- Item 10 (launch communication): CEO must draft or approve the communication before starting the paper loop. Required verbatim disclosure clause (from `pm-acceptance-criteria.yaml` item 10): *"CF-T9 is binding on Clauses A and B. Clause C is accepted as a known-incomplete deferral and is pending ratification within 60 trading days of paper launch."*

### f. Choose one of two paths

**Option A (strongly recommended by all 5 roles):** Authorize Wave-7 to close items 2 and 8. After Wave-7 completes and NHT re-verifies item 2, CEO issues a final pre-flight gate ratification that, together with this document and `CONSENSUS_2026-05-02`, constitutes the complete paper-launch authorization chain.

**Option B (strongly NOT recommended by all 5 roles):** Explicitly accept the gaps — start the paper loop knowing that item 2 (BC-4 cold-start gate) is structurally non-functional and item 8 has no equity-curve persistence from the Python process. Consequences: BC-4 cannot be satisfied without operator-mediated JSON stub fabrication that is overwritten each cron tick and leaves no governed audit trail; equity-curve state is not persisted per-cycle, limiting post-session analysis. All 5 roles advise against Option B. If CEO chooses Option B, the explicit acceptance must be recorded in a ratification artifact before the paper loop is started.

---

*This document was produced by the PM role in the Wave-6 fan-out. It synthesizes the 5 role artifacts listed in Section 11 and does not introduce new domain-technical judgments. For domain-technical questions, route back to the originating role.*
