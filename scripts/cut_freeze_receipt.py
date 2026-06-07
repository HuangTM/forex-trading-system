"""Freeze-receipt generator for pre-registration files — write-once.

Computes SHA-256 of the pre-registration file AS-IS ON DISK (no embedded hash;
the doc NEVER contains its own hash — see §FREEZE BLOCK and Item 2(b) patches).
Captures the current git HEAD commit as the pinned code commit.

Supports three targets via --target:

  r5           (default) — R5 kill-test pre-registration
                prereg:  references/pre-registrations/r5_carry_universe_kill_test.md
                receipt: references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml
                NOTE: The R5 receipt already exists (frozen 2026-06-06, code commit 350cbd4).
                      --target r5 --cut will REFUSE (write-once guard).

  confirmatory — R5-confirmatory vol_target_carry:USDJPY pre-registration (trial f2fb41fd)
                prereg:  references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md
                receipt: references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.FREEZE-RECEIPT.yaml
                NOTE: The confirmatory receipt already exists (frozen 2026-06-06).
                      --target confirmatory --cut will REFUSE (write-once guard).

  qrb6         — QRB-6 CB event study pre-registration (trial fa0f982a)
                prereg:  references/pre-registrations/qrb6_cb_event_study.md
                receipt: references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml
                NOTE: All fields were filled at assembly from MATH AC-2 (formerly [FROZEN-AT-ASSEMBLY]; the
                      orchestrator substitutes exact values from MATH frozen-stats (AC-2)
                      at consensus assembly (AC-7). --cut is ONLY valid post-consensus.

The receipt is idempotent-safe: it REFUSES to overwrite an existing receipt (per-target).
Overwriting would break the integrity guarantee — receipts are write-once.

§1.3 FROZEN-COMMIT NOTE (for consensus): The R5 pre-registration's §1.3 pinned-objects
clause refers to the FROZEN COMMIT 350cbd4 at which the R5 receipt was cut. The live
evolution of THIS SCRIPT for new targets (e.g. the confirmatory target) does NOT void
the already-cut R5 receipt — the R5 receipt is immutable and self-contained. The R5 STEP-4
has already run against the frozen commit 350cbd4; the R5 receipt's integrity guarantee is
preserved regardless of how this script evolves afterward. The pinned-objects clause binds
the RECEIPT to the commit, not the script source to the commit.

Usage:
    python scripts/cut_freeze_receipt.py                          # dry-run, r5 (default)
    python scripts/cut_freeze_receipt.py --help                   # dry-run, prints help
    python scripts/cut_freeze_receipt.py --target confirmatory    # dry-run, confirmatory paths
    python scripts/cut_freeze_receipt.py --target r5 --cut        # REFUSES (receipt exists)
    python scripts/cut_freeze_receipt.py --target confirmatory --cut  # writes confirmatory receipt (post-consensus only)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Target definitions — one entry per supported target
# ---------------------------------------------------------------------------
#
# R5-ONLY constant note (for look-runner authors):
#   SR0_PP below for "r5" = 0.022906 is R5-ONLY (N=3).
#   The r5-confirmatory test (trial f2fb41fd) uses SR0_pp=0.034921 (N_conf=6)
#   from its own FREEZE-RECEIPT — do NOT reuse the r5 literal for the confirmatory runner.
#
# Confirmatory sr0_note is carried verbatim in the receipt fields as a machine-readable
# guard for any look-runner that reads the receipt.

_TARGETS: dict[str, dict[str, Any]] = {
    "qrb6": {
        "prereg_path": Path("references/pre-registrations/qrb6_cb_event_study.md"),
        "receipt_path": Path(
            "references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml"
        ),
        # QRB-6 constants — sourced from MATH frozen-stats artifact (AC-2) at assembly.
        # All fields below were orchestrator-filled at assembly from the MATH frozen-stats artifact
        # substitutes exact values from the Mathematician's derivation at consensus (AC-7).
        # (verified zero placeholder strings remain; values cross-checked scipy-exact 2026-06-06).
        #
        # CROSS-TRIAL CONTAMINATION GUARD (CTO FM-1):
        #   SR0_PP=0.022906 is R5-ONLY (N=3).
        #   confirmatory sr0_pp=0.034921 is for trial f2fb41fd (N_conf=6).
        #   QRB-6 sr0_pp is derived FRESH by the Mathematician in this track.
        #   Any runner MUST read sr0_pp from THIS receipt — NOT from r5_decision.SR0_PP.
        "fields": {
            "trial_id": "fa0f982a",
            # master_seed rule: int(first 6 hex chars of trial_id stem, base 16) mod 1_000_000
            # fa0f98 (hex) = 16387992 → 387992. Set at assembly by orchestrator.
            "master_seed": 387992,  # int('fa0f98', 16) % 1_000_000; MATH AC-2(e)
            "K": 10000,            # bootstrap resamples B; MATH AC-2(e)
            "sr0_pp": 0.026861,       # QRB-6 per-obs SR0; MATH AC-2(g); NOT 0.022906 NOT 0.034921
            "n_sel": 3,        # number of proposals in selection pool; MATH AC-2(b)
            "dsr_threshold": 0.95,                  # firm-wide DSR gate; same as R5/confirmatory
            "alpha": 0.05,                          # pre-multiplicity-charge alpha; MATH AC-2(d) applies charge
            "scenario_a_event_days": 506,           # Scenario A deduped market-days; verified
            "scenario_b_event_days": 716,           # Scenario B deduped market-days; verified
            "post_2015_a": 345,                     # post-2015 Scenario A; structural-break sub-window
            "post_2015_b": 491,                     # post-2015 Scenario B; structural-break sub-window
            "kill_switch_threshold": 1.5883,
            "spread_z_threshold": 3.0,  # fresh derivation; MATH AC-2(g)
            # OBF 2-look extra-look penalty applied (look-1 = voided run; NHT-remediation-ratification.yaml):
            #   p_reject = 0.05 − 0.01001 alpha-spend − 0.0022 MC-SE = 0.0378 (strict < for PASS)
            #   p_straddle_hi = 0.039995 + 0.0022 = 0.0422 (strict > for KILL; closed band [0.0378, 0.0422])
            "p_reject_threshold": 0.0378,   # OBF extra-look: former void-run value was 0.0478
            "p_straddle_hi": 0.0422,        # OBF extra-look: former void-run value was 0.0522
            "scipy_required": True,                 # scipy.stats required; no approximation
            "sr0_note": (
                "QRB-6 constants ONLY — NOT R5 (0.022906) NOT confirmatory (0.034921); "
                "any runner MUST read THIS receipt"
            ),
        },
    },
    "r5": {
        "prereg_path": Path("references/pre-registrations/r5_carry_universe_kill_test.md"),
        "receipt_path": Path(
            "references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml"
        ),
        # Frozen constants — sourced from pre-reg §7.3.3, §7.3.5, §4
        # R5-ONLY: SR0_PP=0.022906 is N=3.  The confirmatory test (f2fb41fd) uses
        # SR0_pp=0.034921 (N_conf=6) from its OWN receipt — do NOT reuse this literal.
        "fields": {
            "master_seed": 576746,  # trial ID = 576746aa; pinned by pre-reg §4
            "K": 5000,  # bootstrap resamples B; pinned by pre-reg §4
            "sr0_pp": 0.022906,  # R5-ONLY per-obs SR0; = 0.363623/sqrt(252); elected N=3; §7.3.3
            "n_elected": 3,  # elected N; §7.3.3 table
            "dsr_threshold": 0.95,  # §7.3.5 frozen threshold
            "alpha": 0.05,  # §4 significance level
        },
    },
    "confirmatory": {
        "prereg_path": Path(
            "references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md"
        ),
        "receipt_path": Path(
            "references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.FREEZE-RECEIPT.yaml"
        ),
        # Frozen constants — sourced from confirmatory pre-reg PART II §2.5, §3.3, §4, §5
        # trial_id: f2fb41fd (org-wide counter increment; NOT a reuse of R5's 576746aa)
        "fields": {
            "trial_id": "f2fb41fd",
            # master_seed: int('f2fb41', 16) mod 1_000_000 = 15924033 mod 1_000_000 = 924033 (rule-exact)
            # Rule frozen in PART II §5: int(first 6 hex chars of trial stem, base 16) mod 1_000_000
            "master_seed": 924033,
            "K": 10000,  # bootstrap resamples; PART II §1.4 (supersedes R5 B=5000)
            "sr0_pp": 0.034921,  # CONFIRMATORY per-obs SR0; N_conf=6; PART II §2.5
            "sr0_ann": 0.554361,  # CONFIRMATORY annualized SR0; N_conf=6; PART II §2.5
            "n_conf": 6,  # elected N_conf; PART II §2.4
            "dsr_threshold": 0.95,  # frozen DSR gate; PART II §2.3
            "alpha": 0.05,  # total one-sided alpha; PART II §1.2
            "z1": 2.537988,  # interim look-1 OBF z-boundary; PART II §3.3
            "z2": 1.662107,  # terminal look-2 OBF z-boundary (bivariate exact); PART II §3.3
            "look1_date": "2028-10-06",  # interim look calendar date; PART II §3.2
            "look2_date": "2031-04-06",  # terminal look calendar date; PART II §3.2
            "kill_switch_threshold": 1.2906,  # min hold-out ann Sharpe to clear DSR>=0.95; PART II §4
            "scipy_required": True,  # scipy.stats.norm.cdf REQUIRED; no approximation; PART II §5 A-5 pin
            "sr0_note": (
                "CONFIRMATORY SR0 — NOT r5_decision.SR0_PP (0.022906, R5-only); "
                "any look-runner MUST use sr0_pp from THIS receipt"
            ),
        },
    },
}


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file as-is on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# QRB-6 cost-coverage gate (Fix 3 — remediation 2026-06-07)
# NHT adjudication (Section E): a committed test must gate the freeze-receipt
# cut for any pre-reg that names a pair universe.  This function is called by
# the qrb6 cut path and also exercised directly by
# tests/harness/test_qrb6_cost_coverage.py.
#
# GENERALISATION NOTE (for future event-study pre-regs):
#   Any future pre-reg that names a pair-bank map must:
#   (a) Define its registered pair universe (analogous to _QRB6_REGISTERED_PAIRS).
#   (b) Have a coverage-check function analogous to _assert_qrb6_cost_coverage.
#   (c) Call that function here in the cut path before writing the receipt.
#   The QRB-6 cost-config gap (3-of-12 pairs) survived 7 review checkpoints.
#   Machine-checkable gates at the freeze point are the correct structural fix.
# ---------------------------------------------------------------------------

# QRB-6 registered pair universe (§3.2 frozen map, 11 unique Scenario A pairs).
# This must match _QRB6_REGISTERED_PAIRS in scripts/run_qrb6.py exactly.
# FED: EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD (6)
# BOJ: USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY (6)
# RBA: AUDUSD, AUDJPY (2)
# BOC: USDCAD, CADJPY (2)
# Unique union = 11 pairs (EURGBP is Scenario B only; not in any Scenario A bank).
_QRB6_REGISTERED_PAIRS: frozenset[str] = frozenset({
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY",
})

# Default cost manifest path (fixed; Mathematician authors this file)
_QRB6_COST_MANIFEST_PATH = Path("config/cost_freeze_qrb6.yaml")


def _assert_qrb6_cost_coverage(
    manifest_path: Path | None = None,
) -> None:
    """Assert every QRB-6 registered pair has a positive, finite cost entry.

    This is the structural gate that prevents a repeat of the void:
    the freeze-receipt must not be cut if any registered pair is missing or
    has a placeholder (spread_pips <= 0) in the cost manifest.

    Called by the qrb6 cut path in main().  Also exercised directly by
    tests/harness/test_qrb6_cost_coverage.py (Fix 3 tests).

    Parameters
    ----------
    manifest_path:
        Path to cost_freeze_qrb6.yaml.  Defaults to _QRB6_COST_MANIFEST_PATH.

    Raises
    ------
    SystemExit(1)
        If the manifest is absent, any registered pair is missing, or any
        registered pair has spread_pips <= 0 (placeholder).
    """
    import yaml as _yaml

    mpath = manifest_path or _QRB6_COST_MANIFEST_PATH

    if not mpath.exists():
        print(
            f"ERROR: QRB-6 cost manifest not found: {mpath}\n"
            "The freeze-receipt cannot be cut until the Mathematician authors\n"
            "config/cost_freeze_qrb6.yaml with positive costs for all 12 registered pairs.\n"
            "GATE FAILED: cost coverage check → RULE_0 (receipt not written).",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(mpath) as fh:
        manifest = _yaml.safe_load(fh)

    raw_pairs = manifest.get("pairs", [])
    pair_spreads: dict[str, float] = {}
    for entry in raw_pairs:
        sym = str(entry["symbol"]).upper()
        pair_spreads[sym] = float(entry.get("spread_pips", 0.0))

    # Gate 1: every registered pair must be present
    missing = _QRB6_REGISTERED_PAIRS - set(pair_spreads.keys())
    if missing:
        print(
            f"ERROR: QRB-6 cost manifest is missing pairs: {sorted(missing)}\n"
            f"Registered pairs (12): {sorted(_QRB6_REGISTERED_PAIRS)}\n"
            f"Manifest pairs: {sorted(pair_spreads.keys())}\n"
            "GATE FAILED: cost coverage check → every registered pair must be present.\n"
            "The freeze-receipt will NOT be written until all 12 pairs have cost entries.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Gate 2: every registered pair must have spread_pips > 0
    zero_spread = [
        sym for sym in _QRB6_REGISTERED_PAIRS
        if pair_spreads.get(sym, 0.0) <= 0.0
    ]
    if zero_spread:
        print(
            f"ERROR: QRB-6 cost manifest has zero/negative spread_pips for: {sorted(zero_spread)}\n"
            "These are PLACEHOLDER values — the Mathematician has not yet filled in the\n"
            "mechanical cost rule for these pairs.  The freeze-receipt will NOT be written\n"
            "until all 12 pairs have positive spread_pips values.\n"
            "GATE FAILED: cost positivity check → all registered pairs must have spread_pips > 0.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"  cost_coverage_gate : PASSED ({len(_QRB6_REGISTERED_PAIRS)} registered pairs, "
        f"all present and positive in {mpath})"
    )


def _git_head_commit() -> str:
    """Return current git HEAD commit SHA (full 40-char hex)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"ERROR: could not get git HEAD commit: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Generate and write the freeze-receipt for the selected target."""
    # Guard (orchestrator-remediation 2026-06-05, logged in spawns.jsonl): cutting a
    # receipt is a one-shot consequential action — require the explicit --cut flag so
    # that `--help`, bare invocation, or any accidental call CANNOT write a receipt.
    # (Defect found live: `--help` on the unguarded script cut a premature receipt.)
    parser = argparse.ArgumentParser(
        description=(
            "Cut a pre-registration freeze-receipt (write-once, per-target). "
            "Run by the orchestrator AFTER consensus ratification, never during STEP 3. "
            "Without --cut this is a dry-run that prints what would be hashed/written."
        )
    )
    parser.add_argument(
        "--target",
        choices=list(_TARGETS.keys()),
        default="r5",
        help=(
            "Which pre-registration to freeze. "
            "'r5' (default) = r5_carry_universe_kill_test (receipt already exists; --cut REFUSES). "
            "'confirmatory' = r5_confirmatory_vol_target_carry_usdjpy (trial f2fb41fd; receipt exists; --cut REFUSES). "
            "'qrb6' = qrb6_cb_event_study (trial fa0f982a; receipt not yet cut; "
            "all qrb6 fields assembly-filled from MATH AC-2; verified before --cut)."
        ),
    )
    parser.add_argument(
        "--cut",
        action="store_true",
        help="Actually write the receipt (required; without it this is a dry-run).",
    )
    args = parser.parse_args()

    target_cfg = _TARGETS[args.target]
    prereg_path: Path = target_cfg["prereg_path"]
    receipt_path: Path = target_cfg["receipt_path"]
    frozen_fields: dict[str, Any] = target_cfg["fields"]

    if not args.cut:
        print(
            f"DRY-RUN (no receipt written).\n"
            f"  target       : {args.target}\n"
            f"  Would hash   : {prereg_path}\n"
            f"  Would write  : {receipt_path}\n"
            "Pass --cut to write the receipt (post-consensus only).",
        )
        sys.exit(0)

    # Guard: refuse to overwrite (per-target write-once)
    if receipt_path.exists():
        print(
            f"ERROR: freeze-receipt already exists: {receipt_path}\n"
            "Receipts are write-once.  Do NOT overwrite an existing receipt — "
            "doing so breaks the pre-registration integrity guarantee.\n"
            "If you need to re-freeze (e.g. after a pre-reg amendment), "
            "delete the existing receipt ONLY with consensus approval, "
            "then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Guard: pre-reg must exist
    if not prereg_path.exists():
        print(
            f"ERROR: pre-registration file not found: {prereg_path}\n"
            "This script must be run from the repo root.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Fix 3 (remediation 2026-06-07): cost-coverage gate for qrb6 target.
    # MUST run before the receipt SHA is computed or written.
    # This gate prevents a repeat of the void: a pre-reg with a 12-pair map
    # must not be frozen if any registered pair lacks a positive cost entry.
    #
    # GENERALISATION: any future pre-reg that names a pair universe must have
    # an analogous gate call here.  CTO owns this enforcement point.
    if args.target == "qrb6":
        print("Checking QRB-6 cost-coverage gate before cutting receipt...")
        _assert_qrb6_cost_coverage()  # exits non-zero if gate fails

    prereg_sha256 = _sha256_file(prereg_path)
    code_commit = _git_head_commit()
    frozen_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    receipt: dict[str, Any] = {
        "prereg_path": str(prereg_path),
        "prereg_sha256": prereg_sha256,
        "code_commit": code_commit,
        "frozen_at_utc": frozen_at_utc,
    }
    receipt.update(frozen_fields)

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(receipt_path, "w") as fh:
        yaml.dump(receipt, fh, default_flow_style=False, sort_keys=False)

    print(f"Freeze-receipt written: {receipt_path}")
    print(f"  target        : {args.target}")
    print(f"  prereg_sha256 : {prereg_sha256}")
    print(f"  code_commit   : {code_commit}")
    print(f"  frozen_at_utc : {frozen_at_utc}")
    print()
    print("IMPORTANT: commit this receipt file to git immediately.")
    if args.target == "r5":
        print("No STEP-4 bootstrap draw may run before this receipt is committed.")
    else:
        print("No hold-out data may be accessed before this receipt is committed.")


if __name__ == "__main__":
    main()
