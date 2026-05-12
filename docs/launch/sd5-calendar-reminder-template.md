# SD-5 Calendar Reminder Template — CF-T9 Clause C 60-Trading-Day Deadline

**Status:** TEMPLATE — set actual reminder at T=0 (day of first paper bar)
**Authorization:** [CONSENSUS_2026-05-10_paper_launch_authorization.md](../decisions/CONSENSUS_2026-05-10_paper_launch_authorization.md) SD-5
**Drafted:** 2026-05-11 by /fintech-org orchestrator (under `--no-ceo` continuation mode)
**Operator at T=0:** CEO huangtm@gmail.com

---

## What this reminder is for

CONSENSUS_2026-05-02 Section 3 Condition 2 (NHT Wave-5 Round-3 co-sign, binding):

> "Clause C must be ratified within 60 trading days of paper launch, or a mandatory NHT CF-T9 re-review is triggered."

If the 60-trading-day window expires without explicit Clause C ratification, an NHT re-review of the entire CF-T9 amendment is automatically required. The calendar reminder exists so that the deadline does not pass silently.

---

## Trading-day → calendar-day conversion

60 trading days ≈ 12 calendar weeks ≈ **84-90 calendar days** depending on holidays. The forex market trades Sun 22:00 UTC → Fri 22:00 UTC (5 trading days per week). Public holidays in major sessions (London, NY, Tokyo) reduce effective volume but the market does NOT close on most of them.

**Practical conversion:** `T0 + 90 calendar days` is a safe upper bound; `T0 + 84 days` is the tight estimate. Recommend setting the reminder for `T0 + 84 days` AND a second reminder for `T0 + 75 days` as a 9-day pre-warning.

**Reminder targets (calendar dates relative to T=0):**

| Reminder | Calendar offset | Purpose |
|---|---|---|
| Pre-warning | T0 + 75 days | "9 trading days remaining — start drafting Clause C ratification" |
| Hard deadline | T0 + 84 days | "Clause C must be ratified or NHT re-review triggers TODAY" |

---

## Mechanism options (all 3 confirmed available by ops-engineer 2026-05-11)

### Option 1 — `crontab` (recommended for headless / persistent)

Set persistent cron entries that fire even if you reboot. Both reminders defined; replace `<DATE>` placeholders at T=0.

```bash
# At T=0, compute the dates:
T0=$(date +%Y-%m-%d)  # e.g., "2026-05-11"
T_PREWARN=$(date -v+75d +%Y-%m-%d)   # macOS BSD date
T_DEADLINE=$(date -v+84d +%Y-%m-%d)

# Pre-warning at 09:00 on T0+75
(crontab -l 2>/dev/null; echo "0 9 $(date -j -f %Y-%m-%d $T_PREWARN +'%-d %-m') * * osascript -e 'display notification \"CF-T9 Clause C: 9 trading days remaining\" with title \"Forex paper-launch deadline\"'") | crontab -

# Hard deadline at 09:00 on T0+84
(crontab -l 2>/dev/null; echo "0 9 $(date -j -f %Y-%m-%d $T_DEADLINE +'%-d %-m') * * osascript -e 'display notification \"CF-T9 Clause C DEADLINE TODAY — NHT re-review triggers\" with title \"Forex paper-launch deadline\" sound name \"Submarine\"'") | crontab -

# Verify
crontab -l | grep CF-T9
```

**Note:** cron entries with `osascript` require the user to be logged in at the firing time. If you're not at the machine, use option 2 (calendar) instead.

### Option 2 — macOS `calendar` app (Cal.app via AppleScript)

Persistent across logins, syncs to iCloud, fires on phone too. Recommended for round-the-clock visibility.

```bash
# Compose the event-creation AppleScript at T=0 (templates ready; replace dates):
osascript << 'EOF'
tell application "Calendar"
    tell calendar "Home"   -- or your preferred calendar name
        make new event with properties { \
            summary: "CF-T9 Clause C: 9 trading days remaining", \
            start date: (current date) + (75 * days), \
            end date: (current date) + (75 * days) + (15 * minutes), \
            description: "CF-T9 Clause C must be ratified within 9 trading days or NHT re-review triggers. See docs/decisions/CONSENSUS_2026-05-10_paper_launch_authorization.md SD-5." \
        }
        make new event with properties { \
            summary: "CF-T9 Clause C DEADLINE — NHT re-review triggers TODAY", \
            start date: (current date) + (84 * days), \
            end date: (current date) + (84 * days) + (30 * minutes), \
            description: "CF-T9 Clause C ratification deadline. If not ratified by EOD, NHT re-review is mandatory per CONSENSUS_2026-05-02 Section 3 Condition 2." \
        }
    end tell
end tell
EOF
```

### Option 3 — `at` (one-shot, fires once and forgets)

Simplest but no GUI notification — `at` runs commands in the background. Best paired with a script that sends you an email or pages a chat channel.

```bash
# Pre-warning
echo "echo 'CF-T9 Clause C: 9 trading days remaining' | mail -s 'Forex deadline pre-warning' huangtm@gmail.com" | at 09:00 $(date -v+75d +%m/%d/%Y)

# Hard deadline
echo "echo 'CF-T9 Clause C DEADLINE TODAY — NHT re-review triggers' | mail -s 'Forex deadline TODAY' huangtm@gmail.com" | at 09:00 $(date -v+84d +%m/%d/%Y)

# Verify
atq
```

**Note:** `at` daemon must be running (`sudo launchctl load -F /System/Library/LaunchDaemons/com.apple.atrun.plist` on macOS). `mail` requires SMTP setup. Most fragile of the three options.

---

## Recommendation

**Option 2 (calendar app)** for primary durability + cross-device visibility, with **Option 1 (cron)** as a redundant local-machine reminder. Execute both at T=0.

---

## SD-5 closure (operator action at T=0)

After setting the reminder(s), record in the launch-day ops log:

```bash
cat >> docs/launch/sd6-launch-comm-verbatim-check.yaml << EOF

sd5_calendar_reminder_set_at_T0:
  t0_date: "<YYYY-MM-DD>"
  pre_warning_date: "<YYYY-MM-DD>"   # T0 + 75 calendar days
  hard_deadline_date: "<YYYY-MM-DD>"  # T0 + 84 calendar days
  mechanism_chosen: "<crontab|calendar|at|multiple>"
  set_at: "<ISO 8601 timestamp>"
  set_by: huangtm@gmail.com
  verification_command_output: "<paste output of crontab -l | grep CF-T9 OR Calendar query OR atq>"
EOF
```

This closes SD-5 governance gate.

---

## Cross-references

- CONSENSUS_2026-05-10 SD-5 acceptance criterion: `criteria[4].done_when`
- NHT binding source: `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml` lines 67-70
- Original preflight item 9: CONSENSUS_2026-05-03_preflight_closure.md Section 8e
- CF-T9 amendment spec: `references/pre-registrations/carry_fred.md`
