# Forex Trading System -- Architectural Design

> A phased architecture that respects one finding above all others: **alpha first, infrastructure second.** Every module earns its existence by serving edge discovery or protecting real capital. Nothing else gets built.

---

## 1. Design Principles

| Principle | Implication |
|-----------|-------------|
| **Alpha first** | Research velocity > code elegance. Don't build infrastructure for strategies that don't work. |
| **Measure reality, don't model it** | Costs, spreads, slippage measured empirically from Saxo, not assumed from config. |
| **Flat is default** | The system needs a reason to be in market. No position is the safest position. |
| **Continuous, not discrete** | Signal strength maps to position size continuously. Avoid hard thresholds that create overfitting. |
| **Vectorized for research, event-driven for live** | Backtest stays vectorized for speed. Live trading gets a thin event-driven execution layer. |
| **Same signal, different execution** | Strategy code is identical in backtest and live. Only the execution backend changes. |
| **Safety through simplicity** | Binary kill switch over graduated degradation. Flat file logs over event sourcing. |

---

## 2. System Phases

```
Phase 0 (current)     Phase 1               Phase 2               Phase 3
Backtest-Only    -->  Research + Validate  -->  Paper + Micro-Live -->  Live Trading
~2,700 LOC            +1,500 LOC               +2,000 LOC             +1,500 LOC

What exists:          What to add:              What to add:           What to add:
- Vectorized engine   - Measured cost model     - Saxo SIM connector   - Full Saxo live
- 3 strategies        - Carry strategy          - Paper reconciliation - Execution FSM
- Walk-forward        - Null hypothesis gate    - Micro-trade engine   - Token management
- Cost model (static) - Backtest arson test     - Autonomy: Manual     - Kill switch
- Data validation     - Experiment registry     - Prediction log       - Skinny live loop
                      - Continuous sizing       - Autonomy: Suggest    - Reconciliation
                      - Capital ratchet (spec)  - Structured trade log - Autonomy: Auto
```

**Gate between phases:** Each phase requires evidence that the previous phase's hypothesis was validated.

- **Phase 1 -> 2 gate:** At least one strategy passes the null hypothesis gate on a **held-out out-of-sample period** (designated before research begins, never used for development). The gate uses DSR-adjusted significance, corrected for total trials in the experiment registry. The arson test is run as a diagnostic (not a gate) to characterize signal sensitivity.
- **Phase 2 -> 3 gate:** Paper trading "reality tax" (backtest-vs-paper divergence) within acceptable bounds, measured over at least 50 paper trades.

---

## 3. Architecture Overview

```
                        +------------------+
                        |   Configuration  |
                        |  (YAML + Tiers)  |
                        +--------+---------+
                                 |
              +------------------+------------------+
              |                  |                  |
    +---------v-------+  +------v-------+  +-------v--------+
    |   Data Layer    |  | Strategy     |  | Cost Layer     |
    |                 |  | Layer        |  |                |
    | - Sources       |  | - Interface  |  | - Static model |
    | - Validation    |  | - Registry   |  | - Measured     |
    | - Storage       |  | - Strategies |  |   (from Saxo)  |
    | - Transforms    |  | - Carry      |  | - Time-varying |
    +---------+-------+  +------+-------+  +-------+--------+
              |                  |                  |
              +------------------+------------------+
                                 |
                    +------------v-----------+
                    |   Execution Backend    |
                    |   (swappable)          |
                    |                        |
                    |  +------------------+  |
                    |  | Backtest Engine  |  |  <-- Phase 0-1: vectorized
                    |  +------------------+  |
                    |  +------------------+  |
                    |  | Paper Engine     |  |  <-- Phase 2: Saxo SIM
                    |  +------------------+  |
                    |  +------------------+  |
                    |  | Live Engine      |  |  <-- Phase 3: Saxo Live
                    |  +------------------+  |
                    +------------+-----------+
                                 |
              +------------------+------------------+
              |                  |                  |
    +---------v-------+  +------v-------+  +-------v--------+
    |   Sizing Layer  |  | Risk Layer   |  | Analysis Layer |
    |                 |  |              |  |                |
    | - Continuous    |  | - Kill switch|  | - Metrics      |
    |   sizing        |  | - Capital    |  | - Experiment   |
    | - Capital       |  |   ratchet    |  |   registry     |
    |   ratchet       |  | - Autonomy   |  | - Prediction   |
    |                 |  |   level      |  |   log          |
    +-----------------+  +--------------+  | - Reports      |
                                           | - Null hyp.    |
                                           | - Arson test   |
                                           +----------------+
```

---

## 4. Module Design

### 4.1 Core Layer (`core/`)

**Unchanged from Phase 0, with additions:**

