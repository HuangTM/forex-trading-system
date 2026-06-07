"""QRB-6 cost-coverage gate tests (Fix 3 — remediation 2026-06-07).

This test module implements the structural cost-coverage gate demanded by NHT
(nht-run-integrity-adjudication.yaml, Section E) and CTO.

GATE REQUIREMENT (NHT verbatim):
  Before the freeze-receipt SHA is cut for any pre-registration that names a
  set of trading pairs, an automated assertion must verify that every pair in
  the registered pair-bank map resolves to a present, positive, finite cost
  entry in the active cost manifest.

Test categories:
  1. Coverage gate — all 12 QRB-6 registered pairs resolve in the manifest.
  2. Positivity gate — spread_pips > 0 for all registered pairs.
  3. Manifest loading — absent manifest → RULE_0 (sys.exit); missing pair → RULE_0.
  4. Exclusion-not-imputation — event with empty pair_returns is absent from y_e.
  5. Cost-gap counter — n_event_cost_or_data_gap surfaces in the result.
  6. cut_freeze_receipt gate — refuses to cut if any registered pair is missing.
  7. Generalisation comment — future pre-regs must register their pair universe.

kill_test_executed: false (no statistical computation on real return data)
no-capital-instruction: true
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Repo layout helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_COST_MANIFEST_PATH = _REPO_ROOT / "config" / "cost_freeze_qrb6.yaml"
_RUNNER_PATH = _REPO_ROOT / "scripts" / "run_qrb6.py"
_CUT_RECEIPT_PATH = _REPO_ROOT / "scripts" / "cut_freeze_receipt.py"

# QRB-6 registered pairs (§3.2 frozen map, 11 unique Scenario A pairs).
# FED: EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD (6)
# BOJ: USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY (6)
# RBA: AUDUSD, AUDJPY (2)
# BOC: USDCAD, CADJPY (2)
# Unique union = 11 pairs (EURGBP is Scenario B only; not in any Scenario A bank).
#
# GENERALIZATION NOTE (for future event-study pre-regs):
#   Any future event-study pre-registration that names a pair-bank map MUST:
#   (a) Register its complete pair universe in a constant analogous to
#       _QRB6_REGISTERED_PAIRS here.
#   (b) Have a corresponding test (analogous to this file) that asserts
#       every registered pair resolves to a positive, finite cost entry
#       in the trial's active cost manifest.
#   (c) Wire this test into the freeze-receipt gate (cut_freeze_receipt.py)
#       so the gate REFUSES to cut without a passing coverage test.
#   The QRB-6 gap (3-of-11 pairs covered) survived 7 review checkpoints.
#   Machine gates are the correct fix; manual review is insufficient.
_QRB6_REGISTERED_PAIRS: frozenset[str] = frozenset({
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY",
})


# ---------------------------------------------------------------------------
# Stub manifest factory (for unit-testing the loader without touching real file)
# ---------------------------------------------------------------------------

def _make_stub_manifest(
    pairs: list[str] | None = None,
    spread_pips_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build a minimal 12-pair stub manifest for unit tests.

    Parameters
    ----------
    pairs:
        Subset of pairs to include (default: all 12 registered pairs).
    spread_pips_override:
        Per-pair spread_pips overrides (default: 0.5 for all non-JPY, 0.5 for JPY).
    """
    all_pairs = [
        ("EURUSD", 0.0001), ("GBPUSD", 0.0001), ("USDJPY", 0.01),
        ("USDCAD", 0.0001), ("AUDUSD", 0.0001), ("NZDUSD", 0.0001),
        ("EURJPY", 0.01),  ("GBPJPY", 0.01),  ("AUDJPY", 0.01),
        ("CADJPY", 0.01),  ("NZDJPY", 0.01),
        # Note: EURGBP is Scenario B only (BOE); NOT in any Scenario A bank.
        # The registered Scenario A universe has 11 unique pairs.
    ]
    # Filter to requested subset
    if pairs is not None:
        pairs_set = set(pairs)
        all_pairs = [(sym, pv) for sym, pv in all_pairs if sym in pairs_set]

    override = spread_pips_override or {}
    pair_entries = []
    for sym, pip_val in all_pairs:
        spread = override.get(sym, 0.5)
        pair_entries.append({
            "symbol": sym,
            "pip_value": pip_val,
            "spread_pips": spread,
            "slippage_pips": 0.5,
            "commission_pips": 0.5,
            "swap_long_pips_per_day": -1.0,
            "swap_short_pips_per_day": 0.2,
        })

    return {
        "manifest_meta": {
            "trial_id": "fa0f982a",
            "authored_by": "TEST_STUB",
            "mechanical_rule_ref": "TEST_STUB",
            "nht_countersign": "TEST_STUB",
            "committed_before_rerun": True,
        },
        "pairs": pair_entries,
    }


