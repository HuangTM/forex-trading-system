# COT positioning vs carry: signal-only overlap check (2026-10-29)

Not a trial; honest N is unchanged (35). This check runs before any COT pre-registration,
to decide whether a "carry conditioned on speculative positioning" bet is worth spending
trial #36 on. It read only interest rates and CFTC positions. No spot rate was loaded, so
no return of any kind was computed.

Inputs:
- `data/factors/raw/cot_legacy_fx.csv`, built by `scripts/fetch_cot_legacy_fx.py`. Source is
  the CFTC legacy futures-only COT, joined by contract code across name changes, with the
  1986 ECU rows dropped.
- `data/rates/raw`, with the same publication lags as `run_fx_multifactor.py --pit-rates`.

Script: `scripts/check_cot_signal_overlap.py`. Output: `data/results/cot_signal_overlap_2026-10-29.json` (gitignored).

Universe: the 6 foreign currencies of the multifactor test (EUR, JPY, GBP, AUD, NZD, CAD),
ranked among themselves, with no USD score. Formation months are 2000-12 to 2026-08 (309 in all).
At each formation date the script uses the latest COT report released before the month's last
business day, taking release as the as-of date + 3 days. Shutdown delays are not modelled.
47 months have NZD missing (2000-12..2005-07) and 1 month has AUD missing.

## Results

| Statistic (monthly cross-section, Spearman) | full | pre-2012 | post-2012 |
|---|---|---|---|
| carry rank vs net-speculative/OI **level** rank, mean | 0.31 | 0.44 | 0.21 |
| same, share of months > 0.5 | 0.38 | 0.50 | 0.29 |
| carry rank vs **3-year own-history z-score** of net/OI, mean | −0.04 | 0.01 | −0.08 |

- The composite weights from carry rank minus positioning-level rank have a mean correlation
  of 0.55 with the carry weights. They are never negative.
- Mean monthly turnover (Σ|Δw|, gross exposure 2) is 0.13 for carry, 1.08 for
  positioning-level and 1.16 for the composite.

## Reading

- **The positioning level partly restates carry.** Speculators are long high-carry currencies:
  the mean correlation is 0.31, rising to 0.44 before 2012. The composite therefore does not
  collapse into noise; it keeps about half of carry's ordering. But most of what it adds comes
  from a signal that turns over roughly 8× faster than carry.
- **Crowding measured against a currency's own history is orthogonal to carry** (≈0).
  If the bet is run, this is the measure to use. It matches the time-series crowding of
  Brunnermeier/Nagel/Pedersen (2008), and it is genuinely new information relative to carry.
- Orthogonality says nothing about predictive power. Whether the z-score improves carry net of
  costs is exactly what a pre-registered paired test would have to show.
- This check only rules out one failure mode, signal collapse. It does not lower the DSR(N=36)
  hurdle of SR ≈ 0.75–0.80. A devil's-advocate review raised other points that still apply to
  any pre-registration: the Friday month-end release timing, the shutdown release dates, the
  forward window not being confirmatory, and pre-2012 being in practice in-sample.