```python
# core/interfaces.py -- EXTENDED

class Strategy(ABC):
    """Contract for all trading strategies."""

    def __init__(self, params: dict[str, Any]):
        self.params = params

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Returns Series of floats in [-1.0, +1.0]."""
        ...

    def generate_predictions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Optional richer output. Default wraps generate_signals().

        Returns DataFrame with required 'signal' column + optional:
        - confidence: float [0, 1] -- signal confidence
        - model_id: str -- which model/version produced this
        - feature_hash: str -- hash of input features
        """
        signals = self.generate_signals(data)
        return pd.DataFrame({'signal': signals}, index=data.index)

    @abstractmethod
    def required_indicators(self) -> list[str]: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    def min_bars_required(self) -> int:
        """Minimum bars needed before strategy can produce valid signals.
        Override in subclass. Default: infer from indicator names.
        """
        return 0


class CostModel(ABC):
    """Extended to support time-varying costs.

    MIGRATION NOTE: timestamp parameter added with default None so that
    existing RealisticCostModel remains valid (it accepts-but-ignores
    timestamp). Engine call sites MUST be updated to pass the current
    bar's timestamp, otherwise MeasuredCostModel silently falls back
    to static costs. This is a 4-file atomic change:
    1. core/interfaces.py (this ABC)
    2. costs/model.py (RealisticCostModel: add **kwargs or timestamp=None)
    3. backtest/engine.py (pass ts to cost_model.entry_cost/exit_cost)
    4. tests/ (update all cost model call sites)
    """

    @abstractmethod
    def entry_cost(self, pair: str, size: float,
                   timestamp: pd.Timestamp | None = None) -> float: ...

    @abstractmethod
    def exit_cost(self, pair: str, size: float,
                  timestamp: pd.Timestamp | None = None) -> float: ...

    @abstractmethod
    def holding_cost(self, pair: str, direction: Direction,
                     days: float) -> float: ...


class ExecutionBackend(ABC):
    """Contract for execution -- backtest, paper, or live."""

    @abstractmethod
    def execute_signal(self, pair: str, signal: float, size: float,
                       context: dict[str, Any]) -> ExecutionResult: ...

    @abstractmethod
    def get_positions(self) -> dict[str, Position]: ...

    @abstractmethod
    def flatten_all(self) -> list[ExecutionResult]: ...


class PositionSizer(ABC):
    """Continuous sizing: signal strength -> position size.

    MIGRATION NOTE: Two new params (confidence, ratchet_level) added with
    defaults so existing FixedFractionalSizer remains valid. The ABC
    signature must match the existing one + defaulted extensions:
    - confidence defaults to 1.0 (full confidence, no ML yet)
    - ratchet_level defaults to 1.0 (no ratchet, full sizing)
    Existing callers that pass 5 positional args continue to work.
    New callers (ContinuousSizer) use all 7.
    """

    @abstractmethod
    def calculate_size(
        self,
        signal_strength: float,  # [-1, 1] from strategy
        account_equity: float,
        current_price: float,
        atr: float,
        pair: str,
        confidence: float = 1.0,       # [0, 1], 1.0 if not available
        ratchet_level: float = 1.0,    # [0, 1] from capital ratchet
    ) -> float: ...
```

**New domain types:**

```python
# core/types.py -- ADDITIONS

@dataclass(frozen=True)
class Position:
    """A currently open position."""
    pair: str
    direction: Direction
    size: float
    entry_price: float
    entry_time: pd.Timestamp
    unrealized_pnl: float

@dataclass(frozen=True)
class ExecutionResult:
    """Result of executing a trade."""
    pair: str
    direction: Direction
    size: float
    requested_price: float
    fill_price: float
    fill_time: pd.Timestamp
    slippage_pips: float
    spread_at_fill: float
    success: bool
    error: str | None = None

@dataclass(frozen=True)
class ExperimentRecord:
    """Metadata for a single backtest experiment."""
    experiment_id: str          # UUID
    git_hash: str
    timestamp: pd.Timestamp
    strategy_name: str
    pair: str
    config_hash: str            # hash of full config snapshot
    data_hash: str              # hash of input data
    metrics: dict[str, float]   # sharpe, drawdown, etc.
    parameters: dict[str, Any]
    tags: list[str]             # e.g., ["carry", "4h", "walk-forward"]
```

### 4.2 Data Layer (`data/`)

**Phase 0:** CSV/Parquet sources (unchanged)
**Phase 1:** Add measured cost data collection
**Phase 2:** Add Saxo streaming data source

```python
# data/sources/saxo_source.py (Phase 2)

class SaxoDataSource(DataSource):
    """Fetch historical and streaming data from Saxo Bank API."""

    def __init__(self, auth: SaxoAuth):
        self.auth = auth

    def fetch(self, pair: str, start: str, end: str,
              timeframe: str = "daily") -> pd.DataFrame:
        """Fetch historical OHLCV from Saxo chart API."""
        ...

    def stream_prices(self, pairs: list[str],
                      callback: Callable[[str, float, float, pd.Timestamp], None]):
        """WebSocket streaming of bid/ask prices.
        Callback receives: (pair, bid, ask, timestamp)
        """
        ...
```

```python
# data/spread_recorder.py (Phase 1)

class SpreadRecorder:
    """Record actual Saxo spreads for cost empiricism.

    Stores: (timestamp, pair, bid, ask, spread_pips, mid_price)
    to Parquet files, partitioned by date.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def record(self, pair: str, bid: float, ask: float,
               timestamp: pd.Timestamp): ...

    def load_spread_distribution(
        self, pair: str, start: str, end: str
    ) -> pd.DataFrame:
        """Returns spread statistics grouped by hour_of_day, day_of_week."""
        ...
```

### 4.3 Cost Layer (`costs/`)

**Phase 0:** `RealisticCostModel` with fixed per-pair constants (unchanged)
**Phase 1:** Add `MeasuredCostModel` that reads from spread recordings

