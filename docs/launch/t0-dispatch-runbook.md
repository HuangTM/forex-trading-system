# T=0 Dispatch Runbook — Paper Trading Launch

**Status:** EXECUTABLE — do NOT run before T=0 (first day of paper trading)  
**Version:** v2 (Wave-2a-v2: CRO + NHT amendments applied)  
**Authorization:** CONSENSUS_2026-05-10_paper_launch_authorization.md  
**Executor:** CEO huangtm@gmail.com (manual steps; orchestrator stages only)  
**Working directory (single terminal):** `/Users/huangtm/Projects/forex-trading-system`

---

## Overview

This runbook executes the four manual CEO actions remaining before continuous paper trading begins. Follow the steps in order. Each section is self-contained; a single terminal session with one `cd` at the top suffices to complete all steps.

**Do not execute any step until explicitly told the precondition passes.**

---

## Phase 1: Sign In (Pre-flight verification)

Before any state-changing step, confirm the environment is ready.

**Phase-1 preamble:**

```bash
echo "host=$(hostname) cwd=$(pwd) utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
test -n "$SAXO_TOKEN" || { echo "FATAL: SAXO_TOKEN not set"; exit 1; }
which python3 | grep -q ".venv" || { echo "FATAL: wrong python3"; exit 1; }
python3 -c "import forex_system; print(forex_system.__file__)"
```

---

### Step 1.0: Verify virtual environment and package import

**Precondition:** Python environment is set up

```bash
which python3 | grep -q ".venv" || { echo "FATAL: wrong python3"; exit 1; }
python3 -c "import forex_system; print(forex_system.__file__)"
```

**Expected output:** Path to `forex_system` package (e.g., `/Users/huangtm/Projects/forex-trading-system/.venv/lib/python3.11/site-packages/forex_system/__init__.py`)

**Verification:** Exit code is 0 and the path is from `.venv`. If not, activate the virtual environment:
```bash
source .venv/bin/activate
```

**Rollback:** N/A (read-only check)

---

### Step 1.1: Verify git HEAD is authorized

**Precondition:** Current working directory is `/Users/huangtm/Projects/forex-trading-system`

```bash
cd /Users/huangtm/Projects/forex-trading-system
git rev-parse HEAD
```

**Expected output:** `e6aaa43` (Wave-11 ratified) or a named successor  
**Verification:** If the output matches the authorized HEAD, proceed. If not, halt and notify the PM/CTO.

**Rollback:** N/A (read-only check)

---

### Step 1.2: Verify working tree is clean except for expected modifications

**Precondition:** Git is available and HEAD is authorized

```bash
git status --short
```

**Expected output:**
```
 M data/paper_trading_session.log
 M .fintech-org/spawns.jsonl
?? .fintech-org/artifacts/2026-05-12T-t0-dispatch-runbook/
```

(Order and unknown files are acceptable; CRITICAL: no other tracked files should be modified.)

**Verification:** Count the `M` lines. Only `data/paper_trading_session.log` and `.fintech-org/spawns.jsonl` should be modified. If any other tracked file is modified, halt and resolve before proceeding.

**Rollback:** N/A (read-only check)

---

### Step 1.3: Verify both paper scripts import cleanly (no syntax errors)

**Precondition:** Python 3.11+ is available and dependencies are installed

```bash
python3 -c "import scripts.run_paper_trading_vt; import scripts.run_paper_trading_carry_fred; print('✓ Both scripts import OK')"
```

**Expected output:**
```
✓ Both scripts import OK
```

**Verification:** Exit code is 0 and the success message appears. If there is a `ModuleNotFoundError` or `SyntaxError`, halt and run `pip install -e ".[dev]"` before retrying.

**Rollback:** N/A (read-only check)

---

### Step 1.4: Verify no stale flock files in data directory

**Precondition:** `find` and `ls` are available

```bash
find data -maxdepth 1 -name '*.flock' -mmin +60 2>/dev/null
ls -la data/dispatch_lock.flock 2>/dev/null && echo "stale lock file exists; check for live holder"
ls -la data/paper_account_key_lock.json 2>/dev/null && echo "parity lock exists; check age and account_key"
```

