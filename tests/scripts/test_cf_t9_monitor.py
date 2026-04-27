"""Tests for CF-T9 regime monitor (scripts/monitor_regime_triggers.py).

Pre-registered retirement trigger CF-T9 (CONSENSUS 2026-04-26, references/
pre-registrations/carry_fred.md amendment). Both clauses must be evaluable
with deterministic synthetic data so that future BoJ-rate / pair-data
changes can be tested without depending on live FRED state.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

import monitor_regime_triggers as m


# --------------------------------------------------------------------------- #
# Synthetic data builders
# --------------------------------------------------------------------------- #

def _boj_series(monthly_rates: list[tuple[str, float]]) -> pd.Series:
    """Build a monthly-frequency BoJ rate series from (start_date, rate) tuples.

    The rate at index i applies from start_date i to start_date i+1.
    Final rate extends to 2026-04-01 by default.
    """
    rows = []
    for start, rate in monthly_rates:
        rows.append((pd.Timestamp(start), rate))
    rows.append((pd.Timestamp("2026-05-01"), rows[-1][1]))  # sentinel
    dates = pd.date_range(rows[0][0], rows[-1][0], freq="MS")
    series = pd.Series(index=dates, dtype=float)
    for i, (start, rate) in enumerate(rows[:-1]):
        end = rows[i + 1][0]
        mask = (series.index >= start) & (series.index < end)
        series.loc[mask] = rate
    return series.dropna()


def _flat_returns_df(annual_sharpe: float, n_days: int = 800) -> pd.DataFrame:
    """Synthetic daily returns with a target annualized Sharpe across 6 pairs.

    Used to drive Clause B evaluation deterministically. Each pair has
    iid Normal returns with mean and std calibrated to produce the target
    aggregate Sharpe after equal-vol-weighting.
    """
    rng = np.random.default_rng(0)
    daily_sigma = 0.005  # ~8% annualized vol per pair
    daily_mu = annual_sharpe * daily_sigma / np.sqrt(252)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    cols = m.JPY_CROSS_PAIRS
    data = rng.normal(daily_mu, daily_sigma, size=(n_days, len(cols)))
    return pd.DataFrame(data, index=dates, columns=cols)


# --------------------------------------------------------------------------- #
# Clause A: BoJ rate threshold
# --------------------------------------------------------------------------- #

class TestClauseA:
    def test_boj_below_threshold_throughout(self):
        """30 bp throughout history -> clause A NOT satisfied."""
        boj = _boj_series([("2010-01-01", 0.30)])
        quarterly = m.quarter_end_observations(boj)
        passed, obs = m.boj_clause_satisfied(quarterly)
        assert passed is False
        assert obs == []

    def test_boj_at_50bp_for_one_quarter_only(self):
        """Single quarter at threshold doesn't satisfy -- need >=2 consecutive."""
        boj = _boj_series([("2010-01-01", 0.30),
                           ("2024-10-01", 0.50),
                           ("2024-12-15", 0.30)])  # back down before next q-end
        quarterly = m.quarter_end_observations(boj)
        passed, _ = m.boj_clause_satisfied(quarterly)
        assert passed is False

    def test_boj_at_50bp_for_two_consecutive_quarters(self):
        """Threshold sustained 2 consecutive q-ends -> clause A satisfied."""
        boj = _boj_series([("2010-01-01", 0.30), ("2024-10-01", 0.50)])
        quarterly = m.quarter_end_observations(boj)
        passed, obs = m.boj_clause_satisfied(quarterly)
        assert passed is True
        assert len(obs) >= 2
        assert all(o["rate_pct"] >= 0.50 for o in obs)

    def test_boj_above_threshold_with_break(self):
        """Two qualifying runs separated by a break -- longest run must be >=2."""
        boj = _boj_series([
            ("2010-01-01", 0.30),
            ("2020-04-01", 0.55),     # one qualifying q-end
            ("2020-07-01", 0.30),     # break
            ("2024-10-01", 0.50),     # >=2 consecutive from here
        ])
        quarterly = m.quarter_end_observations(boj)
        passed, obs = m.boj_clause_satisfied(quarterly)
        assert passed is True
        # Latest qualifying run should be from 2024-Q4 onward, not 2020
        for o in obs:
            assert pd.Timestamp(o["quarter_end"]) >= pd.Timestamp("2024-09-30")


# --------------------------------------------------------------------------- #
# Clause B: rolling basket Sharpe
# --------------------------------------------------------------------------- #

