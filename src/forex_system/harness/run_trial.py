"""Harness CLI — production trial runner.

Every backtest that counts flows through here. Ad-hoc scripts are research
tools only; this module is the execution firewall.

Usage:
    python -m forex_system.harness.run_trial \\
        --config config/vol_target_carry.yaml \\
        --pair USDJPY \\
        --pre-reg references/pre-registrations/vol_target_carry.md

Decision log events emitted:
    trial.start       — trial spawned, pre-reg validated
    trial.data.loaded — data loaded, shape confirmed
    trial.result      — Sharpe, MaxDD, n_trades, DSR, pass/fail
    trial.written     — trial appended to registry, report written
    trial.error       — any exception (always written before propagation)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.backtest.walkforward import run_walkforward
from forex_system.core.config import SystemConfig, load_config
from forex_system.core.errors import ConfigError, DataError
from forex_system.core.types import PairInfo
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.harness.dsr import compute_dsr
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.registry import create_strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("forex_system.harness")

_TRIALS_REGISTRY = Path(".fintech-org/trials.jsonl")
_RESULTS_DIR = Path("data/results/trials")


def _json_default(obj: object) -> object:
    """JSON encoder for numpy scalar types (numpy.bool_, integer, floating)."""
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log line (log-as-decision-trace §1-10)."""
    entry = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(entry, default=_json_default))


def _config_hash(config_path: Path) -> str:
    """SHA256 of the config file — identifies parameter set in registry."""
    return hashlib.sha256(config_path.read_bytes()).hexdigest()[:12]


