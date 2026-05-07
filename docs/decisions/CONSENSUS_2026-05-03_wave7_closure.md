# CONSENSUS 2026-05-03: Wave-7 Preflight Fix Closure

**Date:** 2026-05-03
**Status:** AUTO-RATIFIED — NHT severity `none`, does_block `false`; pre-flight checklist 8/10 engineering-closed
**Track ID:** wave7-preflight-closure:phase1:task1.0
**Produced by:** PM (Product Manager) role, Wave-7 fan-out synthesis
**Auto-ratification authority:** `--full-auto` per `fintech-org/protocols/full-auto.md`; user preference `feedback_full_auto_no_prompts.md`

---

## 1. Summary

Wave-7 preflight fix is **COMPLETE**. Items 2 and 8, which were BLOCKED-engineering in the Wave-6 closure (`CONSENSUS_2026-05-03_preflight_closure.md`), are now **verified-wired-and-tested** following QD's implementation and NHT's independent re-verification. The NHT material_concern dissent (severity `material_concern`, does_block `true`) that blocked Wave-6 auto-ratification has been **LIFTED** by NHT — the original BC-4 producer/consumer schema mismatch in `scripts/monitor_regime_triggers.py` is fully resolved. Items 9 and 10 remain **BLOCKED-CEO-action** and are unchanged from Wave-6 (item 9 requires a known paper-launch date; item 10 is a CEO-authored disclosure). The pre-flight checklist stands at **8/10 engineering-closed** (items 1, 2, 3, 4, 5, 6, 7, 8) with 2/10 blocked-CEO-action (items 9, 10). This document does NOT start the paper loop. CEO retains full authority to veto this auto-ratification post-hoc.

---

## 2. Per-Item Terminal-State Table

| Item | Description | Status | Owner | Evidence Pointer |
|------|-------------|--------|-------|-----------------|
| 1 | CF-T9 monitor (`scripts/monitor_regime_triggers.py`) running on cron; `data/cf_t9_status.json` updated within last 5 minutes | verified-wired-as-code (cron deferred to CEO) | QD + Ops | `qd-implementation-closure.yaml` item-1-status; `ops-engineer-verification.yaml` item-1-terminal-state (Wave-6 artifacts) |
| 2 | CF-T9 cold-start gate: ≥10 regime-flag readings logged, both TRUE and FALSE states observed at least once (BC-4) | **verified-wired-and-tested-after-wave7-fix** | QD (fix) + NHT (re-verify) | `qd-implementation.yaml` task-A-status: verified-wired-and-tested; `nht-reverification.yaml` decision: dissent-lifted |
| 3 | heartbeat_watchdog (300s timeout) starts cleanly in main(); on_timeout callback verified in tests | verified-wired-and-tested | QD + CTO | `qd-implementation-closure.yaml` item-3-status; `cto-architecture-review.yaml` decision-on-item-3 (Wave-6 artifacts) |
| 4 | exposure_aggregator.check_dispatch_allowed pre-trade gate active; JPY-correlated cap 15% enforced (BC-8) | verified-wired-and-tested | CRO + QD | `cro-bc-wiring-verification.yaml` BC-8: wired; `qd-implementation-closure.yaml` item-4-status (Wave-6 artifacts) |
| 5 | Bet #1 size_multiplier source verified to reach the actual trade-sizing code path (Gap C closure) | verified-wired-and-tested | QD + CRO | `qd-implementation-closure.yaml` item-5-status; `cro-bc-wiring-verification.yaml` BC-1/BC-2: wired (Wave-6 artifacts) |
| 6 | auto_retire_on_trigger.py running on cron; reads `data/cf_t9_status.json`; kill-switch wired end-to-end | verified-wired-as-code (cron deferred to CEO) | QD + Ops + CTO | `qd-implementation-closure.yaml` item-6-status; `cto-architecture-review.yaml` decision-on-item-6; `ops-engineer-verification.yaml` item-6-terminal-state (Wave-6 artifacts) |
| 7 | Drawdown contract triggers active: 10% halt-new / 15% reduce / 20% full halt (Gap B closure) | verified-wired-and-tested | QD | `qd-implementation-closure.yaml` item-7-status (Wave-6 artifact) |
| 8 | Equity curve write enabled; `data/paper_trading_session.log` file rolling | **verified-wired-and-tested-after-wave7-fix** | QD | `qd-implementation.yaml` task-B-status: verified-wired-and-tested |
| 9 | CF-T9 Clause C 60-trading-day deadline logged; calendar reminder set (NHT binding condition 2) | BLOCKED-CEO-action (requires known paper-launch date) | CEO | `pm-acceptance-criteria.yaml` item 9 |
| 10 | Launch communication drafted; includes explicit statement that CF-T9 is A+B binding with Clause C pending | BLOCKED-CEO-action (CEO-authored disclosure) | CEO | `pm-acceptance-criteria.yaml` item 10 |

