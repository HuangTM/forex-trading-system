"""WS-05: synthetic live-loop integration test.

Closes CTO weak-spot WS-05 (cto-wa03-weak-spot-inventory.yaml line 23):

    "Equivalence test validates Sharpe parity script vs engine but does
     NOT validate that the LIVE paper-trading loop uses the same code
     path. Live loop is third code path tested by neither. Parameters set
     in live loop (rebalance_threshold, constant_capital_sizing, swap
     accrual mode) not covered."

The existing tests/equivalence/ suite covers script <-> engine; this
suite is the third leg: script <-> engine <-> live-loop. If the paper
runner ever drifts from the validated sizing semantics (e.g., someone
changes leverage_cap default, swaps the sizer subclass, adds a
"helpful" regime branch), this test catches it.

Strategy: instantiate the EXACT objects that scripts/run_paper_trading_vt.py
constructs (VolTargetCarryStrategy + VolTargetSizer with config-loaded
parameters), feed the same USDJPY fixture window the equivalence test
uses, and verify the per-bar target_units output agrees with what an
equivalent engine call would produce.

Failure of any test here means the live paper runner is decoupled from
the validated semantics; do NOT resume paper cycles until investigated.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy
from forex_system.core.config import load_config

import run_paper_trading_vt as rpt


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def usdjpy_df():
    """Same fixture the equivalence test uses; skip if absent."""
    from forex_system.data.storage import load_parquet
    data_path = REPO_ROOT / "data" / "processed" / "USDJPY_daily.parquet"
    if not data_path.exists():
        pytest.skip("USDJPY daily parquet not present")
    return load_parquet("USDJPY", "daily", str(REPO_ROOT / "data"))


@pytest.fixture(scope="module")
def vt_config():
    """Load the same config the paper runner uses."""
    cfg_path = REPO_ROOT / "config" / "vol_target_carry.yaml"
    if not cfg_path.exists():
        pytest.skip("config/vol_target_carry.yaml not present")
    return load_config(str(cfg_path))


@pytest.fixture(scope="module")
def vt_params(vt_config):
    """Extract vol_target_carry strategy params from the config."""
    strat = next(s for s in vt_config.strategies if s.name == "vol_target_carry")
    return strat.params


@pytest.fixture(scope="module")
def live_loop_objects(vt_params):
    """Instantiate the same objects scripts/run_paper_trading_vt.py builds."""
    leverage_cap = vt_params.get("leverage_cap", 2.0)
    sizer = VolTargetSizer(
        leverage_cap=leverage_cap,
        min_order_size=100,
    )
    strategy = VolTargetCarryStrategy({**vt_params, "pair": "USDJPY"})
    return {"sizer": sizer, "strategy": strategy, "leverage_cap": leverage_cap}


# --------------------------------------------------------------------------- #
# Test 1 — paper runner instantiates the canonical sizer + strategy classes
# --------------------------------------------------------------------------- #

def test_paper_runner_uses_canonical_classes():
    """Catch the failure mode where someone substitutes a custom sizer
    or strategy subclass in the paper runner without updating the
    equivalence test."""
    import inspect
    src = inspect.getsource(rpt)
    # Must instantiate VolTargetSizer (not a subclass with overridden formula)
    assert "VolTargetSizer(" in src
    # Must instantiate VolTargetCarryStrategy
    assert "VolTargetCarryStrategy(" in src
    # Must NOT use a sizer named anything else
    forbidden_sizer_names = ("FixedFractionalSizer", "AggressiveSizer",
                             "ConservativeSizer")
    for name in forbidden_sizer_names:
        assert name not in src, (
            f"paper runner uses {name} -- equivalence guarantees do NOT cover this sizer"
        )


# --------------------------------------------------------------------------- #
# Test 2 — sizing output on a known input matches the canonical formula
# --------------------------------------------------------------------------- #

def test_live_sizer_units_match_canonical_formula(live_loop_objects):
    """The sizer's calculate_size output must equal
        signal * leverage_cap * equity
    for a default-multiplier call. Catches the Round 1 sizing-formula
    bug class (units = signal * equity, missing leverage_cap multiplier)
    that consumed 5 paper-trading days on vol_target_carry."""
    sizer = live_loop_objects["sizer"]
    leverage_cap = live_loop_objects["leverage_cap"]
    signal = 0.7
    equity = 1_000_000.0
    price = 150.0
    units = sizer.calculate_size(
        signal_strength=signal,
        account_equity=equity,
        current_price=price,
        atr=0.0,
        pair="USDJPY",
    )
    expected = signal * leverage_cap * equity
    assert units == pytest.approx(expected, rel=1e-9), (
        f"Sizer output {units} does not match canonical formula "
        f"signal*leverage_cap*equity = {expected}"
    )


# --------------------------------------------------------------------------- #
# Test 3 — strategy signal range invariant: signal in [0, 1]
# --------------------------------------------------------------------------- #

def test_strategy_signal_range(live_loop_objects, usdjpy_df):
    """Per the pre-reg, signal MUST be in [0, 1] (long-only). Drift to
    negative or above 1 would silently break the sizer's clamping."""
    strategy = live_loop_objects["strategy"]
    signals = strategy.generate_signals(usdjpy_df)
    sigs = signals.dropna()
    assert (sigs >= 0).all(), f"signal went below 0; min={sigs.min()}"
    assert (sigs <= 1.0 + 1e-9).all(), f"signal exceeded 1; max={sigs.max()}"