```python
# costs/measured.py (Phase 1)

class MeasuredCostModel(CostModel):
    """Cost model derived from actual recorded Saxo spreads.

    Falls back to static model for time periods without data.
    """

    def __init__(self, spread_data: pd.DataFrame,
                 fallback: CostModel):
        self.spread_surface = self._build_surface(spread_data)
        self.fallback = fallback

    def entry_cost(self, pair: str, size: float,
                   timestamp: pd.Timestamp | None = None) -> float:
        """Lookup actual spread for this (pair, hour, day) bucket."""
        if timestamp and self._has_data(pair, timestamp):
            spread = self._lookup_spread(pair, timestamp)
            return spread / 2.0  # half-spread to enter
        return self.fallback.entry_cost(pair, size)

    def _build_surface(self, data: pd.DataFrame) -> dict:
        """Build spread lookup: (pair, hour, day_of_week) -> median spread."""
        ...
```

### 4.4 Strategy Layer (`strategies/`)

**Phase 0:** MA crossover, Bollinger-RSI, Momentum (unchanged)
**Phase 1:** Add carry strategy

```python
# strategies/carry.py (Phase 1)

class CarryStrategy(Strategy):
    """FX Carry trade -- long high-yield, short low-yield.

    The one strategy with decades of academic evidence.
    Signal is proportional to interest rate differential.

    DATA SOURCE NOTE: Carry signals require historical interest rate
    differentials, not just static swap rates from PairInfo config.
    Static swap rates produce a degenerate constant signal (always +1
    or always -1 per pair) which would pass the null hypothesis gate
    as a false positive.

    Phase 1 approach: Source historical central bank rate data from
    FRED (Federal Reserve Economic Data, free API). Key series:
    - EURUSD: ECB deposit rate vs Fed Funds rate
    - USDJPY: Fed Funds vs BOJ policy rate
    - GBPUSD: BOE bank rate vs Fed Funds rate

    The rate differential changes over time (monthly/quarterly),
    creating a real dynamic signal. As a cross-check, compare the
    computed carry direction against PairInfo swap sign -- they must
    agree for the cost model to be consistent.

    Phase 2 alternative: Use Saxo's real-time swap rates from the
    conditions endpoint, which change daily based on interbank rates.

    LIMITATION: In Phase 1 backtest, carry signals will be piecewise
    constant (changing when central banks move rates, typically 4-8
    times per year per pair). The null hypothesis gate must account
    for this low signal frequency -- a strategy that changes direction
    6 times in 5 years needs a different null distribution than one
    that trades 40 times per year.
    """

    def __init__(self, params: dict[str, Any],
                 rate_data: pd.DataFrame | None = None):
        """
        Args:
            params: Strategy parameters
            rate_data: DataFrame with columns [date, pair, rate_differential]
                       sourced from FRED or Saxo. If None, falls back to
                       static PairInfo swap rates (with a logged warning
                       that signals will be constant).
        """
        super().__init__(params)
        self.rate_data = rate_data

    @property
    def name(self) -> str:
        return "carry"

    def required_indicators(self) -> list[str]:
        return []  # Carry uses rate differentials, not technical indicators

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Signal based on interest rate differential.

        If rate_data provided: signal tracks historical differential.
        If not: falls back to static swap direction (constant signal,
        logged warning that this is for sanity checking only).
        """
        ...

    def generate_predictions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Adds confidence based on rate differential magnitude."""
        signals = self.generate_signals(data)
        confidence = ...  # Normalized absolute differential
        return pd.DataFrame({
            'signal': signals,
            'confidence': confidence,
            'model_id': 'carry_v1',
        }, index=data.index)
```

### 4.5 Sizing Layer (`sizing/`) -- NEW

**Replaces the inline `_calculate_size` in `backtest/engine.py`.**

```python
# sizing/continuous.py

class ContinuousSizer(PositionSizer):
    """Signal strength maps continuously to position size.

    size = base_size * |signal| * confidence * ratchet_level

    This gives flat-as-default naturally: signal=0 -> size=0.
    Weak signals get tiny positions. Strong signals get full positions.
    No hard threshold to overfit.
    """

    def __init__(self, risk_per_trade: float = 0.02,
                 stop_loss_atr_multiple: float = 2.0,
                 max_position_pct: float = 0.10):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_atr_multiple = stop_loss_atr_multiple
        self.max_position_pct = max_position_pct

    def calculate_size(
        self,
        signal_strength: float,
        account_equity: float,
        current_price: float,
        atr: float,
        pair: str,
        confidence: float = 1.0,
        ratchet_level: float = 1.0,
    ) -> float:
        if abs(signal_strength) < 1e-6 or atr <= 0:
            return 0.0

        # Base size from ATR-based risk
        stop_distance = atr * self.stop_loss_atr_multiple
        base_size = account_equity * self.risk_per_trade / stop_distance

        # Scale by signal strength, confidence, and capital ratchet
        scaled_size = base_size * abs(signal_strength) * confidence * ratchet_level

        # Cap at max position
        max_size = account_equity * self.max_position_pct / current_price
        return min(scaled_size, max_size)
```

