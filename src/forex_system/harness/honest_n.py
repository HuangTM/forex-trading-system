"""HoQR Honest-N — two distinct functions for two distinct purposes.

compute_honest_n()
    De-duplication view (N ≈ 11).  Answers "how many distinct hypothesis
    FAMILIES has the firm explored?"  Research-portfolio / anti-survivorship-bias
    view for HoQR only.

    IMPORTANT: this function is FORBIDDEN at any compute_dsr call site.
    It answers the portfolio de-dup question (N ≈ 11), NOT the multiplicity-
    deflation question.  Passing its result to compute_dsr UNDER-deflates and
    manufactures false passes (the unacceptable error direction).
    Use honest_n_deflation_denominator() for all compute_dsr sites.

honest_n_deflation_denominator()
    Multiplicity denominator (N = 30 as of 2026-06-18 ratification).  Answers
    "how many independent attempts could have been selected as the winner?"
    Every attempt burns one slot, programme-wide, monotonic.  THIS is what must
    be passed to compute_dsr().

    Algorithm (HoQR + NHT jointly ratified 2026-06-18; CTO spec
    .fintech-org/artifacts/2026-06-17-forward-test-loop/cto-honest-n-rebuild-spec.yaml):

      1. Parse JSONL.  Locate the single 'honest-n-classification' record.
         Raises RuntimeError if absent (fail-closed — never silently under-count).
      2. The record's ``counted_trial_ids`` list is the LEGACY classification
         (the 30 ratified by HoQR + NHT).  Each entry has a per-trial reason.
      3. For any trial_id present in the ledger but NOT in the record's
         counted or excluded lists, classify mechanically:
           DROP if: spawned-only (no terminal record, sharpe=null);
                    re-run-equivalent (same config_hash AND same sharpe as a
                      prior counted id);
                    withdrawn-pre-freeze OR counts_toward_deflation_denominator==false
                      (sticky-exclusion: once flagged, always excluded).
           COUNT otherwise (ambiguity default = over-deflate per SD2/IC-9).
      4. Return len(counted_legacy ∪ counted_new).  NO integer offset.

    Returns: PRIOR attempt count.  Caller adds +1 for the trial being scored.
    Ratified value (post-2026-06-18): 30.

    Ratification artifacts:
        .fintech-org/artifacts/2026-06-17-forward-test-loop/hoqr-dsr-debate-r1.yaml
        .fintech-org/artifacts/2026-06-17-forward-test-loop/nht-dsr-debate-r1.yaml
        .fintech-org/ceo-digest.jsonl DSR-DENOMINATOR-RECONCILED-CONVERGED 2026-06-18T03:41:24Z

De-duplication rule (verbatim from HoQR spec):
  A distinct hypothesis is keyed by:
    hypothesis_key = pre_reg_path  (if non-null)
                   else strategy_family_id
  where strategy_family_id = strategy name with cost-variant/pair-variant
  suffixes stripped (e.g. carry_2x_costs→carry, momentum_GBPUSD_only→momentum).

  EXCLUDE rows with status ∈ {spawned, exploratory}
  RETAIN  rows with status ∈ {complete, passed, rejected}
  UNKNOWN status → logged (not silently dropped)

  N_honest = count of DISTINCT hypothesis_key among retained rows.

Usage:
    n_honest, retained_keys, excluded_counts = compute_honest_n(Path(".fintech-org/trials.jsonl"))

    n_prior = honest_n_deflation_denominator(Path(".fintech-org/trials.jsonl"))
    n_trials = n_prior + 1  # +1 for the trial being scored
    dsr = compute_dsr(..., n_trials=n_trials, ...)
"""

from __future__ import annotations

import datetime
import json
import logging
import re
import subprocess
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Statuses for compute_honest_n (de-dup view)
# ---------------------------------------------------------------------------

# Statuses that indicate a falsification criterion was (or could be) applied.
RETAIN_STATUSES: frozenset[str] = frozenset({"complete", "passed", "rejected"})

