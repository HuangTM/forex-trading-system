"""CRO Wave-4 + Phase-1 drawdown contract ladder.

Enforces three mandatory halt levels sourced verbatim from:
    .fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/
    cro-bet1-sizing-revision.yaml  (BC-DD-1 / BC-DD-2 / BC-DD-3)

    paper-equity DD ≥ 10%  →  halt new trial dispatch
    paper-equity DD ≥ 15%  →  reduce all sizing to 0.5x
    paper-equity DD ≥ 20%  →  full halt pending CRO review

These are NOT the KillSwitch 2% daily-loss limits — they apply to running
peak-to-trough drawdown on the paper account, independent of intra-day moves.

DO NOT modify threshold constants without a CONSENSUS amendment co-signed by
NHT + HoQR.

Clock discipline:
    No wall-clock or monotonic is needed here; drawdown is a pure equity ratio.
    The caller owns the clock (it passes equity each cycle).

Thread-safety:
    _peak_equity is protected by threading.Lock so the same DrawdownContract
    instance can be shared across threads (e.g. a monitor thread + a cycle
    thread).  In production the paper loops are single-threaded, but the lock
    costs nothing and prevents subtle bugs if the architecture evolves.

Structured-log keys emitted on every assess() call:
    event, current_equity, peak_equity, drawdown_pct, level, sizing_multiplier,
    allows_new_dispatch, [transition] (if the level changed from previous call)
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("drawdown_contract")


class DrawdownLevel(Enum):
    NORMAL = "normal"
    HALT_NEW_DISPATCH = "halt_new_dispatch"  # DD >= halt_threshold (10%)
    REDUCE_SIZING = "reduce_sizing"           # DD >= reduce_threshold (15%)
    FULL_HALT = "full_halt"                   # DD >= full_halt_threshold (20%)


@dataclass(frozen=True)
class DrawdownAssessment:
    """Immutable snapshot of the current drawdown state.

    Callers must honour:
      - allows_new_dispatch: if False, do NOT dispatch new trades.
      - sizing_multiplier: apply to all position sizes before sending.
      - level == FULL_HALT: call halt_paper_loop and exit the dispatch path.
    """

    current_equity: float
    peak_equity: float
    drawdown_pct: float         # 0.0 to 1.0; positive means drawdown from peak
    level: DrawdownLevel
    sizing_multiplier: float    # 1.0 at NORMAL/HALT_NEW; 0.5 at REDUCE_SIZING; 0.0 at FULL_HALT
    allows_new_dispatch: bool   # True only at NORMAL


# Sizing multipliers per level — sourced from CRO Wave-4 binding; no silent defaults.
_SIZING_BY_LEVEL: dict[DrawdownLevel, float] = {
    DrawdownLevel.NORMAL: 1.0,
    DrawdownLevel.HALT_NEW_DISPATCH: 1.0,   # existing positions held; no NEW dispatch
    DrawdownLevel.REDUCE_SIZING: 0.5,
    DrawdownLevel.FULL_HALT: 0.0,
}


@dataclass
class DrawdownContract:
    """Enforces the CRO Wave-4 + Phase-1 drawdown contract ladder.

    Caller passes equity each cycle via assess(); the returned DrawdownAssessment
    contains the current level and sizing_multiplier.  Caller MUST honour the
    assessment in its dispatch path — this module enforces the contract logic;
    it does NOT take action on its own.

    Construction requires explicit threshold values — no silent defaults
    (per hard rule in dispatch).

    Args:
        halt_threshold:       DD fraction at which new dispatch is halted.
                              CRO binding: 0.10 (10%).
        reduce_threshold:     DD fraction at which sizing is cut to 0.5x.
                              CRO binding: 0.15 (15%).
        full_halt_threshold:  DD fraction at which all activity halts (0.0x sizing).
                              CRO binding: 0.20 (20%).

    Example::

        contract = DrawdownContract(
            halt_threshold=0.10,
            reduce_threshold=0.15,
            full_halt_threshold=0.20,
        )
        assessment = contract.assess(current_equity=95_000.0)
        if assessment.level == DrawdownLevel.FULL_HALT:
            halt_paper_loop(reason=f"drawdown_full_halt_{assessment.drawdown_pct:.4f}")
            return SKIP_DD_FULL_HALT
        elif assessment.level == DrawdownLevel.HALT_NEW_DISPATCH:
            return SKIP_DD_HALT_NEW
        # apply sizing_multiplier to target_units downstream
    """

    halt_threshold: float        # 0.10 — caller passes; no silent default
    reduce_threshold: float      # 0.15
    full_halt_threshold: float   # 0.20

    # Internal state — peak tracks the running high-water mark.
    _peak_equity: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _last_level: DrawdownLevel = field(default=DrawdownLevel.NORMAL, init=False)

    def __post_init__(self) -> None:
        if not (0.0 < self.halt_threshold < self.reduce_threshold < self.full_halt_threshold < 1.0):
            raise ValueError(
                f"DrawdownContract thresholds must satisfy "
                f"0 < halt({self.halt_threshold}) < reduce({self.reduce_threshold}) "
                f"< full_halt({self.full_halt_threshold}) < 1.0"
            )

    def assess(self, current_equity: float) -> DrawdownAssessment:
        """Evaluate current drawdown and return a DrawdownAssessment.

        Updates the running peak if current_equity > _peak_equity.
        Classifies the drawdown into one of four DrawdownLevel values.
        Emits one structured log line per call including level transitions.

        Args:
            current_equity: The current account equity (same currency as the
                initial equity — fetched from broker each cycle).

        Returns:
            DrawdownAssessment with level, sizing_multiplier, and allows_new_dispatch.
        """
        with self._lock:
            if current_equity > self._peak_equity:
                self._peak_equity = current_equity
            peak = self._peak_equity
            previous_level = self._last_level

        if peak <= 0.0:
            # Defensive: cannot compute drawdown without a positive peak.
            # Treat as NORMAL but log a warning.
            dd_pct = 0.0
            level = DrawdownLevel.NORMAL
        else:
            dd_pct = max(0.0, (peak - current_equity) / peak)

            if dd_pct >= self.full_halt_threshold:
                level = DrawdownLevel.FULL_HALT
            elif dd_pct >= self.reduce_threshold:
                level = DrawdownLevel.REDUCE_SIZING
            elif dd_pct >= self.halt_threshold:
                level = DrawdownLevel.HALT_NEW_DISPATCH
            else:
                level = DrawdownLevel.NORMAL

        sizing_multiplier = _SIZING_BY_LEVEL[level]
        allows_new_dispatch = level == DrawdownLevel.NORMAL

        with self._lock:
            self._last_level = level

        log_extra: dict = {
            "event": "DRAWDOWN_ASSESSMENT",
            "current_equity": current_equity,
            "peak_equity": peak,
            "drawdown_pct": round(dd_pct, 6),
            "level": level.value,
            "sizing_multiplier": sizing_multiplier,
            "allows_new_dispatch": allows_new_dispatch,
            "halt_threshold": self.halt_threshold,
            "reduce_threshold": self.reduce_threshold,
            "full_halt_threshold": self.full_halt_threshold,
        }

        if level != previous_level:
            log_extra["transition"] = f"{previous_level.value} → {level.value}"
            if level == DrawdownLevel.NORMAL:
                log_level = logging.INFO
            elif level == DrawdownLevel.FULL_HALT:
                log_level = logging.CRITICAL
            else:
                log_level = logging.WARNING
            logger.log(
                log_level,
                "drawdown_level_transition %s → %s (dd=%.4f)",
                previous_level.value,
                level.value,
                dd_pct,
                extra=log_extra,
            )
        else:
            logger.debug(
                "drawdown_assessment level=%s dd=%.4f",
                level.value,
                dd_pct,
                extra=log_extra,
            )

        return DrawdownAssessment(
            current_equity=current_equity,
            peak_equity=peak,
            drawdown_pct=dd_pct,
            level=level,
            sizing_multiplier=sizing_multiplier,
            allows_new_dispatch=allows_new_dispatch,
        )
