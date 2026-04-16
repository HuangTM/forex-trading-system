# PyBroker Architecture Analysis

Source: [edtechre/pybroker](https://github.com/edtechre/pybroker) (3,248 stars)
Analyzed: 2026-03-30

---

## 1. Overview

ML-integrated backtesting library. Key differentiator: first-class ML model integration with walk-forward retraining. Function-based strategy pattern (not class-based). Dependencies: numpy, numba, pandas, diskcache, joblib.

---

## 2. Module Structure

| File | Purpose |
|------|---------|
| `strategy.py` | Strategy, BacktestMixin, WalkforwardMixin (~1600 lines) |
| `model.py` | ModelSource, ModelTrainer, ModelLoader, ModelsMixin |
| `indicator.py` | Indicator, IndicatorsMixin, built-in indicators |
| `context.py` | ExecContext, PosSizeContext, ExecResult |
| `scope.py` | StaticScope (singleton registry), ColumnScope, IndicatorScope, ModelInputScope, PredictionScope |
| `data.py` | DataSource (ABC), YFinance, Alpaca, AlpacaCrypto |
| `config.py` | StrategyConfig (frozen dataclass) |
| `portfolio.py` | Portfolio, Position, Order, Trade, Stop |
| `cache.py` | diskcache-based caching for data/indicators/models |
| `eval.py` | EvalMetrics, BCa bootstrap confidence intervals (Numba) |
| `slippage.py` | SlippageModel (ABC), RandomSlippageModel |
| `vect.py` | Numba @njit vectorized primitives |

---

## 3. Strategy Pattern: Functions, Not Classes

Register plain Python functions that receive `ExecContext`:

```python
def exec_fn(ctx):
    preds = ctx.preds('my_model')       # ML predictions up to current bar
    high_10d = ctx.indicator('high_10d') # Indicator data up to current bar

    if not ctx.long_pos() and preds[-1] > threshold:
        ctx.buy_shares = 100
        ctx.hold_bars = 5
        ctx.stop_loss_pct = 2
        ctx.score = preds[-1]   # Used for ranking when max_long_positions is set

strategy = Strategy(YFinance(), start_date='1/1/2022', end_date='7/1/2022')
strategy.add_execution(exec_fn, ['AAPL', 'MSFT'], models=my_model, indicators=my_ind)
```

One function per symbol per bar. Strategy class inherits from 5 mixins: `BacktestMixin`, `EvaluateMixin`, `IndicatorsMixin`, `ModelsMixin`, `WalkforwardMixin`.

---

## 4. ML Model Integration

### 4.1 Model Registration (Global Singleton)

```python
def my_train_fn(symbol, train_data, test_data):
    # train_data: DataFrame with OHLCV + indicator columns for TRAINING window
    # test_data: same for TEST window
    model = RandomForestClassifier()
    model.fit(train_data[feature_cols], train_data['target'])
    return model  # Or: return (model, ['col1', 'col2']) to specify input columns

my_model = pybroker.model('my_model', my_train_fn, indicators=[rsi_ind, bb_ind])
```

The tuple return `(model, input_cols)` specifies which columns to feed during prediction.

### 4.2 Training Inside Walk-Forward

```python
for train_idx, test_idx in self.walkforward_split(df, windows, lookahead, train_size):
    train_data, test_data = df.loc[train_idx], df.loc[test_idx]
    # Models trained PER SYMBOL: 2 models x 5 stocks = 10 separate instances
    model_syms = {ModelSymbol(model_name, sym) for sym, model_name in ...}
    models = self.train_models(model_syms, train_data, test_data, indicator_data)
    # Then backtest on test_data with trained models
    self.backtest_executions(..., models=models, test_data=test_data)
```

Indicators computed ONCE for full date range, then sliced into train/test windows.

### 4.3 Lazy Prediction (Critical Optimization)

Predictions computed **ONCE per walk-forward window**, cached, then sliced by `end_index`:

```python
# scope.py - PredictionScope.fetch()
def fetch(self, symbol, name, end_index=None):
    if model_sym in self._sym_preds:
        return self._sym_preds[model_sym][:end_index]  # Cache hit: just slice

    input_ = self._input_scope.fetch(symbol, name)
    pred = trained_model.instance.predict(input_)      # Called ONCE
    self._sym_preds[model_sym] = pred                  # Cache
    return pred[:end_index]
```

The `end_index` simulates time progression without recomputing predictions.

### 4.4 Feature Pipeline

`ModelInputScope` assembles input DataFrame from:
1. All data columns (OHLCV + custom)
2. All indicators registered with this model
3. Filter to `input_cols` if model returned them
4. Apply `input_data_fn` for custom preprocessing

```python
# Default: only indicator columns
df = df[[*self.indicators]]
# Custom: user-defined preprocessing
df = model_source.prepare_input_data(df)
```

---

## 5. Walk-Forward Analysis

Three cases based on `train_size`:
- `train_size == 0`: No training -- pure backtest
- `train_size == 1`: Training only -- no testing
- `0 < train_size < 1`: Standard walk-forward with overlapping windows

```python
# backtest() is walkforward() with windows=1
def backtest(self, ..., train_size=0, ...):
    return self.walkforward(windows=1, train_size=train_size, ...)
```

`lookahead` gap prevents leakage between train/test boundaries.

---

## 6. Position Sizing with ML Confidence

**Score-based ranking:**
```python
def exec_fn(ctx):
    ctx.buy_shares = 100
    ctx.score = preds[-1]  # ML confidence becomes ranking score
# Signals sorted by score descending when max_long_positions is set
```

**Custom position size handler:**
```python
def pos_size_handler(ctx):
    for signal in ctx.signals('buy'):
        if signal.score > high_confidence:
            ctx.set_shares(signal, 200)   # Double allocation
        else:
            ctx.set_shares(signal, 50)    # Smaller position

strategy.set_pos_size_handler(pos_size_handler)
```

Access to `ctx.preds()`, `ctx.indicator()`, `ctx.total_equity`, `ctx.cash`, `ctx.calc_target_shares()`.

---

## 7. Backtesting Loop

```python
for i, date in enumerate(test_dates):
    # 1. Advance end_index for each symbol
    # 2. Execute scheduled orders from previous bars (buy_delay/sell_delay)
    # 3. Check stops (stop_loss, take_profit, trailing_stop)
    # 4. Place cover orders -> sell orders -> buy orders
    # 5. Capture bar state
    # 6. Run before_exec_fn(active_ctxs)   -- cross-symbol logic
    # 7. Run each symbol's exec_fn(ctx)     -- per-symbol logic
    # 8. Run after_exec_fn(active_ctxs)     -- cross-symbol logic
    # 9. Collect results, schedule future orders (buy_delay bars ahead)
```

- **Order delay**: `buy_delay=1` (default) prevents look-ahead bias
- **Order priority**: cover before buy, buy before sell
- **Score ranking** when `max_long_positions` or `pos_size_handler` set

---

## 8. Three-Layer Disk Cache

```python
enable_data_source_cache('namespace')   # Downloaded OHLCV
enable_indicator_cache('namespace')     # Computed indicators
enable_model_cache('namespace')         # Trained model instances
```

Composite keys include symbol, timeframe, date range, indicator/model name. Cache checked before training: if all models cached, skip training entirely.

---

## 9. Indicator System

```python
# Custom indicator
def cmma(bar_data):
    return bar_data.close - np.mean(bar_data.close)
my_cmma = pybroker.indicator('cmma', cmma)

# Built-in helpers
high_10d = pybroker.highest('high_10d', 'close', period=10)
low_20d  = pybroker.lowest('low_20d', 'low', period=20)
ret_5d   = pybroker.returns('ret_5d', 'close', period=5)
```

Dual purpose: used directly in execution functions AND as features for ML models. When passed to `pybroker.model(indicators=[...])`, values auto-added as training DataFrame columns.

Parallel computation via joblib when multiple indicator-symbol pairs.

---

## 10. Key Architecture Patterns

| Pattern | Details |
|---------|---------|
| **Global Registry Singleton** | `StaticScope` holds all indicators, models, caches, columns |
| **Lazy Evaluation + Index Slicing** | Predictions computed once, sliced by end_index per bar |
| **Training Function as Black Box** | `train_fn(symbol, train_data, test_data)` -- any ML framework |
| **Mixin Composition** | Strategy = 5 separate mixins, each for one concern |
| **Execution as Data** | `Execution(symbols, fn, model_names, indicator_names)` -- config as namedtuple |
| **Three-Phase Hooks** | `before_exec_fn` -> `exec_fn` -> `after_exec_fn` for cross-symbol logic |

---

## 11. Comparison with Our System

| Area | Our System (Phase 0) | PyBroker | Recommendation |
|------|---------------------|----------|----------------|
| Strategy pattern | ABC class | Registered functions + ExecContext | Consider function-based for ML strategies |
| ML integration | None | First-class: train/predict/cache pipeline | Adopt for Phase 1 ML |
| Walk-forward | Rolling windows | Rolling + train_size control + lookahead gap | Add lookahead gap parameter |
| Indicators | Computed in pipeline | Global registry, dual-purpose (display + ML features) | Adopt dual-purpose pattern |
| Caching | None | Three-layer disk cache (data, indicators, models) | Add caching for expensive computations |
| Position sizing | ATR fixed fractional | Score-based ranking + custom handler | Add score-based ranking |
| Cross-symbol logic | None | before_exec_fn / after_exec_fn hooks | Add for portfolio-level decisions |
| Order delay | entry_delay_bars | buy_delay / sell_delay (separate) | Add separate buy/sell delays |

### Priority Adoptions for ML Integration

1. **Lazy prediction with index slicing** -- compute once per window, slice per bar
2. **Training function as black box** -- `train_fn(symbol, train_data, test_data)` contract
3. **Three-layer disk cache** -- avoid retraining/recomputing across runs
4. **Score-based position ranking** -- ML confidence drives allocation priority
5. **Dual-purpose indicators** -- same indicators for display and ML features
6. **before/after execution hooks** -- cross-symbol portfolio logic
