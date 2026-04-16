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
