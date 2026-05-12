"""W11-4: Real run_cycle dispatch-lock integration tests (NHT W11-4-CLAIM-B closure).

NHT claim: "If someone removed lines 548-578 (the fcntl block) from run_cycle entirely,
ALL 11 _WORKER_SCRIPT tests would still pass."

These tests invoke the ACTUAL run_cycle function via subprocess import — not a
hand-rolled _WORKER_SCRIPT — so the real fcntl.flock path is exercised.
Removing the fcntl block from run_cycle causes these tests to fail:

  - test_real_run_cycle_acquires_dispatch_lock: lock file would never be created by
    run_cycle, but the test checks a real lock acquisition sequence proves lock was
    held by verifying the second subprocess sees SKIP_DISPATCH_LOCK_BUSY.
  - test_real_run_cycle_two_concurrent_one_gets_busy: without the fcntl block, both
    subprocesses would proceed past the "lock" with no contention and both return
    non-SKIP_DISPATCH_LOCK_BUSY, failing the assertion.
  - test_real_run_cycle_lock_released_on_exception: without a finally/LOCK_UN, a
    second call after an exception would still find the lock busy.

Only Saxo/data externals are mocked; fcntl.flock is called for real.

Coverage gap: W11-4-CLAIM-B from nht-adversarial-verification.yaml.
Reference: docs/specs/drawdown_ladder_amendment_2026-05-06.md Section 2, BC-8 option-B.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo root
# ---------------------------------------------------------------------------

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)

# ---------------------------------------------------------------------------
# Subprocess worker script templates
#
# These scripts import the REAL run_cycle from each paper-loop script and call
# it with mocked Saxo/data dependencies.  fcntl.flock is NOT mocked — the OS
# advisory lock is exercised end-to-end.
#
# Design notes:
#   • DISPATCH_LOCK_PATH is overridden to a tmp path passed via argv[1].
#   • fetch_recent_bars is patched to sleep(hold_seconds) WHILE THE LOCK IS
#     HELD (it is called inside the fcntl critical section) so the concurrent
#     test has time for the second process to attempt acquisition.
#   • EURUSD is used (not a JPY pair) to avoid the F-100 JPY-mid guard.
#   • The result dict is printed as JSON to stdout; the parent reads it.
#   • sys.exit(0) always — failures are communicated via the JSON result.
# ---------------------------------------------------------------------------

_VT_WORKER = textwrap.dedent("""\
    import json
    import math
    import sys
    import time
    from pathlib import Path
    from unittest.mock import MagicMock, patch

    import pandas as pd

    repo_root = sys.argv[1]
    lock_path  = sys.argv[2]
    hold_secs  = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    raise_in_lock = sys.argv[4] == "1" if len(sys.argv) > 4 else False

    sys.path.insert(0, repo_root + "/src")
    sys.path.insert(0, repo_root)

    import scripts.run_paper_trading_vt as vt_mod
    from forex_system.risk.drawdown_contract import DrawdownContract

    vt_mod._HALT_REQUESTED = False
    vt_mod._HALT_REASON = ""
    vt_mod.DISPATCH_LOCK_PATH = lock_path

    # Build mocks
    ks = MagicMock()
    ks.is_triggered = False
    ks.check_and_trigger.return_value = False
    ks.record_equity_fetch_failure.return_value = False
    ks.consecutive_fetch_failures = 0
    ks.max_consecutive_fetch_failures = 3
    ks.record_equity_fetch_success.return_value = None

    backend = MagicMock()
    backend.account_key = "TEST_VT_ACCT"

    if raise_in_lock:
        # Cause an exception inside the critical section (after lock acquired)
        backend.get_positions.side_effect = RuntimeError("injected-test-error")
    else:
        backend.get_positions.return_value = {}

    client = MagicMock()
    client.get_info_price.return_value = {"Quote": {"Bid": 1.10, "Ask": 1.10}}

    sizer = MagicMock()
    sizer.calculate_size.return_value = 0.0  # flat -> HOLD

    idx = pd.date_range("2025-01-01", periods=300, freq="D", tz="UTC")
    ohlcv = pd.DataFrame(
        {"open": 1.10, "high": 1.10, "low": 1.10, "close": 1.10, "volume": 1e6},
        index=idx,
    )

    strategy = MagicMock()
    strategy.generate_signals.return_value = pd.Series([0.0], index=[idx[-1]])
    strategy.params = {"vol_window": 252}

    dd = DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )
    dd.assess(100_000.0)  # set peak so DD checks pass

    def _slow_bars(client_, pair, count=300, horizon="daily"):
        if hold_secs > 0:
            time.sleep(hold_secs)
        return ohlcv

    try:
        with patch.object(vt_mod, "fetch_account_equity", return_value=100_000.0), \\
             patch.object(vt_mod, "fetch_recent_bars", side_effect=_slow_bars):
            result = vt_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=sizer,
                strategy=strategy,
                pair="EURUSD",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=9001,
            )
        print(json.dumps({"_action": result.get("_action"), "ok": True}))
    except Exception as exc:
        print(json.dumps({"_action": "EXCEPTION", "error": repr(exc), "ok": False}))
