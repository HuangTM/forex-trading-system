# NautilusTrader Architecture Analysis

Source: [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) (21,534 stars)
Analyzed: 2026-03-30

---

## 1. Overview

Rust-native, event-driven trading engine with Python control plane. Dual-language: Rust core (22+ crates) for performance, Cython/Python for orchestration and user-facing APIs. Key principle: **research-to-live parity** -- same strategy code runs unchanged in backtest and live.

---

## 2. The Kernel -- Composition Root

`NautilusKernel` is the central wiring point, shared across all environments (BACKTEST, SANDBOX, LIVE):

```
NautilusKernel
  +-- Clock (TestClock for backtest, LiveClock for live)
  +-- MessageBus (central pub/sub + point-to-point)
  +-- Cache (in-memory, optionally Redis-backed)
  +-- Portfolio
  +-- DataEngine
  +-- ExecutionEngine
  +-- RiskEngine
  +-- OrderEmulator
  +-- Trader (orchestrates strategies and actors)
```

Environment polymorphism via config types -- the kernel inspects whether config objects are `DataEngineConfig` (backtest) or `LiveDataEngineConfig` (live) to instantiate the correct engine variant. Strategies never reference the live/backtest distinction.

---

## 3. Component Hierarchy

```
Component (base -- Clock, MessageBus, Logger, FSM lifecycle)
  +-- Actor (data subscriptions, indicators, event handlers)
      +-- Strategy (order management, trading commands)
  +-- DataEngine
  +-- ExecutionEngine
  +-- RiskEngine
  +-- OrderEmulator
```

**Component** lifecycle FSM: `PRE_INITIALIZED -> READY -> STARTING -> RUNNING -> STOPPING -> STOPPED -> DISPOSING -> DISPOSED`

**Actor** extends Component with:
- Data subscriptions: `subscribe_bars`, `subscribe_quote_ticks`, `subscribe_trade_ticks`, `subscribe_order_book_deltas`
- Event handlers: `on_bar`, `on_quote_tick`, `on_trade_tick`, `on_order_book`, `on_data`, `on_event`
- Indicator registration and automatic updating
- State save/load for persistence

**Strategy** extends Actor with:
- `OrderFactory` for generating orders with proper IDs
- `OrderManager` for contingent orders, GTD expiry
- Trading commands: `submit_order`, `submit_order_list`, `modify_order`, `cancel_order`, `cancel_all_orders`, `close_position`, `close_all_positions`
- OMS type: `HEDGING` / `NETTING` / `UNSPECIFIED`
- Per-event hooks: `on_order_filled`, `on_order_rejected`, `on_position_opened`, `on_position_closed`

---

## 4. MessageBus -- Central Nervous System

Two communication patterns:

**Point-to-point (endpoint registration):**
```python
self._msgbus.register(endpoint="DataEngine.execute", handler=self.execute)
self._msgbus.register(endpoint="RiskEngine.execute", handler=self.execute)
```

**Pub/Sub (topic-based with wildcard matching):**
```python
self._msgbus.subscribe(topic="events.order.*", handler=self._handle_event, priority=10)
self._msgbus.subscribe(topic=f"events.position.{self.id}", handler=self.handle_event)
self._msgbus.publish_c(topic=f"events.order.{order.strategy_id}", msg=event)
```

Priority-based handlers (RiskEngine subscribes with priority=10 to see events before strategies). Optional Redis-backed persistence.

---

## 5. Command and Event Flow

**Command flow (Strategy -> Venue):**
```
Strategy.submit_order()
  -> OrderManager.send_risk_command()
    -> MessageBus -> "RiskEngine.execute"
      -> RiskEngine pre-trade checks (throttling, max notional, trading state)
        -> MessageBus -> "ExecEngine.execute"
          -> ExecutionEngine routes to correct ExecutionClient
            -> Venue (SimulatedExchange or real exchange)
```

**Event flow (Venue -> Strategy):**
```
Venue generates OrderFilled event
  -> ExecutionClient.process()
    -> MessageBus -> "ExecEngine.process"
      -> ExecutionEngine: update cache, generate position events
        -> MessageBus.publish("events.order.{strategy_id}", event)
          -> Strategy.handle_event() -> on_order_filled(), on_position_opened()
```

---

## 6. Data Engine