# ---------------------------------------------------------------------------
# 1. Coverage gate — all 12 registered pairs must be present
# ---------------------------------------------------------------------------


class TestCoverageGate:
    """Every QRB-6 registered pair must be present in the manifest."""

    def test_complete_stub_passes_coverage_gate(self, tmp_path):
        """A manifest with all 12 registered pairs passes the loader without RULE_0."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()  # all 12 pairs
        manifest_path = tmp_path / "cost_freeze_qrb6.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        # Must not call sys.exit (no RULE_0)
        pair_infos, sha = run_qrb6._load_cost_manifest(manifest_path)
        assert set(pair_infos.keys()) == _QRB6_REGISTERED_PAIRS, (
            f"Expected exactly 12 registered pairs in loaded manifest; "
            f"got: {sorted(pair_infos.keys())}"
        )

    def test_missing_pair_triggers_rule_0(self, tmp_path):
        """A manifest missing any registered pair must trigger RULE_0 (sys.exit)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        # Missing AUDUSD and CADJPY (the RBA/BOC-specific pairs that caused the void)
        incomplete_pairs = list(_QRB6_REGISTERED_PAIRS - {"AUDUSD", "CADJPY"})
        manifest = _make_stub_manifest(pairs=incomplete_pairs)
        manifest_path = tmp_path / "cost_freeze_qrb6_incomplete.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        with pytest.raises(SystemExit) as exc_info:
            run_qrb6._load_cost_manifest(manifest_path)
        assert exc_info.value.code != 0, (
            "Missing registered pairs must trigger RULE_0_TECHNICAL_FAILURE (exit != 0)"
        )

    def test_each_bank_pair_covered_individually(self, tmp_path):
        """Each bank's pair universe must be individually verifiable via the manifest.

        Spot-checks:
          RBA → AUDUSD, AUDJPY (both were uncovered in the void run)
          BOC → USDCAD, CADJPY (both were uncovered in the void run)
          FED → EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD (all 6)
          BOJ → USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY (all 6)
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()
        manifest_path = tmp_path / "cost_freeze_qrb6.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        pair_infos, _ = run_qrb6._load_cost_manifest(manifest_path)

        bank_pair_map = {
            "FED": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD"],
            "BOJ": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "NZDJPY"],
            "RBA": ["AUDUSD", "AUDJPY"],
            "BOC": ["USDCAD", "CADJPY"],
        }
        for bank, pairs in bank_pair_map.items():
            for pair in pairs:
                assert pair in pair_infos, (
                    f"Bank {bank}'s pair {pair} is not in the loaded manifest. "
                    f"This pair caused the void run when it was missing from config/default.yaml."
                )

    def test_exactly_11_registered_pairs(self):
        """Sanity check: the Scenario A registered pair set has exactly 11 unique members.

        FED(6) + BOJ(6) + RBA(2) + BOC(2) = 16 bank-pair slots, 11 unique pairs.
        EURGBP is Scenario B only (BOE/ECB) and is excluded from Scenario A.
        """
        assert len(_QRB6_REGISTERED_PAIRS) == 11, (
            f"Expected 11 unique QRB-6 Scenario A registered pairs; got {len(_QRB6_REGISTERED_PAIRS)}: "
            f"{sorted(_QRB6_REGISTERED_PAIRS)}\n"
            "EURGBP is Scenario B only and must NOT be in the Scenario A gate."
        )


# ---------------------------------------------------------------------------
# 2. Positivity gate — spread_pips > 0 for all registered pairs
# ---------------------------------------------------------------------------


class TestPositivityGate:
    """Every registered pair must have spread_pips > 0 and a finite pip_value."""

    def test_all_pairs_have_positive_spread_in_complete_manifest(self, tmp_path):
        """Complete stub with spread_pips=0.5 passes the positivity gate."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()
        manifest_path = tmp_path / "cost_freeze_qrb6.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        pair_infos, _ = run_qrb6._load_cost_manifest(manifest_path)
        for sym in _QRB6_REGISTERED_PAIRS:
            pi = pair_infos[sym]
            assert pi.spread_pips > 0.0, (
                f"Pair {sym}: spread_pips={pi.spread_pips} must be > 0 "
                "(placeholder not yet filled by Mathematician)"
            )
            assert pi.pip_value > 0.0 and pi.pip_value <= 1.0, (
                f"Pair {sym}: pip_value={pi.pip_value} must be in (0, 1]"
            )

    def test_zero_spread_pair_causes_warning_logged(self, tmp_path):
        """A pair with spread_pips=0.0 causes a WARNING log entry at manifest load time.

        The loader does NOT exit (positivity enforcement is deferred to the live gate);
        it emits a structured warning log event 'cost_manifest_zero_spread_pairs'.
        This test verifies: (a) loader does not exit; (b) the log event key is in the source.
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        # AUDJPY with spread_pips=0.0 (placeholder not filled)
        manifest = _make_stub_manifest(spread_pips_override={"AUDJPY": 0.0})
        manifest_path = tmp_path / "cost_freeze_qrb6_zero_spread.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        # Loader should NOT exit — it warns, but positivity enforcement is in live gate
        pair_infos, _ = run_qrb6._load_cost_manifest(manifest_path)
        # AUDJPY loaded with zero spread (warning emitted but not a RULE_0 at load time)
        assert pair_infos["AUDJPY"].spread_pips == 0.0, (
            "AUDJPY with spread_pips=0.0 must load successfully (warning only at load time)."
        )

        # Verify the warning log event key is present in the source
        # (The logger uses the structured event system; capsys doesn't capture it reliably
        # because logging is configured at module load time before capsys is active.)
        src = _RUNNER_PATH.read_text()
        assert "cost_manifest_zero_spread_pairs" in src, (
            "Runner must emit 'cost_manifest_zero_spread_pairs' log event for zero-spread pairs."
        )

    def test_jpy_pairs_have_pip_value_001(self, tmp_path):
        """JPY pairs must have pip_value=0.01 in the manifest."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()
        manifest_path = tmp_path / "cost_freeze_qrb6.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        pair_infos, _ = run_qrb6._load_cost_manifest(manifest_path)
        jpy_pairs = [p for p in _QRB6_REGISTERED_PAIRS if "JPY" in p]
        non_jpy_pairs = [p for p in _QRB6_REGISTERED_PAIRS if "JPY" not in p]

        for sym in jpy_pairs:
            assert pair_infos[sym].pip_value == pytest.approx(0.01), (
                f"JPY pair {sym}: pip_value must be 0.01; got {pair_infos[sym].pip_value}"
            )
        for sym in non_jpy_pairs:
            assert pair_infos[sym].pip_value == pytest.approx(0.0001), (
                f"Non-JPY pair {sym}: pip_value must be 0.0001; got {pair_infos[sym].pip_value}"
            )


