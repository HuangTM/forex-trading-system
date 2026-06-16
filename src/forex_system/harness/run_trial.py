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
from forex_system.backtest.metrics import calculate_metrics, infer_periods_per_year
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


def record_trial_rejection(
    trial_id: str,
    strategy: str,
    rejection_reason: str,
    falsification_criterion: str,
    *,
    registry: Path | None = None,
) -> dict:
    """Append a status='rejected' entry to trials.jsonl.

    Called when a completed trial fails its pre-registered OOS gate, making the
    falsification of the null hypothesis explicit and machine-checkable.

    Parameters
    ----------
    trial_id:
        The trial_id of the completed trial being rejected (must already exist
        in the registry with status='complete').
    strategy:
        Strategy name (e.g. 'vol_target_carry').
    rejection_reason:
        Human-readable string describing why the trial was rejected
        (e.g. 'OOS Sharpe 0.12 < VTC-T1 threshold 0.30').
    falsification_criterion:
        The pre-registered trigger/threshold that was evaluated
        (e.g. 'VTC-T1', 'FRED-T2').  Machine-checkable — must match a
        trigger defined in the strategy's pre-registration document.
    registry:
        Override trials.jsonl path (default: .fintech-org/trials.jsonl).
        Use a temp path in tests to avoid corrupting production data.

    Decision trace
    --------------
    Emits ``trial.rejected`` log event so a future reader can reconstruct
    when and why each rejection occurred from logs alone (no debugger needed).

    Returns
    -------
    dict
        The appended entry (for test assertions / caller inspection).
    """
    target = registry if registry is not None else _TRIALS_REGISTRY
    entry = {
        "trial_id": trial_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_hash": _git_hash(),
        "strategy": strategy,
        "status": "rejected",
        "rejection_reason": rejection_reason,
        "falsification_criterion": falsification_criterion,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _log_event(
        "trial.rejected",
        trial_id=trial_id,
        strategy=strategy,
        rejection_reason=rejection_reason,
        falsification_criterion=falsification_criterion,
        registry=str(target),
    )
    return entry


def _build_cost_model(
    config: SystemConfig, pair_symbol: str, timeframe: str = "daily"
) -> RealisticCostModel:
    """Build the cost model for a trial. Raises ConfigError if pair not found.

    Daily timeframe → fixed-spread RealisticCostModel (unchanged). Intraday
    timeframes → a conservative (q=0.9) hour-of-day spread curve derived from the
    pair's 4h spread series when that file exists; otherwise it falls back to the
    fixed-spread model and logs the gap (HourlySpreadCostModel is a RealisticCostModel
    subclass, so the return type still holds).
    """
    pair_info = config.get_pair_info(pair_symbol)
    pair_configs = {pair_symbol.upper(): pair_info}
    if timeframe != "daily":
        spreads_path = (
            Path(config.data_dir) / "spreads" / f"{pair_symbol.upper()}_4h_spreads.parquet"
        )
        if spreads_path.exists():
            from forex_system.costs.hourly_spread import make_hourly_spread_cost_model
            return make_hourly_spread_cost_model(pair_configs, str(spreads_path), quantile=0.9)
        logger.warning(
            '{"event":"cost_model.intraday_no_4h_spreads","pair":"%s","timeframe":"%s",'
            '"action":"fallback_fixed_spread"}',
            pair_symbol.upper(), timeframe,
        )
    return RealisticCostModel(pair_configs=pair_configs)


def _apply_holdout_filter(data: pd.DataFrame, holdout_after: str | None) -> pd.DataFrame:
    """Return only PRE-holdout (in-sample) rows; ``holdout_after`` None → unchanged.

    The cutoff is exclusive (rows strictly before ``holdout_after`` are kept), and
    tz-localised to the data's index timezone so a naive ISO date compares cleanly
    against a tz-aware UTC index (same convention as storage.load_parquet).
    """
    if not holdout_after:
        return data
    cutoff = pd.Timestamp(holdout_after)
    if data.index.tz is not None and cutoff.tz is None:
        cutoff = cutoff.tz_localize(data.index.tz)
    return data.loc[data.index < cutoff]


def _slice_to_oos(
    equity_curve: pd.DataFrame, trade_log: list, holdout_after: str
) -> tuple[pd.DataFrame, list]:
    """Slice an equity curve + trade log to the OOS (on/after holdout) period.

    For a final OOS test the backtest runs over the FULL series (so indicators,
    signals and strategy state get proper pre-holdout warm-up), but metrics must
    reflect the held-out period ONLY — otherwise the in-sample portion contaminates
    the OOS equity curve and metrics. Trades are included when ENTERED in the OOS
    period. The cutoff (``index >= holdout``) is the exact complement of
    _apply_holdout_filter's in-sample cut (``index < holdout``).
    """
    cutoff = pd.Timestamp(holdout_after)
    if equity_curve.index.tz is not None and cutoff.tz is None:
        cutoff = cutoff.tz_localize(equity_curve.index.tz)
    eq = equity_curve.loc[equity_curve.index >= cutoff]
    trades = [
        t for t in trade_log
        if getattr(t, "entry_time", None) is not None and t.entry_time >= cutoff
    ]
    return eq, trades


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

        # -- Resolve data timeframe (config.data.timeframe; default daily) --
        timeframe = config.raw.get("data", {}).get("timeframe", "daily")

        # Walk-forward windows in walkforward.py are bar-counts used directly as
        # iloc offsets (train_days/test_days), which only equal calendar days for
        # daily bars. On intraday data 504 "days" = 504 bars (~3 weeks), silently
        # producing garbage windows. Fail loud until walkforward gains a
        # bars-per-day conversion.
        if timeframe != "daily" and config.backtest.walkforward_enabled:
            raise ConfigError(
                f"walkforward is enabled with timeframe={timeframe!r}, but walk-forward "
                "windows (train_days/test_days) are bar-counts that assume daily bars "
                "(walkforward.py:91). Intraday walkforward is not yet supported — disable "
                "walkforward or use daily data."
            )

        # -- Build cost model (reject if pair not in config) --
        cost_model = _build_cost_model(config, pair, timeframe)

        # -- Build sizer --
        sizer = _build_sizer(config)

        # -- Load data (with OOS-holdout enforcement) --
        # OOS discipline: a normal trial trains/tests on PRE-holdout (in-sample)
        # data only; the reserved holdout is read exactly once, via final_oos_test
        # (which burns it). load_parquet's non-oos path RAISES on holdout-crossing
        # data (a tripwire for direct callers, tests/data/test_holdout_enforcement),
        # so run_trial filters to in-sample itself — keeping normal trials runnable
        # while never exposing the model to OOS rows. No holdout configured → no-op.
        holdout_after = config.raw.get("data", {}).get("oos_holdout_start")
        if final_oos_test:
            data = load_parquet(
                pair, timeframe, config.data_dir,
                holdout_after=holdout_after, oos_mode=True,
            )
        else:
            data = load_parquet(pair, timeframe, config.data_dir)
            rows_before = len(data)
            data = _apply_holdout_filter(data, holdout_after)
            if holdout_after:
                _log_event(
                    "trial.holdout.applied",
                    trial_id=trial_id,
                    oos_holdout_start=holdout_after,
                    rows_dropped=rows_before - len(data),
                    rows_kept=len(data),
                )

        _log_event(
            "trial.data.loaded",
            trial_id=trial_id,
            pair=pair,
            timeframe=timeframe,
            final_oos_test=final_oos_test,
            oos_holdout_start=holdout_after,
            cost_model=type(cost_model).__name__,
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

        # -- Select the evaluation window --
        # A final OOS test backtests the full series for warm-up but reports metrics
        # on the OOS (post-holdout) slice ONLY, so the in-sample portion does not
        # contaminate the OOS equity curve / metrics.
        if final_oos_test and holdout_after:
            eval_equity, eval_trades = _slice_to_oos(
                bt_result.equity_curve, bt_result.trade_log, holdout_after
            )
            if len(eval_equity.dropna()) < 2:
                raise ConfigError(
                    f"final_oos_test: no evaluable data on/after oos_holdout_start="
                    f"{holdout_after!r} (OOS slice has < 2 rows)."
                )
            _log_event(
                "trial.oos_eval.sliced", trial_id=trial_id,
                oos_holdout_start=holdout_after, eval_rows=len(eval_equity.dropna()),
            )
        else:
            eval_equity, eval_trades = bt_result.equity_curve, bt_result.trade_log
            if final_oos_test and not holdout_after:
                logger.warning(
                    '{"event":"final_oos_test.no_holdout_configured","trial_id":"%s",'
                    '"action":"metrics_over_full_series"}', trial_id,
                )

        # -- Compute metrics (annualisation matched to bar frequency) --
        # Infer from the (evaluation) equity-curve index so Sharpe annualisation and
        # the DSR sqrt(P) factor stay consistent with the bar frequency.
        ec = eval_equity.dropna()
        periods_per_year = infer_periods_per_year(ec.index)
        metrics = calculate_metrics(
            eval_equity,
            eval_trades,
            periods_per_year=periods_per_year,
        )

        # -- Compute return stats for DSR --
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
            periods_per_year=periods_per_year,
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
            cost_model=type(cost_model).__name__,
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
                "periods_per_year": periods_per_year,
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
            "cost_model": type(cost_model).__name__,
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