Orchestrates `DataClient` instances (fan-in fan-out). Routes subscriptions by venue. Handles bar aggregation in-engine.

**Data types:**
- `QuoteTick`, `TradeTick`, `Bar`, `OrderBookDelta`, `OrderBookDeltas`, `OrderBookDepth10`
- `InstrumentStatus`, `InstrumentClose`, `CustomData`
- `FundingRateUpdate`, `MarkPriceUpdate`, `IndexPriceUpdate`, `OptionGreeks`

**Bar aggregation types:** TICK, TICK_IMBALANCE, TICK_RUNS, VOLUME, VOLUME_IMBALANCE, VOLUME_RUNS, VALUE, VALUE_IMBALANCE, VALUE_RUNS, MILLISECOND, SECOND, MINUTE, HOUR, DAY, WEEK, MONTH, YEAR, RENKO.

---

## 7. Risk Engine

Pre-trade risk checks:
- **Order submit throttling**: configurable rate limits (e.g., 100 orders/second)
- **Order modify throttling**: separate rate limits
- **Max notional per order**: per-instrument limits
- **Trading state**: ACTIVE, REDUCING (only reduce-position orders), HALTED (only cancels)

Denied orders generate `OrderDenied` events that flow back to the strategy.

---

## 8. Backtesting Engine

Uses the same `NautilusKernel` with:
- `TestClock` instead of `LiveClock`
- `SimulatedExchange` instead of real venues
- `BacktestDataClient` / `BacktestExecClient` instead of live clients

**Main loop:**
```python
while True:
    data = self._data_iterator.next()
    if data is None:
        done = self._process_next_timer()
        if done: break
        continue
    if data.ts_init > end_ns: break

    # Advance clocks to data timestamp
    self._advance_time(data.ts_init)

    # Route data to SimulatedExchange
    exchange.process_quote_tick(data)  # or process_bar, etc.

    # Process through DataEngine (same as live)
    self._data_engine.process(data)

    # Settle venues
    self._process_and_settle_venues(data.ts_init)
```

**Deterministic time model:** `_advance_time` fires all timer events in strict chronological order. `SimulatedExchange` provides full venue simulation: order matching, order book management, account tracking, configurable fill/fee/latency models.

**Streaming mode** for datasets larger than memory:
```python
for batch in data_batches:
    engine.add_data(batch)
    engine.run(streaming=True)
    engine.clear_data()
engine.end()
```

---

## 9. Domain Model

**Identifiers** (Rust-backed):
- `TraderId`, `StrategyId` (`{ClassName}-{tag}`), `InstrumentId` (`{Symbol}.{Venue}`)
- `ClientOrderId`, `VenueOrderId`, `PositionId`, `AccountId`, `TradeId`

**Value objects** -- fixed-point arithmetic (128-bit or 64-bit integers):
- `Price`, `Quantity`, `Money`, `Currency`
- Avoids floating-point errors while maintaining performance

**Instruments:** `CurrencyPair`, `Equity`, `FuturesContract`, `OptionContract`, `CryptoPerpetual`, `CryptoFuture`, `CFD`, `Commodity`, `BinaryOption`, `SyntheticInstrument`, and more.

**Orders:** `MarketOrder`, `LimitOrder`, `StopMarketOrder`, `StopLimitOrder`, `MarketToLimitOrder`, `MarketIfTouchedOrder`, `LimitIfTouchedOrder`, `TrailingStopMarketOrder`, `TrailingStopLimitOrder`, `OrderList` (contingent groups).

**Events (event-sourced order state machine):**
- Order events: `OrderInitialized`, `OrderSubmitted`, `OrderAccepted`, `OrderRejected`, `OrderDenied`, `OrderCanceled`, `OrderExpired`, `OrderTriggered`, `OrderFilled`, `OrderUpdated`, etc.
- Position events: `PositionOpened`, `PositionChanged`, `PositionClosed`
- Every order carries its full event history; current state = replaying event sequence.

---

## 10. Configuration System

Based on `msgspec.Struct` (frozen, kw_only) -- immutable, serializable, hashable:

```python
class StrategyConfig(NautilusConfig, frozen=True):
    strategy_id: StrategyId | None = None
    order_id_tag: str | None = None
    oms_type: str | None = None
    manage_contingent_orders: bool = False
    manage_gtd_expiry: bool = False
```