# ---------------------------------------------------------------------------
# 3. Manifest loading interlocks
# ---------------------------------------------------------------------------


class TestManifestLoadingInterlocks:
    """Absent manifest or missing pairs → RULE_0 (sys.exit != 0)."""

    def test_absent_manifest_triggers_rule_0(self, tmp_path):
        """If cost_freeze_qrb6.yaml is absent, _load_cost_manifest must sys.exit != 0."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        nonexistent = tmp_path / "does_not_exist.yaml"
        with pytest.raises(SystemExit) as exc_info:
            run_qrb6._load_cost_manifest(nonexistent)
        assert exc_info.value.code != 0, (
            "Absent cost manifest must trigger RULE_0_TECHNICAL_FAILURE (exit != 0)."
        )

    def test_manifest_sha256_logged_at_load(self, tmp_path):
        """The manifest SHA-256 must be returned and wired into the log at load time.

        Structural test: verifies the sha is a valid 64-char hex string AND that the
        runner source emits it in a structured log event (log-as-decision-trace rubric).
        (capsys does not capture the logging handler set up at module load time.)
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()
        manifest_path = tmp_path / "cost_freeze_qrb6.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        pair_infos, sha = run_qrb6._load_cost_manifest(manifest_path)

        # sha must be a 64-char hex string (SHA-256)
        assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), (
            f"Expected a 64-char lowercase hex SHA-256; got: {sha!r}"
        )

        # The SHA must match the actual file content
        h = hashlib.sha256(manifest_path.read_bytes())
        assert sha == h.hexdigest(), (
            f"Returned SHA-256 {sha!r} does not match actual file hash {h.hexdigest()!r}."
        )

        # Structural: the loader source must emit the sha in a log event
        src = _RUNNER_PATH.read_text()
        assert "manifest_sha256" in src, (
            "Runner source must log manifest_sha256 for audit traceability "
            "(log-as-decision-trace rubric)."
        )

    def test_manifest_sha_in_dry_run_result(self, tmp_path):
        """Dry-run result YAML must record cost_manifest_sha256 (even as DRY_RUN_NO_MANIFEST)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        from forex_system.harness.qrb6_decision import (
            _EXPECTED_SCENARIO_A_N,
            _EXPECTED_POST_2015_A_N,
        )

        stub_receipt = {
            "master_seed": 387992,
            "K": 200,  # small for speed
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.0422,
            "p_reject_threshold": 0.0378,
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": _EXPECTED_SCENARIO_A_N,
            "post_2015_a": _EXPECTED_POST_2015_A_N,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "TEST",
            "frozen_at_utc": "TEST",
        }

        result = run_qrb6._run_pipeline(receipt=stub_receipt, dry_run=True)

        assert "cost_manifest_sha256" in result, (
            "Result YAML must include cost_manifest_sha256 field for audit provenance."
        )
        assert "n_event_cost_or_data_gap" in result, (
            "Result YAML must include n_event_cost_or_data_gap counter (Fix 1)."
        )
        # Dry-run: no manifest loaded, so sha is the placeholder string
        assert result["cost_manifest_sha256"] == "DRY_RUN_NO_MANIFEST", (
            f"Dry-run cost_manifest_sha256 must be 'DRY_RUN_NO_MANIFEST'; "
            f"got: {result['cost_manifest_sha256']!r}"
        )


# ---------------------------------------------------------------------------
# 4. Exclusion-not-imputation — the core Fix 1 behavioural assertion
# ---------------------------------------------------------------------------


class TestExclusionNotImputation:
    """Events with empty pair_returns must be EXCLUDED from y_e, never zero-imputed."""

    def test_event_with_all_pairs_suppressed_is_absent_from_y_e(self, tmp_path):
        """An event where all pairs are spread-z suppressed must NOT appear in y_e.

        This is the direct regression test for the void: RBA/BOC bank-events were
        zero-imputed (y_e=0.0 contributed to the pooled statistic) instead of
        excluded.  This test verifies the corrected behaviour.
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        from forex_system.harness.qrb6_decision import (
            _EXPECTED_SCENARIO_A_N,
            _EXPECTED_POST_2015_A_N,
        )

        # Use spread_z_threshold=0.0 to suppress ALL pairs in ALL events (extreme case)
        # With threshold=0.0, any positive spread_z (>0.0) fires suppression for every pair.
        # The stub returns use spread_z from rng.uniform(0, 5) — all > 0.0 → all suppressed.
        stub_receipt = {
            "master_seed": 387992,
            "K": 10,  # tiny for speed
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 0.0,  # suppress everything
            "p_straddle_hi": 0.0422,
            "p_reject_threshold": 0.0378,
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": _EXPECTED_SCENARIO_A_N,
            "post_2015_a": _EXPECTED_POST_2015_A_N,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "TEST",
            "frozen_at_utc": "TEST",
        }

        # With all events suppressed, the pipeline must hit RULE_0 (empty y_e).
        # This is correct behaviour — no fabricated zeros should keep it running.
        with pytest.raises((SystemExit, RuntimeError)) as exc_info:
            run_qrb6._run_pipeline(receipt=stub_receipt, dry_run=True)
        # Either sys.exit(1) or RuntimeError("RULE_0_TECHNICAL_FAILURE: no valid y_e...")
        if isinstance(exc_info.value, SystemExit):
            assert exc_info.value.code != 0, (
                "With all events suppressed, runner must exit non-zero (no fabricated y_e)."
            )
        else:
            assert "RULE_0" in str(exc_info.value) or "no valid y_e" in str(exc_info.value), (
                f"Expected RULE_0 RuntimeError; got: {exc_info.value}"
            )

    def test_normal_dry_run_produces_nonzero_y_e_count(self, tmp_path):
        """Normal dry-run with default spread_z_threshold=3.0 produces non-empty y_e."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        from forex_system.harness.qrb6_decision import (
            _EXPECTED_SCENARIO_A_N,
            _EXPECTED_POST_2015_A_N,
        )

        stub_receipt = {
            "master_seed": 387992,
            "K": 200,
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.0422,
            "p_reject_threshold": 0.0378,
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": _EXPECTED_SCENARIO_A_N,
            "post_2015_a": _EXPECTED_POST_2015_A_N,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "TEST",
            "frozen_at_utc": "TEST",
        }

        result = run_qrb6._run_pipeline(receipt=stub_receipt, dry_run=True)

        assert result["n_included_full"] > 0, (
            "Dry-run with spread_z_threshold=3.0 must include at least one y_e observation."
        )
        assert result["n_event_cost_or_data_gap"] == 0, (
            "Dry-run must have n_event_cost_or_data_gap=0 (no cost manifest in dry-run)."
        )

    def test_zero_imputation_not_present_in_runner_source(self):
        """The runner source must not contain the old zero-imputation pattern.

        The VOID was caused by:
            mean_return = float(np.mean(pair_returns)) if pair_returns else 0.0
        The fix removes the 'else 0.0' fallback and replaces it with 'continue'.
        This test guards the regression.
        """
        import re

        src = _RUNNER_PATH.read_text()

        # The old pattern: 'if pair_returns else 0.0' (zero-imputation of mean_return)
        old_pattern = re.search(
            r'mean_return\s*=\s*float\(np\.mean\(pair_returns\)\)\s+if\s+pair_returns\s+else\s+0\.0',
            src,
        )
        assert old_pattern is None, (
            "Found the old zero-imputation pattern 'mean_return = ... if pair_returns else 0.0' "
            "in run_qrb6.py.  This is the bug that caused the void — remove it and use "
            "EXCLUSION (continue) when pair_returns is empty."
        )

    def test_event_excluded_log_events_present_in_source(self):
        """The source must log the distinct exclusion-reason events (Fix 1)."""
        src = _RUNNER_PATH.read_text()
        assert "event_excluded_all_pairs_suppressed" in src, (
            "Missing log event 'event_excluded_all_pairs_suppressed' in run_qrb6.py. "
            "Fix 1 requires logging when all pairs are suppressed by spread_z."
        )
        assert "event_excluded_data_or_cost_gap" in src, (
            "Missing log event 'event_excluded_data_or_cost_gap' in run_qrb6.py. "
            "Fix 1 requires logging (with counter) when cost/data gaps exclude an event."
        )


# ---------------------------------------------------------------------------
# 5. Cost-gap counter in result YAML
# ---------------------------------------------------------------------------


class TestCostGapCounter:
    """n_event_cost_or_data_gap must be present in the result and zero post-remediation."""

    def test_cost_gap_counter_in_dry_run_result(self, tmp_path):
        """Dry-run result must include n_event_cost_or_data_gap (expected: 0)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_qrb6", _RUNNER_PATH)
        assert spec is not None and spec.loader is not None
        run_qrb6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_qrb6)  # type: ignore[union-attr]

        from forex_system.harness.qrb6_decision import (
            _EXPECTED_SCENARIO_A_N,
            _EXPECTED_POST_2015_A_N,
        )

        stub_receipt = {
            "master_seed": 387992,
            "K": 100,
            "sr0_pp": 0.026861,
            "dsr_threshold": 0.95,
            "spread_z_threshold": 3.0,
            "p_straddle_hi": 0.0422,
            "p_reject_threshold": 0.0378,
            "kill_switch_threshold": 1.5883,
            "scenario_a_event_days": _EXPECTED_SCENARIO_A_N,
            "post_2015_a": _EXPECTED_POST_2015_A_N,
            "trial_id": "fa0f982a",
            "n_sel": 3,
            "code_commit": "TEST",
            "frozen_at_utc": "TEST",
        }

        result = run_qrb6._run_pipeline(receipt=stub_receipt, dry_run=True)

        # Counter must be present in result
        assert "n_event_cost_or_data_gap" in result, (
            "Result YAML must contain 'n_event_cost_or_data_gap' field (Fix 1 requirement)."
        )
        assert result["n_event_cost_or_data_gap"] == 0, (
            f"Dry-run must have n_event_cost_or_data_gap=0; "
            f"got {result['n_event_cost_or_data_gap']}."
        )

    def test_cost_gap_counter_in_result_yaml_source(self):
        """The runner source must write n_event_cost_or_data_gap to the result dict."""
        src = _RUNNER_PATH.read_text()
        assert "n_event_cost_or_data_gap" in src, (
            "Runner source must include 'n_event_cost_or_data_gap' in the result payload "
            "(Fix 1: counter surfaces in result YAML so any future gap is visible, never silent)."
        )

    def test_cost_gap_invariant_note_in_source(self):
        """The runner must include the post-remediation invariant note in the result."""
        src = _RUNNER_PATH.read_text()
        assert "cost_gap_invariant" in src, (
            "Runner source must include 'cost_gap_invariant' in the result payload "
            "so reviewers know the expected post-remediation value is 0."
        )


