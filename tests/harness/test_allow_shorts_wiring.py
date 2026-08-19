"""F-A regression: allow_shorts (and risk knobs) must reach the engine.

Covers the three backtest entry paths that parsed but never forwarded
execution config:
  - forex_system.harness.run_trial.run_trial
  - scripts/run_falsification_trial.py::_run_single_pair
  - scripts/trial_basket_is_eval.py (M1/M2 are pre-registered always-in
    long/short — see references/pre-registrations/macd_cross.md, ema_cross.md)

Plus engine-level semantics: a short-biased signal produces non-flat short
positions when allow_shorts=True and stays flat when False.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forex_system.core.types import BacktestResult, Direction
from forex_system.harness.run_trial import run_trial

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _daily_data(n: int = 120, start: str = "2020-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range(start, periods=n, freq="B", tz="UTC")
    close = 1.10 + np.cumsum(rng.normal(0, 0.001, n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.001,
            "low": close - 0.001,
            "close": close,
            "volume": 1000.0,
        },
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


class _DummyStrategy:
    name = "dummy"

    def __init__(self, signal: float = -1.0):
        self._signal = signal

    def required_indicators(self) -> list[str]:
        return ["atr_14"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series(self._signal, index=data.index)


def _canned_backtest_result(data: pd.DataFrame, signals: pd.Series) -> BacktestResult:
    """A valid BacktestResult with a mildly varying equity curve."""
    n = len(data)
    equity = pd.Series(
        100_000.0 * (1.0 + np.linspace(0.0, 0.01, n)), index=data.index
    )
    return BacktestResult(
        equity_curve=equity,
        trade_log=[],
        signals=signals,
        parameters={},
        pair="EURUSD",
        strategy_name="dummy",
        start_date=data.index[0],
        end_date=data.index[-1],
    )


def _capture_run_backtest(module):
    """Monkeypatch run_backtest on a module; return the captured-kwargs dict."""
    captured: dict = {}

    def fake_run_backtest(**kwargs):
        captured.update(kwargs)
        return _canned_backtest_result(kwargs["data"], kwargs["signals"])

    return captured, fake_run_backtest


def _write_config(tmp_path: Path, extra_execution: str = "", extra_ps: str = "") -> Path:
    config_text = f"""
system:
  name: "test-shorts"
  log_level: "INFO"
data:
  base_dir: "data"
pairs:
  - symbol: "EURUSD"
    pip_value: 0.0001
    spread_pips: 1.0
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_day: 0.1
    swap_short_pips_per_day: -0.5
strategies:
  active:
    - "ma_crossover"
  ma_crossover:
    fast_period: 10
    slow_period: 30
backtest:
  initial_capital: 100000.0
  position_sizing:
    risk_per_trade: 0.02
    stop_loss_atr_multiple: 2.0
{extra_ps}
  execution:
    entry_delay_bars: 1
{extra_execution}
  walkforward:
    enabled: false