# Statuses excluded per spec: no test occurred / no falsification criterion.
EXCLUDE_STATUSES: frozenset[str] = frozenset({"spawned", "exploratory"})

# Status that is the ONLY legitimate non-count for deflation purposes.
_WITHDRAWN_STATUS = "withdrawn-pre-freeze"

# Event type for the ratified classification record (replaces the retired
# 'honest-n-reconciliation' / integer-offset approach).
_CLASSIFICATION_EVENT = "honest-n-classification"

# Regex to iteratively strip known cost-variant and pair-variant suffixes.
# Order matters: longer / more-specific patterns first so they match before shorter ones.
_SUFFIX_PATTERN = re.compile(
    r"("
    r"_no_vol_scaling"
    r"|_vol_scaling"
    r"|_\d+x_costs?"  # e.g. _2x_costs, _3x_cost
    r"|_\d+x"  # e.g. _2x, _3x
    r"|_stripped"
    r"|_canonical"
    r"|_portfolio"
    r"|_revalidation"
    r"|_diagnostic"
    r"|_USDJPY|_GBPUSD|_EURUSD|_GBPJPY|_CADJPY"
    r"|_4h|_1h|_daily"
    r"|_only"
    r"|_variant\d*"
    r"|_v\d+"
    r")$",
    re.IGNORECASE,
)

_MAX_STRIP_ITERATIONS = 10  # guard against infinite loops


def _normalize_strategy(strategy: str) -> str:
    """Strip cost-variant and pair-variant suffixes from a strategy name.

    Iterates until no further suffix is removed (or _MAX_STRIP_ITERATIONS hit).

    Examples:
        vol_target_carry_no_vol_scaling → vol_target_carry
        carry_2x_costs                  → carry
        momentum_GBPUSD_only            → momentum
        fred_carry_stripped             → fred_carry
        tas_ceiling_4h                  → tas_ceiling
    """
    name = strategy
    for _ in range(_MAX_STRIP_ITERATIONS):
        stripped = _SUFFIX_PATTERN.sub("", name)
        if stripped == name:
            break
        name = stripped
    return name


