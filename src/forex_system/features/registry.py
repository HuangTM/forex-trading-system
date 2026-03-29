"""Indicator registry — maps config strings to computed columns."""

import pandas as pd

from forex_system.features import indicators as ind


def compute_indicators(df: pd.DataFrame, indicator_names: list[str]) -> pd.DataFrame:
    """Compute requested indicators and add as columns to a copy of df.

    Indicator name format: "{indicator}_{param}" e.g. "sma_50", "rsi_14", "bb_20_2"
    """
    result = df.copy()

    for name in indicator_names:
        if name in result.columns:
            continue  # Already computed

        parts = name.split("_")
        ind_type = parts[0]

        if ind_type == "sma" and len(parts) == 2:
            period = int(parts[1])
            result[name] = ind.sma(result["close"], period)

        elif ind_type == "ema" and len(parts) == 2:
            period = int(parts[1])
            result[name] = ind.ema(result["close"], period)

        elif ind_type == "rsi" and len(parts) == 2:
            period = int(parts[1])
            result[name] = ind.rsi(result["close"], period)

        elif ind_type == "bb" and len(parts) >= 2:
            period = int(parts[1])
            num_std = float(parts[2]) if len(parts) > 2 else 2.0
            upper, middle, lower = ind.bollinger_bands(result["close"], period, num_std)
            result[f"bb_upper_{period}_{num_std}"] = upper
            result[f"bb_middle_{period}_{num_std}"] = middle
            result[f"bb_lower_{period}_{num_std}"] = lower

        elif ind_type == "atr" and len(parts) == 2:
            period = int(parts[1])
            result[name] = ind.atr(
                result["high"], result["low"], result["close"], period
            )

        elif ind_type == "momentum" and len(parts) == 2:
            period = int(parts[1])
            result[name] = ind.momentum(result["close"], period)

        else:
            raise ValueError(f"Unknown indicator: {name}")

    return result
