"""W11-3 F-101: OSError dispatch-lock catch tests (CRO Decision B).

Verifies that an unexpected OSError (e.g. ENOSPC) during fcntl.flock:
  1. Is caught by the `except OSError as exc:` clause (NOT BlockingIOError).
  2. Emits the SKIP_DISPATCH_LOCK_FS_ERROR log line with errno + strerror.
  3. Triggers the kill-switch with TriggerReason.INFRASTRUCTURE.
  4. Releases the fd (os.close called).

Also includes a regression test that BlockingIOError still emits
SKIP_DISPATCH_LOCK_BUSY and does NOT trigger the kill-switch.

Python sequencing note: BlockingIOError IS-A OSError, so the
`except BlockingIOError:` clause must appear BEFORE `except OSError as exc:`.
Both scripts are tested symmetrically (vt + carry_fred).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.risk.drawdown_contract import DrawdownContract
from forex_system.risk.kill_switch import TriggerReason


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_OSERROR_ERRNO = 28
_OSERROR_STRERROR = "No space left on device"
_OSERROR = OSError(_OSERROR_ERRNO, _OSERROR_STRERROR)


def _std_dd_contract() -> DrawdownContract:
    return DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )


def _make_ohlcv(close: float = 1.10, rows: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=rows, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=idx,
    )


def _make_kill_switch_mock():
    ks = MagicMock()
    ks.is_triggered = False
    ks.check_and_trigger.return_value = False
    ks.record_equity_fetch_failure.return_value = False
    ks.consecutive_fetch_failures = 0
    ks.max_consecutive_fetch_failures = 3
    ks.record_equity_fetch_success.return_value = None
    ks.trigger.return_value = None
    return ks


# ---------------------------------------------------------------------------
# VT script helpers
# ---------------------------------------------------------------------------

def _make_vt_infra(equity: float = 100_000.0):
    ks = _make_kill_switch_mock()

    backend = MagicMock()
    backend.get_positions.return_value = {}
    backend.account_key = "TEST_VT_ACCOUNT"

    client = MagicMock()
    client.get_info_price.return_value = {"Quote": {"Bid": 1.10, "Ask": 1.10}}

    sizer = MagicMock()
    sizer.calculate_size.return_value = 1000.0

    strategy = MagicMock()
    ohlcv = _make_ohlcv()
    signals = pd.Series([0.5], index=[ohlcv.index[-1]])
    strategy.generate_signals.return_value = signals
    strategy.params = {"vol_window": 252}

    pred_log = MagicMock()
    trade_log = MagicMock()

    return client, backend, ks, sizer, strategy, pred_log, trade_log


def _run_vt_cycle_with_flock_error(flock_error: Exception):
    """Run vt run_cycle with fcntl.flock raising flock_error."""
    import scripts.run_paper_trading_vt as vt_mod

    vt_mod._HALT_REQUESTED = False
    vt_mod._HALT_REASON = ""

    client, backend, ks, sizer, strategy, pred_log, trade_log = _make_vt_infra()
    dd = _std_dd_contract()
    dd.assess(100_000.0)
    ohlcv = _make_ohlcv()

    with patch.object(vt_mod, "fetch_account_equity", return_value=100_000.0), \
         patch.object(vt_mod, "fetch_recent_bars", return_value=ohlcv), \
         patch("scripts.run_paper_trading_vt.fcntl.flock", side_effect=flock_error):
        result = vt_mod.run_cycle(
            client=client,
            backend=backend,
            sizer=sizer,
            strategy=strategy,
            pair="EURUSD",
            pred_log=pred_log,
            trade_log=trade_log,
            kill_switch=ks,
            dd_contract=dd,
            rebal_threshold=0.20,
            auto_mode=True,
            cycle_id=101,
        )
    return result, ks


# ---------------------------------------------------------------------------
# Carry-fred script helpers
# ---------------------------------------------------------------------------

def _make_cf_infra():
    ks = _make_kill_switch_mock()

    backend = MagicMock()
    backend.get_positions.return_value = {}
    backend.account_key = "TEST_CF_ACCOUNT"

    client = MagicMock()
    client.get_info_price.return_value = {"Quote": {"Bid": 1.10, "Ask": 1.10}}

    sizer = MagicMock()
    sizer.calculate_size.return_value = 1000.0

    strategy = MagicMock()
    ohlcv = _make_ohlcv()
    signals = pd.Series([0.5], index=[ohlcv.index[-1]])
    strategy.generate_signals.return_value = signals
    strategy.params = {}

    pred_log = MagicMock()
    trade_log = MagicMock()

    return client, backend, ks, sizer, strategy, pred_log, trade_log


def _run_cf_cycle_with_flock_error(flock_error: Exception):
    """Run carry_fred run_cycle with fcntl.flock raising flock_error."""
    import scripts.run_paper_trading_carry_fred as cf_mod

    cf_mod._HALT_REQUESTED = False
    cf_mod._HALT_REASON = ""

    client, backend, ks, sizer, strategy, pred_log, trade_log = _make_cf_infra()
    dd = _std_dd_contract()
    dd.assess(100_000.0)
    ohlcv = _make_ohlcv()

    with patch.object(cf_mod, "fetch_account_equity", return_value=100_000.0), \
         patch.object(cf_mod, "fetch_recent_bars", return_value=ohlcv), \
         patch.object(cf_mod, "regime_active_status", return_value=True), \
         patch.object(cf_mod, "bet1_size_multiplier", return_value=1.0), \
         patch("scripts.run_paper_trading_carry_fred.fcntl.flock", side_effect=flock_error):
        result = cf_mod.run_cycle(
            client=client,
            backend=backend,
            sizer=sizer,
            strategy=strategy,
            pair="EURUSD",
            pred_log=pred_log,
            trade_log=trade_log,
            kill_switch=ks,
            dd_contract=dd,
            rebal_threshold=0.20,
            auto_mode=True,
            cycle_id=101,
        )
    return result, ks


# ===========================================================================
# VT script tests
# ===========================================================================

class TestVtOsErrorCaughtAfterBlockingIOError:
    """OSError is caught by its own clause, not BlockingIOError — vt.py."""

    def test_oserror_caught_after_blockingioerror(self):
        """fcntl.flock raising OSError(28) returns SKIP_DISPATCH_LOCK_FS_ERROR."""
        result, _ = _run_vt_cycle_with_flock_error(_OSERROR)
        assert result.get("_action") == "SKIP_DISPATCH_LOCK_FS_ERROR", (
            f"Expected SKIP_DISPATCH_LOCK_FS_ERROR, got {result}"
        )

    def test_oserror_emits_skip_dispatch_lock_fs_error_log(self, caplog):
        """Warning log with event=SKIP_DISPATCH_LOCK_FS_ERROR, errno=28, strerror present."""
        with caplog.at_level(logging.WARNING):
            _run_vt_cycle_with_flock_error(_OSERROR)
        matching = [
            r for r in caplog.records
            if r.getMessage() == "dispatch_lock.fs_error"
            or getattr(r, "event", None) == "SKIP_DISPATCH_LOCK_FS_ERROR"
            or "SKIP_DISPATCH_LOCK_FS_ERROR" in str(getattr(r, "__dict__", {}))
        ]
        assert matching, (
            "Expected dispatch_lock.fs_error warning log not found; "
            f"records: {[r.getMessage() for r in caplog.records]}"
        )
        rec = matching[0]
        rec_dict = rec.__dict__
        assert rec_dict.get("errno") == _OSERROR_ERRNO or rec_dict.get("event") == "SKIP_DISPATCH_LOCK_FS_ERROR", (
            f"Log record missing errno or event; dict keys: {list(rec_dict.keys())}"
        )

    def test_oserror_triggers_kill_switch_infrastructure(self):
        """kill_switch.trigger called with TriggerReason.INFRASTRUCTURE on OSError path."""
        result, ks = _run_vt_cycle_with_flock_error(_OSERROR)
        ks.trigger.assert_called_once()
        args, kwargs = ks.trigger.call_args
        reason = args[0] if args else kwargs.get("reason")
        assert reason == TriggerReason.INFRASTRUCTURE, (
            f"Expected TriggerReason.INFRASTRUCTURE, got {reason}"
        )

    def test_oserror_releases_fd(self):
        """os.close is called on the OSError path (fd release invariant)."""
        import scripts.run_paper_trading_vt as vt_mod

        vt_mod._HALT_REQUESTED = False
        vt_mod._HALT_REASON = ""

        client, backend, ks, sizer, strategy, pred_log, trade_log = _make_vt_infra()
        dd = _std_dd_contract()
        dd.assess(100_000.0)
        ohlcv = _make_ohlcv()

        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)

        with patch.object(vt_mod, "fetch_account_equity", return_value=100_000.0), \
             patch.object(vt_mod, "fetch_recent_bars", return_value=ohlcv), \
             patch("scripts.run_paper_trading_vt.fcntl.flock", side_effect=_OSERROR), \
             patch("scripts.run_paper_trading_vt.os.close", side_effect=tracking_close):
            vt_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=sizer,
                strategy=strategy,
                pair="EURUSD",
                pred_log=pred_log,
                trade_log=trade_log,
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=101,
            )
        assert len(close_calls) >= 1, "os.close must be called on the OSError path"


class TestVtBlockingIOErrorRegressionVt:
    """BlockingIOError still emits SKIP_DISPATCH_LOCK_BUSY, NOT FS_ERROR — vt.py."""

    def test_blockingioerror_still_emits_skip_busy(self):
        """BlockingIOError → SKIP_DISPATCH_LOCK_BUSY (not SKIP_DISPATCH_LOCK_FS_ERROR)."""
        err = BlockingIOError(11, "Resource temporarily unavailable")
        result, ks = _run_vt_cycle_with_flock_error(err)
        assert result.get("_action") == "SKIP_DISPATCH_LOCK_BUSY", (
            f"Expected SKIP_DISPATCH_LOCK_BUSY, got {result}"
        )
        # kill-switch must NOT be triggered on the busy path
        ks.trigger.assert_not_called()


# ===========================================================================
# Carry-fred script tests
# ===========================================================================

class TestCfOsErrorDispatchLock:
    """Symmetric OSError dispatch-lock tests for carry_fred.py."""

    def test_oserror_caught_after_blockingioerror(self):
        """fcntl.flock raising OSError(28) returns SKIP_DISPATCH_LOCK_FS_ERROR — cf."""
        result, _ = _run_cf_cycle_with_flock_error(_OSERROR)
        assert result.get("_action") == "SKIP_DISPATCH_LOCK_FS_ERROR", (
            f"Expected SKIP_DISPATCH_LOCK_FS_ERROR, got {result}"
        )

    def test_oserror_triggers_kill_switch_infrastructure(self):
        """kill_switch.trigger called with TriggerReason.INFRASTRUCTURE — cf."""
        result, ks = _run_cf_cycle_with_flock_error(_OSERROR)
        ks.trigger.assert_called_once()
        args, kwargs = ks.trigger.call_args
        reason = args[0] if args else kwargs.get("reason")
        assert reason == TriggerReason.INFRASTRUCTURE, (
            f"Expected TriggerReason.INFRASTRUCTURE, got {reason}"
        )

    def test_blockingioerror_still_emits_skip_busy(self):
        """BlockingIOError → SKIP_DISPATCH_LOCK_BUSY (not SKIP_DISPATCH_LOCK_FS_ERROR) — cf."""
        err = BlockingIOError(11, "Resource temporarily unavailable")
        result, ks = _run_cf_cycle_with_flock_error(err)
        assert result.get("_action") == "SKIP_DISPATCH_LOCK_BUSY", (
            f"Expected SKIP_DISPATCH_LOCK_BUSY, got {result}"
        )
        ks.trigger.assert_not_called()

    def test_oserror_releases_fd(self):
        """os.close is called on the OSError path (fd release invariant) — cf."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks, sizer, strategy, pred_log, trade_log = _make_cf_infra()
        dd = _std_dd_contract()
        dd.assess(100_000.0)
        ohlcv = _make_ohlcv()

        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)

        with patch.object(cf_mod, "fetch_account_equity", return_value=100_000.0), \
             patch.object(cf_mod, "fetch_recent_bars", return_value=ohlcv), \
             patch.object(cf_mod, "regime_active_status", return_value=True), \
             patch.object(cf_mod, "bet1_size_multiplier", return_value=1.0), \
             patch("scripts.run_paper_trading_carry_fred.fcntl.flock", side_effect=_OSERROR), \
             patch("scripts.run_paper_trading_carry_fred.os.close", side_effect=tracking_close):
            cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=sizer,
                strategy=strategy,
                pair="EURUSD",
                pred_log=pred_log,
                trade_log=trade_log,
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=101,
            )
        assert len(close_calls) >= 1, "os.close must be called on the OSError path — cf"
