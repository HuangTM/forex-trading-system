"""Point-in-time rate table: monthly FRED rates are dated by publication.

Audit backlog 2026-08-17: FRED dates monthly series at the first of the reference
month, so a plain ffill let signals "know" month M's rate from M-01.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts import download_fred_rates as d  # noqa: E402


def _monthly(values, start="2022-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"))


def _rates():
    rates = {c: _monthly([1.0] * 12, start="2021-06-01") for c in ["JPY", "AUD", "NZD", "CAD"]}
    rates["USD"] = _monthly([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    rates["EUR"] = pd.Series([1.0, 1.5], index=pd.to_datetime(["2022-01-03", "2022-03-10"]))
    rates["GBP"] = pd.Series([0.5], index=pd.to_datetime(["2021-12-16"]))
    return rates


def test_every_currency_has_a_lag():
    assert set(d.PUBLICATION_LAG_MONTHS) == {*d.SERIES, "GBP"}


def test_monthly_value_is_redated_to_month_plus_lag():
    pit = d.to_point_in_time(_rates())
    # USD lag 1: January's value becomes usable on Feb 1.
    assert pit["USD"].index[0] == pd.Timestamp("2022-02-01")
    # AUD lag 3: June's value becomes usable on Sep 1.
    assert pit["AUD"].index[0] == pd.Timestamp("2021-09-01")
    assert list(pit["USD"].to_numpy()) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_lag_zero_series_untouched():
    rates = _rates()
    pit = d.to_point_in_time(rates)
    pd.testing.assert_series_equal(pit["EUR"], rates["EUR"])
    pd.testing.assert_series_equal(pit["GBP"], rates["GBP"])


def test_input_not_mutated():
    rates = _rates()
    before = rates["USD"].index.copy()
    d.to_point_in_time(rates)
    assert rates["USD"].index.equals(before)


def test_signal_table_never_uses_unpublished_month():
    """On any date, the PIT USDJPY diff must only reflect USD months already published."""
    pit = d.build_rate_differentials(d.to_point_in_time(_rates()))
    # Mid-March: USD Jan (1.0) and Feb (2.0) are public, March (3.0) is not.
    # JPY is flat at 1.0, so the diff is (USD - 1.0) / 100.
    assert pit.loc["2022-03-15", "USDJPY_diff"] == pytest.approx((2.0 - 1.0) / 100)
    ref = d.build_rate_differentials(_rates())
    assert ref.loc["2022-03-15", "USDJPY_diff"] == pytest.approx((3.0 - 1.0) / 100)


def test_strategies_default_to_pit_table():
    from forex_system.strategies import carry_fred, fred_carry_stripped

    for mod in (carry_fred, fred_carry_stripped):
        assert mod._DEFAULT_RATE_DATA_PATH.endswith("rate_differentials_pit.parquet")
