"""CRO Wave-4 sizing helpers for Bet #1 (carry_fred / BoJ-divergence regime).

The vol_target_carry paper loop (scripts/run_paper_trading_vt.py) is a
single-pair vt strategy and does NOT dispatch Bet #1 trades directly.
These helpers are provided as typed stubs so that Wave-5 Round 2+
multi-strategy variants can import regime-aware sizing without reimplementing
the CRO binding constraints.

CRO Wave-4 binding constraints sourced from:
    .fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/
    cro-bet1-sizing-revision.yaml

    BC-1 (regime-inactive no-trade): size_multiplier = 0.0 when BoJ-divergence
          regime flag is FALSE; zero positions permitted when regime is inactive.
    BC-2 (regime-active sizing): size_multiplier = 0.25 (product of Phase-1
          envelope 0.5 × 0.5 concentration haircut) when regime flag is TRUE.
    BC-3 (CF-T9 pre-launch gate): CF-T9 monitor must be deployed and emitting a
          heartbeat (≥1 per 5-min window) before any trade is placed.
    BC-4 (CF-T9 cold-start gate): CF-T9 must have emitted ≥10 regime-flag
          readings, with BOTH TRUE and FALSE observed, before first trade.
    BC-5 (CF-T9 heartbeat failure): If CF-T9 emits no heartbeat for
          >5 consecutive minutes, all NEW Bet #1 trades are halted.

DO NOT modify these constants without a formal CONSENSUS amendment and
co-sign from NHT + HoQR.

Clock discipline: time.monotonic() for elapsed measurements; file mtime
from os.stat() for CF-T9 status file freshness (wall-clock — intentional;
we are comparing the file's creation time against wall-clock to detect
stale external artifacts).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("bet1_sizing")

# ---------------------------------------------------------------------------
# CRO Wave-4 binding constants — DO NOT CHANGE without governance amendment
# ---------------------------------------------------------------------------

# BC-1 / BC-2: size multipliers sourced from cro-bet1-sizing-revision.yaml
BET1_SIZE_MULTIPLIER_REGIME_INACTIVE: float = 0.0
BET1_SIZE_MULTIPLIER_REGIME_ACTIVE: float = 0.25  # 0.5 envelope × 0.5 haircut

# BC-3 / BC-5: CF-T9 heartbeat window — if file mtime is older than this,
# treat as stale and return False (fail-safe to halt)
CF_T9_HEARTBEAT_MAX_AGE_SECONDS: float = 300.0  # 5 minutes

# BC-4: minimum regime readings before first trade is permitted
CF_T9_MIN_REGIME_READINGS: int = 10

# Default path for the CF-T9 status file emitted by monitor_regime_triggers.py
CF_T9_STATUS_DEFAULT_PATH: str = "data/cf_t9_status.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bet1_size_multiplier(regime_active: bool) -> float:
    """Return the CRO Wave-4 binding size multiplier for Bet #1.

    Args:
        regime_active: True if BoJ-divergence regime is currently active
            AND the CF-T9 monitor is healthy (call ``regime_active_status``
            to obtain this value).

    Returns:
        0.25 if regime_active is True (Phase-1 0.5x × 0.5 concentration
        haircut per BC-2), or 0.0 if regime_active is False (hard zero —
        no trades permitted when regime is inactive per BC-1).

    Note: The returned multiplier is a *maximum* — the JPY-correlation cap
    (BC-8, inherited: ≤15% of total book notional) may constrain effective
    size further when other JPY strategies are simultaneously active.
    """
    if regime_active:
        multiplier = BET1_SIZE_MULTIPLIER_REGIME_ACTIVE
    else:
        multiplier = BET1_SIZE_MULTIPLIER_REGIME_INACTIVE

    logger.info(
        "bet1_size_multiplier",
        extra={
            "event": "BET1_SIZE_MULTIPLIER",
            "regime_active": regime_active,
            "size_multiplier": multiplier,
            "bc_ref": "BC-1/BC-2 cro-bet1-sizing-revision.yaml",
        },
    )
    return multiplier


def regime_active_status(
    cf_t9_status_path: str = CF_T9_STATUS_DEFAULT_PATH,
) -> bool:
    """Read CF-T9 monitor status and return True only if:

      1. The status file exists (BC-3: CF-T9 must be deployed).
      2. The file mtime is within CF_T9_HEARTBEAT_MAX_AGE_SECONDS of now
         (BC-5: heartbeat failure → halt new trades; fail-safe to False).
      3. The file's ``regime_active`` field is True (BoJ-divergence active).
      4. The file's ``n_readings`` is ≥ CF_T9_MIN_REGIME_READINGS AND both
         True and False regime states have been observed (BC-4: cold-start gate).

    Returns False (= no Bet #1 trades) in all failure/stale/missing cases —
    the system is designed to fail SAFE.

    Args:
        cf_t9_status_path: Path to the JSON file emitted by
            ``scripts/monitor_regime_triggers.py``.  Resolved relative to the
            working directory of the caller.

    Structured log keys emitted on every call:
        event, file_path, file_exists, file_age_seconds, regime_active,
        n_readings, both_states_observed, result, block_reason (if blocked)
    """
    path = Path(cf_t9_status_path)
    log_fields: dict = {
        "event": "CF_T9_STATUS_CHECK",
        "file_path": str(path),
    }

    # Check 1: file existence (BC-3)
    if not path.exists():
        log_fields.update({
            "file_exists": False,
            "result": False,
            "block_reason": "CF_T9_STATUS_FILE_MISSING",
        })
        logger.warning("CF-T9 status file missing — bet1 regime_active=False", extra=log_fields)
        return False

    log_fields["file_exists"] = True

    # Check 2: file freshness (BC-5 heartbeat failure)
    try:
        mtime = os.stat(path).st_mtime
        file_age_seconds = time.time() - mtime
    except OSError as exc:
        log_fields.update({
            "result": False,
            "block_reason": f"CF_T9_STATUS_STAT_ERROR:{exc}",
        })
        logger.warning("CF-T9 status file stat failed — bet1 regime_active=False", extra=log_fields)
        return False

    log_fields["file_age_seconds"] = file_age_seconds

    if file_age_seconds > CF_T9_HEARTBEAT_MAX_AGE_SECONDS:
        log_fields.update({
            "result": False,
            "block_reason": (
                f"CF_T9_HEARTBEAT_STALE:{file_age_seconds:.1f}s"
                f">{CF_T9_HEARTBEAT_MAX_AGE_SECONDS}s"
            ),
        })
        logger.warning(
            "CF-T9 status file stale (%.1fs > %.1fs) — bet1 regime_active=False",
            file_age_seconds,
            CF_T9_HEARTBEAT_MAX_AGE_SECONDS,
            extra=log_fields,
        )
        return False

    # Check 3+4: parse file content
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        log_fields.update({
            "result": False,
            "block_reason": f"CF_T9_STATUS_PARSE_ERROR:{exc}",
        })
        logger.warning("CF-T9 status file parse error — bet1 regime_active=False", extra=log_fields)
        return False

    regime_flag = bool(payload.get("regime_active", False))
    n_readings = int(payload.get("n_readings", 0))
    seen_true = bool(payload.get("seen_regime_active_true", False))
    seen_false = bool(payload.get("seen_regime_active_false", False))
    both_states = seen_true and seen_false

    log_fields.update({
        "regime_active": regime_flag,
        "n_readings": n_readings,
        "both_states_observed": both_states,
    })

    # BC-4: cold-start gate — both states must have been observed, ≥10 readings
    if n_readings < CF_T9_MIN_REGIME_READINGS:
        log_fields.update({
            "result": False,
            "block_reason": (
                f"CF_T9_COLD_START_GATE:n_readings={n_readings}"
                f"<{CF_T9_MIN_REGIME_READINGS}"
            ),
        })
        logger.warning(
            "CF-T9 cold-start gate not cleared (n_readings=%d < %d) — bet1 regime_active=False",
            n_readings,
            CF_T9_MIN_REGIME_READINGS,
            extra=log_fields,
        )
        return False

    if not both_states:
        log_fields.update({
            "result": False,
            "block_reason": "CF_T9_COLD_START_GATE:both_states_not_observed",
        })
        logger.warning(
            "CF-T9 cold-start gate not cleared (both states not seen) — bet1 regime_active=False",
            extra=log_fields,
        )
        return False

    # All gates cleared — return the actual regime flag
    log_fields["result"] = regime_flag
    log_level = logging.INFO if regime_flag else logging.DEBUG
    logger.log(
        log_level,
        "CF-T9 status check complete",
        extra=log_fields,
    )
    return regime_flag
