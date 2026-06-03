"""BC-COST-RECON Option B — cumulative modeled-equity ledger + graduated alarm ladder.

CRO invariant (VETO #1):
    Drawdown / kill contracts MUST watch the broker TotalValue series (cost-inclusive
    exactly once, via real bid/ask fills). Never feed paper_equity_bt_equiv or any
    broker-minus-modeled_cost quantity into kill_switch, dd_contract.assess(), or
    _check_aggregate_drawdown — that double-counts costs the broker already charged.

Design references:
    .fintech-org/artifacts/2026-05-30T-p3-intraday-orb/  (BC-COST-RECON ratification)
    docs/specs/drawdown_ladder_amendment_2026-05-06.md

Mathematician recurrence (E_m):
    E_m(0) = E_b(0)            # seed once from initial broker equity
    E_m(t) = E_m(t-1)
             + held_engine_units(t-1) * (P(t) - P(t-1))   # unrealised P&L
             + swap_usd(t)                                  # carry credit (>0) or cost (<0)
             - cost_usd(t)                                  # transaction cost (>= 0)

where:
    held_engine_units = held_units_nom / mid   for JPY pairs  (mirrors vt.py:758)
                      = held_units_nom          for non-JPY pairs
    swap_usd is the already-computed modeled swap (from _accrue_swap / base_runner)
    cost_usd is the already-computed modeled transaction cost (spread + slippage)

On the first real-fill cycle: swap_usd = 0.0, P(t-1) is undefined → P&L term = 0.0

Persistence:
    Atomic write-then-rename to data/paper_modeled_ledger_{strategy_id}.json
    State: modeled_equity (E_m), last_mid per pair, cycle_count.
    On load after restart: resumes cumulative running total (NOT re-anchored to broker).

Residual:
    residual(t) = broker_equity(t) - E_m(t)
    Both are cumulative running curves from the same seed.

Tolerance band:
    OK if |residual| <= max(tol_abs, tol_rel * peak_broker_equity)
    Configurable via config paper.cost_reconciliation:
        tol_rel: 0.005  (0.5% of peak broker equity)
        tol_abs: 500.0  (USD absolute floor)
        reconciliation_enforce: false   (alarm-only until ≥30-50 real fills accrue)
        consecutive_breach_halt_n: 3    (N consecutive real-fill-cycle breaches → HALT-NEW)

Run-mode discriminator (MC-6 fix, CRO+ET 2026-06-01):
    run_mode is an explicit string discriminator for mock-cycle detection:
        "mock-test"  — test harness; float-sentinel check + is_mock_backend both force mock
        "sim-paper"  — Saxo SIM paper account (default for real runners)
        "live"       — reserved; not used in current codebase
    In "sim-paper" / "live" mode, broker_equity == 100_000.0 is NOT treated as mock.
    The sentinel check becomes a WARNING-only defence-in-depth log (once per ledger).
    In "mock-test" mode, all historical behaviour is preserved.

Mock-cycle guard (CRO VETO #4, updated):
    A cycle is "mock" if:
      - is_mock_backend is True (backend-identity override — test stubs), OR
      - run_mode == "mock-test" (explicit test-harness discriminator)
    In "sim-paper" / "live" mode, broker_equity == 100_000.0 is processed normally
    (not excluded). A one-time defence-in-depth WARNING is logged if the value collides.

Enforce-mode ladder (inactive by default; reconciliation_enforce: false):
    1 breach          → ALARM (structured log + ntfy; no halt)
    N consecutive     → HALT-NEW-DISPATCH (reuse SKIP_DD_HALT_NEW path; no flatten, no kill)
    single-cycle 2×   → HALT-NEW-DISPATCH + page
    Breaches NEVER call kill_switch.trigger or flatten_all.
    Measurement failure ≠ capital failure (CRO).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Run-mode discriminator (MC-6 fix — CRO+ET 2026-06-01).
# "mock-test": test harness — float-sentinel + is_mock_backend both force mock exclusion.
# "sim-paper": Saxo SIM paper account — 100_000.0 is NOT excluded (processed normally).
# "live":      reserved for future live trading; same semantics as "sim-paper".
RunMode = Literal["mock-test", "sim-paper", "live"]

# Sentinel — broker equity value that was PREVIOUSLY used as the mock discriminator.
# Kept for defence-in-depth WARNING in sim-paper/live mode (MC-6 fix: no longer excludes).
# In mock-test mode, float-equality on this value still forces mock exclusion.
_MOCK_EQUITY_SENTINEL: float = 100_000.0


@dataclass
class ReconResult:
    """Immutable result of one reconciliation cycle.

    Callers inspect .breach and .consecutive_breaches to gate dispatch.
    They must NOT modify fields after construction.
    """

    cycle_id: int
    modeled_equity: float  # E_m(t)
    broker_equity: float  # E_b(t) — raw broker TotalValue (NOT fed to kill/DD)
    residual: float  # broker_equity - modeled_equity
    tolerance: float  # effective tolerance band (abs floor or rel*peak)
    breach: bool  # |residual| > tolerance
    double_breach: bool  # |residual| > 2 * tolerance
    consecutive_breaches: int  # running count of consecutive real-fill breaches
    is_mock: bool  # True if this cycle was excluded (mock sentinel)


class ModeledEquityLedger:
    """Stateful, persisted cumulative modeled-equity ledger.

    One instance per strategy per process. Created once in main() / at startup
    and updated each real cycle. Persists state atomically so process restarts
    resume cumulative tracking (not re-anchoring to broker snapshot — that was
    the bug at vt.py:799 / carry_fred.py:771).

    Thread-safety: Not designed for multi-thread access. Paper loops are single-
    threaded; no locking provided. If the architecture evolves to multi-thread,
    add a lock around _modeled_equity / _last_mid.

    Args:
        strategy_id:    Strategy identifier for file naming (e.g. "vol_target_carry").
        tol_rel:        Relative tolerance (fraction of peak broker equity). Default 0.005.
        tol_abs:        Absolute tolerance floor (USD). Default 500.0.
        enforce:        If True, activate the halt ladder. Default False (alarm-only).
        consecutive_n:  Consecutive real-fill breaches before HALT-NEW-DISPATCH. Default 3.
        data_dir:       Directory for state files. Default "data".
        ntfy_fn:        Optional callable(title, message, priority) for notifications.
    """

    def __init__(
        self,
        strategy_id: str,
        *,
        tol_rel: float = 0.005,
        tol_abs: float = 500.0,
        enforce: bool = False,
        consecutive_n: int = 3,
        data_dir: str = "data",
        ntfy_fn=None,  # callable(title, message, priority) | None
        run_mode: RunMode = "sim-paper",
    ) -> None:
        if not strategy_id or not strategy_id.strip():
            raise ValueError("ModeledEquityLedger requires a non-empty strategy_id")
        if tol_rel < 0.0:
            raise ValueError(f"tol_rel must be >= 0.0, got {tol_rel}")
        if tol_abs < 0.0:
            raise ValueError(f"tol_abs must be >= 0.0, got {tol_abs}")
        if consecutive_n < 1:
            raise ValueError(f"consecutive_n must be >= 1, got {consecutive_n}")
        if run_mode not in ("mock-test", "sim-paper", "live"):
            raise ValueError(
                f"run_mode must be 'mock-test', 'sim-paper', or 'live'; got {run_mode!r}"
            )

        self.strategy_id = strategy_id
        self.tol_rel = tol_rel
        self.tol_abs = tol_abs
        self.enforce = enforce
        self.consecutive_n = consecutive_n
        self._data_dir = data_dir
        self._ntfy_fn = ntfy_fn
        self.run_mode: RunMode = run_mode

        # Running state — initialised to None until seed() is called.
        self._modeled_equity: Optional[float] = None
        self._last_mid: dict[str, float] = {}  # per-pair last mid price
        self._cycle_count: int = 0  # total update() calls (including mock)
        self._real_cycle_count: int = 0  # real-fill cycles only
        self._peak_broker_equity: float = 0.0  # real-fill cycles only (VETO #4)
        self._consecutive_breaches: int = 0  # real-fill consecutive breach counter
        # Defence-in-depth: warn once when sim-paper sees 100_000.0 (log once per instance).
        self._sentinel_warning_emitted: bool = False

        # Try to load persisted state; if missing, wait for seed().
        self._load()

    # ---------------------------------------------------------------------------
    # State file path
    # ---------------------------------------------------------------------------

    def _state_path(self) -> Path:
        """Canonical state file path for this strategy's ledger."""
        safe_id = self.strategy_id.replace("/", "_").replace(" ", "_")
        return Path(self._data_dir) / f"paper_modeled_ledger_{safe_id}.json"

    # ---------------------------------------------------------------------------
    # Persistence — atomic write-then-rename (mirrors base_runner.persist_last_cycle_ts)
    # ---------------------------------------------------------------------------

    def _save(self) -> None:
        """Persist ledger state atomically (write-then-rename)."""
        if self._modeled_equity is None:
            # Not yet seeded — nothing to save.
            return
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "strategy_id": self.strategy_id,
            "modeled_equity": self._modeled_equity,
            "last_mid": dict(self._last_mid),
            "cycle_count": self._cycle_count,
            "real_cycle_count": self._real_cycle_count,
            "peak_broker_equity": self._peak_broker_equity,
            "consecutive_breaches": self._consecutive_breaches,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=path.parent,
                prefix=f".paper_modeled_ledger_{self.strategy_id}_tmp_",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(payload, f)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            logger.debug(
                "cost_recon.save strategy_id=%s modeled_equity=%.4f path=%s",
                self.strategy_id,
                self._modeled_equity,
                str(path),
            )
        except OSError as exc:
            logger.warning(
                "cost_recon.save strategy_id=%s outcome=WRITE_ERROR exc=%s path=%s",
                self.strategy_id,
                repr(exc),
                str(path),
                extra={
                    "event": "COST_RECON_SAVE_ERROR",
                    "strategy_id": self.strategy_id,
                    "path": str(path),
                    "exc": repr(exc),
                },
            )

    def _load(self) -> None:
        """Load persisted ledger state. Silent on missing file (first run)."""
        path = self._state_path()
        if not path.exists():
            logger.debug(
                "cost_recon.load strategy_id=%s outcome=NO_FILE — will seed on first update",
                self.strategy_id,
            )
            return
        try:
            payload = json.loads(path.read_text())
            self._modeled_equity = float(payload["modeled_equity"])
            self._last_mid = {k: float(v) for k, v in payload.get("last_mid", {}).items()}
            self._cycle_count = int(payload.get("cycle_count", 0))
            self._real_cycle_count = int(payload.get("real_cycle_count", 0))
            self._peak_broker_equity = float(payload.get("peak_broker_equity", 0.0))
            self._consecutive_breaches = int(payload.get("consecutive_breaches", 0))
            logger.info(
                "cost_recon.load strategy_id=%s outcome=OK modeled_equity=%.4f "
                "real_cycles=%d peak_broker=%.4f",
                self.strategy_id,
                self._modeled_equity,
                self._real_cycle_count,
                self._peak_broker_equity,
                extra={
                    "event": "COST_RECON_LOAD_OK",
                    "strategy_id": self.strategy_id,
                    "modeled_equity": self._modeled_equity,
                    "real_cycle_count": self._real_cycle_count,
                    "peak_broker_equity": self._peak_broker_equity,
                    "path": str(path),
                },
            )
        except (KeyError, ValueError, json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "cost_recon.load strategy_id=%s outcome=PARSE_ERROR exc=%s — "
                "will seed on first update",
                self.strategy_id,
                repr(exc),
                extra={
                    "event": "COST_RECON_LOAD_ERROR",
                    "strategy_id": self.strategy_id,
                    "path": str(path),
                    "exc": repr(exc),
                },
            )
            # Reset to clean state so seed() works correctly.
            self._modeled_equity = None
            self._last_mid = {}
            self._cycle_count = 0
            self._real_cycle_count = 0
            self._peak_broker_equity = 0.0
            self._consecutive_breaches = 0

    # ---------------------------------------------------------------------------
    # Public: seed (once, on first run or after state deletion)
    # ---------------------------------------------------------------------------

    def seed(self, initial_broker_equity: float, pair: str, mid: float) -> None:
        """Seed the ledger: E_m(0) = E_b(0).

        Called once at startup with the first broker equity snapshot and the
        current mid price. Skipped if state was already loaded from disk.

        Args:
            initial_broker_equity: First broker TotalValue (USD). Must be > 0.
            pair: The primary pair for this strategy (used to init last_mid).
            mid: Current mid price for pair.
        """
        if self._modeled_equity is not None:
            logger.debug(
                "cost_recon.seed strategy_id=%s outcome=ALREADY_SEEDED modeled_equity=%.4f",
                self.strategy_id,
                self._modeled_equity,
            )
            return
        if initial_broker_equity <= 0:
            raise ValueError(
                f"ModeledEquityLedger.seed: initial_broker_equity must be > 0, "
                f"got {initial_broker_equity}"
            )
        self._modeled_equity = initial_broker_equity
        self._last_mid[pair.upper()] = mid
        logger.info(
            "cost_recon.seed strategy_id=%s modeled_equity=%.4f pair=%s mid=%.6f",
            self.strategy_id,
            self._modeled_equity,
            pair,
            mid,
            extra={
                "event": "COST_RECON_SEEDED",
                "strategy_id": self.strategy_id,
                "modeled_equity": self._modeled_equity,
                "pair": pair,
                "mid": mid,
            },
        )
        self._save()

    # ---------------------------------------------------------------------------
    # Mock-cycle detection (CRO VETO #4)
    # ---------------------------------------------------------------------------

    @staticmethod
    def is_mock_cycle(
        broker_equity: float,
        *,
        is_mock_backend: bool = False,
        run_mode: RunMode = "sim-paper",
    ) -> bool:
        """Return True if this cycle should be excluded from residual + peak tracking.

        MC-6 fix (CRO+ET 2026-06-01): mock determination is now run_mode-gated.

        A cycle is mock if:
          - is_mock_backend is True (backend-identity override: test stubs), OR
          - run_mode == "mock-test" (explicit test-harness discriminator)

        In "sim-paper" / "live" mode, broker_equity == 100_000.0 is NO LONGER treated
        as mock — the float-equality sentinel check is removed as a decision gate.
        See ModeledEquityLedger.update() for the defence-in-depth WARNING that fires
        (once per ledger instance) when sim-paper sees 100_000.0.

        Args:
            broker_equity: Raw broker TotalValue for this cycle.
            is_mock_backend: True if the execution backend is a mock/test backend
                (derived from backend.is_mock — see ExecutionBackend.is_mock property).
            run_mode: Explicit run-mode discriminator. Default "sim-paper" (real runner).
                Pass "mock-test" for test harnesses (preserves historical exclusion logic).

        Returns:
            True if this cycle is mock and should be excluded.
        """
        # is_mock_backend is always authoritative (backend-identity override).
        if is_mock_backend:
            return True
        # In mock-test mode: float-sentinel check is ACTIVE (preserves legacy test behaviour).
        # In sim-paper / live mode: float-sentinel check is DISABLED (MC-6 fix — the Saxo
        # SIM paper account also seeds at 100_000.0; float-equality cannot distinguish it
        # from a test mock).
        if run_mode == "mock-test" and broker_equity == _MOCK_EQUITY_SENTINEL:
            return True
        return False

    # ---------------------------------------------------------------------------
    # Public: update — called each cycle (real or mock)
    # ---------------------------------------------------------------------------

    def update(
        self,
        pair: str,
        mid_now: float,
        held_units_nom: float,
        cost_usd: float,
        swap_usd: float,
        broker_equity: float,
        *,
        is_mock_backend: bool = False,
        cycle_id: Optional[int] = None,
        run_mode: Optional[RunMode] = None,
    ) -> ReconResult:
        """Apply one cycle of the Mathematician recurrence and compute residual.

        The ledger is updated unconditionally (E_m advances each cycle). However,
        residual tolerance checking and peak tracking are ONLY applied on real-fill
        cycles (mock cycles excluded per CRO VETO #4).

        Recurrence:
            held_engine_units = held_units_nom / mid_prev   (JPY pairs)
                              = held_units_nom               (non-JPY pairs)
            pnl_usd = held_engine_units * (mid_now - mid_prev)
            E_m(t)  = E_m(t-1) + pnl_usd + swap_usd - cost_usd

        On first real cycle after seed: mid_prev = seed mid; pnl_usd = 0 when
        mid_now == mid_prev (same cycle as seed). swap_usd = 0.0 on first cycle.

        Args:
            pair:             Currency pair (e.g. "USDJPY").
            mid_now:          Current mid price.
            held_units_nom:   USD-nominal held position BEFORE this cycle's action
                              (i.e. what was held last cycle — same semantics as
                              engine.py:313 cur_units and vt.py:758).
            cost_usd:         Modeled transaction cost this cycle (>= 0).
            swap_usd:         Modeled swap credit/debit (positive = carry income).
            broker_equity:    Raw broker TotalValue for this cycle. Used only for
                              residual and peak tracking; NOT fed to kill/DD.
            is_mock_backend:  True if backend is mock/test (VETO #4 exclusion).
            cycle_id:         Optional cycle counter for observability logging.
            run_mode:         Explicit run-mode override for this call. If None,
                              falls back to self.run_mode set at construction.
                              Callers may pass "mock-test" to force mock-exclusion.

        Returns:
            ReconResult with modeled_equity, residual, breach flags, and mock flag.

        Raises:
            RuntimeError: if seed() was not called and no persisted state exists.

        Note (F2): Cycles that skip before reaching this call (e.g. SKIP_DD_HALT_NEW,
        SKIP_KILL_SWITCH, SKIP_AGGREGATE_DD_LOCKOUT) do NOT advance the ledger mid
        price (_last_mid). This means the P&L term for the next real-fill cycle will
        use the mid from the last cycle that DID reach update(), not the skipped
        cycle's price — acceptable in alarm-only mode (reconciliation_enforce=False)
        where measurement drift does not trigger dispatch decisions. Revisit before
        enabling enforce-mode: consider calling update() with cost_usd=0 on every
        cycle (including skipped ones) so mid tracks the live price continuously.
        """
        pair = pair.upper()

        if self._modeled_equity is None:
            raise RuntimeError(
                f"ModeledEquityLedger for strategy_id={self.strategy_id!r} has not been seeded. "
                "Call seed() with the initial broker equity before the first update()."
            )

        self._cycle_count += 1
        effective_run_mode: RunMode = run_mode if run_mode is not None else self.run_mode
        is_mock = self.is_mock_cycle(
            broker_equity,
            is_mock_backend=is_mock_backend,
            run_mode=effective_run_mode,
        )

        # Defence-in-depth WARNING (MC-6 fix): when sim-paper/live sees 100_000.0,
        # log once per ledger instance. The cycle is NOT excluded — only logged.
        if (
            not is_mock
            and effective_run_mode != "mock-test"
            and broker_equity == _MOCK_EQUITY_SENTINEL
            and not self._sentinel_warning_emitted
        ):
            self._sentinel_warning_emitted = True
            logger.warning(
                "cost_recon.sentinel_collision strategy_id=%s cycle_id=%s "
                "broker_equity exactly equals legacy mock sentinel (%.1f); "
                "NOT excluding because run_mode=%s — processing cycle normally",
                self.strategy_id,
                cycle_id,
                _MOCK_EQUITY_SENTINEL,
                effective_run_mode,
                extra={
                    "event": "COST_RECON_SENTINEL_COLLISION",
                    "strategy_id": self.strategy_id,
                    "cycle_id": cycle_id,
                    "broker_equity": broker_equity,
                    "run_mode": effective_run_mode,
                    "decision": "not_excluding_sentinel_in_sim_paper_mode",
                },
            )

        # --- Step 1: Compute unrealised P&L from held position ---
        # F3: The Mathematician recurrence assumes long-only (held_units_nom >= 0).
        # Both current strategies (vol_target_carry, carry_fred) are long-only.
        # A short-capable strategy needs signed units and a directional P&L term:
        #   pnl_usd = held_engine_units * direction_sign * (mid_now - mid_prev)
        # Revisit before enabling any short-capable strategy.
        assert held_units_nom >= 0, (
            "F3: ModeledEquityLedger recurrence is long-only; "
            f"received held_units_nom={held_units_nom:.4f} < 0. "
            "Short-capable strategies require a directional P&L term."
        )
        mid_prev = self._last_mid.get(pair)
        is_jpy = "JPY" in pair
        if mid_prev is not None and mid_prev > 0 and held_units_nom > 0:
            # Convert USD-nominal → engine-units (mirrors vt.py:758 / base_runner.py:575-588)
            held_engine_units = (held_units_nom / mid_prev) if is_jpy else held_units_nom
            pnl_usd = held_engine_units * (mid_now - mid_prev)
        else:
            # First real cycle after seed, or flat position: no P&L
            pnl_usd = 0.0
            held_engine_units = 0.0

        # --- Step 2: Apply recurrence ---
        prev_modeled = self._modeled_equity
        self._modeled_equity = prev_modeled + pnl_usd + swap_usd - cost_usd

        # --- Step 3: Advance last_mid ---
        self._last_mid[pair] = mid_now

        # --- Step 4: Compute residual; update peak and breach counters (real only) ---
        residual = broker_equity - self._modeled_equity

        if not is_mock:
            self._real_cycle_count += 1
            if broker_equity > self._peak_broker_equity:
                self._peak_broker_equity = broker_equity

        peak = self._peak_broker_equity
        tolerance = max(self.tol_abs, self.tol_rel * peak) if peak > 0 else self.tol_abs
        breach = (abs(residual) > tolerance) and not is_mock
        double_breach = (abs(residual) > 2.0 * tolerance) and not is_mock

        if not is_mock:
            if breach:
                self._consecutive_breaches += 1
            else:
                self._consecutive_breaches = 0

        consecutive = self._consecutive_breaches

        # --- Step 5: Emit structured log ---
        log_extra: dict = {
            "event": "COST_RECON_UPDATE",
            "strategy_id": self.strategy_id,
            "cycle_id": cycle_id,
            "pair": pair,
            "is_mock": is_mock,
            "modeled_equity": round(self._modeled_equity, 4),
            "broker_equity": round(broker_equity, 4),
            "residual": round(residual, 4),
            "tolerance": round(tolerance, 4),
            "breach": breach,
            "double_breach": double_breach,
            "consecutive_breaches": consecutive,
            "pnl_usd": round(pnl_usd, 4),
            "swap_usd": round(swap_usd, 4),
            "cost_usd": round(cost_usd, 4),
            "held_units_nom": round(held_units_nom, 4),
            "mid_prev": round(mid_prev, 6) if mid_prev is not None else None,
            "mid_now": round(mid_now, 6),
        }
        logger.debug(
            "cost_recon cycle_id=%s pair=%s E_m=%.4f E_b=%.4f residual=%.4f "
            "breach=%s consecutive=%d is_mock=%s",
            cycle_id,
            pair,
            self._modeled_equity,
            broker_equity,
            residual,
            breach,
            consecutive,
            is_mock,
            extra=log_extra,
        )

        # --- Step 6: Alarm / ladder ---
        if breach and not is_mock:
            self._handle_breach(
                broker_equity=broker_equity,
                modeled_equity=self._modeled_equity,
                residual=residual,
                tolerance=tolerance,
                cycle_id=cycle_id,
                consecutive=consecutive,
                double_breach=double_breach,
            )

        # --- Step 7: Persist ---
        self._save()

        return ReconResult(
            cycle_id=cycle_id if cycle_id is not None else self._cycle_count,
            modeled_equity=self._modeled_equity,
            broker_equity=broker_equity,
            residual=residual,
            tolerance=tolerance,
            breach=breach,
            double_breach=double_breach,
            consecutive_breaches=consecutive,
            is_mock=is_mock,
        )

    # ---------------------------------------------------------------------------
    # Alarm / ladder implementation
    # ---------------------------------------------------------------------------

    def _handle_breach(
        self,
        *,
        broker_equity: float,
        modeled_equity: float,
        residual: float,
        tolerance: float,
        cycle_id: Optional[int],
        consecutive: int,
        double_breach: bool,
    ) -> None:
        """Emit alarm + optional ladder action on a reconciliation breach.

        Alarm-only mode (enforce=False, default):
            All breaches emit WARNING log + ntfy. No halt, no flatten.

        Enforce mode (enforce=True):
            consecutive >= N       → HALT-NEW-DISPATCH (log CRITICAL; caller checks result)
            double_breach          → HALT-NEW-DISPATCH + page (single-cycle 2× tolerance)
            1 breach               → WARNING log + ntfy (same as alarm-only)

        Breaches NEVER call kill_switch.trigger or flatten_all.
        Measurement failure ≠ capital failure (CRO).
        """
        breach_extra: dict = {
            "event": "COST_RECON_DIVERGENCE",
            "strategy_id": self.strategy_id,
            "cycle_id": cycle_id,
            "broker_equity": round(broker_equity, 4),
            "modeled_equity": round(modeled_equity, 4),
            "residual": round(residual, 4),
            "tolerance": round(tolerance, 4),
            "consecutive_breaches": consecutive,
            "double_breach": double_breach,
            "enforce_mode": self.enforce,
        }

        # Always emit ALARM WARNING
        logger.warning(
            "COST_RECON_DIVERGENCE strategy_id=%s cycle_id=%s broker_equity=%.4f "
            "modeled_equity=%.4f residual=%.4f tolerance=%.4f consecutive=%d",
            self.strategy_id,
            cycle_id,
            broker_equity,
            modeled_equity,
            residual,
            tolerance,
            consecutive,
            extra=breach_extra,
        )

        # ntfy notification (non-fatal; errors swallowed)
        if self._ntfy_fn is not None:
            try:
                self._ntfy_fn(
                    f"COST_RECON_DIVERGENCE [{self.strategy_id}]",
                    (
                        f"residual={residual:.2f} tolerance={tolerance:.2f} "
                        f"consecutive={consecutive}"
                    ),
                    "high"
                    if double_breach or (self.enforce and consecutive >= self.consecutive_n)
                    else "default",
                )
            except Exception as _ntfy_exc:
                logger.debug("cost_recon.ntfy_fn raised: %s", repr(_ntfy_exc))

        if not self.enforce:
            return  # alarm-only mode — done

        # Enforce-mode ladder
        if double_breach:
            logger.critical(
                "COST_RECON_DOUBLE_BREACH_HALT_NEW strategy_id=%s cycle_id=%s "
                "residual=%.4f 2×tolerance=%.4f — HALT-NEW-DISPATCH (measurement failure, "
                "NOT capital failure; no flatten)",
                self.strategy_id,
                cycle_id,
                residual,
                2.0 * tolerance,
                extra={**breach_extra, "event": "COST_RECON_DOUBLE_BREACH_HALT_NEW"},
            )
        elif consecutive >= self.consecutive_n:
            logger.critical(
                "COST_RECON_CONSECUTIVE_BREACH_HALT_NEW strategy_id=%s cycle_id=%s "
                "consecutive=%d >= N=%d — HALT-NEW-DISPATCH (measurement failure, "
                "NOT capital failure; no flatten)",
                self.strategy_id,
                cycle_id,
                consecutive,
                self.consecutive_n,
                extra={**breach_extra, "event": "COST_RECON_CONSECUTIVE_BREACH_HALT_NEW"},
            )

    # ---------------------------------------------------------------------------
    # Query: should_halt_new_dispatch — checked by caller each cycle
    # ---------------------------------------------------------------------------

    def should_halt_new_dispatch(self) -> bool:
        """Return True if enforce-mode ladder has escalated to HALT-NEW-DISPATCH.

        Callers (run_cycle) check this AFTER update() and reuse the existing
        SKIP_DD_HALT_NEW path (no flatten, no kill-switch trigger).

        Returns False in alarm-only mode (self.enforce == False) regardless of
        breach count.
        """
        if not self.enforce:
            return False
        return (
            self._consecutive_breaches >= self.consecutive_n
            # Double-breach is handled per-call in update(); consecutive counter
            # resets on a clean cycle so caller can also check last ReconResult.
        )

    # ---------------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------------

    @property
    def modeled_equity(self) -> Optional[float]:
        """Current E_m value (None if not yet seeded)."""
        return self._modeled_equity

    @property
    def real_cycle_count(self) -> int:
        """Number of real-fill (non-mock) cycles processed."""
        return self._real_cycle_count

    @property
    def consecutive_breaches(self) -> int:
        """Current consecutive-breach counter (real cycles only)."""
        return self._consecutive_breaches

    @property
    def peak_broker_equity(self) -> float:
        """Running high-water mark of broker equity (real cycles only)."""
        return self._peak_broker_equity