```python
# sizing/ratchet.py

class CapitalRatchet:
    """Trust-building position sizing protocol.

    Starts at minimum allocation. Ratchets up on sustained performance.
    Ratchets down FAST on any anomaly. Asymmetric by design.

    Returns ratchet_level in [0, 1] that multiplies position size.

    PERSISTENCE: Ratchet state (level + history) is persisted to
    data/ratchet_state.json after every update() call. On startup,
    the ratchet loads its last known state. This prevents months of
    earned trust from being lost on process restart. If the state
    file is missing or corrupt, the ratchet starts at initial_level
    (safe default).
    """

    def __init__(self, initial_level: float = 0.05,  # 5% of full size
                 max_level: float = 1.0,
                 state_path: str = "data/ratchet_state.json"):
        self.max_level = max_level
        self.state_path = state_path
        self.history: list[dict] = []
        # Load persisted state or start fresh
        self.level = self._load_state() or initial_level

    def update(self, period_metrics: PerformanceMetrics) -> float:
        """Update ratchet level based on recent performance.

        Promotion: requires N consecutive periods with Sharpe > threshold.
        Demotion: instant on any single-period anomaly.
        Persists state after every update.
        """
        ...
        self._save_state()
        return self.level

    def demote(self, reason: str):
        """Instant demotion to minimum level."""
        self.level = 0.05
        self.history.append({'action': 'demote', 'reason': reason})
        self._save_state()

    def _save_state(self): ...
    def _load_state(self) -> float | None: ...
```

### 4.6 Execution Layer -- Backtest (`backtest/`)

**Phase 0 engine stays vectorized (unchanged).** The only change: it now accepts a `PositionSizer` instead of inline sizing.

```python
# backtest/engine.py -- signature change

def run_backtest(
    data: pd.DataFrame,
    signals: pd.Series,            # or predictions: pd.DataFrame
    pair: str,
    strategy_name: str,
    cost_model: CostModel,         # accepts both Static and Measured
    sizer: PositionSizer,          # NEW: injected instead of inline
    initial_capital: float = 100_000.0,
    entry_delay_bars: int = 1,     # sacred no-lookahead invariant
) -> BacktestResult:
    ...
```

### 4.7 Execution Layer -- Live (`execution/`) -- Phase 3

```
execution/
  broker.py          # SaxoAuth, SaxoBroker (implements ExecutionBackend)
  fsm.py             # Order lifecycle state machine
  token_manager.py   # Token chain with fuel gauge
  reconciler.py      # Position reconciliation against Saxo
  kill_switch.py     # Binary circuit breaker
  live_loop.py       # Skinny live loop (price -> lookup -> execute)
```

```python
# execution/fsm.py

class OrderState(Enum):
    """Explicit order lifecycle states."""
    IDLE = "idle"
    SIGNAL_RECEIVED = "signal_received"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

@dataclass
class OrderFSM:
    """State machine for a single order's lifecycle.

    Each state has:
    - allowed transitions
    - timeout (max time in state before escalation)
    - action on timeout (retry, cancel, alert)
    """
    state: OrderState = OrderState.IDLE
    entered_at: pd.Timestamp | None = None
    timeouts: dict[OrderState, int] = ...  # seconds

    def transition(self, new_state: OrderState, timestamp: pd.Timestamp):
        """Attempt state transition. Raises on invalid transition."""
        ...

    def check_stuck(self, now: pd.Timestamp) -> bool:
        """Returns True if current state has exceeded its timeout."""
        ...
```

```python
# execution/live_loop.py

class SkinnyLiveLoop:
    """The real-time execution path. As thin as possible.

    Heavy computation (indicators, signals, sizing) runs on a slower
    cadence and produces a DecisionEnvelope. The live loop only does:
    1. Receive price
    2. Lookup decision from envelope
    3. Execute (or abstain)

    If the envelope is stale (heavy computation hasn't run), the only
    valid action is abstain.
    """

    def __init__(self, broker: ExecutionBackend,
                 kill_switch: KillSwitch,
                 reconciler: Reconciler,
                 alerter: Callable[[str], None] | None = None,
                 max_stale_minutes: float = 360):  # 6 hours for 4H bars
        self.broker = broker
        self.kill_switch = kill_switch
        self.reconciler = reconciler
        self.alerter = alerter
        self.max_stale_minutes = max_stale_minutes
        self.envelope: DecisionEnvelope | None = None
        self.last_envelope_at: pd.Timestamp | None = None
        self._stale_alert_sent = False

    def on_price(self, pair: str, bid: float, ask: float,
                 timestamp: pd.Timestamp):
        """Called on every price tick. Must be fast and exception-safe."""
        if self.kill_switch.is_triggered:
            return
        if self.envelope is None or self.envelope.is_expired(timestamp):
            self._check_stale_envelope(timestamp)
            return  # Abstain -- no valid decision available
        self._stale_alert_sent = False  # Reset: envelope is fresh
        action = self.envelope.lookup(pair, bid, ask)
        if action.type == ActionType.ABSTAIN:
            return
        self._execute(action)

    def _check_stale_envelope(self, now: pd.Timestamp):
        """Alert if no envelope received for longer than expected.

        Catches silent death of the heavy computation process.
        Without this, the system abstains forever with no alert.
        """
        if self._stale_alert_sent:
            return
        if self.last_envelope_at is None:
            return  # Still initializing
        minutes_stale = (now - self.last_envelope_at).total_seconds() / 60
        if minutes_stale > self.max_stale_minutes and self.alerter:
            self.alerter(
                f"Decision envelope stale for {minutes_stale:.0f} min. "
                f"Heavy computation may have died."
            )
            self._stale_alert_sent = True

    def update_envelope(self, envelope: DecisionEnvelope):
        """Called by the heavy computation process on bar close."""
        self.envelope = envelope
        self.last_envelope_at = envelope.computed_at
        self._stale_alert_sent = False


@dataclass(frozen=True)
class DecisionEnvelope:
    """Pre-computed decisions for the live loop to execute.

    Generated by heavy computation on bar close. Expires after
    a configurable duration (e.g., next bar close + buffer).
    """
    decisions: dict[str, Action]  # pair -> action
    computed_at: pd.Timestamp
    expires_at: pd.Timestamp
    strategy_name: str
    feature_hash: str

    def is_expired(self, now: pd.Timestamp) -> bool:
        return now > self.expires_at

    def lookup(self, pair: str, bid: float, ask: float) -> Action:
        return self.decisions.get(pair, Action(type=ActionType.ABSTAIN))
```

