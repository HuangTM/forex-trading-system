# Freqtrade Architecture Analysis

Source: [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) (48,197 stars)
Analyzed: 2026-03-30

---

## 1. Strategy Plugin System

Strategies subclass `IStrategy` and override three methods:

| Method | Purpose |
|--------|---------|
| `populate_indicators(df, metadata)` | Add all indicator columns to the DataFrame |
| `populate_entry_trend(df, metadata)` | Set `enter_long=1` / `enter_short=1` columns |
| `populate_exit_trend(df, metadata)` | Set `exit_long=1` / `exit_short=1` columns |

### Signal Model

Signals are **binary 0/1 integer columns** in the DataFrame, not continuous floats. Entry and exit are separate signals. Signal columns:

| Column | Value | Meaning |
|--------|-------|---------|
| `enter_long` | 1 | Long entry signal |
| `exit_long` | 1 | Long exit signal |
| `enter_short` | 1 | Short entry signal |
| `exit_short` | 1 | Short exit signal |
| `enter_tag` | str | Tag identifying entry reason |
| `exit_tag` | str | Tag identifying exit reason |

Conflicting signals (e.g., `enter_long + exit_long` both 1) cancel each other out.

### Strategy Discovery

Filesystem-based plugin loader:
1. Scan directories for `.py` files (user_data/strategies/, --strategy-path)
2. Quick text check: `class {StrategyName}(` must appear in file
3. Dynamic import via `importlib.util.spec_from_file_location()` + `exec_module()`
4. Inspect module members for `issubclass(cls, IStrategy)`
5. Instantiate with `strategy_class(config=config)`

Also supports base64-encoded inline strategies and recursive directory search.

### 15+ Lifecycle Callbacks

```python
# Trade gates
confirm_trade_entry(pair, order_type, amount, rate, ...) -> bool
confirm_trade_exit(pair, trade, order_type, amount, rate, ...) -> bool

# Custom pricing
custom_entry_price(pair, trade, current_time, proposed_rate, ...) -> float
custom_exit_price(pair, trade, current_time, proposed_rate, ...) -> float

# Dynamic risk management
custom_stoploss(pair, trade, current_time, current_rate, current_profit, ...) -> float | None
custom_exit(pair, trade, current_time, current_rate, current_profit, ...) -> str | bool | None

# Position management
custom_stake_amount(pair, current_time, current_rate, proposed_stake, ...) -> float
adjust_trade_position(trade, current_time, current_rate, current_profit, ...) -> float | None
leverage(pair, current_time, current_rate, proposed_leverage, max_leverage, ...) -> float

# Order management
order_filled(pair, trade, order, current_time, ...) -> None
check_entry_timeout(pair, trade, order, current_time, ...) -> bool
check_exit_timeout(pair, trade, order, current_time, ...) -> bool
adjust_entry_price(trade, order, pair, current_time, proposed_rate, ...) -> float | None

# Lifecycle
bot_start(**kwargs) -> None           # once after instantiation
bot_loop_start(current_time, ...) -> None  # each iteration

# Data
informative_pairs() -> list[(pair, timeframe)]
```

### Hyperopt Parameters

Declared as class attributes, integrate with Optuna:

```python
class MyStrategy(IStrategy):
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")
    buy_adx = DecimalParameter(20.0, 40.0, decimals=1, default=30.0)
    use_ema = BooleanParameter(default=True)
    sma_type = CategoricalParameter(["SMA", "EMA", "WMA"], default="SMA")
```

---

## 2. Configuration System

### Three-Tier Precedence

```
Config Files (last wins) < Environment Variables < CLI Arguments (highest priority)
```

Environment variables use `FREQTRADE__` prefix with double-underscore nesting:
`FREQTRADE__EXCHANGE__NAME=binance`

### Schema-Driven Defaults

Custom `FreqtradeValidator` extends `Draft4Validator` to auto-inject defaults from JSON Schema. Code never needs to scatter `config.get("key", default)`.

### RunMode-Aware Validation

| Mode | Required Fields |
|------|----------------|
| LIVE / DRY_RUN | 17 fields: exchange, timeframe, max_open_trades, stake_currency, stake_amount, stoploss, minimal_roi, pairlists, entry_pricing, exit_pricing, ... |
| BACKTEST / HYPEROPT | 10 fields: + stoploss, minimal_roi, max_open_trades |
| WEBSERVER | 5 fields: exchange, dry_run, dataformat_ohlcv, dataformat_trades, api_server |
| UTILITY | 4 fields: exchange, dry_run, dataformat_ohlcv, dataformat_trades |

