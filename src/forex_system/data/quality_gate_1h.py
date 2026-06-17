"""1h parquet data-quality gate — admit / exclude / manual-review per pair.

Authoritative spec: .fintech-org/artifacts/2026-06-16-prep-plan/cto-gate-spec-corrected.yaml
CRO binding constraints: .fintech-org/artifacts/2026-06-16-prep-plan/cro-risk-gates.yaml

GATE SEMANTICS
--------------
Per-pair, fully independent. Verdict = ADMIT | EXCLUDE | MANUAL_REVIEW.
- ADMIT        : pair cleared all gates; may enter trial universe.
- EXCLUDE      : pair fails one or more hard gates; dropped from universe, never imputed.
- MANUAL_REVIEW: pair passes hard gates but has SC-3 or SC-4 flags requiring human sign-off.

NEVER IMPUTE — the direct remediation of the QRB-6 zero-imputed trial void.

CALL SEQUENCE
-------------
Individual pairs (steps 1-8):

    result = coverage_gate(parquet_path, "EURUSD", config, trade_window="2yr")

Cross-pair SC-4 (step 9) — run after all individual gates:

    results = run_all_pair_gates(pair_paths, config)
    apply_sc4_cross_pair_check(results, config)  # mutates in-place (flag only)

Write aggregate gate results:

    write_gate_results(results, out_path)

CONFIGURATION
-------------
Load from config/data_quality_gates_1h.yaml via load_gate_config().
Per-pair thresholds override global defaults; global fills any missing per-pair keys.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# FX market weekend-closed window (UTC): Fri >=21:00 through Sun <22:00.
# Bars in this window are EXCLUDED from in-session / measured-spread counts.
_WEEKEND_CLOSED_DAY_HOUR: frozenset[tuple[int, int]] = frozenset(
    # Friday hours 21..23 (dayofweek == 4)
    [(4, h) for h in range(21, 24)]
    # All of Saturday (dayofweek == 5)
    + [(5, h) for h in range(24)]
    # Sunday hours 0..21 (dayofweek == 6, market opens ~22:00 UTC)
    + [(6, h) for h in range(22)]
)

# Hours per trading week = 24h/day × 5 trading days
_TRADING_HOURS_PER_WEEK = 24 * 5  # = 120; excludes 48h weekend


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ConfigurationError(Exception):
    """Raised when gate configuration is internally inconsistent (e.g. ceiling <= floor)."""


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_gate_config(config_path: Path | str | None = None) -> dict:
    """Load gate config from YAML, merging per-pair overrides onto global defaults.

    Returns a dict with keys:
      'global': dict of global threshold fields
      'per_pair': dict[pair_symbol -> dict] of merged (global + override) thresholds
      'sc4_scaling': dict of SC-4 cross-pair ratio bounds
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "data_quality_gates_1h.yaml"
    config_path = Path(config_path)
    with config_path.open() as f:
        raw = yaml.safe_load(f)

    global_cfg = raw.get("global", {})
    per_pair_raw = raw.get("per_pair", {})
    sc4 = raw.get("sc4_scaling", {})

    # Merge: per-pair entries inherit all global fields not explicitly overridden
    per_pair_merged: dict[str, dict] = {}
    for pair, overrides in per_pair_raw.items():
        merged = dict(global_cfg)
        merged.update(overrides)
        per_pair_merged[pair] = merged

    return {"global": global_cfg, "per_pair": per_pair_merged, "sc4_scaling": sc4}


def _pair_cfg(pair: str, config: dict) -> dict:
    """Return merged config for a single pair, falling back to global defaults."""
    pp = config.get("per_pair", {})
    if pair in pp:
        return pp[pair]
    # Pair not in per_pair — use globals with no spread band (will be checked later)
    return config.get("global", {})


# ---------------------------------------------------------------------------
# Weekend / in-session helpers
# ---------------------------------------------------------------------------


def _is_in_session(ts: pd.Timestamp) -> bool:
    """Return True if the timestamp is an FX trading-session hour (UTC)."""
    dow = ts.dayofweek  # 0=Mon, 6=Sun
    return (dow, ts.hour) not in _WEEKEND_CLOSED_DAY_HOUR