```python
# execution/kill_switch.py

class KillSwitch:
    """Binary circuit breaker. RUN or FLAT. Nothing in between.

    Triggers:
    - Daily P&L crosses -X% of equity -> flatten all, stop for 24h
    - Position reconciliation mismatch -> flatten all, alert
    - Token chain < 2 min remaining -> flatten all

    Can only be reset by human (function call, not automatic).
    """

    def __init__(self, max_daily_loss_pct: float = 0.02):
        self.is_triggered = False
        self.trigger_reason: str | None = None
        self.triggered_at: pd.Timestamp | None = None
        self.max_daily_loss_pct = max_daily_loss_pct

    def check(self, daily_pnl_pct: float, equity: float,
              token_minutes_remaining: float,
              reconciliation_ok: bool) -> bool:
        """Check all trigger conditions. Returns True if triggered."""
        ...

    def trigger(self, reason: str, broker: ExecutionBackend):
        """Flatten all positions and halt."""
        broker.flatten_all()
        self.is_triggered = True
        self.trigger_reason = reason
        ...

    def reset(self, operator_confirmation: str):
        """Human-only reset."""
        ...
```

```python
# execution/reconciler.py

class Reconciler:
    """Compares internal state against Saxo broker state.

    Runs on state transitions (after order fills), not on a timer,
    to conserve API rate limit budget.
    """

    def reconcile(self, internal: dict[str, Position],
                  broker: ExecutionBackend) -> ReconciliationResult:
        """Query broker positions, compare to internal state.

        Returns match/mismatch with details.
        """
        broker_positions = broker.get_positions()
        mismatches = []
        for pair in set(list(internal.keys()) + list(broker_positions.keys())):
            internal_pos = internal.get(pair)
            broker_pos = broker_positions.get(pair)
            if not self._positions_match(internal_pos, broker_pos):
                mismatches.append(Mismatch(pair, internal_pos, broker_pos))
        return ReconciliationResult(ok=len(mismatches) == 0,
                                   mismatches=mismatches)
```

### 4.8 Analysis Layer (`analysis/`) -- EXTENDED

```python
# analysis/experiment_registry.py (Phase 1)

class ExperimentRegistry:
    """SQLite-backed registry of all backtest experiments.

    Every backtest run gets a record: git hash, config snapshot,
    data fingerprint, all metrics. Enables queries like:
    "across all EURUSD carry experiments, which param region
    produced the highest Sharpe?"
    """

    def __init__(self, db_path: str = "data/experiments.db"):
        self.db_path = db_path
        self._init_db()

    def record(self, result: BacktestResult, config: dict,
               tags: list[str] | None = None) -> str:
        """Record experiment, return experiment_id."""
        ...

    def query(self, strategy: str | None = None,
              pair: str | None = None,
              min_sharpe: float | None = None,
              tags: list[str] | None = None) -> list[ExperimentRecord]:
        """Query experiments by criteria."""
        ...

    def trial_count(self) -> int:
        """Total trials run -- denominator for Deflated Sharpe Ratio."""
        ...
```

```python
# analysis/null_hypothesis.py (Phase 1)

class NullHypothesisGate:
    """Statistical validation: is this strategy distinguishable from random?

    For a candidate strategy, generates N random strategies with the same
    trade frequency and holding period. If the candidate isn't in the top
    percentile (DSR-adjusted), it's noise.

    DATA SCOPE (critical for validity):
    The null hypothesis test MUST run on held-out out-of-sample data that
    was NEVER used for strategy development or parameter tuning. Options:

    1. RECOMMENDED: Designate a held-out period BEFORE research begins
       (e.g., most recent 1 year). Never look at this data during
       development. Run the gate once as a final validation.

    2. ALTERNATIVE: Run per walk-forward test window. Each window's test
       period is out-of-sample relative to its training period. But with
       ~126 bars per window, statistical power is low. Require the
       candidate to pass in a MAJORITY of windows, not just one.

    3. AVOID: Running on the full backtest period including data used
       for development. This biases the result and defeats the purpose.

    The ExperimentRegistry's trial_count() provides the denominator
    for Deflated Sharpe Ratio adjustment, which corrects for the total
    number of strategies ever tested (not just the one being gated).
    """

    def __init__(self, n_random: int = 1000, percentile: float = 99.0):
        self.n_random = n_random
        self.percentile = percentile

    def test(self, candidate_result: BacktestResult,
             data: pd.DataFrame, pair: str,
             cost_model: CostModel,
             sizer: PositionSizer,
             total_trials: int = 1,  # from ExperimentRegistry.trial_count()
             ) -> NullHypothesisResult:
        """Run null hypothesis test on HELD-OUT data only.

        Args:
            candidate_result: Backtest result on held-out period
            data: The held-out OHLCV data (must not overlap with dev data)
            total_trials: Total strategies ever tested (for DSR correction)

        Returns: pass/fail, candidate rank, DSR-adjusted p-value.
        """
        ...

    def _generate_random_signals(self, reference: pd.Series) -> pd.Series:
        """Generate random signals with same frequency as reference."""
        ...
```