"""
    p = tmp_path / "config.yaml"
    p.write_text(config_text)
    return p


@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    """Redirect the trials registry / results dir to tmp_path."""
    import forex_system.harness.run_trial as rt_mod

    registry_path = tmp_path / "trials.jsonl"
    classification = {
        "event": "honest-n-classification",
        "version": 1,
        "ratified_n": 0,
        "ratified_by": ["test-fixture"],
        "counted_trial_ids": [],
        "excluded_trial_ids": [],
        "n_legacy_classified": 0,
        "forward_classification": "all new trials classify mechanically",
        "ts": "2026-06-18T00:00:00Z",
    }
    registry_path.write_text(json.dumps(classification) + "\n")
    monkeypatch.setattr(rt_mod, "_TRIALS_REGISTRY", registry_path)
    monkeypatch.setattr(rt_mod, "_RESULTS_DIR", tmp_path / "results")
    return tmp_path


@pytest.fixture
def minimal_pre_reg(tmp_path):
    p = tmp_path / "pre_reg.md"
    p.write_text("# Pre-Registration\ngate_threshold: 0.50\n")
    return p


# ---------------------------------------------------------------------------
# run_trial wiring
# ---------------------------------------------------------------------------


class TestRunTrialAllowShortsWiring:
    def test_forwards_allow_shorts_and_risk_knobs(
        self, tmp_registry, minimal_pre_reg, tmp_path, monkeypatch
    ):
        import forex_system.harness.run_trial as rt_mod

        config = _write_config(
            tmp_path,
            extra_execution="    allow_shorts: true\n",
            extra_ps="",  # risk knobs from defaults: 0.02 / 2.0
        )
        captured, fake = _capture_run_backtest(rt_mod)
        monkeypatch.setattr(rt_mod, "run_backtest", fake)
        monkeypatch.setattr(rt_mod, "load_parquet", lambda *a, **k: _daily_data())
        monkeypatch.setattr(
            rt_mod, "create_strategy", lambda name, params: _DummyStrategy()
        )

        run_trial(
            config_path=str(config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        assert captured, "run_backtest was never called"
        assert captured["allow_shorts"] is True
        assert captured["risk_per_trade"] == pytest.approx(0.02)
        assert captured["stop_loss_atr_multiple"] == pytest.approx(2.0)

    def test_forwards_nondefault_risk_knobs(
        self, tmp_registry, minimal_pre_reg, tmp_path, monkeypatch
    ):
        import forex_system.harness.run_trial as rt_mod

        config = _write_config(
            tmp_path,
            extra_execution="    allow_shorts: true\n",
        )
        # Override the position_sizing defaults with distinctive values.
        text = config.read_text().replace(
            "    risk_per_trade: 0.02", "    risk_per_trade: 0.007"
        ).replace(
            "    stop_loss_atr_multiple: 2.0", "    stop_loss_atr_multiple: 3.0"
        )
        config.write_text(text)

        captured, fake = _capture_run_backtest(rt_mod)
        monkeypatch.setattr(rt_mod, "run_backtest", fake)
        monkeypatch.setattr(rt_mod, "load_parquet", lambda *a, **k: _daily_data())
        monkeypatch.setattr(
            rt_mod, "create_strategy", lambda name, params: _DummyStrategy()
        )

        run_trial(
            config_path=str(config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        assert captured["risk_per_trade"] == pytest.approx(0.007)
        assert captured["stop_loss_atr_multiple"] == pytest.approx(3.0)

    def test_defaults_to_long_only(
        self, tmp_registry, minimal_pre_reg, tmp_path, monkeypatch
    ):
        import forex_system.harness.run_trial as rt_mod

        config = _write_config(tmp_path)  # no allow_shorts key
        captured, fake = _capture_run_backtest(rt_mod)
        monkeypatch.setattr(rt_mod, "run_backtest", fake)
        monkeypatch.setattr(rt_mod, "load_parquet", lambda *a, **k: _daily_data())
        monkeypatch.setattr(
            rt_mod, "create_strategy", lambda name, params: _DummyStrategy()
        )

        run_trial(
            config_path=str(config),
            pair="EURUSD",
            pre_reg_path=str(minimal_pre_reg),
        )

        assert captured["allow_shorts"] is False


# ---------------------------------------------------------------------------
# run_falsification_trial wiring
# ---------------------------------------------------------------------------


class TestFalsificationAllowShortsWiring:
    def test_run_single_pair_forwards_allow_shorts(self, tmp_path, monkeypatch):
        from scripts import run_falsification_trial as rft

        config = _write_config(
            tmp_path,
            extra_execution="    allow_shorts: true\n",
        )
        captured, fake = _capture_run_backtest(rft)
        monkeypatch.setattr(rft, "run_backtest", fake)
        monkeypatch.setattr(rft, "load_parquet", lambda *a, **k: _daily_data())
        monkeypatch.setattr(
            rft,
            "create_strategy",
            lambda name, params, rate_data=None: _DummyStrategy(),
        )

        rft._run_single_pair(
            strategy_name="ma_crossover",
            pair="EURUSD",
            oos_start="2020-03-02",
            oos_end="2020-04-30",
            config_path=config,
        )

        assert captured, "run_backtest was never called"
        assert captured["allow_shorts"] is True
        assert captured["risk_per_trade"] == pytest.approx(0.02)
        assert captured["stop_loss_atr_multiple"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# trial_basket_is_eval wiring (M1/M2 always-in long/short per pre-reg)
# ---------------------------------------------------------------------------


class TestBasketEvalAllowShortsWiring:
    def test_member_backtest_enables_shorts(self, monkeypatch):
        from scripts import trial_basket_is_eval as tbe

        captured, fake = _capture_run_backtest(tbe)
        monkeypatch.setattr(tbe, "run_backtest", fake)

        data = _daily_data()
        signals = pd.Series(-1.0, index=data.index)
        tbe.run_member_backtest(data, signals, "M1_MACD_cross")

        assert captured, "run_backtest was never called"
        assert captured["allow_shorts"] is True


# ---------------------------------------------------------------------------
# Engine semantics through the production wiring
# ---------------------------------------------------------------------------


def _zero_swap_eurusd():
    from forex_system.core.types import PairInfo
    from forex_system.costs.model import RealisticCostModel

    return RealisticCostModel(
        pair_configs={
            "EURUSD": PairInfo(
                symbol="EURUSD",
                pip_value=0.0001,
                spread_pips=0.0,
                slippage_pips=0.0,
                commission_pips=0.0,
                swap_long_pips_per_day=0.0,
                swap_short_pips_per_day=0.0,
            )
        }
    )


def _falling_1h_data(n: int = 10) -> pd.DataFrame:
    start_ts = pd.Timestamp("2023-09-01 08:00:00", tz="UTC")
    ts = [start_ts + pd.Timedelta(hours=i) for i in range(n)]
    close = 1.1000 - 0.001 * np.arange(n)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.0002,
            "low": close - 0.0002,
            "close": close,
            "volume": 1000.0,
        },
        index=pd.DatetimeIndex(ts, name="datetime"),
    )


class TestEngineShortSemantics:
    """Short-biased signal through run_backtest: shorts when enabled, flat when not."""

    def test_short_signal_takes_short_legs_when_enabled(self):
        from forex_system.backtest.engine import run_backtest
        from forex_system.sizing.vol_target import VolTargetSizer

        data = _falling_1h_data()
        signals = pd.Series(-1.0, index=data.index)
        result = run_backtest(
            data=data,
            signals=signals,
            pair="EURUSD",
            strategy_name="short_enabled",
            cost_model=_zero_swap_eurusd(),
            initial_capital=100_000.0,
            entry_delay_bars=1,
            sizer=VolTargetSizer(leverage_cap=1.0, min_order_size=1.0),
            rebalance_mode="continuous",
            rebalance_threshold=0.20,
            constant_capital_sizing=True,
            allow_shorts=True,
        )
        shorts = [t for t in result.trade_log if t.direction == Direction.SHORT]
        assert shorts, "expected at least one SHORT trade with allow_shorts=True"
        # Price fell while short → equity grew (zero cost, zero swap).
        assert result.equity_curve.dropna().iloc[-1] > 100_000.0

    def test_short_signal_flat_when_disabled(self):
        from forex_system.backtest.engine import run_backtest
        from forex_system.sizing.vol_target import VolTargetSizer

        data = _falling_1h_data()
        signals = pd.Series(-1.0, index=data.index)
        result = run_backtest(
            data=data,
            signals=signals,
            pair="EURUSD",
            strategy_name="short_disabled",
            cost_model=_zero_swap_eurusd(),
            initial_capital=100_000.0,
            entry_delay_bars=1,
            sizer=VolTargetSizer(leverage_cap=1.0, min_order_size=1.0),
            rebalance_mode="continuous",
            rebalance_threshold=0.20,
            constant_capital_sizing=True,
            allow_shorts=False,
        )
        ec = result.equity_curve.dropna()
        assert (ec == 100_000.0).all(), (
            "allow_shorts=False must clamp negative signals to flat"
        )
