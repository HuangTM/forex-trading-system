# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phase 0 baseline forex trading system — proving alpha exists before building complexity. Backtest-only (no live trading). Python 3.11+, ~21k LOC in `src/` (plus ~35k tests, ~18k scripts).

## Commands

```bash
# Install
pip install -e ".[dev]"

# Test
pytest                                    # all tests
pytest tests/backtest/test_engine.py      # single file
pytest -k "test_no_lookahead"             # single test by name
pytest --cov                              # with coverage

# Lint
ruff check src/
ruff format src/

# Run backtests
python scripts/run_backtest.py --config config/default.yaml
python scripts/run_backtest.py --config config/default.yaml --walkforward
python scripts/run_backtest.py --config config/default.yaml --plots
```

## Architecture

Clean architecture with dependency inversion — all modules depend on abstract interfaces in `core/interfaces.py`, never on concrete implementations.

**Data pipeline flow:**
```
Raw OHLCV → Validate → Store (Parquet) → Load → Compute Indicators →
Strategy.generate_signals() → Shift by entry_delay_bars (no lookahead) →
Discretize to positions → Run backtest (sizing, costs) → Metrics → Reports
```

**Module layers** (`src/forex_system/`):

| Layer | Purpose |
|-------|---------|
| `core/` | Domain types (frozen dataclasses), abstract interfaces (`Strategy`, `DataSource`, `CostModel`, `PositionSizer`), YAML config loading, constants, errors |
| `data/` | OHLCV validation (6 quality checks), Parquet I/O, resampling/gap-filling, CSV source |
| `features/` | Pure-function indicators (SMA, EMA, RSI, BB, ATR, momentum) + registry that parses names like `"sma_50"`, `"bb_20_2"` |
| `strategies/` | Three baseline strategies: `ma_crossover` (trend), `bollinger_rsi` (mean-reversion), `momentum`. Factory via `registry.py` |
| `costs/` | `RealisticCostModel`: per-pair spread, slippage, commission, direction-dependent swap |
| `backtest/` | Vectorized engine, 12+ performance metrics, walk-forward validation |
| `analysis/` | Text reports, equity curve / monthly return plots, strategy comparison tables |

## Critical Invariant: No-Lookahead Guarantee

The backtester shifts signals by `entry_delay_bars` (default 1) so signals at bar N execute at bar N+1. This is validated by the **sacred test** `test_no_lookahead` in `tests/backtest/test_engine.py` — it uses a strategy that's trivially profitable WITH lookahead but not with the delay. **Never break this test.** Any change to signal handling or the engine must preserve this guarantee.

## Key Conventions

- **Signals**: floats in [-1.0, +1.0]. +1 = max long, -1 = max short, 0 = flat.
- **Indicator naming**: `{type}_{params}` — e.g., `sma_50`, `bb_20_2`, `atr_14`. Parsed by `features/registry.py`.
- **Strategy creation**: registry/factory pattern in `strategies/registry.py`. Strategy classes implement `Strategy` ABC.
- **Configuration-driven**: all parameters in `config/default.yaml` — pair costs, strategy params, backtest settings, walk-forward windows. No hardcoded magic numbers.
- **Immutable domain types**: `Direction`, `PairInfo`, `Trade`, `BacktestResult` are frozen dataclasses.
- **Pure functions**: indicators and transforms have no side effects.
- **Ruff**: line length 100, target Python 3.11.

## Memory — 2026-08-17 Independent Audit & Fix Cycle

Independent code-level audit (6 areas) + fixes, commits `2b50dd9` (data) / `9a11be6` (wiring).

**Fixed defects (do not re-litigate):**
- 3 daily pairs were SYNTHETIC (AUDUSD/USDCAD/EURGBP); replaced with real HistData M1→daily data, quarantined at `data/raw/quarantine_fake_daily_2026-08-17/`, range bounds now enforced in `storage.py`. Provenance: `references/histdata_daily_PROVENANCE.md`.
- JPY rates were frozen at 2017-04; rebuilt through 2026-06, `rate_differentials.parquet` regenerated (12 cols), provenance in `references/rates_PROVENANCE.md`.
- USDJPY 4h spreads were in pipettes; fixed via `scripts/fix_usdjpy_4h_spread_units.py`. `saxo/history.py` pip heuristic replaced with pair-based rule.
- `allow_shorts` was parsed but never forwarded (M1/M2 basket ran long-only); now forwarded everywhere. Re-run: FAMILY_KILL **unchanged** — short legs improve economics but don't clear the 7.5-pip cost wall. Addenda in `references/pre-registrations/macd_cross.md` / `ema_cross.md`.
- `ContinuousSizer` in continuous mode on JPY pairs carried ~1/150 intended risk (unit contract); new `usd_nominal=True` flag. `min_order_size` clipping is now loud (`n_clipped_to_zero`). R5 STEP-4 correction re-run: AMBIGUOUS_GATE_FAIL **unchanged**; see `references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.superseded.md`.