class TestClauseB:
    def test_high_sharpe_basket_does_not_trigger(self):
        """Basket Sharpe well above 0.20 -> clause B NOT satisfied."""
        returns = _flat_returns_df(annual_sharpe=1.0, n_days=800)
        basket = m.equal_vol_weighted_basket(returns)
        rs = m.rolling_sharpe(basket, m.CF_T9_ROLLING_SHARPE_WINDOW)
        passed, _ = m.sharpe_clause_satisfied(rs)
        assert passed is False

    def test_zero_sharpe_basket_triggers(self):
        """Basket with zero Sharpe -> rolling realizations dip below 0.20."""
        returns = _flat_returns_df(annual_sharpe=0.0, n_days=800)
        basket = m.equal_vol_weighted_basket(returns)
        rs = m.rolling_sharpe(basket, m.CF_T9_ROLLING_SHARPE_WINDOW)
        passed, evidence = m.sharpe_clause_satisfied(rs)
        assert passed is True
        assert evidence["min_in_window"] < 0.20

    def test_negative_sharpe_basket_triggers(self):
        returns = _flat_returns_df(annual_sharpe=-0.5, n_days=800)
        basket = m.equal_vol_weighted_basket(returns)
        rs = m.rolling_sharpe(basket, m.CF_T9_ROLLING_SHARPE_WINDOW)
        passed, _ = m.sharpe_clause_satisfied(rs)
        assert passed is True


# --------------------------------------------------------------------------- #
# Combined CF-T9 evaluation
# --------------------------------------------------------------------------- #

class TestEvaluateCFT9:
    def test_neither_clause_no_trigger(self):
        """Low BoJ rate + high basket Sharpe -> NOT triggered."""
        boj = _boj_series([("2010-01-01", 0.10)])
        returns = _flat_returns_df(annual_sharpe=1.0)
        rec = m.evaluate_cf_t9(boj, returns)
        assert rec["triggered"] is False
        assert rec["clause_a_boj_rate"]["satisfied"] is False
        assert rec["clause_b_basket_sharpe"]["satisfied"] is False

    def test_only_clause_a_no_trigger(self):
        """High BoJ + high basket Sharpe -> NOT triggered (need both)."""
        boj = _boj_series([("2010-01-01", 0.30), ("2024-10-01", 0.75)])
        returns = _flat_returns_df(annual_sharpe=1.0)
        rec = m.evaluate_cf_t9(boj, returns)
        assert rec["triggered"] is False
        assert rec["clause_a_boj_rate"]["satisfied"] is True
        assert rec["clause_b_basket_sharpe"]["satisfied"] is False

    def test_only_clause_b_no_trigger(self):
        """Low BoJ + zero-Sharpe basket -> NOT triggered (need both)."""
        boj = _boj_series([("2010-01-01", 0.10)])
        returns = _flat_returns_df(annual_sharpe=0.0)
        rec = m.evaluate_cf_t9(boj, returns)
        assert rec["triggered"] is False
        assert rec["clause_a_boj_rate"]["satisfied"] is False
        assert rec["clause_b_basket_sharpe"]["satisfied"] is True

    def test_both_clauses_triggers(self):
        """High BoJ + zero-Sharpe basket -> TRIGGERED."""
        boj = _boj_series([("2010-01-01", 0.30), ("2024-10-01", 0.75)])
        returns = _flat_returns_df(annual_sharpe=-0.3)
        rec = m.evaluate_cf_t9(boj, returns)
        assert rec["triggered"] is True
        assert rec["clause_a_boj_rate"]["satisfied"] is True
        assert rec["clause_b_basket_sharpe"]["satisfied"] is True
        # Pre-reg cross-references must be present (audit invariant)
        assert "carry_fred.md" in rec["pre_reg_reference"]


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #

class TestAuditLog:
    def test_audit_record_appended(self, tmp_path):
        """Each invocation appends one JSON-line to the audit log."""
        audit = tmp_path / "cf_t9_audit.log"
        record = {"monitor_id": "CF-T9", "evaluated_at": "2026-04-27T00:00:00Z",
                  "triggered": False}
        m.write_audit_record(record, audit_path=audit)
        m.write_audit_record(record, audit_path=audit)
        lines = audit.read_text().strip().split("\n")
        assert len(lines) == 2
        # Each line must be parseable JSON
        import json
        for line in lines:
            json.loads(line)
