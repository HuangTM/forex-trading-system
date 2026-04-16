# backtesting.py Architecture Analysis

Source: [kernc/backtesting.py](https://github.com/kernc/backtesting.py) (8,133 stars)
Analyzed: 2026-03-30

---

## 1. Overview

Remarkably compact (~3,800 LOC across 6 files) backtesting library. Only 3 runtime dependencies: numpy, pandas, bokeh. Known for simplicity and interactive plotting. Key design: **hybrid architecture -- vectorized indicators + event-driven execution**.

---

## 2. File Structure

| File | Lines | Purpose |
|------|-------|---------|
| `backtesting.py` | 1,750 | Core: Strategy, Order, Trade, Position, _Broker, Backtest |
| `_plotting.py` | 785 | Interactive Bokeh plotting |
| `lib.py` | 646 | Composable strategies, utilities, MultiBacktest |
| `_util.py` | 337 | _Data, _Array, _Indicator, SharedMemory for multiprocessing |
| `_stats.py` | 212 | Statistics (Sharpe, Sortino, drawdown, etc.) |
| `__init__.py` | 95 | Package init, configurable multiprocessing Pool |

---

## 3. Strategy Interface

Users override exactly two methods:

```python
class Strategy(metaclass=ABCMeta):
    @abstractmethod
    def init(self):
        """Declare indicators with self.I()."""

    @abstractmethod
    def next(self):
        """Called on each bar. Make trading decisions."""
```

**Properties in `next()`:** `self.data`, `self.equity`, `self.position`, `self.orders`, `self.trades`, `self.closed_trades`

**Order placement:**
```python
def buy(self, *, size=_FULL_EQUITY, limit=None, stop=None, sl=None, tp=None, tag=None) -> Order
def sell(self, *, size=_FULL_EQUITY, limit=None, stop=None, sl=None, tp=None, tag=None) -> Order
```

**Parameters as class attributes** (no registration system):
```python
class SmaCross(Strategy):
    n1 = 10   # Optimizable parameter
    n2 = 20

    def init(self):
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)
```

The optimizer discovers params from `kwargs` and mutates via `setattr`.

---

## 4. The Hybrid Engine

**Phase 1: Vectorized precomputation** (in `Strategy.init()`):
- All indicators computed over FULL data array at once via `self.I(func, *args)`
- numpy/pandas/TA-Lib run at full vectorized speed

**Phase 2: Event-driven bar-by-bar simulation** (in `Backtest.run()`):
```python
strategy.init()              # Vectorized precompute
start = 1 + _indicator_warmup_nbars(strategy)  # Auto-detect warmup

for i in range(start, len(self._data)):
    data._set_length(i + 1)  # Progressive reveal (O(1), numpy view)
    for attr, indicator in indicator_attrs:
        setattr(strategy, attr, indicator[..., :i + 1])  # Also a view
    broker.next()       # Process pending orders
    strategy.next()     # User's decision logic
```

**Critical performance trick:** `_Data._set_length(i)` changes only a length counter. Array access returns `array[:length]` -- a numpy view, not a copy. Zero-copy progressive data reveal.

---

## 5. The I() Pattern

```python
def I(self, func, *args, name=None, plot=True, overlay=None, color=None, scatter=False, **kwargs):
```

1. Calls `func(*args, **kwargs)` during `init()` for full indicator array
2. Validates result length matches data
3. Wraps in `_Indicator` (numpy subclass with `.name`, `.s`, `.df` and plot metadata)
4. Stores in `self._indicators` for automatic plotting
5. During `next()`, progressively sliced to `indicator[..., :i+1]`

**Auto-overlay detection:** if most values are within 30% of Close, overlays on price chart.

**Auto-warmup detection:** finds first non-NaN bar across all indicators; simulation starts after warmup.

**Library-agnostic:** `func` can be TA-Lib, pandas rolling, custom numpy, or a lambda. Only requirement: returns array of `len(data)`.

---

## 6. Backtest Class API

```python
bt = Backtest(data, Strategy,
    cash=10_000,
    spread=0.,              # Constant bid-ask spread (useful for forex)
    commission=0.,          # Float, (fixed, relative) tuple, or callable
    margin=1.,              # margin=0.02 means 50:1 leverage
    trade_on_close=False,
    hedging=False,          # Allow simultaneous long/short
    exclusive_orders=False, # Auto-close previous on new order
    finalize_trades=False,  # Force-close open trades at end
)

stats = bt.run(**kwargs)    # kwargs override class-level params
stats = bt.optimize(maximize='SQN', method='grid', **param_ranges)
bt.plot(results=stats)
```

---

## 7. Position Sizing

- `size` between 0 and 1 (exclusive): fraction of available equity
- `size` >= 1 (integer): absolute number of units
- Default `_FULL_EQUITY = 1 - sys.float_info.epsilon`: use all available equity

FIFO trade closing when `hedging=False`: opposite-direction orders close existing trades first. Matches NFA Compliance Rule 2-43b (relevant for forex).

**Writable SL/TP after trade creation:**
```python
for trade in self.trades:
    trade.sl = max(trade.sl or -np.inf, self.data.Close[-1] - atr * 2)
```

---

## 8. Order Types

- **Market**: no limit/stop -- fills at next bar open (or current close if `trade_on_close=True`)
- **Limit**: fills when price reaches limit
- **Stop**: triggers on stop price, becomes market
- **Stop-limit**: both stop and limit set
- **Bracket**: `sl` and `tp` create automatic contingent OCO orders

---

## 9. Optimization System

**Grid search** (`method='grid'`):
- Cartesian product of all parameter combinations
- User `constraint` function for filtering
- Randomized subsampling via `max_tries`
- Parallelized via multiprocessing with **shared memory** for OHLC DataFrame
- Default maximize: SQN (System Quality Number)

```python
stats = bt.optimize(
    n1=range(5, 30, 5),
    n2=range(10, 70, 5),
    maximize='Sharpe Ratio',
    constraint=lambda p: p.n1 < p.n2,
    return_heatmap=True
)
```

**SAMBO optimization** (`method='sambo'`): Bayesian optimization with `lru_cache` memoization. Supports mixed integer/float/categorical spaces.

**Shared memory** avoids DataFrame serialization across processes.

---

## 10. Plotting

Bokeh-based interactive HTML. Indicator metadata flows through `_Indicator._opts`. Auto-resampling for >10,000 candles. Superimposed timeframes (daily gets monthly overlay). Synchronized panning/zooming across equity curve, drawdown, volume, indicators.

---

## 11. Composable Strategies (lib.py)

**SignalStrategy** -- bridge vectorized and event-driven:
```python
class MyStrategy(SignalStrategy):
    def init(self):
        super().init()
        self.set_signal(sma1 > sma2, sma1 < sma2)
```

**TrailingStrategy** -- automatic ATR trailing stop:
```python
class MyStrategy(TrailingStrategy):
    def init(self):
        super().init()
        self.set_trailing_sl(n_atr=3)
```

**MultiBacktest** -- one strategy across multiple instruments:
```python
btm = MultiBacktest([EURUSD, BTCUSD, GOOG], SmaCross)
stats_df = btm.run(fast=10, slow=20)
```

**Utilities:** `crossover()`, `cross()`, `barssince()`, `quantile()`, `resample_apply()`, `random_ohlc_data()` (Monte Carlo).

---

## 12. What Makes It Lightweight

1. **3 runtime dependencies** (numpy, pandas, bokeh)
2. **No indicator library bundled** -- `I()` accepts ANY function returning an array
3. **numpy arrays during simulation**, not pandas Series
4. **Zero-copy progressive reveal** via numpy view slicing
5. **Single-file core engine** (1,750 lines)
6. **Broker is internal** -- no public Broker API
7. **Parameters as class attributes** -- no registration/schema system
8. **Statistics computed once after run** -- no running accumulators
9. **Public API is 4 classes** (Backtest, Strategy, Order, Trade)

---

## 13. Comparison with Our System

| Area | Our System (Phase 0) | backtesting.py | Recommendation |
|------|---------------------|----------------|----------------|
| Architecture | Vectorized pipeline | Hybrid (vectorized indicators + event-driven execution) | Adopt hybrid for flexibility without losing speed |
| Indicator pattern | compute_indicators() | I(func, *args) -- library-agnostic | Adopt I() pattern for user strategies |
| Data reveal | Full array at once | Progressive numpy views (zero-copy) | Adopt for lookahead safety |
| Position sizing | ATR fixed fractional | Fractional equity + absolute units | Add fractional equity mode |
| Optimization | None | Grid search + Bayesian (SAMBO) + shared memory multiprocessing | Adopt grid search with shared memory |
| Plotting | matplotlib | Bokeh interactive HTML | Consider Bokeh for exploration |
| Order types | Market only (implicit) | Market, limit, stop, stop-limit, bracket (OCO) | Add limit/stop orders |
| Parameters | Config YAML | Class attributes + optimizer discovery | Add class-level params for user strategies |
| Spread model | Per-pair config | Global constant | Keep per-pair (more realistic for forex) |

### Priority Adoptions

1. **Hybrid architecture** -- vectorized indicators + event-driven execution
2. **I() pattern** -- library-agnostic indicator registration with auto-plotting
3. **Zero-copy progressive data reveal** -- numpy view slicing for lookahead safety
4. **Grid search optimization** -- with shared memory multiprocessing
5. **Bracket orders (OCO)** -- SL + TP as contingent orders
6. **SignalStrategy base class** -- easy bridge for vectorized-signal users
