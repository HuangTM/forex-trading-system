"""
Tests for data/rates/cb_decision_dates.parquet.

Validates schema, date window, per-(bank,year) counts, cadence sanity,
weekday rules, uniqueness, and verification column values.
"""

from __future__ import annotations

import pandas as pd
import pytest

PARQUET_PATH = "data/rates/cb_decision_dates.parquet"

WINDOW_START = pd.Timestamp("2010-01-01")
WINDOW_END = pd.Timestamp("2026-04-06")

EXPECTED_BANKS = {"FED", "ECB", "BOE", "BOJ", "BOC", "RBA", "RBNZ"}
EXPECTED_CURRENCIES = {
    "FED": "USD", "ECB": "EUR", "BOE": "GBP", "BOJ": "JPY",
    "BOC": "CAD", "RBA": "AUD", "RBNZ": "NZD",
}
ALLOWED_GRADES = {
    "verified-official",
    "anchor-verified",
    "aggregator-only",
    "training-memory-unverified",
}

# ── Per-(bank, year) counts from the fragments ─────────────────────────────
# These are the authoritative counts and must match exactly.
PER_YEAR_COUNTS: dict[str, dict[int, int]] = {
    "FED": {
        2010: 8, 2011: 8, 2012: 8, 2013: 8, 2014: 8, 2015: 8, 2016: 8,
        2017: 8, 2018: 8, 2019: 8, 2020: 7, 2021: 8, 2022: 8, 2023: 8,
        2024: 8, 2025: 8, 2026: 2,
    },
    "ECB": {
        2010: 11, 2011: 11, 2012: 11, 2013: 11, 2014: 11,
        2015: 8, 2016: 8, 2017: 8, 2018: 8, 2019: 8,
        2020: 8, 2021: 8, 2022: 8, 2023: 8, 2024: 8, 2025: 8, 2026: 2,
    },
    "BOE": {
        2010: 12, 2011: 12, 2012: 12, 2013: 12, 2014: 12, 2015: 12, 2016: 12,
        2017: 8, 2018: 8, 2019: 8, 2020: 8, 2021: 8, 2022: 8, 2023: 8,
        2024: 8, 2025: 8, 2026: 2,
    },
    "BOJ": {
        2010: 16, 2011: 14, 2012: 14, 2013: 14, 2014: 14, 2015: 14,
        2016: 8, 2017: 8, 2018: 8, 2019: 8, 2020: 9, 2021: 8, 2022: 8,
        2023: 8, 2024: 8, 2025: 8, 2026: 2,
    },
    "BOC": {
        # 2010-2018: excluded (unverified — no dates in dataset)
        2019: 8, 2020: 8, 2021: 8, 2022: 8, 2023: 8, 2024: 8, 2025: 8, 2026: 2,
    },
    "RBA": {
        2010: 11, 2011: 11, 2012: 11, 2013: 11, 2014: 11, 2015: 11, 2016: 11,
        2017: 11, 2018: 11, 2019: 11, 2020: 11, 2021: 11, 2022: 11, 2023: 11,
        2024: 8, 2025: 8, 2026: 2,
    },
    "RBNZ": {
        # 2010-2023: excluded (unverified — no dates)
        # 2025: only 3 partial dates
        2024: 7, 2025: 3, 2026: 1,
    },
}

# ── Cadence expectations (meetings per year) ───────────────────────────────
# Used for sanity range checks; regime transitions documented.
CADENCE_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    # FED: 8/yr always (7 in 2020)
    "FED": {"default": (7, 8)},
    # ECB: 11/yr through 2014, 8/yr from 2015
    "ECB": {"pre_2015": (11, 11), "post_2014": (8, 8)},
    # BOE: 12/yr through 2016, 8/yr from 2017
    "BOE": {"pre_2017": (12, 12), "post_2016": (8, 8)},
    # BOJ: ~14/yr through 2015, 8/yr from 2016 (exceptions: 2010=16, 2020=9)
    "BOJ": {"pre_2016": (14, 16), "post_2015": (8, 9)},
    # BOC: 8/yr (only 2019+)
    "BOC": {"default": (8, 8)},
    # RBA: 11/yr through 2023, 8/yr from 2024
    "RBA": {"pre_2024": (11, 11), "post_2023": (8, 8)},
    # RBNZ: 7/yr for 2024 (partial 2025, partial 2026)
    "RBNZ": {"default": (1, 7)},
}

# ── Documented weekday exceptions (non-Thursday/non-Tuesday for BoE) ───────
# BoE: all decisions on Thursday EXCEPT election reschedulings (Monday)
BOE_MONDAY_EXCEPTIONS = {"2010-05-10", "2015-05-11"}


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_parquet(PARQUET_PATH)


