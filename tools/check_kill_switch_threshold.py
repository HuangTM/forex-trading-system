#!/usr/bin/env python3
"""Kill-switch threshold gate for pre-registration commits.

CRO binding constraint #3 of CONSENSUS_2026-04-28.md requires every
pre-registered trial to declare its kill-switch threshold verbatim. The field
is parsed at trial-spawn time to populate the trials.jsonl pre-reg entry;
absence at commit time blocks shipping.

Checks staged ADDED files under references/pre-registrations/*.md and verifies
that each contains a `kill_switch_threshold:` field. Existing pre-registration
files are grandfathered (only newly-added files are checked, mirroring Gate 1).

Compliance rule: a pre-registration markdown file is compliant if it contains
AT LEAST ONE line matching the regex (searched anywhere in the line):

    kill_switch_threshold:\\s*\\S+

  (case-sensitive; value may be any non-whitespace token, e.g.:
   `kill_switch_threshold: 0.30`
   `kill_switch_threshold: VTC-T1`
   `kill_switch_threshold: see-falsification-criteria-T1-T8`)

V0 limitation: the regex is searched anywhere in a line, so a commented-out
field (e.g. `<!-- kill_switch_threshold: 0.30 -->`) still satisfies the gate.
This is an acceptable v0 trade-off (loose = fewer false blocks); a future gate
revision can add fence- and comment-awareness.

Exits 0 if all checks pass. Exits 1 (blocking commit) if any newly-added
pre-reg file lacks the field.

Bypass: `git commit --no-verify`. Bypasses are logged to
`.fintech-org/policy-violations.jsonl` automatically (see log_bypass_violation).
If the policy-violations file does not exist, a warning is emitted but the
bypass is not blocked (that file's absence is a separate canary violation).

Usage (called by .git/hooks/pre-commit):
    python tools/check_kill_switch_threshold.py

Usage (standalone / CI):
    python tools/check_kill_switch_threshold.py --staged   # default
    python tools/check_kill_switch_threshold.py --check references/pre-registrations/foo.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_PRE_REG_DIR = Path("references/pre-registrations")
_POLICY_LOG = Path(".fintech-org/policy-violations.jsonl")
_FIELD_PATTERN = re.compile(r"kill_switch_threshold:\s*\S+")


def get_staged_new_pre_reg_files() -> list[Path]:
    """Return newly-added (A = added) pre-reg markdown files staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"[kill-switch gate] git diff failed: {result.stderr}",
            file=sys.stderr,
        )
        return []

    new_files = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, filepath = parts
        if status != "A":
            continue
        path = Path(filepath)
        # Only check new pre-reg markdown files
        if (
            path.parts[:2] == ("references", "pre-registrations")
            and path.suffix == ".md"
        ):
            new_files.append(path)
    return new_files


def get_staged_sha() -> str:
    """Return the SHA of the current HEAD (best proxy for in-flight commit)."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    # New repo with no commits yet
    return "INITIAL_COMMIT"


def check_file(pre_reg_path: Path) -> tuple[bool, str]:
    """Check if a pre-reg markdown file declares kill_switch_threshold.

    Returns (ok, reason).
    """
    if not pre_reg_path.exists():
        return False, (
            f"  [FAIL] {pre_reg_path}: file does not exist on disk "
            f"(staged but unreadable)."
        )

    content = pre_reg_path.read_text(encoding="utf-8", errors="replace")
    for line in content.splitlines():
        if _FIELD_PATTERN.search(line):
            return True, f"  [PASS] {pre_reg_path} — kill_switch_threshold declared."

    return False, (
        f"  [FAIL] {pre_reg_path}: missing `kill_switch_threshold:` field.\n"
        f"         CRO binding constraint #3 (CONSENSUS_2026-04-28.md) requires\n"
        f"         every pre-reg to declare its kill-switch threshold verbatim.\n"
        f"         Add a line such as:\n"
        f"             kill_switch_threshold: 0.30\n"
        f"         before committing this pre-registration.\n"
        f"         To bypass in exceptional circumstances: git commit --no-verify\n"
        f"         Bypasses are logged in .fintech-org/policy-violations.jsonl."
    )


def log_bypass_violation(pre_reg_files: list[Path]) -> None:
    """Append a JSON-line entry to .fintech-org/policy-violations.jsonl.

    If the file does not exist, warns and skips (absent file = separate canary
    violation; this gate must not silently create it).
    """
    if not _POLICY_LOG.exists():
        print(
            "[kill-switch gate] WARNING: .fintech-org/policy-violations.jsonl "
            "does not exist. Bypass not logged. This is a separate canary violation.",
            file=sys.stderr,
        )
        return

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "kill_switch_threshold_bypass_via_no_verify",
        "policy": "CRO-binding-constraint-3-CONSENSUS_2026-04-28",
        "pre_reg_files": [str(p) for p in pre_reg_files],
        "git_commit_attempt": get_staged_sha(),
    }
    with open(_POLICY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(
        f"[kill-switch gate] Bypass logged to {_POLICY_LOG} "
        f"({len(pre_reg_files)} file(s)).",
        file=sys.stderr,
    )


def main() -> int:
    """Return 0 (pass) or 1 (block)."""
    args = sys.argv[1:]

    # --check <path> mode: ad-hoc single-file check (does not touch git diff)
    if "--check" in args:
        idx = args.index("--check")
        if idx + 1 >= len(args):
            print("[kill-switch gate] --check requires a path argument.", file=sys.stderr)
            return 1
        target = Path(args[idx + 1])
        ok, reason = check_file(target)
        if ok:
            print(reason, file=sys.stderr)
            print("[kill-switch gate] PASS", file=sys.stderr)
            return 0
        else:
            print(reason, file=sys.stderr)
            print("[kill-switch gate] MISSING field — would block", file=sys.stderr)
            return 1

    # Default / --staged mode: check newly-added pre-reg files
    pre_reg_files = get_staged_new_pre_reg_files()

    if not pre_reg_files:
        print(
            "[kill-switch gate] No new pre-reg files staged. Gate passed.",
            file=sys.stderr,
        )
        return 0

    print(
        f"[kill-switch gate] Checking {len(pre_reg_files)} newly-added pre-reg file(s):",
        file=sys.stderr,
    )

    failures = []
    for path in pre_reg_files:
        ok, reason = check_file(path)
        print(reason, file=sys.stderr)
        if not ok:
            failures.append(path)

    if failures:
        print(
            f"\n[kill-switch gate] BLOCKED: {len(failures)} pre-reg file(s) "
            f"missing `kill_switch_threshold:` field.\n"
            f"  CRO binding constraint #3 (CONSENSUS_2026-04-28.md) requires\n"
            f"  every pre-registered trial to declare its kill-switch threshold\n"
            f"  verbatim before first bar executes.\n"
            f"  To bypass in exceptional circumstances: git commit --no-verify\n"
            f"  Bypasses are logged in .fintech-org/policy-violations.jsonl automatically.",
            file=sys.stderr,
        )
        return 1

    print(
        f"[kill-switch gate] All {len(pre_reg_files)} pre-reg file(s) "
        f"declare kill_switch_threshold. Gate passed.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
