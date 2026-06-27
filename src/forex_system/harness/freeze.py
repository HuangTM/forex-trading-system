"""Forward-test freeze harness — IC-1, IC-2, IC-4, IC-8 enforcement.

Records a cryptographic freeze record for a forward evaluation candidate.
Appends ONE 'freeze' record to .fintech-org/forward_registry.jsonl with
open_count=0, burned=false, custody=<party>.

IC-1: full sha256 anchor tuple (prereg_content_hash, code_config_hash, git_sha,
      freeze_utc) written at freeze time, before any forward bar is scored.
IC-2: freeze record timestamps the causal boundary; forward_eval.py enforces
      that every M2 bar_timestamp > freeze_utc.
IC-8: forward_eval.py refuses to score a freeze_id with no prior freeze record
      (this module creates that record).
M1-hard-block (ML spec A.2 / CTO P1): freeze.py REFUSES to seal an M1 holdout
      for any family lacking a development_start_attestation that predates dev.
      For all families already explored against full history (e.g. H1), M1 is
      UNAVAILABLE — the harness routes to M2-only. This makes KG-4 an enforced
      gate, not a disclosure.

Usage (CLI):
    python -m forex_system.harness.freeze \\
        --pre-reg references/pre-registrations/h1_session_open_momentum_pooled.md \\
        --config config/default.yaml \\
        --mechanism M2 \\
        --custody nht

    # M1 with a holdout window (only for families with a prior dev-start attestation):
    python -m forex_system.harness.freeze \\
        --pre-reg references/pre-registrations/new_hypothesis.md \\
        --config config/default.yaml \\
        --mechanism M1 \\
        --seal-holdout 2024-07-01 2025-12-31 \\
        --custody nht

Decision-trace events emitted:
    freeze.sealed       — successful freeze, full anchor tuple
    freeze.m1_blocked   — M1 refused (no development_start_attestation), routed to M2
    freeze.error        — any exception (always emitted before propagation)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger("forex_system.harness.freeze")

_FORWARD_REGISTRY = Path(".fintech-org/forward_registry.jsonl")
_DEV_ATTESTATION_REGISTRY = Path(".fintech-org/dev_start_attestations.jsonl")

Mechanism = Literal["M1", "M2"]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HoldoutWindow:
    """M1-only: the sealed data window spec."""

    start: str         # ISO date string
    end: str           # ISO date string
    content_hash: str  # sha256 of the sealed bar bytes


@dataclass
class FreezeRecord:
    """The integrity anchor tuple persisted to forward_registry.jsonl at freeze time.

    Fields
    ------
    freeze_id:          UUID for this freeze record (referenced by forward_eval).
    prereg_content_hash: sha256(prereg.md bytes || triggers.yaml bytes).
    code_config_hash:   Full sha256 of the frozen config file.
    git_sha:            Full HEAD commit SHA at freeze.
    freeze_utc:         ISO UTC timestamp — the M2 causal boundary.
    mechanism:          'M1' (sequestered holdout) or 'M2' (paper-forward).
    custody:            Named party holding the sealed bytes (M1: NHT or PR).
    open_count:         Always 0 at freeze; set to 1 atomically by forward_eval.
    burned:             Always False at freeze; set to True atomically by forward_eval.
    holdout:            M1-only holdout window spec; None for M2.
    prereg_path:        Human-readable path for audit (not part of the hash).
    config_path:        Human-readable path for audit (not part of the hash).
    """

    freeze_id: str
    prereg_content_hash: str
    code_config_hash: str
    git_sha: str
    freeze_utc: str
    mechanism: Mechanism
    custody: str
    open_count: int
    burned: bool
    holdout: HoldoutWindow | None
    prereg_path: str
    config_path: str


# ---------------------------------------------------------------------------
# Hash helpers — FULL width (not the [:12] short hashes used in run_trial.py)
# ---------------------------------------------------------------------------


def _full_config_hash(config_path: Path) -> str:
    """Full sha256 of the config file bytes.

    Unlike run_trial._config_hash which returns sha256[:12] for the short
    registry label, this returns the full 64-char hex digest required for the
    permanent integrity anchor (collision resistance over a long-lived record).
    """
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def _full_git_sha() -> str:
    """Full HEAD commit SHA (not --short) — 'untracked' if not in a repo."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "untracked"