class TestFileLoads:
    def test_loads(self, df: pd.DataFrame) -> None:
        assert len(df) > 0


class TestSchema:
    def test_columns(self, df: pd.DataFrame) -> None:
        expected = {"bank", "currency", "date", "scheduled", "verification", "source_tier"}
        assert expected == set(df.columns)

    def test_date_dtype(self, df: pd.DataFrame) -> None:
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_bank_dtype(self, df: pd.DataFrame) -> None:
        assert df["bank"].dtype == pd.StringDtype() or df["bank"].dtype == object

    def test_scheduled_all_true(self, df: pd.DataFrame) -> None:
        assert df["scheduled"].dtype == bool or pd.api.types.is_bool_dtype(df["scheduled"])
        assert df["scheduled"].all()

    def test_banks_present(self, df: pd.DataFrame) -> None:
        assert set(df["bank"].unique()) == EXPECTED_BANKS

    def test_currencies_correct(self, df: pd.DataFrame) -> None:
        for bank, currency in EXPECTED_CURRENCIES.items():
            actual = df[df["bank"] == bank]["currency"].unique()
            assert len(actual) == 1 and actual[0] == currency, (
                f"{bank}: expected currency {currency}, got {actual}"
            )


class TestDateWindow:
    def test_no_dates_before_window(self, df: pd.DataFrame) -> None:
        assert (df["date"] >= WINDOW_START).all()

    def test_no_dates_after_window(self, df: pd.DataFrame) -> None:
        assert (df["date"] <= WINDOW_END).all()

    def test_earliest_date_in_2010(self, df: pd.DataFrame) -> None:
        assert df["date"].min().year == 2010

    def test_latest_date_on_or_before_terminus(self, df: pd.DataFrame) -> None:
        assert df["date"].max() <= WINDOW_END


class TestPerYearCounts:
    """Each (bank, year) count must exactly match the fragment per_year_counts."""

    @pytest.mark.parametrize("bank", list(PER_YEAR_COUNTS.keys()))
    def test_per_year_counts(self, df: pd.DataFrame, bank: str) -> None:
        sub = df[df["bank"] == bank].copy()
        sub["year"] = sub["date"].dt.year
        actual: dict[int, int] = sub.groupby("year").size().to_dict()
        expected = PER_YEAR_COUNTS[bank]
        for year, expected_count in expected.items():
            actual_count = actual.get(year, 0)
            assert actual_count == expected_count, (
                f"{bank} {year}: expected {expected_count} rows, got {actual_count}"
            )


class TestCadenceSanity:
    """Per (bank, year) count must fall within documented cadence ranges."""

    def _check_bank(
        self, df: pd.DataFrame, bank: str, year: int, lo: int, hi: int
    ) -> None:
        sub = df[(df["bank"] == bank) & (df["date"].dt.year == year)]
        n = len(sub)
        assert lo <= n <= hi, (
            f"{bank} {year}: count {n} outside expected range [{lo},{hi}]"
        )

    def test_fed_cadence(self, df: pd.DataFrame) -> None:
        for year in range(2010, 2026):
            self._check_bank(df, "FED", year, 7, 8)

    def test_ecb_cadence_pre_2015(self, df: pd.DataFrame) -> None:
        for year in range(2010, 2015):
            self._check_bank(df, "ECB", year, 11, 11)

    def test_ecb_cadence_post_2014(self, df: pd.DataFrame) -> None:
        for year in range(2015, 2026):
            self._check_bank(df, "ECB", year, 8, 8)

    def test_boe_cadence_pre_2017(self, df: pd.DataFrame) -> None:
        for year in range(2010, 2017):
            self._check_bank(df, "BOE", year, 12, 12)

    def test_boe_cadence_post_2016(self, df: pd.DataFrame) -> None:
        for year in range(2017, 2026):
            self._check_bank(df, "BOE", year, 8, 8)

    def test_boj_cadence_pre_2016(self, df: pd.DataFrame) -> None:
        # 2010=16 (special), 2011-2015=14
        self._check_bank(df, "BOJ", 2010, 16, 16)
        for year in range(2011, 2016):
            self._check_bank(df, "BOJ", year, 14, 14)

    def test_boj_cadence_post_2015(self, df: pd.DataFrame) -> None:
        # 2016-2019: 8; 2020: 9; 2021+: 8
        self._check_bank(df, "BOJ", 2020, 9, 9)
        for year in [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]:
            self._check_bank(df, "BOJ", year, 8, 8)

    def test_rba_cadence_pre_2024(self, df: pd.DataFrame) -> None:
        for year in range(2010, 2024):
            self._check_bank(df, "RBA", year, 11, 11)

    def test_rba_cadence_post_2023(self, df: pd.DataFrame) -> None:
        for year in [2024, 2025]:
            self._check_bank(df, "RBA", year, 8, 8)

    def test_boc_cadence(self, df: pd.DataFrame) -> None:
        for year in range(2019, 2026):
            self._check_bank(df, "BOC", year, 8, 8)

    def test_boc_missing_pre_2019(self, df: pd.DataFrame) -> None:
        """BoC has no dates for 2010-2018 (unverified per fragment)."""
        sub = df[(df["bank"] == "BOC") & (df["date"].dt.year < 2019)]
        assert len(sub) == 0, (
            f"Expected 0 BoC rows before 2019, got {len(sub)}"
        )

    def test_rbnz_missing_pre_2024(self, df: pd.DataFrame) -> None:
        """RBNZ has no dates for 2010-2023 (anti-fabrication rule)."""
        sub = df[(df["bank"] == "RBNZ") & (df["date"].dt.year < 2024)]
        assert len(sub) == 0, (
            f"Expected 0 RBNZ rows before 2024, got {len(sub)}"
        )