---

## 3. NHT Re-Verification — Append-Only Summary

**This section is append-only and must never be paraphrased, edited, summarized, or erased.** The following is the verbatim `body` field from artifact `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/nht-reverification.yaml`.

---

> All four BC-4 keys (regime_active, n_readings, seen_regime_active_true, seen_regime_active_false)
> are present in the return dict of evaluate_cf_t9() at lines 291-297 of monitor_regime_triggers.py.
> The state file implements a full read-modify-write cycle: on each invocation, n_readings increments
> unconditionally, seen_regime_active_true is set True and never cleared when regime_active is True,
> and seen_regime_active_false is set True and never cleared when regime_active is False. The state
> defaults to {n_readings: 0, seen_seen_regime_active_true: False, seen_regime_active_false: False}
> on first run or on state-file corruption/deletion.
>
> Adversarial question answers:
> A. Persistence (file deleted): YES, counter resets to 0. Lines 266-268 show the default state
>    is used when state_path does not exist or is unreadable. This is expected behavior; it means
>    a deleted state file restarts the cold-start gate from zero, which is the safe direction
>    (fail-closed, not fail-open).
> B. Monotonicity (n_readings going DOWN): NO. Line 269 is an unconditional increment on the in-
>    memory state loaded from file; there is no decrement path in the code.
> C. Stickiness (seen_state reset to false): NO code path in the producer resets seen_regime_active_true
>    or seen_regime_active_false to False once set. The only way to lose stickiness is file deletion
>    (answered in A above), which restarts the gate from scratch — fail-closed.
> D. Concurrent-write: two overlapping cron ticks would cause a last-write-wins race. Both ticks
>    read the same state, both increment from the same n_readings, and the later write_text call
>    overwrites the earlier. The result is n_readings increments by 1 instead of 2 — a missed
>    count. This is a known class of race for file-based state; it does not cause
>    seen_state to flip back to False, so it is an undercounting issue rather than a safety hazard.
>    The cold-start gate (n_readings >= 10) makes an occasional missed count benign.
> E. Schema/type-validation in consumer: YES in practice, NO formally. bet1_sizing.py:184-187 uses
>    payload.get() with safe defaults and bool()/int() coercion — not a schema validator. Missing
>    keys default to False/0 (fail-safe). There is no jsonschema or Pydantic validation.
> F. Original adversarial "10 same-state readings": STILL REJECTED. The consumer at bet1_sizing.py:
>    213-222 checks both_states = seen_true AND seen_false. Ten readings all with regime_active=True
>    would set seen_regime_active_true=True but seen_regime_active_false would remain False.
>    both_states would be False and the cold-start gate would block. This is correctly handled.
>
> Summary: the original dissent (BC-4 keys absent from producer output) is fully resolved. The
> producer now emits all four keys and persists state across invocations. The consumer at
> bet1_sizing.py:101-232 reads exactly these keys and the gate logic is correct. No new material
> concerns were found during this re-verification.

---

**NHT verbatim attestation (from `nht-reverification.yaml` decision field):**

> "Item 2 dissent resolved. BC-4 is now satisfiable through normal cron operation. Severity: none."

Original Wave-6 dissent (severity `material_concern`, does_block: `true`) is **LIFTED**. New findings are non-blocking (file-lock absence: future-hardening; consumer fail-safe on corrupt JSON: informational).

**NHT re-verification artifact metadata:**
- decision: `dissent-lifted`
- does_block: `false`
- gate-implementation-status: `implemented-and-correct`
- original-dissent-resolved: `true`
- Artifact path: `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/nht-reverification.yaml`
- Original dissent artifact (Wave-6, append-only): `.agent-accountability/dissents/wave6-preflight-closure:phase1:task1.0:null-hypothesis-tester.yaml`

---

## 4. NHT 2 New Findings — Preserved Verbatim (Non-Blocking)

These findings are preserved verbatim from `nht-reverification.yaml` `new-findings` field. They do **NOT** block paper launch. They are recorded here so they survive into git history.

### Finding 1 — File-Lock Absence (Category: future-hardening)

