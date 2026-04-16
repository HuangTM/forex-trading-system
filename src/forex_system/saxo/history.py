"""Convert Saxo chart API responses to pandas DataFrames.

Handles the Saxo-specific OHLCV format (bid/ask OHLC) and converts
to the system's standard DataFrame format.
"""

from __future__ import annotations

import pandas as pd


def bars_to_dataframe(bars: list[dict]) -> pd.DataFrame:
    """Convert Saxo chart API bars to standard OHLCV DataFrame.

    Saxo returns separate bid/ask OHLC. We use the mid-price
    (average of bid and ask) for each field.

    Args:
        bars: List of bar dicts from Saxo chart API.
              Each has: Time, OpenBid, HighBid, LowBid, CloseBid,
              OpenAsk, HighAsk, LowAsk, CloseAsk, TotalTickCount

    Returns:
        DataFrame with columns: open, high, low, close, volume
        Index: DatetimeIndex (UTC)
    """
    if not bars:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    records = []
    for bar in bars:
        # Mid-price: average of bid and ask
        open_mid = (bar.get("OpenBid", 0) + bar.get("OpenAsk", 0)) / 2
        high_mid = (bar.get("HighBid", 0) + bar.get("HighAsk", 0)) / 2
        low_mid = (bar.get("LowBid", 0) + bar.get("LowAsk", 0)) / 2
        close_mid = (bar.get("CloseBid", 0) + bar.get("CloseAsk", 0)) / 2
        volume = bar.get("TotalTickCount", 0)

        records.append({
            "datetime": bar["Time"],
            "open": open_mid,
            "high": high_mid,
            "low": low_mid,
            "close": close_mid,
            "volume": float(volume),
            # Preserve spread data for cost empiricism
            "bid_close": bar.get("CloseBid", 0),
            "ask_close": bar.get("CloseAsk", 0),
        })

    df = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.set_index("datetime").sort_index()

    # Remove duplicates (can happen at pagination boundaries)
    df = df[~df.index.duplicated(keep="last")]

    return df


def compute_spread_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute spread statistics from bid/ask columns.

    Returns DataFrame with spread in pips per bar, useful for
    cost empiricism (measuring actual Saxo spreads).
    """
    if "bid_close" not in df.columns or "ask_close" not in df.columns:
        return pd.DataFrame()

    spread = df["ask_close"] - df["bid_close"]
    # Convert to pips (0.0001 for most pairs, 0.01 for JPY)
    # Heuristic: if prices > 10, it's a JPY pair
    pip_value = 0.01 if df["close"].mean() > 10 else 0.0001
    spread_pips = spread / pip_value

    result = pd.DataFrame({
        "spread_pips": spread_pips,
        "hour": df.index.hour,
        "day_of_week": df.index.dayofweek,
    }, index=df.index)

    return result
