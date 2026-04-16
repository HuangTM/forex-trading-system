"""Tests for TradeLog."""

from __future__ import annotations

import pandas as pd
import pytest

from forex_system.analysis.trade_log import TradeLog
from forex_system.core.types import Direction, ExecutionResult


@pytest.fixture
def trade_log(tmp_path):
    tl = TradeLog(output_dir=tmp_path / "trades")
    yield tl
    tl.close()


@pytest.fixture
def sample_result():
    return ExecutionResult(
        pair="USDJPY",
        direction=Direction.LONG,
        size=1000,
        requested_price=145.50,
        fill_price=145.52,
        fill_time=pd.Timestamp("2024-01-15 10:00", tz="UTC"),
        slippage_pips=0.2,
        spread_at_fill=1.5,
        success=True,
        error=None,
    )


class TestTradeLog:

    def test_record_and_load(self, trade_log, sample_result):
        trade_log.record(sample_result, signal=0.8, strategy="carry_momentum")
        trade_log.flush()

        df = trade_log.load()
        assert len(df) == 1
        assert df["pair"].iloc[0] == "USDJPY"
        assert df["signal"].iloc[0] == 0.8
        assert df["success"].iloc[0] == True  # noqa: E712

    def test_filter_by_pair(self, trade_log, sample_result):
        trade_log.record(sample_result, signal=0.8, strategy="cm")

        gbp_result = ExecutionResult(
            pair="GBPJPY", direction=Direction.LONG, size=500,
            requested_price=185.0, fill_price=185.02,
            fill_time=pd.Timestamp("2024-01-15 10:01", tz="UTC"),
            slippage_pips=0.3, spread_at_fill=2.0, success=True,
        )
        trade_log.record(gbp_result, signal=0.6, strategy="cm")
        trade_log.flush()

        usdjpy = trade_log.load(pair="USDJPY")
        assert len(usdjpy) == 1
        assert usdjpy["pair"].iloc[0] == "USDJPY"

    def test_filter_by_source(self, trade_log, sample_result):
        trade_log.record(sample_result, signal=0.8, strategy="cm", source="paper")
        trade_log.record(sample_result, signal=0.8, strategy="cm", source="live")
        trade_log.flush()

        paper = trade_log.load(source="paper")
        assert len(paper) == 1

    def test_context_stored(self, trade_log, sample_result):
        trade_log.record(
            sample_result, signal=0.8, strategy="cm",
            context={"atr": 1.5, "carry_diff": 0.03},
        )
        trade_log.flush()

        df = trade_log.load()
        assert "ctx_atr" in df.columns
        assert df["ctx_atr"].iloc[0] == 1.5

    def test_execution_quality_report(self, trade_log, sample_result):
        trade_log.record(sample_result, signal=0.8, strategy="cm")
        trade_log.flush()

        report = trade_log.execution_quality_report()
        assert "Total executions: 1" in report
        assert "USDJPY" in report

    def test_empty_load(self, trade_log):
        assert trade_log.load().empty

    def test_empty_report(self, trade_log):
        assert "No trades" in trade_log.execution_quality_report()