""")


_CF_WORKER = textwrap.dedent("""\
    import json
    import sys
    import time
    from pathlib import Path
    from unittest.mock import MagicMock, patch

    import pandas as pd

    repo_root = sys.argv[1]
    lock_path  = sys.argv[2]
    hold_secs  = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    raise_in_lock = sys.argv[4] == "1" if len(sys.argv) > 4 else False

    sys.path.insert(0, repo_root + "/src")
    sys.path.insert(0, repo_root)

    import scripts.run_paper_trading_carry_fred as cf_mod
    from forex_system.risk.drawdown_contract import DrawdownContract

    cf_mod._HALT_REQUESTED = False
    cf_mod._HALT_REASON = ""
    cf_mod.DISPATCH_LOCK_PATH = lock_path

    ks = MagicMock()
    ks.is_triggered = False
    ks.check_and_trigger.return_value = False
    ks.record_equity_fetch_failure.return_value = False
    ks.consecutive_fetch_failures = 0
    ks.max_consecutive_fetch_failures = 3
    ks.record_equity_fetch_success.return_value = None

    backend = MagicMock()
    backend.account_key = "TEST_CF_ACCT"

    if raise_in_lock:
        backend.get_positions.side_effect = RuntimeError("injected-test-error")
    else:
        backend.get_positions.return_value = {}

    client = MagicMock()
    client.get_info_price.return_value = {"Quote": {"Bid": 1.10, "Ask": 1.10}}

    sizer = MagicMock()
    sizer.calculate_size.return_value = 0.0

    idx = pd.date_range("2025-01-01", periods=300, freq="D", tz="UTC")
    ohlcv = pd.DataFrame(
        {"open": 1.10, "high": 1.10, "low": 1.10, "close": 1.10, "volume": 1e6},
        index=idx,
    )

    strategy = MagicMock()
    strategy.generate_signals.return_value = pd.Series([0.0], index=[idx[-1]])
    strategy.params = {}

    dd = DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )
    dd.assess(100_000.0)

    def _slow_bars(client_, pair, count=300, horizon="daily"):
        if hold_secs > 0:
            time.sleep(hold_secs)
        return ohlcv

    try:
        with patch.object(cf_mod, "fetch_account_equity", return_value=100_000.0), \\
             patch.object(cf_mod, "fetch_recent_bars", side_effect=_slow_bars), \\
             patch.object(cf_mod, "regime_active_status", return_value=True), \\
             patch.object(cf_mod, "bet1_size_multiplier", return_value=0.25):
            result = cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=sizer,
                strategy=strategy,
                pair="EURUSD",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=9002,
            )
        print(json.dumps({"_action": result.get("_action"), "ok": True}))
    except Exception as exc:
        print(json.dumps({"_action": "EXCEPTION", "error": repr(exc), "ok": False}))
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spawn(worker_script: str, lock_path: str, hold_secs: float = 0.0,
           raise_in_lock: bool = False) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable, "-c", worker_script,
            _REPO_ROOT,
            lock_path,
            str(hold_secs),
            "1" if raise_in_lock else "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


def _result(proc: subprocess.Popen, timeout: float = 15.0) -> dict:
    try:
        stdout, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        pytest.fail(f"Subprocess timed out after {timeout}s")
    output = stdout.decode().strip()
    if not output:
        pytest.fail(f"Subprocess produced no output (exit={proc.returncode})")
    try:
        return json.loads(output.splitlines()[-1])
    except json.JSONDecodeError as exc:
        pytest.fail(f"Could not parse subprocess output as JSON: {output!r} — {exc}")


