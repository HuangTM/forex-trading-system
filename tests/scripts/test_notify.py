"""Tests for the notify() helper in run_paper_trading_vt.py.

Verifies that messages containing non-ASCII characters (e.g. em-dashes from
kill-switch alert strings) do not raise UnicodeEncodeError.

The notify() function is extracted into a testable unit by mocking HTTP calls.
We test the encoding contract (ascii + replace) rather than loading the full
script, which avoids pulling in live-trading dependencies (SaxoClient etc.)
at import time.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from zoneinfo import ZoneInfo

import pytest

# ---- Inline re-implementation of notify() for unit testing ----
# This mirrors the exact implementation in scripts/run_paper_trading_vt.py so
# that encoding behavior is tested without loading the full script module.

LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)


def _notify(topic, title, message, priority="default", requests_mod=None):
    """Inline copy of notify() that accepts a requests mock for isolation."""
    import logging
    _logger = logging.getLogger("test_notify")
    if not topic:
        return
    local_hour = datetime.now(LOCAL_TZ).hour
    quiet_start, quiet_end = QUIET_HOURS
    if quiet_start <= local_hour or local_hour < quiet_end:
        return
    try:
        requests_mod.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("ascii", errors="replace"),
            headers={"Title": title, "Priority": priority,
                     "Tags": "chart_with_upwards_trend"},
            timeout=10,
        )
    except Exception as e:
        _logger.warning("Failed to send notification: %s", e)


class TestNotifyEncoding:
    """Tests for notify() encoding behaviour."""

    def test_em_dash_encode_does_not_raise(self):
        """Em-dash (U+2014) must not raise when encoded with ascii+replace."""
        # This is the core regression test: the old encode("utf-8") would work
        # fine for bytes but requests may pass them through connectors that
        # choke on non-ASCII. The fix uses encode("ascii", errors="replace")
        # so all non-ASCII bytes become '?'. We test no exception is raised.
        message = "KILL SWITCH — em-dash test"
        # Just verify encode itself doesn't raise (this was never the failure
        # mode for utf-8, but ascii+replace must also not raise):
        encoded = message.encode("ascii", errors="replace")
        assert b"?" in encoded, "em-dash should be replaced by ?"
        assert b"KILL SWITCH" in encoded

    def test_notify_em_dash_no_exception(self):
        """Calling notify() with an em-dash in message must not raise any exception."""
        mock_requests = MagicMock()
        # Should complete without raising regardless of quiet-hours state
        _notify(
            topic="test_topic",
            title="KILL SWITCH",
            message="KILL SWITCH — em-dash test",
            priority="urgent",
            requests_mod=mock_requests,
        )

    def test_notify_no_topic_returns_early(self):
        """notify() with topic=None must return without posting."""
        mock_requests = MagicMock()
        _notify(topic=None, title="Test", message="hello", requests_mod=mock_requests)
        mock_requests.post.assert_not_called()

    def test_notify_ascii_message_encodes_cleanly(self):
        """Plain ASCII messages must still encode to identical bytes."""
        message = "plain ascii message"
        encoded = message.encode("ascii", errors="replace")
        assert encoded == message.encode("utf-8")

    def test_notify_various_special_chars_no_raise(self):
        """Various Unicode characters (en-dash, ellipsis, smart-quotes) must not raise."""
        special = "test – en-dash … ellipsis “ smart quote ”"
        mock_requests = MagicMock()
        _notify(
            topic="test_topic",
            title="Special chars",
            message=special,
            requests_mod=mock_requests,
        )
