# RESULT: FX fix-reversal on 1h data, 2021–2025 (2026-10-25)

Pre-registration `fix_reversal_1h.md` (frozen `796951b`, before the run).
kill_switch_threshold: 0.0
(as pre-registered; this file records results, it declares no new trial)
Artifact: `data/results/fix_reversal_1h_2026-10-25.json`.

## Verdict: FAIL (primary: combined schedule × CD0 costs)

| Cell (6-pair dollar portfolio) | bp/day | ann. | Sharpe | t |
|---|---|---|---|---|
| Combined, **gross** | **+1.95** | +5.1% | 0.89 | 1.98 (p_boot 0.007) |
| Combined, spread only | −5.17 | −13.5% | −2.35 | −5.24 |
| **Combined, CD0 (primary)** | **−8.49** | −22.2% | −3.85 | −8.61 |
| Combined, skip 17:00 ET bar, CD0 | −7.27 | −19.0% | −3.29 | −7.36 |
| Tokyo only, gross / CD0 | +0.58 / −4.73 | | 0.48 / −3.96 | |
| Europe only, gross / CD0 | +1.37 / −3.81 | | 0.73 / −2.02 | |

- **The gross pattern replicates out of sample** (entirely after the paper's
  1999–2019 sample): +1.95 bp/day, t = 1.98. Strongest piece: USD appreciation
  before the ECB fix in all 6 pairs (+1.0 to +2.0 bp/day). Post-London USD weakness
  holds for EUR/GBP/NZD/CAD, not AUD; USDJPY moves the other way (the paper's yen
  exception). Tokyo reversal is weak (t ≈ 1.1), consistent with the paper's
  post-2013 decay. Gross by year: 1.95, 4.78, 1.45, 1.92, **−0.36 (2025)**.
- **Costs are ~4–5× the edge.** 4 round trips/day per pair cost ≈ 7 bp/day at
  Dukascopy spreads alone and ≈ 10 bp/day with CD0 slippage, vs ~2 bp/day gross.
  Every pair is negative net, under both cost models, in every year.
- Break-even all-in cost ≈ 1.95 bp / 8 position-units ≈ 0.24 bp per side, i.e. about
  0.5 pip round trip on EURUSD, including the 17:00 ET rollover hour and the wider
  AUD/NZD books. That is below a retail ECN all-in cost (~0.7–1.0 pip) on EURUSD
  alone. This matches the paper's own Section V.E conclusion.

## Post-hoc observation (NOT a result — selected after seeing this data)

The pre-ECB window alone (1 round trip/day) earned +1.0–2.0 bp/day gross, roughly the
size of one CD0 round trip (~1–1.7 bp), so at best around break-even. Choosing it now
from this data would be data-mining; it could only be tested on data not used here
(e.g. pre-2021 Dukascopy) or forward.
