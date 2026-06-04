"""Carry-universe joint return matrix — data plumbing for R5 kill-test (STEP 2b).

Surfaces the (T, ~36) joint net-of-cost, post-entry-delay per-bar return matrix
that feeds r5c_hansen_spa / r5a_circular_block_bootstrap in reality_check.py.

The carry universe (frozen by CONSENSUS_2026-06-02_r5_scope.md):
  6 variants × 6 JPY crosses = up to 36 cells.
  Variants: carry, carry_fred, fred_carry_stripped, vol_target_carry,
            vol_target_carry_no_vol_scaling, carry_momentum
  Pairs: USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY

Design decisions (full rationale in .fintech-org/artifacts/2026-06-02T-r5-scope/
qd-step2b-joint-matrix.yaml):

  Return type: simple pct_change() — matches calculate_metrics() and
  _annualized_sharpe() in reality_check.py (both use pct_change() convention).
  With benchmark=zero, the per-cell return series IS the benchmark-relative series.

  Alignment: inner join (intersection of all cells' valid dates). Produces a
  rectangular, NaN-free matrix. No forward-fill on returns — mid-series NaN is
  abnormal and causes cell drop.

  Window: optional (start, end) slice applied AFTER alignment. Default = full
  common history. STEP 3 pre-registration will freeze the exact OOS window.

  Dropped cells: logged at WARNING with structured fields and returned in the
  dropped list. Silent exclusion PROHIBITED — it voids the FWER guarantee.
  CODE ERRORS (KeyError, AttributeError, TypeError, etc.) RAISE immediately
  (fail-closed loud) — only genuine data-insufficiency drops with a structured
  reason. The FWER guarantee requires every drop be a confirmable benign data
  reason, never a masked bug.

No-lookahead: guaranteed by run_backtest's entry_delay_bars=1 (sacred invariant).
The builder does NOT re-shift; it extracts pct_change() of the equity_curve only.

Execution mode per variant (sourced from each variant's registered config and
canonical runner — NOT from a hardcoded allowlist that can drift):
  carry                        → discrete, sizer=None   (carry_fred.yaml)
  carry_fred                   → discrete, sizer=None   (carry_fred.yaml)
  fred_carry_stripped          → discrete, sizer=None   (no indicators; pure carry)
  vol_target_carry             → continuous, VolTargetSizer (vol_target_carry.yaml)
  vol_target_carry_no_vol_scaling → discrete, sizer=None (discrete unit signal)
  carry_momentum               → continuous, ContinuousSizer (carry_momentum_portfolio.yaml)

Decision-trace events emitted:
  carry_matrix.cell_start     — cell run attempted (variant, pair)
  carry_matrix.cell_ok        — cell built successfully (n, date_start, date_end,
                                 entry_delay_bars, rebalance_mode, sizer_type)
  carry_matrix.cell_dropped   — cell excluded (reason, exc_type, category) — WARNING
  carry_matrix.alignment      — common index resolved (T, date_start, date_end)
  carry_matrix.window_slice   — window applied (T_before, T_after, window)
  carry_matrix.matrix_built   — final matrix shape (T, k, dropped_count)
  r5_smoke.start              — run_r5_on_carry_universe invoked
  r5_smoke.result             — SPA and RC p-values returned
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.costs.model import RealisticCostModel
from forex_system.core.types import PairInfo
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.harness.reality_check import R5cResult, r5c_hansen_spa
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.registry import create_strategy

logger = logging.getLogger("forex_system.harness.carry_universe_matrix")

# ---------------------------------------------------------------------------
# Consensus universe (frozen by CONSENSUS_2026-06-02_r5_scope.md)
# ---------------------------------------------------------------------------

CARRY_VARIANTS: tuple[str, ...] = (
    "carry",
    "carry_fred",
    "fred_carry_stripped",
    "vol_target_carry",
    "vol_target_carry_no_vol_scaling",
    "carry_momentum",
)

CARRY_PAIRS: tuple[str, ...] = (
    "USDJPY",
    "EURJPY",
    "GBPJPY",
    "AUDJPY",
    "CADJPY",
    "NZDJPY",
)

# ---------------------------------------------------------------------------
# Per-pair PairInfo defaults for the 6 JPY crosses.
# Cost parameters sourced from carry_fred.yaml (the committed config that covers
# all 6 JPY crosses). These are the defaults used when no explicit PairInfo is
# supplied by the caller.
# ---------------------------------------------------------------------------
_DEFAULT_PAIR_INFO: dict[str, PairInfo] = {
    "USDJPY": PairInfo(
        symbol="USDJPY",
        pip_value=0.01,
        spread_pips=1.0,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.8,
        swap_short_pips_per_day=-1.5,
    ),
    "EURJPY": PairInfo(
        symbol="EURJPY",
        pip_value=0.01,
        spread_pips=1.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.3,
        swap_short_pips_per_day=-0.8,
    ),
    "GBPJPY": PairInfo(
        symbol="GBPJPY",
        pip_value=0.01,
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.5,
        swap_short_pips_per_day=-1.0,
    ),
    "AUDJPY": PairInfo(
        symbol="AUDJPY",
        pip_value=0.01,
        spread_pips=1.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.5,
        swap_short_pips_per_day=-1.0,
    ),
    "CADJPY": PairInfo(
        symbol="CADJPY",
        pip_value=0.01,
        spread_pips=1.5,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.4,
        swap_short_pips_per_day=-0.9,
    ),
    "NZDJPY": PairInfo(
        symbol="NZDJPY",
        pip_value=0.01,
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_pips=0.5,
        swap_long_pips_per_day=0.4,
        swap_short_pips_per_day=-0.9,
    ),
}

# Default path to rate differentials (used when variant needs it and no
# explicit path is provided via variant_params).
_DEFAULT_RATE_DATA_PATH = "data/rates/rate_differentials.parquet"

# Variants that expect rate_data columns named as pair symbol (e.g. "USDJPY"),
# NOT as "USDJPY_diff". The real rate_differentials.parquet uses *_diff names;
# we rename on the fly for these variants.
_PLAIN_SYMBOL_RATE_VARIANTS: frozenset[str] = frozenset(
    ("carry", "carry_momentum", "vol_target_carry", "vol_target_carry_no_vol_scaling")
)

# Variants that expect rate_data columns named as "USDJPY_diff" (the raw parquet format).
_DIFF_SUFFIX_RATE_VARIANTS: frozenset[str] = frozenset(
    ("carry_fred", "fred_carry_stripped")
)

# ---------------------------------------------------------------------------
# Per-variant execution config (sourced from each variant's registered config
# and canonical runner — NOT from a hardcoded allowlist that can drift).
#
# rebalance_mode and sizer_type must match EXACTLY what the variant's config
# and canonical runner use, so the builder produces the SAME return series as
# the production runner. Audit trail:
#   carry                        → carry_fred.yaml:execution.rebalance_mode=discrete
#   carry_fred                   → carry_fred.yaml:execution.rebalance_mode=discrete
#   fred_carry_stripped          → no config; pure carry, no indicators, discrete
#   vol_target_carry             → vol_target_carry.yaml:execution.rebalance_mode=continuous
#                                  + position_sizing.method=vol_target → VolTargetSizer
#   vol_target_carry_no_vol_scaling → discrete unit signal (no vol-targeting)
#   carry_momentum               → carry_momentum_portfolio.yaml:position_sizing.method=continuous
#                                  → ContinuousSizer (scripts/run_carry_momentum.py:54)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _VariantExecConfig:
    """Execution mode and sizer type for a single variant.

    All numeric parameters here are sourced from the variant's COMMITTED config file,
    not from runner scripts (which are exploratory). The config file is the authority
    for R5 — it defines what the strategy AS DEPLOYED looks like.

    Fields
    ------
    rebalance_mode : "discrete" or "continuous"
    rebalance_threshold : float
        Only meaningful in continuous mode.
    sizer_type : "none", "vol_target", or "continuous"
    risk_per_trade : float | None
        ContinuousSizer param. None for non-continuous variants.
        Source: config backtest.position_sizing.risk_per_trade.
    stop_loss_atr_multiple : float | None
        ContinuousSizer param. None for non-continuous variants.
        Source: config backtest.position_sizing.stop_loss_atr_multiple.
    leverage_cap : float | None
        VolTargetSizer param. None for non-vol-target variants.
        Source: config backtest.position_sizing.leverage_cap.
    max_order_units : float | None
        VolTargetSizer param. None for non-vol-target variants.
        Source: config backtest.position_sizing.max_order_units.
    min_order_size : float | None
        VolTargetSizer param. None for non-vol-target variants.
        Source: config backtest.position_sizing.min_order_size.
    config_source : str
        Human-readable citation of the committed config file these values come from.
    """

    rebalance_mode: str           # "discrete" or "continuous"
    rebalance_threshold: float    # only meaningful in continuous mode
    sizer_type: str               # "none", "vol_target", or "continuous"
    config_source: str            # e.g. "config/carry_momentum_portfolio.yaml"
    # ContinuousSizer params (None for non-continuous variants)
    risk_per_trade: float | None = None
    stop_loss_atr_multiple: float | None = None
    # VolTargetSizer params (None for non-vol-target variants)
    leverage_cap: float | None = None
    max_order_units: float | None = None
    min_order_size: float | None = None


_VARIANT_EXEC: dict[str, _VariantExecConfig] = {
    # carry — no dedicated config; uses carry_fred.yaml conventions (discrete carry)
    "carry": _VariantExecConfig(
        rebalance_mode="discrete",
        rebalance_threshold=0.05,   # carry_fred.yaml:backtest.execution.rebalance_threshold
        sizer_type="none",
        config_source="config/carry_fred.yaml",
    ),
    # carry_fred — CONSENSUS Bet #1, discrete, no position sizer
    "carry_fred": _VariantExecConfig(
        rebalance_mode="discrete",
        rebalance_threshold=0.05,   # carry_fred.yaml:backtest.execution.rebalance_threshold
        sizer_type="none",
        config_source="config/carry_fred.yaml",
    ),
    # fred_carry_stripped — pure rate-differential carry, no indicators, discrete
    "fred_carry_stripped": _VariantExecConfig(
        rebalance_mode="discrete",
        rebalance_threshold=0.20,
        sizer_type="none",
        config_source="config/carry_fred.yaml",  # no dedicated config; same family
    ),
    # vol_target_carry — continuous, VolTargetSizer
    # Source: config/vol_target_carry.yaml backtest.position_sizing + execution
    "vol_target_carry": _VariantExecConfig(
        rebalance_mode="continuous",
        rebalance_threshold=0.20,       # vol_target_carry.yaml:backtest.execution.rebalance_threshold
        sizer_type="vol_target",
        config_source="config/vol_target_carry.yaml",
        leverage_cap=2.0,               # vol_target_carry.yaml:backtest.position_sizing.leverage_cap
        max_order_units=5_000_000.0,    # vol_target_carry.yaml:backtest.position_sizing.max_order_units
        min_order_size=100.0,           # vol_target_carry.yaml:backtest.position_sizing.min_order_size
    ),
    # vol_target_carry_no_vol_scaling — discrete unit signal, no sizer
    "vol_target_carry_no_vol_scaling": _VariantExecConfig(
        rebalance_mode="discrete",
        rebalance_threshold=0.20,
        sizer_type="none",
        config_source="config/vol_target_carry.yaml",  # derived from vol_target_carry family
    ),
    # carry_momentum — continuous, ContinuousSizer
    # Source: config/carry_momentum_portfolio.yaml backtest.position_sizing
    # IMPORTANT: risk_per_trade=0.007 (config authority), NOT 0.02 (which is the
    # exploratory value in scripts/run_carry_momentum.py line 54 — that script is a
    # parameter-grid sweep, not the registered production runner). Provisional until
    # STEP 3 pre-registration freezes it.
    "carry_momentum": _VariantExecConfig(
        rebalance_mode="continuous",
        rebalance_threshold=0.20,
        sizer_type="continuous",
        config_source="config/carry_momentum_portfolio.yaml",
        risk_per_trade=0.007,           # carry_momentum_portfolio.yaml:backtest.position_sizing.risk_per_trade
        stop_loss_atr_multiple=2.0,     # carry_momentum_portfolio.yaml:backtest.position_sizing.stop_loss_atr_multiple
    ),
}


def _rename_rate_data_to_plain(df: pd.DataFrame) -> pd.DataFrame:
    """Rename 'USDJPY_diff' → 'USDJPY' columns for variants that expect plain pair symbols."""
    rename_map = {col: col.replace("_diff", "") for col in df.columns if col.endswith("_diff")}
    return df.rename(columns=rename_map)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    """Return series for a single (variant, pair) cell."""

    label: str  # "variant:pair"
    variant: str
    pair: str
    returns: pd.Series  # net-of-cost pct_change() series, DatetimeIndex


@dataclass
class DroppedCell:
    """Record of a cell excluded from the matrix."""

    label: str
    variant: str
    pair: str
    reason: str
    exc_type: str = ""                # exception class name (e.g. "ValueError")
    category: str = "data-insufficiency"  # "data-insufficiency" or "code-error"


@dataclass
class JointReturnMatrix:
    """Result of build_joint_return_matrix.

    Attributes
    ----------
    R:
        (T, k) float64 array of net-of-cost per-bar simple returns.
        Benchmark = zero: R[:, j] IS the benchmark-relative series for cell j.
    index:
        Common DatetimeIndex shared by all columns (length T).
    labels:
        List of "variant:pair" strings, one per column.
    dropped:
        List of DroppedCell records for cells that could not be built.
        Never silent — every exclusion has a reason.
    """

    R: np.ndarray  # shape (T, k)
    index: pd.DatetimeIndex
    labels: list[str]
    dropped: list[DroppedCell] = field(default_factory=list)

    @property
    def T(self) -> int:
        return self.R.shape[0]

    @property
    def k(self) -> int:
        return self.R.shape[1]


@dataclass
class R5CarryResult:
    """Result of run_r5_on_carry_universe."""

    spa_pvalue_consistent: float
    spa_pvalue_lower: float
    spa_pvalue_upper: float
    white_rc_pvalue: float
    block_length_used: int
    block_length_auto: bool
    B: int
    seed: int
    T: int
    k: int
    labels: list[str]
    dropped: list[DroppedCell]
    r5c_result: R5cResult


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _log(event: str, **fields: Any) -> None:
    """Emit a structured decision-trace log line."""
    entry = {"event": event, **fields}
    logger.info(json.dumps(entry, default=str))


def _load_rate_data(path: str) -> pd.DataFrame:
    """Load FRED rate differentials from parquet. Strips timezone."""
    df = pd.read_parquet(path)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def _build_sizer(
    exec_cfg: _VariantExecConfig,
    variant_params: dict[str, Any],
) -> VolTargetSizer | ContinuousSizer | None:
    """Instantiate the correct sizer for this variant from its exec config.

    All sizer parameters are sourced from exec_cfg (which itself is sourced from
    the variant's committed config file — see _VARIANT_EXEC and config_source).
    variant_params may override individual fields when an explicit caller-supplied
    override is present (non-None); otherwise the config-sourced defaults win.

    Returns None for discrete variants (no sizer needed).
    """
    if exec_cfg.sizer_type == "vol_target":
        # Parameters from _VARIANT_EXEC (sourced from config — see config_source).
        # variant_params overrides are accepted for test/caller flexibility but the
        # config value is the default, not a magic literal here.
        leverage_cap = variant_params.get("leverage_cap") or exec_cfg.leverage_cap
        max_order_units = variant_params.get("max_order_units") or exec_cfg.max_order_units
        min_order_size = variant_params.get("min_order_size") or exec_cfg.min_order_size
        return VolTargetSizer(
            leverage_cap=float(leverage_cap),
            max_order_units=float(max_order_units),
            min_order_size=float(min_order_size),
        )
    if exec_cfg.sizer_type == "continuous":
        # Parameters from _VARIANT_EXEC (sourced from the variant's committed config).
        # For carry_momentum: risk_per_trade=0.007 from carry_momentum_portfolio.yaml
        # (NOT 0.02 from scripts/run_carry_momentum.py, which is an exploratory sweep).
        # Provisional until STEP 3 pre-registration freezes the exact value.
        risk_per_trade = variant_params.get("risk_per_trade") or exec_cfg.risk_per_trade
        stop_loss_atr_multiple = (
            variant_params.get("stop_loss_atr_multiple") or exec_cfg.stop_loss_atr_multiple
        )
        return ContinuousSizer(
            risk_per_trade=float(risk_per_trade),
            stop_loss_atr_multiple=float(stop_loss_atr_multiple),
        )
    return None


def _build_cell(
    variant: str,
    pair: str,
    data_dir: str,
    variant_params: dict[str, Any],
    pair_info: PairInfo,
    rate_data: pd.DataFrame | None,
    initial_capital: float,
    entry_delay_bars: int,
) -> tuple[pd.Series, str, str]:
    """Run a single (variant, pair) backtest and return its pct_change() return Series.

    Returns (returns, rebalance_mode, sizer_type) for decision-trace logging.

    Raises ValueError / DataError for data-insufficiency (legitimate drop).
    Raises all other exceptions (KeyError, AttributeError, TypeError, etc.) as
    code errors — these must not be caught and silently dropped (F4 fix).

    The caller is responsible for catching ONLY ValueError/DataError and recording
    a DroppedCell. All other exceptions propagate as code errors (fail-closed loud).
    """
    # Resolve per-variant execution config (mode + sizer) from the frozen table.
    # This replaces the former hardcoded variant-name if/else that missed carry_momentum.
    if variant not in _VARIANT_EXEC:
        raise ValueError(
            f"_build_cell: unknown variant '{variant}'. "
            f"Add it to _VARIANT_EXEC with explicit rebalance_mode + sizer_type."
        )
    exec_cfg = _VARIANT_EXEC[variant]

    # Load OHLCV data (always from data/processed/ — loader is locked to it)
    data = load_parquet(pair, "daily", data_dir)

    # Instantiate strategy — pass rate_data keyword-only (REM-1 ABC contract)
    params: dict[str, Any] = {"pair": pair, **variant_params}
    strategy = create_strategy(variant, params, rate_data=rate_data)

    # Compute required indicators and drop warm-up NaN ONLY on indicators the
    # strategy actually requires (F1 fix: fred_carry_stripped.required_indicators()
    # returns [] → no dropna on atr_14, no KeyError).
    required = strategy.required_indicators()
    enriched = compute_indicators(data, required)
    if required:
        enriched = enriched.dropna(subset=required)

    if enriched.empty:
        raise ValueError(f"No data after indicator warm-up for {variant}:{pair}")

    # Generate signals
    signals = strategy.generate_signals(enriched)

    # Build cost model for this pair
    cost_model = RealisticCostModel(pair_configs={pair: pair_info})

    # Build sizer from config — not from a variant-name membership test (F2 fix).
    sizer = _build_sizer(exec_cfg, variant_params)
    rebalance_mode = exec_cfg.rebalance_mode
    rebalance_threshold = exec_cfg.rebalance_threshold

    # Run backtest — entry_delay_bars guarantees no-lookahead (sacred invariant)
    bt_result = run_backtest(
        data=enriched,
        signals=signals,
        pair=pair,
        strategy_name=f"{variant}:{pair}",
        cost_model=cost_model,
        initial_capital=initial_capital,
        entry_delay_bars=entry_delay_bars,
        sizer=sizer,
        rebalance_mode=rebalance_mode,
        rebalance_threshold=rebalance_threshold,
    )

    # Extract net-of-cost per-bar simple returns from equity_curve
    # pct_change() matches calculate_metrics() and _annualized_sharpe() convention
    ec = bt_result.equity_curve.dropna()
    if len(ec) < 2:
        raise ValueError(f"Equity curve too short (n={len(ec)}) for {variant}:{pair}")

    returns = ec.pct_change().dropna()

    # Guard: no mid-series NaN (pct_change() can only produce NaN at position 0,
    # which dropna() removes — but check post-hoc as a fail-closed safety net)
    if returns.isna().any():
        raise ValueError(
            f"Mid-series NaN detected in returns for {variant}:{pair} — "
            "indicates a data gap in equity_curve. Drop and investigate."
        )

    return returns, rebalance_mode, exec_cfg.sizer_type


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_joint_return_matrix(
    variants: list[str] | tuple[str, ...],
    pairs: list[str] | tuple[str, ...],
    data_dir: str = "data",
    variant_params: dict[str, dict[str, Any]] | None = None,
    pair_infos: dict[str, PairInfo] | None = None,
    rate_data: pd.DataFrame | None = None,
    rate_data_path: str | None = None,
    initial_capital: float = 1_000_000.0,
    entry_delay_bars: int = 1,
    window: tuple[str, str] | None = None,
) -> JointReturnMatrix:
    """Build the (T, k) joint net-of-cost return matrix for the carry universe.

    For each (variant, pair) cell: run the backtest via run_backtest, extract
    the net-of-cost per-bar simple return series from equity_curve.pct_change().
    Align ALL cells on ONE common gap-aligned daily DatetimeIndex (inner join).

    Parameters
    ----------
    variants:
        Ordered list of strategy variant names (subset of CARRY_VARIANTS).
    pairs:
        Ordered list of currency pair symbols (subset of CARRY_PAIRS).
    data_dir:
        Base data directory. Passed to load_parquet — loader is locked to
        data_dir/processed/ (STEP 1 range-assert guards against synthetic data).
    variant_params:
        Optional dict mapping variant name → extra strategy params. If not
        provided, sensible defaults are used for each variant.
    pair_infos:
        Optional dict mapping pair symbol → PairInfo. Defaults to
        _DEFAULT_PAIR_INFO sourced from carry_fred.yaml.
    rate_data:
        Optional pre-loaded rate_differentials DataFrame. If None and a variant
        that requires rate data is requested, loaded from rate_data_path.
    rate_data_path:
        Path to rate_differentials.parquet. Defaults to _DEFAULT_RATE_DATA_PATH.
        Ignored if rate_data is supplied directly.
    initial_capital:
        Starting equity for each cell's backtest (default 1_000_000).
    entry_delay_bars:
        No-lookahead delay (default 1 = next bar). Must match the pre-registered
        value; do NOT change without updating the pre-registration.
    window:
        Optional (start_date, end_date) ISO strings to slice the final matrix.
        Applied AFTER inner-join alignment, so the common index is resolved from
        the full history first. STEP 3 pre-registration will freeze this value.

    Returns
    -------
    JointReturnMatrix
        R: (T, k) float64 array. index: common DatetimeIndex. labels: column
        names "variant:pair". dropped: list of DroppedCell (never silent).

    Raises
    ------
    ValueError
        If the resulting matrix has k=0 (no cells built) or T=0 (no common dates).
    """
    # Resolve rate data once (shared across all cells that need it).
    #
    # Two column-naming conventions exist in this codebase:
    #   - "diff" format: "USDJPY_diff" — used by carry_fred, fred_carry_stripped
    #   - "plain" format: "USDJPY"     — used by carry, carry_momentum, vol_target_*
    #
    # The real rate_differentials.parquet uses the "diff" format. We prepare
    # both variants here so each cell gets the right format without mutation.
    _rate_data_path = rate_data_path or _DEFAULT_RATE_DATA_PATH
    _needs_rate_variants = frozenset(
        ("carry", "carry_fred", "fred_carry_stripped", "carry_momentum",
         "vol_target_carry", "vol_target_carry_no_vol_scaling")
    )

    # Base rate_data in "diff" format (as loaded from parquet)
    _rate_data_diff: pd.DataFrame | None = rate_data  # caller may pass in either format

    if _rate_data_diff is None and any(v in _needs_rate_variants for v in variants):
        try:
            _rate_data_diff = _load_rate_data(_rate_data_path)
            _log(
                "carry_matrix.rate_data_loaded",
                path=_rate_data_path,
                n_rows=len(_rate_data_diff),
                columns=list(_rate_data_diff.columns),
            )
        except Exception as exc:
            # Non-fatal: cells that need rate_data will be dropped individually
            logger.warning(
                json.dumps({
                    "event": "carry_matrix.rate_data_load_failed",
                    "path": _rate_data_path,
                    "error": str(exc),
                    "consequence": "cells requiring rate_data will be dropped",
                })
            )
            _rate_data_diff = None

    # "Plain" format: rename "USDJPY_diff" → "USDJPY" (for carry, carry_momentum, etc.)
    _rate_data_plain: pd.DataFrame | None = (
        _rename_rate_data_to_plain(_rate_data_diff)
        if _rate_data_diff is not None
        else None
    )

    _pair_infos = pair_infos or _DEFAULT_PAIR_INFO
    _variant_params = variant_params or {}

    cells: list[CellResult] = []
    dropped: list[DroppedCell] = []

    for variant in variants:
        extra_params = _variant_params.get(variant, {})
        for pair in pairs:
            label = f"{variant}:{pair}"
            _log("carry_matrix.cell_start", variant=variant, pair=pair, label=label)

            # Resolve PairInfo — fail-closed if missing
            if pair not in _pair_infos:
                reason = (
                    f"PairInfo not found for pair '{pair}' — add to pair_infos or "
                    f"_DEFAULT_PAIR_INFO"
                )
                _drop_cell(dropped, label, variant, pair, reason)
                continue

            pair_info = _pair_infos[pair]

            # Assign rate_data in the correct column-naming format for this variant:
            #   "diff" format ("USDJPY_diff"): carry_fred, fred_carry_stripped
            #   "plain" format ("USDJPY"):     carry, carry_momentum, vol_target_*
            # vol_target variants accept None (carry filter is optional), so we
            # pass plain format when available but do not hard-fail on None.
            if variant in _DIFF_SUFFIX_RATE_VARIANTS:
                cell_rate_data = _rate_data_diff
            else:
                cell_rate_data = _rate_data_plain

            _hard_rate_variants = frozenset(
                ("carry", "carry_fred", "fred_carry_stripped", "carry_momentum")
            )
            if variant in _hard_rate_variants and cell_rate_data is None:
                reason = (
                    f"rate_data is None and variant '{variant}' requires rate differentials "
                    f"for dynamic signals. Load failed or path not provided."
                )
                _drop_cell(dropped, label, variant, pair, reason)
                continue

            try:
                returns, cell_rebalance_mode, cell_sizer_type = _build_cell(
                    variant=variant,
                    pair=pair,
                    data_dir=data_dir,
                    variant_params=extra_params,
                    pair_info=pair_info,
                    rate_data=cell_rate_data,
                    initial_capital=initial_capital,
                    entry_delay_bars=entry_delay_bars,
                )
            except ValueError as exc:
                # Legitimate data-insufficiency: too few bars, empty enriched frame,
                # short equity curve, mid-series NaN. These are valid reasons to drop.
                _drop_cell(
                    dropped, label, variant, pair,
                    reason=str(exc),
                    exc_type=type(exc).__name__,
                    category="data-insufficiency",
                )
                continue
            except Exception:
                # CODE ERROR (KeyError, AttributeError, TypeError, ConfigError, etc.).
                # Re-raise immediately — fail-closed loud. A code error that silently
                # drops a whole variant voids the FWER guarantee (F4 fix).
                # The full traceback propagates so the caller sees the root cause.
                raise

            n = len(returns)
            date_start = str(returns.index[0].date()) if n > 0 else "N/A"
            date_end = str(returns.index[-1].date()) if n > 0 else "N/A"
            _log(
                "carry_matrix.cell_ok",
                label=label,
                variant=variant,
                pair=pair,
                n=n,
                date_start=date_start,
                date_end=date_end,
                entry_delay_bars=entry_delay_bars,
                rebalance_mode=cell_rebalance_mode,
                sizer_type=cell_sizer_type,
            )
            cells.append(CellResult(label=label, variant=variant, pair=pair, returns=returns))

    if not cells:
        raise ValueError(
            "build_joint_return_matrix: all cells failed to build — k=0. "
            f"Dropped cells: {[d.label for d in dropped]}"
        )

    # --- Inner-join alignment ---
    # Start from the first cell's index; intersect with each subsequent cell.
    # This gives the set of dates where ALL cells have valid returns.
    common_index: pd.DatetimeIndex = cells[0].returns.index
    for cell in cells[1:]:
        common_index = common_index.intersection(cell.returns.index)

    if len(common_index) == 0:
        raise ValueError(
            "build_joint_return_matrix: inner-join of all cell indices is empty "
            f"(T=0). Check that variants/pairs share a common date range. "
            f"Labels: {[c.label for c in cells]}"
        )

    _log(
        "carry_matrix.alignment",
        T=len(common_index),
        date_start=str(common_index[0].date()),
        date_end=str(common_index[-1].date()),
        k=len(cells),
        dropped_count=len(dropped),
    )

    # --- Optional window slice ---
    if window is not None:
        start_str, end_str = window
        T_before = len(common_index)
        common_index = common_index[
            (common_index >= pd.Timestamp(start_str))
            & (common_index <= pd.Timestamp(end_str))
        ]
        if len(common_index) == 0:
            raise ValueError(
                f"build_joint_return_matrix: window slice [{start_str}, {end_str}] "
                f"produces T=0. Common index spans "
                f"[{cells[0].returns.index[0].date()}, {cells[0].returns.index[-1].date()}]."
            )
        _log(
            "carry_matrix.window_slice",
            window_start=start_str,
            window_end=end_str,
            T_before=T_before,
            T_after=len(common_index),
        )

    # --- Build rectangular matrix ---
    T = len(common_index)
    k = len(cells)
    R = np.empty((T, k), dtype=np.float64)
    labels: list[str] = []

    for j, cell in enumerate(cells):
        col = cell.returns.reindex(common_index)
        if col.isna().any():
            # A cell that has NaN on common dates (should not happen with inner-join,
            # but fail-closed if it ever does — indicates a logic error)
            n_nan = int(col.isna().sum())
            raise ValueError(
                f"carry_universe_matrix: cell {cell.label} has {n_nan} NaN values "
                f"after inner-join alignment — this should not occur. "
                f"Investigate the cell's return series."
            )
        R[:, j] = col.to_numpy(dtype=np.float64)
        labels.append(cell.label)

    _log(
        "carry_matrix.matrix_built",
        T=T,
        k=k,
        dropped_count=len(dropped),
        labels=labels,
        dropped_labels=[d.label for d in dropped],
    )

    return JointReturnMatrix(R=R, index=common_index, labels=labels, dropped=dropped)


def _drop_cell(
    dropped: list[DroppedCell],
    label: str,
    variant: str,
    pair: str,
    reason: str,
    exc_type: str = "",
    category: str = "data-insufficiency",
) -> None:
    """Record a dropped cell with a WARNING log. Never silent.

    Parameters
    ----------
    reason:
        Human-readable description of why the cell was dropped.
    exc_type:
        Exception class name (e.g. "ValueError", "FileNotFoundError").
    category:
        Drop taxonomy: "data-insufficiency" for genuine data gaps (legitimate
        drop), "code-error" for bugs (should never reach here — code errors
        must raise, not drop).
    """
    logger.warning(
        json.dumps({
            "event": "carry_matrix.cell_dropped",
            "label": label,
            "variant": variant,
            "pair": pair,
            "reason": reason,
            "exc_type": exc_type,
            "category": category,
        })
    )
    dropped.append(
        DroppedCell(
            label=label,
            variant=variant,
            pair=pair,
            reason=reason,
            exc_type=exc_type,
            category=category,
        )
    )


def run_r5_on_carry_universe(
    variants: list[str] | tuple[str, ...],
    pairs: list[str] | tuple[str, ...],
    master_seed: int,
    data_dir: str = "data",
    variant_params: dict[str, dict[str, Any]] | None = None,
    pair_infos: dict[str, PairInfo] | None = None,
    rate_data: pd.DataFrame | None = None,
    rate_data_path: str | None = None,
    initial_capital: float = 1_000_000.0,
    entry_delay_bars: int = 1,
    window: tuple[str, str] | None = None,
    B: int = 2_000,
    block_length: int | None = None,
) -> R5CarryResult:
    """Build the joint carry universe matrix and run R5c Hansen SPA + White RC.

    This is the callable STEP 4 will invoke ONE shot against the frozen pre-reg.
    It does NOT register a trial (no new trial_id, no append to trials.jsonl) and
    does NOT execute the final kill-test decision — that is STEP 4, post pre-reg.

    A small smoke-run (2 variants × 2 pairs) is sufficient to verify wiring.

    Parameters
    ----------
    variants, pairs:
        Universe subset. Use the full CARRY_VARIANTS × CARRY_PAIRS for STEP 4.
    master_seed:
        Master seed passed to r5c_hansen_spa (child seed = master_seed + 2).
    data_dir, variant_params, pair_infos, rate_data, rate_data_path,
    initial_capital, entry_delay_bars, window:
        Forwarded to build_joint_return_matrix.
    B:
        Bootstrap resamples. Default 2_000 (Mathematician spec minimum).
        Use B=10_000 for the final STEP 4 run.
    block_length:
        Mean block length L override. None = auto (Politis-White 2004).

    Returns
    -------
    R5CarryResult
        SPA and White RC p-values, metadata, dropped cells.

    Raises
    ------
    ValueError
        If k < 2 after drops (degenerate: SPA is meaningless on a single cell).
    """
    _log("r5_smoke.start", variants=list(variants), pairs=list(pairs), B=B, seed=master_seed)

    matrix = build_joint_return_matrix(
        variants=variants,
        pairs=pairs,
        data_dir=data_dir,
        variant_params=variant_params,
        pair_infos=pair_infos,
        rate_data=rate_data,
        rate_data_path=rate_data_path,
        initial_capital=initial_capital,
        entry_delay_bars=entry_delay_bars,
        window=window,
    )

    if matrix.k < 2:
        raise ValueError(
            f"run_r5_on_carry_universe: k={matrix.k} after cell drops — "
            "SPA requires at least 2 cells (a single-cell test has no multiplicity). "
            f"Dropped: {[d.label for d in matrix.dropped]}"
        )

    # Log any dropped cells so the caller can audit them
    if matrix.dropped:
        for dc in matrix.dropped:
            logger.warning(
                json.dumps({
                    "event": "r5_smoke.dropped_cell",
                    "label": dc.label,
                    "variant": dc.variant,
                    "pair": dc.pair,
                    "reason": dc.reason,
                })
            )

    # Run R5c Hansen SPA + White RC on the joint matrix
    r5c = r5c_hansen_spa(
        pair_returns=matrix.R,
        master_seed=master_seed,
        block_length=block_length,
        B=B,
    )

    _log(
        "r5_smoke.result",
        T=matrix.T,
        k=matrix.k,
        labels=matrix.labels,
        spa_consistent=r5c.pvalue_consistent,
        spa_lower=r5c.pvalue_lower,
        spa_upper=r5c.pvalue_upper,
        white_rc_pvalue=r5c.white_rc_pvalue,
        block_length_used=r5c.block_length_used,
        block_length_auto=r5c.block_length_auto,
        B=r5c.B,
        seed=r5c.seed,
    )

    return R5CarryResult(
        spa_pvalue_consistent=r5c.pvalue_consistent,
        spa_pvalue_lower=r5c.pvalue_lower,
        spa_pvalue_upper=r5c.pvalue_upper,
        white_rc_pvalue=r5c.white_rc_pvalue,
        block_length_used=r5c.block_length_used,
        block_length_auto=r5c.block_length_auto,
        B=r5c.B,
        seed=r5c.seed,
        T=matrix.T,
        k=matrix.k,
        labels=matrix.labels,
        dropped=matrix.dropped,
        r5c_result=r5c,
    )