**Verbatim from `nht-reverification.yaml` new-findings[0]:**

> {finding: "No file-lock on state write (write_text is not atomic on all filesystems); concurrent cron ticks can lose one increment per race", category: future-hardening}

**NHT context (from `body` field, adversarial question D):**

> Concurrent-write: two overlapping cron ticks would cause a last-write-wins race. Both ticks
> read the same state, both increment from the same n_readings, and the later write_text call
> overwrites the earlier. The result is n_readings increments by 1 instead of 2 — a missed
> count. This is a known class of race for file-based state; it does not cause
> seen_state to flip back to False, so it is an undercounting issue rather than a safety hazard.
> The cold-start gate (n_readings >= 10) makes an occasional missed count benign.

**Disposition:** future-hardening. An optional file-lock (e.g., `fcntl.flock` or `filelock` library) on `data/cf_t9_state.json` would eliminate the undercounting race entirely. This is a Wave-8+ hardening item. Does NOT block paper launch.

### Finding 2 — Consumer Fail-Safe on Corrupt JSON (Category: informational)

**Verbatim from `nht-reverification.yaml` new-findings[1]:**

> {finding: "Consumer uses payload.get() with defaults rather than schema validation; a corrupt or truncated status file that still parses as valid JSON with wrong types would silently use defaults (False/0) rather than raising — this is fail-safe but not fail-loud", category: informational}

**NHT context (from `body` field, adversarial question E):**

> Schema/type-validation in consumer: YES in practice, NO formally. bet1_sizing.py:184-187 uses
> payload.get() with safe defaults and bool()/int() coercion — not a schema validator. Missing
> keys default to False/0 (fail-safe). There is no jsonschema or Pydantic validation.

**Disposition:** informational. The fail-safe direction (defaults to False/0 → cold-start gate blocks → no trade dispatch) is the correct safety posture. Fail-loud schema validation (e.g., Pydantic model or jsonschema) would improve observability without changing the safety outcome. This is a Wave-8+ observability item. Does NOT block paper launch.

---

## 5. QD Wave-7 Implementation Summary

**Source:** `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/qd-implementation.yaml`

**Verbatim diff stats and pytest summary from QD artifact:**

```
git diff --stat:
  scripts/monitor_regime_triggers.py  +21 (net)
  scripts/run_paper_trading_vt.py     +7  (net)
  scripts/run_paper_trading_carry_fred.py  +8 (net)
  tests/scripts/test_cf_t9_monitor.py +37 (supplementary; counts separately per PM AC)

Total production LoC added: 36 across 3 files (21+7+8) — within ≤50 budget
Test file LoC: 37 (supplementary)
Total files changed: 3 production files

pytest --no-header -q: 666 passed in 16.71s
pytest tests/scripts/test_cf_t9_monitor.py -v: 14 passed in 0.13s (0 failed, exit 0)
pytest tests/backtest/test_engine.py -k test_no_lookahead -v: PASSED
```

**Task A — Item 2 (producer schema fix):**

- `scripts/monitor_regime_triggers.py:75` — `CF_T9_STATE_PATH = Path('data/cf_t9_state.json')` constant added
- `scripts/monitor_regime_triggers.py:247` — `evaluate_cf_t9()` signature: `state_path: Path = CF_T9_STATE_PATH` parameter added
- `scripts/monitor_regime_triggers.py:263-275` — BC-4 read-modify-write block: reads state file at invocation start, increments `n_readings`, sets sticky `seen-state` flags, writes back
- `scripts/monitor_regime_triggers.py:291-297` — four BC-4 keys emitted: `regime_active`, `n_readings`, `seen_regime_active_true`, `seen_regime_active_false`
- `tests/scripts/test_cf_t9_monitor.py:226-261` — `TestBC4PersistentCounter::test_bc4_counter_and_sticky_flags`: two invocations, asserts `n_readings` 1→2 (monotonic), `seen_regime_active_true` sticky across regime change, all four keys present

**Task B — Item 8 (RotatingFileHandler + equity-write):**

