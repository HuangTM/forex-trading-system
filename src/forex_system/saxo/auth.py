"""OAuth2 PKCE token management for Saxo Bank API.

Handles the full token lifecycle:
    1. Initial login via browser (PKCE flow)
    2. Automatic refresh before access token expiry
    3. Persistent storage of refresh tokens
    4. Fuel gauge: time-to-auth-death monitoring

Token lifetimes (Saxo):
    - Access token: 20 minutes
    - Refresh token: 40 minutes (single-use — each refresh returns a new pair)
    - Missing a refresh window = auth chain death = manual re-login required

Usage:
    auth = SaxoAuth(client_id="...", redirect_uri="http://localhost:9160/callback")

    # First time: opens browser for login
    auth.login()

    # Before each API call (auto-refreshes if needed):
    token = auth.ensure_valid()

    # Or integrate with SaxoClient:
    client = SaxoClient.from_auth(auth)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

logger = logging.getLogger(__name__)

# Saxo OAuth endpoints
SIM_AUTH_URL = "https://sim.logonvalidation.net/authorize"
SIM_TOKEN_URL = "https://sim.logonvalidation.net/token"
LIVE_AUTH_URL = "https://live.logonvalidation.net/authorize"
LIVE_TOKEN_URL = "https://live.logonvalidation.net/token"

# Safety margins
REFRESH_BEFORE_EXPIRY_SECONDS = 120  # Refresh 2 min before access token dies
AUTH_DEATH_WARNING_MINUTES = 2.0  # Emergency flatten threshold

# Default token storage
DEFAULT_TOKEN_FILE = "data/.saxo_tokens.json"


class AuthChainDead(Exception):
    """Raised when the refresh token has expired — manual re-login required."""


@dataclass
class TokenState:
    """Current token state."""

    access_token: str
    refresh_token: str
    access_expires_at: float  # Unix timestamp
    refresh_expires_at: float  # Unix timestamp

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "access_expires_at": self.access_expires_at,
            "refresh_expires_at": self.refresh_expires_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TokenState:
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            access_expires_at=d["access_expires_at"],
            refresh_expires_at=d["refresh_expires_at"],
        )


@dataclass
class SaxoAuth:
    """OAuth2 PKCE token manager for Saxo Bank.

    Manages the full lifecycle: login, refresh, persistence, fuel gauge.
    Thread-safe for refresh operations.
    """

    client_id: str
    redirect_uri: str = "http://localhost:9160/callback"
    token_file: str | Path = DEFAULT_TOKEN_FILE
    live: bool = False

    # Internal state
    _tokens: TokenState | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _keepalive_thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _keepalive_stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    def __post_init__(self):
        self.token_file = Path(self.token_file)
        self._try_load_tokens()

    # --- Public API ---

    def ensure_valid(self) -> str:
        """Return a valid access token, auto-refreshing if needed.

        Raises AuthChainDead if the refresh token has expired.
        """
        with self._lock:
            if self._tokens is None:
                raise AuthChainDead("No tokens available — call login() first")

            now = time.time()

            # Check if refresh token is dead
            if now >= self._tokens.refresh_expires_at:
                raise AuthChainDead(
                    "Refresh token expired — manual re-login required"
                )

            # Refresh if access token is close to expiry
            if now >= self._tokens.access_expires_at - REFRESH_BEFORE_EXPIRY_SECONDS:
                self._refresh()

            return self._tokens.access_token

    @property
    def minutes_to_auth_death(self) -> float:
        """Minutes until refresh token expires (= permanent auth loss)."""
        with self._lock:
            tokens = self._tokens
        if tokens is None:
            return 0.0
        remaining = tokens.refresh_expires_at - time.time()
        return max(0.0, remaining / 60.0)

    @property
    def minutes_to_access_expiry(self) -> float:
        """Minutes until access token expires (auto-refresh handles this)."""
        with self._lock:
            tokens = self._tokens
        if tokens is None:
            return 0.0
        remaining = tokens.access_expires_at - time.time()
        return max(0.0, remaining / 60.0)

    def should_emergency_flatten(self) -> bool:
        """True if < 2 minutes to auth death."""
        return self.minutes_to_auth_death < AUTH_DEATH_WARNING_MINUTES

    @property
    def is_authenticated(self) -> bool:
        """True if we have tokens (may still need refresh)."""
        with self._lock:
            return self._tokens is not None

    @property
    def fuel_gauge(self) -> str:
        """Human-readable auth status."""
        with self._lock:
            tokens = self._tokens
        if tokens is None:
            return "NOT AUTHENTICATED"
        remaining = tokens.refresh_expires_at - time.time()
        death = max(0.0, remaining / 60.0)
        if death <= 0:
            return "AUTH DEAD — re-login required"
        if death < AUTH_DEATH_WARNING_MINUTES:
            return f"CRITICAL — {death:.1f}min to auth death"
        return f"OK — {death:.0f}min remaining"

    def login(self) -> None:
        """Start the PKCE login flow — opens browser for Saxo login.

        Blocks until the callback is received or times out.
        """
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )

        auth_url = LIVE_AUTH_URL if self.live else SIM_AUTH_URL
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        full_url = f"{auth_url}?{urlencode(params)}"

        # Start local server to receive callback
        auth_code = _wait_for_callback(self.redirect_uri)

        logger.info("Opening browser for Saxo login...")
        webbrowser.open(full_url)

        code = auth_code.wait(timeout=300)  # 5 min timeout
        if code is None:
            raise AuthChainDead("Login timed out — no callback received")

        # Exchange code for tokens
        self._exchange_code(code, code_verifier)
        logger.info("Login successful — tokens acquired")

    def login_with_token(self, access_token: str, expires_in: int = 86400) -> None:
        """Initialize from a static developer token (24h tokens from Saxo portal).

        Use this for development instead of the full PKCE flow.
        """
        now = time.time()
        tokens = TokenState(
            access_token=access_token,
            refresh_token="",  # No refresh for dev tokens
            access_expires_at=now + expires_in,
            refresh_expires_at=now + expires_in,  # Same as access for dev tokens
        )
        with self._lock:
            self._tokens = tokens
        self._save_tokens()
        logger.info("Initialized with developer token (expires in %ds)", expires_in)

    def start_keepalive(self, interval_seconds: int = 900) -> None:
        """Start background thread that refreshes tokens before they expire.

        Saxo refresh tokens are single-use and expire in ~40 minutes.
        This thread calls ensure_valid() every `interval_seconds` (default 15 min)
        to keep the auth chain alive during long sleeps between trading cycles.

        Safe to call multiple times — restarts if already running.
        """
        self.stop_keepalive()

        def _keepalive_loop():
            while not self._keepalive_stop.is_set():
                try:
                    self.ensure_valid()
                    logger.debug(
                        "Keepalive refresh OK — %.1f min to auth death",
                        self.minutes_to_auth_death,
                    )
                except AuthChainDead as e:
                    logger.error("Keepalive: auth chain dead — %s", e)
                    break
                except Exception as e:
                    logger.warning("Keepalive refresh error: %s", e)
                self._keepalive_stop.wait(timeout=interval_seconds)

        self._keepalive_stop.clear()
        self._keepalive_thread = threading.Thread(
            target=_keepalive_loop, daemon=True, name="saxo-keepalive",
        )
        self._keepalive_thread.start()
        logger.info("Token keepalive started (every %ds)", interval_seconds)

    def stop_keepalive(self) -> None:
        """Stop the background keepalive thread."""
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_stop.set()
            self._keepalive_thread.join(timeout=5)
            logger.info("Token keepalive stopped")

    # --- Internal ---

    def _exchange_code(self, code: str, code_verifier: str) -> None:
        """Exchange authorization code for access + refresh tokens."""
        token_url = LIVE_TOKEN_URL if self.live else SIM_TOKEN_URL
        resp = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
            },
        )
        resp.raise_for_status()
        self._apply_token_response(resp.json())

    def _refresh(self) -> None:
        """Refresh the access token using the refresh token.

        Must be called under self._lock.
        """
        if not self._tokens or not self._tokens.refresh_token:
            raise AuthChainDead("No refresh token available")

        token_url = LIVE_TOKEN_URL if self.live else SIM_TOKEN_URL
        try:
            resp = requests.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._tokens.refresh_token,
                    "client_id": self.client_id,
                },
            )
            resp.raise_for_status()
            self._apply_token_response(resp.json())
            logger.info(
                "Token refreshed — %.1f min to auth death",
                self.minutes_to_auth_death,
            )
        except Exception as e:
            logger.error("Token refresh failed: %s", e)
            raise AuthChainDead(f"Token refresh failed: {e}") from e

    def _apply_token_response(self, data: dict) -> None:
        """Update token state from OAuth response."""
        now = time.time()
        access_expires_in = data.get("expires_in", 1200)  # Default 20 min
        # Use actual refresh expiry from response; fallback to 2x access lifetime
        refresh_expires_in = data.get("refresh_token_expires_in", access_expires_in * 2)

        tokens = TokenState(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            access_expires_at=now + access_expires_in,
            refresh_expires_at=now + refresh_expires_in,
        )
        with self._lock:
            self._tokens = tokens
        self._save_tokens()

    def _save_tokens(self) -> None:
        """Persist tokens to disk (owner-readable only)."""
        if self._tokens is None:
            return
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.token_file.with_suffix(".tmp")
        try:
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(self._tokens.to_dict(), f, indent=2)
            os.replace(tmp, self.token_file)
        except Exception as e:
            logger.warning("Failed to save tokens: %s", e)
            if tmp.exists():
                tmp.unlink()

    def _try_load_tokens(self) -> None:
        """Load tokens from disk if available and not expired."""
        if not self.token_file.exists():
            return
        try:
            data = json.loads(self.token_file.read_text())
            tokens = TokenState.from_dict(data)
            # Only use if refresh token hasn't expired
            if tokens.refresh_expires_at > time.time():
                self._tokens = tokens
                logger.info(
                    "Loaded saved tokens — %.1f min to auth death",
                    self.minutes_to_auth_death,
                )
            else:
                logger.warning("Saved tokens expired — re-login required")
        except Exception as e:
            logger.warning("Could not load saved tokens: %s", e)


# --- Local callback server for PKCE flow ---

class _AuthCodeResult:
    """Thread-safe container for the authorization code."""

    def __init__(self):
        self._code: str | None = None
        self._error: str | None = None
        self._event = threading.Event()

    def set(self, code: str) -> None:
        self._code = code
        self._event.set()

    def set_error(self, error: str) -> None:
        self._error = error
        self._event.set()

    def wait(self, timeout: float = 300) -> str | None:
        self._event.wait(timeout=timeout)
        if self._error:
            raise AuthChainDead(f"OAuth login failed: {self._error}")
        return self._code


def _wait_for_callback(redirect_uri: str) -> _AuthCodeResult:
    """Start a local HTTP server to receive the OAuth callback.

    Returns an _AuthCodeResult that will be populated when the callback arrives.
    """
    parsed = urlparse(redirect_uri)
    port = parsed.port or 9160
    result = _AuthCodeResult()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            if code:
                result.set(code)
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Login successful!</h2>"
                    b"<p>You can close this window and return to the terminal.</p>"
                    b"</body></html>"
                )
            else:
                error = query.get("error", ["unknown"])[0]
                result.set_error(error)
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>Login failed: {error}</h2></body></html>".encode()
                )

        def log_message(self, format, *args):
            pass  # Suppress default HTTP logging

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 300  # 5 min timeout

    def serve():
        server.handle_request()  # Handle single request then stop
        server.server_close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    logger.info("Callback server listening on port %d", port)

    return result