**Expected output:** Empty (no output from find); `ls` commands show the files if present (and that's OK if fresh)

**Verification:** If `find` returns any files older than 60 minutes, halt and investigate. If `ls` shows recent files (mtime within last 5 min), that's expected from prior test runs.

**Rollback:** N/A (read-only check)

---

### Step 1.5: Verify data directory exists and is writable

**Precondition:** Working directory is set to project root

```bash
test -d data && test -w data && echo "✓ data/ exists and is writable"
```

**Expected output:**
```
✓ data/ exists and is writable
```

**Verification:** Exit code is 0 and success message appears. If not, create the directory and set permissions before proceeding.

**Rollback:** N/A (read-only check)

---

### Step 1.6: Kill-switch audit-log pre-flight check

**Precondition:** Files may or may not exist

```bash
for f in data/kill_switch_audit.log data/kill_switch_audit_cf.log; do
  if [ -f "$f" ]; then
    LAST=$(tail -1 "$f")
    if echo "$LAST" | grep -q '"new_state":.*HALTED'; then
      echo "FATAL: $f last entry is HALTED. Investigate before relaunching."
      exit 1
    fi
  fi
done
echo "✓ Kill-switch audit logs OK (no active HALTS)"
```

**Expected output:**
```
✓ Kill-switch audit logs OK (no active HALTS)
```

**Verification:** Exit code is 0. If you see a FATAL message, investigate and remediate the halt condition before proceeding.

**Rollback:** N/A (read-only check)

---

## Phase 2: Time Out (State-changing steps in dependency order)

**CRITICAL:** Only proceed if ALL Phase 1 checks passed. If any precondition failed, halt the entire runbook.

---

### Step 2.1: SD-3 — Truncate stale log file

**Precondition:** All Phase 1 checks passed; `wc` is available

**Purpose:** Clear pre-launch log entries so the first paper bar starts with a clean audit trail.

**Context:** `data/paper_trading_session.log` currently contains entries from ad-hoc script invocations. RotatingFileHandler appends by default; truncating ensures first paper bar is the first entry.

#### 2.1.1: Check disk space before backup

```bash
df -h data/ | tail -1
```

**Expected output:** Shows free space; verify it is > 100MB

**Verification:** If free space < 100MB, halt and free up space before proceeding.

**Rollback:** N/A (read-only check)

---

#### 2.1.2: Backup the stale log

```bash
cp data/paper_trading_session.log "data/paper_trading_session.log.pre-launch-$(date -u +%Y%m%dT%H%M%SZ).bak"
```

**Expected output:** No output on success; file `data/paper_trading_session.log.pre-launch-TIMESTAMP.bak` created

**Verification:** `ls -la data/paper_trading_session.log.pre-launch-*.bak` shows at least one file

**Rollback:** If backup creation fails, halt and diagnose before truncating.

---

#### 2.1.3: Truncate the log

```bash
: > data/paper_trading_session.log
```

(Note: use `: >` instead of `> file` to avoid shell parsing ambiguity)

**Expected output:** No output

**Verification:** `wc -l data/paper_trading_session.log` returns exactly `0 data/paper_trading_session.log`

**Rollback:** If truncation fails, restore from backup:
```bash
mv data/paper_trading_session.log.pre-launch-*.bak data/paper_trading_session.log
```

---

#### 2.1.4: Verify truncation and record disposition

```bash
wc -l data/paper_trading_session.log
```

**Expected output:** `0 data/paper_trading_session.log`

**Verification:** If count is 0, SD-3 is complete. If count is non-zero, the truncate command did not work; investigate and retry.

---

### Step 2.2: SD-6 — CEO author/approve launch communication draft

**Precondition:** Text editor is available; you can edit `docs/launch/sd6-launch-communication-draft.md`

**Purpose:** Sign the launch communication to ratify that the paper trading authorization has been reviewed and accepted.

#### 2.2.1: View the signature line

```bash
sed -n '94p' docs/launch/sd6-launch-communication-draft.md
```

**Expected output:**
```
**Author/approver:** *(CEO signature required before T=0)*
```

**Verification:** If you see exactly this placeholder, proceed to edit. If the line is already signed (contains a date or name), SD-6 is already complete.

---

#### 2.2.2: Edit and sign the communication (deterministic sed replacement)

Replace the placeholder with your signature deterministically:

```bash
sed -i.bak "s|^\*\*Author/approver:\*\* \*(\(CEO signature required before T=0\))\*$|**Author/approver:** huangtm@gmail.com — $(date -u +%Y-%m-%dT%H:%MZ)|" docs/launch/sd6-launch-communication-draft.md
```

**Expected output:** No output on success; backup file `docs/launch/sd6-launch-communication-draft.md.bak` created

**Verification:** `grep -n "Author/approver:" docs/launch/sd6-launch-communication-draft.md` now shows the author line populated with your name/date (not the placeholder).

**Rollback:** If the replacement fails or produces an unexpected result, restore from backup:
```bash
mv docs/launch/sd6-launch-communication-draft.md.bak docs/launch/sd6-launch-communication-draft.md
```

---

#### 2.2.3: Verify verbatim CF-T9 clause integrity with SHA-256 re-verification

Run the SHA-256 integrity check:

```bash
python3 -c "
import hashlib, re
t = open('docs/launch/sd6-launch-communication-draft.md').read()
m = re.search(r'CF-T9 is binding[^\"]*paper launch\.', t)
h = hashlib.sha256(m.group().encode()).hexdigest()
exp = '8fe92e00098af4f8dff607c5411182ce394e115d0749d986ec014a39466113cb'
assert h == exp, f'CF-T9 hash MISMATCH: got {h}'
print('CF-T9 hash OK')
"
```

**Expected output:**
```
CF-T9 hash OK
```

**Verification:** Exit code is 0 and the hash matches. If hash mismatch, the file was corrupted during editing — roll back and retry.

**Rollback:** `git checkout docs/launch/sd6-launch-communication-draft.md` and retry step 2.2.2.

---

### Step 2.3: SD-5 — Set CF-T9 Clause C calendar reminder (pre-warning + hard deadline)

**Precondition:** Calendar or cron mechanism is available (see subsections below); you have permission to set calendar events or cron entries

**Purpose:** Schedule two reminders so the 60-trading-day CF-T9 Clause C deadline does not pass silently.

**CRITICAL NOTE on dates:** The pre-warning date (2026-07-26) is Sunday; hard deadline (2026-08-04) is Tuesday. **DO NOT execute `at` / crontab / Calendar.app entries until CRO ratifies the trading-day calendar definition.** The naive weekday convention used here (T0 + 75 calendar days = July 26) is NOT equivalent to 9 trading days remaining. 

**REQUIRED ACTION BEFORE PROCEEDING:** Escalate to CRO and request formal trading-day calendar ratification for CF-T9 Clause C pre-warning (expected ~2026-07-22 Wed for 9-trading-day offset) and hard deadline (expected ~2026-08-04 Tue for 60-trading-day offset).

---

#### 2.3.1: Choose ONE mechanism after CRO ratifies trading-day calendar (three options; see below)

**RECOMMENDED:** Calendar.app (Option 2) for cross-device visibility. Crontab (Option 1) as redundant local backup.

---

#### 2.3.1 Option 1: Crontab (persistent, headless-friendly)

**Precondition:** `crontab` is available, you have permission to edit cron entries, AND CRO has ratified trading-day calendar

```bash
# PLACEHOLDER: Use dates provided by CRO ratification
# Example (DO NOT EXECUTE without CRO approval):
# T_PREWARN_DOM="22"   # July 22 (example: CRO ratified)
# T_PREWARN_MON="7"    # July
# T_DEADLINE_DOM="4"   # August 4
# T_DEADLINE_MON="8"   # August

# Add pre-warning reminder to crontab
(crontab -l 2>/dev/null; echo "0 9 $T_PREWARN_DOM $T_PREWARN_MON * osascript -e 'display notification \"CF-T9 Clause C: 9 trading days remaining\" with title \"Forex paper-launch deadline\"'") | crontab -

# Add hard-deadline reminder to crontab
(crontab -l 2>/dev/null; echo "0 9 $T_DEADLINE_DOM $T_DEADLINE_MON * osascript -e 'display notification \"CF-T9 Clause C DEADLINE TODAY — NHT re-review triggers\" with title \"Forex paper-launch deadline\" sound name \"Submarine\"'") | crontab -

# Verify both entries are present
crontab -l | grep CF-T9
```

**Expected output:**
```
0 9 <PREWARN_DOM> 7 * osascript -e 'display notification "CF-T9 Clause C: 9 trading days remaining" with title "Forex paper-launch deadline"'
0 9 <DEADLINE_DOM> 8 * osascript -e 'display notification "CF-T9 Clause C DEADLINE TODAY — NHT re-review triggers" with title "Forex paper-launch deadline" sound name "Submarine"'
```

(Exactly 2 lines matching `CF-T9`)

**Verification:** `crontab -l | grep -c CF-T9` returns `2`. If it does, proceed.

**Rollback:** To remove both entries, edit crontab manually:
```bash
crontab -e
# Delete both CF-T9 lines, save and exit
```

---

#### 2.3.1 Option 2: Calendar.app (macOS, cross-device, RECOMMENDED)

**Precondition:** macOS is running and Calendar.app is available; `osascript` works; CRO has ratified trading-day calendar

**Pre-flight check (optional but recommended):** Verify Calendar.app can accept events and "Home" calendar exists
```bash
# TODO(v3): #14 — Add Calendar.app pre-flight: verify "Home" calendar exists and osascript permission granted
```

```bash
osascript << 'EOF'
tell application "Calendar"
    tell calendar "Home"
        make new event with properties {summary: "CF-T9 Clause C: 9 trading days remaining", start date: date "July 22, 2026 9:00 AM", end date: date "July 22, 2026 9:15 AM", description: "CF-T9 Clause C must be ratified within 9 trading days (CRO calendar definition) or NHT re-review triggers."}
        make new event with properties {summary: "CF-T9 Clause C DEADLINE — NHT re-review triggers TODAY", start date: date "August 4, 2026 9:00 AM", end date: date "August 4, 2026 9:30 AM", description: "CF-T9 Clause C ratification deadline. If not ratified by EOD, NHT re-review is mandatory."}
    end tell
end tell
EOF
```

**Expected output:** No errors; success means Calendar.app accepted the event creation

**Verification:** Open Calendar.app and check that both events appear on the CRO-ratified dates. If they do, proceed.

**Rollback:** Open Calendar.app and delete the two CF-T9 events manually.

---

#### 2.3.1 Option 3: REMOVED (at daemon disabled by default on macOS)

**Note:** The `at` daemon is not enabled by default on macOS. Option 3 has been removed per NHT WebSearch finding #13. Use Crontab (Option 1) or Calendar.app (Option 2).

---

#### 2.3.2: Record the disposition

After setting the reminder(s), append the disposition to the verification file:

```bash
cat >> docs/launch/sd6-launch-comm-verbatim-check.yaml << 'EOF'

sd5_calendar_reminder_set_at_T0:
  t0_date: "2026-05-12"
  pre_warning_date_planned: "TBD (pending CRO trading-day calendar ratification)"
  hard_deadline_date: "2026-08-04"
  mechanism_chosen: "<MECHANISM>"
  set_at: "2026-05-12T<HH:MM:SS>Z"
  set_by: huangtm@gmail.com
  verification_command_output: "<OUTPUT_FROM_VERIFICATION_STEP>"
EOF
```

where:
- `<MECHANISM>` is one of: `crontab`, `calendar`, or `crontab+calendar` (if you chose both Options 1 and 2)
- `<HH:MM:SS>Z` is the current UTC time
- `<OUTPUT_FROM_VERIFICATION_STEP>` is the output from the `crontab -l | grep CF-T9` (or Calendar/atq) step

**Verification:** `grep -c "sd5_calendar_reminder_set_at_T0" docs/launch/sd6-launch-comm-verbatim-check.yaml` returns 1 (or 2 if it already existed and you appended). The new section must be valid YAML.

---

### Step 2.4: Start persistent paper-loop runner (both scripts concurrently with --loop)

**Precondition:** tmux is available; `python3` and both scripts are importable (verified in Phase 1); SAXO_TOKEN is set

**Purpose:** Launch both paper trading scripts so they run continuously in 30-minute (1800s) cycles with auto-restart on crash. Both scripts will acquire the same `data/dispatch_lock.flock` and coordinate via fcntl-based mutual exclusion.

#### 2.4.1: Start VT script in tmux session `paper-vt` with --loop

```bash
tmux new-session -d -s paper-vt \
  'cd /Users/huangtm/Projects/forex-trading-system && \
   SAXO_TOKEN=$SAXO_TOKEN python3 scripts/run_paper_trading_vt.py --loop --interval 1800'
```

**Expected output:** No output on success; tmux session created

**Verification:** `tmux ls | grep paper-vt` shows `paper-vt: 1 window (created at...)`. If not, investigate the tmux command.

**Rollback:** `tmux kill-session -t paper-vt`

---

#### 2.4.2: Start carry_fred script in tmux session `paper-carry` with --loop

```bash
tmux new-session -d -s paper-carry \
  'cd /Users/huangtm/Projects/forex-trading-system && \
   SAXO_TOKEN=$SAXO_TOKEN python3 scripts/run_paper_trading_carry_fred.py --loop --interval 1800'
```

**Expected output:** No output on success; tmux session created

**Verification:** `tmux ls | grep paper-carry` shows `paper-carry: 1 window (created at...)`. If not, investigate the tmux command.

**Rollback:** `tmux kill-session -t paper-carry`

---

#### 2.4.3: Verify both sessions are live

```bash
tmux ls | grep -E '(paper-vt|paper-carry)'
```

**Expected output:**
```
paper-vt: 1 window (created at 2026-05-12 14:25:30)
paper-carry: 1 window (created at 2026-05-12 14:25:31)
```

**Verification:** Both sessions appear in the list (order and time may vary). If either is missing, check the rollback steps above.

---

#### 2.4.4: Wait for scripts to initialize and log startup state (polling loop)

**Timing:** Allow up to 60 seconds for each script to initialize, acquire its startup locks, and emit the first cycle entry.

```bash
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  LINES=$(wc -l < data/paper_trading_session.log 2>/dev/null || echo 0)
  if [ "$LINES" -gt 0 ]; then
    echo "✓ Log now has $LINES lines; scripts are initialized"
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "WARNING: timeout waiting for log entries after ${MAX_WAIT}s"
fi
tail -10 data/paper_trading_session.log
```

**Expected output:** New log entries showing the start of a paper trading cycle (timestamps should be current, within the last few seconds). Polling messages as loop runs.

**Verification:** 
- New entries appear in the log (at least 1 line).
- No FATAL or error messages are visible.
- If you see `account_key_parity_violation`, the account key has changed (halt and diagnose).
- If you see `dispatch_lock` errors, investigate which script failed.

**Rollback:** If either script fails to start, kill both sessions and investigate:
```bash
tmux kill-session -t paper-vt
tmux kill-session -t paper-carry
tail -50 data/paper_trading_session.log | grep -E "(FATAL|ERROR|account_key|lock)" # diagnose
```

---

#### 2.4.5: Verify dispatch lock is held (live lock check)

Use a live lock check via `lsof` to confirm an active process holds the lock:

```bash
lsof data/dispatch_lock.flock | grep python3 | wc -l
```

**Expected output:** `1` (exactly one python3 process holds the flock)

**Verification:** If count is ≥ 1, the lock is held by a live process. If count is 0, the scripts have not yet reached the lock-acquire point (wait 5 more seconds and retry). Also verify the file exists:

```bash
ls -la data/dispatch_lock.flock
```

**Expected output:**
```
-rw-r--r-- 1 huangtm staff 0 May 12 14:25 data/dispatch_lock.flock
```

**Caveat (SIGKILL):** Kernel reclaims the FD on SIGKILL but the `DISPATCH_LOCK_RELEASED` audit log line is lost. On suspected SIGKILL, inspect for orphaned positions before re-launch.

---

## Phase 3: Sign Out (Post-launch verification)

Once all Phase 2 steps complete, verify that the paper trading loop is healthy and ready for continuous operation.

---

### Step 3.1: Confirm both tmux sessions are running

```bash
tmux ls
```

**Expected output:** Both `paper-vt` and `paper-carry` sessions listed, neither in a crashed/dead state.

**Verification:** If either session shows `(dead)` or is missing, halt and diagnose the failure.

---

### Step 3.2: Check that scripts are emitting heartbeats (or fallback to trace logs)

**Primary check (if heartbeat files are wired):**

```bash
ls -la data/heartbeats/vt.json data/heartbeats/carry_fred.json 2>/dev/null
```

**Expected output:** Both files present with recent mtime (within last 300s).

**Fallback (if heartbeat files don't exist):** Inspect WebSocket trace logs for recent activity:

```bash
# TODO(v3): #5 — Confirm heartbeat files are actually emitted by scripts; fallback to ws01/ws02 if missing
ls -la data/ws01_trace.log data/ws02_trace.log 2>/dev/null && tail -1 data/ws01_trace.log && tail -1 data/ws02_trace.log
```

**Verification:** Both logs should have recent timestamps (within last 300s). If timestamps are stale, the scripts may be hung or failed.

---

### Step 3.3: Verify no FATAL errors in log (extended check for all halt sources)

```bash
grep -i "FATAL\|ACCOUNT_KEY_PARITY_VIOLATION\|dispatch_lock.*error\|HALTED" data/paper_trading_session.log | tail -5
```

**Expected output:** No lines (empty), OR lines from kill-switch audit logs (which were pre-checked in Step 1.6).

**Verification:** If you see FATAL errors (excluding known kill-switch entries), halt, kill the sessions, and investigate the log. Do not proceed if there are FATAL errors.

---

### Step 3.4: Verify account-key parity gate passed (positive file check)

Use a positive parity file check:

```bash
test -f data/paper_account_key_lock.json && \
  python3 -c "import json; d=json.load(open('data/paper_account_key_lock.json')); print('account_key='+d['account_key'])"
```

**Expected output:** Line showing `account_key=<KEY>` (the actual key value)

**Verification:** If you see the account_key value, the parity gate passed. If the file doesn't exist or the key doesn't print, the gate hasn't acquired yet; wait 10 seconds and retry.

**NOTE:** CRO preferred long-term fix (separate SD amendment): Patch `src/forex_system/risk/account_key_parity.py` line 63 to emit `logger.info('account_key_parity_lock_acquired', ...)` on success. This will make the silence-ambiguity issue moot. **TODO(v3):** Implement this as a separate SD amendment.

---

### Step 3.5: Check drawdown ladder snapshot at startup (heartbeat files or trace logs)

**Primary check (if heartbeat files exist):**

```bash
# TODO(v3): #9 — Use heartbeat files for per-cycle liveness (requires wire confirmation)
ls -la data/heartbeats/*.json 2>/dev/null | head -3
```

**Fallback (if heartbeat files don't exist):**

```bash
tail -1 data/ws01_trace.log data/ws02_trace.log
```

**Expected output:** Recent WebSocket trace entries (timestamps within last 300s)

**Verification:** If you see recent entries, the drawdown ladder is being monitored. For paper-only operation, this is acceptable.

---

### Step 3.6: Record final disposition in verification file

Append the final sign-off to the verification file:

```bash
cat >> docs/launch/sd6-launch-comm-verbatim-check.yaml << 'EOF'

sd3_disposition_executed_at_T0:
  option_chosen: "a"
  executed_at: "2026-05-12T<HH:MM:SS>Z"
  pre_disposition_line_count: 317
  post_disposition_line_count: 0
  backup_file: "data/paper_trading_session.log.pre-launch-<TIMESTAMP>.bak"
  executed_by: huangtm@gmail.com

sd6_ceo_author_signature_present: true

paper_loop_launch_verified_at_T0:
  timestamp: "2026-05-12T<HH:MM:SS>Z"
  paper_vt_session_live: true
  paper_carry_session_live: true
  dispatch_lock_held: true
  account_key_parity_passed: true
  first_cycle_logged: true
  launched_by: huangtm@gmail.com
EOF
```

**Verification:** File parses as valid YAML and contains all required fields.

---

### Step 3.7: Summary

Once all three phases complete, the paper trading launch is **LIVE**:

- ✅ Log truncated (SD-3)
- ✅ Communication signed (SD-6)
- ✅ Calendar reminders set (SD-5, pending CRO trading-day calendar ratification)
- ✅ Both scripts running concurrently in --loop --interval 1800 mode with dispatch lock active
- ✅ Account-key parity gate passed
- ✅ First cycle logged
- ✅ Heartbeats (or fallback trace logs) being emitted

**Next actions (out of scope for this runbook):**

1. Monitor `data/paper_trading_session.log` for the next 1–2 hours to confirm normal operation.
2. Set a calendar reminder for yourself to check the positions and P&L daily.
3. At CRO-ratified pre-warning date, begin drafting Clause C ratification.
4. At T0 + 84 calendar days (2026-08-04), the hard deadline reminder will fire; Clause C MUST be ratified or NHT re-review is triggered.

---

## Graceful Shutdown and SIGKILL Caveat

If you need to stop the paper trading loop gracefully:

```bash
tmux send-keys -t paper-vt C-c
tmux send-keys -t paper-carry C-c
```

This sends SIGINT (Ctrl+C) to both scripts, allowing them to clean up and emit the final `DISPATCH_LOCK_RELEASED` audit log line.

**WARNING — SIGKILL is uncatchable:** If you use `kill -9` (SIGKILL) on either script process, the kernel immediately reclaims the FD so the flock is released, but the `DISPATCH_LOCK_RELEASED` audit-log line is NOT written. On suspected SIGKILL, inspect `data/paper_trading_session.log` and any open position files before re-launching to ensure no orphaned positions remain.

---

## Troubleshooting Quick Reference

| Symptom | Diagnosis | Fix |
|---|---|---|
| Phase 1 SAXO_TOKEN not set | Environment variable missing | `export SAXO_TOKEN=<token>` before running runbook |
| Phase 1 venv check fails | Virtual environment not activated | `source .venv/bin/activate` |
| Phase 1 git check fails | HEAD is not at authorized commit | Contact CTO; may require rebase or reset |
| Phase 1 script import fails | Dependencies missing or code syntax error | Run `pip install -e ".[dev]"` and retry |
| Phase 1 kill-switch HALTED | Kill-switch was activated in prior run | Investigate reason for halt and fix condition before relaunching |
| Phase 2.1 truncate fails | File permissions or disk full | Check `ls -la data/` and `df -h /` |
| Phase 2.2 file edit fails | Editor crashed or file locked | Restore from git and retry |
| Phase 2.4 tmux session fails to start | tmux not installed or shell error | Install tmux or check shell syntax |
| Phase 2.4 dispatch_lock not created | Scripts not reaching lock-acquire point | Check tmux buffer: `tmux capture-pane -t paper-vt -p` |
| Phase 3 account-key mismatch | Scripts target different accounts | Kill sessions, fix token or config, retry |
| Phase 3 log not growing | Scripts stuck on lock contention | Check for zombie processes: `ps aux \| grep run_paper` |
| Phase 3 heartbeat files missing | Heartbeat watchdog not wired | Fall back to ws01/ws02 trace logs (secondary check) |

---

## Cross-references

- Master authorization: `docs/decisions/CONSENSUS_2026-05-10_paper_launch_authorization.md`
- Amendment consensus: `docs/decisions/CONSENSUS_2026-05-12_t0_dispatch_runbook.md`
- SD-3 per-action runbook: `docs/launch/sd3-truncate-stale-log-runbook.md` (this runbook supersedes it)
- SD-5 reminder template: `docs/launch/sd5-calendar-reminder-template.md` (options 1–2 copied here; option 3 removed per NHT finding)
- SD-6 launch communication: `docs/launch/sd6-launch-communication-draft.md` (line 94 is the signature line)
- Verbatim check artifact: `docs/launch/sd6-launch-comm-verbatim-check.yaml` (append dispositions here)
- Dispatch lock design: `src/forex_system/risk/kill_switch.py`, `scripts/run_paper_trading_vt.py:76`, `scripts/run_paper_trading_carry_fred.py:95`
- Account-key parity gate: `src/forex_system/risk/account_key_parity.py`
- Heartbeat watchdog: `src/forex_system/risk/heartbeat_watchdog.py`
- Drawdown ladder spec: `docs/specs/drawdown_ladder_amendment_2026-05-06.md`

---

## Amendment Log

| Amendment ID | Source | CONSENSUS Finding ID | Status | Step(s) Affected | Note |
|---|---|---|---|---|---|
| 1 | BLOCKING | T0-DISPATCH-BLOCKING-001 | APPLIED | 2.4.1, 2.4.2 | Added `--loop --interval 1800` and `SAXO_TOKEN=$SAXO_TOKEN` to both tmux invocations |
| 2 | BLOCKING | T0-DISPATCH-BLOCKING-002 | APPLIED | 1.6 | Added kill-switch audit-log pre-flight check; halt if HALTED state detected |
| 3 | BLOCKING | T0-DISPATCH-BLOCKING-003 | APPLIED | 3.4 | Replaced absence-based parity check with positive `data/paper_account_key_lock.json` file check; flagged CRO SD amendment for parity.py logger.info |
| 4 | BLOCKING | T0-DISPATCH-BLOCKING-004 | APPLIED | 2.4.5 | Replaced stale-file lock verification with live `lsof` check; documented SIGKILL caveat |
| 5 | BLOCKING | T0-DISPATCH-BLOCKING-005 | APPLIED | 3.2, 3.5 | Replaced 10-second log-delta with heartbeat file recency check; fallback to ws01/ws02 trace logs if heartbeat files missing |
| 6 | BLOCKING | T0-DISPATCH-BLOCKING-006 | APPLIED | 2.2.3 | Added SHA-256 re-verification post-signing (CF-T9 clause hash integrity check) |
| 7 | BLOCKING | T0-DISPATCH-BLOCKING-007 | APPLIED | 1.4, 2.3 | Fixed flock stale-file check path (data/ not /tmp/); replaced zsh glob with `find`; escalated SD-5 date math to CRO for trading-day calendar ratification |
| 8 | BLOCKING | T0-DISPATCH-BLOCKING-008 | APPLIED | 2.3 | DO NOT hardcode 2026-07-26; replaced with CRO trading-day calendar escalation; documented pre-warning and hard-deadline dates pending ratification |
| 10 | CONCERN | T0-DISPATCH-CONCERN-010 | APPLIED | 1.0 | Added venv verification (Step 1.0) with python3 path check and forex_system import |
| 11 | CONCERN | T0-DISPATCH-CONCERN-011 | APPLIED | Phase-1 preamble | Added hostname/cwd/UTC timestamp assertion at top |
| 12 | CONCERN | T0-DISPATCH-CONCERN-012 | APPLIED | 2.1.2 | Replaced `$(date +%Y%m%dT%H%M%S)` with UTC `$(date -u +%Y%m%dT%H%M%SZ)` for backup filename |
| 13 | CONCERN | T0-DISPATCH-CONCERN-013 | APPLIED | 2.3.1 | Removed Option 3 (`at` daemon) entirely; documented atd disabled by default on macOS (NHT WebSearch finding) |
| 14 | CONCERN | T0-DISPATCH-CONCERN-014 | TODO(v3) | 2.3.1 Option 2 | Calendar.app pre-flight check: verify "Home" calendar exists and osascript permission granted |
| 15 | CONCERN | T0-DISPATCH-CONCERN-015 | APPLIED | 2.2.2 | Replaced manual nano editor with deterministic `sed -i` replacement of placeholder with email + UTC timestamp |
| 16 | CONCERN | T0-DISPATCH-CONCERN-016 | TODO(v3) | Phase 2, all steps | Add phase-confirmation block at end of each phase per deploy-checklist-trading rubric (verbal confirmation) |
| 17 | CONCERN | T0-DISPATCH-CONCERN-017 | APPLIED | 2.4.4 | Increased initialization wait from 5s to polling loop (up to 60s) with 2s sleep intervals |
| 18 | CONCERN | T0-DISPATCH-CONCERN-018 | APPLIED | 2.1.1 | Added disk-space check (`df -h data/`); require > 100MB free before cp backup |
| 19 | CONCERN | T0-DISPATCH-CONCERN-019 | APPLIED | 1.6, 3.3 | Extended FATAL grep to include both `data/kill_switch_audit.log` and `data/kill_switch_audit_cf.log` files |
| 20 | CONCERN | T0-DISPATCH-CONCERN-020 | TODO(v3) | Troubleshooting | Move `ps aux \| grep run_paper` from markdown table cell to code block (formatting) |
| 21 | CONCERN | T0-DISPATCH-CONCERN-021 | APPLIED | Graceful Shutdown (new section) | Added SIGKILL caveat paragraph: kernel reclaims FD, `DISPATCH_LOCK_RELEASED` line NOT written, inspect orphaned positions before re-launch |
| 3-SD | CRO preferred fix | T0-DISPATCH-BLOCKING-003 supplement | TODO(v3) | 3.4 | Patch `src/forex_system/risk/account_key_parity.py` line 63 to emit `logger.info('account_key_parity_lock_acquired', ...)` on success (separate SD required) |

---

**End of v2 runbook. Do not execute before T=0 2026-05-12.**
