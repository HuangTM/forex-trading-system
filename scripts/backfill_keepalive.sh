#!/bin/bash
# Durable, single-instance Dukascopy 1h backfill runner for launchd.
#
# Owned by the LaunchAgent com.forex.backfill (see ~/Library/LaunchAgents/).
# The underlying backfill is resumable (atomic monthly chunks, skip-existing),
# so re-invocation after a kill/reboot just continues. launchd guarantees ONE
# instance per label, which is essential: concurrent pulls trip Dukascopy's
# concurrency tarpit. workers=1 is the gentlest footprint under the IP throttle.
#
# Exit contract (paired with KeepAlive>SuccessfulExit=false in the plist):
#   exit 1  -> backfill incomplete; launchd restarts after ThrottleInterval.
#   exit 0  -> all 12 *_1h.parquet assembled; launchd stops (job done).
#
# Teardown:
#   launchctl bootout gui/$(id -u)/com.forex.backfill
#   rm ~/Library/LaunchAgents/com.forex.backfill.plist
set -u
PROJ="/Users/huangtm/Projects/forex-trading-system"
PY="/opt/homebrew/bin/python3"
PAIRS="EURUSD,GBPUSD,USDJPY,EURJPY,AUDUSD,USDCAD,NZDUSD,EURGBP,AUDJPY,CADJPY,GBPJPY,NZDJPY"
cd "$PROJ" || exit 1
mkdir -p logs

echo "=== keepalive run start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> logs/backfill_launchd.log

# caffeinate -i prevents *idle* system sleep for the lifetime of the wrapped
# python, so the pull is not suspended mid-fetch during overnight idle. It is
# scoped to this process only — when the backfill exits (done or killed), the
# assertion drops and normal sleep resumes. No persistent power-setting change.
caffeinate -i "$PY" scripts/backfill_dukascopy_all.py \
  --pairs "$PAIRS" --start-year 2021 --end 2026-01-01 \
  --workers 1 --timeout 8 --request-delay 0.1 \
  >> logs/backfill_launchd.log 2>&1

n=$(ls data/processed/*_1h.parquet 2>/dev/null | wc -l | tr -d ' ')
if [ "${n:-0}" -ge 12 ]; then
  echo "=== ALL 12 PAIRS DONE ($n/12) — keepalive exit 0; launchd will stop $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> logs/backfill_launchd.log
  exit 0
fi
echo "=== incomplete ($n/12) — keepalive exit 1; launchd restarts after throttle $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> logs/backfill_launchd.log
exit 1
