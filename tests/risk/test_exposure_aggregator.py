"""Tests for exposure_aggregator — CRO binding constraint #1.

Covers:
    - is_jpy_correlated for all 3 universe pairs
    - check_dispatch_allowed allows at 14% JPY-correlated
    - check_dispatch_allowed blocks at 16% JPY-correlated
    - check_dispatch_allowed blocks on 5 active strategies (limit 4)
    - check_dispatch_allowed blocks on 7 concurrent positions (limit 6)
    - Structured log line emitted in both allow and block cases
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from forex_system.core.types import Direction, Position
from forex_system.risk.exposure_aggregator import (
    AggregationGateBlocked,
    ExposureSnapshot,
    check_dispatch_allowed,
    compute_exposure,
    is_jpy_correlated,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = pd.Timestamp("2026-04-28T12:00:00", tz="UTC")


def _make_position(pair: str, size: float, entry_price: float) -> Position:
    return Position(
        pair=pair,
        direction=Direction.LONG if size > 0 else Direction.SHORT,
        size=abs(size),
        entry_price=entry_price,
        entry_time=_NOW,
        unrealized_pnl=0.0,
    )


def _snapshot(
    *,
    jpy_pct: float,
    active_strategies: int = 1,
    open_positions: int = 1,
    jpy_notional: float = 1_000.0,
) -> ExposureSnapshot:
    """Build a minimal ExposureSnapshot for gate tests."""
    total = jpy_notional / jpy_pct if jpy_pct > 0 else 1_000.0
    return ExposureSnapshot(
        jpy_correlated_notional=jpy_notional,
        total_paper_book_notional=total,
        jpy_correlated_pct=jpy_pct,
        active_paper_strategies=active_strategies,
        concurrent_open_positions=open_positions,
    )


# ---------------------------------------------------------------------------
# is_jpy_correlated — 3 universe pairs
# ---------------------------------------------------------------------------


class TestIsJpyCorrelated:
    def test_usdjpy_is_correlated(self) -> None:
        assert is_jpy_correlated("USDJPY") is True

    def test_gbpusd_is_correlated(self) -> None:
        # Indirect JPY tail risk per CRO envelope
        assert is_jpy_correlated("GBPUSD") is True

    def test_eurusd_is_not_correlated(self) -> None:
        assert is_jpy_correlated("EURUSD") is False

    def test_case_insensitive(self) -> None:
        assert is_jpy_correlated("usdjpy") is True
        assert is_jpy_correlated("eurusd") is False


# ---------------------------------------------------------------------------
# compute_exposure — basic sanity
# ---------------------------------------------------------------------------


class TestComputeExposure:
    def test_empty_positions(self) -> None:
        snap = compute_exposure([])
        assert snap.total_paper_book_notional == 0.0
        assert snap.jpy_correlated_notional == 0.0
        assert snap.jpy_correlated_pct == 0.0
        assert snap.concurrent_open_positions == 0

    def test_single_jpy_position(self) -> None:
        pos = _make_position("USDJPY", size=10_000, entry_price=155.0)
        snap = compute_exposure([pos])
        assert snap.total_paper_book_notional == pytest.approx(10_000 * 155.0)
        assert snap.jpy_correlated_notional == pytest.approx(10_000 * 155.0)
        assert snap.jpy_correlated_pct == pytest.approx(1.0)

    def test_mixed_positions(self) -> None:
        jpy_pos = _make_position("USDJPY", size=10_000, entry_price=155.0)
        eur_pos = _make_position("EURUSD", size=100_000, entry_price=1.10)
        snap = compute_exposure([jpy_pos, eur_pos])
        jpy_notional = 10_000 * 155.0
        eur_notional = 100_000 * 1.10
        total = jpy_notional + eur_notional
        assert snap.total_paper_book_notional == pytest.approx(total)
        assert snap.jpy_correlated_notional == pytest.approx(jpy_notional)
        assert snap.jpy_correlated_pct == pytest.approx(jpy_notional / total)


# ---------------------------------------------------------------------------
# check_dispatch_allowed — allow at 14%
# ---------------------------------------------------------------------------


class TestCheckDispatchAllowedPasses:
    def test_allow_at_14_pct_jpy(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.14, active_strategies=2, open_positions=3)
        with caplog.at_level(logging.INFO, logger="exposure_aggregator"):
            check_dispatch_allowed(
                snap,
                max_correlated_pct=0.15,
                max_active_strategies=4,
                max_concurrent_positions=6,
            )
        # Verify structured log emitted
        assert any("DISPATCH_ALLOWED" in r.message for r in caplog.records)

    def test_allow_log_contains_all_fields(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.10, active_strategies=1, open_positions=2)
        with caplog.at_level(logging.INFO, logger="exposure_aggregator"):
            check_dispatch_allowed(
                snap,
                max_correlated_pct=0.15,
                max_active_strategies=4,
                max_concurrent_positions=6,
            )
        log_text = " ".join(r.message for r in caplog.records)
        assert "jpy_correlated_pct" in log_text
        assert "active_strategies" in log_text
        assert "open_positions" in log_text
        assert "limits" in log_text


# ---------------------------------------------------------------------------
# check_dispatch_allowed — block at 16%
# ---------------------------------------------------------------------------


class TestCheckDispatchAllowedBlocksJpy:
    def test_blocks_at_16_pct_jpy(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.16, active_strategies=1, open_positions=1)
        with caplog.at_level(logging.WARNING, logger="exposure_aggregator"):
            with pytest.raises(AggregationGateBlocked) as exc_info:
                check_dispatch_allowed(
                    snap,
                    max_correlated_pct=0.15,
                    max_active_strategies=4,
                    max_concurrent_positions=6,
                )
        assert "DISPATCH_BLOCKED" in str(exc_info.value)
        assert any("DISPATCH_BLOCKED" in r.message for r in caplog.records)

    def test_block_log_contains_all_fields(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.20)
        with caplog.at_level(logging.WARNING, logger="exposure_aggregator"):
            with pytest.raises(AggregationGateBlocked):
                check_dispatch_allowed(
                    snap,
                    max_correlated_pct=0.15,
                    max_active_strategies=4,
                    max_concurrent_positions=6,
                )
        log_text = " ".join(r.message for r in caplog.records)
        assert "jpy_correlated_pct" in log_text
        assert "max_correlated_pct" in log_text


# ---------------------------------------------------------------------------
# check_dispatch_allowed — block on 5 active strategies (limit 4)
# ---------------------------------------------------------------------------


class TestCheckDispatchAllowedBlocksStrategies:
    def test_blocks_at_5_strategies(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.10, active_strategies=5, open_positions=3)
        with caplog.at_level(logging.WARNING, logger="exposure_aggregator"):
            with pytest.raises(AggregationGateBlocked) as exc_info:
                check_dispatch_allowed(
                    snap,
                    max_correlated_pct=0.15,
                    max_active_strategies=4,
                    max_concurrent_positions=6,
                )
        assert "active_strategies" in str(exc_info.value)
        assert any("DISPATCH_BLOCKED" in r.message for r in caplog.records)

    def test_allows_at_exactly_4_strategies(self) -> None:
        snap = _snapshot(jpy_pct=0.10, active_strategies=4, open_positions=3)
        # Should not raise
        check_dispatch_allowed(
            snap,
            max_correlated_pct=0.15,
            max_active_strategies=4,
            max_concurrent_positions=6,
        )


# ---------------------------------------------------------------------------
# check_dispatch_allowed — block on 7 concurrent positions (limit 6)
# ---------------------------------------------------------------------------


class TestCheckDispatchAllowedBlocksPositions:
    def test_blocks_at_7_positions(self, caplog: pytest.LogCaptureFixture) -> None:
        snap = _snapshot(jpy_pct=0.10, active_strategies=2, open_positions=7)
        with caplog.at_level(logging.WARNING, logger="exposure_aggregator"):
            with pytest.raises(AggregationGateBlocked) as exc_info:
                check_dispatch_allowed(
                    snap,
                    max_correlated_pct=0.15,
                    max_active_strategies=4,
                    max_concurrent_positions=6,
                )
        assert "open_positions" in str(exc_info.value)
        assert any("DISPATCH_BLOCKED" in r.message for r in caplog.records)

    def test_allows_at_exactly_6_positions(self) -> None:
        snap = _snapshot(jpy_pct=0.10, active_strategies=2, open_positions=6)
        # Should not raise
        check_dispatch_allowed(
            snap,
            max_correlated_pct=0.15,
            max_active_strategies=4,
            max_concurrent_positions=6,
        )
