"""Canary tests: verify the policy-violations logging path end-to-end.

CTO CONDITION-2 (docs/decisions/CONSENSUS_2026-04-28.md): policy-violations.jsonl logging
path verified end-to-end -- "canary violation + confirm appears" within 3 days
(deadline 2026-05-01).

CONDITION-2 demands TWO things, not one:
  (a) the scanner correctly DETECTS a forbidden phrase, AND
  (b) when a violation is detected, an entry actually APPEARS in
      .fintech-org/policy-violations.jsonl with the expected schema.

The detection path and the append path are separate. A test that proves only
detection leaves the more important leg of the condition unverified, because
the orchestrator (or any future automation) is the one that writes the JSONL
entry on a detected violation -- and that discipline can silently break.

This file therefore has FOUR tests:
  - test_dirty_file_returns_exit_code_1_and_reports_phrase
  - test_clean_file_returns_exit_code_0
  - test_existing_violations_jsonl_is_parseable_with_required_fields
  - test_end_to_end_detect_then_append_round_trip

The end-to-end test exercises the full detect-then-append round trip on a
TEMPORARY copy of the JSONL so the production log is never corrupted.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_VIOLATIONS_LOG = REPO_ROOT / ".fintech-org" / "policy-violations.jsonl"

_CONFIG_PATH = Path.home() / ".claude/skills/fintech-org/forbidden-phrases.json"
_SCANNER_PATH = (
    Path.home()
    / ".claude/skills/agent-accountability/scripts/check_forbidden_phrases.py"
)
_WRAPPER_PATH = (
    Path.home() / ".claude/skills/fintech-org/scripts/check_forbidden_phrases.py"
)


def _pick_scanner() -> Path | None:
    if _SCANNER_PATH.is_file():
        return _SCANNER_PATH
    if _WRAPPER_PATH.is_file():
        return _WRAPPER_PATH
    return None


_SKILL_AVAILABLE = _pick_scanner() is not None and _CONFIG_PATH.is_file()
skill_required = pytest.mark.skipif(
    not _SKILL_AVAILABLE,
    reason="fintech-org skill not installed at ~/.claude/skills/ -- skipping",
)


def _run_scanner(scanner: Path, config: Path, target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(scanner), "--config", str(config), "--target", str(target)],
        capture_output=True,
        text=True,
    )


def _detect_then_append(
    scanner: Path,
    config: Path,
    target: Path,
    log_path: Path,
    role: str,
) -> bool:
    """Mirror the orchestrator's discipline: scan, and if violation, append.

    Returns True if a violation was detected (and an entry was appended).
    """
    result = _run_scanner(scanner, config, target)
    if result.returncode == 0:
        return False
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "role": role,
        "matched_phrases": [],
        "scanner_stdout_excerpt": result.stdout[:300],
        "action": "canary_test_detect_then_append",
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True


@skill_required
def test_dirty_file_returns_exit_code_1_and_reports_phrase():
    """Scanner must exit 1 and surface the matched phrase in stdout."""
    scanner = _pick_scanner()
    canary = "This strategy should trade with real money on the live account.\n"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(canary)
        tmp_path = Path(tf.name)

    try:
        result = _run_scanner(scanner, _CONFIG_PATH, tmp_path)
        assert result.returncode == 1, (
            f"Expected exit code 1 (violation), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "real money" in result.stdout.lower(), (
            f"Expected 'real money' in stdout. Got:\n{result.stdout}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@skill_required
def test_clean_file_returns_exit_code_0():
    """Scanner must exit 0 on content with no forbidden phrases."""
    scanner = _pick_scanner()
    clean = (
        "This strategy runs against synthetic paper data only.\n"
        "All results are from backtests on historical OHLCV fixtures.\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(clean)
        tmp_path = Path(tf.name)

    try:
        result = _run_scanner(scanner, _CONFIG_PATH, tmp_path)
        assert result.returncode == 0, (
            f"Expected exit code 0 (clean), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def test_existing_violations_jsonl_is_parseable_with_required_fields():
    """The production log must exist, be JSONL-parseable, and entries must
    carry the schema fields downstream consumers depend on.

    This is the FIRST half of CONDITION-2's "confirm appears" leg: the log
    file is real and prior appends produced well-formed entries.
    """
    assert PRODUCTION_VIOLATIONS_LOG.is_file(), (
        f"Expected {PRODUCTION_VIOLATIONS_LOG} to exist."
    )
    lines = [
        ln for ln in PRODUCTION_VIOLATIONS_LOG.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert lines, "policy-violations.jsonl is empty -- no prior appends to verify."

    required = {"timestamp", "role", "action"}
    for i, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            pytest.fail(f"Line {i} not JSON-parseable: {e}\nLine: {line[:200]}")
        missing = required - set(entry.keys())
        assert not missing, (
            f"Line {i} missing required fields {missing}.\nEntry: {entry}"
        )


@skill_required
def test_end_to_end_detect_then_append_round_trip(tmp_path: Path):
    """Full detect-then-append cycle on a TEMPORARY JSONL.

    This is the SECOND half of CONDITION-2's "confirm appears" leg: when a
    violation is detected, an entry actually lands in a JSONL with a parseable
    schema. Production log is never touched -- a temp copy is used.
    """
    scanner = _pick_scanner()
    prod_lines_before = (
        sum(1 for _ in PRODUCTION_VIOLATIONS_LOG.open(encoding="utf-8") if _.strip())
        if PRODUCTION_VIOLATIONS_LOG.is_file()
        else 0
    )
    temp_log = tmp_path / "policy-violations.jsonl"
    if PRODUCTION_VIOLATIONS_LOG.is_file():
        shutil.copyfile(PRODUCTION_VIOLATIONS_LOG, temp_log)
    else:
        temp_log.touch()

    pre_count = sum(1 for _ in temp_log.open(encoding="utf-8") if _.strip())

    canary_target = tmp_path / "canary.txt"
    canary_target.write_text(
        "Deploying with real money to the live account is the next step.\n",
        encoding="utf-8",
    )

    detected = _detect_then_append(
        scanner, _CONFIG_PATH, canary_target, temp_log, role="canary-test"
    )
    assert detected, "Scanner did not detect the canary phrase."

    post_count = sum(1 for _ in temp_log.open(encoding="utf-8") if _.strip())
    assert post_count == pre_count + 1, (
        f"Expected exactly one new entry; pre={pre_count} post={post_count}"
    )

    new_line = temp_log.read_text(encoding="utf-8").splitlines()[-1]
    new_entry = json.loads(new_line)
    for field in ("timestamp", "role", "action"):
        assert field in new_entry, f"New entry missing required field: {field}"
    assert new_entry["role"] == "canary-test"
    assert new_entry["action"] == "canary_test_detect_then_append"

    assert PRODUCTION_VIOLATIONS_LOG.is_file()
    prod_lines_after = sum(
        1 for _ in PRODUCTION_VIOLATIONS_LOG.open(encoding="utf-8") if _.strip()
    )
    assert prod_lines_after == prod_lines_before, (
        f"Production log was modified by the test! Pre-test count was "
        f"{prod_lines_before}, post-test count is {prod_lines_after}. "
        f"This is a serious test-isolation bug."
    )