def _expected_trading_bars(start: pd.Timestamp, end: pd.Timestamp) -> int:
    """Count 1h trading-session slots in [start, end) excluding weekend-closed hours.

    The denominator for bar_coverage_pct (gate_1). Slots are Mon 22:00 UTC through
    Fri 20:59 UTC, matching Dukascopy's observed trading hours.
    """
    # Generate every hourly slot in the window and count in-session ones
    idx = pd.date_range(start=start, end=end, freq="1h", tz="UTC", inclusive="left")
    count = sum(1 for ts in idx if _is_in_session(ts))
    return count


# ---------------------------------------------------------------------------
# Spread-correctness check helpers (SC-1, SC-2, SC-3, SC-5)
# ---------------------------------------------------------------------------


def _apply_sc_bar_checks(
    df: pd.DataFrame,
    zero_spread_run_threshold: int = 6,
    sc1_sc5_pair_threshold: float = 0.05,
) -> tuple[pd.Series, list[str], str | None]:
    """Apply per-bar SC-1, SC-2, SC-5 checks; detect SC-3 runs.

    Returns
    -------
    measured_mask : bool Series — True where bar is MEASURED (passes all SC checks).
                    Reflects the TRUE per-bar exclusion rate so the caller's
                    measured_spread_fraction diagnostic stays honest even when the
                    SC-1/SC-5 pair-level threshold trips.
    spread_flags  : list of manual-review flag strings (SC-3)
    pair_sc_exclude : non-None issue string if the SC-1/SC-5 pair-level threshold
                      tripped (>5% of bars fail ordering/p90). When set, the caller
                      MUST EXCLUDE the pair regardless of the measured fraction.
    """
    spread_flags: list[str] = []
    pair_sc_exclude: str | None = None

    n = len(df)
    measured = pd.Series(True, index=df.index)

    # SC-5: spread_p90_pips must be > 0 and finite
    bad_p90 = ~(df["spread_p90_pips"].notna() & (df["spread_p90_pips"] > 0) & np.isfinite(df["spread_p90_pips"]))
    if bad_p90.any():
        measured &= ~bad_p90
        logger.debug("SC-5: %d bars excluded (p90 not positive/finite)", bad_p90.sum())

    # SC-1: spread_median_pips <= spread_p90_pips (ordering sanity)
    bad_order = df["spread_median_pips"] > df["spread_p90_pips"]
    if bad_order.any():
        measured &= ~bad_order
        logger.debug("SC-1: %d bars excluded (median > p90 ordering violation)", bad_order.sum())

    # SC-2: zero-volume bars — spread aggregate fabricated from no ticks
    bad_vol = df["volume"] <= 0
    if bad_vol.any():
        measured &= ~bad_vol
        logger.debug("SC-2: %d bars excluded (volume <= 0)", bad_vol.sum())

    # SC-3: run of >=N consecutive bars with spread_median_pips == 0.0
    zero_spread = (df["spread_median_pips"] == 0.0)
    if zero_spread.any():
        # Find max run of consecutive True values
        max_run = _max_consecutive_run(zero_spread)
        if max_run >= zero_spread_run_threshold:
            flag = (
                f"SC-3: run of {max_run} consecutive zero-spread bars detected "
                f"(threshold={zero_spread_run_threshold}) — MANUAL REVIEW required"
            )
            spread_flags.append(flag)
            logger.warning("SC-3 flag: %s", flag)

    # Pair-level SC-1/SC-5 check: if > threshold fraction of bars fail the ordering
    # (SC-1) or p90-positive (SC-5) checks, the PAIR is excluded. We signal this via
    # a dedicated flag rather than zeroing the measured mask, so the reported
    # measured_spread_fraction stays an honest diagnostic of the true exclusion rate.
    n_failed_bar = int((bad_p90 | bad_order).sum())
    if n > 0 and n_failed_bar / n > sc1_sc5_pair_threshold:
        pct = 100.0 * n_failed_bar / n
        pair_sc_exclude = (
            f"SC-1/SC-5 pair-level FAIL: {pct:.1f}% of bars failed ordering/p90 checks "
            f"(threshold {100.0 * sc1_sc5_pair_threshold:.1f}%) — pair EXCLUDED"
        )
        logger.warning(pair_sc_exclude)

    return measured, spread_flags, pair_sc_exclude


