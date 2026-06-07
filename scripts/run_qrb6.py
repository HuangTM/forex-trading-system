"""QRB-6 one-shot CB-event-study runner (trial fa0f982a).

ABSOLUTE PROHIBITION: this script MUST NOT be executed before the freeze-receipt
is committed AND the --ceo-ack flag is passed.  Running it early voids the
pre-registration (§1.4(1), §7).

Usage:
    # Dry run (default) — exercises the full pipeline against synthetic stub data;
    # NEVER reads data/processed/*.parquet; validates structure only.
    python scripts/run_qrb6.py

    # Live run — requires freeze-receipt AND --ceo-ack; reads real data.
    python scripts/run_qrb6.py --ceo-ack

    # Explicit dry-run flag (equivalent to default):
    python scripts/run_qrb6.py --dry-run

Hard interlocks (RULE 0 TECHNICAL_FAILURE if any fires):
  (a) Freeze-receipt file must exist at the canonical path.
  (b) receipt.prereg_sha256 must match sha256(pre-reg file as committed).
  (c) --ceo-ack flag must be passed for a live run.
  (d) All receipt constants must match the embedded _EXPECTED guards in
      qrb6_decision.py (cross-trial constant contamination check).
  (e) No data/processed/ read occurs unless --ceo-ack is present.

The receipt does not exist yet — the runner REFUSES to run live without it.
That is the ordering clause: freeze-receipt cut is ORDERED AFTER this runner
commit exists and is pinned (§7 ordering clause).

Orchestration (live run):
    receipt validation → event-set construction → per-pair returns (D-1, D, D+2)
    → sign_align → y_e assembly → spread_z suppression → Politis-White auto
    block-length per bank → bank-blocked bootstrap (K=10000, seed=387992)
    → DSR gate → evaluate_decision (§4.2 RULES 0-4) → result YAML

Dry run:
    Same pipeline; synthetic stub data replaces file-based returns and spreads.
    calendar parquet IS read (calendar-count validation is structure-validate-only;
    no return data).

Result written to:
    references/pre-registrations/qrb6_cb_event_study.STEP-RESULT.yaml
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import sys
from pathlib import Path

import numpy as np
import yaml

# ---------------------------------------------------------------------------
# Logging — structured decision-trace (log-as-decision-trace rubric)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("forex_system.harness.qrb6_runner")


def _log(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log entry."""
    entry = {"event": event, **fields}
    logger.info(json.dumps(entry, default=str))


# ---------------------------------------------------------------------------
# Frozen path constants (QRB-6 specific; no cross-trial constants)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_PREREG_PATH = Path(
    "references/pre-registrations/qrb6_cb_event_study.md"
)
_RECEIPT_PATH = Path(
    "references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml"
)
_RESULT_PATH = Path(
    "references/pre-registrations/qrb6_cb_event_study.STEP-RESULT.yaml"
)
# Dry-run results NEVER land at the canonical path — a stub verdict at the real
# path is poison if mistaken for the one-shot outcome (RULE-0 remediation 2026-06-07).
_DRY_RUN_RESULT_PATH = Path(
    "references/pre-registrations/qrb6_cb_event_study.STEP-RESULT.DRY-RUN.yaml"
)
_CALENDAR_PATH = Path("data/rates/cb_decision_dates.parquet")
_PROCESSED_DATA_DIR = Path("data/processed")
_SPREADS_DATA_DIR = Path("data/spreads")
# Fix 2: frozen cost manifest path — Mathematician authors values; loader wires here.
# If absent → RULE_0_TECHNICAL_FAILURE (same discipline as missing receipt).
_COST_MANIFEST_PATH = Path("config/cost_freeze_qrb6.yaml")

# QRB-6 registered pair universe (§3.2, frozen, 11 unique Scenario A pairs).
# This is the ground-truth universe for the cost-coverage gate (Fix 3).
# FED: EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD (6)
# BOJ: USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY (6)
# RBA: AUDUSD, AUDJPY (2)
# BOC: USDCAD, CADJPY (2)
# Unique union = 11 pairs (EURGBP is Scenario B only; not in any Scenario A bank).
_QRB6_REGISTERED_PAIRS: frozenset[str] = frozenset({
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY",
})

# Refusal message (printed to stderr when no receipt or no --ceo-ack)
_REFUSAL_MESSAGE = (
    "\n"
    "QRB-6 RUNNER REFUSED — pre-registration freeze-receipt not present or\n"
    "--ceo-ack flag not passed.\n"
    "\n"
    "This is the QRB-6 one-shot runner (trial fa0f982a).  It refuses to\n"
    "execute a live run unless:\n"
    "  (a) The freeze-receipt exists at:\n"
    "        references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml\n"
    "  (b) The receipt's prereg_sha256 matches sha256(the pre-reg file).\n"
    "  (c) The --ceo-ack flag is explicitly passed.\n"
    "\n"
    "The freeze-receipt is cut AFTER consensus ratification (AC-7) and CEO\n"
    "sign-off (AC-8) by running:\n"
    "    python scripts/cut_freeze_receipt.py --target qrb6 --cut\n"
    "\n"
    "Running this script before the receipt exists voids the pre-registration\n"
    "(§1.4(1)/(5), §7 ordering clause).  DO NOT attempt to bypass this gate.\n"
    "\n"
    "Use --dry-run (or no flags) to exercise the pipeline against synthetic\n"
    "stub data without touching data/processed/ or requiring a receipt.\n"
)


