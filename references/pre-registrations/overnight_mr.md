# Pre-Registration: overnight_mr (A2′)

**Status:** Frozen pre-registration, EXECUTED as trial 48 → result KILL-1 (see Outcome below)
**Date frozen:** 2026-06-17 (before any IS look; Principal-Reviewer cycle-2 APPROVED)
**Strategy ID:** overnight_mr
**Pair:** EURUSD (1h bars)
**Trial:** 48 — `trial_id: 15923fe1` (org-wide N = 48 at execution)
**Canonical frozen spec:** `.fintech-org/artifacts/2026-06-17T02-37-59Z_intraday_eurusd_1h/qr-prereg-v2.yaml`
**Parent CONSENSUS:** `CONSENSUS.md` (intraday EURUSD 1h strategy-design; fintech-org cycle 2026-06-17)
**CEO ratification:** "proceed with fixes" → `.agent-accountability/ratifications/intraday-eurusd-1h-strategy-design:phase1:task1.0.yaml`

## Hypothesis (the NULL being tested)

During the low-liquidity UTC overnight window (02:00–05:00), an EURUSD hour that closes
beyond its own same-hour-class volatility (|r_t| ≥ 2.0·σ_sess, close-to-close) over-extends
on transient inventory/liquidity-demand flow rather than information, so the next single hour
partially reverts. **The NULL (H0):** the sign-reversed (fade) return on the bar following an
over-extended overnight hour has expected value ≤ 0 net of a frozen, conservative, session-aware
round-trip cost; any positive in-sample Sharpe is multiple-testing/selection (captured by the
N=48 Deflated-Sharpe deflation).

## Mechanism

`src/forex_system/strategies/overnight_mr.py` (`OvernightMRStrategy`). On each completed 1h bar t:
- Entry universe = UTC hour ∈ {02,03,04,05} (via `src/forex_system/backtest/session_filter.py`).
- σ_sess = stdev of 1h log-returns over the trailing 20 bars of the SAME UTC-hour-class, computed
  STRICTLY from bars ≤ t-1 (current bar EXCLUDED — no-lookahead by construction).
- Signal: SHORT if r_t ≥ +2.0·σ_sess; LONG if r_t ≤ −2.0·σ_sess; else flat (fade). Engine shifts by
  `entry_delay_bars=1` (signal at t executes t+1; `test_no_lookahead` preserved).
- Single-bar hold (exit at t+1 close); per-trade stop = 1.0·σ_trigger adverse cap + 1-bar time-stop.
- Weekend/holiday NO-TRADE: the last in-window bar before a Fri/holiday gap is NO-TRADE (never held
  across the gap); σ window skips gap bars (no forward-fill).
- Cost: `src/forex_system/costs/static_roundtrip.py` (`StaticRoundTripCostModel`), FROZEN 7.5-pip
  conservative round-trip (overnight-P90-grade, justified from `data/spreads/EURUSD_4h_spreads.parquet`;
  the 1h OHLCV parquet has no bid/ask column, so a per-bar realized-spread gate is uncomputable —
  PR finding F-006). Size: vol-targeted, size_multiplier 0.25.

All degrees of freedom are LOCKED before any IS look (no grid/sweep — a search would inflate N):
session window {02,03,04,05} UTC · σ-lookback 20 same-hour-class · k=2.0 · static cost 7.5 pips ·
0.30 reversion-capture coefficient (feasibility projection only) · 1σ stop · 1-bar time-stop · size 0.25.

## Falsification Criteria

FALSIFIED (status: rejected) if ANY trigger fires. Pre-OOS gates (IS only) are checked first; the
one-shot OOS holdout is burned ONLY if all pre-OOS gates pass.

- **KILL-4 (power, IS-only extrapolation):** f_IS = qualifying IS trades / IS trading days;
  N_oos_expected = f_IS × OOS trading-day count (from calendar, NOT by reading OOS data).
  If N_oos_expected < 48 → INSUFFICIENT-POWER, OOS never burned.
- **KILL-1 (DSR):** IS net-of-cost Deflated Sharpe ≤ 0.95 at org-wide N=48 → KILL.
- **KILL-2 (cost domination):** avg net trade ≤ 0 pips after the 7.5-pip cost on the 2σ subset → KILL.
- **KILL-3 (reversion is information):** 2σ single-bar reversion hit-rate ≤ 0.50 → KILL.
- **KILL-5 (forward-decay, OOS):** OOS net annualized Sharpe < 0.30 → KILL.
- **KILL-6 (sign-inversion, OOS):** OOS net Sharpe sign ≠ IS sign → KILL.
- **KILL-7 (concentration):** any single calendar quarter > 40% of net PnL → KILL.

`kill_switch_threshold: 0.30` (OOS net annualized Sharpe floor; KILL-5)

## OOS Sample Discipline

`oos_overlap: false`
`is_window: 2021-01-03 .. 2024-05-31`
`seam_embargo: 2024-06 (≥20 trading days, discarded)`
`oos_window_start: 2024-07-01`
`oos_window_end: 2025-12-31`
`oos_one_shot: true` (burned exactly once, and only if all pre-OOS gates pass)
`cpcv: 6 groups, k=2, purge/embargo = ~480 bars (full same-hour-class feature window)`

## Approval

- **HoQR:** prioritization + debate-r1 (`hoqr-prioritization.yaml`, `hoqr-debate-r1.yaml`) — approved
  to run as a cost-aware falsification; rates expectancy TRAP (cost-dominated).
- **Quant-Researcher:** author of frozen spec (`qr-prereg-v2.yaml`).
- **CRO:** size_multiplier 0.25; veto lifted by the per-trade stop (`cro-risk-assessment.yaml`).
- **NHT:** STRETCH / survives at design; no formal dissent (`nht-confirmability.yaml`).
- **Principal-Reviewer:** cycle-2 APPROVE, all blocking findings closed (`pr-cycle2-closure.yaml`).
- **CEO:** ratified "proceed with fixes".

## Outcome (recorded post-run — IS only, OOS never burned)

Ran 2026-06-17 (`scripts/trial_48_is_eval.py`). **Result: KILL-1** (and KILL-2 corollary).
- KILL-4 power: N_oos_expected = 83.5 ≥ 48 → did not fire.
- **KILL-1: CPCV net Sharpe = −4.93 → DSR = 0.00 at N=48 → FIRES.**
- KILL-2: avg net trade = −4.09 pips → fires.
- KILL-3: reversion hit-rate = 0.5517 > 0.50 → did NOT fire (directional MR edge is real).

Per-trade GROSS fade capture = +3.41 pips (positive, 55% hit-rate) but dominated by the 7.5-pip
conservative cost → nets −4.09. NHT confirmed a CLEAN falsification (sign convention traced correct;
not a bug). **H0 stands: single-pair EURUSD 1h overnight mean-reversion is cost-dominated, not
tradeable.** The one-shot OOS holdout (2024-07..2025-12) was NEVER read. Counts toward the org-wide
Deflated-Sharpe denominator (honest-N = 48).
