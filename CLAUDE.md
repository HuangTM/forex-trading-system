# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phase 0 baseline forex trading system — proving alpha exists before building complexity. Backtest-only (no live trading). Python 3.11+, ~2,700 LOC.

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
- Fake-edge direction: no margin/liquidation simulation (equity can go negative and "recover"; max_dd clamps at 1.0); static time-invariant swap rates; script-level null gates use in-sample "held-out" tails + hardcoded DSR denominators; FEDFUNDS month-start publication-lag lookahead; no config sets `oos_holdout_start` so the one-shot OOS machinery is disarmed; `run_falsification_trial.py --dry-run` is a free OOS peek.
- False-negative direction: rollover-aware swap silently charges 0 on non-1h bars; `run_walkforward` always runs discrete (vol_target_carry WF tests a degenerate strategy).
- Ops: deploy gate (`assert_deployable`) wired in only 2 of 4 order-capable loops (`run_paper_trading_vt.py` and `run_paper_trading_carry_fred.py` lack it); kill-switch state not persisted in 2 loops; `data/paper_trading_session.log` is test-contaminated (mock rows indistinguishable from broker rows) — never cite it as evidence.

**Pending governance decisions (user/CEO):**
1. honest-N pins fail: 3 sacred tests assert N=30, ledger yields 32 — re-ratify or explain.
2. Whether the R5 correction re-run formally supersedes the 2026-06-06 STEP-4 result.
3. Bet #1 (`data/results/carry_fred_aggregate_2026-04-25.json`, "PASS Sharpe 0.796") was computed on the 3 fake pairs → VOID; re-run on real data is the only open empirical question with new information.

**Test note:** `tests/saxo/test_rem6_429_hardening.py` takes ~9 min (real backoff sleeps); full `pytest tests/` will exceed 10 min.
