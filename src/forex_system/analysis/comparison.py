"""Strategy comparison — side-by-side metrics for the Phase 0 go/no-go decision."""

from forex_system.backtest.metrics import PerformanceMetrics


def format_comparison_table(
    results: list[dict],
) -> str:
    """Format a comparison table of multiple backtest results.

    Args:
        results: List of dicts with keys:
            strategy, pair, metrics (PerformanceMetrics),
            sharpe_gross (optional)

    Returns:
        Formatted text table for the Phase 0 decision gate.
    """
    header = (
        f"{'Strategy':<18} {'Pair':<8} {'Sharpe':>8} {'Return':>10} "
        f"{'MaxDD':>8} {'Trades':>7} {'WinRate':>8} {'PF':>6} {'Edge?':>6}"
    )
    sep = "-" * len(header)

    lines = [
        "=" * len(header),
        "PHASE 0 DECISION GATE — Strategy Comparison (Net of Costs)",
        "=" * len(header),
        "",
        header,
        sep,
    ]

    for r in results:
        m: PerformanceMetrics = r["metrics"]
        edge = "YES" if m.sharpe_ratio > 0.5 and m.num_trades >= 30 else "NO"

        lines.append(
            f"{r['strategy']:<18} {r['pair']:<8} {m.sharpe_ratio:>8.2f} "
            f"{m.total_return:>10.2%} {m.max_drawdown:>8.2%} "
            f"{m.num_trades:>7d} {m.win_rate:>8.2%} {m.profit_factor:>6.2f} {edge:>6}"
        )

    lines.append(sep)
    lines.append("")

    # Summary
    edge_found = any(
        r["metrics"].sharpe_ratio > 0.5 and r["metrics"].num_trades >= 30
        for r in results
    )

    if edge_found:
        lines.append("DECISION: GO — Edge found. Proceed to Phase 1.")
    else:
        lines.append(
            "DECISION: NO-GO — No strategy/pair shows net Sharpe > 0.5 "
            "with sufficient trades. Stop here."
        )

    lines.append("=" * len(header))
    return "\n".join(lines)
