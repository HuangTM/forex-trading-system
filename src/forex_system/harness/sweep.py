"""Parallel parameter sweep over cartesian grid of config params.

Usage:
    python -m forex_system.harness.sweep \\
        --config config/vol_target_carry.yaml \\
        --param strategies.vol_target_carry.target_vol=0.05,0.10,0.15 \\
        --param strategies.vol_target_carry.vol_window=126,252 \\
        --pair USDJPY \\
        --pre-reg references/pre-registrations/vol_target_carry.md \\
        --workers 4

Each worker runs one harness trial (via run_trial.run_trial()) and appends to
.fintech-org/trials.jsonl under a file lock (fcntl.flock) to prevent races.

The sweep records a cohort_id and cohort_size so DSR can Bonferroni-correct
significance relative to the full cohort.

Decision log events emitted:
    sweep.start       — cohort_id, parameter grid, total combinations
    sweep.worker      — one trial result per worker
    sweep.complete    — summary: best trial, cohort DSR correction factor
    sweep.error       — any exception in coordinator
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import itertools
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from forex_system.harness.run_trial import _json_default, _log_event, run_trial

logger = logging.getLogger("forex_system.harness.sweep")

_TRIALS_REGISTRY = Path(".fintech-org/trials.jsonl")
_SWEEP_LOG = Path(".fintech-org/sweeps.jsonl")


def _parse_param_arg(param_str: str) -> tuple[str, list[str]]:
    """Parse --param key=v1,v2,v3 into (key, [v1, v2, v3]).

    Key supports dotted paths: strategies.vol_target_carry.target_vol=0.05,0.10
    """
    if "=" not in param_str:
        raise ValueError(f"--param must be key=v1,v2,...: got '{param_str}'")
    key, values_str = param_str.split("=", 1)
    values = [v.strip() for v in values_str.split(",") if v.strip()]
    return key.strip(), values


def _coerce_value(value_str: str) -> Any:
    """Coerce a string param value to int, float, or string."""
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    return value_str


def _set_nested(d: dict, dotted_key: str, value: Any) -> None:
    """Set a value in a nested dict using a dotted key path.

    Example: _set_nested(d, "strategies.vol_target_carry.target_vol", 0.10)
    """
    keys = dotted_key.split(".")
    node = d
    for k in keys[:-1]:
        if k not in node or not isinstance(node[k], dict):
            node[k] = {}
        node = node[k]
    node[keys[-1]] = value


def _write_temp_config(base_config_path: Path, param_overrides: dict[str, Any]) -> Path:
    """Write a temporary YAML config with overridden parameters.

    Returns the path to the temp config file.
    """
    with open(base_config_path) as f:
        config_data = yaml.safe_load(f)

    for dotted_key, value in param_overrides.items():
        _set_nested(config_data, dotted_key, value)

    # Write to a temp file under .fintech-org/sweep_configs/
    temp_dir = Path(".fintech-org/sweep_configs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_id = str(uuid.uuid4())[:8]
    temp_path = temp_dir / f"sweep_{temp_id}.yaml"
    with open(temp_path, "w") as f:
        yaml.safe_dump(config_data, f, default_flow_style=False)
    return temp_path


def _run_one_worker(args: tuple) -> dict:
    """Worker function: run a single trial for one parameter combination.

    Called by joblib.Parallel. Each worker gets an independent tmp config file.

    Args:
        args: (base_config, pair, pre_reg, param_overrides, cohort_id, combo_idx)

    Returns:
        dict with trial results or error info.
    """
    base_config, pair, pre_reg, param_overrides, cohort_id, combo_idx = args

    try:
        temp_config = _write_temp_config(Path(base_config), param_overrides)
        result = run_trial(
            config_path=str(temp_config),
            pair=pair,
            pre_reg_path=pre_reg,
        )
        result["cohort_id"] = cohort_id
        result["cohort_combo_idx"] = combo_idx
        result["param_overrides"] = {k: str(v) for k, v in param_overrides.items()}
        return result
    except Exception as exc:
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "cohort_id": cohort_id,
            "cohort_combo_idx": combo_idx,
            "param_overrides": {k: str(v) for k, v in param_overrides.items()},
            "status": "error",
        }


def run_sweep(
    config_path: str,
    pair: str,
    pre_reg_path: str,
    param_specs: list[str],
    n_workers: int = 1,
) -> list[dict]:
    """Run a parallel parameter sweep.

    Args:
        config_path: base YAML config path
        pair: currency pair symbol
        pre_reg_path: pre-registration markdown path
        param_specs: list of "key=v1,v2,v3" strings
        n_workers: number of parallel workers (joblib.Parallel)

    Returns:
        List of trial result dicts (one per combination).
    """
    import joblib

    cohort_id = str(uuid.uuid4())[:8]

    # Parse param grid
    param_grid: dict[str, list[Any]] = {}
    for spec in param_specs:
        key, value_strs = _parse_param_arg(spec)
        param_grid[key] = [_coerce_value(v) for v in value_strs]

    # Cartesian product of all param values
    keys = list(param_grid.keys())
    value_lists = [param_grid[k] for k in keys]
    combinations = [
        dict(zip(keys, combo, strict=False))
        for combo in itertools.product(*value_lists)
    ]
    cohort_size = len(combinations)

    _log_event(
        "sweep.start",
        cohort_id=cohort_id,
        base_config=config_path,
        pair=pair,
        pre_reg=pre_reg_path,
        param_grid={k: [str(v) for v in vals] for k, vals in param_grid.items()},
        cohort_size=cohort_size,
        n_workers=n_workers,
    )

    print(f"\n{'='*60}")
    print(f"SWEEP {cohort_id}: {cohort_size} combinations, {n_workers} workers")
    print(f"  Pair: {pair}")
    print(f"  Params: {param_grid}")
    print(f"{'='*60}\n")

    # Build worker args
    worker_args = [
        (config_path, pair, pre_reg_path, combo, cohort_id, idx)
        for idx, combo in enumerate(combinations)
    ]

    # Run in parallel
    results: list[dict] = joblib.Parallel(n_jobs=n_workers, verbose=5)(
        joblib.delayed(_run_one_worker)(args) for args in worker_args
    )

    # Annotate each result with cohort metadata for Bonferroni correction
    # Record cohort_size in registry entries so DSR can use it
    _TRIALS_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with open(_TRIALS_REGISTRY, "a") as f:
        # File-locking for parallel safety (though joblib workers already returned)
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            cohort_entry = {
                "event": "sweep.cohort",
                "cohort_id": cohort_id,
                "cohort_size": cohort_size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trial_ids": [r.get("trial_id") for r in results if "trial_id" in r],
                "pair": pair,
                "base_config": config_path,
            }
            f.write(json.dumps(cohort_entry, default=_json_default) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

    # Write sweep summary log
    _SWEEP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_SWEEP_LOG, "a") as f:
        sweep_summary = {
            "cohort_id": cohort_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cohort_size": cohort_size,
            "n_workers": n_workers,
            "pair": pair,
            "param_grid": {k: [str(v) for v in vals] for k, vals in param_grid.items()},
            "n_succeeded": sum(1 for r in results if "error" not in r),
            "n_failed": sum(1 for r in results if "error" in r),
        }
        f.write(json.dumps(sweep_summary, default=_json_default) + "\n")

    # Print summary
    succeeded = [r for r in results if "error" not in r and "metrics" in r]
    failed = [r for r in results if "error" in r]

    print(f"\n{'='*60}")
    print(f"SWEEP {cohort_id} COMPLETE")
    print(f"  Combinations:  {cohort_size}")
    print(f"  Succeeded:     {len(succeeded)}")
    print(f"  Failed:        {len(failed)}")

    if succeeded:
        best = max(succeeded, key=lambda r: r["metrics"]["sharpe"])
        print(f"\n  Best trial:    {best.get('trial_id', 'unknown')}")
        print(f"  Best Sharpe:   {best['metrics']['sharpe']:.4f}")
        print(f"  Best params:   {best.get('param_overrides', {})}")
        print(f"\n  NOTE: Bonferroni correction for cohort_size={cohort_size}.")
        print(f"  DSR is deflated by n_trials (org-wide) at each worker spawn.")
        print(f"  Cohort entry written to {_TRIALS_REGISTRY} for downstream DSR.")

    print(f"{'='*60}\n")

    _log_event(
        "sweep.complete",
        cohort_id=cohort_id,
        cohort_size=cohort_size,
        n_succeeded=len(succeeded),
        n_failed=len(failed),
        best_trial_id=best.get("trial_id") if succeeded else None,
        best_sharpe=best["metrics"]["sharpe"] if succeeded else None,
    )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parallel parameter sweep over a base config."
    )
    parser.add_argument("--config", required=True, help="Base YAML config path")
    parser.add_argument("--pair", required=True, help="Currency pair symbol")
    parser.add_argument("--pre-reg", required=True, dest="pre_reg", help="Pre-registration markdown path")
    parser.add_argument(
        "--param", action="append", dest="params", default=[],
        metavar="KEY=V1,V2,...",
        help="Parameter grid spec. Repeatable. E.g. --param strategies.vt.target_vol=0.05,0.10",
    )
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers")
    args = parser.parse_args()

    if not args.params:
        parser.error("At least one --param is required for a sweep.")

    run_sweep(
        config_path=args.config,
        pair=args.pair,
        pre_reg_path=args.pre_reg,
        param_specs=args.params,
        n_workers=args.workers,
    )


if __name__ == "__main__":
    main()