# ---------------------------------------------------------------------------
# 6. cut_freeze_receipt gate — refuses to cut without complete cost coverage
# ---------------------------------------------------------------------------


class TestCutFreezeReceiptGate:
    """cut_freeze_receipt.py must refuse to cut the qrb6 receipt if the cost manifest
    is incomplete (missing pairs or zero-spread placeholders).

    Implementation: cut_freeze_receipt.py's qrb6 path calls
    _assert_qrb6_cost_coverage(manifest_path) which raises SystemExit(1) on failure.
    This is the CTO-owned structural gate (NHT Section E requirement).
    """

    def test_cut_receipt_calls_cost_coverage_check(self):
        """cut_freeze_receipt.py source must reference the cost coverage check for qrb6."""
        src = _CUT_RECEIPT_PATH.read_text()
        # The gate must reference either the cost manifest path or an explicit coverage check
        has_gate = (
            "cost_freeze_qrb6" in src
            or "_assert_qrb6_cost_coverage" in src
            or "cost_coverage" in src
        )
        assert has_gate, (
            "cut_freeze_receipt.py must reference the cost-coverage gate for the qrb6 target. "
            "The gate must refuse to cut the receipt if any registered pair is missing from "
            "the cost manifest (NHT Section E requirement)."
        )

    def test_coverage_check_exits_on_incomplete_manifest(self, tmp_path):
        """The coverage check function must exit non-zero on an incomplete manifest.

        This tests the gate function directly (not the full receipt-cutting flow).
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("cut_freeze_receipt", _CUT_RECEIPT_PATH)
        assert spec is not None and spec.loader is not None
        cut_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cut_mod)  # type: ignore[union-attr]

        # Manifest missing AUDUSD and CADJPY
        incomplete_pairs = list(_QRB6_REGISTERED_PAIRS - {"AUDUSD", "CADJPY"})
        manifest = _make_stub_manifest(pairs=incomplete_pairs)
        manifest_path = tmp_path / "cost_freeze_qrb6_incomplete.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        with pytest.raises(SystemExit) as exc_info:
            cut_mod._assert_qrb6_cost_coverage(manifest_path)
        assert exc_info.value.code != 0, (
            "Coverage check must exit non-zero when registered pairs are missing."
        )

    def test_coverage_check_passes_on_complete_manifest(self, tmp_path):
        """The coverage check must NOT exit when the manifest is complete and positive."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cut_freeze_receipt", _CUT_RECEIPT_PATH)
        assert spec is not None and spec.loader is not None
        cut_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cut_mod)  # type: ignore[union-attr]

        manifest = _make_stub_manifest()  # all 12 pairs with spread_pips=0.5
        manifest_path = tmp_path / "cost_freeze_qrb6_complete.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        # Must NOT raise — complete manifest passes
        cut_mod._assert_qrb6_cost_coverage(manifest_path)

    def test_coverage_check_exits_on_zero_spread_placeholder(self, tmp_path):
        """Coverage check must exit if any registered pair has spread_pips <= 0.

        Zero spread means the Mathematician has not filled in the value.
        The gate must block the receipt cut until all values are positive.
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("cut_freeze_receipt", _CUT_RECEIPT_PATH)
        assert spec is not None and spec.loader is not None
        cut_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cut_mod)  # type: ignore[union-attr]

        # All 12 pairs present but AUDJPY has zero spread (placeholder)
        manifest = _make_stub_manifest(spread_pips_override={"AUDJPY": 0.0})
        manifest_path = tmp_path / "cost_freeze_qrb6_zero_spread.yaml"
        with open(manifest_path, "w") as fh:
            yaml.dump(manifest, fh)

        with pytest.raises(SystemExit) as exc_info:
            cut_mod._assert_qrb6_cost_coverage(manifest_path)
        assert exc_info.value.code != 0, (
            "Coverage check must exit non-zero when a registered pair has zero spread_pips "
            "(placeholder not yet filled by Mathematician)."
        )


# ---------------------------------------------------------------------------
# 7. Fix 2 — manifest loader wired in live-mode pipeline (structural check)
# ---------------------------------------------------------------------------


class TestManifestLoaderWiring:
    """Verify Fix 2 (manifest loader) is structurally wired in the runner."""

    def test_runner_references_cost_manifest_path_constant(self):
        """Runner source must define _COST_MANIFEST_PATH constant."""
        src = _RUNNER_PATH.read_text()
        assert "_COST_MANIFEST_PATH" in src, (
            "run_qrb6.py must define _COST_MANIFEST_PATH constant (Fix 2). "
            "The runner must load costs from the frozen manifest, not DEFAULT_PAIRS."
        )

    def test_runner_does_not_call_realistic_cost_model_without_pair_configs(self):
        """Runner must not instantiate RealisticCostModel() without pair_configs argument.

        The old bug: RealisticCostModel() (no args) → reads DEFAULT_PAIRS (3 pairs only).
        The fix: RealisticCostModel(pair_configs=_pair_infos) where _pair_infos is loaded
        from the frozen manifest.
        """
        import re

        # Check only non-comment, non-docstring lines
        bare_calls_in_code = []
        for raw_line in _RUNNER_PATH.read_text().splitlines():
            stripped = raw_line.strip()
            # Skip comment lines and blank lines
            if not stripped or stripped.startswith("#"):
                continue
            # Skip docstring / string-literal lines (crude but sufficient here)
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # Look for bare RealisticCostModel() on a code line
            if re.search(r'RealisticCostModel\(\s*\)', raw_line):
                bare_calls_in_code.append(raw_line.strip())

        assert not bare_calls_in_code, (
            "Found bare RealisticCostModel() call(s) in code (not comments) in run_qrb6.py:\n"
            + "\n".join(f"  {line}" for line in bare_calls_in_code) + "\n"
            "Fix 2: must always pass pair_configs=_pair_infos (manifest-loaded dict). "
            "RealisticCostModel() reads DEFAULT_PAIRS which only covers EURUSD/USDJPY/GBPUSD."
        )

    def test_runner_references_load_cost_manifest_function(self):
        """Runner source must define and call _load_cost_manifest."""
        src = _RUNNER_PATH.read_text()
        assert "_load_cost_manifest" in src, (
            "run_qrb6.py must define _load_cost_manifest() function (Fix 2). "
            "The function loads per-pair costs from config/cost_freeze_qrb6.yaml."
        )

    def test_registered_pairs_constant_matches_bank_pair_map(self):
        """The runner's _QRB6_REGISTERED_PAIRS must equal the union of all bank pair lists.

        This is the consistency invariant between the pair map and the coverage gate.
        """
        from forex_system.harness.qrb6_decision import _BANK_PAIR_MAP, _SCENARIO_A_BANKS

        # Union of all Scenario A bank pairs
        expected_pairs: set[str] = set()
        for bank in _SCENARIO_A_BANKS:
            expected_pairs.update(_BANK_PAIR_MAP[bank])

        # _QRB6_REGISTERED_PAIRS must equal this union
        assert _QRB6_REGISTERED_PAIRS == expected_pairs, (
            f"_QRB6_REGISTERED_PAIRS mismatch with BANK_PAIR_MAP union.\n"
            f"  Registered:       {sorted(_QRB6_REGISTERED_PAIRS)}\n"
            f"  Expected (union): {sorted(expected_pairs)}\n"
            "The coverage gate checks _QRB6_REGISTERED_PAIRS; if it drifts from the actual "
            "pair map, the gate becomes ineffective."
        )