```python
# analysis/arson_test.py (Phase 1)

class BacktestArsonTest:
    """Sabotage strategy to measure signal SENSITIVITY (diagnostic).

    Systematically degrades the strategy and measures how much
    performance changes. This is a diagnostic tool, not a gate.

    INTERPRETATION (corrected from initial brainstorm):
    - If 10% randomization DOES hurt Sharpe significantly: signals
      are load-bearing. Good -- the strategy depends on its signals.
    - If 10% randomization does NOT hurt: signals may be noise, OR
      the strategy is robust to small perturbations (which is fine).
    - If 2x costs kills the strategy: edge is thin, execution critical.
    - If extra delay kills it: time-sensitive, potential lookahead risk.

    The arson test measures SENSITIVITY to degradation (diagnostic).
    The NullHypothesisGate measures SIGNIFICANCE vs random (the gate).
    Both are useful; they answer different questions. The arson test
    alone should NOT be used as a pass/fail gate.
    """

    def run(self, result: BacktestResult, data: pd.DataFrame,
            strategy: Strategy, pair: str, cost_model: CostModel,
            sizer: PositionSizer) -> ArsonResult:
        """Run suite of sabotage tests."""
        degradations = {
            'randomize_10pct': self._randomize_signals(result.signals, 0.10),
            'randomize_25pct': self._randomize_signals(result.signals, 0.25),
            'double_costs': ...,     # 2x cost multiplier
            'extra_delay': ...,      # shift signals by 1 more bar
            'corrupt_indicator': ..., # zero out one indicator
        }
        # Run backtest for each degraded version, compare metrics
        ...
```

```python
# analysis/prediction_log.py (Phase 2)

class PredictionLog:
    """Append-only log of every signal/prediction.

    Every call to generate_signals() produces a log entry:
    {timestamp, pair, strategy, signal, confidence, feature_hash,
     model_id, params_hash}

    Stored as Parquet, partitioned by month.

    This log becomes:
    - Trial registry (each unique params_hash is a trial)
    - Future meta-labeling training data
    - DSR denominator
    - Backtest-vs-live comparison dataset
    """

    def __init__(self, output_dir: str = "data/predictions"):
        self.output_dir = output_dir

    def log(self, predictions: pd.DataFrame, strategy_name: str,
            pair: str, params_hash: str): ...

    def load(self, start: str, end: str,
             strategy: str | None = None) -> pd.DataFrame: ...
```

### 4.9 Saxo Integration (`saxo/`) -- Phase 2-3

```
saxo/
  auth.py             # OAuth2 with token chain fuel gauge
  client.py           # REST client (positions, orders, instruments)
  streaming.py        # WebSocket price streaming
  mapping.py          # Internal pair names <-> Saxo UICs
```

```python
# saxo/auth.py

class SaxoAuth:
    """OAuth2 token management with fuel gauge.

    Saxo tokens: 20-min access, 40-min single-use refresh.
    Missing a single refresh cycle = permanent auth death = manual re-auth.

    Fuel gauge: tracks time-to-death, refresh jitter, and triggers
    emergency procedures when running low.
    """

    def __init__(self, client_id: str, redirect_uri: str):
        self.client_id = client_id
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.access_expires_at: pd.Timestamp | None = None
        self.refresh_expires_at: pd.Timestamp | None = None

    @property
    def minutes_to_auth_death(self) -> float:
        """Time until refresh token expires (= permanent auth loss)."""
        ...

    def ensure_valid(self) -> str:
        """Return valid access token, refreshing if needed.
        Raises AuthChainDead if refresh token has expired.
        """
        ...

    def should_emergency_flatten(self) -> bool:
        """True if < 2 minutes to auth death."""
        return self.minutes_to_auth_death < 2.0
```

---

## 5. Data Flow

### Research Mode (Phase 1)

```
OHLCV (Parquet)
    |
    v
validate() --> compute_indicators() --> strategy.generate_predictions()
    |                                           |
    |                                    +------v-------+
    |                                    | signal       |
    |                                    | confidence   |
    |                                    | feature_hash |
    |                                    +------+-------+
    |                                           |
    v                                           v
experiment_registry.record()     sizer.calculate_size(signal, confidence,
    |                                ratchet_level)
    |                                           |
    v                                           v
null_hypothesis_gate.test()      run_backtest(data, signals, sizer, costs)
    |                                           |
    v                                           v
arson_test.run()                 BacktestResult + PerformanceMetrics
    |                                           |
    v                                           v
PASS / FAIL decision             prediction_log.log()
```

### Live Mode (Phase 3)

