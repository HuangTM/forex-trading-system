"""Falsification trial entry-point — Phase 2 sub-wave 3c.1.

CONTRACT
--------
This script is the integration point that sub-wave 3c.2 will invoke to
run each of the 6 Phase 2 falsification trials defined in
``references/pre-registrations/``.

CONSENSUS clauses implemented
------------------------------
- CONSENSUS_2026-05-01_phase2_falsification.md §3 (OOS-2022 window from sidecar;
  no silent default for oos_window_start / oos_window_end).
- §4 (kill_switch_threshold must be present; halt with ConfigError if absent).
- §7 (NHT rubric loaded from .fintech-org/nht-rubric.yaml; no embedded defaults).
- §8 (DSR n_trials = current count of trials.jsonl + 1 at write time, per
  fintech-org rule 5).
- §9 (write-on-spawn: rejection entries written to trials.jsonl via
  record_trial_rejection; completion entries written via _append_trial).
- §11 Wave-3 sub-wave 3c: this script is the entry-point; 3c.2 runs it per pair.

Tools that MUST run first
--------------------------
- Data: ``data/processed/<PAIR>_<timeframe>.parquet`` must exist (flat layout,
  e.g. ``data/processed/EURUSD_daily.parquet``). Produce via ``scripts/download_data.py``
  or ``scripts/download_saxo_data.py``. Do NOT point data_dir at
  ``data/processed_synthetic_phase0/`` — that directory contains corrupted synthetic
  series and is NOT a valid input for falsification trials.
- Rates: ``data/rates/rate_differentials.parquet`` for carry strategies.
- FRED macro: ``data/fred_macro.parquet`` for fred_carry_stripped.
- trials.jsonl: may or may not exist; created on first write.

Dominance benchmark (Option A — auto-compute on miss)
------------------------------------------------------
For T5 triggers (carry_baseline-T5, carry_momentum-T5) the evaluator needs
``sharpe_minus_carry_fred_sharpe``, computed as:

    candidate_oos_sharpe − carry_fred_oos_sharpe_2022

The benchmark (carry_fred OOS-2022 Sharpe) is cached in
``.fintech-org/dominance_benchmarks.json`` with key
``carry_fred|<oos_window_start>|<oos_window_end>``.

On first invocation with a strategy that has a T5 trigger:
  1. The cache is checked; if hit, the cached value is used.
  2. If miss: carry_fred is run on the OOS-2022 window to obtain its Sharpe.
     This run does NOT spawn a trial entry in trials.jsonl — it is purely a
     reference computation. The carry_fred strategy is a Phase 2 VALIDATED
     strategy (FRED-carry Bet #1); running it to obtain a reference value does
     not affect its validation status.
  3. The result is written to the cache and returned.

Usage
-----
    python scripts/run_falsification_trial.py \\
        --pre-reg references/pre-registrations/carry_baseline.md \\
        [--config config/default.yaml] \\
        [--registry .fintech-org/trials.jsonl] \\
        [--dry-run] \\
        [--cost-multiplier 3.0] \\
        [--pair-restrict EURUSD]

Hook flags (Wave-5 Round-2 extensions)
---------------------------------------
--cost-multiplier <float>
    When set, multiply all cost-model spread/slippage/commission/swap
    parameters by this factor before the backtest run. Used for cost-stress
    falsification candidates (e.g. ma_crossover_3x_costs passes 3.0).
    Default: 1.0 (no multiplier). Flag must be explicitly passed; never
    silently applied.

--pair-restrict <comma-separated-pairs>
    When set, override the sidecar's pair_resolved field with the specified
    subset. Must be a non-empty subset of the sidecar's pair_resolved list.
    Used for single-pair falsification candidates (e.g. bollinger_rsi_EURUSD_only
    passes EURUSD). If a pair is specified that does not appear in the sidecar's
    pair_resolved list, raises ConfigError.  No silent default.

Exit codes
----------
    0 — trial ran; verdict emitted (pass OR rejection both exit 0 — verdict is
        part of normal operation, not an error).
    1 — unexpected error (missing data, invalid pre-reg, engine failure).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# -- Project imports --
from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.core.config import load_config
from forex_system.core.errors import ConfigError, DataError
from forex_system.core.types import PairInfo
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.core.constants import TRADING_DAYS_PER_YEAR
from forex_system.harness.dsr import compute_dsr
from forex_system.harness.falsification_evaluator import NhtRubric, evaluate
from forex_system.harness.preregistration import parse_pre_registration
from forex_system.harness.run_trial import (
    _append_trial,
    _build_cost_model,
    _build_sizer,
    _count_prior_trials,
    _git_hash,
    _json_default,
    record_trial_rejection,
)
from forex_system.strategies.registry import create_strategy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = Path("config/default.yaml")
_DEFAULT_REGISTRY = Path(".fintech-org/trials.jsonl")
_NHT_RUBRIC_PATH = Path(".fintech-org/nht-rubric.yaml")
_DOMINANCE_CACHE_PATH = Path(".fintech-org/dominance_benchmarks.json")

# Pairs targeted by multi-pair strategies (carry, carry_momentum, carry_fred, etc.)
_PHASE2_PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]

# Carry_fred strategy name — used for dominance benchmark
_CARRY_FRED_STRATEGY = "fred_carry_stripped"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("forex_system.harness.falsification_trial")


def _log(event: str, **fields: object) -> None:
    """Emit structured JSON decision-trace event to stderr."""
    entry = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(entry, default=_json_default))


# ---------------------------------------------------------------------------
# Hook helpers: cost-multiplier and pair-restrict
# ---------------------------------------------------------------------------


def _build_scaled_cost_model(
    config: object,
    pair_symbol: str,
    cost_multiplier: float,
) -> RealisticCostModel:
    """Build a RealisticCostModel with all cost parameters scaled by cost_multiplier.

    Sources cost parameters from config (via _build_cost_model), then scales
    spread_pips, slippage_pips, commission_pips, and swap rates by the multiplier.
    This is the sole hook for the cost-stress falsification candidates.

    Parameters
    ----------
    config:
        Loaded SystemConfig (from load_config()).
    pair_symbol:
        Currency pair, e.g. "EURUSD".
    cost_multiplier:
        Scaling factor for all cost parameters (e.g. 3.0 for 3× cost stress).
        Must be explicitly passed — never silently default.

    Returns
    -------
    RealisticCostModel
        A new model with scaled cost parameters for this pair.
    """
    base_model = _build_cost_model(config, pair_symbol)
    base_pair_info = base_model.pairs[pair_symbol.upper()]
    scaled_pair_info = PairInfo(
        symbol=base_pair_info.symbol,
        pip_value=base_pair_info.pip_value,
        spread_pips=base_pair_info.spread_pips * cost_multiplier,
        slippage_pips=base_pair_info.slippage_pips * cost_multiplier,
        commission_pips=base_pair_info.commission_pips * cost_multiplier,
        swap_long_pips_per_day=base_pair_info.swap_long_pips_per_day * cost_multiplier,
        swap_short_pips_per_day=base_pair_info.swap_short_pips_per_day * cost_multiplier,
    )
    return RealisticCostModel(pair_configs={pair_symbol.upper(): scaled_pair_info})


def _apply_pair_restrict(
    sidecar_pair_resolved: tuple[str, ...],
    pair_restrict: str,
    pre_reg_path: object,
) -> tuple[str, ...]:
    """Validate and apply a pair-restrict override to the sidecar's pair_resolved list.

    The pair_restrict must be a non-empty subset of sidecar_pair_resolved.
    Raises ConfigError if any requested pair is absent from the sidecar list.

    Parameters
    ----------
    sidecar_pair_resolved:
        The authoritative pair list from the pre-reg sidecar.
    pair_restrict:
        Comma-separated string of pairs to restrict to (e.g. "EURUSD,GBPUSD").
    pre_reg_path:
        Path of the pre-reg (for error messages).

    Returns
    -------
    tuple[str, ...]
        Validated restricted pair list.
    """
    requested = tuple(p.strip().upper() for p in pair_restrict.split(",") if p.strip())
    if not requested:
        raise ConfigError(
            f"--pair-restrict: empty value after parsing '{pair_restrict}'. "
            "Provide at least one valid pair symbol."
        )
    unknown = [p for p in requested if p not in sidecar_pair_resolved]
    if unknown:
        raise ConfigError(
            f"--pair-restrict: {unknown} not in sidecar pair_resolved {list(sidecar_pair_resolved)} "
            f"for {pre_reg_path}. Restriction must be a subset of the sidecar's authoritative list."
        )
    return requested


# ---------------------------------------------------------------------------
# Dominance benchmark cache
# ---------------------------------------------------------------------------


def _dominance_cache_key(strategy: str, oos_start: str, oos_end: str) -> str:
    return f"{strategy}|{oos_start}|{oos_end}"


def _load_dominance_cache() -> dict:
    """Load the dominance benchmarks cache (returns empty dict if absent)."""
    if not _DOMINANCE_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_DOMINANCE_CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_dominance_cache(cache: dict) -> None:
    """Persist the dominance benchmarks cache."""
    _DOMINANCE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DOMINANCE_CACHE_PATH.write_text(json.dumps(cache, indent=2, default=_json_default))


def _needs_dominance_benchmark(pre_reg_strategy: str, triggers: tuple) -> bool:
    """Return True if any trigger references ``sharpe_minus_carry_fred_sharpe``."""
    return any(t.metric == "sharpe_minus_carry_fred_sharpe" for t in triggers)


def _get_or_compute_carry_fred_sharpe(
    oos_start: str,
    oos_end: str,
    config_path: Path,
    dry_run: bool = False,
) -> float:
    """Return carry_fred OOS Sharpe for the given window.

    Cache hit → return immediately.
    Cache miss → run carry_fred on the window (WITHOUT writing a trial entry),
    cache result, return.

    IMPORTANT: this run is a reference computation only. It does NOT write
    to trials.jsonl. Carry_fred is a validated strategy; its OOS-2022 Sharpe
    is a benchmark constant for the dominance test, not a new trial.

    Parameters
    ----------
    oos_start, oos_end:
        ISO date strings for the OOS window.
    config_path:
        Config YAML to use for carry_fred run.
    dry_run:
        If True, cache writes are skipped (but computation still occurs).

    Returns
    -------
    float
        Aggregate (mean-across-pairs) OOS Sharpe for carry_fred on the window.
    """
    cache = _load_dominance_cache()
    cache_key = _dominance_cache_key(_CARRY_FRED_STRATEGY, oos_start, oos_end)

    if cache_key in cache:
        cached_sharpe = float(cache[cache_key])
        _log(
            "dominance_benchmark.cache_hit",
            strategy=_CARRY_FRED_STRATEGY,
            oos_start=oos_start,
            oos_end=oos_end,
            cached_sharpe=cached_sharpe,
        )
        return cached_sharpe

    _log(
        "dominance_benchmark.cache_miss",
        strategy=_CARRY_FRED_STRATEGY,
        oos_start=oos_start,
        oos_end=oos_end,
        action="running carry_fred on OOS window; NO trial entry written",
    )

    # Run carry_fred across all Phase-2 pairs; aggregate with simple mean.
    sharpes: list[float] = []
    for pair in _PHASE2_PAIRS:
        try:
            metrics_dict = _run_single_pair(
                strategy_name=_CARRY_FRED_STRATEGY,
                pair=pair,
                oos_start=oos_start,
                oos_end=oos_end,
                config_path=config_path,
            )
            sharpes.append(metrics_dict["oos_sharpe"])
            _log(
                "dominance_benchmark.pair_computed",
                pair=pair,
                sharpe=metrics_dict["oos_sharpe"],
            )
        except (DataError, ConfigError, ValueError) as exc:
            _log(
                "dominance_benchmark.pair_skipped",
                pair=pair,
                error=str(exc),
                note="pair excluded from benchmark aggregate",
            )

    if not sharpes:
        raise DataError(
            "Could not compute carry_fred OOS Sharpe on any Phase-2 pair. "
            "Ensure data is available for at least one of: " + ", ".join(_PHASE2_PAIRS)
        )

    aggregate_sharpe = float(np.mean(sharpes))
    _log(
        "dominance_benchmark.computed",
        strategy=_CARRY_FRED_STRATEGY,
        oos_start=oos_start,
        oos_end=oos_end,
        n_pairs=len(sharpes),
        aggregate_sharpe=aggregate_sharpe,
    )

    if not dry_run:
        cache[cache_key] = aggregate_sharpe
        _save_dominance_cache(cache)
        _log(
            "dominance_benchmark.cached",
            cache_path=str(_DOMINANCE_CACHE_PATH),
            cache_key=cache_key,
        )

    return aggregate_sharpe


# ---------------------------------------------------------------------------
# Core backtest helper
# ---------------------------------------------------------------------------


def _run_single_pair(
    strategy_name: str,
    pair: str,
    oos_start: str,
    oos_end: str,
    config_path: Path,
    timeframe: str = "daily",
    data_dir: str | None = None,
    cost_model_override: RealisticCostModel | None = None,
) -> dict:
    """Run the backtest engine for one strategy+pair on the OOS window.

    Returns a dict with keys: oos_sharpe, max_dd, n_trades, n_oos_bars,
    skewness, excess_kurtosis (used for DSR), and the raw equity_curve series.

    Parameters
    ----------
    cost_model_override:
        When provided, use this cost model instead of building one from config.
        Used by the cost-stress hook (--cost-multiplier). Must be None for
        standard runs (no silent override).

    Raises
    ------
    DataError
        If pair data is not found.
    ConfigError
        If config cannot be loaded.
    """
    config = load_config(config_path)

    # Build cost model for this pair — use override if provided (cost-stress hook).
    if cost_model_override is not None:
        cost_model = cost_model_override
    else:
        cost_model = _build_cost_model(config, pair)
    sizer = _build_sizer(config)

    # Load full history — we filter to OOS window after indicators are computed.
    # data_dir and timeframe may be overridden for non-daily strategies (e.g. tas_ceiling_4h).
    effective_data_dir = data_dir if data_dir is not None else config.data_dir
    data = load_parquet(pair, timeframe, effective_data_dir)

    _log(
        "backtest.data.loaded",
        pair=pair,
        rows=len(data),
        date_start=str(data.index[0].date()),
        date_end=str(data.index[-1].date()),
    )

    # Instantiate strategy via the unified ABC contract (REM-1 / D-1.3).
    # The per-strategy allowlist and reflection-based dual-path construction
    # have been DELETED per CTO D-1.3 — they were an execution-firewall violation
    # (hardcoded per-strategy branching requiring manual update on each new strategy).
    # All strategies now accept rate_data as a keyword-only arg (ABC contract D-1.1).
    # Strategies that self-load (carry_fred, vol_target_carry, fred_carry_stripped)
    # use the injected rate_data when present and fall back to self-loading when None.
    base_params = {"pair": pair.upper()}
    _rate_data_path = "data/rates/rate_differentials.parquet"
    _rate_df: pd.DataFrame | None = None
    try:
        _rate_df = pd.read_parquet(_rate_data_path)
        # Rename columns: strip "_diff" suffix for consistent column naming across scripts.
        _rate_df = _rate_df.rename(
            columns={c: c.replace("_diff", "") for c in _rate_df.columns}
        )
        _log(
            "backtest.rate_data.loaded",
            pair=pair,
            strategy=strategy_name,
            rate_path=_rate_data_path,
            n_rows=len(_rate_df),
        )
    except FileNotFoundError:
        _rate_df = None
        _log(
            "backtest.rate_data.missing",
            pair=pair,
            strategy=strategy_name,
            note="rate_differentials.parquet not found; strategy uses static fallback",
        )
    strategy = create_strategy(strategy_name, base_params, rate_data=_rate_df)

    # Compute indicators on full history (avoid NaN at window boundary).
    enriched = compute_indicators(data, strategy.required_indicators())
    # Drop NaN rows only for the strategy's own required indicators, not a
    # hardcoded atr_14.  atr_14 is only required when the strategy uses it
    # (e.g. vol_target_carry) — hardcoding it causes KeyError for strategies
    # like ma_crossover that do not include it in required_indicators().
    req_cols = [c for c in strategy.required_indicators() if c in enriched.columns]
    if req_cols:
        enriched = enriched.dropna(subset=req_cols)

    # Filter to OOS window.
    oos_mask = (enriched.index >= oos_start) & (enriched.index <= oos_end)
    oos_data = enriched[oos_mask].copy()

    if len(oos_data) < 2:
        raise DataError(
            f"OOS window {oos_start}–{oos_end} has only {len(oos_data)} rows "
            f"for {pair}. Need ≥ 2."
        )

    # Generate signals on the full series, then filter to OOS.
    signals_full = strategy.generate_signals(enriched)
    signals_oos = signals_full[oos_mask]

    # Run backtest on OOS slice.
    bt_result = run_backtest(
        data=oos_data,
        signals=signals_oos,
        pair=pair.upper(),
        strategy_name=strategy_name,
        cost_model=cost_model,
        initial_capital=config.backtest.initial_capital,
        entry_delay_bars=config.backtest.entry_delay_bars,
        sizer=sizer,
        rebalance_mode=config.backtest.rebalance_mode,
        rebalance_threshold=config.backtest.rebalance_threshold,
    )

    metrics = calculate_metrics(bt_result.equity_curve, bt_result.trade_log)

    ec = bt_result.equity_curve.dropna()
    rets = ec.pct_change().dropna()
    n_obs = len(rets)
    skewness = float(rets.skew()) if n_obs > 3 else 0.0
    excess_kurtosis = float(rets.kurt()) if n_obs > 3 else 0.0

    return {
        "oos_sharpe": float(metrics.sharpe_ratio),
        "max_dd": float(metrics.max_drawdown),
        "n_trades": int(metrics.num_trades),
        "n_oos_bars": int(len(oos_data)),
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
        "equity_curve": bt_result.equity_curve,
    }


# ---------------------------------------------------------------------------
# Multi-pair aggregation
# ---------------------------------------------------------------------------


def _aggregate_pair_results(pair_results: list[dict]) -> dict:
    """Aggregate metrics across pairs.

    Strategy: mean Sharpe (portfolio-level), worst max_dd, sum n_trades,
    min n_oos_bars (most conservative for sample-size gate), mean skewness/kurtosis.
    """
    if not pair_results:
        raise ValueError("No pair results to aggregate.")

    oos_sharpe = float(np.mean([r["oos_sharpe"] for r in pair_results]))
    max_dd = float(max(r["max_dd"] for r in pair_results))
    n_trades = int(sum(r["n_trades"] for r in pair_results))
    n_oos_bars = int(min(r["n_oos_bars"] for r in pair_results))
    skewness = float(np.mean([r["skewness"] for r in pair_results]))
    excess_kurtosis = float(np.mean([r["excess_kurtosis"] for r in pair_results]))

    return {
        "oos_sharpe": oos_sharpe,
        "max_dd": max_dd,
        "n_trades": n_trades,
        "n_oos_bars": n_oos_bars,
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
        # Legacy keys expected by evaluate() (uses "max_drawdown" not "max_dd").
        "max_drawdown": max_dd,
    }


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


def run_falsification_trial(
    pre_reg_path: Path,
    config_path: Path = _DEFAULT_CONFIG,
    registry: Path = _DEFAULT_REGISTRY,
    dry_run: bool = False,
    cost_multiplier: float = 1.0,
    pair_restrict: str | None = None,
) -> dict:
    """Run a Phase 2 falsification trial end-to-end.

    Steps:
      1. Parse pre-reg + sidecar.
      2. Load NHT rubric.
      3. Apply hook overrides (cost_multiplier, pair_restrict) if set.
      4. Run backtest on OOS window (single-pair or multi-pair per sidecar).
      5. Compute DSR.
      6. Resolve dominance benchmark if T5 trigger present.
      7. Evaluate verdict via falsification_evaluator.evaluate().
      8. Write trial entry (rejected or complete) to trials.jsonl.

    Parameters
    ----------
    pre_reg_path:
        Path to the pre-registration markdown file.
    config_path:
        YAML config (default: config/default.yaml).
    registry:
        trials.jsonl path (default: .fintech-org/trials.jsonl).
    dry_run:
        If True, all computation runs but nothing is written to registry.
    cost_multiplier:
        When != 1.0, multiply all cost-model parameters by this factor.
        Sourced from --cost-multiplier CLI flag. Default 1.0 (no scaling).
        Explicitly passed — never silently applied.
    pair_restrict:
        When set, restrict pairs to this comma-separated subset of the sidecar's
        pair_resolved list. Sourced from --pair-restrict CLI flag. None = use
        full sidecar pair list.

    Returns
    -------
    dict
        Trial result including metrics, verdict, and trial_id.
    """
    trial_id = str(uuid.uuid4())[:8]
    _log("falsification_trial.start", trial_id=trial_id, pre_reg_path=str(pre_reg_path))

    # --- Step 1: Parse pre-registration ---
    pre_reg = parse_pre_registration(pre_reg_path)
    _log(
        "falsification_trial.pre_reg.loaded",
        trial_id=trial_id,
        strategy=pre_reg.strategy,
        pair=pre_reg.pair,
        oos_window_start=pre_reg.oos_window_start,
        oos_window_end=pre_reg.oos_window_end,
        kill_switch_threshold=pre_reg.kill_switch_threshold,
    )

    # Hard guards: OOS window and kill_switch_threshold must be present.
    if not pre_reg.oos_window_start:
        raise ConfigError(
            f"Pre-reg {pre_reg_path}: oos_window_start is empty. "
            "This must be set in the sidecar YAML. No silent default."
        )
    if not pre_reg.oos_window_end:
        raise ConfigError(
            f"Pre-reg {pre_reg_path}: oos_window_end is empty. "
            "This must be set in the sidecar YAML. No silent default."
        )
    if not pre_reg.kill_switch_threshold:
        raise ConfigError(
            f"Pre-reg {pre_reg_path}: kill_switch_threshold is empty. "
            "This must be set in the pre-reg markdown. No silent default."
        )

    oos_start = pre_reg.oos_window_start
    oos_end = pre_reg.oos_window_end

    # --- Step 2: Load NHT rubric ---
    nht_rubric = NhtRubric.load_from_yaml(_NHT_RUBRIC_PATH)
    _log("falsification_trial.rubric.loaded", trial_id=trial_id,
         r1=nht_rubric.r1_oos_sharpe_lt, r2=nht_rubric.r2_dsr_lt)

    # --- Step 3: Run backtest ---
    strategy_name = pre_reg.strategy

    # --- Step 2b: Apply hook overrides ---
    # cost_multiplier hook: log if != 1.0 so the decision trace is unambiguous.
    if cost_multiplier != 1.0:
        _log(
            "hook.cost_multiplier.applied",
            trial_id=trial_id,
            cost_multiplier=cost_multiplier,
            note="All cost-model parameters will be scaled by this factor; "
                 "sourced from --cost-multiplier flag (no silent default).",
        )

    # pair_restrict hook: override sidecar pair_resolved with a subset.
    if pair_restrict is not None:
        restricted = _apply_pair_restrict(
            sidecar_pair_resolved=pre_reg.pair_resolved,
            pair_restrict=pair_restrict,
            pre_reg_path=pre_reg_path,
        )
        _log(
            "hook.pair_restrict.applied",
            trial_id=trial_id,
            sidecar_pair_resolved=list(pre_reg.pair_resolved),
            restricted_pairs=list(restricted),
            note="Pair list overridden by --pair-restrict flag; "
                 "must be subset of sidecar pair_resolved (no silent default).",
        )
        pairs_to_run = list(restricted)
    else:
        # Use sidecar-authoritative pair_resolved list (Bug-2 fix: sidecar is
        # the structured source-of-truth; markdown **Pair:** is informational only).
        pairs_to_run = list(pre_reg.pair_resolved)

    _log("falsification_trial.backtest.start",
         trial_id=trial_id, strategy=strategy_name, pairs=pairs_to_run,
         oos_start=oos_start, oos_end=oos_end)

    # Sidecar-authoritative timeframe and data_dir (default to daily / config.data_dir).
    pre_reg_timeframe = getattr(pre_reg, "timeframe", "daily")
    pre_reg_data_dir = getattr(pre_reg, "data_dir", None)

    # Pre-load config once for cost-multiplier hook (avoids re-loading per pair).
    _config_for_costs = load_config(config_path) if cost_multiplier != 1.0 else None

    pair_results: list[dict] = []
    for pair in pairs_to_run:
        try:
            # Build per-pair cost model override when cost-stress hook is active.
            cost_model_override: RealisticCostModel | None = None
            if cost_multiplier != 1.0 and _config_for_costs is not None:
                cost_model_override = _build_scaled_cost_model(
                    config=_config_for_costs,
                    pair_symbol=pair,
                    cost_multiplier=cost_multiplier,
                )
                _log(
                    "hook.cost_multiplier.pair_model",
                    trial_id=trial_id,
                    pair=pair,
                    cost_multiplier=cost_multiplier,
                )

            result = _run_single_pair(
                strategy_name=strategy_name,
                pair=pair,
                oos_start=oos_start,
                oos_end=oos_end,
                config_path=config_path,
                timeframe=pre_reg_timeframe,
                data_dir=pre_reg_data_dir,
                cost_model_override=cost_model_override,
            )
            pair_results.append(result)
            _log("falsification_trial.pair.done", trial_id=trial_id,
                 pair=pair, oos_sharpe=result["oos_sharpe"])
        except (DataError, ValueError) as exc:
            _log("falsification_trial.pair.error", trial_id=trial_id,
                 pair=pair, error=str(exc))
            raise

    # Aggregate metrics across pairs.
    agg = _aggregate_pair_results(pair_results)
    _log("falsification_trial.backtest.done", trial_id=trial_id, **{
        k: v for k, v in agg.items() if k != "equity_curve"
    })

    # --- Step 4: Compute DSR ---
    # n_trials = current count + 1 (this trial at write-time, per fintech-org rule 5).
    n_prior = _count_prior_trials()
    n_trials_total = n_prior + 1

    dsr = compute_dsr(
        sharpe_ratio=agg["oos_sharpe"],
        n_observations=agg["n_oos_bars"],
        skewness=agg["skewness"],
        excess_kurtosis=agg["excess_kurtosis"],
        n_trials=n_trials_total,
        periods_per_year=float(TRADING_DAYS_PER_YEAR),
    )
    _log("falsification_trial.dsr.computed", trial_id=trial_id,
         dsr=dsr, n_trials=n_trials_total, n_obs=agg["n_oos_bars"])

    # --- Step 5: Resolve dominance benchmark if needed ---
    metrics: dict[str, float] = {
        "oos_sharpe": agg["oos_sharpe"],
        "max_drawdown": agg["max_dd"],
        "max_dd": agg["max_dd"],
        "n_trades": float(agg["n_trades"]),
        "n_oos_bars": float(agg["n_oos_bars"]),
        "dsr": dsr,
    }

    if _needs_dominance_benchmark(strategy_name, pre_reg.triggers):
        carry_fred_sharpe = _get_or_compute_carry_fred_sharpe(
            oos_start=oos_start,
            oos_end=oos_end,
            config_path=config_path,
            dry_run=dry_run,
        )
        metrics["sharpe_minus_carry_fred_sharpe"] = (
            agg["oos_sharpe"] - carry_fred_sharpe
        )
        _log(
            "falsification_trial.dominance.resolved",
            trial_id=trial_id,
            carry_fred_sharpe=carry_fred_sharpe,
            sharpe_minus_carry_fred_sharpe=metrics["sharpe_minus_carry_fred_sharpe"],
        )

    # --- Step 6: Evaluate verdict ---
    verdict = evaluate(metrics, pre_reg, nht_rubric)
    _log(
        "falsification_trial.verdict",
        trial_id=trial_id,
        strategy=strategy_name,
        passed=verdict.passed,
        triggered=list(verdict.triggered),
        falsification_criterion=verdict.falsification_criterion,
        rejection_reason=verdict.rejection_reason,
    )

    # --- Step 7: Write to registry ---
    git_hash = _git_hash()
    if verdict.passed:
        complete_entry = {
            "trial_id": trial_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_hash": git_hash,
            "strategy": strategy_name,
            "pair": pre_reg.pair,
            "pre_reg_path": str(pre_reg_path),
            "sharpe": agg["oos_sharpe"],
            "max_dd": agg["max_dd"],
            "n_trades": agg["n_trades"],
            "dsr": dsr,
            "n_trials_at_spawn": n_trials_total,
            "oos_window_start": oos_start,
            "oos_window_end": oos_end,
            "oos": True,
            "status": "complete",
            "verdict": "passed",
            "triggered": [],
        }
        if not dry_run:
            _append_trial(complete_entry)
            _log("falsification_trial.written.complete",
                 trial_id=trial_id, registry=str(registry))
        else:
            _log("falsification_trial.dry_run.complete_skipped",
                 trial_id=trial_id)
    else:
        if not dry_run:
            record_trial_rejection(
                trial_id=trial_id,
                strategy=strategy_name,
                rejection_reason=verdict.rejection_reason or "",
                falsification_criterion=verdict.falsification_criterion or "",
                registry=registry,
            )
            _log("falsification_trial.written.rejected",
                 trial_id=trial_id, registry=str(registry))
        else:
            _log("falsification_trial.dry_run.rejection_skipped",
                 trial_id=trial_id,
                 rejection_reason=verdict.rejection_reason)

    result = {
        "trial_id": trial_id,
        "strategy": strategy_name,
        "pair": pre_reg.pair,
        "oos_window_start": oos_start,
        "oos_window_end": oos_end,
        "metrics": metrics,
        "dsr": dsr,
        "n_trials_at_spawn": n_trials_total,
        "verdict": {
            "passed": verdict.passed,
            "triggered": list(verdict.triggered),
            "rejection_reason": verdict.rejection_reason,
            "falsification_criterion": verdict.falsification_criterion,
        },
        "dry_run": dry_run,
    }
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a Phase 2 falsification trial: load pre-reg, run OOS backtest, "
            "evaluate against NHT rubric + strategy triggers, write to trials.jsonl."
        )
    )
    parser.add_argument(
        "--pre-reg", required=True, dest="pre_reg",
        help="Path to pre-registration markdown (e.g. references/pre-registrations/carry_baseline.md)",
    )
    parser.add_argument(
        "--config", default=str(_DEFAULT_CONFIG), dest="config",
        help=f"YAML config path (default: {_DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--registry", default=str(_DEFAULT_REGISTRY), dest="registry",
        help=f"Path to trials.jsonl (default: {_DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Run everything but skip writes to trials.jsonl and dominance cache.",
    )
    parser.add_argument(
        "--cost-multiplier", type=float, default=1.0, dest="cost_multiplier",
        help=(
            "Scale all cost-model parameters (spread, slippage, commission, swap) "
            "by this factor. Default 1.0 (no scaling). Pass 2.0 for 2× cost stress, "
            "3.0 for 3× cost stress. Used for cost-stress falsification candidates."
        ),
    )
    parser.add_argument(
        "--pair-restrict", default=None, dest="pair_restrict",
        help=(
            "Restrict backtest to a comma-separated subset of the sidecar's "
            "pair_resolved list (e.g. 'EURUSD' or 'EURUSD,GBPUSD'). "
            "Must be a non-empty subset of sidecar pairs. No silent default."
        ),
    )
    args = parser.parse_args()

    pre_reg_path = Path(args.pre_reg)
    config_path = Path(args.config)
    registry_path = Path(args.registry)

    try:
        result = run_falsification_trial(
            pre_reg_path=pre_reg_path,
            config_path=config_path,
            registry=registry_path,
            dry_run=args.dry_run,
            cost_multiplier=args.cost_multiplier,
            pair_restrict=args.pair_restrict,
        )
    except (ConfigError, DataError) as exc:
        _log("falsification_trial.fatal", error=str(exc), error_type=type(exc).__name__)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    verdict = result["verdict"]
    status = "PASSED" if verdict["passed"] else "REJECTED"
    print(f"\n{'=' * 60}")
    print(f"FALSIFICATION TRIAL {result['trial_id']}: {status}")
    print(f"{'=' * 60}")
    print(f"  Strategy:    {result['strategy']}")
    print(f"  OOS Window:  {result['oos_window_start']} → {result['oos_window_end']}")
    print(f"  OOS Sharpe:  {result['metrics']['oos_sharpe']:.4f}")
    print(f"  Max DD:      {result['metrics']['max_dd']:.2%}")
    print(f"  N Trades:    {int(result['metrics']['n_trades'])}")
    print(f"  DSR:         {result['dsr']:.4f}  (n_trials={result['n_trials_at_spawn']})")
    if not verdict["passed"]:
        print(f"  Criterion:   {verdict['falsification_criterion']}")
        print(f"  Reason:      {verdict['rejection_reason']}")
    if args.cost_multiplier != 1.0:
        print(f"  CostMult:    {args.cost_multiplier}× (cost-stress hook active)")
    if args.pair_restrict:
        print(f"  PairRestr:   {args.pair_restrict} (pair-restrict hook active)")
    if args.dry_run:
        print("  [DRY RUN — no registry writes]")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
