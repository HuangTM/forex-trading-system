"""Tests for technical indicators — verified against known values."""

import numpy as np
import pandas as pd

from forex_system.features.indicators import atr, bollinger_bands, ema, momentum, rsi, sma


def test_sma_basic():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(s, 3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_sma_all_same():
    s = pd.Series([5.0] * 10)
    result = sma(s, 3)
    assert result.iloc[-1] == pytest.approx(5.0)


def test_ema_basic():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    result = ema(s, 3)
    # EMA should be closer to recent values than SMA
    assert result.iloc[-1] > sma(s, 3).iloc[-1]


def test_rsi_range():
    """RSI must always be between 0 and 100."""
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(0, 1, 200).cumsum() + 100)
    result = rsi(s, 14)
    valid = result.dropna()
    assert (valid >= 0).all()
    assert (valid <= 100).all()


def test_rsi_all_up():
    """Purely rising prices should give RSI near 100."""
    s = pd.Series(np.arange(1.0, 51.0))
    result = rsi(s, 14)
    assert result.iloc[-1] > 95


def test_rsi_all_down():
    """Purely falling prices should give RSI near 0."""
    s = pd.Series(np.arange(50.0, 0.0, -1.0))
    result = rsi(s, 14)
    assert result.iloc[-1] < 5


def test_bollinger_bands_structure():
    s = pd.Series(np.random.default_rng(42).normal(100, 5, 100))
    upper, middle, lower = bollinger_bands(s, 20, 2.0)
    valid_idx = middle.dropna().index
    assert (upper.loc[valid_idx] >= middle.loc[valid_idx]).all()
    assert (lower.loc[valid_idx] <= middle.loc[valid_idx]).all()


def test_atr_positive(sample_ohlcv):
    result = atr(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], 14)
    valid = result.dropna()
    assert (valid > 0).all()


def test_momentum_basic():
    s = pd.Series([100.0, 105.0, 110.0, 115.0, 120.0])
    result = momentum(s, 2)
    # 110/100 - 1 = 0.10
    assert result.iloc[2] == pytest.approx(0.10)


# Need pytest for approx
import pytest
