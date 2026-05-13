"""REM-4 config dispatch-stagger acceptance tests.

Covers:
    REM-4-T1: stagger offsets are unique within a bar-close window and no
              offset shifts dispatch past the bar-close tolerance.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"

# Tolerance: stagger offsets must not shift any strategy dispatch past
# 5 minutes (300s) of the bar-close window.
BAR_CLOSE_TOLERANCE_SECONDS = 300
# Base interval (same as --interval default in paper scripts)
BASE_INTERVAL_SECONDS = 1800


def _load_stagger_offsets() -> list[int]:
    """Load paper.dispatch_stagger_offsets_seconds from config/default.yaml."""
    assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    paper = cfg.get("paper", {})
    offsets = paper.get("dispatch_stagger_offsets_seconds")
    assert offsets is not None, (
        "paper.dispatch_stagger_offsets_seconds key missing from config/default.yaml "
        "(REM-4 / D-4.1 not applied)"
    )
    return offsets


class TestRem4StaggerConfig:
    """REM-4-T1: stagger uniqueness and bar-close window compliance."""

    def test_stagger_key_exists(self) -> None:
        """Config contains the required stagger key."""
        offsets = _load_stagger_offsets()
        assert isinstance(offsets, list), "dispatch_stagger_offsets_seconds must be a list"
        assert len(offsets) >= 2, "Must have at least 2 stagger offsets (minimum 2 strategies)"

    def test_stagger_offsets_are_unique(self) -> None:
        """No two strategies share the same dispatch second within one 1800s interval.

        REM-4-T1 first assertion: unique offsets prevent burst collisions at bar-close.
        """
        offsets = _load_stagger_offsets()
        assert len(offsets) == len(set(offsets)), (
            f"Stagger offsets are not unique: {offsets}. "
            "Two strategies would dispatch at the same second (REM-4-T1)."
        )

    def test_stagger_offsets_within_bar_close_tolerance(self) -> None:
        """All offsets fit within ±5 minutes of the bar-close window.

        REM-4-T1 second assertion: offsets must not push any strategy's dispatch
        past 300s after the base interval, otherwise the dispatch is effectively
        in the NEXT bar-close window.
        """
        offsets = _load_stagger_offsets()
        for i, offset in enumerate(offsets):
            assert 0 <= offset < BAR_CLOSE_TOLERANCE_SECONDS, (
                f"Strategy at index {i} has offset {offset}s which exceeds the "
                f"bar-close window tolerance ({BAR_CLOSE_TOLERANCE_SECONDS}s). "
                "This would shift the dispatch into the next bar-close window (REM-4-T1)."
            )

    def test_stagger_count_covers_four_strategies(self) -> None:
        """Config has offsets for at least 4 strategies (the N=4 target architecture)."""
        offsets = _load_stagger_offsets()
        assert len(offsets) >= 4, (
            f"dispatch_stagger_offsets_seconds has {len(offsets)} entries; "
            "expected >= 4 for the N=4 strategy target (REM-4 / D-4.1)."
        )

    def test_stagger_offsets_are_non_negative(self) -> None:
        """All offsets are non-negative (no strategy dispatches before bar-close)."""
        offsets = _load_stagger_offsets()
        for i, offset in enumerate(offsets):
            assert offset >= 0, (
                f"Stagger offset at index {i} is negative ({offset}s). "
                "Negative offsets dispatch BEFORE bar-close — lookahead violation risk."
            )
