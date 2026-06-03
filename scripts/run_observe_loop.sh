#!/bin/sh
# Observe-only momentum-EURUSD canary — CONTINUOUS loop starter (launchd KeepAlive / bg).
#
# Runs the canary in --loop mode: one long-running process that observes each cycle
# (read-only; no orders possible — ReadOnlySaxoClient) and appends to
# data/paper_observe_momentum_eurusd.jsonl on each NEW closed daily bar. Use a
# LONG-RUNNING process (NOT single-shot cron): the script's new-bar dedup is
# in-process, so repeated single-shot invocations would append duplicate bars.
# Under launchd use KeepAlive (restart on exit), NOT StartInterval.
#
# Scope (HONEST): accumulates the live SIGNAL/DECISION series only. It does NOT
# calibrate the cost-reconciliation tolerance and does NOT confirm the Saxo marking
# convention — both need real fills (see run_observe_momentum_eurusd.py docstring).
#
# Token: read at runtime from $SAXO_TOKEN_FILE (default ~/.saxo_sim_token); NEVER
# stored in this repo. Saxo SIM tokens are short-lived (~24h) — refresh the file to
# keep the loop alive; on a missing token this exits non-zero and logs it.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TOKEN_FILE="${SAXO_TOKEN_FILE:-$HOME/.saxo_sim_token}"
LOG="${OBSERVE_LOG:-$HOME/Library/Logs/forex-observe.log}"
PY="${PYTHON:-python3}"
INTERVAL="${INTERVAL:-3600}"
mkdir -p "$(dirname "$LOG")"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
if [ ! -f "$TOKEN_FILE" ]; then
  echo "$(ts) ERROR no token file at $TOKEN_FILE — refresh the SIM token to resume" >> "$LOG"
  exit 1
fi
cd "$REPO"
SAXO_TOKEN="$(cat "$TOKEN_FILE")" "$PY" scripts/run_observe_momentum_eurusd.py \
    --timeframe daily --loop --interval "$INTERVAL" >> "$LOG" 2>&1