def _git_hash() -> str:
    """Current HEAD commit SHA (short) — or 'untracked' if not in a repo."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "untracked"


def _count_prior_trials() -> int:
    """Count lines in trials.jsonl — used as n_trials for DSR."""
    if not _TRIALS_REGISTRY.exists():
        return 0
    with open(_TRIALS_REGISTRY) as f:
        return sum(1 for _ in f)


def _append_trial(entry: dict) -> None:
    """Append a trial entry to .fintech-org/trials.jsonl (write-on-spawn)."""
    _TRIALS_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with open(_TRIALS_REGISTRY, "a") as f:
        f.write(json.dumps(entry, default=_json_default) + "\n")


def _build_cost_model(config: SystemConfig, pair_symbol: str) -> RealisticCostModel:
    """Build RealisticCostModel from config. Raises ConfigError if pair not found."""
    pair_info = config.get_pair_info(pair_symbol)
    pair_configs = {pair_symbol.upper(): pair_info}
    return RealisticCostModel(pair_configs=pair_configs)


def _build_sizer(config: SystemConfig) -> VolTargetSizer | None:
    """Build VolTargetSizer from config position_sizing section."""
    ps = config.backtest
    method = getattr(ps, "position_sizing_method", None)
    # Read directly from raw config: check if method is vol_target
    # We check strategy names to infer sizer type
    strategy_names = [s.name for s in config.strategies]
    if "vol_target_carry" in strategy_names:
        # Find leverage_cap from strategy params
        for s in config.strategies:
            if s.name == "vol_target_carry":
                leverage_cap = s.params.get("leverage_cap", 2.0)
                break
        else:
            leverage_cap = 2.0
        return VolTargetSizer(
            leverage_cap=leverage_cap,
            max_order_units=5_000_000.0,
            min_order_size=100.0,
        )
    return None


def run_trial(
    config_path: str,
    pair: str,
    pre_reg_path: str,
    final_oos_test: bool = False,
) -> dict:
    """Run a single trial through the production engine.

    Returns a dict with trial results. Always appends to trials.jsonl before
    returning (write-on-spawn — failed trials count too).

    Raises:
        ConfigError: if config or pre-reg is missing/invalid
        DataError: if pair data is not found
        ValueError: if cost model is undefined for the pair
    """
    trial_id = str(uuid.uuid4())[:8]
    config_path_obj = Path(config_path)
    pre_reg_path_obj = Path(pre_reg_path)

    # Count prior trials BEFORE appending (so N includes this trial)
    n_prior = _count_prior_trials()
    n_trials_total = n_prior + 1  # This trial included

    git_hash = _git_hash()
    config_hash = _config_hash(config_path_obj) if config_path_obj.exists() else "missing"

    _log_event(
        "trial.start",
        trial_id=trial_id,
        config=str(config_path_obj),
        pair=pair,
        pre_reg=str(pre_reg_path_obj),
        n_prior_trials=n_prior,
        git_hash=git_hash,
        config_hash=config_hash,
    )

    # Append skeleton entry immediately (write-on-spawn — failed trials count)
    skeleton = {
        "trial_id": trial_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_hash": git_hash,
        "strategy": "unknown",
        "pair": pair.upper(),
        "config_hash": config_hash,
        "pre_reg_path": str(pre_reg_path_obj),
        "sharpe": None,
        "max_dd": None,
        "n_trades": None,
        "dsr": None,
        "n_trials_at_spawn": n_trials_total,
        "oos": final_oos_test,
        "status": "spawned",
    }
    _append_trial(skeleton)
    _log_event("trial.spawned", trial_id=trial_id)

    try:
        # -- Validate pre-registration exists --
        if not pre_reg_path_obj.exists():
            raise ConfigError(
                f"Pre-registration not found: {pre_reg_path_obj}. "
                "A pre-registration markdown must exist before running a trial. "
                "See references/pre-registrations/ for the required format."
            )

        # -- Load config --
        if not config_path_obj.exists():
            raise ConfigError(f"Config not found: {config_path_obj}")
        config = load_config(config_path_obj)

        # -- Build cost model (reject if pair not in config) --
        cost_model = _build_cost_model(config, pair)

        # -- Build sizer --
        sizer = _build_sizer(config)

        # -- Load data --
        data = load_parquet(pair, "daily", config.data_dir)

        _log_event(
            "trial.data.loaded",
            trial_id=trial_id,
            pair=pair,
            rows=len(data),
            date_start=str(data.index[0].date()),
            date_end=str(data.index[-1].date()),
            data_dir=config.data_dir,
            source="parquet",
        )

        # -- Instantiate strategy --
        strategy_name = config.strategies[0].name
        strategy_params = dict(config.strategies[0].params)
        strategy_params["pair"] = pair.upper()
        strategy = create_strategy(strategy_name, strategy_params)

        # -- Compute indicators --
        enriched = compute_indicators(data, strategy.required_indicators())
        enriched = enriched.dropna(subset=["atr_14"])

        # -- Generate signals --
        signals = strategy.generate_signals(enriched)

        # -- Run backtest through production engine --
        bt_result = run_backtest(
            data=enriched,
            signals=signals,
            pair=pair.upper(),
            strategy_name=strategy_name,
            cost_model=cost_model,
            initial_capital=config.backtest.initial_capital,
            entry_delay_bars=config.backtest.entry_delay_bars,
            sizer=sizer,
            rebalance_mode=config.backtest.rebalance_mode,
            rebalance_threshold=config.backtest.rebalance_threshold,
        )

        # -- Compute metrics --
        metrics = calculate_metrics(bt_result.equity_curve, bt_result.trade_log)

        # -- Compute return stats for DSR --
        ec = bt_result.equity_curve.dropna()
        rets = ec.pct_change().dropna()
        n_obs = len(rets)
        skewness = float(rets.skew()) if n_obs > 3 else 0.0
        excess_kurtosis = float(rets.kurt()) if n_obs > 3 else 0.0  # pandas returns excess kurtosis

        dsr = compute_dsr(
            sharpe_ratio=metrics.sharpe_ratio,
            n_observations=n_obs,
            skewness=skewness,
            excess_kurtosis=excess_kurtosis,
            n_trials=n_trials_total,
        )

        # -- Walk-forward (if enabled in config) --
        wf_result = None
        wf_windows_beat = None
        wf_windows_total = None
        if getattr(config.backtest, "walkforward_enabled", False):
            from forex_system.backtest.walkforward import run_walkforward
            wf_result = run_walkforward(
                data=enriched,
                strategy=strategy,
                pair=pair.upper(),
                cost_model=cost_model,
                initial_capital=config.backtest.initial_capital,
                train_days=config.backtest.walkforward_train_days,
                test_days=config.backtest.walkforward_test_days,
                step_days=config.backtest.walkforward_step_days,
                sizer=sizer,
            )
            if wf_result and wf_result.windows:
                oos_sharpes = [w.metrics.sharpe_ratio for w in wf_result.windows]
                wf_windows_total = len(oos_sharpes)
                wf_windows_beat = sum(1 for s in oos_sharpes if s > 0)

        # -- Gate decision against pre-reg threshold --
        # Read the pre-reg to find the gate_threshold field
        pre_reg_text = pre_reg_path_obj.read_text()
        gate_threshold = _parse_pre_reg_threshold(pre_reg_text)
        passes_gate = bool(metrics.sharpe_ratio >= gate_threshold) if gate_threshold is not None else None

        _log_event(
            "trial.result",
            trial_id=trial_id,
            strategy=strategy_name,
            pair=pair.upper(),
            sharpe=round(metrics.sharpe_ratio, 4),
            max_dd=round(metrics.max_drawdown, 4),
            n_trades=metrics.num_trades,
            dsr=round(dsr, 4),
            n_trials=n_trials_total,
            n_observations=n_obs,
            skewness=round(skewness, 4),
            excess_kurtosis=round(excess_kurtosis, 4),
            gate_threshold=gate_threshold,
            passes_gate=passes_gate,
            wf_windows_beat=wf_windows_beat,
            wf_windows_total=wf_windows_total,
            cost_model="RealisticCostModel",
            config_hash=config_hash,
            git_hash=git_hash,
        )

        # -- Write structured report --
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "trial_id": trial_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_hash": git_hash,
            "strategy": strategy_name,
            "pair": pair.upper(),
            "config_path": str(config_path_obj),
            "config_hash": config_hash,
            "pre_reg_path": str(pre_reg_path_obj),
            "metrics": {
                "sharpe": metrics.sharpe_ratio,
                "max_dd": metrics.max_drawdown,
                "n_trades": metrics.num_trades,
                "total_return": metrics.total_return,
                "annualized_return": metrics.annualized_return,
                "sortino": metrics.sortino_ratio,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
            },
            "dsr": {
                "value": dsr,
                "n_trials": n_trials_total,
                "n_observations": n_obs,
                "skewness": skewness,
                "excess_kurtosis": excess_kurtosis,
            },
            "gate": {
                "threshold": gate_threshold,
                "passes": passes_gate,
            },
            "walkforward": {
                "windows_total": wf_windows_total,
                "windows_beat_zero": wf_windows_beat,
            },
            "oos": final_oos_test,
            "cost_model": "RealisticCostModel",
            "sizer": type(sizer).__name__ if sizer else "default",
        }
        report_path = _RESULTS_DIR / f"{trial_id}.json"
        report["report_path"] = str(report_path)

        # Write equity-curve Parquet alongside the JSON report.
        # Columns: timestamp, equity, signal (position signal; rename from
        # BacktestResult.signals which holds raw signal floats in [-1, +1]).
        equity_df = pd.DataFrame({
            "timestamp": bt_result.equity_curve.index,
            "equity": bt_result.equity_curve.values,
            "signal": bt_result.signals.reindex(bt_result.equity_curve.index).values,
        })
        equity_parquet_path = _RESULTS_DIR / f"{trial_id}_equity.parquet"
        equity_df.to_parquet(equity_parquet_path, index=False)
        report["equity_curve_path"] = str(equity_parquet_path)

        report_path.write_text(json.dumps(report, indent=2, default=_json_default))

        # -- Update registry entry from skeleton to complete --
        # Append completed entry (skeleton already written; we append a completion record)
        complete_entry = {
            "trial_id": trial_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_hash": git_hash,
            "strategy": strategy_name,
            "pair": pair.upper(),
            "config_hash": config_hash,
            "pre_reg_path": str(pre_reg_path_obj),
            "sharpe": metrics.sharpe_ratio,
            "max_dd": metrics.max_drawdown,
            "n_trades": metrics.num_trades,
            "dsr": dsr,
            "n_trials_at_spawn": n_trials_total,
            "oos": final_oos_test,
            "status": "complete",
            "report_path": str(report_path),
        }
        _append_trial(complete_entry)

        _log_event(
            "trial.written",
            trial_id=trial_id,
            report_path=str(report_path),
            registry=str(_TRIALS_REGISTRY),
        )

        print("\n" + "=" * 60)
        print(f"TRIAL {trial_id} COMPLETE")
        print("=" * 60)
        print(f"  Strategy:    {strategy_name}")
        print(f"  Pair:        {pair.upper()}")
        print(f"  Sharpe:      {metrics.sharpe_ratio:.4f}")
        print(f"  Max DD:      {metrics.max_drawdown:.2%}")
        print(f"  N Trades:    {metrics.num_trades}")
        print(f"  DSR:         {dsr:.4f}  (n_trials={n_trials_total})")
        if passes_gate is not None:
            verdict = "PASS" if passes_gate else "FAIL"
            print(f"  Gate:        {verdict} (threshold={gate_threshold:.2f}, got {metrics.sharpe_ratio:.4f})")
        print(f"  Report:      {report_path}")
        print(f"  Registry:    {_TRIALS_REGISTRY}")
        print("=" * 60 + "\n")

        return report

    except Exception as exc:
        _log_event(
            "trial.error",
            trial_id=trial_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


def _parse_pre_reg_threshold(text: str) -> float | None:
    """Extract gate_threshold from pre-registration markdown.

    Looks for a line matching: gate_threshold: <float>
    Returns None if not found (no gate applied).
    """
    import re
    match = re.search(r"gate_threshold:\s*([\d.]+)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a production backtest trial through the harness."
    )
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--pair", required=True, help="Currency pair symbol (e.g. USDJPY)")
    parser.add_argument("--pre-reg", required=True, dest="pre_reg", help="Path to pre-registration markdown")
    parser.add_argument("--final-oos-test", action="store_true", help="This is a one-shot OOS test (burns the holdout)")
    args = parser.parse_args()

    run_trial(
        config_path=args.config,
        pair=args.pair,
        pre_reg_path=args.pre_reg,
        final_oos_test=args.final_oos_test,
    )


if __name__ == "__main__":
    main()
