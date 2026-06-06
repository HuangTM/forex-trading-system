"""Freeze-receipt generator for R5 pre-registration — Item 2(a).

Computes SHA-256 of the pre-registration file AS-IS ON DISK (no embedded hash;
the doc NEVER contains its own hash — see §FREEZE BLOCK and Item 2(b) patches).
Captures the current git HEAD commit as the pinned code commit.

Writes:
    references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml

The receipt is idempotent-safe: it REFUSES to overwrite an existing receipt.
Overwriting would break the integrity guarantee — receipts are write-once.

This script is run by the orchestrator AFTER consensus ratification and CEO
sign-off, NEVER by the Quant Developer during implementation (STEP 3).

Usage:
    python scripts/cut_freeze_receipt.py          # dry-run (prints, writes nothing)
    python scripts/cut_freeze_receipt.py --cut    # writes the receipt (post-consensus only)
"""

from __future__ import annotations

import argparse

import datetime
import hashlib
import subprocess
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Frozen receipt fields (sourced from pre-reg §7.3.3, §7.3.5, §4)
# ---------------------------------------------------------------------------

_PREREG_PATH = Path(
    "references/pre-registrations/r5_carry_universe_kill_test.md"
)
_RECEIPT_PATH = Path(
    "references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml"
)

# Frozen constants — do NOT change without a new pre-registration
_MASTER_SEED = 576746       # trial ID = 576746aa; pinned by pre-reg §4
_K = 5000                   # bootstrap resamples B; pinned by pre-reg §4
_SR0_PP = 0.022906          # per-obs SR0; = 0.363623/sqrt(252); elected N=3; §7.3.3
_N_ELECTED = 3              # elected N; §7.3.3 table
_DSR_THRESHOLD = 0.95       # §7.3.5 frozen threshold
_ALPHA = 0.05               # §4 significance level


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
    """Generate and write the freeze-receipt."""
    # Guard (orchestrator-remediation 2026-06-05, logged in spawns.jsonl): cutting a
    # receipt is a one-shot consequential action — require the explicit --cut flag so
    # that `--help`, bare invocation, or any accidental call CANNOT write a receipt.
    # (Defect found live: `--help` on the unguarded script cut a premature receipt.)
    parser = argparse.ArgumentParser(
        description=(
            "Cut the R5 pre-registration freeze-receipt (write-once). "
            "Run by the orchestrator AFTER consensus ratification, never during STEP 3."
        )
    )
    parser.add_argument(
        "--cut",
        action="store_true",
        help="actually write the receipt (required; without it this is a dry-run that prints what would be hashed)",
    )
    args = parser.parse_args()
    if not args.cut:
        print(
            f"DRY-RUN (no receipt written). Would hash: {_PREREG_PATH}\n"
            f"Would write: {_RECEIPT_PATH}\n"
            "Pass --cut to write the receipt (post-consensus only).",
        )
        sys.exit(0)

    # Guard: refuse to overwrite
    if _RECEIPT_PATH.exists():
        print(
            f"ERROR: freeze-receipt already exists: {_RECEIPT_PATH}\n"
            "Receipts are write-once.  Do NOT overwrite an existing receipt — "
            "doing so breaks the pre-registration integrity guarantee.\n"
            "If you need to re-freeze (e.g. after a pre-reg amendment), "
            "delete the existing receipt ONLY with consensus approval, "
            "then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Guard: pre-reg must exist
    if not _PREREG_PATH.exists():
        print(
            f"ERROR: pre-registration file not found: {_PREREG_PATH}\n"
            "This script must be run from the repo root.",
            file=sys.stderr,
        )
        sys.exit(1)

    prereg_sha256 = _sha256_file(_PREREG_PATH)
    code_commit = _git_head_commit()
    frozen_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    receipt: dict = {
        "prereg_path": str(_PREREG_PATH),
        "prereg_sha256": prereg_sha256,
        "code_commit": code_commit,
        "frozen_at_utc": frozen_at_utc,
        "master_seed": _MASTER_SEED,
        "K": _K,
        "sr0_pp": _SR0_PP,
        "n_elected": _N_ELECTED,
        "dsr_threshold": _DSR_THRESHOLD,
        "alpha": _ALPHA,
    }

    _RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_RECEIPT_PATH, "w") as fh:
        yaml.dump(receipt, fh, default_flow_style=False, sort_keys=False)

    print(f"Freeze-receipt written: {_RECEIPT_PATH}")
    print(f"  prereg_sha256 : {prereg_sha256}")
    print(f"  code_commit   : {code_commit}")
    print(f"  frozen_at_utc : {frozen_at_utc}")
    print()
    print("IMPORTANT: commit this receipt file to git immediately.")
    print("No STEP-4 bootstrap draw may run before this receipt is committed.")


if __name__ == "__main__":
    main()