class TestNoDuplicates:
    def test_no_duplicate_bank_date(self, df: pd.DataFrame) -> None:
        dupes = df.duplicated(subset=["bank", "date"])
        assert not dupes.any(), (
            f"Found duplicate (bank, date) rows:\n{df[dupes]}"
        )


class TestVerificationGrades:
    def test_only_allowed_grades(self, df: pd.DataFrame) -> None:
        bad = ~df["verification"].isin(ALLOWED_GRADES)
        assert not bad.any(), (
            f"Invalid verification values:\n{df[bad]['verification'].unique()}"
        )

    def test_fed_all_verified_official(self, df: pd.DataFrame) -> None:
        fed = df[df["bank"] == "FED"]
        assert (fed["verification"] == "verified-official").all()

    def test_boj_all_verified_official(self, df: pd.DataFrame) -> None:
        boj = df[df["bank"] == "BOJ"]
        assert (boj["verification"] == "verified-official").all()

    def test_rba_all_verified_official(self, df: pd.DataFrame) -> None:
        rba = df[df["bank"] == "RBA"]
        assert (rba["verification"] == "verified-official").all()

    def test_boc_all_verified_official(self, df: pd.DataFrame) -> None:
        boc = df[df["bank"] == "BOC"]
        assert (boc["verification"] == "verified-official").all()

    def test_boe_all_aggregator_only(self, df: pd.DataFrame) -> None:
        boe = df[df["bank"] == "BOE"]
        assert (boe["verification"] == "aggregator-only").all()

    def test_ecb_has_unverified_years(self, df: pd.DataFrame) -> None:
        """ECB unverified years (2010, 2017, 2018, 2020, 2021) must be training-memory-unverified."""
        ecb = df[df["bank"] == "ECB"].copy()
        ecb["year"] = ecb["date"].dt.year
        for yr in [2010, 2017, 2018, 2020, 2021]:
            yr_rows = ecb[ecb["year"] == yr]
            assert (yr_rows["verification"] == "training-memory-unverified").all(), (
                f"ECB {yr}: expected training-memory-unverified"
            )

    def test_ecb_partial_years_aggregator_only(self, df: pd.DataFrame) -> None:
        """ECB partially-verified years must be aggregator-only."""
        ecb = df[df["bank"] == "ECB"].copy()
        ecb["year"] = ecb["date"].dt.year
        partial_years = [2011, 2012, 2013, 2014, 2015, 2016, 2019, 2022, 2023, 2024, 2025, 2026]
        for yr in partial_years:
            yr_rows = ecb[ecb["year"] == yr]
            assert (yr_rows["verification"] == "aggregator-only").all(), (
                f"ECB {yr}: expected aggregator-only"
            )


class TestWeekdaySanity:
    """
    BoE: all decisions on Thursday (weekday=3) except documented Monday
    election reschedulings (2010-05-10, 2015-05-11).
    All other banks: no weekday constraint enforced (BoJ, ECB, etc. vary).
    """

    def test_boe_thursdays_with_exceptions(self, df: pd.DataFrame) -> None:
        boe = df[df["bank"] == "BOE"].copy()
        boe["date_str"] = boe["date"].dt.strftime("%Y-%m-%d")
        for _, row in boe.iterrows():
            dow = row["date"].dayofweek  # 0=Mon, 3=Thu
            date_str = row["date_str"]
            if date_str in BOE_MONDAY_EXCEPTIONS:
                assert dow == 0, (
                    f"BoE election reschedule {date_str} expected Monday, got weekday {dow}"
                )
            else:
                assert dow == 3, (
                    f"BoE date {date_str} expected Thursday, got weekday {dow}"
                )