- `scripts/run_paper_trading_vt.py:25` — `from logging.handlers import RotatingFileHandler`
- `scripts/run_paper_trading_vt.py:64` — `EQUITY_LOG_PATH = 'data/paper_trading_session.log'`
- `scripts/run_paper_trading_vt.py:109` (was 107) — `RotatingFileHandler(path, maxBytes=10*1024*1024, backupCount=5)` replaces `logging.FileHandler`
- `scripts/run_paper_trading_vt.py:566-568` — equity-write call: `open(EQUITY_LOG_PATH, 'a') + json.dumps + newline` after `_emit_ws01` main-path call
- `scripts/run_paper_trading_carry_fred.py:43` — `from logging.handlers import RotatingFileHandler`
- `scripts/run_paper_trading_carry_fred.py:85` — `EQUITY_LOG_PATH = 'data/paper_trading_session.log'`
- `scripts/run_paper_trading_carry_fred.py:123` (was 121) — `RotatingFileHandler(path, maxBytes=10*1024*1024, backupCount=5)` replaces `logging.FileHandler`
- `scripts/run_paper_trading_carry_fred.py:529-532` — equity-write call with `regime_active` included after `_emit_ws02` main-path call

**Two-invocation persistence evidence (verbatim from QD artifact):**

```
Invocation 1: {"regime_active": false, "n_readings": 1, "seen_regime_active_true": false, "seen_regime_active_false": true}
Invocation 2: {"regime_active": false, "n_readings": 2, "seen_regime_active_true": false, "seen_regime_active_false": true}
```
`n_readings == 2` confirmed after second invocation. `seen_regime_active_false` sticky.

---

## 6. What This Consensus Does NOT Do

- Does **NOT** start the paper loop. The hard constraint `no-paper-loop-start-by-orchestrator: true` remains in force. Paper loop start is a CEO operational action.
- Does **NOT** close items 9 or 10. Those remain BLOCKED-CEO-action (item 9: calendar reminder requires known paper-launch date; item 10: CEO-authored launch communication).
- Does **NOT** modify `CONSENSUS_2026-05-02_paper_launch_authorization.md`. That document is ratified and unmodified.
- Does **NOT** modify `CONSENSUS_2026-05-03_preflight_closure.md`. That document is closed and unmodified; this Wave-7 closure document is the addendum.
- Does **NOT** close CRO Assumption 1 (`_JPY_CORRELATED` frozenset asymmetry — `src/forex_system/risk/exposure_aggregator.py:46` contains only `{USDJPY, GBPUSD}`; cross-JPY pairs EURJPY, GBPJPY, AUDJPY, NZDJPY would silently bypass the cap). This is Wave-8+ scope; not relevant for the USDJPY-only paper launch.
- Does **NOT** close CRO Assumption 2 (Saxo paper account isolation). Both paper loops must run in the same Saxo paper account for portfolio-level JPY-correlated aggregation to work. This is an operational pre-flight reminder for CEO; not resolvable by engineering.
- Does **NOT** run new backtests, sweep configs, strategies, or trial pre-registrations.
- Does **NOT** modify any NHT dissent artifacts. The original Wave-6 dissent at `.agent-accountability/dissents/wave6-preflight-closure:phase1:task1.0:null-hypothesis-tester.yaml` is append-only per Rule 6 and is preserved unmodified. Resolution is documented in the new Wave-7 re-verification artifact only.

---

## 7. Pre-Flight Checklist Final Tally

| Category | Count | Items |
|----------|-------|-------|
| Engineering-closed | 8/10 | Items 1, 2, 3, 4, 5, 6, 7, 8 |
| Blocked-CEO-action | 2/10 | Items 9, 10 |

**Items 2 and 8 transition:** BLOCKED-engineering (Wave-6) → **verified-wired-and-tested** (Wave-7).

The pre-flight checklist is now fully resolved at the engineering layer. The remaining 2 items are exclusively CEO-action items that require a known paper-launch date and a CEO-authored disclosure — they cannot be closed by any engineering dispatch.

---

## 8. Recommended CEO Actions Before First Paper Bar

These are reminders to the CEO. They are not orchestrator-enforceable. No paper bar may be executed until the CEO has addressed these items.

**(a) Choose stale-log disposition for `data/paper_trading_session.log`**

The file exists from 2026-04-26T15:04:07Z (6 days old as of 2026-05-03) with 122 lines of stale content from a prior development session. The Ops Engineer flagged this in Wave-6 (`ops-engineer-verification.yaml`, `item-8-terminal-state: flag-for-ceo`). When the first paper bar executes, the equity-curve write (now wired via Wave-7 Task B) will append to this stale log. CEO must choose one of:

- **(a)** Truncate the file to 0 lines immediately before the first paper bar.
- **(b)** Verify that the new RotatingFileHandler creates a fresh file on startup (Wave-7 fix uses `open(path, 'a')` for equity-write, which preserves existing content; QD did not assert a truncation-on-startup behavior).
- **(c)** Accept the merged log, understanding the first 122 lines predate paper launch (operationally safe with rotating handler preventing unbounded growth).

