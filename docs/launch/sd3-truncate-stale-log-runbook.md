# SD-3 Runbook — Stale-Log Disposition at T=0

**Status:** DRAFT runbook — do NOT execute until T=0 (day of first paper bar)
**Authorization:** [CONSENSUS_2026-05-10_paper_launch_authorization.md](../decisions/CONSENSUS_2026-05-10_paper_launch_authorization.md) SD-3
**Drafted:** 2026-05-11 by /fintech-org orchestrator (under `--no-ceo` continuation mode)
**Executor:** CEO huangtm@gmail.com (manual step; orchestrator is staging, not executing)

---

## Decision context

`data/paper_trading_session.log` exists from before the current run:

- **Path:** `/Users/huangtm/Projects/forex-trading-system/data/paper_trading_session.log`
- **Current size:** 26 KB, 269 lines (verified 2026-05-11)
- **Current mtime:** 2026-05-06 23:12 (Wave-10 commit day; activity post-2026-04-26)
- **Originally flagged in:** CONSENSUS_2026-05-03_preflight_closure.md Section 5 at 122 lines / mtime 2026-04-26. State has changed since flagging.

The CONSENSUS_2026-05-10 ratified SD-3 with the 3 disposition options below. SD-3 done_when requires CEO to choose one before first paper bar.

**Note on logger configuration:** Both paper scripts use `RotatingFileHandler(path, maxBytes=10*1024*1024, backupCount=5)` (10 MB rotation, 5 backups) — confirmed at `scripts/run_paper_trading_vt.py:220` and `scripts/run_paper_trading_carry_fred.py:235`. `RotatingFileHandler` APPENDS by default and rotates on size threshold; it does NOT truncate or clear on startup. The "verify-startup-clears" SD-3 option (b) is a misnomer with the current handler — there is no startup-clear behavior to verify. If option (b) is preferred, the handler choice would need to change to `mode='w'` or explicit pre-startup truncate.

---

## Option (a) — TRUNCATE (recommended per CONSENSUS context)

Cleanest cutover. Pre-launch state is discarded; first paper bar writes to a fresh file.

**Execution command (do at T=0, before starting paper scripts):**

```bash
# Pre-flight: confirm git HEAD is at the authorized commit
cd /Users/huangtm/Projects/forex-trading-system
git rev-parse HEAD  # expect 747a6ad or a successor

# Backup the stale log to a timestamped name (operator-discretion; data IS irreversibly removed by truncate)
cp data/paper_trading_session.log "data/paper_trading_session.log.pre-launch-$(date +%Y%m%dT%H%M%S).bak"

# Truncate
: > data/paper_trading_session.log
# OR equivalent: truncate -s 0 data/paper_trading_session.log

# Verify
wc -l data/paper_trading_session.log   # expect 0
ls -la data/paper_trading_session.log  # confirm 0-byte
```

**Verification predicate (CONSENSUS done_when):** `wc -l data/paper_trading_session.log` returns 0 immediately before first paper bar execution.

---

## Option (b) — VERIFY STARTUP-CLEARS (NOT recommended without code change)

This option presupposes that the logging configuration truncates or rotates on startup. **The current code does not do this.** `RotatingFileHandler` opens in append mode and rotates only at the 10 MB size threshold.

If you prefer this option, a code change is required first:
- Change handler to `RotatingFileHandler(path, maxBytes=10*1024*1024, backupCount=5, mode='w')` at both `run_paper_trading_vt.py:220` and `run_paper_trading_carry_fred.py:235` (truncate on first open)
- This is a Wave-11 ticket, not a runbook step; it requires a separate dispatch + ratification

**Recommendation:** if (b) is preferred for any reason, defer to Wave-11. Do not select (b) on the current code.

---

## Option (c) — ACCEPT-MERGED

The 269-line pre-launch content remains. First paper bar appends after line 269. Audit trail is mixed pre/post-launch.

**Execution:** no action. Skip the truncate step entirely.

**Operational consequence:** log analyzers / dashboards must be aware that line numbers <270 are pre-launch noise. The RotatingFileHandler will eventually rotate when the file exceeds 10 MB and 5 backups will accumulate.

**Recommendation:** acceptable only if a downstream consumer specifically needs the pre-launch content. Otherwise option (a) is cleaner.

---

## SD-3 closure (operator action at T=0)

Whichever option is chosen, record the disposition in the launch-day ops log:

```bash
# After executing the chosen option (or skipping for option c):
cat >> docs/launch/sd6-launch-comm-verbatim-check.yaml << 'EOF'

sd3_disposition_executed_at_T0:
  option_chosen: "<a|b|c>"
  executed_at: "<ISO 8601 timestamp>"
  pre_disposition_line_count: 269
  post_disposition_line_count: <observed>
  backup_file: "<path>"  # only for option (a)
  executed_by: huangtm@gmail.com
EOF
```

This closes SD-3 governance gate. The paper loop can then start.

---

## Cross-references

- CONSENSUS_2026-05-10 SD-3 acceptance criterion: `criteria[2].done_when`
- Original preflight finding: CONSENSUS_2026-05-03_preflight_closure.md Section 5 / Section 12c
- Logger configuration: `scripts/run_paper_trading_vt.py:220`, `scripts/run_paper_trading_carry_fred.py:235`
- Wave-7 closure (RotatingFileHandler implementation): CONSENSUS_2026-05-03_wave7_closure.md
