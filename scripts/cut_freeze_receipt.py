"""Freeze-receipt generator for pre-registration files — write-once.

Computes SHA-256 of the pre-registration file AS-IS ON DISK (no embedded hash;
the doc NEVER contains its own hash — see §FREEZE BLOCK and Item 2(b) patches).
Captures the current git HEAD commit as the pinned code commit.

Supports two targets via --target:

  r5           (default) — R5 kill-test pre-registration
                prereg:  references/pre-registrations/r5_carry_universe_kill_test.md
                receipt: references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml
                NOTE: The R5 receipt already exists (frozen 2026-06-06, code commit 350cbd4).
                      --target r5 --cut will REFUSE (write-once guard).

  confirmatory — R5-confirmatory vol_target_carry:USDJPY pre-registration (trial f2fb41fd)
                prereg:  references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md
                receipt: references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.FREEZE-RECEIPT.yaml

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
            "'confirmatory' = r5_confirmatory_vol_target_carry_usdjpy (trial f2fb41fd)."
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