### Domain-Specific Consistency Checks

- Stoploss != 0, trailing offset > trailing positive
- Market orders require "other" price side
- `max_open_trades` and `stake_amount` can't both be unlimited
- StaticPairList needs pair_whitelist
- `can_short=True` can't run in spot mode
- Deprecated buy/sell terminology auto-migrated in spot mode, hard error in futures

### Loading Pipeline

```python
def load_config(self):
    config = load_from_files(self.args.get("config", []))    # 1. merge config files
    env_data = environment_vars_to_dict()                     # 2. env vars
    config = deep_merge_dicts(env_data, config)
    self._process_logging_options(config)                     # 3. CLI overrides
    self._process_runmode(config)
    self._process_common_options(config)
    self._process_trading_options(config)
    self._process_optimize_options(config)
    # ... more subsystems
    check_exchange(config)                                    # 4. validate exchange
    self._resolve_pairs_list(config)                          # 5. resolve pairs
    process_temporary_deprecated_settings(config)             # 6. migrations
    return config
```

---

## 3. Data Pipeline

### Raw Data Processing

```
Exchange (ccxt) -> timestamp flooring -> deduplication (groupby) ->
incomplete candle removal -> missing data fill (ffill close) -> DataFrame
```

Deduplication via groupby:
```python
dataframe.groupby(by="date", as_index=False, sort=True).agg({
    "open": "first", "high": "max", "low": "min", "close": "last", "volume": "max",
})
```

Missing data fill: forward-filled close price, zero volume for synthetic bars.

### DataProvider Abstraction

Strategies never know if they're running live or backtesting:

```python
def get_pair_dataframe(self, pair, timeframe=None, candle_type=""):
    if self.runmode in (RunMode.DRY_RUN, RunMode.LIVE):
        data = self.ohlcv(pair=pair, timeframe=timeframe)           # exchange cache
    else:
        data = self.historic_ohlcv(pair=pair, timeframe=timeframe)  # disk files
        if self.__slice_date:
            cutoff_date = timeframe_to_prev_date(timeframe, self.__slice_date)
            data = data.loc[data["date"] < cutoff_date]             # lookahead protection
    return data
```

Full DataProvider API:

| Method | Returns | Live | Backtest |
|--------|---------|------|----------|
| `ohlcv(pair, tf)` | DataFrame | Exchange cache | Empty |
| `get_pair_dataframe(pair, tf)` | DataFrame | Via exchange | Via disk + lookahead protection |
| `historic_ohlcv(pair, tf)` | DataFrame | From disk | From disk with startup padding |
| `get_analyzed_dataframe(pair, tf)` | (DataFrame, datetime) | Full cached DF | Last 1000 candles to eval point |
| `ticker(pair)` | dict | Exchange | N/A |
| `orderbook(pair, max)` | OrderBook | Exchange | N/A |
| `current_whitelist()` | list[str] | Pairlist provider | Pairlist provider |
| `send_msg(message)` | None | Queues RPC message | No-op |

### Multi-Timeframe via @informative Decorator

```python
@informative("1h")
def populate_indicators_1h(self, dataframe, metadata):
    dataframe["rsi"] = ta.RSI(dataframe)
    return dataframe
```

