"""Tests for data validation."""

import numpy as np
import pandas as pd

from forex_system.data.validation import validate_ohlcv


def test_valid_data(sample_ohlcv):
    report = validate_ohlcv(sample_ohlcv, "EURUSD")
    assert report.passed
    assert report.row_count == 100
    assert report.date_range is not None


def test_detect_ohlc_violation(sample_ohlcv):
    df = sample_ohlcv.copy()
    # Make high < close on some bars
    df.iloc[10, df.columns.get_loc("high")] = df.iloc[10]["close"] - 0.01
    report = validate_ohlcv(df, "EURUSD")
    assert not report.passed
    assert any("high" in issue for issue in report.issues)


def test_detect_negative_prices(sample_ohlcv):
    df = sample_ohlcv.copy()
    df.iloc[5, df.columns.get_loc("close")] = -1.0
    report = validate_ohlcv(df, "EURUSD")
    assert not report.passed
    assert any("non-positive" in issue for issue in report.issues)


def test_detect_duplicates(sample_ohlcv):
    df = pd.concat([sample_ohlcv, sample_ohlcv.iloc[:5]])
    report = validate_ohlcv(df, "EURUSD")
    assert not report.passed
    assert any("duplicate" in issue for issue in report.issues)


def test_missing_columns():
    df = pd.DataFrame({"open": [1.0], "high": [1.1]}, index=pd.DatetimeIndex(["2020-01-01"]))
    report = validate_ohlcv(df, "EURUSD")
    assert not report.passed
    assert any("Missing" in issue for issue in report.issues)
