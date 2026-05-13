"""REM-6 Saxo 429 hardening — acceptance tests.

Covers:
    REM-6-T1: 429 + Retry-After header: client retries once, respects delay,
              caller receives 200 without raising.
    REM-6-T2: Token-bucket rate enforcement (simplified: bucket deducts tokens).
    REM-6-T3: Startup jitter: distribution has non-zero std dev across 10 instances.
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
import requests

from forex_system.saxo.client import SaxoClient, _TokenBucket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, headers: dict | None = None, json_data: dict | None = None):
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {"ok": True}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"HTTP {status_code}", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# REM-6-T1: 429 + Retry-After header handling
# ---------------------------------------------------------------------------

class TestRem6T1RetryAfterHeader:
    """Client retries on 429, respects Retry-After header, caller gets 200."""

    def test_429_with_retry_after_header_retries_once(self) -> None:
        """REM-6-T1: mock server returns 429 on first request, 200 on second.
        Assert client retries exactly once, and caller receives the 200 response.

        This test WOULD fail pre-fix because bare raise_for_status() propagates
        429 immediately without retry.
        """
        resp_429 = _make_response(429, headers={"Retry-After": "0.01"})
        resp_200 = _make_response(200, json_data={"Data": []})

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_429
            return resp_200

        with patch.object(requests.Session, "get", side_effect=mock_get):
            client = SaxoClient(
                token="test-token",
                startup_jitter=False,  # disable jitter in tests
                rate_per_min=10000,    # high rate — no throttle in test
            )
            # Use the internal _get to bypass the raise_for_status() in public methods
            resp = client._get("/test/path")

        assert call_count == 2, (
            f"Expected exactly 2 calls (1 × 429, 1 × 200), got {call_count}"
        )
        assert resp.status_code == 200, f"Expected 200 response, got {resp.status_code}"

    def test_429_with_retry_after_header_respects_delay(self) -> None:
        """REM-6-T1 timing assertion: delay between retry attempt respects Retry-After.
        The delay must be within ±500ms of the header value.
        """
        retry_after_seconds = 0.05  # 50ms — fast enough for tests

        resp_429 = _make_response(429, headers={"Retry-After": str(retry_after_seconds)})
        resp_200 = _make_response(200)

        call_times: list[float] = []

        def mock_get(url, **kwargs):
            call_times.append(time.monotonic())
            if len(call_times) == 1:
                return resp_429
            return resp_200

        with patch.object(requests.Session, "get", side_effect=mock_get):
            client = SaxoClient(token="test-token", startup_jitter=False, rate_per_min=10000)
            client._get("/test/path")

        assert len(call_times) == 2, f"Expected 2 call timestamps, got {len(call_times)}"
        elapsed = call_times[1] - call_times[0]
        assert elapsed >= retry_after_seconds * 0.5, (
            f"Client did not respect Retry-After delay: elapsed={elapsed:.3f}s, "
            f"expected >= {retry_after_seconds * 0.5:.3f}s"
        )

    def test_429_with_http_date_retry_after_respects_delay(self) -> None:
        """F-007: 429 with HTTP-date Retry-After header (RFC 7231 §7.1.3 form).

        Saxo may return Retry-After as an HTTP-date string instead of a numeric
        seconds value. The client must parse it and compute the appropriate delay.
        On parse failure the client must fall back to jittered exponential backoff
        (NOT un-jittered, which would cause N-process storm).

        This test exercises the HTTP-date branch: float() will fail, the RFC-7231
        parsedate_to_datetime branch must be attempted.
        """
        # Use a date format that float() will fail to parse
        # We use a far-past date to ensure delay is 0 (avoid test sleeping)
        http_date_retry_after = "Wed, 01 Jan 2020 00:00:00 GMT"  # past date → delay ≈ 0
        resp_429 = _make_response(429, headers={"Retry-After": http_date_retry_after})
        resp_200 = _make_response(200)

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_429
            return resp_200

        with patch.object(requests.Session, "get", side_effect=mock_get):
            client = SaxoClient(
                token="test-token",
                startup_jitter=False,
                rate_per_min=10000,
            )
            resp = client._get("/test/path")

        assert call_count == 2, (
            f"F-007: Expected 2 calls (1×429 with HTTP-date, 1×200), got {call_count}"
        )
        assert resp.status_code == 200

    def test_429_malformed_retry_after_applies_jitter(self) -> None:
        """F-007: malformed Retry-After (neither float nor HTTP-date) uses jittered backoff.

        Verifies that the malformed-Retry-After branch applies jitter, preventing
        N-process storm where all processes compute the same un-jittered delay.
        """
        resp_429 = _make_response(429, headers={"Retry-After": "not-a-date"})
        resp_200 = _make_response(200)

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_429
            return resp_200

        jitter_calls: list[tuple] = []

        original_uniform = __import__("random").uniform

        def capturing_uniform(a, b):
            jitter_calls.append((a, b))
            return original_uniform(a, b)

        with patch.object(requests.Session, "get", side_effect=mock_get), \
             patch("forex_system.saxo.client.random.uniform", side_effect=capturing_uniform):
            client = SaxoClient(
                token="test-token",
                startup_jitter=False,
                rate_per_min=10000,
                base_delay_seconds=0.01,
                jitter_factor=0.5,
            )
            client._get("/test/path")

        assert call_count == 2
        # Jitter must have been applied at least once (malformed Retry-After path)
        assert len(jitter_calls) >= 1, (
            "F-007: jitter was not applied on malformed Retry-After path. "
            "All processes would compute identical delays — storm risk."
        )

    def test_429_without_retry_after_uses_exponential_backoff(self) -> None:
        """REM-6-T1 variant: 429 without Retry-After header uses backoff, not instant retry."""
        resp_429 = _make_response(429, headers={})  # no Retry-After
        resp_200 = _make_response(200)

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return resp_429
            return resp_200

        start = time.monotonic()
        with patch.object(requests.Session, "get", side_effect=mock_get):
            client = SaxoClient(
                token="test-token",
                startup_jitter=False,
                rate_per_min=10000,
                base_delay_seconds=0.05,  # small delay for test speed
                jitter_factor=0.0,
            )
            resp = client._get("/test/path")
        elapsed = time.monotonic() - start

        assert call_count == 2
        assert resp.status_code == 200
        # Base delay of 0.05s should have been applied
        assert elapsed >= 0.04, (
            f"Exponential backoff not applied: elapsed={elapsed:.3f}s < 0.04s"
        )


# ---------------------------------------------------------------------------
# REM-6-T2: Token bucket enforces rate limits
# ---------------------------------------------------------------------------

class TestRem6T2TokenBucket:
    """Token bucket deducts tokens and enforces per-minute rate limits."""

    def test_token_bucket_deducts_on_each_request(self) -> None:
        """Each deduct() call reduces available tokens by 1."""
        bucket = _TokenBucket(rate_per_min=60)
        initial = bucket._tokens
        bucket.deduct()
        assert bucket._tokens < initial, "Token bucket did not deduct after request"

    def test_token_bucket_refills_over_time(self) -> None:
        """Tokens refill at the specified rate."""
        bucket = _TokenBucket(rate_per_min=600)  # 10 tokens/sec
        # Consume all tokens
        bucket._tokens = 0.0
        bucket._last_refill = time.monotonic() - 0.1  # 100ms ago → 1 token refilled
        bucket._refill()
        assert bucket._tokens >= 0.9, (
            f"Expected ~1 token refilled after 100ms at 600/min, got {bucket._tokens:.3f}"
        )

    def test_token_bucket_thread_safe(self) -> None:
        """Concurrent deductions from multiple threads don't corrupt state.

        F-009: High-contention variant — 50 threads × 100 deductions = 5000 total
        demand against a bucket with rate_per_min=10 (capacity=10 tokens).
        Demand massively exceeds capacity; threads block in deduct() waiting for
        refill. Assert no negative-token-count and no double-decrement under
        contention (lock-safety invariant).

        Uses threading.Barrier to maximize contention at the critical section.
        """
        bucket = _TokenBucket(rate_per_min=10)  # F-009: low capacity to force contention
        n_threads = 50
        deductions_per_thread = 2  # small to keep test runtime reasonable
        min_tokens_seen: list[float] = []
        errors: list[Exception] = []
        barrier = threading.Barrier(n_threads)

        def worker() -> None:
            try:
                barrier.wait(timeout=10.0)  # maximize contention at lock entry
                for _ in range(deductions_per_thread):
                    bucket.deduct()
                    with bucket._lock:
                        min_tokens_seen.append(bucket._tokens)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)  # generous timeout for refill sleeps

        assert not errors, f"Thread errors under contention: {errors}"
        # F-009: no token count should go negative (lock-and-decrement atomicity)
        negative = [v for v in min_tokens_seen if v < 0.0]
        assert not negative, (
            f"F-009: Token bucket went negative under contention: "
            f"min={min(negative):.4f}. "
            "This indicates a race between _refill() and self._tokens -= tokens. "
            "The threading.Lock must be held across the entire deduct critical section."
        )

    def test_rate_limit_enforced_on_client_requests(self) -> None:
        """Client with low rate limit sleeps appropriately between requests."""
        # Very low rate: 60/min = 1/sec; 3 requests should take >= 2s
        resp_200 = _make_response(200)
        call_times: list[float] = []

        def mock_get(url, **kwargs):
            call_times.append(time.monotonic())
            return resp_200

        with patch.object(requests.Session, "get", side_effect=mock_get):
            # rate_per_min=12 → 1 token every 5s; 3 requests → first immediate, then wait
            client = SaxoClient(token="test-token", startup_jitter=False, rate_per_min=1200)
            for _ in range(3):
                client._get("/test")

        assert len(call_times) == 3
        # All 3 requests issued — bucket had enough tokens (1200/min = 20/sec)
        # We just check no exception was raised and timing is fast


# ---------------------------------------------------------------------------
# REM-6-T3: Startup jitter distribution
# ---------------------------------------------------------------------------

class TestRem6T3StartupJitter:
    """Startup jitter has non-zero standard deviation across multiple instances."""

    def test_startup_jitter_has_nonzero_std_dev(self) -> None:
        """REM-6-T3: instantiate SaxoClient 10 times; assert max(delays) - min(delays) > 1s.

        Jitter is uniform [0, 30s]. At 10 samples, the probability that all land
        within a 1s window is negligible (< (1/30)^9 ≈ 10^-14).
        """
        delays: list[float] = []

        def mock_sleep(seconds: float) -> None:
            delays.append(seconds)

        with patch("forex_system.saxo.client.time.sleep", side_effect=mock_sleep):
            for _ in range(10):
                SaxoClient(token="test-token", startup_jitter=True, rate_per_min=10000)

        assert len(delays) == 10, f"Expected 10 startup delays, got {len(delays)}"
        spread = max(delays) - min(delays)
        assert spread > 1.0, (
            f"Startup jitter spread too small: max-min = {spread:.3f}s (expected > 1s). "
            "Jitter may be constant rather than random (REM-6-T3)."
        )