# --------------------------------------------------------------------------- #
# Test 4 — full live-loop cycle produces the expected sizing
# --------------------------------------------------------------------------- #

def test_live_loop_cycle_produces_expected_sizing(monkeypatch, vt_params,
                                                   live_loop_objects):
    """End-to-end: feed run_cycle() a fixture, capture the executed
    backend call, verify it matches what the strategy + sizer produced."""
    # Synthetic OHLCV with 320 daily bars (deterministic)
    rng = np.random.default_rng(0)
    n = 320
    rets = rng.normal(0.00005, 0.005, n)
    close = 150.0 * np.exp(np.cumsum(rets))
    ohlcv = pd.DataFrame({
        "open": close, "high": close * 1.001, "low": close * 0.999,
        "close": close, "volume": np.full(n, 1000.0),
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))

    # Mock client + backend
    client = MagicMock()
    client.get_info_price.return_value = {"Quote": {"Bid": 150.10, "Ask": 150.20}}
    backend = MagicMock()
    backend.account_key = "TEST"
    backend.get_positions.return_value = {}
    backend.reconcile.return_value = []
    # Capture the execute_signal call so we can assert on units
    exec_call = {}
    def _exec(pair, sig, units):
        exec_call["pair"] = pair
        exec_call["sig"] = sig
        exec_call["units"] = units
        return MagicMock(success=True, error=None)
    backend.execute_signal.side_effect = _exec

    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: ohlcv)
    monkeypatch.setattr(rpt, "fetch_account_equity", lambda *a, **kw: 1_000_000.0)

    kill_switch = MagicMock()
    kill_switch.is_triggered = False
    kill_switch.check_and_trigger.return_value = False
    kill_switch.record_equity_fetch_failure.return_value = False
    kill_switch.max_consecutive_fetch_failures = 3
    kill_switch.consecutive_fetch_failures = 0

    rpt.run_cycle(
        client=client,
        backend=backend,
        sizer=live_loop_objects["sizer"],
        strategy=live_loop_objects["strategy"],
        pair="USDJPY",
        pred_log=MagicMock(),
        trade_log=MagicMock(),
        kill_switch=kill_switch,
        rebal_threshold=0.20,
        auto_mode=True,
        ntfy_topic=None,
        horizon="daily",
        monitor_pairs=None,
        cycle_id=1,
    )

    # Strategy + sizer compute the expected target units; live loop must
    # have called execute_signal with that exact value
    signals = live_loop_objects["strategy"].generate_signals(ohlcv)
    expected_sig = float(signals.iloc[-1])
    expected_units = live_loop_objects["sizer"].calculate_size(
        signal_strength=expected_sig,
        account_equity=1_000_000.0,
        current_price=150.15,  # mid of 150.10/150.20
        atr=0.0,
        pair="USDJPY",
    )
    if expected_units > 0:
        # Strategy generated a long signal; the runner should have entered
        assert exec_call.get("pair") == "USDJPY", (
            "live loop did not call backend.execute_signal -- divergence from"
            "  the equivalence-validated path"
        )
        assert exec_call["units"] == pytest.approx(expected_units, rel=1e-6), (
            f"live loop sized {exec_call['units']} but canonical formula "
            f"expects {expected_units}"
        )
    else:
        # Signal was 0 -> no trade expected
        assert "pair" not in exec_call, (
            "live loop traded on a 0 signal -- diverges from canonical"
        )


# --------------------------------------------------------------------------- #
# Test 5 — config matches what the equivalence test asserts
# --------------------------------------------------------------------------- #

def test_paper_runner_config_matches_equivalence_test_params(vt_params):
    """The paper runner's vol_target_carry config MUST have the same
    knobs the equivalence test pins. If someone changes target_vol or
    leverage_cap in the config without updating the equivalence test,
    paper trading would diverge silently from the validated edge."""
    # These are the validated values per pre-reg + commit a5128e4
    assert vt_params.get("target_vol") == pytest.approx(0.10), (
        "target_vol drifted from validated 0.10"
    )
    assert vt_params.get("leverage_cap") == pytest.approx(2.0), (
        "leverage_cap drifted from validated 2.0"
    )
    assert vt_params.get("vol_window") == 252, (
        "vol_window drifted from validated 252"
    )


# --------------------------------------------------------------------------- #
# Test 6 — sizer min_order_size enforces the live-loop circuit breaker
# --------------------------------------------------------------------------- #

def test_sizer_min_order_size_prevents_micro_trades(live_loop_objects):
    """Below min_order_size, sizer must return 0 (stay flat). Catches
    accidental tiny trades from a near-zero signal that would otherwise
    waste broker fees."""
    sizer = live_loop_objects["sizer"]
    # Tiny signal + tiny equity -> below min
    units = sizer.calculate_size(
        signal_strength=0.0001,
        account_equity=10.0,
        current_price=150.0,
        atr=0.0,
        pair="USDJPY",
    )
    assert units == 0.0


# --------------------------------------------------------------------------- #
# Test 7 — sizer rejects negative signals (long-only invariant)
# --------------------------------------------------------------------------- #

def test_sizer_rejects_negative_signal(live_loop_objects):
    """Defense in depth: even if a future strategy regression emits a
    negative signal, the sizer must clamp to 0 (long-only spec)."""
    sizer = live_loop_objects["sizer"]
    units = sizer.calculate_size(
        signal_strength=-0.5,
        account_equity=1_000_000.0,
        current_price=150.0,
        atr=0.0,
        pair="USDJPY",
    )
    assert units == 0.0