# ---------------------------------------------------------------------------
# Factory: from_config
# ---------------------------------------------------------------------------


def ledger_from_config(
    strategy_id: str,
    config: dict,
    ntfy_fn=None,
    run_mode: RunMode = "sim-paper",
) -> ModeledEquityLedger:
    """Construct a ModeledEquityLedger from the loaded config dict.

    Reads from config['paper']['cost_reconciliation']:
        tol_rel:                    0.005
        tol_abs:                    500.0
        reconciliation_enforce:     false
        consecutive_breach_halt_n:  3

    Falls back to spec defaults if config keys are absent.

    Args:
        strategy_id: Strategy identifier.
        config: The full loaded config dict (from load_config or as dict).
        ntfy_fn: Optional notification callable.
        run_mode: Run-mode discriminator — "sim-paper" for real runners (default),
            "mock-test" for test harnesses. Passed through to ModeledEquityLedger.

    Returns:
        Configured ModeledEquityLedger instance (state loaded from disk if present).
    """
    # F4: production always passes a plain dict (load_config returns dict).
    # The dataclass-branch is unreachable in the current codebase and has been removed.
    raw: dict = (config or {}).get("paper", {}) if isinstance(config, dict) else {}
    recon_cfg: dict = raw.get("cost_reconciliation", {}) if isinstance(raw, dict) else {}

    tol_rel = float(recon_cfg.get("tol_rel", 0.005))
    tol_abs = float(recon_cfg.get("tol_abs", 500.0))
    enforce = bool(recon_cfg.get("reconciliation_enforce", False))
    consecutive_n = int(recon_cfg.get("consecutive_breach_halt_n", 3))

    return ModeledEquityLedger(
        strategy_id=strategy_id,
        tol_rel=tol_rel,
        tol_abs=tol_abs,
        enforce=enforce,
        consecutive_n=consecutive_n,
        ntfy_fn=ntfy_fn,
        run_mode=run_mode,
    )
