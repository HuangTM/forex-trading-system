"""Text and markdown report generation."""

from forex_system.backtest.metrics import PerformanceMetrics
from forex_system.backtest.walkforward import WalkForwardResult
from forex_system.core.types import BacktestResult


def format_backtest_report(result: BacktestResult, metrics: PerformanceMetrics) -> str:
    """Generate a text summary of a single backtest run."""
    lines = [
        f"{'=' * 60}",
        f"Backtest Report: {result.strategy_name} on {result.pair}",
        f"{'=' * 60}",
        f"Period: {result.start_date.date()} to {result.end_date.date()}",
        f"",
        f"--- Returns ---",
        f"  Total Return:      {metrics.total_return:>10.2%}",
        f"  Annualized Return: {metrics.annualized_return:>10.2%}",
        f"  Sharpe Ratio:      {metrics.sharpe_ratio:>10.2f}",
        f"  Sortino Ratio:     {metrics.sortino_ratio:>10.2f}",
        f"",
        f"--- Risk ---",
        f"  Max Drawdown:          {metrics.max_drawdown:>10.2%}",
        f"  Max DD Duration:       {metrics.max_drawdown_duration_days:>7d} days",
        f"",
        f"--- Trades ---",
        f"  Total Trades:      {metrics.num_trades:>10d}",
        f"  Win Rate:          {metrics.win_rate:>10.2%}",
        f"  Profit Factor:     {metrics.profit_factor:>10.2f}",
        f"  Avg P&L (pips):    {metrics.avg_trade_pnl_pips:>10.1f}",
        f"  Avg Duration:      {metrics.avg_trade_duration_days:>10.1f} days",
        f"  Exposure:          {metrics.exposure_pct:>10.2%}",
        f"{'=' * 60}",
    ]
    return "\n".join(lines)


def format_walkforward_report(wf_result: WalkForwardResult) -> str:
    """Generate a text summary of walk-forward analysis."""
    lines = [
        f"{'=' * 70}",
        f"Walk-Forward Report: {wf_result.strategy_name} on {wf_result.pair}",
        f"{'=' * 70}",
        f"Windows: {len(wf_result.windows)}",
        f"Avg OOS Sharpe: {wf_result.avg_sharpe:.2f}",
        f"Avg OOS Max DD: {wf_result.avg_max_drawdown:.2%}",
        f"Total OOS Trades: {wf_result.total_trades}",
        f"Consistent: {'YES' if wf_result.consistent else 'NO'}",
        f"",
        f"{'Window':<8} {'Test Period':<25} {'Sharpe':>8} {'MaxDD':>8} "
        f"{'Trades':>7} {'WinRate':>8} {'Return':>10}",
        f"{'-' * 70}",
    ]

    for i, w in enumerate(wf_result.windows):
        period = f"{w.test_start.date()} to {w.test_end.date()}"
        lines.append(
            f"{i + 1:<8} {period:<25} {w.metrics.sharpe_ratio:>8.2f} "
            f"{w.metrics.max_drawdown:>8.2%} {w.metrics.num_trades:>7d} "
            f"{w.metrics.win_rate:>8.2%} {w.metrics.total_return:>10.2%}"
        )

    lines.append(f"{'=' * 70}")
    return "\n".join(lines)
