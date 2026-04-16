"""Tests for Saxo OAuth token management."""

import json
import threading
import time
from unittest.mock import patch

import pytest

from forex_system.saxo.auth import (
    AUTH_DEATH_WARNING_MINUTES,
    AuthChainDead,
    SaxoAuth,
    TokenState,
)


@pytest.fixture
def tmp_token_file(tmp_path):
    return tmp_path / "tokens.json"


@pytest.fixture
def auth(tmp_token_file):
    return SaxoAuth(client_id="test_client", token_file=tmp_token_file)


class TestTokenState:
    def test_roundtrip_serialization(self):
        now = time.time()
        state = TokenState(
            access_token="access_123",
            refresh_token="refresh_456",
            access_expires_at=now + 1200,
            refresh_expires_at=now + 2400,
        )
        d = state.to_dict()
        restored = TokenState.from_dict(d)
        assert restored.access_token == "access_123"
        assert restored.refresh_token == "refresh_456"
        assert restored.access_expires_at == state.access_expires_at


class TestSaxoAuthInit:
    def test_starts_unauthenticated(self, auth):
        assert not auth.is_authenticated
        assert auth.minutes_to_auth_death == 0.0
        assert auth.fuel_gauge == "NOT AUTHENTICATED"

    def test_loads_saved_tokens(self, tmp_token_file):
        # Pre-save valid tokens
        now = time.time()
        tokens = TokenState(
            access_token="saved_access",
            refresh_token="saved_refresh",
            access_expires_at=now + 1200,
            refresh_expires_at=now + 2400,
        )
        tmp_token_file.write_text(json.dumps(tokens.to_dict()))

        auth = SaxoAuth(client_id="test", token_file=tmp_token_file)
        assert auth.is_authenticated
        assert auth.minutes_to_auth_death > 0

    def test_ignores_expired_saved_tokens(self, tmp_token_file):
        # Pre-save expired tokens
        now = time.time()
        tokens = TokenState(
            access_token="old_access",
            refresh_token="old_refresh",
            access_expires_at=now - 100,
            refresh_expires_at=now - 50,
        )
        tmp_token_file.write_text(json.dumps(tokens.to_dict()))

        auth = SaxoAuth(client_id="test", token_file=tmp_token_file)
        assert not auth.is_authenticated


class TestLoginWithToken:
    def test_sets_tokens(self, auth):
        auth.login_with_token("dev_token_123", expires_in=86400)
        assert auth.is_authenticated
        assert auth.minutes_to_auth_death > 1400  # ~24h in minutes

    def test_persists_to_file(self, auth, tmp_token_file):
        auth.login_with_token("dev_token_123")
        assert tmp_token_file.exists()
        data = json.loads(tmp_token_file.read_text())
        assert data["access_token"] == "dev_token_123"


class TestEnsureValid:
    def test_raises_when_no_tokens(self, auth):
        with pytest.raises(AuthChainDead, match="No tokens"):
            auth.ensure_valid()

    def test_returns_access_token_when_valid(self, auth):
        auth.login_with_token("valid_token", expires_in=86400)
        token = auth.ensure_valid()
        assert token == "valid_token"

    def test_raises_when_refresh_expired(self, auth):
        now = time.time()
        auth._tokens = TokenState(
            access_token="expired_access",
            refresh_token="expired_refresh",
            access_expires_at=now - 100,
            refresh_expires_at=now - 50,
        )
        with pytest.raises(AuthChainDead, match="Refresh token expired"):
            auth.ensure_valid()

    def test_triggers_refresh_when_access_near_expiry(self, auth):
        now = time.time()
        auth._tokens = TokenState(
            access_token="old_access",
            refresh_token="valid_refresh",
            access_expires_at=now + 60,  # Only 1 min left (< 2 min threshold)
            refresh_expires_at=now + 2400,
        )

        # Mock the refresh to succeed
        mock_response = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 1200,
        }
        with patch("forex_system.saxo.auth.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            mock_post.return_value.json.return_value = mock_response
            token = auth.ensure_valid()

        assert token == "new_access"
        assert auth._tokens.refresh_token == "new_refresh"


class TestFuelGauge:
    def test_not_authenticated(self, auth):
        assert auth.fuel_gauge == "NOT AUTHENTICATED"

    def test_ok(self, auth):
        auth.login_with_token("token", expires_in=86400)
        assert auth.fuel_gauge.startswith("OK")

    def test_critical_when_near_death(self, auth):
        now = time.time()
        auth._tokens = TokenState(
            access_token="access",
            refresh_token="refresh",
            access_expires_at=now + 30,
            refresh_expires_at=now + 60,  # 1 min left
        )
        assert "CRITICAL" in auth.fuel_gauge

    def test_dead(self, auth):
        now = time.time()
        auth._tokens = TokenState(
            access_token="access",
            refresh_token="refresh",
            access_expires_at=now - 100,
            refresh_expires_at=now - 50,
        )
        assert "DEAD" in auth.fuel_gauge


class TestEmergencyFlatten:
    def test_not_triggered_when_healthy(self, auth):
        auth.login_with_token("token", expires_in=86400)
        assert not auth.should_emergency_flatten()

    def test_triggered_when_near_death(self, auth):
        now = time.time()
        auth._tokens = TokenState(
            access_token="access",
            refresh_token="refresh",
            access_expires_at=now + 30,
            refresh_expires_at=now + 60,
        )
        assert auth.should_emergency_flatten()

    def test_threshold_is_two_minutes(self):
        assert AUTH_DEATH_WARNING_MINUTES == 2.0


class TestThreadSafety:
    def test_concurrent_reads_during_write(self, auth):
        """Properties should not crash when tokens are being replaced."""
        auth.login_with_token("initial_token", expires_in=86400)
        errors = []

        def read_properties():
            try:
                for _ in range(1000):
                    auth.minutes_to_auth_death
                    auth.minutes_to_access_expiry
                    auth.is_authenticated
                    auth.fuel_gauge
                    auth.should_emergency_flatten()
            except Exception as e:
                errors.append(e)

        def write_tokens():
            try:
                for i in range(1000):
                    auth.login_with_token(f"token_{i}", expires_in=86400)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=read_properties),
            threading.Thread(target=read_properties),
            threading.Thread(target=write_tokens),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread-safety errors: {errors}"


class TestTokenPersistence:
    def test_atomic_write(self, auth, tmp_token_file):
        auth.login_with_token("token_1")
        assert tmp_token_file.exists()
        # No .tmp file left behind
        assert not tmp_token_file.with_suffix(".tmp").exists()

    def test_survives_missing_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "tokens.json"
        auth = SaxoAuth(client_id="test", token_file=nested)
        auth.login_with_token("token")
        assert nested.exists()