Framework automatically: fetches the data, calls the method, renames columns (`rsi` -> `rsi_1h`), merges into main DataFrame with **lookahead protection** (shifts informative data forward by one period so smaller timeframe can't see unfinished higher-timeframe candles).

---

## 4. Execution Loop

### Worker -- Candle-Aligned Polling

Not event-driven. Sleeps until next candle boundary + 1 second offset:

```python
self._throttle(
    func=self._process_running,
    throttle_secs=self._throttle_secs,
    timeframe=self._config["timeframe"],
    timeframe_offset=1,
)
```

State machine: `RUNNING -> PAUSED -> STOPPED -> RELOAD_CONFIG`

### Main Trading Loop (FreqtradeBot.process)

```python
def process(self):
    self.exchange.reload_markets()                    # 1. refresh markets
    self.update_trades_without_assigned_fees()        # 2. housekeeping
    trades = Trade.get_open_trades()                  # 3. current trades
    self.active_pair_whitelist = self._refresh_active_whitelist(trades)  # 4. pairs
    self.dataprovider.refresh(...)                    # 5. download candles
    self.strategy.bot_loop_start(current_time=now)    # 6. strategy callback
    self.strategy.analyze(self.active_pair_whitelist)  # 7. generate signals (TIMED)
    with self._exit_lock:
        self.manage_open_orders()                     # 8. cancel timeouts
        self.exit_positions(trades)                   # 9. check exits FIRST
        Trade.commit()
    if self.strategy.position_adjustment_enable:
        self.process_open_trade_positions()            # 10. DCA
    if self.state == State.RUNNING:
        self.enter_positions()                         # 11. new entries AFTER exits
    self._schedule.run_pending()                       # 12. scheduled tasks
    Trade.commit()
```

**Key design decisions:**
- Exits before entries (frees trade slots)
- `_exit_lock` protects against RPC thread race conditions (Telegram force-sell)
- Execution timing guard warns if strategy analysis takes >25% of timeframe
- PAUSED state: exits still process, entries skipped

### Entry Pipeline

```
enter_positions() -> create_trade() -> execute_entry()
```

1. Get analyzed DataFrame, read signal from last candle
2. Check pair locks, depth of market
3. Calculate stake amount from wallet
4. Call `strategy.confirm_trade_entry()` (user can veto)
5. Place order via exchange
6. Create Order + Trade objects
7. Send RPC notification

### Exit Pipeline

```
exit_positions() -> handle_trade() -> _check_and_execute_exit() -> execute_trade_exit()
```

Exit conditions evaluated in priority order:
1. Exit signal (from `populate_exit_trend` or `custom_exit()`)
2. Stop loss (hard or trailing)
3. ROI (time-based minimum profit)
4. Trailing stop loss

Returns `list[ExitCheckTuple]` -- multiple exits can fire (supports partial exits).

---

## 5. Backtesting Engine

### Row-by-Row Iteration (NOT Vectorized)

Converts DataFrames to lists-of-tuples for speed:

```python
HEADERS = ["date", "open", "high", "low", "close",
           "enter_long", "exit_long", "enter_short", "exit_short",
           "enter_tag", "exit_tag"]
DATE_IDX = 0; OPEN_IDX = 1; HIGH_IDX = 2; LOW_IDX = 3; CLOSE_IDX = 4
```

### Signal Shifting (Lookahead Prevention)

```python
for col in HEADERS[5:]:
    df_analyzed[col] = df_analyzed.loc[:, col].shift(1)
df_analyzed = df_analyzed.drop(df_analyzed.head(1).index)
```

### Per-Candle Processing

```python
def backtest_loop(self, row, pair, current_time, trade_dir, can_enter):
    # 1. Manage open orders of active trades
    for t in LocalTrade.bt_trades_open_pp[pair]:
        self.manage_open_orders(t, current_time, row)
    # 2. Process new entries (if slot available)
    if can_enter and trade_dir is not None:
        self._enter_trade(pair, row, trade_dir)
    for trade in LocalTrade.bt_trades_open_pp[pair]:
        # 3. Fill entry orders
        self._try_close_open_order(order, trade, current_time, row)
        # 4. Create exit orders (evaluate exit conditions)
        self._check_trade_exit(trade, row, current_time)
        # 5. Fill exit orders
        self._process_exit_order(order, trade, current_time, row, pair)
```

### Fill Price Simulation

Realistic fills within OHLC bounds:
- **Stoploss exits**: `trade.stop_loss`, or `row[OPEN]` if gap beyond stoploss
- **ROI exits**: `trade.calc_close_rate_for_roi(roi)`, clamped to [LOW, HIGH]
- **Signal exits**: `row[OPEN]` (next candle open)

Supports "detail timeframe" (e.g., 1m within 5m candles) for precise exit timing.

### Performance Optimizations

- `LocalTrade` (plain Python) instead of `Trade` (SQLAlchemy) -- no ORM overhead
- `bt_trades_open_pp` -- dict indexed by pair for O(1) lookup
- Lists-of-tuples instead of DataFrames for iteration
- Simple bounds check for order fills: `row[LOW] <= rate <= row[HIGH]`

---

## 6. Trade Model

### Two-Class Design

- **`LocalTrade`** -- pure Python, backtesting (no DB overhead)
- **`Trade`** -- extends LocalTrade + SQLAlchemy ORM, live trading

### Key Fields

```python
# Identity
id, pair, base_currency, stake_currency, exchange, strategy

# Position
is_open, is_short, leverage, amount, stake_amount, open_rate, close_rate

# Stop loss state machine
stop_loss, stop_loss_pct, initial_stop_loss, initial_stop_loss_pct
is_stop_loss_trailing, max_rate, min_rate

# Profit
close_profit, close_profit_abs, realized_profit, max_stake_amount

# Futures
liquidation_price, funding_fees, funding_fee_running

# Orders (one-to-many)
orders: list[Order]
```

### Order-Centric Accounting

All trade state derived from order history via `recalc_trade_from_orders()`:
- Weighted average `open_rate` across multiple entries (DCA)
- Cumulative `amount`, `stake_amount`, `max_stake_amount`
- `realized_profit` from partial exits

### Profit Calculation (Supports All Modes)

```python
if self.is_short:
    profit_abs = open_trade_value - close_trade_value
    profit_ratio = (1 - (close_trade_value / open_trade_value)) * self.leverage
else:
    profit_abs = close_trade_value - open_trade_value
    profit_ratio = ((close_trade_value / open_trade_value) - 1) * self.leverage
```

SPOT: `amount * rate - fees`
MARGIN: adds interest
FUTURES: adds/subtracts `funding_fees`

---

## 7. Key Enums

```python
class SignalType(StrEnum):
    ENTER_LONG, EXIT_LONG, ENTER_SHORT, EXIT_SHORT

class SignalDirection(StrEnum):
    LONG, SHORT

class TradingMode(StrEnum):
    SPOT, MARGIN, FUTURES

class RunMode(StrEnum):
    LIVE, DRY_RUN, BACKTEST, HYPEROPT, UTIL_EXCHANGE, UTIL_NO_EXCHANGE, PLOT, WEBSERVER, OTHER

class ExitType(Enum):
    ROI, STOP_LOSS, STOPLOSS_ON_EXCHANGE, TRAILING_STOP_LOSS, LIQUIDATION,
    EXIT_SIGNAL, FORCE_EXIT, EMERGENCY_EXIT, CUSTOM_EXIT, PARTIAL_EXIT, NONE

class State(Enum):
    RUNNING, PAUSED, STOPPED, RELOAD_CONFIG
```

---

## 8. Comparison with Our System

| Area | Our System (Phase 0) | Freqtrade | Recommendation |
|------|---------------------|-----------|----------------|
| Signals | Continuous [-1,+1] | Binary 0/1 + tags | Keep ours -- more expressive for position sizing |
| Backtesting | Vectorized | Row-by-row | Keep vectorized for speed; add row-by-row mode for DCA/partial exits |
| Strategy loading | Registry/factory | Filesystem scan + importlib | Adopt filesystem discovery for user strategies |
| Config validation | None | JSON Schema + domain checks | Add schema validation |
| Data abstraction | Direct file I/O | DataProvider (live/backtest agnostic) | Adopt DataProvider pattern for Phase 1 |
| Trade model | Frozen dataclass | Mutable + order-centric accounting | Evolve toward order-centric when adding live trading |
| Lookahead protection | Signal shift | Signal shift + DataFrame slicing | Add DataFrame slicing as defense-in-depth |
| Callbacks | None | 15+ lifecycle hooks | Add key callbacks: confirm_trade_entry, custom_stoploss, custom_exit |
| Hyperopt | None | Optuna + parameter decorators | Study for Phase 1 optimization |
| Multi-timeframe | None | @informative decorator + auto-merge | Adopt for multi-timeframe strategies |
| Persistence | None | SQLAlchemy + LocalTrade dual model | Adopt dual model when adding live trading |
| RPC | None | Telegram, REST API, webhooks | Add REST API for monitoring |

### Priority Adoptions for Phase 1

1. **DataProvider pattern** -- single interface for live/backtest, the key enabler for live trading
2. **Config validation** -- JSON Schema with mode-aware required fields
3. **Filesystem strategy discovery** -- let users drop .py files into a strategies/ directory
4. **Lifecycle callbacks** -- `custom_stoploss`, `custom_exit`, `confirm_trade_entry` at minimum
5. **DataFrame slicing** -- defense-in-depth lookahead protection alongside signal shifting
6. **Multi-timeframe @informative decorator** -- declarative multi-timeframe support
