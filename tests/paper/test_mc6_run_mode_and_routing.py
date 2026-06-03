"""MC-6 fix tests: run_mode discriminator + routing_disabled guard.

Spec: CRO + ET 2026-06-01 (paper-launch-acceleration, P4).

TC-MC6-1: sim-paper + broker_equity==100_000.0 → is_mock=False (processed normally).
TC-MC6-2: run_mode="mock-test" → is_mock=True (excluded, regardless of equity value).
TC-MC6-3: is_mock_backend=True → is_mock=True regardless of run_mode.
TC-MC6-4: routing_disabled=True → RoutingDisabledError raised (order NOT sent).
TC-MC6-5: routing_disabled=False → routing proceeds (no error from the guard).
TC-MC6-6: Defence-in-depth WARNING fires (and does NOT exclude) when sim-paper sees 100_000.0.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.core.interfaces import ExecutionBackend, RoutingDisabledError
from forex_system.paper.cost_reconciliation import (
    ModeledEquityLedger,
    _MOCK_EQUITY_SENTINEL,
    ledger_from_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sim_paper_ledger(
    *,
    tol_abs: float = 500.0,
    tol_rel: float = 0.005,
    enforce: bool = False,
    consecutive_n: int = 3,
    ntfy_fn=None,
    data_dir: str | None = None,
) -> ModeledEquityLedger:
    """Create a ledger with run_mode='sim-paper' (production default)."""
    if data_dir is None:
        data_dir = tempfile.mkdtemp()
    return ModeledEquityLedger(
        strategy_id="test_mc6",
        tol_rel=tol_rel,
        tol_abs=tol_abs,
        enforce=enforce,
        consecutive_n=consecutive_n,
        data_dir=data_dir,
        ntfy_fn=ntfy_fn,
        run_mode="sim-paper",
    )


# ---------------------------------------------------------------------------
# TC-MC6-1: sim-paper + broker_equity == 100_000.0 → cycle IS processed (not mock)
# ---------------------------------------------------------------------------


class TestTC_MC6_1_SimPaperSentinelNotMock:
    """run_mode='sim-paper': broker_equity==100_000.0 is processed as a real cycle."""

    def test_is_mock_cycle_returns_false_in_sim_paper_mode(self):
        """Static method: sim-paper + sentinel equity → is_mock=False."""
        result = ModeledEquityLedger.is_mock_cycle(
            _MOCK_EQUITY_SENTINEL,
            is_mock_backend=False,
            run_mode="sim-paper",
        )
        assert result is False, (
            "MC-6 fix: sim-paper mode must NOT treat 100_000.0 as mock; "
            f"is_mock_cycle returned {result}"
        )

    def test_update_sim_paper_sentinel_equity_processed_as_real(self, tmp_path):
        """Ledger update with run_mode='sim-paper' + broker_equity==100_000.0.

        The cycle must be processed as real:
          - ReconResult.is_mock is False
          - peak_broker_equity IS updated to 100_000.0
          - real_cycle_count advances
        """
        led = _make_sim_paper_ledger(data_dir=str(tmp_path))
        # Seed at a different value so the first update can produce a residual
        led.seed(98_000.0, "EURUSD", 1.08)

        result = led.update(
            pair="EURUSD",
            mid_now=1.08,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=_MOCK_EQUITY_SENTINEL,  # exactly 100_000.0 — the legacy sentinel
            is_mock_backend=False,
            cycle_id=1,
        )

        assert result.is_mock is False, (
            "TC-MC6-1: sim-paper cycle with broker_equity=100_000.0 must NOT be treated as mock; "
            f"got is_mock={result.is_mock}"
        )
        # Peak must be updated because this is a real cycle
        assert led.peak_broker_equity == _MOCK_EQUITY_SENTINEL, (
            "TC-MC6-1: peak must advance to 100_000.0 in sim-paper mode; "
            f"got peak={led.peak_broker_equity}"
        )
        # real_cycle_count must advance
        assert led.real_cycle_count == 1, (
            f"TC-MC6-1: real_cycle_count must be 1 after one sim-paper cycle; "
            f"got {led.real_cycle_count}"
        )

    def test_breach_counting_proceeds_in_sim_paper_with_sentinel_equity(self, tmp_path):
        """Breach counting must work normally for sentinel-equity cycles in sim-paper.

        If broker_equity is 100_000.0 and modeled_equity is different, the residual
        and breach logic must fire (not be suppressed by mock exclusion).
        """
        led = _make_sim_paper_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,    # tiny tolerance so any deviation breaches
            tol_rel=0.0,
            enforce=True,
            consecutive_n=3,
        )
        # Seed below sentinel so there is a real residual when broker reports 100_000.0
        led.seed(99_000.0, "EURUSD", 1.08)

        result = led.update(
            pair="EURUSD",
            mid_now=1.08,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=_MOCK_EQUITY_SENTINEL,  # 100_000.0 — real cycle in sim-paper
            is_mock_backend=False,
            cycle_id=1,
        )

        assert result.is_mock is False
        # residual = 100_000.0 - 99_000.0 = 1000, tolerance = max(1.0, 0.0*100_000)=1.0
        assert result.breach is True, (
            "TC-MC6-1: residual=1000 >> tol=1.0 must produce breach in sim-paper mode; "
            f"got breach={result.breach}"
        )
        assert led.consecutive_breaches == 1


# ---------------------------------------------------------------------------
# TC-MC6-2: run_mode="mock-test" → is_mock=True
# ---------------------------------------------------------------------------


class TestTC_MC6_2_MockTestModeExcludes:
    """run_mode='mock-test': sentinel equity + mock-test mode → cycle IS excluded."""

    def test_is_mock_cycle_true_in_mock_test_mode(self):
        """Static method: mock-test + sentinel → is_mock=True (legacy behaviour preserved)."""
        assert ModeledEquityLedger.is_mock_cycle(
            _MOCK_EQUITY_SENTINEL,
            is_mock_backend=False,
            run_mode="mock-test",
        ) is True

    def test_non_sentinel_in_mock_test_mode_is_not_mock(self):
        """Non-sentinel values are NOT excluded even in mock-test mode."""
        assert ModeledEquityLedger.is_mock_cycle(
            99_999.99,
            is_mock_backend=False,
            run_mode="mock-test",
        ) is False, "mock-test mode should only exclude the exact sentinel value, not all equity"

    def test_update_mock_test_mode_sentinel_excluded(self, tmp_path):
        """Ledger update with run_mode='mock-test' + broker_equity==100_000.0 → excluded."""
        led = ModeledEquityLedger(
            strategy_id="test_mc6_mocktest",
            tol_abs=1.0,
            tol_rel=0.0,
            enforce=True,
            data_dir=str(tmp_path),
            run_mode="mock-test",
        )
        led.seed(50_000.0, "EURUSD", 1.08)

        result = led.update(
            pair="EURUSD",
            mid_now=1.08,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=_MOCK_EQUITY_SENTINEL,
            is_mock_backend=False,
            cycle_id=1,
        )

        assert result.is_mock is True, (
            "TC-MC6-2: mock-test mode must exclude sentinel equity; "
            f"got is_mock={result.is_mock}"
        )
        assert led.peak_broker_equity == 0.0, (
            "TC-MC6-2: mock cycle must not advance peak; "
            f"got peak={led.peak_broker_equity}"
        )
        assert led.consecutive_breaches == 0, (
            "TC-MC6-2: mock cycle must not advance consecutive_breaches"
        )

    def test_ledger_from_config_passes_run_mode(self, tmp_path):
        """ledger_from_config threads run_mode through to the ledger."""
        led = ledger_from_config(
            "test_config_runmode",
            {},
            ntfy_fn=None,
            run_mode="mock-test",
        )
        assert led.run_mode == "mock-test", (
            f"ledger_from_config must pass run_mode to ledger; got {led.run_mode}"
        )

    def test_ledger_from_config_defaults_to_sim_paper(self):
        """ledger_from_config defaults to sim-paper (production default)."""
        led = ledger_from_config("test_config_default", {})
        assert led.run_mode == "sim-paper", (
            f"ledger_from_config must default to sim-paper; got {led.run_mode}"
        )


# ---------------------------------------------------------------------------
# TC-MC6-3: is_mock_backend=True → is_mock=True regardless of run_mode
# ---------------------------------------------------------------------------


class TestTC_MC6_3_IsMockBackendOverride:
    """is_mock_backend=True forces mock exclusion in all run_mode values."""

    @pytest.mark.parametrize("run_mode,broker_equity", [
        ("sim-paper", 100_000.0),
        ("sim-paper", 200_000.0),
        ("sim-paper", 50_000.0),
        ("mock-test", 200_000.0),  # non-sentinel in mock-test, but backend flag overrides
        ("live", 100_000.0),
        ("live", 75_000.0),
    ])
    def test_is_mock_backend_always_excludes(self, run_mode, broker_equity: float):
        """is_mock_backend=True → is_mock=True regardless of run_mode and equity value."""
        result = ModeledEquityLedger.is_mock_cycle(
            broker_equity,
            is_mock_backend=True,
            run_mode=run_mode,  # type: ignore[arg-type]
        )
        assert result is True, (
            f"TC-MC6-3: is_mock_backend=True must force is_mock=True; "
            f"got {result} for run_mode={run_mode!r} broker_equity={broker_equity}"
        )

    def test_is_mock_backend_flag_via_update(self, tmp_path):
        """update() with is_mock_backend=True excludes peak/breach in sim-paper mode."""
        led = _make_sim_paper_ledger(data_dir=str(tmp_path))
        led.seed(100_000.0, "EURUSD", 1.08)

        result = led.update(
            pair="EURUSD",
            mid_now=1.08,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=200_000.0,  # non-sentinel, large value
            is_mock_backend=True,
            cycle_id=1,
        )

        assert result.is_mock is True, (
            "TC-MC6-3: is_mock_backend=True must force is_mock=True in sim-paper mode; "
            f"got is_mock={result.is_mock}"
        )
        assert led.peak_broker_equity == 0.0, (
            "TC-MC6-3: is_mock_backend=True must suppress peak update; "
            f"got peak={led.peak_broker_equity}"
        )

    def test_is_mock_backend_via_backend_property(self, tmp_path):
        """Simulate the script path: _cycle_is_mock = backend.is_mock used for exclusion."""

        class MockTestBackend(ExecutionBackend):
            """Test stub with is_mock=True."""

            @property
            def is_mock(self) -> bool:
                return True

            def execute_signal(self, pair, signal, size, context=None):
                raise NotImplementedError

            def get_positions(self):
                return {}

            def flatten_all(self):
                return []

        backend = MockTestBackend()
        assert backend.is_mock is True

        led = _make_sim_paper_ledger(data_dir=str(tmp_path))
        led.seed(100_000.0, "EURUSD", 1.08)

        result = led.update(
            pair="EURUSD",
            mid_now=1.08,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=150_000.0,
            is_mock_backend=backend.is_mock,  # sourced from backend.is_mock
            cycle_id=1,
        )

        assert result.is_mock is True


# ---------------------------------------------------------------------------
# TC-MC6-4: routing_disabled=True → RoutingDisabledError
# ---------------------------------------------------------------------------


class TestTC_MC6_4_RoutingDisabledBlocks:
    """routing_disabled=True hard-blocks order routing with RoutingDisabledError."""

    def _make_routing_disabled_backend(self, *, routing_disabled: bool):
        """Create a SaxoExecutionBackend with a mock SaxoClient."""
        # Import here to avoid top-level Saxo dependency in test file
        from forex_system.saxo.execution import SaxoExecutionBackend

        mock_client = MagicMock()
        return SaxoExecutionBackend(mock_client, routing_disabled=routing_disabled)

    def test_routing_disabled_raises_before_broker_call(self):
        """execute_signal raises RoutingDisabledError before any broker I/O."""
        backend = self._make_routing_disabled_backend(routing_disabled=True)
        assert backend.routing_disabled is True

        with pytest.raises(RoutingDisabledError) as exc_info:
            backend.execute_signal("EURUSD", 1.0, 10_000.0)

        # Verify the error message is informative
        assert "routing_disabled=True" in str(exc_info.value)
        assert "EURUSD" in str(exc_info.value)

    def test_routing_disabled_blocks_all_signal_values(self):
        """routing_disabled=True blocks buy, sell, and flatten signals."""
        backend = self._make_routing_disabled_backend(routing_disabled=True)

        for signal, size in [(1.0, 10_000.0), (-1.0, 10_000.0), (0.0, 0.0)]:
            with pytest.raises(RoutingDisabledError):
                backend.execute_signal("EURUSD", signal, size)

    def test_routing_disabled_error_is_structured_log(self, caplog):
        """routing_disabled block emits a structured ERROR log for decision-trace."""
        from forex_system.saxo.execution import SaxoExecutionBackend

        mock_client = MagicMock()
        backend = SaxoExecutionBackend(mock_client, routing_disabled=True)

        with caplog.at_level(logging.ERROR, logger="forex_system.saxo.execution"):
            with pytest.raises(RoutingDisabledError):
                backend.execute_signal("EURUSD", 1.0, 5_000.0)

        # At least one ERROR log must have been emitted
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) >= 1, (
            "TC-MC6-4: routing_disabled block must emit an ERROR log for decision-trace; "
            f"got {len(error_records)} error records"
        )
        # Verify the log contains the key fields
        combined = " ".join(r.getMessage() for r in error_records)
        assert "routing_blocked" in combined or "ROUTING_DISABLED_BLOCK" in combined, (
            f"Log must include routing_blocked or ROUTING_DISABLED_BLOCK; got: {combined!r}"
        )

    def test_routing_disabled_property_reflects_construction(self):
        """routing_disabled property matches the value passed at construction."""
        from forex_system.saxo.execution import SaxoExecutionBackend

        mock_client = MagicMock()
        backend_on = SaxoExecutionBackend(mock_client, routing_disabled=True)
        backend_off = SaxoExecutionBackend(mock_client, routing_disabled=False)

        assert backend_on.routing_disabled is True
        assert backend_off.routing_disabled is False

    def test_routing_disabled_default_is_false(self):
        """SaxoExecutionBackend defaults to routing_disabled=False (no change to existing callers)."""
        from forex_system.saxo.execution import SaxoExecutionBackend

        mock_client = MagicMock()
        backend = SaxoExecutionBackend(mock_client)
        assert backend.routing_disabled is False

    def test_base_interface_routing_disabled_default_false(self):
        """ExecutionBackend ABC property defaults to False (no-break for subclasses)."""

        class MinimalBackend(ExecutionBackend):
            def execute_signal(self, pair, signal, size, context=None):
                return None

            def get_positions(self):
                return {}

            def flatten_all(self):
                return []

        b = MinimalBackend()
        assert b.routing_disabled is False, (
            "ExecutionBackend.routing_disabled must default to False for backward compat"
        )


# ---------------------------------------------------------------------------
# TC-MC6-5: routing_disabled=False → routing proceeds (no RoutingDisabledError)
# ---------------------------------------------------------------------------


class TestTC_MC6_5_RoutingEnabledProceeds:
    """routing_disabled=False: execute_signal proceeds past the guard."""

    def test_routing_enabled_reaches_broker_call(self):
        """With routing_disabled=False, execute_signal calls the broker (mock)."""
        from forex_system.saxo.execution import SaxoExecutionBackend

        mock_client = MagicMock()
        # get_info_price returns a minimal valid quote so execute_signal doesn't crash early
        mock_client.get_info_price.return_value = {
            "Quote": {"Bid": 1.0800, "Ask": 1.0802}
        }
        mock_client.get_account_key.return_value = "test_account_key"
        mock_client.place_order.return_value = {"OrderId": "mock-order-123"}

        backend = SaxoExecutionBackend(mock_client, routing_disabled=False)

        # Should NOT raise RoutingDisabledError
        try:
            backend.execute_signal("EURUSD", 1.0, 10_000.0)
        except RoutingDisabledError:
            pytest.fail("routing_disabled=False must not raise RoutingDisabledError")
        except Exception:
            # Other exceptions (e.g. from mock setup) are acceptable — the guard didn't fire
            pass

        # Crucially: place_order was reached (the guard did not short-circuit)
        assert mock_client.place_order.called, (
            "TC-MC6-5: routing_disabled=False must let execution reach place_order"
        )


# ---------------------------------------------------------------------------
# TC-MC6-6: Defence-in-depth WARNING fires when sim-paper sees 100_000.0
# ---------------------------------------------------------------------------


class TestTC_MC6_6_SentinelCollisionWarning:
    """sim-paper + broker_equity==100_000.0 → WARNING logged + cycle NOT excluded."""

    def test_warning_emitted_when_sentinel_seen_in_sim_paper(self, tmp_path, caplog):
        """The COST_RECON_SENTINEL_COLLISION WARNING fires on first sentinel encounter."""
        led = _make_sim_paper_ledger(data_dir=str(tmp_path))
        led.seed(98_000.0, "EURUSD", 1.08)

        with caplog.at_level(logging.WARNING, logger="forex_system.paper.cost_reconciliation"):
            result = led.update(
                pair="EURUSD",
                mid_now=1.08,
                held_units_nom=0.0,
                cost_usd=0.0,
                swap_usd=0.0,
                broker_equity=_MOCK_EQUITY_SENTINEL,
                is_mock_backend=False,
                cycle_id=1,
            )

        # Cycle must NOT be excluded (is_mock=False)
        assert result.is_mock is False, (
            "TC-MC6-6: sentinel collision in sim-paper must NOT exclude the cycle"
        )

        # WARNING must have been emitted
        warning_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "sentinel" in r.getMessage().lower()
        ]
        assert len(warning_records) >= 1, (
            "TC-MC6-6: defence-in-depth WARNING must fire when sim-paper sees 100_000.0; "
            f"caplog records: {[r.getMessage() for r in caplog.records]}"
        )
        # The warning must mention run_mode
        combined = " ".join(r.getMessage() for r in warning_records)
        assert "sim-paper" in combined or "run_mode" in combined, (
            f"TC-MC6-6: WARNING must mention run_mode; got: {combined!r}"
        )

    def test_sentinel_warning_emitted_only_once_per_ledger(self, tmp_path, caplog):
        """Defence-in-depth warning fires only once per ledger instance (no log spam)."""
        led = _make_sim_paper_ledger(data_dir=str(tmp_path))
        led.seed(98_000.0, "EURUSD", 1.08)

        with caplog.at_level(logging.WARNING, logger="forex_system.paper.cost_reconciliation"):
            for i in range(3):
                led.update(
                    pair="EURUSD",
                    mid_now=1.08,
                    held_units_nom=0.0,
                    cost_usd=0.0,
                    swap_usd=0.0,
                    broker_equity=_MOCK_EQUITY_SENTINEL,
                    is_mock_backend=False,
                    cycle_id=i + 1,
                )

        # WARNING must have fired exactly once
        sentinel_warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "sentinel" in r.getMessage().lower()
        ]
        assert len(sentinel_warnings) == 1, (
            f"TC-MC6-6: sentinel WARNING must fire once per ledger, not {len(sentinel_warnings)} times"
        )

    def test_no_warning_in_mock_test_mode(self, tmp_path, caplog):
        """No sentinel WARNING in mock-test mode (cycle is excluded silently)."""
        led = ModeledEquityLedger(
            strategy_id="test_no_warn",
            data_dir=str(tmp_path),
            run_mode="mock-test",
        )
        led.seed(98_000.0, "EURUSD", 1.08)

        with caplog.at_level(logging.WARNING, logger="forex_system.paper.cost_reconciliation"):
            led.update(
                pair="EURUSD",
                mid_now=1.08,
                held_units_nom=0.0,
                cost_usd=0.0,
                swap_usd=0.0,
                broker_equity=_MOCK_EQUITY_SENTINEL,
                is_mock_backend=False,
                cycle_id=1,
            )

        sentinel_warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "sentinel" in r.getMessage().lower()
        ]
        assert len(sentinel_warnings) == 0, (
            "TC-MC6-6: no sentinel WARNING should fire in mock-test mode; "
            f"got {len(sentinel_warnings)}"
        )
