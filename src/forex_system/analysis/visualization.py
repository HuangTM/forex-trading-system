"""Visualization — equity curves, drawdowns, and trade analysis plots."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from forex_system.backtest.metrics import PerformanceMetrics
from forex_system.core.types import BacktestResult


def plot_equity_curve(
    result: BacktestResult,
    metrics: PerformanceMetrics,
    save_path: str | Path | None = None,
) -> None:
    """Plot equity curve with drawdown overlay."""
    ec = result.equity_curve.dropna()
    if len(ec) < 2:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1], sharex=True)
    fig.suptitle(
        f"{result.strategy_name} on {result.pair}  |  "
        f"Sharpe: {metrics.sharpe_ratio:.2f}  |  "
        f"MaxDD: {metrics.max_drawdown:.1%}  |  "
        f"Trades: {metrics.num_trades}",
        fontsize=12,
    )

    # Equity curve
    ax1.plot(ec.index, ec.values, color="#2563eb", linewidth=1.2)
    ax1.axhline(y=ec.iloc[0], color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylabel("Equity ($)")
    ax1.grid(True, alpha=0.3)

    # Drawdown
    cummax = ec.cummax()
    drawdown = (ec - cummax) / cummax
    ax2.fill_between(drawdown.index, drawdown.values, 0, color="#dc2626", alpha=0.4)
    ax2.set_ylabel("Drawdown")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_monthly_returns(
    result: BacktestResult,
    save_path: str | Path | None = None,
) -> None:
    """Plot monthly returns heatmap."""
    ec = result.equity_curve.dropna()
    if len(ec) < 30:
        return

    # Calculate monthly returns
    monthly = ec.resample("ME").last().pct_change().dropna()
    if len(monthly) < 2:
        return

    # Pivot into year x month grid
    monthly_df = pd.DataFrame({
        "year": monthly.index.year,
        "month": monthly.index.month,
        "return": monthly.values,
    })
    pivot = monthly_df.pivot_table(index="year", columns="month", values="return")

    fig, ax = plt.subplots(figsize=(12, max(4, len(pivot) * 0.5)))
    fig.suptitle(f"Monthly Returns: {result.strategy_name} on {result.pair}", fontsize=12)

    # Color map: red for negative, green for positive
    vmax = max(abs(pivot.min().min()), abs(pivot.max().max()), 0.05)
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")

    # Labels
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([month_names[m - 1] for m in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    # Annotate cells
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1%}", ha="center", va="center", fontsize=8)

    plt.colorbar(im, ax=ax, format="%.1%%", shrink=0.8)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
