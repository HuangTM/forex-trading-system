"""Tests for saxo/history.py pip-value convention (2026-08-17 incident fix).

The price-level pip heuristic (0.01 if close.mean() > 10) misfired on
anomalously-scaled series and produced USDJPY 4h spreads in pipettes.
The fix is a pair-based pip convention.
"""

import warnings

import pandas as pd
import pytest

from forex_system.saxo.history import bars_to_dataframe, compute_spread_stats, pip_value_for_pair


def _bars(bid: float, ask: float) -> list[dict]:
    return [{
        "Time": "2024-01-02T00:00:00Z",
        "OpenBid": bid, "HighBid": ask, "LowBid": bid, "CloseBid": bid,
        "OpenAsk": ask, "HighAsk": ask, "LowAsk": bid, "CloseAsk": ask,
        "TotalTickCount": 100,
    }]


class TestPipValueForPair:
    @pytest.mark.parametrize("pair", ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY"])
    def test_jpy_quoted_pairs_use_0_01(self, pair):
        assert pip_value_for_pair(pair) == 0.01

    @pytest.mark.parametrize("pair", ["EURUSD", "GBPUSD", "AUDUSD", "USDCAD", "EURGBP", "NZDUSD"])
    def test_non_jpy_pairs_use_0_0001(self, pair):
        assert pip_value_for_pair(pair) == 0.0001

    def test_case_and_slash_insensitive(self):
        assert pip_value_for_pair("usdjpy") == 0.01
        assert pip_value_for_pair("USD/JPY") == 0.01


class TestComputeSpreadStats:
    def test_jpy_pair_pips_not_pipettes(self):
        """A 2.5-pip USDJPY spread must come out as 2.5, not 25 (pipettes)."""
        df = bars_to_dataframe(_bars(bid=150.000, ask=150.025))
        stats = compute_spread_stats(df, pair="USDJPY")
        assert stats["spread_pips"].iloc[0] == pytest.approx(2.5)

    def test_non_jpy_pair_pips(self):
        df = bars_to_dataframe(_bars(bid=1.10000, ask=1.10020))
        stats = compute_spread_stats(df, pair="EURUSD")
        assert stats["spread_pips"].iloc[0] == pytest.approx(2.0)

    def test_pair_based_ignores_anomalous_price_scale(self):
        """Prices at an anomalous scale (fake ~7 for USDJPY) must NOT change the pip.

        This is the regression test for the 2026-08-17 incident: the old
        heuristic would still pick 0.01 here (mean > 10 fails, picks 0.0001),
        producing 100x-wrong spreads.
        """
        df = bars_to_dataframe(_bars(bid=7.5000, ask=7.5025))
        stats = compute_spread_stats(df, pair="USDJPY")
        assert stats["spread_pips"].iloc[0] == pytest.approx(0.25)  # 0.0025 / 0.01

    def test_missing_pair_falls_back_with_deprecation_warning(self):
        df = bars_to_dataframe(_bars(bid=150.000, ask=150.025))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            stats = compute_spread_stats(df)
        assert any(issubclass(x.category, DeprecationWarning) for x in w)
        # heuristic: mean > 10 -> 0.01 -> 2.5 pips (legacy behaviour preserved)
        assert stats["spread_pips"].iloc[0] == pytest.approx(2.5)

    def test_no_bid_ask_returns_empty(self):
        df = pd.DataFrame({"close": [1.1]}, index=pd.DatetimeIndex(["2024-01-02"], tz="UTC"))
        assert compute_spread_stats(df, pair="EURUSD").empty