**Importable configs** for dynamic strategy loading:
```python
class ImportableStrategyConfig(NautilusConfig, frozen=True):
    strategy_path: str    # "module.path:ClassName"
    config_path: str      # "module.path:ConfigClass"
    config: dict[str, Any]
```

**Config hierarchy:** `NautilusKernelConfig` -> `BacktestEngineConfig` / `TradingNodeConfig`, plus per-engine configs (`DataEngineConfig`, `ExecEngineConfig`, `RiskEngineConfig`).

---

## 11. Backtest vs Live -- Strategy-Agnostic Pattern

| Concern | Backtest | Live |
|---------|----------|------|
| Clock | `TestClock` (manual advance) | `LiveClock` (real time) |
| DataClient | `BacktestMarketDataClient` | `LiveDataClient` (per adapter) |
| ExecutionClient | `BacktestExecClient` | `LiveExecClient` (per adapter) |
| DataEngine | `DataEngine` | `LiveDataEngine` (async) |
| ExecutionEngine | `ExecutionEngine` | `LiveExecutionEngine` (async + reconciliation) |
| Venue | `SimulatedExchange` | Real exchange via adapter |

Strategy interacts only with: `self.cache`, `self.portfolio`, `self.clock`, `self.order_factory`, `self.submit_order()` / `self.cancel_order()`.

---

## 12. Example: EMA Cross Strategy

```python
class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: PositiveInt = 10
    slow_ema_period: PositiveInt = 20

class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self):
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.buy()
        elif self.fast_ema.value < self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.sell()

    def buy(self):
        order = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)
```

This exact code runs in both backtest and live with zero changes.

---

## 13. Key Design Patterns

| Pattern | Where | Details |
|---------|-------|---------|
| **Composition Root / Kernel** | `NautilusKernel` | Assembles all components; environment injected through config |
| **Event Sourcing** | Order model | Orders maintain full event history; state = replayed events |
| **Message Bus / Mediator** | `MessageBus` | All inter-component communication; no direct references |
| **Strategy Pattern (GoF)** | `Strategy` class | Template with hook methods (`on_bar`, `on_order_filled`, etc.) |
| **Facade** | `CacheFacade`, `PortfolioFacade` | Read-only views preventing state corruption |
| **Factory** | `OrderFactory`, `StrategyFactory` | Configurable creation with proper ID management |
| **Client-Engine** | Data/Exec engines | Registry of clients, routing by venue |
| **Fixed-Point Arithmetic** | `Price`, `Quantity`, `Money` | Integer-backed, no floating-point errors |
| **Deterministic Time** | `TestClock` | Exact reproducibility; timers fire in strict chronological order |
| **Dual-Language** | Rust + Cython + Python | Rust for perf-critical paths, Python for config/orchestration |

---

## 14. Comparison with Our System

| Area | Our System (Phase 0) | NautilusTrader | Recommendation |
|------|---------------------|----------------|----------------|
| Architecture | Procedural pipeline | Event-driven kernel + message bus | Adopt message bus for Phase 2 (live trading) |
| Order model | Frozen Trade dataclass | Event-sourced order state machine | Evolve toward event sourcing for live |
| Price types | Python floats | Fixed-point integers (128-bit) | Adopt for live trading accuracy |
| Strategy API | ABC with generate_signals() | Actor with on_bar/on_tick hooks | Keep simple for backtest; add hooks for live |
| Risk management | None | Pre-trade risk engine (throttling, max notional, trading state) | Add risk engine before going live |
| Backtest/live parity | N/A (backtest only) | Same kernel, swapped components | Design DataProvider pattern with this in mind |
| Config | YAML dict | Frozen msgspec structs | Adopt frozen config objects |
| Data pipeline | File-based, single timeframe | Multi-source, multi-timeframe, bar aggregation | Adopt client-engine pattern |

### Priority Adoptions

1. **Message bus pattern** -- decouple components before adding live trading
2. **Fixed-point money types** -- eliminate floating-point errors in P&L
3. **Event-sourced orders** -- audit trail and state reconstruction
4. **Risk engine as mandatory gate** -- every order through pre-trade checks
5. **Frozen config structs** -- immutable, hashable, reproducible backtests
6. **Facade read-only interfaces** -- strategies can't corrupt system state