# ---------------------------------------------------------------------------
# SHA-256 helpers (mirroring run_r5_step4.py)
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cost_manifest(manifest_path: Path) -> tuple[dict, str]:
    """Load the QRB-6 frozen cost manifest and return a PairInfo dict.

    Fix 2 (remediation 2026-06-07): per-pair costs come from a frozen manifest
    at config/cost_freeze_qrb6.yaml authored by the Mathematician under a
    mechanical rule ratified by NHT.  Hardcoding costs or reading DEFAULT_PAIRS
    is FORBIDDEN here — it would expose only the 3 original pairs.

    Interlock:
      - If the manifest file is absent → RULE_0_TECHNICAL_FAILURE.
      - If a registered QRB-6 pair is absent from the manifest → RULE_0_TECHNICAL_FAILURE.
      - If a registered pair has spread_pips == 0.0 and the manifest is not marked
        as a test stub → loud WARNING (placeholder not yet filled by Mathematician;
        RULE_0 in live mode).

    The manifest sha256 is logged for audit traceability.

    Parameters
    ----------
    manifest_path:
        Absolute path to config/cost_freeze_qrb6.yaml.

    Returns
    -------
    dict[str, PairInfo]
        Mapping of UPPERCASE pair symbol → PairInfo (same type as DEFAULT_PAIRS).
    """
    from forex_system.core.types import PairInfo

    if not manifest_path.exists():
        _log(
            "qrb6_runner.cost_manifest_missing",
            manifest_path=str(manifest_path),
            action="RULE_0_TECHNICAL_FAILURE",
        )
        print(
            f"RULE_0_TECHNICAL_FAILURE: cost manifest not found: {manifest_path}\n"
            "The Mathematician must author config/cost_freeze_qrb6.yaml before the "
            "remediated re-run is authorized.",
            file=sys.stderr,
        )
        sys.exit(1)

    manifest_sha = _sha256_file(manifest_path)
    _log(
        "qrb6_runner.cost_manifest_loaded",
        manifest_path=str(manifest_path),
        manifest_sha256=manifest_sha,
    )

    with open(manifest_path) as fh:
        manifest = yaml.safe_load(fh)

    raw_pairs = manifest.get("pairs", [])
    pair_dict: dict[str, PairInfo] = {}
    for entry in raw_pairs:
        sym = str(entry["symbol"]).upper()
        pair_dict[sym] = PairInfo(
            symbol=sym,
            pip_value=float(entry["pip_value"]),
            spread_pips=float(entry["spread_pips"]),
            slippage_pips=float(entry["slippage_pips"]),
            commission_pips=float(entry["commission_pips"]),
            swap_long_pips_per_day=float(entry["swap_long_pips_per_day"]),
            swap_short_pips_per_day=float(entry["swap_short_pips_per_day"]),
        )

    # Coverage gate: every registered pair must appear in the manifest.
    missing = _QRB6_REGISTERED_PAIRS - set(pair_dict.keys())
    if missing:
        _log(
            "qrb6_runner.cost_manifest_coverage_fail",
            missing_pairs=sorted(missing),
            registered_pairs=sorted(_QRB6_REGISTERED_PAIRS),
            manifest_pairs=sorted(pair_dict.keys()),
            action="RULE_0_TECHNICAL_FAILURE",
        )
        print(
            f"RULE_0_TECHNICAL_FAILURE: cost manifest missing pairs: {sorted(missing)}\n"
            "Every QRB-6 registered pair must have a non-zero cost entry.\n"
            f"Manifest: {manifest_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Positivity gate: spread_pips must be > 0 for every registered pair in live mode.
    # (In test-stub manifests, zeros are acceptable for the unit tests; the live gate
    # is applied separately inside _run_pipeline for live runs.)
    zero_spread = [
        sym for sym in _QRB6_REGISTERED_PAIRS
        if pair_dict[sym].spread_pips <= 0.0
    ]
    if zero_spread:
        _log(
            "qrb6_runner.cost_manifest_zero_spread_pairs",
            zero_spread_pairs=sorted(zero_spread),
            note="placeholder_values_not_yet_authored_by_mathematician",
            level="WARNING",
        )
        # This is a WARNING at load time; the live gate enforces positivity.

    _log(
        "qrb6_runner.cost_manifest_ok",
        pairs_loaded=sorted(pair_dict.keys()),
        manifest_sha256=manifest_sha,
    )
    return pair_dict, manifest_sha


def _validate_receipt(receipt_path: Path) -> dict:
    """Load and validate the freeze-receipt.

    Checks:
      (a) Receipt file exists.
      (b) prereg_sha256 field present.
      (c) sha256(pre-reg file bytes) == receipt.prereg_sha256.

    Returns the parsed receipt dict on success.
    Calls sys.exit(1) on any validation failure (RULE 0 TECHNICAL FAILURE).
    """
    if not receipt_path.exists():
        _log(
            "qrb6_runner.gate_refused",
            reason="freeze_receipt_missing",
            receipt_path=str(receipt_path),
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(_REFUSAL_MESSAGE, file=sys.stderr)
        print(
            f"ERROR: freeze-receipt not found: {receipt_path}\n"
            "Run scripts/cut_freeze_receipt.py --target qrb6 --cut after "
            "consensus ratification to produce the receipt.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(receipt_path) as fh:
        receipt = yaml.safe_load(fh)

    if "prereg_sha256" not in receipt:
        _log(
            "qrb6_runner.gate_refused",
            reason="receipt_missing_prereg_sha256",
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(
            f"ERROR: freeze-receipt {receipt_path} missing 'prereg_sha256'.",
            file=sys.stderr,
        )
        sys.exit(1)

    prereg_path = Path(receipt.get("prereg_path", str(_PREREG_PATH)))
    if not prereg_path.exists():
        _log(
            "qrb6_runner.gate_refused",
            reason="prereg_file_missing",
            prereg_path=str(prereg_path),
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(f"ERROR: pre-reg file not found: {prereg_path}", file=sys.stderr)
        sys.exit(1)

    actual_sha256 = _sha256_file(prereg_path)
    expected_sha256 = receipt["prereg_sha256"]

    _log(
        "qrb6_runner.receipt_check",
        prereg_path=str(prereg_path),
        actual_sha256=actual_sha256,
        expected_sha256=expected_sha256,
        match=(actual_sha256 == expected_sha256),
    )

    if actual_sha256 != expected_sha256:
        _log(
            "qrb6_runner.gate_refused",
            reason="prereg_sha256_mismatch",
            actual=actual_sha256,
            expected=expected_sha256,
            action="EXIT_1_TECHNICAL_FAILURE",
        )
        print(
            f"ERROR: pre-registration SHA-256 mismatch.\n"
            f"  Expected: {expected_sha256}\n"
            f"  Actual:   {actual_sha256}\n"
            "The pre-reg file has been modified after the receipt was written. "
            "This voids the pre-registration.  Do not read any p-values.",
            file=sys.stderr,
        )
        sys.exit(1)

    return receipt


# ---------------------------------------------------------------------------
# Stub data generator (dry-run mode)
# ---------------------------------------------------------------------------


def _make_stub_returns(
    n_events: int,
    n_pairs: int,
    seed: int = 42,
    include_zero_ret_d: bool = True,
) -> dict:
    """Generate synthetic stub return data for dry-run validation.

    Returns a dict with keys:
      - 'close_d':   shape (n_events, n_pairs) — close prices bar D
      - 'close_dm1': shape (n_events, n_pairs) — close prices bar D-1
      - 'close_dp2': shape (n_events, n_pairs) — close prices bar D+2
      - 'spread_z':  shape (n_events, n_pairs) — spread z-scores
      - 'banks':     list of bank labels per event (length n_events)
    """
    rng = np.random.default_rng(seed)
    close_dm1 = rng.uniform(1.0, 2.0, size=(n_events, n_pairs))
    # Bar-D returns: mix of positive, negative, zero
    ret_d = rng.normal(0.0, 0.01, size=(n_events, n_pairs))
    if include_zero_ret_d:
        # Inject one exactly-zero return to test degenerate handling
        ret_d[0, 0] = 0.0
    close_d = close_dm1 + ret_d
    # Post-window returns (K_post=2 net-of-cost cumulative)
    post_ret = rng.normal(0.0, 0.01, size=(n_events, n_pairs))
    close_dp2 = close_d + post_ret
    spread_z = rng.uniform(0.0, 5.0, size=(n_events, n_pairs))

    # Assign bank labels (cycle through Scenario A banks)
    _scenario_a_banks_list = ["FED", "BOJ", "RBA", "BOC"]
    banks = [_scenario_a_banks_list[i % 4] for i in range(n_events)]

    return {
        "close_d": close_d,
        "close_dm1": close_dm1,
        "close_dp2": close_dp2,
        "spread_z": spread_z,
        "banks": banks,
    }


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


def _run_pipeline(
    receipt: dict,
    dry_run: bool,
    cost_manifest_path: Path | None = None,
) -> dict:
    """Execute the full QRB-6 pipeline.

    Parameters
    ----------
    receipt:
        Validated freeze-receipt dict (constants already interlock-checked).
    dry_run:
        If True, use synthetic stub data and skip data/processed reads.
    cost_manifest_path:
        Override cost manifest path (for testing; defaults to _COST_MANIFEST_PATH).

    Returns
    -------
    dict
        Result payload for the STEP-RESULT YAML.
    """
    import scipy.stats as sp_stats

    from forex_system.harness.qrb6_decision import (
        _BANK_PAIR_MAP,
        _EXPECTED_POST_2015_CUTOFF,
        _SCENARIO_A_BANKS,
        build_scenario_a_event_set,
        compute_dsr_qrb6,
        compute_event_sharpe_ann,
        compute_sign_align,
        compute_y_e,
        evaluate_decision,
        get_post_2015_mask,
        is_spread_suppressed,
        run_bank_blocked_bootstrap,
    )
    # politis_white_block_length is used inside run_bank_blocked_bootstrap

    # --- Load constants from receipt ---
    master_seed: int = int(receipt["master_seed"])
    K: int = int(receipt["K"])
    sr0_pp: float = float(receipt["sr0_pp"])
    dsr_threshold: float = float(receipt["dsr_threshold"])
    spread_z_threshold: float = float(receipt["spread_z_threshold"])  # NO silent default — guard-checked
    # Hard-key lookups — NO silent fallbacks (RULE-0 if field missing).
    # Silent defaults (get("p_straddle_hi", 0.0522) / get("p_reject_threshold", 0.0478))
    # were the exact same class of bug that caused the spread_z void; removed here.
    # The receipt carries these fields (OBF extra-look penalty applied 2026-06-07;
    # former void-run values 0.0522 / 0.0478 are NOT acceptable fallbacks).
    p_kill_threshold: float = float(receipt["p_straddle_hi"])
    p_reject_threshold: float = float(receipt["p_reject_threshold"])
    kill_switch_threshold: float = float(receipt["kill_switch_threshold"])

    _log(
        "qrb6_runner.constants_loaded",
        master_seed=master_seed,
        K=K,
        sr0_pp=sr0_pp,
        dsr_threshold=dsr_threshold,
        spread_z_threshold=spread_z_threshold,
        p_kill_threshold=p_kill_threshold,
        p_reject_threshold=p_reject_threshold,
        kill_switch_threshold=kill_switch_threshold,
        source="freeze_receipt",
    )

    # --- Fix 2: Load frozen cost manifest (RULE_0 if absent or incomplete) ---
    # In dry-run, manifest loading is skipped; costs are not applied to synthetic data.
    # In live mode, the manifest MUST be present and complete for all 12 registered pairs.
    # After the Mathematician's mechanical cost rule is committed, ZERO pairs should hit
    # the data/cost-gap path — any that do are a LOUD WARNING with a counter in the result.
    _manifest_sha: str = "DRY_RUN_NO_MANIFEST"
    _pair_infos: dict = {}  # populated in live mode
    if not dry_run:
        _mpath = cost_manifest_path if cost_manifest_path is not None else _COST_MANIFEST_PATH
        _pair_infos, _manifest_sha = _load_cost_manifest(_mpath)

        # Live-mode positivity gate: spread_pips must be > 0 for all registered pairs.
        # A zero spread means the Mathematician has not yet filled in the value.
        zero_spread_pairs = [
            sym for sym in _QRB6_REGISTERED_PAIRS
            if _pair_infos[sym].spread_pips <= 0.0
        ]
        if zero_spread_pairs:
            _log(
                "qrb6_runner.cost_manifest_positivity_fail",
                zero_spread_pairs=sorted(zero_spread_pairs),
                action="RULE_0_TECHNICAL_FAILURE",
                note="Mathematician must fill spread_pips > 0 for all 12 pairs before live run",
            )
            print(
                f"RULE_0_TECHNICAL_FAILURE: spread_pips == 0 for pairs: {sorted(zero_spread_pairs)}\n"
                "These are PLACEHOLDER values — the Mathematician has not yet authored the "
                "mechanical cost rule for these pairs.  The runner refuses to proceed.",
                file=sys.stderr,
            )
            sys.exit(1)

        _log(
            "qrb6_runner.cost_manifest_live_gate_passed",
            manifest_sha256=_manifest_sha,
            n_pairs=len(_pair_infos),
            pairs=sorted(_pair_infos.keys()),
        )

    # --- Step 1: Event-set construction (always reads calendar; structure only) ---
    _log("qrb6_runner.event_set_build_start", calendar_path=str(_CALENDAR_PATH))
    try:
        event_set = build_scenario_a_event_set(calendar_path=str(_CALENDAR_PATH))
    except Exception as exc:
        _log(
            "qrb6_runner.technical_failure",
            reason="event_set_build_error",
            error=str(exc),
            action="RULE_0_TECHNICAL_FAILURE",
        )
        raise

    n_total_events = len(event_set)
    post2015_mask = get_post_2015_mask(event_set)
    n_post2015 = int(post2015_mask.sum())

    _log(
        "qrb6_runner.event_set_built",
        n_total_events=n_total_events,
        n_post2015=n_post2015,
        post_2015_cutoff=_EXPECTED_POST_2015_CUTOFF,
        scenario_a_banks=sorted(_SCENARIO_A_BANKS),
    )

    # --- Step 2: Load returns (or stub data in dry-run) ---
    if dry_run:
        _log("qrb6_runner.dry_run_stub_data", n_events=n_total_events)
        # Stub: assign pairs based on each event's bank
        n_max_pairs = 6  # FED/BOJ have 6 pairs
        stub = _make_stub_returns(
            n_events=n_total_events,
            n_pairs=n_max_pairs,
            seed=master_seed,
            include_zero_ret_d=True,
        )
        close_d_stub = stub["close_d"]
        close_dm1_stub = stub["close_dm1"]
        close_dp2_stub = stub["close_dp2"]
        spread_z_stub = stub["spread_z"]
    else:
        _log("qrb6_runner.live_data_load_start")
        # Live mode: load per-pair OHLCV from data/processed/
        # This block is GATED behind --ceo-ack (interlock in main()).
        # Return data is the column `close` of {PAIR}_daily.parquet.
        import pandas as pd

        # Collect all unique pairs in Scenario A
        all_pairs_a: set[str] = set()
        for bank in _SCENARIO_A_BANKS:
            all_pairs_a.update(_BANK_PAIR_MAP[bank])

        pair_close: dict[str, pd.Series] = {}
        for pair in sorted(all_pairs_a):
            parquet_path = _PROCESSED_DATA_DIR / f"{pair}_daily.parquet"
            if not parquet_path.exists():
                _log(
                    "qrb6_runner.technical_failure",
                    reason=f"missing_parquet_{pair}",
                    path=str(parquet_path),
                    action="RULE_0_TECHNICAL_FAILURE",
                )
                raise FileNotFoundError(
                    f"Required parquet not found: {parquet_path}"
                )
            df_pair = pd.read_parquet(parquet_path)
            pair_close[pair] = df_pair["close"]

        # Spreads
        spread_close: dict[str, pd.Series] = {}
        for pair in sorted(all_pairs_a):
            sp_path = _SPREADS_DATA_DIR / f"{pair}_daily_spreads.parquet"
            if sp_path.exists():
                sp_df = pd.read_parquet(sp_path)
                spread_close[pair] = sp_df["spread_pips"]

        _log(
            "qrb6_runner.live_data_loaded",
            pairs=sorted(all_pairs_a),
            spreads_available=sorted(spread_close.keys()),
        )

    # --- Step 3: Assemble y_e series per bank ---
    # Each bank-event → sign_align on reference pair → y_e = sign * mean_net_return
    # Pair returns: net-of-cost close(D) → close(D+2), entered at D+1.
    # Fix 1 (remediation 2026-06-07): EXCLUSION, NOT ZERO-IMPUTATION.
    #   If pair_returns is empty for an event (any reason), the event is EXCLUDED
    #   from the y_e series — NEVER assigned mean_return=0.0.
    #   Two distinct exclusion reasons:
    #     event_excluded_all_pairs_suppressed — all pairs suppressed by spread_z (§5.5);
    #       the event-day still counts as a block-day (§5.5 frozen rule). No counter.
    #     event_excluded_data_or_cost_gap — data missing or cost config absent; this
    #       should NEVER happen after the Mathematician completes the manifest; each
    #       occurrence increments n_event_cost_or_data_gap (surfaced in result YAML).
    # Fix 2 (remediation 2026-06-07): costs loaded from frozen manifest, not DEFAULT_PAIRS.

    y_e_by_bank: dict[str, list[float]] = {bank: [] for bank in _SCENARIO_A_BANKS}
    y_e_by_bank_post2015: dict[str, list[float]] = {bank: [] for bank in _SCENARIO_A_BANKS}
    n_degenerate_total = 0
    n_suppressed_total = 0
    # Fix 1 counter: events excluded due to cost/data gap (should be 0 post-remediation)
    n_event_cost_or_data_gap = 0

    for i, row in event_set.iterrows():
        bank = str(row["bank"])
        event_date = row["date"]
        is_post2015 = bool(post2015_mask.iloc[i])  # type: ignore[call-overload]

        if bank not in _SCENARIO_A_BANKS:
            continue

        pairs_for_bank = _BANK_PAIR_MAP[bank]

        if dry_run:
            # Stub: use row i, cycling through the stub pairs
            # sign from reference pair (first pair, column 0)
            close_d_ref = float(close_d_stub[i, 0])
            close_dm1_ref = float(close_dm1_stub[i, 0])
            sign_align = compute_sign_align(close_d_ref, close_dm1_ref)

            # Equal-weight net-of-cost return across pairs for this bank-event
            pair_returns: list[float] = []
            for j, pair in enumerate(pairs_for_bank):
                col = j % n_max_pairs
                ret_post = float(close_dp2_stub[i, col] - close_d_stub[i, col])
                # Spread suppression check
                sz = float(spread_z_stub[i, col])
                if is_spread_suppressed(sz, spread_z_threshold):
                    n_suppressed_total += 1
                    continue
                pair_returns.append(ret_post)

            # Fix 1: EXCLUDE, not zero-impute.
            if not pair_returns:
                # All pairs suppressed by spread_z (dry-run has no cost gaps).
                # Event excluded; still counts as a block-day (§5.5).
                _log(
                    "qrb6_runner.event_excluded_all_pairs_suppressed",
                    event_date=str(event_date),
                    bank=bank,
                    is_post2015=is_post2015,
                )
                continue  # Do NOT append y_e; do NOT zero-impute.

            mean_return = float(np.mean(pair_returns))

        else:
            # Live mode: look up closes in the parquet data
            import pandas as pd

            # Reference pair for sign alignment (first pair in the bank's list)
            ref_pair = pairs_for_bank[0]
            try:
                close_series = pair_close[ref_pair]
                # Find bar D and D-1 by indexing on event_date
                # SS3.4 frozen convention: tz-align to the (UTC-aware) bar index, and if
                # day D has no bar, the first decision-reflecting bar is the NEXT available
                # daily bar (roll forward; no synthetic bar). RULE-0 remediation 2026-06-07:
                # the original exact-match lookup failed 100% on tz-naive calendar timestamps.
                event_ts = pd.Timestamp(event_date)
                if event_ts.tzinfo is None and close_series.index.tz is not None:
                    event_ts = event_ts.tz_localize(close_series.index.tz)
                idx_pos = close_series.index.searchsorted(event_ts)  # first bar >= D
                if idx_pos >= len(close_series.index):
                    _log(
                        "qrb6_runner.event_skip",
                        reason="no_bar_at_or_after_D",
                        event_date=str(event_date),
                        pair=ref_pair,
                    )
                    continue
                resolved_ts = close_series.index[idx_pos]
                if resolved_ts != event_ts:
                    _log(
                        "qrb6_runner.bar_D_rolled_forward",
                        event_date=str(event_date),
                        resolved_bar=str(resolved_ts),
                        pair=ref_pair,
                    )
                event_ts = resolved_ts
                bar_d_val = float(close_series[event_ts])

                # Bar D-1: last bar before event_ts
                idx_d = close_series.index.get_loc(event_ts)
                if idx_d == 0:
                    continue  # No D-1 bar
                bar_dm1_val = float(close_series.iloc[idx_d - 1])
                sign_align = compute_sign_align(bar_d_val, bar_dm1_val)

                # Bar D+2: two bars after event_ts
                if idx_d + 2 >= len(close_series):
                    continue  # No D+2 bar
            except Exception as exc:
                _log(
                    "qrb6_runner.event_skip",
                    reason="data_error",
                    event_date=str(event_date),
                    error=str(exc),
                )
                continue

            # Per-pair returns (equal-weight)
            # Fix 2 (remediation 2026-06-07): costs loaded from frozen manifest (_pair_infos),
            # NOT from RealisticCostModel() which reads DEFAULT_PAIRS (only 3 pairs).
            # Cost model: ONE round trip per event per pair (enter D+1, exit D+2).
            # Convention mirrors engine's _run_discrete: deduct entry_cost + exit_cost
            # (= round_trip_cost) plus 1-day holding_cost, all in pips, converted to
            # fractional return via (total_cost_pips * pip_value / c_d).  Direction is
            # the live sign_align (already resolved on the reference pair above).
            # Source: engine._run_discrete lines 190-191 (entry cost) and
            # _close_position lines 482-491 (exit + swap cost), engine.py.
            from forex_system.costs.model import RealisticCostModel
            from forex_system.core.types import Direction
            from forex_system.backtest.engine import _get_pip_value

            # Fix 2: use manifest-loaded pair_infos, not DEFAULT_PAIRS.
            # _pair_infos is populated at pipeline start from _load_cost_manifest().
            _cost_model = RealisticCostModel(pair_configs=_pair_infos)
            pair_returns = []
            _pair_cost_gap_this_event = False
            for pair in pairs_for_bank:
                try:
                    # Fix 2: check cost coverage for this pair before proceeding.
                    # After manifest is complete, this should NEVER fire.
                    if pair not in _pair_infos:
                        _log(
                            "qrb6_runner.pair_event_skip",
                            reason="cost_config_gap",
                            event_date=str(event_date),
                            pair=pair,
                            note="SHOULD_NOT_HAPPEN_post_remediation_loud_warning",
                        )
                        import warnings
                        warnings.warn(
                            f"QRB-6 cost gap: pair {pair!r} missing from cost manifest "
                            f"for event {event_date}.  This should be impossible after "
                            "the Mathematician completes the manifest.  Check cost_freeze_qrb6.yaml.",
                            stacklevel=2,
                        )
                        _pair_cost_gap_this_event = True
                        continue

                    cs = pair_close[pair]
                    # FIX-1: tz-alignment — mirror the REFERENCE-pair lookup above.
                    # Calendar dates are tz-naive; price index is tz-aware UTC.
                    # Use searchsorted (first bar >= D) with roll-forward (§3.4 frozen).
                    pair_event_ts = pd.Timestamp(event_date)
                    if pair_event_ts.tzinfo is None and cs.index.tz is not None:
                        pair_event_ts = pair_event_ts.tz_localize(cs.index.tz)
                    idx_d_pair = cs.index.searchsorted(pair_event_ts)
                    if idx_d_pair >= len(cs.index):
                        _log(
                            "qrb6_runner.pair_event_skip",
                            reason="no_bar_at_or_after_D",
                            event_date=str(event_date),
                            pair=pair,
                        )
                        continue
                    # Require at least one prior bar (D-1) and a D+2 bar
                    if idx_d_pair == 0 or idx_d_pair + 2 >= len(cs):
                        _log(
                            "qrb6_runner.pair_event_skip",
                            reason="insufficient_bars",
                            event_date=str(event_date),
                            pair=pair,
                            idx=idx_d_pair,
                            n_bars=len(cs),
                        )
                        continue
                    c_d = float(cs.iloc[idx_d_pair])
                    c_dp2 = float(cs.iloc[idx_d_pair + 2])

                    if c_d <= 0.0:
                        _log(
                            "qrb6_runner.pair_event_skip",
                            reason="non_positive_c_d",
                            event_date=str(event_date),
                            pair=pair,
                        )
                        continue

                    # Spread suppression (FIX-5: align spread index tz to entry_ts)
                    entry_ts = cs.index[idx_d_pair + 1]  # already tz-aware (from cs.index)
                    if pair in spread_close:
                        sp_series = spread_close[pair]
                        # Align spread index tz to entry_ts tz (both must match)
                        sp_entry_ts = entry_ts
                        if sp_series.index.tz is None and entry_ts.tzinfo is not None:
                            sp_entry_ts = entry_ts.tz_localize(None)
                        elif sp_series.index.tz is not None and entry_ts.tzinfo is None:
                            sp_entry_ts = entry_ts.tz_localize(sp_series.index.tz)
                        if sp_entry_ts in sp_series.index:
                            sp_loc = sp_series.index.get_loc(sp_entry_ts)
                            # Trailing median/MAD (60 bars causal)
                            start_sp = max(0, sp_loc - 60)
                            trailing = sp_series.iloc[start_sp:sp_loc].values
                            if len(trailing) >= 2:
                                tr_median = float(np.median(trailing))
                                tr_mad = float(np.median(np.abs(trailing - tr_median)))
                                from forex_system.harness.qrb6_decision import compute_spread_z
                                sp_pips = float(sp_series.iloc[sp_loc])
                                sz = compute_spread_z(sp_pips, tr_median, tr_mad)
                                if is_spread_suppressed(sz, spread_z_threshold):
                                    n_suppressed_total += 1
                                    continue

                    # FIX-2: fractional return (§1.2 "close(D)→close(D+2) return")
                    gross_ret = (c_dp2 / c_d) - 1.0

                    # Fix 2 (net-of-cost using manifest model):
                    # §1.2, §3.2, §5.1 — ONE round trip: entry at D+1, exit at D+2.
                    # Direction: long if sign_align > 0, short otherwise.
                    # Cost = (round_trip_cost_pips + holding_cost_pips_1day) * pip_value / c_d
                    # _cost_model is now wired to _pair_infos (manifest-loaded), not DEFAULT_PAIRS.
                    _pip_val = _get_pip_value(pair)
                    _rt_pips = _cost_model.round_trip_cost(pair, 1.0)
                    _direction = Direction.LONG if sign_align > 0 else Direction.SHORT
                    _hold_pips = _cost_model.holding_cost(pair, _direction, 1.0)
                    _total_cost_pips = _rt_pips + _hold_pips
                    _cost_frac = _total_cost_pips * _pip_val / c_d

                    net_ret = gross_ret - _cost_frac
                    pair_returns.append(net_ret)

                except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError) as exc:
                    # FIX-4: replace bare silent except with narrow exception + event_skip log.
                    # Silent drops are how event studies lie.
                    _log(
                        "qrb6_runner.pair_event_skip",
                        reason="data_error",
                        event_date=str(event_date),
                        pair=pair,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    continue

            # Fix 1 (remediation 2026-06-07): EXCLUDE, not zero-impute.
            # If pair_returns is empty, the event is excluded from y_e — NEVER assigned 0.0.
            # Distinguish WHY the event is empty for audit-trail clarity:
            #   (a) All pairs suppressed by spread_z (§5.5 legitimate) → event_excluded_all_pairs_suppressed
            #   (b) Cost/data gap (should not happen post-remediation) → event_excluded_data_or_cost_gap
            # Both are block-days (§5.5); only (b) increments the n_event_cost_or_data_gap counter.
            if not pair_returns:
                if _pair_cost_gap_this_event:
                    n_event_cost_or_data_gap += 1
                    _log(
                        "qrb6_runner.event_excluded_data_or_cost_gap",
                        event_date=str(event_date),
                        bank=bank,
                        is_post2015=is_post2015,
                        note="SHOULD_NOT_HAPPEN_post_remediation — check cost manifest coverage",
                    )
                    import warnings
                    warnings.warn(
                        f"QRB-6: event {event_date} bank={bank} excluded due to cost/data gap. "
                        "This counter should be ZERO on a fully-remediated run.  "
                        f"n_event_cost_or_data_gap={n_event_cost_or_data_gap}",
                        stacklevel=2,
                    )
                else:
                    # All pairs suppressed by spread_z overlay (§5.5 legitimate).
                    # Event-day still counts as a block-day (§5.5 frozen).
                    _log(
                        "qrb6_runner.event_excluded_all_pairs_suppressed",
                        event_date=str(event_date),
                        bank=bank,
                        is_post2015=is_post2015,
                    )
                continue  # EXCLUDED — do NOT assign mean_return = 0.0

            mean_return = float(np.mean(pair_returns))

        # Assemble y_e (only reached when pair_returns is non-empty in live mode,
        # or when pair_returns is non-empty in dry-run mode)
        y_e_val = compute_y_e(sign_align, mean_return)
        if y_e_val is None:
            n_degenerate_total += 1
            # Degenerate: sign_align == 0 (exact tie §4.4.3).
            # Event-day still counts as a block-day (§4.4.3).
            # Do NOT append to y_e arrays.
            continue

        y_e_by_bank[bank].append(y_e_val)
        if is_post2015:
            y_e_by_bank_post2015[bank].append(y_e_val)

    # Fix 1: assertion that cost-gap counter is zero in live mode (post-remediation invariant).
    # If any events hit the cost/data-gap path in live mode, it means the manifest is
    # incomplete — this is a LOUD failure, not a silent continue.
    if not dry_run and n_event_cost_or_data_gap > 0:
        _log(
            "qrb6_runner.cost_gap_invariant_violated",
            n_event_cost_or_data_gap=n_event_cost_or_data_gap,
            action="WARNING_COST_GAP_POST_REMEDIATION",
            note=(
                "n_event_cost_or_data_gap > 0 means the cost manifest is incomplete. "
                "The Mathematician must fill all 12 pairs with positive spread_pips values. "
                "A non-zero counter in a live run means the result is contaminated."
            ),
        )
        import warnings
        warnings.warn(
            f"QRB-6 LIVE RUN: n_event_cost_or_data_gap={n_event_cost_or_data_gap} > 0. "
            "Cost manifest is incomplete — this run's y_e series may be biased. "
            "DO NOT interpret p-values from this run as confirmatory.",
            stacklevel=2,
        )

    _log(
        "qrb6_runner.y_e_assembled",
        n_degenerate=n_degenerate_total,
        n_suppressed=n_suppressed_total,
        n_event_cost_or_data_gap=n_event_cost_or_data_gap,
        bank_counts={b: len(v) for b, v in y_e_by_bank.items()},
        post2015_bank_counts={b: len(v) for b, v in y_e_by_bank_post2015.items()},
    )

    # Convert to numpy arrays (filtering empty banks)
    y_e_np = {b: np.array(v, dtype=float) for b, v in y_e_by_bank.items() if v}
    y_e_post2015_np = {b: np.array(v, dtype=float) for b, v in y_e_by_bank_post2015.items() if v}

    if not y_e_np:
        _log(
            "qrb6_runner.technical_failure",
            reason="empty_y_e_series",
            action="RULE_0_TECHNICAL_FAILURE",
        )
        raise RuntimeError("RULE_0_TECHNICAL_FAILURE: no valid y_e observations assembled.")

    # --- Step 4: Bootstrap — full window ---
    _log("qrb6_runner.bootstrap_full_start", K=K, master_seed=master_seed)
    boot_full = run_bank_blocked_bootstrap(y_e_np, master_seed=master_seed, K=K)
    p_agg = boot_full.pvalue
    _log(
        "qrb6_runner.bootstrap_full_result",
        p_agg=p_agg,
        t_obs=boot_full.t_obs,
        n_included=boot_full.n_included,
        block_lengths=boot_full.block_lengths_per_bank,
        source="run_bank_blocked_bootstrap_full",
    )

    # --- Step 5: Bootstrap — post-2015 sub-window ---
    _log("qrb6_runner.bootstrap_post2015_start", K=K, master_seed=master_seed)
    if y_e_post2015_np:
        # Use master_seed + 1 for the post-2015 resample to avoid seed correlation
        boot_post2015 = run_bank_blocked_bootstrap(
            y_e_post2015_np, master_seed=master_seed + 1, K=K
        )
        p_post2015 = boot_post2015.pvalue
    else:
        p_post2015 = 1.0  # No post-2015 data → fail
        boot_post2015 = None
    _log(
        "qrb6_runner.bootstrap_post2015_result",
        p_post2015=p_post2015,
        n_post2015_included=(boot_post2015.n_included if boot_post2015 else 0),
        source="run_bank_blocked_bootstrap_post2015",
    )

    # --- Step 6: DSR gate ---
    y_all = np.concatenate(list(y_e_np.values()))
    sr_ann = compute_event_sharpe_ann(y_all)
    skew_val = float(sp_stats.skew(y_all, bias=True))
    ek_val = float(sp_stats.kurtosis(y_all, fisher=True, bias=True))

    dsr = compute_dsr_qrb6(
        sr_ann=sr_ann,
        skew=skew_val,
        excess_kurtosis=ek_val,
        T=len(y_all),
        sr0_pp=sr0_pp,
        dsr_threshold=dsr_threshold,
    )
    dsr_cleared = dsr >= dsr_threshold
    _log(
        "qrb6_runner.dsr_result",
        sr_ann=sr_ann,
        skew=skew_val,
        excess_kurtosis=ek_val,
        dsr=dsr,
        dsr_cleared=dsr_cleared,
        sr0_pp=sr0_pp,
        kill_switch_threshold=kill_switch_threshold,
        source="compute_dsr_qrb6",
    )

    # --- Step 7: Per-bank secondary Sharpe (advisory; §5.4) ---
    per_bank_sharpe: dict[str, float] = {}
    for bank in sorted(y_e_np.keys()):
        per_bank_sharpe[bank] = compute_event_sharpe_ann(y_e_np[bank])
    _log(
        "qrb6_runner.per_bank_sharpe",
        per_bank_sharpe=per_bank_sharpe,
        advisory_only=True,
        source="compute_event_sharpe_ann_per_bank",
    )

    # --- Step 8: Decision functional (§4.2 RULES 0-4) ---
    _log(
        "qrb6_runner.decision_start",
        p_post2015=p_post2015,
        p_agg=p_agg,
        dsr=dsr,
        p_kill_threshold=p_kill_threshold,
        p_reject_threshold=p_reject_threshold,
        dsr_threshold=dsr_threshold,
        rule_order="RULE0_techfail->RULE1_post2015->RULE2_agg->RULE3_pass->RULE4_ambiguous",
    )
    decision = evaluate_decision(
        p_post2015=p_post2015,
        p_agg=p_agg,
        dsr=dsr,
        technical_failure=False,
        p_kill_threshold=p_kill_threshold,
        p_reject_threshold=p_reject_threshold,
        dsr_threshold=dsr_threshold,
    )
    _log(
        "qrb6_runner.decision_result",
        decision=decision,
        p_post2015=p_post2015,
        p_agg=p_agg,
        dsr=dsr,
        dsr_cleared=dsr_cleared,
        source="evaluate_decision",
    )

    # --- Step 9: Reversal distinguishability (secondary; §5.3) ---
    # Reversal fraction: fraction of events where sign_align continued into post-window
    # (y_e > 0 means continuation). Distinguishability vs 0% and 100% is the test.
    # Simplified: sign-test proportion of y_e > 0
    n_y = len(y_all)
    n_positive = int(np.sum(y_all > 0))
    reversal_fraction = float(n_positive / n_y) if n_y > 0 else float("nan")
    _log(
        "qrb6_runner.reversal_fraction",
        reversal_fraction=reversal_fraction,
        n_positive=n_positive,
        n_y=n_y,
        note="secondary_diagnostic_no_kill_trigger",
    )

    # --- Assemble result payload ---
    run_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result: dict = {
        "run_utc": run_utc,
        "trial_id": "fa0f982a",
        "dry_run": dry_run,
        "decision": decision,
        # Primary statistics
        "pooled_block_bootstrap_pvalue": p_agg,
        "post_2015_block_bootstrap_pvalue": p_post2015,
        "dsr": dsr,
        "dsr_cleared": dsr_cleared,
        "kill_switch_threshold": kill_switch_threshold,
        "sr_ann_pooled": sr_ann,
        "skew_pooled": skew_val,
        "excess_kurtosis_pooled": ek_val,
        # Event-set metadata
        "scenario_a_event_days": n_total_events,
        "post_2015_event_days": n_post2015,
        "n_included_full": boot_full.n_included,
        "n_included_post2015": (boot_post2015.n_included if boot_post2015 else 0),
        "n_degenerate": n_degenerate_total,
        "n_suppressed": n_suppressed_total,
        # Fix 1 — cost/data gap counter (must be 0 in a clean live run post-remediation)
        "n_event_cost_or_data_gap": n_event_cost_or_data_gap,
        "cost_gap_invariant": (
            "n_event_cost_or_data_gap MUST be 0 in a post-remediation live run. "
            "Any non-zero value means the cost manifest is incomplete and results are contaminated."
        ),
        # Fix 2 — manifest provenance for audit
        "cost_manifest_path": str(
            cost_manifest_path if cost_manifest_path is not None else _COST_MANIFEST_PATH
        ),
        "cost_manifest_sha256": _manifest_sha,
        # Bootstrap metadata
        "block_construction_rule": "bank_level_blocks_stationary_circular",
        "block_length_method": "politis_white_per_bank_group",
        "bootstrap_resamples_B": boot_full.K,
        "master_seed": boot_full.master_seed,
        "block_lengths_per_bank": boot_full.block_lengths_per_bank,
        # Secondary metrics
        "per_bank_sharpe": per_bank_sharpe,
        "reversal_fraction": reversal_fraction,
        # DSR inputs
        "sr0_pp_sel": sr0_pp,
        "sr0_note": (
            "QRB-6-ONLY SR0_pp_sel=0.026861 (N_sel=3, disp=0.50). "
            "NOT the R5-only SR0_pp. NOT the confirmatory-only SR0_pp. "
            "Derived fresh by the Mathematician in this track (§2.5)."
        ),
        # Provenance
        "boc_gap_disclosed": (
            "BOC contributes zero events pre-2019 (2010-2018 FAD dates not acquired "
            "from official sources; anti-fabrication rule applied). BOC is entirely "
            "absent from the pre-2015 sub-window. This is a disclosed confound for "
            "the structural-break test (§3.4b)."
        ),
        "code_commit": receipt.get("code_commit", "UNCOMMITTED"),
        "prereg_sha256": receipt.get("prereg_sha256", "N/A"),
        "spec_ref": "references/pre-registrations/qrb6_cb_event_study.md §4.2",
    }

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrate the QRB-6 one-shot runner.

    Default (no flags): dry-run mode (synthetic stubs, no data/processed read).
    --ceo-ack: live run (requires freeze-receipt + --ceo-ack).
    --dry-run: explicit dry-run (same as default).
    """
    parser = argparse.ArgumentParser(
        description=(
            "QRB-6 CB-event-study one-shot runner (trial fa0f982a).  "
            "Default: --dry-run mode (synthetic stubs, no receipt required).  "
            "Live run requires --ceo-ack AND a valid freeze-receipt."
        )
    )
    parser.add_argument(
        "--ceo-ack",
        action="store_true",
        dest="ceo_ack",
        help=(
            "CEO acknowledgment flag for live execution.  Requires a valid "
            "freeze-receipt at the canonical path.  Without this flag, "
            "the runner operates in --dry-run mode."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Dry-run mode (default): exercises the full pipeline against synthetic "
            "stub data WITHOUT touching data/processed/ or requiring a receipt."
        ),
    )
    args = parser.parse_args()

    # Determine mode: live requires --ceo-ack; otherwise dry-run
    live_run = args.ceo_ack and not args.dry_run
    dry_run = not live_run

    if dry_run and not args.ceo_ack:
        _log(
            "qrb6_runner.mode",
            mode="dry_run",
            reason="no_ceo_ack_flag_or_explicit_dry_run",
        )
        print(
            "QRB-6 RUNNER — dry-run mode (no --ceo-ack; synthetic stubs only).\n"
            "No data/processed/ reads.  No freeze-receipt required for dry-run.\n"
            "Pass --ceo-ack for the live one-shot run (requires freeze-receipt)."
        )

    if live_run:
        # Live run: hard interlock — requires freeze-receipt AND --ceo-ack
        _log(
            "qrb6_runner.mode",
            mode="live",
            receipt_path=str(_RECEIPT_PATH),
        )
        receipt = _validate_receipt(_RECEIPT_PATH)

        # Interlock: constants must match embedded guards
        from forex_system.harness.qrb6_decision import check_receipt_constants
        check_receipt_constants(receipt)

        _log(
            "qrb6_runner.gate_passed",
            code_commit=receipt.get("code_commit", "UNKNOWN"),
            frozen_at_utc=receipt.get("frozen_at_utc", "UNKNOWN"),
        )
    else:
        # Dry-run: print refusal message and use stub receipt
        if args.ceo_ack and args.dry_run:
            # --ceo-ack + --dry-run: print note and proceed with dry-run
            print(
                "NOTE: --ceo-ack ignored in --dry-run mode.  "
                "Proceeding with synthetic stub data."
            )
        # Stub receipt for dry-run (provides structure but no live SHA check)
        receipt = {
            "master_seed": 387992,
            "K": 10000,
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.0422,        # OBF extra-look penalty (former void-run value: 0.0522)
            "p_reject_threshold": 0.0378,   # OBF extra-look penalty (former void-run value: 0.0478)
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": 506,
            "post_2015_a": 345,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "UNCOMMITTED",
            "frozen_at_utc": "DRY_RUN",
        }

    # --- Import harness modules (deferred so --help works without scipy) ---
    try:
        import scipy.stats  # noqa: F401 — ensure scipy available
        from forex_system.harness import qrb6_decision as _qrb6_dec  # noqa: F401
        from forex_system.harness.reality_check import (  # noqa: F401
            politis_white_block_length,
        )
    except ImportError as exc:
        _log(
            "qrb6_runner.technical_failure",
            reason="import_error",
            error=str(exc),
            action="EXIT_1",
        )
        print(f"TECHNICAL FAILURE: import error: {exc}", file=sys.stderr)
        sys.exit(1)

    run_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _log("qrb6_runner.run_start", run_utc=run_utc, dry_run=dry_run)

    # --- Execute pipeline ---
    try:
        result = _run_pipeline(receipt=receipt, dry_run=dry_run)
    except SystemExit:
        raise
    except Exception as exc:
        _log(
            "qrb6_runner.technical_failure",
            reason="pipeline_error",
            error=str(exc),
            action="RULE_0_TECHNICAL_FAILURE",
        )
        print(f"TECHNICAL FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Write result YAML (dry-run NEVER writes to the canonical path) ---
    result_path = _DRY_RUN_RESULT_PATH if dry_run else _RESULT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as fh:
        yaml.dump(result, fh, default_flow_style=False, sort_keys=False)

    _log(
        "qrb6_runner.result_written",
        result_path=str(result_path),
        decision=result["decision"],
        dry_run=dry_run,
    )

    mode_label = "DRY-RUN" if dry_run else "LIVE"
    print(f"\nQRB-6 {mode_label} COMPLETE.  Decision: {result['decision']}")
    print(f"Result artifact: {result_path}")
    if dry_run:
        print(
            "NOTE: dry-run result uses synthetic stub data.  "
            "Decision is NOT a valid pre-reg outcome."
        )


if __name__ == "__main__":
    main()
