"""Forward-harness tests — P1 acceptance suite.

Covers:
  - test_hash_mismatch_voids             — tampered config -> VOID + sys.exit(1) (IC-3/IC-14a)
  - test_m2_pre_freeze_bar_voids         — single pre-freeze bar in M2 window -> VOID (IC-2)
  - test_m1_blocked_for_unattested_family — M1 for full-history family -> REFUSE (M1 gate / KG-4)
  - test_clean_m2_forward_eval           — clean M2 forward eval -> a proper verdict (FALSIFIED is
                                           expected at zero-return data; no lookahead bugs)
  - test_ic9_uses_honest_n_30            — honest_n_deflation_denominator() == 30 (IC-9/IC-14d)
  - test_one_shot_burned_refuses         — second open of burned window -> RuntimeError (IC-6)
  - test_void_after_data_burns_n         — VOID after forward bars loaded -> counts_toward=True (IC-7)
  - test_forward_attempt_counts_n        — clean forward eval appends counts_toward=True trial (IC-7)

The sacred test (test_no_lookahead) lives in tests/backtest/test_engine.py and is
verified separately (see CI command in CLAUDE.md). It must remain green.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_prereg(tmp_path: Path, name: str = "test_strategy") -> tuple[Path, Path]:
    """Write a minimal pre-reg .md + .triggers.yaml pair."""
    md = tmp_path / f"{name}.md"
    triggers = tmp_path / f"{name}.triggers.yaml"
    md.write_text(textwrap.dedent(f"""
        **Strategy ID:** {name}
        **Pair:** EURUSD

        kill_switch_threshold: 0.30

        ## Hypothesis
        Test hypothesis for forward harness tests.

        ## Gates
        - KILL-0: min events gate
        - KILL-DSR: DSR gate
    """))
    triggers.write_text(textwrap.dedent("""
        oos_overlap: false
        oos_window_start: "2024-01-01"
        oos_window_end: "2024-12-31"
        pair: EURUSD
        triggers:
          - label: KILL-0
            metric: n_realized
            operator: "<"
            threshold: 1
          - label: KILL-SHARPE
            metric: net_sharpe
            operator: "<"
            threshold: 0.30
    """))
    return md, triggers


def _make_config(tmp_path: Path) -> Path:
    """Write a minimal YAML config matching the real project config format."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent("""
        system:
          name: "test-config"
          log_level: "WARNING"

        data:
          base_dir: "data"

        pairs:
          - symbol: EURUSD
            pip_value: 0.0001
            spread_pips: 0.5
            slippage_pips: 0.5
            commission_pips: 0.5
            swap_long_pips_per_day: -1.2
            swap_short_pips_per_day: 0.3

        strategies:
          active:
            - ma_crossover
          ma_crossover:
            fast_period: 10
            slow_period: 30

        backtest:
          initial_capital: 10000.0
          position_sizing:
            risk_per_trade: 0.01
            stop_loss_atr_multiple: 2.0
            max_position_pct: 0.10
          execution:
            entry_delay_bars: 1
            rebalance_mode: discrete
            rebalance_threshold: 0.20
            allow_shorts: false
          walkforward:
            enabled: false
            train_window_days: 504
            test_window_days: 126
            step_days: 63
    """))
    return config_path


def _make_ohlcv(
    n_bars: int = 50,
    start: str = "2025-01-01",
    freq: str = "D",
    tz: str = "UTC",
) -> pd.DataFrame:
    """Produce a minimal OHLCV DataFrame for testing."""
    index = pd.date_range(start=start, periods=n_bars, freq=freq, tz=tz)
    import numpy as np
    np.random.seed(42)
    close = 1.1 + np.cumsum(np.random.normal(0, 0.001, n_bars))
    high = close + abs(np.random.normal(0, 0.0005, n_bars))
    low = close - abs(np.random.normal(0, 0.0005, n_bars))
    open_ = close + np.random.normal(0, 0.0003, n_bars)
    volume = np.ones(n_bars) * 1000.0
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=index)


def _freeze_minimal(
    tmp_path: Path,
    prereg_path: Path,
    config_path: Path,
    mechanism: str = "M2",
    custody: str = "nht",
    registry: Path | None = None,
    dev_attestation_registry: Path | None = None,
) -> str:
    """Call freeze_structure and return the freeze_id."""
    from forex_system.harness.freeze import freeze_structure

    reg = registry or (tmp_path / "forward_registry.jsonl")
    attest_reg = dev_attestation_registry or (tmp_path / "dev_start_attestations.jsonl")

    record = freeze_structure(
        prereg_path=prereg_path,
        config_path=config_path,
        mechanism=mechanism,
        custody=custody,
        registry=reg,
        attestation_registry=attest_reg,
    )
    return record.freeze_id


# ---------------------------------------------------------------------------
# IC-9: honest_n_deflation_denominator returns 30
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Locate the repo root by walking up to the directory containing pyproject.toml.

    Makes the live-ledger pin (test_ic9_uses_honest_n_30) independent of the cwd
    at test-execution time (critic finding — relative-path brittleness fixed).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate repo root (no pyproject.toml found above test file).")


def test_ic9_uses_honest_n_30() -> None:
    """IC-9 / IC-14d: honest_n_deflation_denominator() must return 30 (ratified N).

    DELIBERATE LIVE-LEDGER PIN: asserts the production ledger
    (.fintech-org/trials.jsonl) yields the ratified value 30 — NOT a raw line
    count (49), NOT the de-dup families (11), NOT the retired prose counter (48).
    The path is anchored to the repo root (not cwd-relative) so the test is
    location-independent. If the production ledger legitimately changes (a new
    counting trial is appended), this pin must be updated alongside the
    'honest-n-classification' record — that coupling is intentional: the DSR
    denominator is a ratified quantity and must not drift silently.
    """
    from forex_system.harness.honest_n import honest_n_deflation_denominator
    ledger = _repo_root() / ".fintech-org" / "trials.jsonl"
    n = honest_n_deflation_denominator(ledger)
    assert n == 30, (
        f"honest_n_deflation_denominator() returned {n}, expected 30 (ratified 2026-06-18). "
        "This is an IC-9 / IC-14d violation: the DSR denominator must be mechanically derived "
        "from the ledger and match the ratified value. "
        f"Check {ledger} for the 'honest-n-classification' record."
    )


# ---------------------------------------------------------------------------
# IC-3 / IC-14a: hash mismatch -> VOID + sys.exit(1)
# ---------------------------------------------------------------------------


def test_hash_mismatch_voids(tmp_path: Path) -> None:
    """Tamper one byte of config after freeze -> forward_evaluate VOIDS + exits non-zero (IC-3/IC-14a)."""
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"

    # Seed trials.jsonl with a classification record so honest_n can run.
    _seed_trials_with_classification(trials_registry)

    freeze_id = _freeze_minimal(
        tmp_path, prereg_path, config_path,
        registry=registry,
    )

    # Tamper the config AFTER freeze.
    config_path.write_text(config_path.read_text() + "\n# tampered\n")

    bars = _make_ohlcv(start="2026-01-01")

    from forex_system.harness import forward_eval as fe

    with pytest.raises(SystemExit) as exc_info:
        fe.forward_evaluate(
            freeze_id=freeze_id,
            forward_bars=bars,
            pair="EURUSD",
            config_path=config_path,
            prereq_path=prereg_path,
            registry=registry,
            trials_registry=trials_registry,
        )
    assert exc_info.value.code == 1, "Hash mismatch must exit with code 1 (IC-14a)."

    # VOID result should be written to forward_registry.
    records = _read_registry(registry)
    result_records = [r for r in records if r.get("record_type") == "forward-result"]
    assert result_records, "A VOID forward-result record must be written even on hash mismatch."
    assert result_records[0]["verdict"] == "VOID"
    assert not result_records[0]["integrity_ok"]


# ---------------------------------------------------------------------------
# IC-2: M2 pre-freeze bar -> VOID
# ---------------------------------------------------------------------------


def test_m2_pre_freeze_bar_voids(tmp_path: Path) -> None:
    """A single pre-freeze bar in M2 scored set -> VOID (IC-2)."""
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"
    _seed_trials_with_classification(trials_registry)

    freeze_id = _freeze_minimal(tmp_path, prereg_path, config_path, registry=registry)

    # Load the freeze record to get freeze_utc.
    # Build bars: all post-freeze, but inject ONE pre-freeze bar at the front.
    post_bars = _make_ohlcv(n_bars=40, start="2026-07-01")
    pre_bar = _make_ohlcv(n_bars=1, start="2020-01-01")  # clearly pre-freeze
    bars = pd.concat([pre_bar, post_bars]).sort_index()

    from forex_system.harness import forward_eval as fe
    result = fe.forward_evaluate(
        freeze_id=freeze_id,
        forward_bars=bars,
        pair="EURUSD",
        config_path=config_path,
        prereq_path=prereg_path,
        registry=registry,
        trials_registry=trials_registry,
    )

    assert result.verdict == "VOID", "Pre-freeze bar in M2 window must produce VOID."
    assert result.void_after_data, "void_after_data must be True (data was loaded; IC-7)."
    assert not result.integrity_ok or "pre_freeze_bar" in result.hash_mismatch_detail.lower() or "pre-freeze" in result.hash_mismatch_detail.lower()

    # VOID-after-data must still burn N (IC-7).
    _assert_trial_counts_toward_n(trials_registry, result.trial_id)


# ---------------------------------------------------------------------------
# M1 hard block for unattested family (M1 gate / KG-4 / CTO P1)
# ---------------------------------------------------------------------------


def test_m1_blocked_for_unattested_family(tmp_path: Path) -> None:
    """M1 freeze for a family with no development_start_attestation -> REFUSE (ValueError)."""
    prereg_path, _ = _make_prereg(tmp_path, name="h1_session_open_momentum_pooled")
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    # No attestation registry -> empty (no attestations for this family).
    attest_reg = tmp_path / "dev_start_attestations.jsonl"
    # Do NOT create the attestation file -> family has no attestation.

    from forex_system.harness.freeze import freeze_structure

    with pytest.raises(ValueError, match="no_development_start_attestation|M1 freeze REFUSED"):
        freeze_structure(
            prereg_path=prereg_path,
            config_path=config_path,
            mechanism="M1",
            custody="nht",
            registry=registry,
            attestation_registry=attest_reg,
        )

    # No freeze record should have been written.
    assert not registry.exists() or _read_registry(registry) == [], (
        "M1 REFUSE must not write any freeze record to the registry."
    )


# ---------------------------------------------------------------------------
# Clean M2 forward eval -> a proper verdict
# ---------------------------------------------------------------------------


def test_clean_m2_forward_eval(tmp_path: Path) -> None:
    """Clean M2 forward eval on post-freeze bars -> a valid (non-VOID) verdict."""
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"
    _seed_trials_with_classification(trials_registry)

    freeze_id = _freeze_minimal(tmp_path, prereg_path, config_path, registry=registry)

    # All bars strictly post-freeze (freeze happens 'now' during the test).
    # Use a future-dated window that cannot have any pre-freeze risk.
    bars = _make_ohlcv(n_bars=60, start="2030-01-01")

    from forex_system.harness import forward_eval as fe
    result = fe.forward_evaluate(
        freeze_id=freeze_id,
        forward_bars=bars,
        pair="EURUSD",
        config_path=config_path,
        prereq_path=prereg_path,
        registry=registry,
        trials_registry=trials_registry,
    )

    assert result.verdict in ("VALIDATED", "FALSIFIED", "INCONCLUSIVE_UNDERPOWERED"), (
        f"Expected a proper (non-VOID) verdict; got {result.verdict!r}. "
        "A clean M2 eval on post-freeze bars must not produce VOID."
    )
    assert result.integrity_ok, "Integrity must be OK on a clean eval."
    assert result.freeze_id == freeze_id

    # IC-7: counts_toward=True must be in the appended trial.
    _assert_trial_counts_toward_n(trials_registry, result.trial_id)

    # Window must be burned after scoring (IC-6).
    from forex_system.harness.freeze import load_freeze_record_with_state
    _, open_count, burned = load_freeze_record_with_state(freeze_id, registry=registry)
    assert open_count == 1 and burned, "Window must be burned after forward eval (IC-6)."


# ---------------------------------------------------------------------------
# IC-6: one-shot — second open of burned window -> RuntimeError
# ---------------------------------------------------------------------------


def test_one_shot_burned_refuses(tmp_path: Path) -> None:
    """Second open of a burned window -> RuntimeError, no silent re-run (IC-6)."""
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"
    _seed_trials_with_classification(trials_registry)

    freeze_id = _freeze_minimal(tmp_path, prereg_path, config_path, registry=registry)
    bars = _make_ohlcv(n_bars=60, start="2030-01-01")

    from forex_system.harness import forward_eval as fe

    # First eval — must succeed (or produce any non-RuntimeError verdict).
    result1 = fe.forward_evaluate(
        freeze_id=freeze_id,
        forward_bars=bars,
        pair="EURUSD",
        config_path=config_path,
        prereq_path=prereg_path,
        registry=registry,
        trials_registry=trials_registry,
    )
    assert result1.verdict in ("VALIDATED", "FALSIFIED", "INCONCLUSIVE_UNDERPOWERED")

    # Second eval — must REFUSE.
    with pytest.raises(RuntimeError, match="already burned|IC-6|one-score"):
        fe.forward_evaluate(
            freeze_id=freeze_id,
            forward_bars=bars,
            pair="EURUSD",
            config_path=config_path,
            prereq_path=prereg_path,
            registry=registry,
            trials_registry=trials_registry,
        )


# ---------------------------------------------------------------------------
# IC-7: VOID-after-data burns N (void_after_data=True -> counts_toward=True)
# ---------------------------------------------------------------------------


def test_void_after_data_burns_n(tmp_path: Path) -> None:
    """VOID after forward bars were loaded still appends counts_toward=True (IC-7)."""
    # Use the pre-freeze bar test scenario — it VOIDs after loading data.
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"
    _seed_trials_with_classification(trials_registry)

    freeze_id = _freeze_minimal(tmp_path, prereg_path, config_path, registry=registry)

    pre_bar = _make_ohlcv(n_bars=1, start="2020-01-01")
    post_bars = _make_ohlcv(n_bars=40, start="2030-01-01")
    bars = pd.concat([pre_bar, post_bars]).sort_index()

    from forex_system.harness import forward_eval as fe
    result = fe.forward_evaluate(
        freeze_id=freeze_id,
        forward_bars=bars,
        pair="EURUSD",
        config_path=config_path,
        prereq_path=prereg_path,
        registry=registry,
        trials_registry=trials_registry,
    )
    assert result.verdict == "VOID"
    assert result.void_after_data

    # Must still burn N.
    _assert_trial_counts_toward_n(trials_registry, result.trial_id)


# ---------------------------------------------------------------------------
# IC-7: clean eval appends counts_toward=True
# ---------------------------------------------------------------------------


def test_forward_attempt_counts_n(tmp_path: Path) -> None:
    """A forward eval (any verdict) appends a counts_toward=True trial (IC-7)."""
    prereg_path, _ = _make_prereg(tmp_path)
    config_path = _make_config(tmp_path)
    registry = tmp_path / "forward_registry.jsonl"
    trials_registry = tmp_path / "trials_test.jsonl"
    _seed_trials_with_classification(trials_registry)

    # Record N before.
    from forex_system.harness.honest_n import honest_n_deflation_denominator
    n_before = honest_n_deflation_denominator(trials_registry)

    freeze_id = _freeze_minimal(tmp_path, prereg_path, config_path, registry=registry)
    bars = _make_ohlcv(n_bars=60, start="2030-01-01")

    from forex_system.harness import forward_eval as fe
    fe.forward_evaluate(
        freeze_id=freeze_id,
        forward_bars=bars,
        pair="EURUSD",
        config_path=config_path,
        prereq_path=prereg_path,
        registry=registry,
        trials_registry=trials_registry,
    )

    n_after = honest_n_deflation_denominator(trials_registry)
    assert n_after == n_before + 1, (
        f"After a forward eval, honest_n should increment by 1; was {n_before}, now {n_after}."
    )


# ---------------------------------------------------------------------------
# Verdict priority (critic fix): a hard kill always beats a soft INCONCLUSIVE.
# ---------------------------------------------------------------------------


def test_verdict_dsr_fail_and_underpowered_is_falsified() -> None:
    """When DSR fails AND N < power floor, the verdict is FALSIFIED, not softened.

    NHT SD1 / no_gate_softening: an underpowered window must NEVER rescue a result
    that already failed a hard gate. FALSIFIED takes priority over INCONCLUSIVE.
    """
    from forex_system.harness.forward_eval import _determine_verdict

    verdict = _determine_verdict(
        gate_results={"KILL-0": True},   # min-events gate fired (short window)
        dsr=0.50,                        # DSR fails the 0.95 bar
        n_realized=5,
        power_floor_n=48,                # realized N (5) < floor (48)
        power_floor_label="KILL-0",      # KILL-0 IS the power-floor gate
        mechanism="M2",
    )
    assert verdict == "FALSIFIED", (
        "DSR<0.95 must FALSIFY even when underpowered — a short window cannot soften "
        f"a hard DSR kill (got {verdict})."
    )


def test_verdict_underpowered_only_is_inconclusive() -> None:
    """When the ONLY failing condition is the power floor (DSR passes, no other gate
    fired), the verdict is INCONCLUSIVE_UNDERPOWERED — not FALSIFIED.

    This confirms the power-floor gate (KILL-0) is excluded from the hard-kill loop
    and routes to INCONCLUSIVE for M2.
    """
    from forex_system.harness.forward_eval import _determine_verdict

    verdict = _determine_verdict(
        gate_results={"KILL-0": True, "KILL-SHARPE": False},  # only power-floor fired
        dsr=0.99,                        # DSR clears
        n_realized=5,
        power_floor_n=48,
        power_floor_label="KILL-0",
        mechanism="M2",
    )
    assert verdict == "INCONCLUSIVE_UNDERPOWERED", (
        "When DSR passes and only the power-floor gate fired, the M2 verdict must be "
        f"INCONCLUSIVE_UNDERPOWERED (got {verdict})."
    )


def test_verdict_real_kill_gate_beats_underpowered() -> None:
    """A non-power-floor KILL gate firing -> FALSIFIED, even on a short window.

    A real KILL (e.g. KILL-SHARPE) is a hard falsification regardless of N. Only the
    power-floor gate (KILL-0) softens to INCONCLUSIVE.
    """
    from forex_system.harness.forward_eval import _determine_verdict

    verdict = _determine_verdict(
        gate_results={"KILL-0": True, "KILL-SHARPE": True},  # real kill + power floor
        dsr=0.99,
        n_realized=5,
        power_floor_n=48,
        power_floor_label="KILL-0",
        mechanism="M2",
    )
    assert verdict == "FALSIFIED", (
        "A real KILL gate (KILL-SHARPE) firing must FALSIFY even on a short window "
        f"(got {verdict})."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_registry(registry: Path) -> list[dict]:
    if not registry.exists():
        return []
    records = []
    with open(registry) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            records.append(json.loads(raw))
    return records


def _assert_trial_counts_toward_n(trials_registry: Path, trial_id: str) -> None:
    """Assert that a trial with the given id has counts_toward_deflation_denominator=True."""
    assert trials_registry.exists(), "trials_registry must exist after a forward eval."
    found = False
    with open(trials_registry) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            if record.get("trial_id") == trial_id:
                found = True
                counts = record.get("counts_toward_deflation_denominator")
                assert counts is True, (
                    f"Trial {trial_id} must have counts_toward_deflation_denominator=True "
                    f"(IC-7), but got {counts!r}."
                )
    assert found, f"Trial {trial_id!r} was not found in {trials_registry}."


def _seed_trials_with_classification(trials_path: Path) -> None:
    """Write a minimal trials.jsonl with a valid honest-n-classification record.

    The classification record must be present for honest_n_deflation_denominator()
    to succeed (fail-closed: absent classification record -> RuntimeError).

    Uses ratified_n=1 with one counted trial so the baseline is minimal and
    forward_attempt increments are detectable.
    """
    trials_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_trial_id = "test0001"
    counted_entry = {
        "trial_id": baseline_trial_id,
        "status": "complete",
        "sharpe": 0.5,
        "config_hash": "abc12345",
        "counts_toward_deflation_denominator": True,
    }
    classification_record = {
        "event": "honest-n-classification",
        "ratified_n": 1,
        "ratified_by": ["head-of-quant-research", "null-hypothesis-tester"],
        "counted_trial_ids": [
            {"trial_id": baseline_trial_id, "reason": "test baseline trial"},
        ],
        "excluded_trial_ids": [],
        "ts": "2026-06-17T00:00:00Z",
    }
    with open(trials_path, "w") as fh:
        fh.write(json.dumps(counted_entry) + "\n")
        fh.write(json.dumps(classification_record) + "\n")