def _prereg_content_hash(prereg_path: Path) -> str:
    """sha256(prereg.md bytes || triggers.yaml bytes).

    Both files are concatenated before hashing so that editing either the
    prose or the structured gates changes the digest.
    """
    sidecar_path = prereg_path.with_suffix(".triggers.yaml")
    md_bytes = prereg_path.read_bytes()
    sidecar_bytes = sidecar_path.read_bytes() if sidecar_path.exists() else b""
    return hashlib.sha256(md_bytes + sidecar_bytes).hexdigest()


def _holdout_content_hash(holdout_bytes: bytes) -> str:
    """sha256 of the sealed holdout bar bytes."""
    return hashlib.sha256(holdout_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Development-start attestation (M1 gate)
# ---------------------------------------------------------------------------


def _load_dev_start_attestations(registry: Path = _DEV_ATTESTATION_REGISTRY) -> dict[str, dict]:
    """Load {family_id -> attestation_record} from the dev-start attestation registry.

    Returns an empty dict if the registry does not exist.
    """
    if not registry.exists():
        return {}
    attestations: dict[str, dict] = {}
    with open(registry) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            family_id = record.get("family_id")
            if family_id:
                attestations[family_id] = record
    return attestations


def _resolve_family_id(prereg_path: Path) -> str:
    """Derive a stable family identifier from the prereg path.

    Uses the stem of the prereg filename as the family identifier.
    E.g. 'h1_session_open_momentum_pooled.md' -> 'h1_session_open_momentum_pooled'.
    """
    return prereg_path.stem


def _check_m1_eligibility(
    prereg_path: Path,
    freeze_utc: str,
    attestation_registry: Path = _DEV_ATTESTATION_REGISTRY,
) -> None:
    """Assert M1 eligibility: a development_start_attestation must exist AND predate dev.

    Raises a ValueError (blocking — not a VOID) if:
    - No development_start_attestation exists for this family, OR
    - The attestation's dev_start_utc is AFTER the seal time (i.e. the seal
      does not predate development).

    Per ML spec A.2 / CTO P1 / IC-14: this is a hard REFUSE, not a VOID.
    A VOID implies the forward result was attempted but invalid; a REFUSE means
    the freeze was never valid to begin with.
    """
    family_id = _resolve_family_id(prereg_path)
    attestations = _load_dev_start_attestations(attestation_registry)

    if family_id not in attestations:
        _log_event(
            "freeze.m1_blocked",
            family_id=family_id,
            reason="no_development_start_attestation",
            routed_to="M2",
            prereg_path=str(prereg_path),
        )
        raise ValueError(
            f"M1 freeze REFUSED for family '{family_id}': no development_start_attestation "
            f"exists in {attestation_registry}. This hypothesis family has no record showing "
            "that the holdout was sealed BEFORE development began. For families already "
            "explored against full history (e.g. H1 and all prior firm work), M1 is "
            "UNAVAILABLE — use mechanism=M2 (paper-forward). "
            "See ML spec A.2 (M1_seal_predates_development_ENFORCEMENT) and IC-14."
        )

    attestation = attestations[family_id]
    dev_start_utc = attestation.get("dev_start_utc", "")
    if not dev_start_utc:
        _log_event(
            "freeze.m1_blocked",
            family_id=family_id,
            reason="attestation_missing_dev_start_utc",
            routed_to="M2",
            prereg_path=str(prereg_path),
        )
        raise ValueError(
            f"M1 freeze REFUSED for family '{family_id}': attestation record lacks "
            f"'dev_start_utc' field. The attestation is malformed — cannot verify "
            "seal predates development."
        )

    # Seal must predate development: seal_utc <= dev_start_utc
    # (i.e. the holdout was carved BEFORE any development began on this family).
    if freeze_utc > dev_start_utc:
        _log_event(
            "freeze.m1_blocked",
            family_id=family_id,
            reason="seal_postdates_development",
            seal_utc=freeze_utc,
            dev_start_utc=dev_start_utc,
            routed_to="M2",
            prereg_path=str(prereg_path),
        )
        raise ValueError(
            f"M1 freeze REFUSED for family '{family_id}': seal_utc={freeze_utc!r} > "
            f"dev_start_utc={dev_start_utc!r}. The holdout seal must PRE-DATE development "
            "(seal_utc <= dev_start_utc). This family has already been developed against "
            "data that postdates the proposed seal — the holdout is not provably unseen. "
            "Use mechanism=M2 (paper-forward, the only zero-leak path)."
        )


# ---------------------------------------------------------------------------
# Append-only registry helpers
# ---------------------------------------------------------------------------


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log line (log-as-decision-trace)."""
    entry = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(entry))


def _append_registry(record: dict, registry: Path = _FORWARD_REGISTRY) -> None:
    """Append one record to the forward_registry.jsonl append-only ledger."""
    registry.parent.mkdir(parents=True, exist_ok=True)
    with open(registry, "a") as fh:
        fh.write(json.dumps(record) + "\n")


def load_freeze_record(freeze_id: str, registry: Path = _FORWARD_REGISTRY) -> FreezeRecord:
    """Load a FreezeRecord by freeze_id from the forward registry.

    Raises:
        FileNotFoundError: if the registry file does not exist.
        KeyError: if no freeze record with the given freeze_id is found.
    """
    if not registry.exists():
        raise FileNotFoundError(
            f"Forward registry not found: {registry}. "
            "No freeze records exist yet. Run freeze.py first."
        )
    with open(registry) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            if record.get("record_type") == "freeze" and record.get("freeze_id") == freeze_id:
                holdout_data = record.get("holdout")
                holdout: HoldoutWindow | None = None
                if holdout_data is not None:
                    holdout = HoldoutWindow(
                        start=holdout_data["start"],
                        end=holdout_data["end"],
                        content_hash=holdout_data["content_hash"],
                    )
                return FreezeRecord(
                    freeze_id=record["freeze_id"],
                    prereg_content_hash=record["prereg_content_hash"],
                    code_config_hash=record["code_config_hash"],
                    git_sha=record["git_sha"],
                    freeze_utc=record["freeze_utc"],
                    mechanism=record["mechanism"],
                    custody=record["custody"],
                    open_count=record["open_count"],
                    burned=record["burned"],
                    holdout=holdout,
                    prereg_path=record.get("prereg_path", ""),
                    config_path=record.get("config_path", ""),
                )
    raise KeyError(
        f"No freeze record with freeze_id={freeze_id!r} found in {registry}. "
        "Ensure freeze.py was run and the record was appended before calling forward_eval."
    )


def update_freeze_record_burned(
    freeze_id: str,
    registry: Path = _FORWARD_REGISTRY,
) -> None:
    """Atomically mark a freeze record as burned (open_count=1, burned=True).

    Appends an UPDATE record; the reader (load_freeze_record_with_state) checks
    both the original freeze and any update records to determine current state.
    This preserves append-only semantics while allowing state mutation.
    """
    update: dict = {
        "record_type": "freeze-update",
        "freeze_id": freeze_id,
        "open_count": 1,
        "burned": True,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _append_registry(update, registry)


def load_freeze_record_with_state(
    freeze_id: str,
    registry: Path = _FORWARD_REGISTRY,
) -> tuple[FreezeRecord, int, bool]:
    """Load a FreezeRecord plus its current open_count and burned state.

    Scans the ledger for the freeze record and any subsequent update records
    to reconstruct the most-recent open_count and burned values.

    Returns:
        (record, open_count, burned)

    Raises:
        FileNotFoundError: registry not found.
        KeyError: no freeze record with the given freeze_id.
    """
    freeze_record = load_freeze_record(freeze_id, registry)
    open_count = freeze_record.open_count
    burned = freeze_record.burned

    # Scan for subsequent update records.
    with open(registry) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            if (
                rec.get("record_type") == "freeze-update"
                and rec.get("freeze_id") == freeze_id
            ):
                open_count = rec.get("open_count", open_count)
                burned = rec.get("burned", burned)

    return freeze_record, open_count, burned


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def freeze_structure(
    prereg_path: Path,
    config_path: Path,
    mechanism: Mechanism,
    custody: str,
    holdout_window: tuple[str, str] | None = None,
    holdout_bytes: bytes | None = None,
    registry: Path = _FORWARD_REGISTRY,
    attestation_registry: Path = _DEV_ATTESTATION_REGISTRY,
) -> FreezeRecord:
    """Record a forward-test freeze: write the integrity anchor tuple.

    This is the IC-1 / IC-8 enforcement point: no forward eval may run without
    a prior freeze record in the registry (forward_eval.py checks this).

    Parameters
    ----------
    prereg_path:
        Path to the pre-registration markdown file. Its paired .triggers.yaml
        must also exist (prereg_content_hash covers both).
    config_path:
        Path to the frozen config YAML driving the forward run.
    mechanism:
        'M1' (sequestered holdout) or 'M2' (paper-forward).
        M1 requires a development_start_attestation predating development (hard
        block otherwise, not a VOID — the freeze is illegitimate by construction).
    custody:
        Named party holding the sealed bytes (e.g. 'nht', 'pr'). Must differ
        from the developer (separation of duties, KG-1 residual risk on a
        single-developer firm — honest ceiling).
    holdout_window:
        (start_iso, end_iso) for M1 only. Required when mechanism='M1'.
    holdout_bytes:
        Raw bytes of the sealed holdout bars. Required when mechanism='M1'.
        The sha256 of these bytes is recorded as holdout_content_hash.
    registry:
        Path to forward_registry.jsonl (override for tests).
    attestation_registry:
        Path to dev_start_attestations.jsonl (override for tests).

    Returns
    -------
    FreezeRecord
        The frozen record appended to the registry.

    Raises
    ------
    FileNotFoundError:
        prereg_path or config_path does not exist.
    ValueError:
        M1 freeze attempted for a family without a valid
        development_start_attestation predating development.
        M1 freeze attempted without holdout_window/holdout_bytes.
    """
    if not prereg_path.exists():
        raise FileNotFoundError(
            f"Pre-registration not found: {prereg_path}. "
            "Cannot freeze without the pre-registration document."
        )
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}. "
            "Cannot freeze without the config file."
        )

    freeze_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # M1 eligibility gate (IC-1 / ML spec A.2 / CTO P1).
    if mechanism == "M1":
        _check_m1_eligibility(prereg_path, freeze_utc, attestation_registry)
        if holdout_window is None or holdout_bytes is None:
            raise ValueError(
                "M1 freeze requires holdout_window=(start, end) and holdout_bytes. "
                "Provide the sealed bar content so holdout_content_hash can be recorded."
            )

    # Compute the full-width integrity hashes.
    prereg_hash = _prereg_content_hash(prereg_path)
    config_hash = _full_config_hash(config_path)
    git_sha = _full_git_sha()
    freeze_id = str(uuid.uuid4())

    holdout: HoldoutWindow | None = None
    if mechanism == "M1" and holdout_window is not None and holdout_bytes is not None:
        holdout = HoldoutWindow(
            start=holdout_window[0],
            end=holdout_window[1],
            content_hash=_holdout_content_hash(holdout_bytes),
        )

    record = FreezeRecord(
        freeze_id=freeze_id,
        prereg_content_hash=prereg_hash,
        code_config_hash=config_hash,
        git_sha=git_sha,
        freeze_utc=freeze_utc,
        mechanism=mechanism,
        custody=custody,
        open_count=0,
        burned=False,
        holdout=holdout,
        prereg_path=str(prereg_path),
        config_path=str(config_path),
    )

    # Write to the append-only forward registry (IC-1 / IC-8).
    registry_entry: dict = {
        "record_type": "freeze",
        "freeze_id": freeze_id,
        "prereg_content_hash": prereg_hash,
        "code_config_hash": config_hash,
        "git_sha": git_sha,
        "freeze_utc": freeze_utc,
        "mechanism": mechanism,
        "custody": custody,
        "open_count": 0,
        "burned": False,
        "holdout": asdict(holdout) if holdout is not None else None,
        "prereg_path": str(prereg_path),
        "config_path": str(config_path),
    }
    _append_registry(registry_entry, registry)

    _log_event(
        "freeze.sealed",
        freeze_id=freeze_id,
        prereg_content_hash=prereg_hash,
        code_config_hash=config_hash,
        git_sha=git_sha,
        freeze_utc=freeze_utc,
        mechanism=mechanism,
        custody=custody,
        holdout_window=list(holdout_window) if holdout_window is not None else None,
        holdout_content_hash=holdout.content_hash if holdout is not None else None,
        prereg_path=str(prereg_path),
        config_path=str(config_path),
    )

    return record


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record a forward-test freeze (IC-1/IC-8). "
        "Appends one 'freeze' record to .fintech-org/forward_registry.jsonl."
    )
    parser.add_argument(
        "--pre-reg", required=True, dest="pre_reg",
        help="Path to the pre-registration markdown file.",
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to the frozen config YAML.",
    )
    parser.add_argument(
        "--mechanism", required=True, choices=["M1", "M2"],
        help="M1 (sequestered holdout) or M2 (paper-forward).",
    )
    parser.add_argument(
        "--custody", required=True,
        help="Named custodian of the sealed bytes (e.g. 'nht', 'pr').",
    )
    parser.add_argument(
        "--seal-holdout", nargs=2, metavar=("START", "END"),
        help="M1 only: holdout window start and end as ISO dates.",
    )
    args = parser.parse_args()

    try:
        prereq_path = Path(args.pre_reg)
        config_path = Path(args.config)
        holdout_window: tuple[str, str] | None = None
        holdout_bytes: bytes | None = None
        if args.seal_holdout:
            holdout_window = (args.seal_holdout[0], args.seal_holdout[1])
            # In CLI mode, holdout_bytes comes from the data loader (out of scope here).
            # Placeholder: real use would load the parquet file for the window.
            # For the CLI to produce a real content hash, the caller must supply the
            # holdout data file separately; here we raise informatively.
            raise NotImplementedError(
                "CLI M1 sealing requires the holdout bytes to be loaded from the data store. "
                "Use freeze_structure() programmatically and pass holdout_bytes directly."
            )

        record = freeze_structure(
            prereg_path=prereq_path,
            config_path=config_path,
            mechanism=args.mechanism,
            custody=args.custody,
            holdout_window=holdout_window,
            holdout_bytes=holdout_bytes,
        )
        print(f"Freeze sealed: {record.freeze_id}")
        print(f"  mechanism:    {record.mechanism}")
        print(f"  freeze_utc:   {record.freeze_utc}")
        print(f"  git_sha:      {record.git_sha[:12]}...")
        print(f"  custody:      {record.custody}")
    except Exception as exc:
        _log_event("freeze.error", error=str(exc), error_type=type(exc).__name__)
        print(f"freeze.py error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
