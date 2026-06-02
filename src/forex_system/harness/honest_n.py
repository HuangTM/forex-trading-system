"""HoQR Honest-N De-duplication Rule.

Computes N_honest — the count of distinct hypotheses tested programme-wide —
per the Head of Quant Research's anti-survivorship-bias specification.

De-duplication rule (verbatim from HoQR spec):
  A distinct hypothesis is keyed by:
    hypothesis_key = pre_reg_path  (if non-null)
                   else strategy_family_id
  where strategy_family_id = strategy name with cost-variant/pair-variant
  suffixes stripped (e.g. carry_2x_costs→carry, momentum_GBPUSD_only→momentum).

  EXCLUDE rows with status ∈ {spawned, exploratory}
  RETAIN  rows with status ∈ {complete, passed, rejected}

  N_honest = count of DISTINCT hypothesis_key among retained rows.

Usage:
    n_honest, retained_keys, excluded_counts = compute_honest_n(Path(".fintech-org/trials.jsonl"))
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

# Statuses that indicate a falsification criterion was (or could be) applied.
RETAIN_STATUSES: frozenset[str] = frozenset({"complete", "passed", "rejected"})

# Statuses excluded per spec: no test occurred / no falsification criterion.
EXCLUDE_STATUSES: frozenset[str] = frozenset({"spawned", "exploratory"})

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

    Reads ``trials_path`` (JSONL, one record per line).  Multiple rows for the
    same trial_id are collapsed to the *last* occurrence (most complete record).
    Then:
      - Rows with status ∈ EXCLUDE_STATUSES are dropped and counted.
      - Rows with status ∈ RETAIN_STATUSES determine hypothesis_key.
      - N_honest = |{distinct hypothesis_key}| among retained rows.

    Args:
        trials_path: Path to .fintech-org/trials.jsonl.

    Returns:
        (n_honest, retained_keys, excluded_counts) where:
            n_honest        — count of distinct hypothesis keys (the N for DSR)
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
            by_id[record["trial_id"]] = record

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
            logger.warning(
                '{"event": "honest_n.unknown_status", "trial_id": "%s", "status": "%s"}',
                record["trial_id"],
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
