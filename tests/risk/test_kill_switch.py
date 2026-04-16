"""Tests for the binary kill switch."""

from forex_system.risk.kill_switch import (
    MAX_DAILY_LOSS_PCT,
    KillSwitch,
    TriggerReason,
)


class TestKillSwitchDefaults:
    def test_starts_not_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.is_triggered
        assert ks.status_line == "OK"

    def test_default_threshold_is_two_percent(self):
        assert MAX_DAILY_LOSS_PCT == 0.02

    def test_no_events_initially(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.events == []
        assert ks.last_event is None


class TestDailyLossTrigger:
    def test_small_loss_does_not_trigger(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.check_and_trigger(99_000)  # -1%
        assert not ks.is_triggered

    def test_loss_at_threshold_triggers(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.check_and_trigger(98_000)  # exactly -2%
        assert ks.is_triggered

    def test_loss_beyond_threshold_triggers(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.check_and_trigger(95_000)  # -5%
        assert ks.is_triggered

    def test_gain_does_not_trigger(self):
        ks = KillSwitch(initial_equity=100_000)
        assert not ks.check_and_trigger(110_000)
        assert not ks.is_triggered

    def test_trigger_records_event(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.check_and_trigger(97_000)
        assert len(ks.events) == 1
        assert ks.events[0].reason == TriggerReason.DAILY_LOSS
        assert ks.events[0].equity_at_trigger == 97_000

    def test_custom_threshold(self):
        ks = KillSwitch(initial_equity=100_000, max_daily_loss_pct=0.05)
        assert not ks.check_and_trigger(96_000)  # -4%, within 5%
        assert ks.check_and_trigger(94_000)  # -6%, beyond 5%
        assert ks.is_triggered


class TestManualTrigger:
    def test_trigger_reconciliation(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.RECONCILIATION, "size mismatch on USDJPY", 100_000)
        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.RECONCILIATION

    def test_trigger_auth_death(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.AUTH_DEATH, "token expires in 90s", 100_000)
        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.AUTH_DEATH

    def test_trigger_is_idempotent(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test 1", 100_000)
        ks.trigger(TriggerReason.MANUAL, "test 2", 100_000)
        assert len(ks.events) == 1  # Second trigger ignored

    def test_check_after_trigger_stays_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        assert ks.check_and_trigger(110_000)  # Even with gains


class TestReset:
    def test_reset_clears_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        ks.reset(operator="HuangTM")
        assert not ks.is_triggered
        assert ks.status_line == "OK"

    def test_reset_preserves_event_history(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "test", 100_000)
        ks.reset(operator="HuangTM")
        assert len(ks.events) == 1  # History preserved

    def test_reset_when_not_triggered_is_noop(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.reset(operator="HuangTM")
        assert not ks.is_triggered

    def test_can_trigger_again_after_reset(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.MANUAL, "first", 100_000)
        ks.reset(operator="HuangTM")
        ks.trigger(TriggerReason.MANUAL, "second", 95_000)
        assert ks.is_triggered
        assert len(ks.events) == 2


class TestStatusLine:
    def test_ok_when_not_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        assert ks.status_line == "OK"

    def test_shows_reason_when_triggered(self):
        ks = KillSwitch(initial_equity=100_000)
        ks.trigger(TriggerReason.DAILY_LOSS, "lost too much", 95_000)
        assert "HALTED" in ks.status_line
        assert "daily_loss_exceeded" in ks.status_line