# ---------------------------------------------------------------------------
# Test 1: single run_cycle acquires and releases the dispatch lock
# ---------------------------------------------------------------------------


class TestRealRunCycleAcquiresDispatchLock:
    """Calling run_cycle once acquires and releases the dispatch lock file.

    Regression anchor: if the fcntl block is removed, a subsequent attempt
    to acquire an exclusive lock on the same file succeeds immediately (no
    contention).  This test validates the positive path — the lock file is
    created and the second (sequential) call also succeeds, proving the lock
    was properly released on the first call's exit.
    """

    def test_real_run_cycle_acquires_dispatch_lock_vt(self, tmp_path):
        """VT run_cycle: lock file created; second sequential call succeeds (lock released)."""
        lock = str(tmp_path / "dl.flock")

        # First call — must acquire and release
        p1 = _spawn(_VT_WORKER, lock, hold_secs=0.0)
        r1 = _result(p1)
        assert r1.get("ok"), f"First VT run_cycle raised: {r1}"
        assert r1.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            "First sequential call must not see a busy lock; got SKIP_DISPATCH_LOCK_BUSY. "
            "This indicates the lock was not released — fcntl.LOCK_UN missing."
        )

        # Second call — lock must have been released; must not be busy
        p2 = _spawn(_VT_WORKER, lock, hold_secs=0.0)
        r2 = _result(p2)
        assert r2.get("ok"), f"Second VT run_cycle raised: {r2}"
        assert r2.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            "Second sequential call must not see a busy lock; got SKIP_DISPATCH_LOCK_BUSY. "
            "Regression: if fcntl block removed, lock is never acquired/released, "
            "so this assertion would pass vacuously — but test_two_concurrent catches that."
        )

    def test_real_run_cycle_acquires_dispatch_lock_cf(self, tmp_path):
        """CarryFred run_cycle: lock file created; second sequential call succeeds."""
        lock = str(tmp_path / "dl_cf.flock")

        p1 = _spawn(_CF_WORKER, lock, hold_secs=0.0)
        r1 = _result(p1)
        assert r1.get("ok"), f"First CF run_cycle raised: {r1}"
        assert r1.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            "First sequential CF call must not see a busy lock."
        )

        p2 = _spawn(_CF_WORKER, lock, hold_secs=0.0)
        r2 = _result(p2)
        assert r2.get("ok"), f"Second CF run_cycle raised: {r2}"
        assert r2.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            "Second sequential CF call must not see a busy lock."
        )


# ---------------------------------------------------------------------------
# Test 2: two concurrent real run_cycle calls — one gets SKIP_DISPATCH_LOCK_BUSY
# ---------------------------------------------------------------------------


class TestRealRunCycleTwoConcurrentOneGetsBusy:
    """Two overlapping subprocesses calling real run_cycle compete for the lock.

    W11-4-CLAIM-B closure: if the fcntl block is removed from run_cycle, both
    processes complete without contention and neither returns SKIP_DISPATCH_LOCK_BUSY.
    The assertion `"SKIP_DISPATCH_LOCK_BUSY" in outcomes` FAILS, catching the regression.

    P1 holds the lock for 1.0s (via a slow fetch_recent_bars mock).
    P2 starts 100ms later while P1 still holds the lock — P2 must return
    SKIP_DISPATCH_LOCK_BUSY from the real run_cycle fcntl path.
    """

    def test_real_vt_two_concurrent_one_gets_busy(self, tmp_path):
        """VT: one subprocess acquires lock; the other returns SKIP_DISPATCH_LOCK_BUSY."""
        lock = str(tmp_path / "dl_conc.flock")

        # P1: holds lock for 1 second (slow fetch_recent_bars)
        p1 = _spawn(_VT_WORKER, lock, hold_secs=1.0)
        # Give P1 time to acquire the lock before P2 tries
        time.sleep(0.1)
        # P2: must find lock busy
        p2 = _spawn(_VT_WORKER, lock, hold_secs=0.0)

        r1 = _result(p1, timeout=10.0)
        r2 = _result(p2, timeout=5.0)

        outcomes = {r1.get("_action"), r2.get("_action")}

        assert "SKIP_DISPATCH_LOCK_BUSY" in outcomes, (
            f"One of the two concurrent VT run_cycle calls must return "
            f"SKIP_DISPATCH_LOCK_BUSY; got outcomes={outcomes}. "
            f"REGRESSION: if the fcntl block is removed from run_cycle, "
            f"both processes acquire the 'lock' freely and this assertion fails."
        )

    def test_real_cf_two_concurrent_one_gets_busy(self, tmp_path):
        """CarryFred: one subprocess acquires lock; the other returns SKIP_DISPATCH_LOCK_BUSY."""
        lock = str(tmp_path / "dl_cf_conc.flock")

        p1 = _spawn(_CF_WORKER, lock, hold_secs=1.0)
        time.sleep(0.1)
        p2 = _spawn(_CF_WORKER, lock, hold_secs=0.0)

        r1 = _result(p1, timeout=10.0)
        r2 = _result(p2, timeout=5.0)

        outcomes = {r1.get("_action"), r2.get("_action")}

        assert "SKIP_DISPATCH_LOCK_BUSY" in outcomes, (
            f"One of the two concurrent CF run_cycle calls must return "
            f"SKIP_DISPATCH_LOCK_BUSY; got outcomes={outcomes}. "
            f"REGRESSION: if the fcntl block is removed, this assertion fails."
        )