def _max_consecutive_run(mask: pd.Series) -> int:
    """Return the length of the longest consecutive True run in a bool Series."""
    if not mask.any():
        return 0
    # Use numpy cumsum trick
    arr = mask.to_numpy()
    max_run = cur = 0
    for v in arr:
        cur = cur + 1 if v else 0
        if cur > max_run:
            max_run = cur
    return max_run


# ---------------------------------------------------------------------------
# Gate result dataclass
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Result of running the coverage_gate for a single pair."""

    pair: str
    verdict: Literal["ADMIT", "EXCLUDE", "MANUAL_REVIEW"]
    approved: bool
    issues: list[str] = field(default_factory=list)
    spread_flags: list[str] = field(default_factory=list)
    # Diagnostics
    bar_count: int = 0
    expected_trading_bars: int = 0
    bar_coverage_pct: float = 0.0
    measured_spread_bars: int = 0
    in_session_bars: int = 0
    measured_spread_fraction: float = 0.0
    max_contiguous_gap_hours: int = 0
    spread_median_pct: float = 0.0  # pair-level median of spread_median_pips

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "verdict": self.verdict,
            "approved": self.approved,
            "issues": self.issues,
            "spread_flags": self.spread_flags,
            "bar_count": self.bar_count,
            "expected_trading_bars": self.expected_trading_bars,
            "bar_coverage_pct": round(self.bar_coverage_pct, 4),
            "measured_spread_bars": self.measured_spread_bars,
            "in_session_bars": self.in_session_bars,
            "measured_spread_fraction": round(self.measured_spread_fraction, 4),
            "max_contiguous_gap_hours": self.max_contiguous_gap_hours,
            "spread_median_pct": round(self.spread_median_pct, 4),
        }


# ---------------------------------------------------------------------------
# Core gate callable
# ---------------------------------------------------------------------------


def coverage_gate(
    parquet_path: Path | str,
    pair: str,
    config: dict,
    trade_window: Literal["2yr", "5yr"] = "2yr",
) -> GateResult:
    """Run the per-pair 1h data-quality gate.

    Parameters
    ----------
    parquet_path : path to the pair's 1h parquet file
    pair         : pair symbol, e.g. "EURUSD"
    config       : loaded gate config (from load_gate_config())
    trade_window : "2yr" or "5yr" — selects min_bars threshold

    Returns a GateResult with verdict ADMIT | EXCLUDE | MANUAL_REVIEW.
    """
    pair = pair.upper()
    cfg = _pair_cfg(pair, config)
    result = GateResult(pair=pair, verdict="EXCLUDE", approved=True)

    # ------------------------------------------------------------------
    # Step 1: Load parquet
    # ------------------------------------------------------------------
    parquet_path = Path(parquet_path)
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as exc:
        result.approved = False
        result.issues.append(f"parquet load failed: {exc}")
        result.verdict = "EXCLUDE"
        logger.error("coverage_gate[%s] parquet load failed: %s", pair, exc)
        return result

    if df.empty:
        result.approved = False
        result.issues.append("parquet is empty")
        result.verdict = "EXCLUDE"
        return result

    logger.info(
        "coverage_gate[%s] loaded %d bars from %s",
        pair, len(df), parquet_path,
    )

    # ------------------------------------------------------------------
    # Step 2: Structural schema check
    # ------------------------------------------------------------------
    # Import here to avoid circular dependency; validate_1h_schema is in scripts/
    # We only use it for STRUCTURAL checks (index type, OHLC consistency, stale runs,
    # price spikes, duplicate timestamps).  Per-bar data-quality issues (volume <= 0,
    # spread_median <= 0) are INTENTIONALLY left to the gate's own SC-1..SC-5 logic
    # so they result in per-bar EXCLUSION rather than a full-dataset reject.
    _STRUCTURAL_ISSUE_PREFIXES = (
        "Missing columns",
        "Index is not",
        "Index is tz",
        "Index has duplicate",
        "Index is not monoton",
        "bars where high <",
        "bars where low <",
        "NaN price values",
        "non-positive price values",
        "stale data:",
        "price spikes >",
        "Partial spread columns",
    )
    _DATA_QUALITY_WARNINGS = (
        "bars with volume <= 0",
        "bars with spread_median_pips",   # handled by SC gate below
        "NaN spread_median_pips",
        "bars with spread_median_pips > ",
    )

    try:
        import sys
        scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from ingest_dukascopy_1h import SPREAD_COL_MISSING_WARNING, validate_1h_schema
        schema_issues = validate_1h_schema(df, pair)
    except ImportError:
        # C-4 FAIL-CLOSED: if validate_1h_schema cannot be imported, we cannot
        # perform the structural schema check.  Rather than silently skipping it and
        # emitting a potentially wrong ADMIT/EXCLUDE, we treat this as a structural
        # gate failure and return EXCLUDE.  A missing-script environment must be fixed
        # before the gate can run; proceeding without the check is not safe.
        result.approved = False
        result.issues.append(
            "structural schema check SKIPPED — could not import validate_1h_schema "
            "from scripts/ingest_dukascopy_1h.py; gate returns EXCLUDE (fail-closed)"
        )
        result.verdict = "EXCLUDE"
        logger.error(
            "coverage_gate[%s] ImportError: validate_1h_schema not importable — "
            "returning EXCLUDE (fail-closed, C-4)",
            pair,
        )
        return result

    spread_cols_present = all(
        c in df.columns
        for c in ("spread_median_pips", "spread_mean_pips", "spread_p90_pips")
    )

    if schema_issues:
        # Separate structural issues (early-exit) from data-quality warnings (handled by SC).
        #
        # C-3 FAIL-CLOSED (CTO ratification pending): an issue string that does NOT
        # match SPREAD_COL_MISSING_WARNING AND does NOT match any known data-quality
        # warning prefix is treated conservatively as a STRUCTURAL issue (early-exit
        # EXCLUDE), not silently deferred.  This prevents an unrecognized warning
        # category from slipping through as a false ADMIT.  If a new warning category
        # from validate_1h_schema is intended to be deferred to SC gates, it must be
        # explicitly added to _DATA_QUALITY_WARNINGS with CTO sign-off.
        # TODO: CTO ratification of this boundary is pending (C-3, fix-round-1).
        structural_issues = []
        for issue in schema_issues:
            if issue == SPREAD_COL_MISSING_WARNING:
                continue  # handled below via spread_cols_present check
            known_dq = any(issue.startswith(w) or w in issue for w in _DATA_QUALITY_WARNINGS)
            if known_dq:
                continue  # defer to SC gate per documented deviation from spec (see deviations section)
            # C-3: unrecognized / unmatched issue — fail closed
            structural_issues.append(issue)
        if structural_issues:
            result.approved = False
            result.issues.extend(structural_issues)
            result.issues.append("structural schema failed — re-pull required")
            result.verdict = "EXCLUDE"
            logger.error("coverage_gate[%s] structural issues: %s", pair, structural_issues)
            return result
        if not spread_cols_present and SPREAD_COL_MISSING_WARNING in schema_issues:
            result.approved = False
            result.issues.append(
                "spread columns absent — re-pull required; DERIVED cost not accepted for 1h trials"
            )
            result.verdict = "EXCLUDE"
            return result

    if not spread_cols_present:
        result.approved = False
        result.issues.append(
            "spread columns absent — re-pull required; DERIVED cost not accepted for 1h trials"
        )
        result.verdict = "EXCLUDE"
        return result

    # ------------------------------------------------------------------
    # Step 3: Bar-coverage check (gate_1)
    # ------------------------------------------------------------------
    result.bar_count = len(df)
    if not isinstance(df.index, pd.DatetimeIndex):
        result.approved = False
        result.issues.append("index is not DatetimeIndex — cannot compute coverage")
        result.verdict = "EXCLUDE"
        return result

    start_ts = df.index[0]
    end_ts = df.index[-1] + pd.Timedelta(hours=1)  # exclusive end
    expected_bars = _expected_trading_bars(start_ts, end_ts)
    result.expected_trading_bars = expected_bars

    # Numerator: in-session bars only (exclude any weekend/closed bars that
    # may be present in the parquet, e.g. synthetic test data or misclassified bars).
    # Denominator: expected_trading_bars (in-session slots in the window).
    # Both numerator and denominator count in-session slots → ratio in [0, 1].
    actual_in_session = sum(1 for ts in df.index if _is_in_session(ts))
    bar_coverage_pct = actual_in_session / expected_bars if expected_bars > 0 else 0.0
    result.bar_coverage_pct = bar_coverage_pct

    bar_coverage_min = cfg.get("bar_coverage_min", 0.85)
    min_bars_key = "min_bars_2yr" if trade_window == "2yr" else "min_bars_5yr"
    min_bars = cfg.get(min_bars_key, 10000 if trade_window == "2yr" else 25000)

    if bar_coverage_pct < bar_coverage_min:
        result.approved = False
        result.issues.append(
            f"gate_1 FAIL: bar_coverage_pct={bar_coverage_pct:.3f} < {bar_coverage_min} "
            f"(expected_bars={expected_bars}, actual_in_session={actual_in_session})"
        )
        logger.warning("coverage_gate[%s] gate_1 fail: coverage=%.3f", pair, bar_coverage_pct)

    if actual_in_session < min_bars:
        result.approved = False
        result.issues.append(
            f"gate_1 FAIL: bar_count={actual_in_session} < {min_bars_key}={min_bars}"
        )

    # ------------------------------------------------------------------
    # Step 4: Spread-correctness checks (SC-1, SC-2, SC-3, SC-5)
    # ------------------------------------------------------------------
    zero_spread_run_threshold = cfg.get("zero_spread_run_threshold", 6)
    sc1_sc5_threshold = cfg.get("sc1_sc5_pair_exclude_threshold", 0.05)

    measured_mask, spread_flags, pair_sc_exclude = _apply_sc_bar_checks(
        df,
        zero_spread_run_threshold=zero_spread_run_threshold,
        sc1_sc5_pair_threshold=sc1_sc5_threshold,
    )
    result.spread_flags = spread_flags
    # SC-1/SC-5 pair-level exclusion is a HARD gate independent of the measured
    # fraction; recorded as an issue so the verdict is EXCLUDE while the reported
    # measured_spread_fraction below remains the honest per-bar rate.
    if pair_sc_exclude is not None:
        result.approved = False
        result.issues.append(pair_sc_exclude)

    # ------------------------------------------------------------------
    # Step 5: Measured-spread-fraction check (gate_2)
    # ------------------------------------------------------------------
    in_session_mask = pd.Series(
        [_is_in_session(ts) for ts in df.index], index=df.index, dtype=bool
    )
    in_session_bars = int(in_session_mask.sum())
    result.in_session_bars = in_session_bars

    measured_in_session = int((in_session_mask & measured_mask).sum())
    result.measured_spread_bars = measured_in_session

    measured_spread_fraction = measured_in_session / in_session_bars if in_session_bars > 0 else 0.0
    result.measured_spread_fraction = measured_spread_fraction

    measured_spread_min = cfg.get("measured_spread_min", 0.90)
    if measured_spread_fraction < measured_spread_min:
        result.approved = False
        result.issues.append(
            f"gate_2 FAIL: measured_spread_fraction={measured_spread_fraction:.3f} < {measured_spread_min} "
            f"(measured={measured_in_session}, in_session={in_session_bars})"
        )
        logger.warning(
            "coverage_gate[%s] gate_2 fail: measured_fraction=%.3f", pair, measured_spread_fraction
        )

    # ------------------------------------------------------------------
    # Step 6: Max contiguous gap check
    # ------------------------------------------------------------------
    max_gap_h = _max_contiguous_gap_hours(df.index, start_ts, end_ts)
    result.max_contiguous_gap_hours = max_gap_h

    max_gap_allowed = cfg.get("max_contiguous_gap_h", 24)
    if max_gap_h > max_gap_allowed:
        result.approved = False
        result.issues.append(
            f"gap FAIL: max_contiguous_gap_hours={max_gap_h} > {max_gap_allowed}"
        )
        logger.warning("coverage_gate[%s] gap fail: max_gap=%d h", pair, max_gap_h)

    # ------------------------------------------------------------------
    # Step 7: Spread-band check
    # ------------------------------------------------------------------
    spread_median_floor = cfg.get("spread_median_floor")
    spread_median_ceiling = cfg.get("spread_median_ceiling")
    spread_p90_ceiling = cfg.get("spread_p90_ceiling")

    if spread_median_floor is not None and spread_median_ceiling is not None:
        # Band validity — halt on misconfiguration
        if spread_median_ceiling <= spread_median_floor:
            raise ConfigurationError(
                f"Pair {pair}: spread_median_ceiling ({spread_median_ceiling}) "
                f"<= spread_median_floor ({spread_median_floor}) — gate config is invalid"
            )

        measured_spread_vals = df.loc[measured_mask, "spread_median_pips"]
        if len(measured_spread_vals) > 0:
            pair_spread_median = float(measured_spread_vals.median())
        else:
            pair_spread_median = 0.0
        result.spread_median_pct = pair_spread_median

        if pair_spread_median < spread_median_floor:
            result.approved = False
            result.issues.append(
                f"spread_band FAIL: pair_spread_median={pair_spread_median:.3f} pips "
                f"< floor={spread_median_floor}"
            )
        elif pair_spread_median > spread_median_ceiling:
            result.approved = False
            result.issues.append(
                f"spread_band FAIL: pair_spread_median={pair_spread_median:.3f} pips "
                f"> ceiling={spread_median_ceiling}"
            )

        if spread_p90_ceiling is not None:
            measured_p90_vals = df.loc[measured_mask, "spread_p90_pips"]
            if len(measured_p90_vals) > 0:
                pair_p90 = float(measured_p90_vals.median())
                if pair_p90 > spread_p90_ceiling:
                    result.approved = False
                    result.issues.append(
                        f"spread_band FAIL: median of spread_p90_pips={pair_p90:.3f} > p90_ceiling={spread_p90_ceiling}"
                    )

    # ------------------------------------------------------------------
    # Step 8: Emit result
    # ------------------------------------------------------------------
    if not result.approved:
        result.verdict = "EXCLUDE"
    elif result.spread_flags:
        result.verdict = "MANUAL_REVIEW"
    else:
        result.verdict = "ADMIT"

    logger.info(
        "coverage_gate[%s] verdict=%s approved=%s issues=%d flags=%d",
        pair, result.verdict, result.approved, len(result.issues), len(result.spread_flags),
    )
    return result


def _max_contiguous_gap_hours(
    index: pd.DatetimeIndex,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> int:
    """Compute the longest consecutive run of missing in-session trading hours.

    Scans every expected 1h trading slot in [start, end) and counts the longest
    run of consecutive slots absent from the parquet index.

    DELIBERATE: a weekend (legitimately-absent, market-closed bars) RESETS the gap
    counter rather than bridging two weekday gaps into one. Per the CRO coverage_gate
    rationale, the gap rule guards against a spread blackout "during a real trade
    window" — the weekend is not a trade window. A Friday-evening absence and a
    Monday-morning absence are therefore counted as two separate gaps, which is
    correct: neither alone constitutes a multi-day in-session blackout, and the
    market was genuinely closed between them.
    """
    present = set(index)
    slot_range = pd.date_range(start=start, end=end, freq="1h", tz="UTC", inclusive="left")
    max_gap = cur_gap = 0
    for ts in slot_range:
        if not _is_in_session(ts):
            # Weekend/closed — reset gap counter (not a missing in-session bar).
            # See docstring: this is deliberate, not a bug.
            cur_gap = 0
            continue
        if ts not in present:
            cur_gap += 1
            if cur_gap > max_gap:
                max_gap = cur_gap
        else:
            cur_gap = 0
    return max_gap


# ---------------------------------------------------------------------------
# Cross-pair SC-4 check (step 9 — run AFTER all individual gates)
# ---------------------------------------------------------------------------


def apply_sc4_cross_pair_check(
    results: list[GateResult],
    config: dict,
) -> None:
    """Apply SC-4 cross-pair scaling check.  Mutates results in-place.

    SC-4 is a FLAG only — it never auto-excludes. Pairs with suspicious spread
    ratios relative to their instrument-type peers are downgraded ADMIT → MANUAL_REVIEW.
    """
    sc4 = config.get("sc4_scaling", {})
    non_jpy_min = sc4.get("non_jpy_ratio_min", 0.1)
    non_jpy_max = sc4.get("non_jpy_ratio_max", 10.0)
    jpy_min = sc4.get("jpy_vs_nonjpy_ratio_min", 0.05)
    jpy_max = sc4.get("jpy_vs_nonjpy_ratio_max", 20.0)

    jpy_pairs = {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY"}

    # Only consider ADMIT or MANUAL_REVIEW pairs with valid spread_median_pct
    admitted = {r.pair: r for r in results if r.approved and r.spread_median_pct > 0}
    if len(admitted) < 2:
        return

    non_jpy = {p: r.spread_median_pct for p, r in admitted.items() if p not in jpy_pairs}
    jpy = {p: r.spread_median_pct for p, r in admitted.items() if p in jpy_pairs}

    # Check non-JPY pairs against each other
    non_jpy_vals = list(non_jpy.values())
    if len(non_jpy_vals) >= 2:
        for p1, m1 in non_jpy.items():
            for p2, m2 in non_jpy.items():
                if p1 >= p2 or m2 == 0:
                    continue
                ratio = m1 / m2
                if not (non_jpy_min <= ratio <= non_jpy_max):
                    flag = (
                        f"SC-4: non-JPY spread ratio {p1}/{p2} = {ratio:.3f} "
                        f"outside [{non_jpy_min}, {non_jpy_max}] — MANUAL REVIEW"
                    )
                    for pair in (p1, p2):
                        if pair in admitted:
                            r = admitted[pair]
                            r.spread_flags.append(flag)
                            if r.verdict == "ADMIT":
                                r.verdict = "MANUAL_REVIEW"

    # Check JPY pairs against non-JPY reference (use overall non-JPY median as reference)
    if jpy and non_jpy_vals:
        ref_median = float(np.median(non_jpy_vals))
        if ref_median > 0:
            for p, m in jpy.items():
                ratio = m / ref_median
                if not (jpy_min <= ratio <= jpy_max):
                    flag = (
                        f"SC-4: JPY spread ratio {p}/non-JPY-ref = {ratio:.3f} "
                        f"outside [{jpy_min}, {jpy_max}] — MANUAL REVIEW"
                    )
                    r = admitted[p]
                    r.spread_flags.append(flag)
                    if r.verdict == "ADMIT":
                        r.verdict = "MANUAL_REVIEW"


# ---------------------------------------------------------------------------
# Aggregate gate runner
# ---------------------------------------------------------------------------


def run_all_pair_gates(
    pair_paths: dict[str, Path | str],
    config: dict,
    trade_window: Literal["2yr", "5yr"] = "2yr",
) -> list[GateResult]:
    """Run coverage_gate for each pair, then apply SC-4 cross-pair check.

    Parameters
    ----------
    pair_paths   : {pair_symbol: parquet_path}
    config       : loaded gate config
    trade_window : "2yr" | "5yr"

    Returns list of GateResult (one per pair), SC-4 applied in-place.
    """
    results: list[GateResult] = []
    for pair, path in pair_paths.items():
        r = coverage_gate(path, pair, config, trade_window=trade_window)
        results.append(r)

    apply_sc4_cross_pair_check(results, config)

    # Emit never-lands diagnostic
    n_excluded = sum(1 for r in results if r.verdict == "EXCLUDE")
    if n_excluded == len(results):
        logger.critical(
            "coverage_gate NEVER_LANDS_TERMINAL: all %d pairs returned EXCLUDE. "
            "No 1h trial may be frozen. Escalate to CEO per CTO spec Section 5.",
            len(results),
        )

    return results


# ---------------------------------------------------------------------------
# Gate-result writer
# ---------------------------------------------------------------------------


def write_gate_results(
    results: list[GateResult],
    out_path: Path | str,
    *,
    timestamp: str | None = None,
) -> None:
    """Write aggregate gate results to YAML.

    Gate results are versioned by timestamp (ISO-8601 UTC). A re-run replaces
    the old file; callers that need history should version the path externally.
    """
    import datetime as dt

    if timestamp is None:
        timestamp = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_admit = sum(1 for r in results if r.verdict == "ADMIT")
    n_manual = sum(1 for r in results if r.verdict == "MANUAL_REVIEW")
    n_exclude = sum(1 for r in results if r.verdict == "EXCLUDE")

    aggregate_status = "NEVER_LANDS_TERMINAL" if n_exclude == len(results) else "PARTIAL_OR_CLEAR"

    output = {
        "gate_run_timestamp": timestamp,
        "status": aggregate_status,
        "summary": {
            "ADMIT": n_admit,
            "MANUAL_REVIEW": n_manual,
            "EXCLUDE": n_exclude,
        },
        "pairs": [r.to_dict() for r in results],
    }

    with out_path.open("w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False)

    logger.info(
        "gate_results written → %s  ADMIT=%d MANUAL_REVIEW=%d EXCLUDE=%d",
        out_path, n_admit, n_manual, n_exclude,
    )