**(b) Confirm both paper loops will run in the same Saxo paper account (CRO Assumption 2)**

`run_paper_trading_vt.py` (vol_target_carry) and `run_paper_trading_carry_fred.py` (Bet #1 carry_fred) both trade USDJPY. The JPY-correlated cap (BC-8, 15%) is enforced portfolio-wide only if both loops see the same Saxo paper account's position data via `get_positions()`. If run in separate accounts, the cap is computed per-strategy, not portfolio-wide. CEO must confirm a single shared paper account before first bar.

**(c) Set 60-trading-day calendar reminder for CF-T9 Clause C ratification on the day of first paper bar (item 9)**

NHT binding condition 2 (from `CONSENSUS_2026-05-02_paper_launch_authorization.md`) requires Clause C ratification within 60 trading days of paper launch. Item 9 of the pre-flight checklist cannot be set until T=0 is known. CEO must set the reminder on the day of first paper bar.

**(d) Draft launch communication including verbatim CF-T9 disclosure (item 10)**

Required verbatim disclosure clause (from `pm-acceptance-criteria.yaml` item 10):

> *"CF-T9 is binding on Clauses A and B. Clause C is accepted as a known-incomplete deferral and is pending ratification within 60 trading days of paper launch."*

CEO must draft or approve the launch communication containing this verbatim clause before starting the paper loop.

---

## 9. Disagreement Matrix

**Empty.** NHT lifted the Wave-6 material_concern dissent unanimously — `decision: dissent-lifted`, `does_block: false`. No role objections were raised in Wave-7. The A-F adversarial question set was answered satisfactorily (all questions resolved; no new blocking finding escalated).

---

## 10. Signatures

| Role | Decision | Artifact Path |
|------|----------|--------------|
| PM (Product Manager) | wave7-closure — propose-acceptance-criteria → auto-ratified | `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/pm-acceptance-criteria.yaml`; `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/pm-consensus-draft.yaml` |
| QD (Quant Developer) | approve (items 2, 8 verified-wired-and-tested) | `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/qd-implementation.yaml` |
| NHT (Null-Hypothesis Tester) | dissent-lifted (item 2 re-verified; does_block: false) | `.fintech-org/artifacts/2026-05-03T-wave7-preflight-fix/nht-reverification.yaml` |
| CTO (Chief Technology Officer) | Wave-6 sign-off still valid (unchanged); no Wave-7 re-review required | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cto-architecture-review.yaml` |
| CRO (Chief Risk Officer) | Wave-6 sign-off still valid (unchanged); CRO Assumptions 1+2 acknowledged as pre-flight reminders | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/cro-bc-wiring-verification.yaml` |
| Ops Engineer | Wave-6 sign-off still valid; stale-log flag persists (CEO-action pending) | `.fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/ops-engineer-verification.yaml` |

**NHT Wave-6 dissent artifact (append-only, preserved unmodified):** `.agent-accountability/dissents/wave6-preflight-closure:phase1:task1.0:null-hypothesis-tester.yaml`

**Ratification artifact:** `.agent-accountability/ratifications/wave7-preflight-closure:phase1:task1.0.yaml`

---

## 11. Auto-Ratification Record

This consensus was auto-ratified under `--full-auto` per `fintech-org/protocols/full-auto.md`.

| Field | Value |
|-------|-------|
| NHT severity | `none` (dissent lifted) |
| does_block | `false` (orchestrator-computed) |
| POLICY_VIOLATION | none logged this run |
| Auto-ratification trigger | NHT severity `none` → does_block `false` → eligible per protocol |
| User feedback memory | `feedback_full_auto_no_prompts.md` — orchestrator proceeds silently |
| CEO veto authority | Retained post-hoc; CEO may override this auto-ratification at any time |

**No manual CEO ratification is required for this closure.** The paper loop remains blocked by `no-paper-loop-start-by-orchestrator: true` and by items 9 + 10 (BLOCKED-CEO-action). Auto-ratification of this engineering-closure consensus does not authorize starting the paper loop — that remains exclusively a CEO operational action.

---

*This document was produced by the PM role in the Wave-7 fan-out. It synthesizes the Wave-7 QD and NHT artifacts alongside the Wave-6 role artifacts that remain in force. It does not introduce new domain-technical judgments. For domain-technical questions, route back to the originating role.*