def compute_honest_n(
    trials_path: Path,
) -> tuple[int, set[str], dict[str, int]]:
    """Compute N_honest per HoQR de-duplication rule.

    RESEARCH-PORTFOLIO VIEW ONLY — FORBIDDEN at any compute_dsr call site.

    Reads ``trials_path`` (JSONL, one record per line).  Multiple rows for the
    same trial_id are collapsed to the *last* occurrence (most complete record).
    Then:
      - Rows with status ∈ EXCLUDE_STATUSES are dropped and counted.
      - Rows with status ∈ RETAIN_STATUSES determine hypothesis_key.
      - N_honest = |{distinct hypothesis_key}| among retained rows.

    N_honest ≈ 11 (distinct hypothesis families for HoQR portfolio view).
    This value MUST NOT be passed to compute_dsr as n_trials — it under-deflates
    and manufactures false passes.  Use honest_n_deflation_denominator() instead.

    Args:
        trials_path: Path to .fintech-org/trials.jsonl.

    Returns:
        (n_honest, retained_keys, excluded_counts) where:
            n_honest        — count of distinct hypothesis keys (de-dup view)
            retained_keys   — set of distinct hypothesis_key strings
            excluded_counts — Counter of excluded statuses, e.g. {"spawned": 2, "exploratory": 8}
    """
    # Collapse multiple rows per trial_id (last row wins — most complete state).
    by_id: dict[str, dict] = {}
    with open(trials_path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            tid = record.get("trial_id")
            if tid is not None:
                by_id[tid] = record

    retained: list[dict] = []
    excluded_counts: Counter[str] = Counter()

    for record in by_id.values():
        status = record.get("status", "unknown")
        if status in EXCLUDE_STATUSES:
            excluded_counts[status] += 1
            logger.debug(
                '{"event": "honest_n.excluded", "trial_id": "%s", "status": "%s"}',
                record["trial_id"],
                status,
            )
        elif status in RETAIN_STATUSES:
            retained.append(record)
        else:
            # BUG FIX (NHT D5): previously this branch silently dropped unknown-status
            # rows (e.g. pre-registered-frozen-pending-receipt, event-archive lines).
            # These are NOT excluded from the de-dup view — they are explicitly logged
            # and excluded only because they have no falsification criterion applied yet.
            # This does NOT affect honest_n_deflation_denominator (separate function).
            logger.warning(
                '{"event": "honest_n.unknown_status_skipped", "trial_id": "%s", "status": "%s",'
                ' "note": "not retained for de-dup view; status is not in RETAIN_STATUSES"}',
                record.get("trial_id", "?"),
                status,
            )

    logger.info(
        '{"event": "honest_n.filter_summary", "total_unique_trials": %d, '
        '"retained": %d, "excluded": %s}',
        len(by_id),
        len(retained),
        dict(excluded_counts),
    )

    # Compute hypothesis_key for each retained record.
    retained_keys: set[str] = set()
    for record in retained:
        pre_reg = record.get("pre_reg_path")
        if pre_reg:
            hkey = pre_reg
        else:
            strategy = record.get("strategy") or ""
            hkey = _normalize_strategy(strategy)
        retained_keys.add(hkey)
        logger.debug(
            '{"event": "honest_n.key_assigned", "trial_id": "%s", '
            '"strategy": "%s", "pre_reg": "%s", "hypothesis_key": "%s"}',
            record["trial_id"],
            record.get("strategy", ""),
            pre_reg or "",
            hkey,
        )

    n_honest = len(retained_keys)
    logger.info(
        '{"event": "honest_n.result", "n_honest": %d, "retained_keys": %s}',
        n_honest,
        sorted(retained_keys),
    )

    return n_honest, retained_keys, dict(excluded_counts)


# ---------------------------------------------------------------------------
# DSR DEFLATION DENOMINATOR — the multiplicity count (ratified N = 30)
# ---------------------------------------------------------------------------

def honest_n_deflation_denominator(trials_path: Path) -> int:
    """Compute the DSR deflation denominator: org-wide cumulative attempt count.

    Implements the mechanical counting rule ratified by HoQR + NHT (2026-06-18).
    Denominator is pinned at 30 for the current ledger (34 distinct ids, 4 drops).

    Ratification artifacts:
        .fintech-org/artifacts/2026-06-17-forward-test-loop/hoqr-dsr-debate-r1.yaml
        .fintech-org/artifacts/2026-06-17-forward-test-loop/nht-dsr-debate-r1.yaml
        CTO spec: .fintech-org/artifacts/2026-06-17-forward-test-loop/cto-honest-n-rebuild-spec.yaml
        Convergence digest: ceo-digest.jsonl DSR-DENOMINATOR-RECONCILED-CONVERGED 2026-06-18T03:41:24Z

    Returns the PRIOR attempt count (the number of independent research attempts
    the firm has already made).  Callers MUST add +1 for the trial being scored:

        n_prior = honest_n_deflation_denominator(trials_path)
        dsr = compute_dsr(..., n_trials=n_prior + 1, ...)

    Exception: trial_48_is_eval.py passes N_ORG_TRIALS DIRECTLY (no +1) because
    trial-48 (15923fe1) is already ledgered and counted in the 30.

    Algorithm:
        1. Parse JSONL.  Locate the single 'honest-n-classification' record.
           Raises RuntimeError if absent (fail-closed: never silently under-count).
        2. counted_trial_ids from the record form the LEGACY set (the ratified 30).
        3. For trial_ids NOT in the legacy counted/excluded lists, classify
           mechanically per the counting rule (new trials appended after the record).
        4. Return len(counted_legacy ∪ counted_new).  NO integer offset.

    Counting rule for NEW trials (trials appended after the classification record):
        COUNT if:
            - A distinct config that RAN and produced a sharpe/verdict
              (status ∈ {complete, passed, rejected}), including rejects.
            - A param/window variant: distinct config_hash within a strategy family.
            - An ambiguous/unknown-status id whose non-draw status is UNPROVABLE
              (over-deflate default per SD2/IC-9).
        DROP if:
            - spawned-only: status == "spawned" AND sharpe is null (never executed,
              no result could be selected as a max). NOTE the narrowness is deliberate:
              the CTO-spec finding (B) warns that a broad "any null-sharpe => drop" rule
              wrongly sweeps up the ambiguous-but-possible draws (frozen-pending-receipt,
              null-status archive lines, exploratory backfills) that the firm COUNTS.
              Only the unambiguous spawned-only status drops; every other null-sharpe id
              falls through to the SD2 over-deflate COUNT default.
            - pure re-run-equivalent: same config_hash AND same sharpe as an
              EARLIER distinct counted id (config_hash+sharpe is load-bearing;
              sharpe alone over-drops, per CTO spec finding B/C).
            - withdrawn-pre-freeze OR counts_toward_deflation_denominator==false
              (sticky-exclusion: once flagged, always excluded across last-wins).

    Fail-closed invariant (SD2 / IC-9):
        If a trial's classification is ambiguous, COUNT IT toward the denominator.
        A too-large denominator costs a missed real edge (false-negative — the firm's
        stated acceptable error).  A too-small denominator manufactures false passes
        (false-positive — the unacceptable error).

    Args:
        trials_path: Path to .fintech-org/trials.jsonl.

    Returns:
        Prior attempt count (integer, >= 0).  Add +1 before passing to compute_dsr
        for a NEW trial not yet in the ledger.

    Raises:
        RuntimeError: if the 'honest-n-classification' record is absent.
            Fail-closed: without the classification record the count is undefined.
    """
    records_by_id: dict[str, dict] = {}
    classification_record: dict | None = None
    classification_record_count = 0

    # STICKY EXCLUSION (SD2): any trial_id that EVER carried an explicit false flag or a
    # withdrawn-pre-freeze status is permanently non-counting, even if a LATER record for
    # the same trial_id omits the flag.  Tracking the exclusion separately makes it
    # monotonic (last-wins collapse alone could resurrect a flagged trial).
    ever_excluded: set[str] = set()

    with open(trials_path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)

            # Locate the ratified classification record (no trial_id field).
            if record.get("event") == _CLASSIFICATION_EVENT:
                classification_record_count += 1
                # Guard (a): more than one classification record is a miscalibration
                # — the count would be ambiguous (last-wins silently drops one ratification).
                if classification_record_count > 1:
                    raise RuntimeError(
                        f"honest_n_deflation_denominator: found {classification_record_count} "
                        f"'{_CLASSIFICATION_EVENT}' records in {trials_path}. "
                        "Exactly ONE is permitted. Multiple records indicate a ledger "
                        "miscalibration — resolve by removing the duplicate before proceeding."
                    )
                classification_record = record
                logger.debug(
                    '{"event": "honest_n.classification_record_found",'
                    ' "ratified_n": %d, "ratified_by": %s}',
                    record.get("ratified_n", -1),
                    record.get("ratified_by", []),
                )
                continue

            trial_id = record.get("trial_id")
            if trial_id is None:
                # Non-trial metadata record (future-proof). Skip.
                logger.debug(
                    '{"event": "honest_n_deflation.skip_no_trial_id",'
                    ' "event_type": "%s"}',
                    record.get("event", "unknown"),
                )
                continue

            # Sticky exclusion: once flagged false OR withdrawn-pre-freeze, stays excluded.
            if (
                record.get("counts_toward_deflation_denominator") is False
                or record.get("status") == _WITHDRAWN_STATUS
            ):
                ever_excluded.add(trial_id)

            # last-wins collapse: most complete / terminal state overwrites earlier.
            records_by_id[trial_id] = record

    # Fail-closed: classification record MUST be present.
    if classification_record is None:
        raise RuntimeError(
            "honest_n_deflation_denominator: no 'honest-n-classification' record found "
            f"in {trials_path}. The ratified classification record must be appended to the "
            "ledger before this function can return an honest count. "
            "See .fintech-org/artifacts/2026-06-17-forward-test-loop/cto-honest-n-rebuild-spec.yaml "
            "for the required record format."
        )

    # Extract the legacy counted and excluded sets from the record.
    counted_entries = classification_record.get("counted_trial_ids", [])
    excluded_entries = classification_record.get("excluded_trial_ids", [])

    # Guard (b): ratified_n must equal len(counted_trial_ids).
    # A mismatch means the stated N drifted from the actual census — a silent
    # miscalibration that would under- or over-deflate every future DSR.
    ratified_n = classification_record.get("ratified_n")
    actual_counted_len = len(counted_entries)
    if ratified_n is None:
        raise RuntimeError(
            f"honest_n_deflation_denominator: the '{_CLASSIFICATION_EVENT}' record "
            f"in {trials_path} has no 'ratified_n' field. "
            "The record is malformed — it must declare the integer count it was ratified at."
        )
    if int(ratified_n) != actual_counted_len:
        raise RuntimeError(
            f"honest_n_deflation_denominator: ratified_n={ratified_n} in the "
            f"'{_CLASSIFICATION_EVENT}' record does not match len(counted_trial_ids)="
            f"{actual_counted_len} in {trials_path}. "
            "The stated N has drifted from the census — resolve the mismatch before proceeding."
        )

    legacy_counted: set[str] = {e["trial_id"] for e in counted_entries}
    legacy_excluded: set[str] = {e["trial_id"] for e in excluded_entries}

    # Build (config_hash, sharpe) index for counted legacy ids — used for re-run detection
    # on NEW trials.  The load-bearing rule: re-run = same config_hash AND same sharpe.
    counted_signatures: set[tuple[str, float]] = set()
    for tid in legacy_counted:
        rec = records_by_id.get(tid)
        if rec is not None:
            ch = rec.get("config_hash")
            sh = rec.get("sharpe")
            if ch is not None and sh is not None:
                counted_signatures.add((str(ch), float(sh)))

    # Classify NEW trials: trial_ids in the ledger but NOT in either legacy list.
    new_counted: set[str] = set()
    new_excluded_count = 0

    for trial_id, record in records_by_id.items():
        if trial_id in legacy_counted or trial_id in legacy_excluded:
            continue  # already classified by the ratified record

        # Sticky or field-based exclusion.
        flag = record.get("counts_toward_deflation_denominator")
        status = record.get("status", "")
        if trial_id in ever_excluded or flag is False or status == _WITHDRAWN_STATUS:
            new_excluded_count += 1
            logger.debug(
                '{"event": "honest_n_deflation.new_trial_excluded",'
                ' "trial_id": "%s", "reason": "withdrawn_or_flag_false"}',
                trial_id,
            )
            continue

        # Spawned-only: no terminal record, sharpe is null — never executed.
        sharpe = record.get("sharpe")
        if sharpe is None and status == "spawned":
            new_excluded_count += 1
            logger.debug(
                '{"event": "honest_n_deflation.new_trial_excluded",'
                ' "trial_id": "%s", "reason": "spawned_only_no_sharpe"}',
                trial_id,
            )
            continue

        # Re-run-equivalent: same config_hash AND same sharpe as an already-counted id.
        # sharpe alone is insufficient (a9c0902d has same sharpe as 7dde9154 but different
        # config_hash — identity-as-rerun is UNPROVABLE, so it COUNTS per SD2).
        # The signature set includes legacy counted ids AND new ids counted earlier in
        # this pass (ledger order). So if two NEW trials share config_hash+sharpe, the
        # FIRST (the original draw) counts and the SECOND (the byte-equivalent re-run,
        # no new max) drops — the intended de-duplication, deterministic in ledger order.
        config_hash = record.get("config_hash")
        if config_hash is not None and sharpe is not None:
            sig = (str(config_hash), float(sharpe))
            if sig in counted_signatures:
                new_excluded_count += 1
                logger.debug(
                    '{"event": "honest_n_deflation.new_trial_excluded",'
                    ' "trial_id": "%s", "reason": "rerun_equivalent_config_hash_and_sharpe"}',
                    trial_id,
                )
                continue

        # Everything else counts — including ambiguous/unknown status (SD2 rule).
        new_counted.add(trial_id)
        if config_hash is not None and sharpe is not None:
            counted_signatures.add((str(config_hash), float(sharpe)))
        logger.debug(
            '{"event": "honest_n_deflation.new_trial_counted",'
            ' "trial_id": "%s", "status": "%s"}',
            trial_id,
            status,
        )

    n = len(legacy_counted) + len(new_counted)

    # Emit structured decision-trace event (log-as-decision-trace IC-9).
    git_sha = _git_sha_short()
    classification_record_ref = (
        f"honest-n-classification in {trials_path} "
        f"(ratified_n={classification_record.get('ratified_n')}, "
        f"ratified_by={classification_record.get('ratified_by')})"
    )
    logger.info(
        '{"event": "honest_n.computed", "n": %d, '
        '"counted_legacy": %d, "counted_new": %d, "new_excluded": %d,'
        ' "classification_record_ref": "%s",'
        ' "source": "%s", "git_sha": "%s", "ts": "%s"}',
        n,
        len(legacy_counted),
        len(new_counted),
        new_excluded_count,
        classification_record_ref,
        str(trials_path),
        git_sha,
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )

    return n


def ic9_dsr_denominator(
    trials_path: Path,
    is_search_family_size: int,
    forward_attempt_budget: int,
) -> int:
    """Full IC-9 DSR denominator for a specific evaluation.

    Per NHT IC-9 (nht-dsr-denominator.yaml, section 2):
        N_DSR = org_wide_honest_N + IS_search_family + forward_attempt_budget

    This is the FULL denominator to pass to compute_dsr for a forward evaluation.
    It is strictly >= org_wide_honest_N.

    Args:
        trials_path:            Path to .fintech-org/trials.jsonl.
        is_search_family_size:  Number of in-sample configurations searched to PICK
                                this candidate (not yet ledgered as distinct trials).
                                0 for a single frozen structure with no IS search.
                                When unknown/informal, use a conservative worst-case.
        forward_attempt_budget: Pre-declared number of forward candidates the firm
                                reserved the right to try in this window.  Must be
                                frozen before the first candidate spawn (IC-13).
                                0 if a budget record is not yet declared (caller
                                should check and warn; honest_n still computes).

    Returns:
        Full IC-9 denominator (int >= org_wide_honest_N).  Pass directly to
        compute_dsr as n_trials — do NOT add another +1; this value already
        represents the trial being scored as one of the forward attempts.

    Example::

        from forex_system.harness.honest_n import ic9_dsr_denominator
        from forex_system.harness.dsr import compute_dsr

        n_dsr = ic9_dsr_denominator(
            trials_path=Path(".fintech-org/trials.jsonl"),
            is_search_family_size=0,   # single pre-registered structure, no IS sweep
            forward_attempt_budget=1,  # pre-declared: 1 forward candidate
        )
        dsr = compute_dsr(..., n_trials=n_dsr, ...)
    """
    org_n = honest_n_deflation_denominator(trials_path)
    n_dsr = org_n + is_search_family_size + forward_attempt_budget
    logger.info(
        '{"event": "ic9_denominator.computed", "org_wide_n": %d,'
        ' "is_search_family_size": %d, "forward_attempt_budget": %d,'
        ' "n_dsr": %d}',
        org_n,
        is_search_family_size,
        forward_attempt_budget,
        n_dsr,
    )
    return n_dsr


def _git_sha_short() -> str:
    """Current HEAD commit SHA (short) or 'untracked'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "untracked"
