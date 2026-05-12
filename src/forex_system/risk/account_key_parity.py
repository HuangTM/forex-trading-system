"""Startup account-key parity gate shared by all paper-trading loops.

Extraced from scripts/run_paper_trading_vt.py and
scripts/run_paper_trading_carry_fred.py (Wave-11 W11-1).
"""

from __future__ import annotations

import json as _json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

__all__ = (
    "ACCOUNT_KEY_LOCK_PATH",
    "assert_account_key_parity",
    "reset_account_key_lock",
)

ACCOUNT_KEY_LOCK_PATH: Final[str] = "data/paper_account_key_lock.json"

logger = logging.getLogger(__name__)


def assert_account_key_parity(
    account_key: str,
    *,
    loop_name: str,
    lock_path: str = ACCOUNT_KEY_LOCK_PATH,
) -> None:
    """HIGH-2: Startup account_key parity gate (atomic O_EXCL acquire).

    Attempts an atomic O_CREAT|O_EXCL open to write this process's account_key
    to the shared lock file on first call.  If the file already exists
    (FileExistsError), re-reads and compares; raises SystemExit(1) on mismatch.

    Uses O_CREAT|O_EXCL (not Path.exists()+write_text) so two simultaneous
    launches cannot both silently succeed when pointing at divergent accounts.

    To reset: run with --reset-account-key-lock NEW_KEY --confirm-account-reset
    (see main()).  Do NOT delete the lock file manually — operator deletion is
    a documented bypass that bypasses the gate entirely under stress.

    Must be called before any order-dispatch path is reachable.
    """
    p = Path(lock_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = _json.dumps({
        "account_key": account_key,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    try:
        # Atomic create: raises FileExistsError if another process beat us here.
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, payload.encode())
        finally:
            os.close(fd)
        return  # We created the lock — we are first; proceed normally.
    except FileExistsError:
        pass  # Lock already exists — fall through to parity check.
    locked = _json.loads(p.read_text()).get("account_key", "")
    if locked != account_key:
        msg = (
            f"ACCOUNT_KEY_PARITY_VIOLATION: {loop_name} has account_key={account_key!r} "
            f"but lock file records {locked!r}. "
            "Both paper loops must target the same Saxo paper account. "
            "To reset: pass --reset-account-key-lock NEW_KEY --confirm-account-reset "
            "and restart — do NOT delete the lock file manually."
        )
        print(f"FATAL: {msg}")
        logger.critical(
            "account_key_parity_violation",
            extra={
                "event": "ACCOUNT_KEY_PARITY_VIOLATION",
                "account_key": account_key,
                "locked_key": locked,
                "loop_name": loop_name,
            },
        )
        sys.exit(1)


def reset_account_key_lock(new_key: str, *, lock_path: str = ACCOUNT_KEY_LOCK_PATH) -> None:
    """Atomically replace the account-key lock with a new key.

    Called only when both --reset-account-key-lock and --confirm-account-reset
    are passed.  Prints the old and new keys, replaces atomically, then exits.
    This is the ONLY sanctioned way to change the locked account key.
    """
    p = Path(lock_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    old_key = "NONE (no lock file)"
    if p.exists():
        try:
            old_key = _json.loads(p.read_text()).get("account_key", "UNKNOWN")
        except Exception:
            old_key = "UNREADABLE"
    print("  Resetting account-key lock:")
    print(f"    OLD key: {old_key!r}")
    print(f"    NEW key: {new_key!r}")
    payload = _json.dumps({
        "account_key": new_key,
        "ts": datetime.now(timezone.utc).isoformat(),
        "reset_by": "cli_reset",
    })
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".aklock_reset_")
    try:
        os.write(fd, payload.encode())
        os.close(fd)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f"  Lock reset successfully to {new_key!r}. Exiting.")
    sys.exit(0)