```
                    +------ Slow Path (bar close) ------+
                    |                                    |
Saxo WebSocket ---->|  indicators + signals + sizing     |
  (streaming       |  compute_indicators()              |
   bid/ask)        |  strategy.generate_predictions()    |
      |            |  sizer.calculate_size()             |
      |            |  --> DecisionEnvelope               |
      |            +------------------------------------+
      |                          |
      v                          v
+-- Fast Path (every tick) ----------------------------+
|                                                      |
|  SkinnyLiveLoop.on_price(pair, bid, ask, ts)         |
|    if kill_switch.is_triggered: return               |
|    if envelope expired: return (abstain)             |
|    action = envelope.lookup(pair, bid, ask)          |
|    if action == ABSTAIN: return                      |
|    broker.execute_signal(...)                        |
|    reconciler.reconcile(...)                         |
|                                                      |
+------------------------------------------------------+
      |
      v
prediction_log.log()  +  structured_trade_log.append()
```

---

## 6. Key Design Decisions

### 6.1 Why Not Full Event-Driven for Backtest?

NautilusTrader uses event-driven for everything (backtest + live). We don't because:
- Vectorized backtesting is 100-1000x faster for research iteration
- At daily/4H frequency, event-driven overhead isn't justified
- The brainstorm found "death by infrastructure" as the #1 failure mode (60% probability)
- Strategy code is already pure functions that don't depend on execution mode

**Trade-off:** Slight behavioral differences between vectorized backtest and event-driven live. Mitigated by the paper trading reconciliation engine that measures this gap directly.

### 6.2 Why `generate_predictions()` Instead of Changing `generate_signals()`?

Backward compatibility. The 3 existing strategies continue to work via the default implementation that wraps `generate_signals()`. New strategies (carry, ML) use the richer DataFrame output. The engine only reads the `signal` column -- everything else is metadata for downstream systems.

### 6.3 Why Binary Kill Switch, Not 5-Level Degradation?

