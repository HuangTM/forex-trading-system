"""Data quality validation — the gate between raw and trusted data."""

import pandas as pd

from forex_system.core.interfaces import ValidationReport


def validate_ohlcv(df: pd.DataFrame, pair: str) -> ValidationReport:
    """Run quality checks on OHLCV data.

    Checks:
    1. Required columns present
    2. No duplicate timestamps
    3. OHLC consistency (high >= max(open, close), low <= min(open, close))
    4. No negative prices
    5. No extreme outliers (>10 std from rolling mean)
    6. Timestamp gaps (missing trading days)
    """
    issues: list[str] = []

    # 1. Required columns
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        issues.append(f"Missing columns: {missing}")
        return ValidationReport(
            passed=False, pair=pair, issues=issues, row_count=len(df)
        )

    # 2. Duplicate timestamps
    dupes = df.index.duplicated().sum()
    if dupes > 0:
        issues.append(f"{dupes} duplicate timestamps found")

    # 3. OHLC consistency
    high_violations = (
        (df["high"] < df["open"]) | (df["high"] < df["close"])
    ).sum()
    low_violations = (
        (df["low"] > df["open"]) | (df["low"] > df["close"])
    ).sum()
    if high_violations > 0:
        issues.append(f"{high_violations} bars where high < open or close")
    if low_violations > 0:
        issues.append(f"{low_violations} bars where low > open or close")

    # 4. Negative prices
    neg_count = (df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()
    if neg_count > 0:
        issues.append(f"{neg_count} bars with non-positive prices")

    # 5. Extreme outliers on close (>10 std from 50-bar rolling mean)
    if len(df) > 50:
        rolling_mean = df["close"].rolling(50).mean()
        rolling_std = df["close"].rolling(50).std()
        # Guard against division by zero when std is 0
        valid_std = rolling_std > 0
        z_scores = pd.Series(0.0, index=df.index)
        z_scores[valid_std] = (
            (df["close"][valid_std] - rolling_mean[valid_std]) / rolling_std[valid_std]
        ).abs()
        outliers = (z_scores > 10).sum()
        if outliers > 0:
            issues.append(f"{outliers} extreme price outliers (>10 std)")

    # 6. Timestamp gaps (for daily data, expect ~5 trading days per week)
    if len(df) > 1 and isinstance(df.index, pd.DatetimeIndex):
        gaps = df.index.to_series().diff()
        # Flag gaps > 4 calendar days (covers weekends + 1 holiday)
        large_gaps = gaps[gaps > pd.Timedelta(days=4)]
        if len(large_gaps) > 0:
            issues.append(f"{len(large_gaps)} gaps > 4 days detected")

    date_range = None
    if len(df) > 0 and isinstance(df.index, pd.DatetimeIndex):
        date_range = (str(df.index[0].date()), str(df.index[-1].date()))

    return ValidationReport(
        passed=len(issues) == 0,
        pair=pair,
        issues=issues,
        row_count=len(df),
        date_range=date_range,
    )
