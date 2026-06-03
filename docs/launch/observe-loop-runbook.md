# Observe-only momentum-EURUSD canary — loop runbook

Ratified under `docs/decisions/CONSENSUS_2026-06-01_paper_launch_acceleration.md`. The
observe canary is a **read-only shakedown**, not alpha and not capital. It exercises the
paper READ path (Saxo SIM connectivity → chart fetch → momentum signal → account-equity
read) and appends a backtest-faithful signal/decision series to
`data/paper_observe_momentum_eurusd.jsonl` on each NEW closed daily bar.

## Scope — what the loop does and does NOT do (be honest about this)

- **Does:** accumulate the live signal/decision series + the SIM account-equity reading.
- **Does NOT:** route any order (structurally impossible — `ReadOnlySaxoClient`).
- **Does NOT:** calibrate the cost-reconciliation tolerance, and does NOT confirm the
  Saxo TotalValue marking convention. **Both need real fills** — i.e. the full paper
  runner placing SIM orders, which is a separate, CEO-authorized step beyond observe-only.
- **Does NOT:** prove edge. Per the firm's ratified audit + NHT dissent, momentum-EURUSD
  is unvalidated (its OOS equity is missing). A running loop = the pipe is connected.

## Token

Place a Saxo **SIM** developer token (24h TTL) at `~/.saxo_sim_token` (chmod 600, kept
OUTSIDE the repo — never commit it):

```sh
printf '%s' '<SIM_TOKEN>' > ~/.saxo_sim_token && chmod 600 ~/.saxo_sim_token
```

The token self-expires (~24h). To keep the loop alive across days, refresh this file;
on a missing/expired token the wrapper logs an error and exits non-zero.

## Run it

**Continuous loop (the correct mode — one long-running process; in-process new-bar
dedup):**
```sh
sh scripts/run_observe_loop.sh        # --loop; reads ~/.saxo_sim_token; INTERVAL=3600 default
```
> Do NOT drive this single-shot from cron/StartInterval: the script's new-bar dedup is
> in-process, so repeated single-shot runs append duplicate bars. Use one long-running
> `--loop` process (foreground, `&`/`nohup` background, or launchd KeepAlive below).

**One observation (manual check, no loop):**
```sh
SAXO_TOKEN="$(cat ~/.saxo_sim_token)" python3 scripts/run_observe_momentum_eurusd.py --timeframe daily
```

**Durable (opt-in macOS LaunchAgent — operator installs; persistence is your call):**
```sh
cp deploy/launchd/com.htm.forex-observe.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.htm.forex-observe.plist   # hourly, runs at load
# disable:
launchctl unload ~/Library/LaunchAgents/com.htm.forex-observe.plist
rm ~/Library/LaunchAgents/com.htm.forex-observe.plist
```

Logs (outside the repo): `~/Library/Logs/forex-observe.log` (and `.launchd.{out,err}`).

## Cadence reality

Daily timeframe → ~1 new entry/day. A 24h token therefore yields ~1 observation before
it must be refreshed. Accumulating a multi-week series requires daily token refresh.
This is a data-gathering shakedown, not a fixed-N calibration.
