"""Tests for walk-forward analysis."""

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.backtest.walkforward import run_walkforward
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.ma_crossover import MACrossoverStrategy


def test_walkforward_produces_windows(long_ohlcv):
    """Walk-forward should produce multiple test windows."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    assert len(result.windows) > 0
    assert result.pair == "EURUSD"
    assert result.strategy_name == "ma_crossover"


def test_walkforward_no_overlap(long_ohlcv):
    """Test windows should not use training data."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    for w in result.windows:
        # Test period must start after training period ends
        assert w.test_start > w.train_end


def test_walkforward_metrics_populated(long_ohlcv):
    """Each window should have valid metrics."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    for w in result.windows:
        assert w.metrics is not None
        assert w.num_test_bars > 0


# ---------------------------------------------------------------------------
# Execution settings are forwarded to each test window (2026-10-29). Before,
# run_walkforward always ran discrete, so a continuous-mode strategy such as
# vol_target_carry was walked forward as a different (degenerate) strategy.
# ---------------------------------------------------------------------------

_WF = dict(pair="EURUSD", train_days=100, test_days=50, step_days=50)


def _test_window_backtest(data, strategy, start, end, **kw):
    """Re-run one walk-forward test window by hand, mirroring run_walkforward."""
    enriched = compute_indicators(data.iloc[max(0, start - 250):end].copy(),
                                  strategy.required_indicators())
    if "atr_14" not in enriched.columns:
        enriched = compute_indicators(enriched, ["atr_14"])
    signals = strategy.generate_signals(enriched)
    idx = data.index[start:end]
    return run_backtest(data=enriched.loc[idx[0]:idx[-1]], signals=signals.loc[idx[0]:idx[-1]],
                        pair="EURUSD", strategy_name=strategy.name,
                        cost_model=RealisticCostModel(), **kw)


def test_walkforward_continuous_window_matches_direct_backtest(long_ohlcv):
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    kw = dict(sizer=VolTargetSizer(leverage_cap=2.0), rebalance_mode="continuous",
              rebalance_threshold=0.1)
    wf = run_walkforward(data=long_ohlcv, strategy=strategy, cost_model=RealisticCostModel(),
                         **_WF, **kw)
    direct = _test_window_backtest(long_ohlcv, strategy, 100, 150, **kw)
    expected = calculate_metrics(direct.equity_curve, direct.trade_log)
    assert wf.windows[0].metrics.sharpe_ratio == expected.sharpe_ratio
    assert wf.windows[0].metrics.total_return == expected.total_return


def test_walkforward_mode_is_not_ignored(long_ohlcv):
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    sizer = VolTargetSizer(leverage_cap=2.0)
    disc = run_walkforward(data=long_ohlcv, strategy=strategy, cost_model=RealisticCostModel(),
                           sizer=sizer, **_WF)
    cont = run_walkforward(data=long_ohlcv, strategy=strategy, cost_model=RealisticCostModel(),
                           sizer=sizer, rebalance_mode="continuous", **_WF)
    a = [w.metrics.total_return for w in disc.windows]
    b = [w.metrics.total_return for w in cont.windows]
    assert len(a) == len(b) and a != b


def test_walkforward_defaults_unchanged(long_ohlcv):
    """Default call == explicit old behaviour (discrete, delay 1, long-only, no margin)."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    base = run_walkforward(data=long_ohlcv, strategy=strategy, cost_model=RealisticCostModel(),
                           **_WF)
    direct = _test_window_backtest(long_ohlcv, strategy, 100, 150)
    assert base.windows[0].metrics.total_return == calculate_metrics(
        direct.equity_curve, direct.trade_log).total_return