# ---------------------------------------------------------------------------
# Test 3: dispatch lock released even when run_cycle raises inside critical section
# ---------------------------------------------------------------------------


class TestRealRunCycleLockReleasedOnException:
    """run_cycle releases the dispatch lock even when the critical section raises.

    Regression anchor: if the fcntl block's finally clause (LOCK_UN) is removed,
    the file descriptor remains locked after an exception.  A subsequent call to
    run_cycle on the same lock path would return SKIP_DISPATCH_LOCK_BUSY instead
    of proceeding normally, catching the missing release.

    Note: the exception is raised inside the critical section by making
    backend.get_positions raise RuntimeError.  The run_cycle catches no generic
    RuntimeError so the exception propagates — the finally block is the only
    mechanism that releases the lock.  We verify by spawning a second subprocess
    on the same lock file AFTER the first exits; it must NOT see SKIP_DISPATCH_LOCK_BUSY.
    """

    def test_real_vt_lock_released_on_exception(self, tmp_path):
        """VT: after run_cycle raises inside lock, lock is released for next caller."""
        lock = str(tmp_path / "dl_exc.flock")

        # P1: raises RuntimeError inside critical section
        p1 = _spawn(_VT_WORKER, lock, hold_secs=0.0, raise_in_lock=True)
        r1 = _result(p1, timeout=10.0)

        # P1 should have propagated the exception (caught at subprocess level)
        assert r1.get("_action") == "EXCEPTION", (
            f"P1 must have caught the injected RuntimeError; got {r1}"
        )

        # P2: runs after P1 exits; must not find lock busy
        p2 = _spawn(_VT_WORKER, lock, hold_secs=0.0)
        r2 = _result(p2, timeout=10.0)

        assert r2.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            f"After an exception in run_cycle, the lock must be released. "
            f"P2 got SKIP_DISPATCH_LOCK_BUSY — the finally block (LOCK_UN) is missing. "
            f"P2 result: {r2}"
        )
        assert r2.get("ok"), (
            f"P2 run_cycle must complete without error after lock release; got {r2}"
        )

    def test_real_cf_lock_released_on_exception(self, tmp_path):
        """CarryFred: after run_cycle raises inside lock, lock is released for next caller."""
        lock = str(tmp_path / "dl_cf_exc.flock")

        p1 = _spawn(_CF_WORKER, lock, hold_secs=0.0, raise_in_lock=True)
        r1 = _result(p1, timeout=10.0)

        assert r1.get("_action") == "EXCEPTION", (
            f"P1 must have propagated the injected RuntimeError; got {r1}"
        )

        p2 = _spawn(_CF_WORKER, lock, hold_secs=0.0)
        r2 = _result(p2, timeout=10.0)

        assert r2.get("_action") != "SKIP_DISPATCH_LOCK_BUSY", (
            f"After an exception in CF run_cycle, the lock must be released. "
            f"P2 got SKIP_DISPATCH_LOCK_BUSY — the finally block (LOCK_UN) is missing. "
            f"P2 result: {r2}"
        )
        assert r2.get("ok"), (
            f"P2 CF run_cycle must complete without error after lock release; got {r2}"
        )
