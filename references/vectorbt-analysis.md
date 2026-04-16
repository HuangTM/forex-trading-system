# vectorbt Architecture Analysis

Source: [polakowo/vectorbt](https://github.com/polakowo/vectorbt) (7,027 stars)
Analyzed: 2026-03-30

---

## 1. Overview

Vectorized backtesting engine focused on speed through NumPy + Numba JIT compilation. Key strength: parameter sweeps across thousands of combinations in a single pass. Dependencies: numpy, pandas, numba, scipy, plotly.

---

## 2. Module Structure

| Module | Purpose |
|--------|---------|
| `portfolio/` | Portfolio simulation engine (the core) |
| `signals/` | Signal generation, combination, stop-loss logic |
| `indicators/` | Indicator computation via factory pattern |
| `generic/` | Low-level numba primitives (rolling, ewm, diff) |
| `base/` | Broadcasting, array wrapping, flexible indexing |
| `data/` | Data fetching (YFinance, CCXT, Alpaca) |
| `records/` | Record-based storage for orders, trades, drawdowns |
| `utils/` | Config, math tolerances, decorators, caching |

---

## 3. Signal Representation

Signals are **boolean 2D NumPy arrays** where `True` marks entry/exit. Four direction-aware signals: `is_long_entry`, `is_long_exit`, `is_short_entry`, `is_short_exit`.

Three input modes:
1. **Simple**: `entries` + `exits` with `direction` parameter
2. **Direction-aware**: `entries`, `exits`, `short_entries`, `short_exits`
3. **Dynamic**: Numba-compiled `signal_func_nb` callback

**Conflict resolution** (when entry and exit fire simultaneously):
- `ConflictMode.Ignore`: keep both
- `ConflictMode.Entry`: entry wins
- `ConflictMode.Exit`: exit wins
- `ConflictMode.Opposite`: take opposite of current position

---

## 4. Three-Tier Portfolio Simulation

All tiers use Numba JIT loops (not pure vectorization), achieving near-vectorized speed.

### Tier 1: `from_orders` -- Array-driven

All order parameters pre-specified as arrays:

```python
@njit(cache=True)
def simulate_from_orders_nb(target_shape, group_lens, init_cash, call_seq,
                            size, price, size_type, direction, fees, ...):
    for group in range(len(group_lens)):
        for i in range(target_shape[0]):        # time
            for k in range(group_len):           # assets
                order = order_nb(
                    size=flex_select_auto_nb(size, i, col, flex_2d),
                    price=order_price[col], ...
                )
                order_result, new_state = process_order_nb(...)
```

### Tier 2: `from_signals` -- Signal-driven

Adds signal resolution before order creation:
1. Check stop signals (SL/TP/trailing)
2. Call `signal_func_nb` for user signals
3. Resolve entry/exit/direction conflicts
4. Convert signals to size via `signals_to_size_nb`
5. Create and process order

### Tier 3: `from_order_func` -- Callback-driven

Full callback hierarchy:
```
pre_sim_func_nb
  pre_group_func_nb
    pre_segment_func_nb    <-- set call sequence, override val_price
      order_func_nb        <-- generate order for each (row, col)
      post_order_func_nb   <-- check result, custom logging
    post_segment_func_nb
  post_group_func_nb
post_sim_func_nb
```

`flex_simulate_nb` allows **multiple orders per bar per symbol** with runtime-determined call sequence.

---

## 5. Indicator System

**Factory pattern** generates indicator classes declaratively:

```python
MA = IndicatorFactory(
    class_name='MA',
    input_names=['close'],
    param_names=['window', 'ewm'],
    output_names=['ma']
).from_apply_func(
    nb.ma_apply_nb,
    cache_func=nb.ma_cache_nb,
    ewm=False, adjust=False
)
```

**Caching across parameter sweeps** -- compute each unique combination once:

```python
@njit(cache=True)
def ma_cache_nb(close, windows, ewms, adjust):
    cache_dict = dict()
    for i in range(len(windows)):
        h = hash((windows[i], ewms[i]))
        if h not in cache_dict:
            cache_dict[h] = ma_nb(close, windows[i], ewms[i], adjust=adjust)
    return cache_dict
```

When testing 1000 window sizes, each unique window is computed once. `run_combs` generates all r-combinations. `run_unique` deduplicates before running.

---

## 6. Performance Optimization Techniques

### a) Numba JIT

Every hot-path function: `@njit(cache=True)`. Persists compiled bytecode to disk.

### b) Flexible indexing (zero-copy broadcasting)

```python
@njit(cache=True)
def flex_select_auto_nb(a, i, col, flex_2d=True):
    """Select element as if array was broadcast, without copying."""
```

Handles 0-dim (scalar), 1-dim (per-row or per-column), 2-dim (per-element), and singleton dimensions. Passing `fees=0.001` (scalar) costs zero memory vs a full `(5000, 100)` array.

### c) Pre-allocated record arrays

```python
order_records = np.empty(_max_orders, dtype=order_dt)
```

Filled in-place during simulation, truncated at end. Avoids Python object overhead.

### d) Numba typed dicts

Hash-based deduplication for indicator caching across parameter sweeps.

### e) Column-major traversal

Default: process all rows of column 0, then column 1. Better cache locality for time-series data. `simulate_row_wise_nb` available for row-major when needed.

### f) Segment masks

2D boolean array to skip entire segments where no computation needed.

### g) Auto call sequence sorting

When cash sharing enabled, sorts columns so sells execute before buys (releasing cash first).

---

## 7. Position Sizing

Six `SizeType` modes:

| Mode | Meaning |
|------|---------|
| `Amount` | Absolute units |
| `Value` | Dollar value |
| `Percent` | % of available resources |
| `TargetAmount` | Target position in units (delta computed) |
| `TargetValue` | Target position in dollar value |
| `TargetPercent` | Target position as % of portfolio value |

Normalization chain: `TargetPercent -> TargetValue -> TargetAmount -> Amount`

Partial fills supported (if insufficient cash, fill for max affordable). Cash locking prevents multiple orders exceeding free cash in shared groups.

---

## 8. The `from_signals` Pattern (Complete Flow)

```
User provides: close, entries, exits, size, fees, sl_stop, tp_stop, ...
  |
  from_signals() [Python]
  |
  Broadcasting: all arrays to common shape (flexible indexing, no copies)
  |
  simulate_from_signal_func_nb() [Numba]
  |
  For each (group, row, col):
    1. Resolve stop signals (SL/TP/trailing)
    2. Get user signals via signal_func_nb
    3. Resolve conflicts
    4. signals_to_size_nb -> (size, size_type, direction)
    5. order_nb -> Order namedtuple
    6. process_order_nb -> execute, fill records
    7. Update state (cash, position, debt)
  |
  Return: order_records, log_records
  |
  Portfolio.__init__() -> lazy metrics via @cached_method
```

---

## 9. Key Differences: Vectorized vs Event-Driven

| Aspect | vectorbt | Event-Driven (e.g., Backtrader) |
|--------|----------|--------------------------------|
| Signal generation | Entire boolean arrays upfront | Bar-by-bar |
| Parameter sweeps | 10,000 combos in one pass | One backtest per combination |
| Speed | Numba JIT + vectorized ops | Pure Python per-bar loops |
| Memory model | Flexible indexing, scalars stay scalar | Often full arrays per parameter |
| Order execution | Pre-allocated record arrays | Object creation per event |
| Indicator computation | Cached across all combos | Recomputed each run |
| Look-ahead bias | Must manually shift signals | Framework prevents by design |
| Multi-order per bar | Only in flex_simulate_nb mode | Natural in event loop |
| Code style | Numba functions, no classes in hot path | OOP with strategy classes |

---

## 10. Comparison with Our System

| Area | Our System (Phase 0) | vectorbt | Recommendation |
|------|---------------------|----------|----------------|
| Simulation | Vectorized (iterrows) | Numba JIT loops | Adopt Numba for 10-100x speedup |
| Signals | Continuous [-1,+1] | Boolean arrays | Keep continuous; add boolean mode for simple strategies |
| Parameter sweeps | None | Broadcasting across thousands of combos | Critical for Phase 1 optimization |
| Indicators | Pure numpy/pandas | Factory + cache across param combos | Adopt caching pattern for optimization |
| Position sizing | ATR-based fixed fractional | 6 SizeType modes + partial fills | Adopt target-based sizing modes |
| Records | Python list of Trade dataclasses | Pre-allocated numpy structured arrays | Adopt for performance |
| Stop logic | In backtest engine | In signal resolution layer | Separate stop logic from engine |

### Priority Adoptions

1. **Numba JIT compilation** -- wrap hot-path functions with `@njit(cache=True)`
2. **Flexible indexing** -- zero-copy broadcasting for parameter sweeps
3. **Indicator caching** -- compute each unique param combo once
4. **Pre-allocated record arrays** -- structured numpy arrays for orders/trades
5. **Three-tier simulation API** -- simple/signal/callback modes for different use cases
6. **Float tolerance handling** -- `is_close_nb`, `add_nb` for forex position accumulation
