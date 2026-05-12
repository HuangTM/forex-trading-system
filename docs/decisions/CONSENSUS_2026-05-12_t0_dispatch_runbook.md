# Consensus on: T=0 Dispatch Runbook (SD-3 + SD-5 + SD-6 + Persistent Paper-Loop Runner)

**Status:** awaiting-ratification
**Session artifact dir:** `.fintech-org/artifacts/2026-05-12T-t0-dispatch-runbook/`
**Authored:** 2026-05-12 | **PM:** product-manager

---

## Task Statement

Author a single ordered T=0 runbook combining SD-3, SD-5, SD-6, and persistent
paper-loop runner setup, executable by CEO in one terminal session.

---

## Roles Staffed

| Role | Rationale | Wave |
|------|-----------|------|
| ops-engineer | Primary runbook author; exact commands for SD-3/SD-5/SD-6 + persistent runner setup | 2a |
| cro | Risk co-sign on BC-8-LIFT-COND-1..7 preservation under chosen supervisor mechanism | 2b |
| null-hypothesis-tester | Structural skeptic; probes steps that look complete but skip a precondition check | 2b |
| pm | Acceptance-criteria (wave-1); CONSENSUS draft + signature collection (wave-4) | 1+4 |

*Note: Principal Reviewer (PR) was not staffed — this is an operational runbook, not code/design/algorithm. CTO was not staffed for the same reason.*

---

## Acceptance Criteria Status

| ID | Label | Status | Notes |
|----|-------|--------|-------|
| C-1 | SD-3 truncate executed and verified before first paper bar | **NOT MET** | Runbook Step 2.1 not yet executed by CEO |
| C-2 | SD-6 CEO author/approve signature present | **NOT MET** | CEO has not signed |
| C-3 | SD-5 calendar reminders set and verified (T0+75 + T0+84) | **BLOCKED** | G-3: T0+75 date (2026-07-26) is a Sunday; pre-warning fires wrong day and 4 calendar days late |
| C-4 | Persistent runner staged and both scripts confirmed healthy | **BLOCKED** | G-1: tmux invocations omit --token and --loop; scripts will exit within seconds |
| C-5 | Runbook is a single ordered document covering all 4 actions end-to-end | **Partial** | Structure correct; blocking gaps in commands prevent execution |
| C-6 | CRO co-sign confirming BC-8-LIFT-COND-1..7 preserved | **Conditional** | CRO: approve-with-binding-conditions; 3 BLOCKING findings remain |
| C-7 | NHT has probed runbook for steps that skip precondition check | **Complete** | NHT: dissent; 7 blocking gaps found |

---

## Aggregated Findings

*Unified CRO + NHT finding table. Where both independently identified the same issue, entries are merged (source: both). Ordered by severity then by gap ID.*