The brainstorm's Devil's Advocate found that graduated degradation is:
- Untestable (can't simulate all 5 levels reliably)
- Threshold-sensitive (each level boundary is a parameter to miscalibrate)
- Assumes gradual failure (real failures are cliff-edges)

Binary is: working or flat. Easy to test, easy to verify, no edge cases.

### 6.4 Why Reconcile on Events, Not on a Timer?

Saxo rate limit is 1 request/second. Timer-based reconciliation (every 30 seconds) wastes API budget. Event-triggered reconciliation (after each order fill) is cheaper and targets the exact moments when state can diverge.

### 6.5 Why SQLite for Experiment Registry?

- Zero deployment overhead (single file)
- SQL queries for experiment analysis
- Sufficient for millions of records
- No server to maintain (solo operator)
- **NOTE:** Use WAL mode (`PRAGMA journal_mode=WAL`) to support concurrent
  reads during parallel backtest runs. Without WAL, concurrent writes from
  parallel parameter searches will cause lock errors.

---

## 7. Extension Points for ML

The architecture has 4 deliberate ML integration points that require zero ML code today:

| Extension Point | Interface | When to Build |
|----------------|-----------|---------------|
| **Strategy.generate_predictions()** | Returns DataFrame with `signal` + metadata | Now (default wraps generate_signals) |
| **Walk-forward train_fn hook** | `run_walkforward(..., train_fn=None)` | When first ML strategy is ready |
| **Prediction log** | Append-only Parquet with feature_hash | Phase 2 (becomes ML training data) |
| **Three-layer decision** | What (direction) / When (timing) / How Much (sizing) | After multiple strategies proven |

**ML integration sequence (from brainstorm):**
1. First ML: timing layer (CUSUM filter or classifier that decides when NOT to trade)
2. Second ML: sizing layer (meta-labeling -- predicts which signals will be profitable)
3. Last ML: direction layer (only after timing and sizing proven)

---

## 8. Risk Architecture

```
+----------------------------------------------------------+
|                    RISK LAYERS                            |
|                                                          |
|  Layer 1: Signal Level                                   |
|    - Flat as default (continuous sizing)                  |
|    - Null hypothesis gate (pre-deployment)                |
|    - Arson test (pre-deployment)                          |
|                                                          |
|  Layer 2: Position Level                                 |
|    - Capital ratchet (scales with trust)                  |
|    - Max position % cap (hard limit in code, NOT config)  |
|    - ATR-based stop distance                              |
|                                                          |
|  Layer 3: Account Level                                  |
|    - Binary kill switch (daily loss > X% = flatten)       |
|    - Token fuel gauge (auth death = flatten)              |
|    - Reconciliation mismatch = flatten                    |
|                                                          |
|  Layer 4: Operational Level                              |
|    - Autonomy ladder (Manual -> Supervised -> Auto)       |
|    - Daily review ritual (3 numbers: match/drift/should)  |
|    - Monthly chaos test (one fault injection)             |
|                                                          |
+----------------------------------------------------------+
```

### Configuration Tiers (from brainstorm)

| Tier | What | Where | Change Process |
|------|------|-------|----------------|
| **0 (Invariants)** | `entry_delay_bars=1`, `MAX_POSITION_PCT=0.10`, kill switch thresholds | Hardcoded in `core/constants.py` with tests that assert the values. `max_position_pct` is currently a config param in YAML -- must be migrated to a constant. | Code review + test passes |
| **1 (Environment)** | API keys, endpoints, account IDs | Environment variables | Never in source control |
| **2 (Strategy)** | Fast/slow periods, RSI thresholds, rebalance frequency | YAML config | Versioned, logged in experiment registry |
| **3 (Runtime)** | One-off overrides, temporary pair disable | CLI flags | Ephemeral, logged but not persisted |

---

## 9. Directory Structure (Target)

```
forex-trading-system/
  src/forex_system/
    core/
      __init__.py
      interfaces.py      # Strategy, CostModel, ExecutionBackend, PositionSizer
      types.py            # Direction, Trade, Position, ExecutionResult, etc.
      config.py           # YAML loading
      constants.py        # Tier 0 invariants (hardcoded)
      errors.py
    data/
      sources/
        csv_source.py
        parquet_source.py
        saxo_source.py          # Phase 2
      validation.py
      storage.py
      transforms.py
      spread_recorder.py        # Phase 1
    features/
      indicators.py
      registry.py
    strategies/
      registry.py
      ma_crossover.py
      bollinger_rsi.py
      momentum.py
      carry.py                  # Phase 1
    costs/
      model.py                  # Static (Phase 0)
      measured.py               # Measured from Saxo (Phase 1)
    sizing/                     # NEW
      continuous.py             # Signal -> size (continuous)
      ratchet.py                # Capital ratchet protocol
    backtest/
      engine.py                 # Vectorized (unchanged core logic)
      metrics.py
      walkforward.py
      portfolio.py
    analysis/
      reports.py
      visualization.py
      comparison.py
      experiment_registry.py    # Phase 1
      null_hypothesis.py        # Phase 1
      arson_test.py             # Phase 1
      prediction_log.py         # Phase 2
    execution/                  # Phase 3
      broker.py                 # SaxoBroker implements ExecutionBackend
      fsm.py                    # Order state machine
      token_manager.py          # Token chain + fuel gauge
      reconciler.py             # Position reconciliation
      kill_switch.py            # Binary circuit breaker
      live_loop.py              # Skinny live loop
    saxo/                       # Phase 2-3
      auth.py                   # OAuth2 + fuel gauge
      client.py                 # REST client
      streaming.py              # WebSocket
      mapping.py                # Pair <-> UIC mapping
  config/
    default.yaml                # Tier 2 strategy params
  data/
    experiments.db              # SQLite experiment registry
    predictions/                # Append-only prediction logs
    spreads/                    # Recorded Saxo spread data
  docs/
    architecture.md             # This document
  tests/
    ...
  scripts/
    run_backtest.py
    record_spreads.py           # Phase 1
    run_paper.py                # Phase 2
    run_live.py                 # Phase 3
```

---

## 10. Implementation Priority

Based on the brainstorm's recommended sequence, informed by the Devil's Advocate:

### Phase 1: Validate the Premise (Weeks 1-4)

| # | What | Why | LOC est. |
|---|------|-----|----------|
| 1 | Swap rate check | Is carry positive after Saxo costs? 2-hour task | ~50 |
| 2 | `SpreadRecorder` + Saxo SIM connection | Measure real costs | ~300 |
| 3 | `CarryStrategy` | The one strategy with academic evidence | ~100 |
| 4 | `ContinuousSizer` | Flat-as-default via continuous sizing | ~100 |
| 5 | `ExperimentRegistry` (SQLite) | Track all experiments systematically | ~200 |
| 6 | `NullHypothesisGate` | Statistical rigor for every strategy | ~250 |
| 7 | `BacktestArsonTest` | Measure signal robustness | ~200 |
| 8 | `MeasuredCostModel` | Use real spread data in backtests | ~150 |

**Gate:** At least one strategy passes null hypothesis gate.

### Phase 2: Paper + Micro-Live (Month 2)

| # | What | Why |
|---|------|-----|
| 9 | Saxo SIM data source | Real-time data for paper trading |
| 10 | Paper execution backend | Simulated order execution on Saxo SIM |
| 11 | Paper trading reconciliation | Measure backtest-vs-paper divergence |
| 12 | `PredictionLog` | Every signal logged for future analysis |
| 13 | Micro-trade engine (0.01 lots) | Real fills, real slippage, $5/trade risk |
| 14 | Autonomy: Manual + Suggest modes | Human approves/rejects before execution |

**Gate:** Reality tax (backtest-vs-paper divergence) within acceptable bounds.

### Phase 3: Live Trading (Month 3+)

| # | What | Why |
|---|------|-----|
| 15 | `SaxoBroker` (full live) | Real order execution |
| 16 | `OrderFSM` | Explicit order lifecycle with stuck-state detection |
| 17 | `SaxoAuth` with fuel gauge | Token chain management |
| 18 | `KillSwitch` | Binary circuit breaker |
| 19 | `SkinnyLiveLoop` | Thin real-time execution path |
| 20 | `Reconciler` | Event-triggered position reconciliation |
| 21 | `CapitalRatchet` (live) | Trust-building sizing protocol |
| 22 | Autonomy: Supervised + Auto modes | Gradual increase in system independence |

---

## Appendix: What We Deliberately Chose NOT to Build

| Idea | Why Deferred |
|------|-------------|
| Event-sourced audit trail | 80% of value from structured trade log at 10% complexity |
| Shadow signal architecture | Premature until we have working strategies to shadow |
| Three-layer decision (What/When/How Much) | Need working first layer before decomposing |
| Genotype/phenotype strategy separation | Massively expands hypothesis space with insufficient data |
| 5-level graduated degradation | Untestable, threshold-sensitive. Binary kill switch sufficient |
| Full message bus / pub-sub | Overkill for solo operator with 3-10 pairs |
| ML model registry | No ML models yet. Experiment registry sufficient for now |