**Known issues NOT yet fixed (audit backlog, by direction of bias):**
- Fake-edge direction: no margin/liquidation simulation (equity can go negative and "recover"; max_dd clamps at 1.0 — 2026-10-25 retest Part B showed it can invalidate a portfolio result outright); static time-invariant swap rates (opt-in `RateDifferentialSwapCostModel` now exists; `RealisticCostModel` still static); script-level null gates use in-sample "held-out" tails + hardcoded DSR denominators; FEDFUNDS month-start publication-lag lookahead; no config sets `oos_holdout_start` so the one-shot OOS machinery is disarmed; `run_falsification_trial.py --dry-run` is a free OOS peek.
- False-negative direction: rollover-aware swap silently charges 0 on non-1h bars; `run_walkforward` always runs discrete (vol_target_carry WF tests a degenerate strategy).
- Ops: deploy gate (`assert_deployable`) wired in only 2 of 4 order-capable loops (`run_paper_trading_vt.py` and `run_paper_trading_carry_fred.py` lack it); kill-switch state not persisted in 2 loops; `data/paper_trading_session.log` is test-contaminated (mock rows indistinguishable from broker rows) — never cite it as evidence.

**Pending governance decisions (user/CEO):**
1. ~~honest-N pins~~ RESOLVED 2026-10-26: the extra 2 were M1/M2 1h trials (82497d05, b309935c) that ran 2026-06-17 but were never added to the pin. With the carry retest (65d10ede) and fix-reversal (62a72f65) rows appended, the deflation denominator is **34** (owner re-ratified; pins updated) and the de-dup view is 13.
2. Whether the R5 correction re-run formally supersedes the 2026-06-06 STEP-4 result.
3. Bet #1 (carry_fred): the 2026-04-25 "PASS 0.796" is VOID (fake pairs); the 2026-08-23 "PASS again 0.6582" is SUPERSEDED (lump-sum swap artifact; CF-T8 fired unreported). See the 2026-10-25 section below — **FAIL**. Remaining: owner sign-off that Bet #1 is closed.

## Memory — 2026-10-25 Swap-Accounting Fix & Two Pre-Registered Tests

Merged to `main` and pushed 2026-10-26. Each pre-registration was committed before its run.

- **Engine fix `012f6c1`:** discrete mode now accrues swap per elapsed calendar day (was a lump sum at trade exit — e.g. NZDJPY +16% on one day). Per-trade totals and final equity unchanged (verified ~1e-7 USD on 16 backtests); only the equity path moves. `CostModel.holding_cost` gained an optional `timestamp`.
- **Data fix `05e41c1`:** EUR rate was frozen at 4.25% from 2000-06 to 2008-12 (FRED `ECBMRRFR` has no values during the ECB's variable-rate tenders); filled with the ECBDFR/ECBMLFR corridor midpoint. 2010+ data unaffected (bit-identical).
- **carry_fred retest (`carry_fred_retest_2026-10-25.RESULT.md`): FAIL.** 2010–2026: OOS SR 0.915 but IS SR 0.20 (CF-T8) and 0.075 at 2× costs (CF-T6); DSR(N=33) 0.31. A naive equal-weight long-6-JPY-crosses basket beats every carry_fred variant. Blind 2003–2009 holdout: the pre-registered number is invalid (EURGBP sleeve wiped out, no margin sim); post-hoc pooled-account SR 0.23 (t 0.62).
- **Fix-reversal test (Krohn/Mueller/Whelan JF 2024, `fix_reversal_1h.RESULT.md`): FAIL.** The gross pattern replicates out of sample (+1.95 bp/day, t 1.98, 6 USD pairs 2021–2025), but 4 round trips/day cost 7–10 bp/day; net −8.5 bp/day. Break-even needs ~0.5-pip round-trip all-in cost.
- Exploratory (not pre-registered): an equal-weight combination of MA 50/200, BB+RSI, momentum 20, MACD and carry_fred loses money (IS −0.45 / OOS −0.35). Pre-2010 daily data (HistData 2002–2009, bad ticks cleaned by USD-leg triangulation) lives in `data/holdout_pre2010/` (gitignored).

**Test note:** `tests/saxo/test_rem6_429_hardening.py` takes ~9 min (real backoff sleeps); full `pytest tests/` will exceed 10 min.