| Finding ID | Source | Class | Description | Evidence Pointer | Severity | Suggested Amendment |
|-----------|--------|-------|-------------|-----------------|----------|---------------------|
| F-01 (G-1, AMENDMENT-1) | both | failure-mode | tmux invocations omit `--token` and `--loop`; scripts exit within seconds; SAXO_TOKEN not in env; Phase-3 verification falsely confirms success on a dead session | NHT: runbook lines 396-397, 411-412; CRO: runbook lines 396-398; vt.py:828,856; carry_fred.py similar | **blocking** | Append `--loop --interval 1800` to both tmux commands; require `SAXO_TOKEN` env var set and verified in Phase 1 before any state-changing step |
| F-02 (G-3) | nht | date-math | SD-5 pre-warning date 2026-07-26 is a Sunday; independently-computed 9-trading-days-remaining date is 2026-07-22 (Wed); CF-T9 Clause C ratification reminder fires 4 calendar days late and on a non-working day | NHT: date-arithmetic-verification section; runbook lines 247-256 | **blocking** | Definition of "trading day" must be CRO-ratified; pre-warning date must be recomputed against approved calendar. Until then, runbook must not set SD-5 reminders and must escalate to CRO |
| F-03 (G-5, CRO check_id 2 / AMENDMENT-3) | both | silent-confirm | account-key parity gate (COND-3) emits NO log on success; runbook Step 3.4 accepts empty grep as pass; observationally indistinguishable from (a) gate passed, (b) script crashed before gate, (c) script never started | NHT: account_key_parity.py:50-65; CRO: account_key_parity.py:63; runbook lines 526-535 | **blocking** | Either (a) add `logger.info('account_key_parity_lock_acquired')` to account_key_parity.py success path (code change, separate SD), OR (b) verify lock file positive: `test -f data/paper_account_key_lock.json && python3 -c "import json; ..."` |
| F-04 (G-13, AMENDMENT-2 partial) | nht | verification | dispatch_lock.flock already exists at 0 bytes from May 6 session; `ls` presence + 0-byte size does NOT confirm a live fcntl lock; verification is invalid | NHT: data/dispatch_lock.flock confirmed pre-existing; runbook lines 464-477 | **blocking** | Replace `ls data/dispatch_lock.flock` with `lsof data/dispatch_lock.flock \| grep python3 \| wc -l` ≥ 1; caveat: lsof may require root on macOS |
| F-05 (G-14) | nht | verification | Step 3.2 log-growth check (delta ≥ 1 line in 10 seconds) is meaningless given 1800s cycle interval; under G-1, delta=0 forever and runbook says "wait 1800s" — 30-minute false-comfort window | NHT: runbook lines 498-512; vt.py:978 default interval=1800 | **blocking** | Replace with heartbeat file recency check: `data/heartbeats/{vt,carry_fred}.json` mtime within last 5 minutes |
| F-06 (G-9) | nht | hash | Post-signing CF-T9 verbatim check uses 8-word grep substring, not SHA-256; smart-quote or em-dash mishap during editor signing passes grep and fails SHA-256 without detection; verbatim-check.yaml already stale (claims 105 lines; actual 97) | NHT: hash-verification section; runbook lines 230-241 | **blocking** | After signing, re-run SHA-256 hash check against 8fe92e0...cb; refuse to proceed on mismatch |
| F-07 (G-2, CRO check_id 5 / AMENDMENT-2) | both | precondition | Stale flock check targets /tmp/*.flock; actual lock is at data/dispatch_lock.flock; zsh glob failure returns 0 for wrong reason; no check for stale paper_account_key_lock.json; kill-switch audit logs not pre-checked for HALTED state | NHT: runbook lines 84-93; CRO: vt.py:158-188, runbook (no kill-switch arming step); CRO check_id 5 | **blocking** | (a) Fix flock check path to `data/dispatch_lock.flock`; (b) Add Step 1.6: check `kill_switch_audit.log` and `kill_switch_audit_cf.log` for HALTED last entry before starting any session |
| F-08 (G-4) | nht | failure-mode | SD-5 Option 3 (`at`) requires macOS atrun daemon; `atd not found` on target machine; atrun disabled by default on modern macOS; `at` jobs queue but never fire; `atq` verification passes falsely | NHT: G-4; runbook lines 325-345 | concern | Remove Option 3 or add explicit atrun enabled pre-check; recommend Option 1 (crontab) as sole supported mechanism |
| F-09 (CRO check_id 4 / AMENDMENT-4) | cro | verification | Steps 3.2 and 3.5 target data/paper_trading_session.log for liveness/drawdown; this file is trade-event-only (written only at trade execution); per-cycle liveness lives in data/ws01_trace.log (vt) and data/ws02_trace.log (carry_fred) | CRO: vt.py:119-142, vt.py:722; runbook lines 498-512, 539-547 | concern | Replace verification targets: `tail -1 data/ws01_trace.log` and `tail -1 data/ws02_trace.log` for liveness; both should have entries within last 1800s |
| F-10 (G-6) | nht | precondition | Step 1.2 expected-output example does not include `?? docs/launch/t0-dispatch-runbook.md` (runbook itself is currently untracked); careful CEO would flag as anomalous and halt at Phase 1 | NHT: G-6; actual git status confirmed | concern | Either commit the runbook before T=0 and update expected-output, OR list runbook's own path as "untracked is acceptable" in the example |
| F-11 (CRO check_id 7 / AMENDMENT-5) | cro | precondition | No hostname assertion; cross-host deployment silently bypasses BC-8-LIFT-COND-1 (fcntl locks are per-kernel); runbook line 27 has `cd` but no `hostname` check | CRO: check_id 7; PM hard-constraint #9 | concern | Add `echo "host=$(hostname) cwd=$(pwd) utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"` at top of runbook; operator must confirm against prior runs |
| F-12 (G-7) | nht | verifier-tool | Calendar.app AppleScript Option 2 assumes calendar "Home" exists, write-enabled, iCloud online, osascript automation permission granted; locale-dependent date parsing | NHT: G-7; runbook lines 305-322 | concern | Add pre-flight: `osascript -e 'tell application "Calendar" to name of calendars' \| grep "^Home$"`; use ISO-8601 date construction instead of locale-dependent string |
| F-13 (G-8) | nht | order | Step dependencies not machine-enforced; if CEO re-runs from editor out of order, SD-3 truncate could destroy first-bar log entries; Step 2.4 missing pre-check that 2.1 completed | NHT: G-8 | concern | Each step's precondition block must verify all prior steps' completion |
| F-14 (CRO check_id 8 / AMENDMENT-6) | both | clock | Backup filename uses local time (`date` without -u); rest of system uses UTC; DST boundary collision possible; crontab reminder time is local-clock-dependent | CRO: check_id 8; NHT: G-10 | concern | Use `date -u +%Y%m%dT%H%M%SZ` for backup filename; document SD-5 reminder timezone explicitly |
| F-15 (G-12) | nht | failure-mode | No disk-space check before cp backup; cp on full partition produces 0-byte backup; rollback would mv 0-byte file over truncated log, destroying 317 lines of pre-launch audit trail | NHT: G-12; runbook lines 130-141 | concern | Add `df -h data/` check in Phase 1 (require > 100MB free); verify backup file size matches original after cp |
| F-16 (G-15, CRO check_id 5) | both | precondition | kill_switch audit logs (data/kill_switch_audit.log, data/kill_switch_audit_cf.log) not inspected in Phase 3; if kill switch fires at startup, only kill_switch_audit* files capture it; Step 3.3 only checks paper_trading_session.log | NHT: G-15; CRO: check_id 5 | concern | Add to Phase 3: check both kill-switch audit files for non-empty entries since session start; any non-empty entry triggers HALT |
| F-17 (G-16) | nht | precondition | No venv verification in Phase 1; macOS system python3 may be selected; wrong python silently imports project without required deps or with wrong versions | NHT: G-16 | concern | Add Step 1.0: `which python3 \| grep -q ".venv/bin/python3"` AND `python3 -c "import forex_system; print(forex_system.__file__)"` |
| F-18 (G-17) | nht | failure-mode | Step 2.4.4 sleeps only 5 seconds before checking log; SaxoClient initialization + API roundtrip may take 15-30s; delta=0 at 5s is expected even on successful launch; check provides no signal | NHT: G-17; vt.py: SaxoClient construction sequence | concern | Replace with polling loop: up to 60s wait for any line in the log OR specific marker (e.g., "DISPATCH_LOCK_ACQUIRED") |
| F-19 (G-18) | nht | failure-mode | Step 2.2.2 manual editor edit; common error modes: duplicate placeholder+signature lines; smart-quote autocorrect; em-dash substitution; no automated post-edit predicate on the SIGNATURE LINE itself | NHT: G-18 | concern | Replace with deterministic sed; add post-validation: count of placeholder drops to 0, count of CEO name rises to 1 |
| F-20 (CRO check_id 9 / AMENDMENT-7) | cro | protocol | Runbook does not require explicit "confirmed" verbal acknowledgment per phase (Gawande/WHO checklist structure); single-CEO setup collapses to silent execution with no audit-trail-bearing confirmation | CRO: check_id 9 | concern | Add phase-confirmation block at end of each phase: "Phase X confirmed by: huangtm@gmail.com at <UTC ISO 8601>" appended to sd6-launch-comm-verbatim-check.yaml |
| F-21 (CRO check_id 1 / AMENDMENT-8) | cro | risk | SIGKILL (kill -9 or some tmux kill-session configs) bypasses finally block; fcntl lock auto-releases via kernel but audit log entry lost; not documented | CRO: check_id 1; vt.py:807-820 | concern | Document: use `tmux send-keys -t paper-vt C-c` for graceful shutdown (SIGINT runs finally); then `tmux kill-session`; warn that SIGKILL loses the audit log entry |
| F-22 (G-11) | nht | precondition | No Phase 1 check that tmux is installed and on PATH | NHT: G-11 | note | Add Step 1.6: `which tmux && tmux -V` |
| F-23 (G-19) | nht | verifier-tool | Troubleshooting table at line 614 uses `\|` (escaped pipe) in markdown table cell; CEO copy-paste produces literal backslash + pipe in some shells | NHT: G-19 | note | Move troubleshooting commands into code blocks; remove the backslash |

**Summary:** 7 blocking findings (F-01 through F-07), 14 concern findings (F-08 through F-21), 2 note findings (F-22, F-23).

---

## BC-8-LIFT-COND Status Table

*Per CRO wave-2b review. CRO evidence pointers are verbatim from cro-risk-review.yaml.*

| COND | Description | Preserved by Runbook? | Evidence Pointer | Concerns |
|------|-------------|----------------------|-----------------|----------|
| COND-1 | dispatch lock fcntl LOCK_EX\|LOCK_NB active in both scripts | **Conditional** | vt.py:465 + carry_fred.py:446 — code path is reached when `--loop` is set | F-01: without `--loop`, script runs one cycle and exits; mutual exclusion trivially holds but persistence does not |
| COND-2 | lock released on all exit paths (try/finally) | **Yes (code); gap (audit)** | vt.py:807-820 + carry_fred.py:757-770 try/finally release | tmux kill-session SIGTERM: Python finally MAY run; SIGKILL: finally does NOT run; kernel auto-releases but audit log entry lost (F-21) |
| COND-3 | account-key parity gate enforced at startup before any cycle | **Yes (code); fail (verification)** | vt.py:874 + carry_fred.py:814 assert_account_key_parity called at startup | F-03: gate fires correctly; runbook verification (Step 3.4) cannot positively confirm it; absence-of-VIOLATION is not positive confirmation |
| COND-4 | aggregate JPY-correlated cap <=15% | **Yes** | exposure_aggregator.py:46 frozenset immutable; vt.py:94 + carry_fred.py CRO_MAX_CORRELATED_PCT=0.15 | None; config-immutable, runbook does not modify |
| COND-5 | drawdown ladder 10/15/20 assessed per cycle pre-lock | **Yes (code); gap (verification)** | vt.py:418 dd_contract.assess(equity) BEFORE fcntl.flock at line 465 | F-09: runbook Step 3.5 verification probes wrong log file (paper_trading_session.log instead of ws01_trace.log) |
| COND-6 | kill-switch trigger paths wired to both loops | **Fail (runbook)** | KillSwitch instantiated in vt.py:888 + carry_fred.py:828; runbook has no arming-check step | F-07: runbook does not pre-check kill_switch_audit.log for HALTED state; stale HALTED causes RuntimeError on startup; tmux session dies in ms; runbook may not detect it |
| COND-7 | paper-only; live=False hardcoded; no production-account promotion | **Yes** | vt.py:871 + carry_fred.py:811 `SaxoClient(args.token, live=False)` | None |

---

## Aggregated Amendment List

*Flat numbered list for wave-2a-v2 dispatch backlog. Items are actionable commands or file:line targets.*

### BLOCKING (must fix before CEO executes Phase 2)

1. **[runbook lines 396-397, 411-412] Add `--loop --interval 1800` and `SAXO_TOKEN=$SAXO_TOKEN` to both tmux invocations:**
   ```
   tmux new-session -d -s paper-vt \
     'cd /Users/huangtm/Projects/forex-trading-system && \
      SAXO_TOKEN=$SAXO_TOKEN python3 scripts/run_paper_trading_vt.py --loop --interval 1800'
   ```
   Similarly for `paper-carry`. Add Phase 1 precondition step: `test -n "$SAXO_TOKEN" || { echo "FATAL: SAXO_TOKEN not set"; exit 1; }`.

2. **[Phase 1, new Step 1.6] Kill-switch audit-log pre-flight check:**
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
   ```

3. **[runbook lines 526-535, Step 3.4] Replace absence-based account-key parity check with positive file check:**
   ```bash
   test -f data/paper_account_key_lock.json && \
     python3 -c "import json; d=json.load(open('data/paper_account_key_lock.json')); print('account_key='+d['account_key'])"
   ```
   CRO preferred path: patch `src/forex_system/risk/account_key_parity.py` line 63 to emit `logger.info('account_key_parity_lock_acquired', ...)` on success (one log statement; separate SD required).

4. **[runbook lines 464-477, Step 2.4.5] Replace stale-file lock verification with live lock check:**
   ```bash
   lsof data/dispatch_lock.flock | grep python3 | wc -l
   # expect ≥ 1
   ```

5. **[runbook lines 498-512, Step 3.2] Replace 10-second log-delta check with heartbeat file recency:**
   ```bash
   ls -la data/heartbeats/vt.json data/heartbeats/carry_fred.json 2>/dev/null
   # both files must exist and mtime within last 300s (first cycle not yet complete)
   ```

6. **[runbook lines 230-241, Step 2.2.3] Add SHA-256 re-verification post-signing:**
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

7. **[runbook lines 84-93, Step 1.4] Fix flock stale-file check — correct path and zsh glob:**
   ```bash
   find data -maxdepth 1 -name '*.flock' -mmin +60 2>/dev/null
   # expect empty; also check:
   ls -la data/dispatch_lock.flock 2>/dev/null && echo "stale lock file exists; check for live holder"
   ls -la data/paper_account_key_lock.json 2>/dev/null && echo "parity lock exists; check age and account_key"
   ```

8. **[Step 2.3 — SD-5 date math] Do NOT hardcode 2026-07-26 as pre-warning date until CRO ratifies trading-day definition.** Pre-warning must fall on 9-trading-days-before-60-TD-mark; independently computed as 2026-07-22 (Wed) for naive weekday count. Options: (a) CRO ratifies trading-day calendar and runbook recomputes; (b) runbook escalates to CRO before setting reminder.

### CONCERN (should fix; audit-trail and operational quality)

9. **[Steps 3.2, 3.5] Target ws01/ws02 trace files for per-cycle liveness:**
   `tail -1 data/ws01_trace.log data/ws02_trace.log`

10. **[Phase 1] Add Step 1.0 — venv verification:**
    ```bash
    which python3 | grep -q ".venv" || { echo "FATAL: wrong python3"; exit 1; }
    python3 -c "import forex_system; print(forex_system.__file__)"
    ```

11. **[runbook line 27 area] Add hostname assertion:**
    `echo "host=$(hostname) cwd=$(pwd) utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"`

12. **[runbook line 132] Use UTC for backup filename:**
    `cp data/paper_trading_session.log "data/paper_trading_session.log.pre-launch-$(date -u +%Y%m%dT%H%M%SZ).bak"`

13. **[Step 2.3.1 Option 3] Remove `at` option or add atrun-enabled pre-check.**

14. **[Step 2.3.1 Option 2] Add Calendar.app pre-flight: verify "Home" calendar exists and osascript permission granted.**

15. **[Step 2.2.2] Replace manual editor with deterministic sed:**
    ```bash
    sed -i.bak "s|\*(CEO signature required before T=0)\*|huangtm@gmail.com — $(date -u +%Y-%m-%dT%H:%MZ)|" docs/launch/sd6-launch-communication-draft.md
    ```

16. **[Phase 2, all state-changing steps] Add phase-confirmation block at end of each phase** per deploy-checklist-trading rubric.

17. **[Phase 1, Step 2.4.4] Increase initialization wait from 5s to polling loop (up to 60s).**

18. **[Phase 1] Add disk-space check: `df -h data/ | tail -1` — require > 100MB free before cp backup.**

19. **[Step 3.3] Extend FATAL grep to include both kill_switch_audit.log files.**

20. **[Troubleshooting table line 614] Move `ps aux | grep run_paper` from markdown table cell to code block.**

21. **[Document] Add SIGKILL caveat and graceful-shutdown procedure.**

---

## Null-Hypothesis Tester Dissent (append-only)

*Verbatim from nht-null-test-report.yaml `dissent-statement` field. DO NOT paraphrase. DO NOT soften.*

> NHT DISSENT — T=0 DISPATCH RUNBOOK 2026-05-12
>
> The runbook fails the atomic acceptance claim. Seven blocking gaps
> were found, of which the following four are unrecoverable without
> amendment:
>
> D-1. The tmux invocations omit --token and --loop. Both scripts will
>      exit within seconds of spawn; no persistent paper loop will
>      exist. SAXO_TOKEN is not set in the CEO's environment as of
>      this audit. (gap G-1, blocking)
>
> D-2. The SD-5 pre-warning date (2026-07-26) is a Sunday. The actual
>      9-trading-days-remaining date is 2026-07-22 (Wednesday). The
>      runbook conflates calendar arithmetic with trading-day
>      arithmetic. CF-T9 Clause C ratification reminder will fire
>      4 calendar days late and on a non-working day. (gap G-3,
>      blocking)
>
> D-3. Three Phase-3 verifications (account-key parity, dispatch lock
>      held, log growth) accept silence as success. Combined with D-1,
>      the most likely outcome at T=0 — scripts never started — is
>      observationally indistinguishable from "launch succeeded". The
>      CEO will be told the launch is live when nothing is running.
>      (gaps G-5, G-13, G-14, all blocking)
>
> D-4. The post-signing CF-T9 verbatim check uses an 8-word grep
>      substring, not the SHA-256 originally computed. Smart-quote
>      autocorrect, em-dash substitution, or any edit past word 8 of
>      the 156-character clause will pass grep and fail SHA-256
>      without detection. The verbatim-check.yaml is also already
>      stale (claims 105 lines; actual 97). (gap G-9, blocking)
>
> NHT recommends the runbook NOT be ratified for T=0 execution.
> Amendments to address G-1 / G-2 / G-3 / G-5 / G-9 / G-13 / G-14 are
> required. Until amended, T=0 should be deferred.
>
> Per role contract: this dissent is append-only. Subsequent agreement
> by CRO / PM / CTO that the runbook is acceptable does NOT erase
> this dissent from CONSENSUS.md. CEO is to see this verbatim.
>
> — null-hypothesis-tester, 2026-05-12T17:55Z

---

## CRO Blocking Findings (preserved verbatim from cro-risk-review.yaml)

*CRO decision: approve-with-binding-conditions. Three BLOCKING findings reproduced verbatim.*

**CRO BLOCKING FINDING 1 (check_id 2 — Account-key parity gate positive confirmation):**

> status: fail
> observation: "account_key_parity.py:63 returns silently with NO LOG on success (the O_EXCL succeeds, code writes payload, returns). The runbook Step 3.4 verification grep 'account_key' will return EMPTY on success. This is the kill-switch-design rubric anti-pattern: a gate that only logs on failure cannot give positive confirmation of success. The runbook explicitly accepts 'No lines OR lines showing successful parity lock acquisition' — i.e. accepts empty as proof of pass. Empty also means 'gate code path never reached', which is a different failure."
> remediation: "Either (a) modify account_key_parity.py to emit a positive INFO log on successful gate acquisition (preferred — small, surgical, makes the gate testable in prod), OR (b) the runbook must verify parity by checking that data/paper_account_key_lock.json exists AND contains the expected account_key AND was written within the last 60s of script start."

**CRO BLOCKING FINDING 2 (check_id 5 — Kill-switch trigger paths, arming check missing):**

> status: gap
> observation: "KillSwitch instantiated in vt.py:888 and carry_fred.py:828 with per-loop audit log paths (kill_switch_audit.log and kill_switch_audit_cf.log respectively — distinct, no cross-contamination). __post_init__ refuses to start if last audit event was HALTED (lines 158-188), unless KILL_SWITCH_FORCE_RESET=1 is set. Runbook does NOT include a 'kill-switch armed' positive confirmation step. Runbook does NOT include a manual test path (e.g., 'trip a sandbox violation and confirm flatten + halt'). Runbook does NOT pre-check the audit log files for stale HALTED state — if either audit log's last entry is HALTED, the script will RuntimeError on startup. tmux session may then appear 'live' for milliseconds before exit, evading runbook's Phase 3 detection."
> remediation: "Add a Phase 1 pre-flight step: 'Step 1.6 — verify kill-switch audit logs are clean. For each of data/kill_switch_audit.log and data/kill_switch_audit_cf.log, if the file exists, the last line MUST NOT contain new_state=HALTED. If it does, halt the runbook — operator must investigate why the previous session halted before relaunching.' Also add Step 3.6: 'Verify kill-switch status. tmux capture-pane -t paper-vt -p | grep -i \"Kill switch:\" — must show NORMAL or RUNNING state, not TRIGGERED.'"

**CRO BLOCKING FINDING 3 (from body — Step 2.4 --loop missing defeats supervisor purpose):**

> "(i) Step 2.4 invokes scripts WITHOUT --loop and WITHOUT --token; the tmux session 'lives' only for the single-cycle execution then exits — runbook declares 'session alive' based on Phase-3 polling that runs within those seconds, producing a Phase-3 false-positive. Persistent runner is defeated."
> blowup-analog: "Knight Capital, Aug 2012 — kill-switch and supervisor present but invoked incorrectly. Adjacent class: a runbook that invokes a long-running daemon as a single-shot, then declares it 'running' because the tmux session is 'live' (it is — for ~3 seconds before the script exits). Until the supervisor mechanism is verified to keep the script alive through the first 1800s cycle, the run is operationally indistinguishable from no run at all."

---

## Knowledge Gaps Surfaced (routed to skill-gap loop)

*Per pm.md v0.4.10 mandatory step. All knowledge_gaps from wave-2 artifacts are routed to `.fintech-org/skill-gaps.jsonl`.*

| # | Originating Role | Gap Topic | Research Attempted | Suggested Resolution |
|---|-----------------|-----------|-------------------|---------------------|
| KG-1 | ops-engineer | Whether LOCK_EX\|LOCK_NB semantics survive tmux SIGTERM gracefully (specifically: does try/finally block run when tmux session is killed) | false | CRO must review Step 2.4 and confirm lock release behavior post-launch |
| KG-2 | ops-engineer | Exact log line format emitted by account_key_parity gate on success | false | Runbook checks for absence of VIOLATION; if gate passes silently (no log), verification is indirect |
| KG-3 | ops-engineer | Whether drawdown ladder snapshot is logged at startup or only on trigger | false | Runbook checks for drawdown keyword in log; if not present, status is unknown but not a blocker |
| KG-4 | ops-engineer | Exact format of first cycle log entry (varies by strategy; may be different for vt vs carry_fred) | false | Runbook uses conservative check: log must grow by ≥1 line in 10 seconds |
| KG-5 | cro | Behavior of Python's try/finally under tmux kill-session in macOS (does tmux default send SIGTERM or SIGHUP first; does Python convert this to KeyboardInterrupt that runs finally) | false | Operator should prefer 'tmux send-keys C-c' for graceful shutdown |
| KG-6 | cro | Whether data/paper_account_key_lock.json from a prior Saxo token (different account_key) currently exists and would cause parity gate to fail on first run | false | Add to Step 1.5 or 1.6: inspect lock file age and contents; if predates current token, reset before launch |
| KG-7 | cro | Whether KillSwitch.__post_init__ stale-HALTED check would block startup in current state (audit log files from prior dispatch testing) | false | Pre-flight check in Amendment 2 covers this |
| KG-8 | nht | Whether CEO will set SAXO_TOKEN env var as part of pre-flight setup outside this runbook | false | Runbook must be self-contained per the atomic claim; G-1 severity unchanged |
| KG-9 | nht | Exact definition of 'trading day' for CF-T9 Clause C (FX calendar? Saxo Bank business days? NYSE? CME?) | false | CRO ratification required before SD-5 dates can be defended |
| KG-10 | nht | Whether the runbook will be committed to git before T=0 (changes git-status expected output) | false | Either commit or amend expected output |
| KG-11 | nht | Whether CRO's parallel review catches the same gaps; non-overlap risk | false | CONSENSUS surfaces union of both artifacts; CEO sees both |
| KG-12 | nht | Whether existing data/dispatch_lock.flock and lack of data/paper_account_key_lock.json indicate a partially-rolled-back prior session | false | Phase 1 should explicitly inspect these files |

*Routed to: `protocols/skill-gap.md`. Entries appended to `.fintech-org/skill-gaps.jsonl`.*

---

## Decision Posture

The wave-2b reviews (CRO + NHT) surfaced material defects in the runbook. The runbook is NOT auto-ratifiable. Three options are presented to the CEO:

### Option A — Veto the runbook + dispatch ops-engineer wave-2a-v2 (PM recommendation)

Dispatch a new ops-engineer wave to apply the 8 blocking amendments (Amendment List items 1–8). CRO and NHT re-review the amended runbook (wave-2b-v2). The current runbook is archived as DO-NOT-EXECUTE. T=0 is deferred until the amended runbook passes review.

**Rationale:** The blocking findings are clear engineering requirements, not governance judgment calls. Seven independent blockers from two independent reviewers on the same runbook is a clear signal that the runbook needs a revision pass before any execution. Dispatching ops-engineer with the aggregated amendment list (Amendment List items 1–21) produces a runbook that can be reviewed and ratified with confidence. Option A is the fastest path to a runbook the CEO can execute without risk.

### Option B — Ratify runbook as DRAFT (do-not-execute until amended)

The runbook persists in git annotated DO-NOT-EXECUTE. CEO acknowledges the amendment list and commits to applying it manually before execution. No re-review dispatch; CEO owns the amendment burden.

**Rationale:** This is faster in clock time but places the operational amendment burden on the CEO. Given that the blocking amendments include exact commands (Amendment List items 1–8), this is operationally feasible but increases CEO cognitive load during the launch ritual itself — precisely the moment when load should be minimized. Not recommended.

### Option C — Ratify with binding conditions (CEO hand-applies all 7 blocking amendments before executing)

CRO did NOT endorse this path. The CRO's decision was `approve-with-binding-conditions` — the conditions being that amendments 1, 2, 3 are applied before execution. This is operator-burden-heavy and creates no permanent fixed runbook document. Not recommended; CRO's own note: "Without [amendments 1, 2, 3], CEO should not execute Phase 2."

**PM recommendation: Option A.** There is a clear engineering signal that the runbook needs a revision pass. The amendment list is complete and ready for ops-engineer dispatch.

---

## Decisions NOT Made (deferred / out of scope)

- Definition of "trading day" for CF-T9 Clause C (forex calendar vs Saxo Bank business days vs NYSE); requires CRO ratification
- account_key_parity.py positive-log code change (one statement; requires separate SD to stay within no-new-code-in-runbook constraint)
- Whether data/paper_account_key_lock.json from a prior Saxo token needs to be reset (requires CEO to inspect file age and account_key vs current token)
- Kill-switch audit log state inspection at current environment (KG-7); CEO must inspect before T=0 regardless
- Live-account promotion (any step touching the production Saxo account) — explicitly out of scope
- Push to origin/main (51 commits ahead; separate CEO-authorized action)
- Historic-commit account-key literal cleanup (deferred from Wave-10)
- Saxo token revocation (manual user action)
- Wave-11 F-100/F-101 tickets

---

## Assumptions We Are Betting On

- HEAD remains at commit e6aaa43 (Wave-11 ratified) or a named ratified successor
- Both paper scripts use fcntl.flock(LOCK_EX|LOCK_NB) dispatch lock unchanged from Wave-10 (verified by ops-engineer grep)
- Both scripts run on the same host with same data/ directory (single workstation; cross-host would defeat BC-8-LIFT-COND-1)
- macOS is the target OS; tmux 3.5a is available; Calendar.app is available
- CEO has permission to create crontab entries, start tmux sessions, and edit files
- Saxo paper account is provisioned; SAXO_TOKEN will be set before runbook execution (not currently in env)
- T0 = 2026-05-12 (calendar day); 60 trading days = 60 weekdays Mon-Fri (naive; no holiday adjustment until CRO ratifies)

---

## Signatures

| Role | Decision | Timestamp |
|------|----------|-----------|
| pm | authored (wave-4 consensus) | 2026-05-12T00:00:00Z (session) |
| ops-engineer | completed (wave-2a) | 2026-05-12T14:33:00Z |
| cro | approve-with-binding-conditions (wave-2b) | 2026-05-12T18:15:00Z |
| null-hypothesis-tester | dissent (wave-2b) | 2026-05-12T17:55:00Z |

*Note: Principal Reviewer not staffed (operational runbook, not code/algorithm). CTO not staffed (same rationale). All staffed roles signed.*

---

## Cycle-2 Closure (added 2026-05-12T20:30:00Z, post Option-A re-dispatch)

CEO ratified **Option A** at 2026-05-12T18:30:00Z (ratification artifact: `.agent-accountability/ratifications/t0-dispatch-runbook-2026-05-12:phase1:task1.0.yaml`). Wave-2a-v2 + wave-2b-v2 executed.

**Runbook v2:** `docs/launch/t0-dispatch-runbook.md` (773 lines, version-bumped from v1 628 lines). Amendment Log appended with 22 entries.

**Cycle-2 closure verdict:**

| Role | Decision | Blocking closed | Concern closed | New blocking | Artifact |
|------|----------|-----------------|----------------|--------------|----------|
| CRO  | **approve** | 3/3 | 3/5 (2 partial → TODO(v3)) | 0 | `cro-risk-review-cycle2.yaml` |
| NHT  | **survives** | 7/7 | 9/13 (4 TODO(v3)) | 0 (1 non-blocking: tmux idempotency NHT-V2-G1) | `nht-null-test-report-cycle2.yaml` |

**Key closure evidence (v2 runbook line refs):**
- NHT-B1 / CRO-B1 (`--loop` missing): `t0-dispatch-runbook.md:447` — `SAXO_TOKEN=$SAXO_TOKEN python3 ... --loop --interval 1800`; line 27 fatal-exit if SAXO_TOKEN unset
- NHT-B2 (Sunday date): `t0-dispatch-runbook.md:323` — explicit "DO NOT execute until CRO ratifies trading-day calendar"; line 325 escalates to CRO
- CRO-B2 / NHT-B3 (silence-is-success): `t0-dispatch-runbook.md:611` — `json.load` positive parity; `:534` live `lsof` lock check; `:588` heartbeat mtime ≤300s
- CRO-B3 (kill-switch arming): `t0-dispatch-runbook.md:154-163` — Step 1.6 loops both audit logs, FATAL exits on HALTED
- NHT-B4 (hash check): `t0-dispatch-runbook.md:295` — `hashlib.sha256` + `assert h == exp`
- NHT-B5 (`at` daemon): `t0-dispatch-runbook.md:403` — Option 3 REMOVED
- NHT-B6 (zsh glob): `t0-dispatch-runbook.md:117` — `find data -maxdepth 1 -name '*.flock' -mmin +60`

**Cycle-1 dissents persist append-only.** Both NHT cycle-1 D-1..D-4 and CRO cycle-1 risk-architecture findings remain in their dissent artifacts under `.agent-accountability/dissents/`. NHT cycle-2 explicitly states "cycle-1 dissent stands as the append-only record; v2 closures noted".

**Residual TODO(v3) items (concern-level, non-blocking for T=0):**
1. CRO concern #5 — heartbeat file wire-up not empirically confirmed in scripts (fallback to ws01/ws02_trace.log documented)
2. CRO concern #16 — per-phase verbal-confirmation block (Gawande structure; single-CEO degraded form OK for v2)
3. NHT-V2-G1 (NEW) — tmux idempotency: `tmux new-session -d` errors if session exists; recommend `has-session` guard
4. Ops-engineer self-flagged amendment #14 (Calendar.app pre-flight) and #20 (troubleshooting table format)
5. CRO long-term SD — patch `src/forex_system/risk/account_key_parity.py:63` to emit `logger.info` on success (separate dispatch; runbook works around with positive json.load check)

**Status:** **cycle-2-closed-ready-for-final-ratification**. Runbook v2 is now safe to execute at T=0 per CRO + NHT cycle-2 sign-off, subject to:
- SAXO_TOKEN exported in CEO's env before any execution
- CRO trading-day calendar definition ratified before SD-5 reminder is set (runbook will halt at Step 2.3 until this lands)
- Kill-switch audit-log files pre-flight check passes (Phase-1 Step 1.6 enforces)

---

## Ratification Prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise \<X\>)**

*Suggested revise targets:*
- `revise option-b` — if CEO wishes to own the amendment burden manually rather than re-dispatch ops-engineer
- `revise option-c` — if CEO wishes to proceed with CRO binding conditions (CRO did not endorse)
- `revise amendment-list` — if CEO wants to narrow or re-order the amendment backlog
- `revise nht-block` — to discuss the NHT dissent specifically with the org

---

*Sources: `.fintech-org/artifacts/2026-05-12T-t0-dispatch-runbook/pm-acceptance-criteria.yaml`, `ops-engineer-runbook-result.yaml`, `cro-risk-review.yaml`, `nht-null-test-report.yaml`; `docs/launch/t0-dispatch-runbook.md`; `~/.claude/skills/fintech-org/protocols/consensus.md`; `~/.claude/skills/fintech-org/roles/pm.md`*
*web_research_conducted: false | no-capital-instruction: true*
