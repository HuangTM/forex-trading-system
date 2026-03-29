"""Tests for Parquet storage."""

import pandas as pd
import pytest

from forex_system.core.errors import DataError
from forex_system.data.storage import list_available, load_parquet, save_parquet


def test_save_and_load(sample_ohlcv, tmp_path):
    save_parquet(sample_ohlcv, "EURUSD", "daily", str(tmp_path))
    loaded = load_parquet("EURUSD", "daily", str(tmp_path))
    assert len(loaded) == len(sample_ohlcv)
    pd.testing.assert_frame_equal(loaded, sample_ohlcv, check_freq=False)


def test_load_missing(tmp_path):
    with pytest.raises(DataError, match="No data found"):
        load_parquet("XXXYYY", "daily", str(tmp_path))


def test_list_available(sample_ohlcv, tmp_path):
    save_parquet(sample_ohlcv, "EURUSD", "daily", str(tmp_path))
    save_parquet(sample_ohlcv, "USDJPY", "daily", str(tmp_path))
    available = list_available(str(tmp_path))
    assert len(available) == 2
    symbols = {a["pair"] for a in available}
    assert "EURUSD" in symbols
    assert "USDJPY" in symbols
