# mlfinlab Architecture Analysis

Source: [hudson-and-thames/mlfinlab](https://github.com/hudson-and-thames/mlfinlab) (4,639 stars)
Analyzed: 2026-03-30

Implements techniques from Marcos Lopez de Prado's "Advances in Financial Machine Learning" (AFML). Focus: labeling, feature engineering, validation, and bet sizing for ML-driven trading.

---

## 1. Module Structure

| Module | AFML Chapter | Purpose |
|--------|-------------|---------|
| `labeling/` | Ch 3-4 | Triple barrier, meta-labeling, trend scanning |
| `features/` | Ch 5 | Fractional differentiation |
| `filters/` | Ch 2 | CUSUM filter, z-score filter |
| `cross_validation/` | Ch 7, 12 | Purged K-Fold, Combinatorial Purged CV |
| `sample_weights/` | Ch 4 | Return-based and time-decay weights |
| `sampling/` | Ch 4 | Sequential bootstrapping, concurrency |
| `bet_sizing/` | Ch 10 | Probability, dynamic, budget, reserve sizing |
| `structural_breaks/` | Ch 17 | CUSUM test, Chow test, SADF |
| `data_structures/` | Ch 2 | Tick/volume/dollar/imbalance/run bars |

---

## 2. Triple Barrier Method (Labeling)

**Problem:** Fixed-horizon labeling ignores path-dependent outcomes. A trade can hit stop-loss then reverse -- fixed label says "profit" but trade was stopped out.

**Algorithm:**
1. CUSUM filter identifies event timestamps (potential entries)
2. For each event, three barriers:
   - **Upper** = entry + pt_sl[0] * target (profit-take)
   - **Lower** = entry - pt_sl[1] * target (stop-loss)
   - **Vertical** = entry time + max_holding_period
3. Target = daily volatility (ewm std of returns)
4. Walk forward, find which barrier is touched first
5. Label: +1 (upper), -1 (lower), 0 (vertical)

**API:**
```python
from mlfinlab.filters.filters import cusum_filter
from mlfinlab.labeling import add_vertical_barrier, get_events, get_bins

# Event sampling
t_events = cusum_filter(close, threshold=daily_vol.mean())

# Vertical barrier
t1 = add_vertical_barrier(t_events, close, num_days=5)

# Triple barrier events
events = get_events(
    close=close, t_events=t_events, pt_sl=[1, 1],
    target=daily_vol, min_ret=0.01, num_threads=4,
    vertical_barrier_times=t1,
    side_prediction=None,  # None for primary; pd.Series for meta-labeling
)

# Labels
labels = get_bins(triple_barrier_events=events, close=close)
# labels['bin'] in {-1, 0, 1}
```

**Forex params:** `pt_sl=[2, 1]` for 2:1 reward/risk, `target=daily_vol`, `num_days=5` for swing.

---

## 3. Meta-Labeling (Sizing Decisions)

**Problem:** One model learning both side AND size is hard. Decouple: primary model decides side, meta-model decides whether to bet and how much.

**Algorithm:**
1. Train primary model -> side predictions (+1/-1)
2. Pass to `get_events(side_prediction=primary_pred)`
3. Triple barrier considers only relevant barrier (upper for longs, lower for shorts)
4. `get_bins()` returns binary {0, 1} -- was primary correct?
5. Train meta-classifier on binary labels
6. Meta-model's predicted probability = bet size

```python
# Primary model
primary_clf.fit(X_train, y_train_side)
side_pred = pd.Series(primary_clf.predict(X), index=t_events)

# Meta-labeling
meta_events = get_events(
    close=close, t_events=t_events, pt_sl=[1, 2],
    target=daily_vol, vertical_barrier_times=t1,
    side_prediction=side_pred,  # <-- enables meta-labeling
)
meta_labels = get_bins(meta_events, close)  # {0, 1} labels

# Meta-model
meta_clf.fit(X, meta_labels['bin'])
prob = meta_clf.predict_proba(X_new)[:, 1]   # Confidence
bet_size = side * prob                         # Signed position size
```

**Forex application:** MA crossover / Bollinger RSI = primary model (side). Meta-model learns WHEN those strategies are reliable using features like volatility regime, time-of-day, spread.

---

## 4. Fractional Differentiation (Stationarity with Memory)

**Problem:** ML needs stationary features. Standard differencing (d=1) destroys memory/signal. Fractional diff (0 < d < 1) achieves stationarity while preserving predictive information.

**Algorithm:** Binomial expansion of `(1 - B)^d`:
```
(1-B)^d * X_t = sum_{k=0}^{inf} w_k * X_{t-k}
w_k = -w_{k-1} * (d - k + 1) / k,  w_0 = 1
```

Two variants:
- **Expanding window** (`frac_diff`): uses all past, weights approach zero
- **Fixed-width FFD** (`frac_diff_ffd`): truncates below threshold. Preferred in practice.

```python
from mlfinlab.features.fracdiff import FractionalDifferentiation

fd = FractionalDifferentiation()

# Fixed-width (preferred)
frac_series = fd.frac_diff_ffd(series=price_df, diff_amt=0.4, thresh=1e-5)

# Find optimal d: smallest d where ADF test passes
from statsmodels.tsa.stattools import adfuller
for d in np.arange(0.0, 1.1, 0.1):
    frac = fd.frac_diff_ffd(close_df, diff_amt=d, thresh=1e-5)
    adf_p = adfuller(frac.dropna())[1]
    corr = frac.dropna().corr(close.reindex(frac.dropna().index))
    # Choose smallest d where p < 0.05
# For EUR/USD: d typically 0.3-0.5
```

---

## 5. CUSUM Filter (Event Sampling)

**Problem:** Fixed-frequency sampling creates redundant, overlapping observations. CUSUM triggers only when cumulative returns exceed a threshold.

**Algorithm:**
```
S_high = max(0, S_high + (price_change - threshold))
S_low  = min(0, S_low  + (price_change + threshold))
if S_high >= threshold: trigger event, reset
if S_low <= -threshold: trigger event, reset
```

```python
from mlfinlab.filters.filters import cusum_filter

# Fixed threshold
t_events = cusum_filter(close, threshold=0.02)

# Dynamic threshold (rolling volatility)
t_events = cusum_filter(close, threshold=daily_vol)
```

**Forex:** `threshold=daily_vol.mean()` gives ~1-3 events/day in normal conditions.

---

## 6. Purged Cross-Validation

**Problem:** Standard k-fold leaks info when labels overlap in time. Purged CV removes training observations whose label span overlaps test observations. Embargo adds buffer.

```python
from mlfinlab.cross_validation import PurgedKFold, ml_cross_val_score

samples_info_sets = events['t1']  # event end times

cv_gen = PurgedKFold(
    n_splits=5,
    samples_info_sets=samples_info_sets,
    pct_embargo=0.01,  # 1% embargo after test fold
)

scores = ml_cross_val_score(
    classifier=clf, X=X, y=y, cv_gen=cv_gen,
    sample_weight_train=weights.values,
    sample_weight_score=weights.values,
    scoring=accuracy_score,
)
```

**Combinatorial Purged CV** (CPCV): `n_splits=6, n_test_splits=2` produces C(6,2)=15 splits and 5 backtest paths. Tests for backtest overfitting (PBO).

**Forex:** Critical because triple barrier labels overlap ~5x with 5-day holding. Without purging, 75% CV accuracy drops to ~52% OOS. Use `pct_embargo=0.01-0.05`.

---

## 7. Sample Weighting

**Problem:** Overlapping labels = redundant observations. Without weights, model overfits to duplicated information.

**Return-based weights** (uniqueness of each label's return contribution):
```python
from mlfinlab.sample_weights import get_weights_by_return
sample_weights = get_weights_by_return(events, close, num_threads=4)
```

**Time-decay weights** (emphasize recent data):
```python
from mlfinlab.sample_weights import get_weights_by_time_decay
sample_weights = get_weights_by_time_decay(events, close, decay=0.5)
# decay=1: equal, 0<d<1: linear decay, d=0: converge to zero, d<0: oldest erased
```

**Sequential bootstrapping** (draw samples respecting uniqueness):
```python
from mlfinlab.sampling import get_ind_matrix, seq_bootstrap
ind_mat = get_ind_matrix(events['t1'], close)
bootstrapped = seq_bootstrap(ind_mat, sample_length=len(events))
```

---

## 8. Bet Sizing

Convert ML probability to position size.

**Probability-based** (simplest):
```python
from mlfinlab.bet_sizing import bet_size_probability
bet_sizes = bet_size_probability(
    events=events, prob=probabilities, num_classes=2,
    pred=predictions,  # +1/-1 sides
    step_size=0.1,     # discretize to 10% increments
    average_active=True,
)
# signal = (2 * norm.cdf(z_score) - 1) * side
```

**Dynamic sizing** (forecast vs market price divergence):
```python
from mlfinlab.bet_sizing import bet_size_dynamic
result = bet_size_dynamic(
    current_pos=0, max_pos=100, market_price=1.1050,
    forecast_price=1.1100, cal_divergence=10, cal_bet_size=0.95, func='sigmoid',
)
```

**Budget-based** and **Reserve-based** (from concurrent bet counts / Gaussian mixture) also available.

**Discretization** prevents overtrading:
```python
from mlfinlab.bet_sizing.ch10_snippets import discrete_signal
discretized = discrete_signal(signal0=bet_sizes, step_size=0.1)
```

---

## 9. Structural Breaks (Regime Detection)

```python
from mlfinlab.structural_breaks import (
    get_chu_stinchcombe_white_statistics,  # CUSUM -- detect mean shift
    get_chow_type_stat,                    # Chow -- detect unit root change
    get_sadf,                              # SADF -- detect bubbles/explosiveness
)
```

**SADF** for forex: detect when a pair enters explosive/trending phase vs mean-reverting. **Chow test** detects structural breaks triggering model retraining.

---

## 10. Complete Pipeline for Forex

```python
# 1. FRACTIONAL DIFFERENTIATION
frac_close = fd.frac_diff_ffd(close_df, diff_amt=0.4, thresh=1e-5)

# 2. EVENT SAMPLING
t_events = cusum_filter(close, threshold=daily_vol.mean())

# 3. TRIPLE BARRIER LABELING
t1 = add_vertical_barrier(t_events, close, num_days=5)
events = get_events(close, t_events, pt_sl=[1,1], target=daily_vol, vertical_barrier_times=t1)
labels = get_bins(events, close)

# 4. SAMPLE WEIGHTS
weights = get_weights_by_return(events, close)

# 5. FEATURES
features = pd.DataFrame({
    'frac_diff': frac_close.reindex(t_events),
    'rsi': rsi.reindex(t_events),
    'volatility': daily_vol.reindex(t_events),
})

# 6. PRIMARY MODEL (side)
cv_gen = PurgedKFold(n_splits=5, samples_info_sets=events['t1'], pct_embargo=0.02)
scores = ml_cross_val_score(clf, X, y, cv_gen, sample_weight_train=weights.values)

# 7. META-LABELING (bet/no-bet)
side_pred = primary_clf.predict(X)
meta_events = get_events(close, t_events, pt_sl=[1,2], target=daily_vol,
                          vertical_barrier_times=t1, side_prediction=side_pred)
meta_labels = get_bins(meta_events, close)
meta_clf.fit(X, meta_labels['bin'], sample_weight=weights)

# 8. BET SIZING
prob = meta_clf.predict_proba(X)[:, 1]
bet_sizes = bet_size_probability(events, prob, num_classes=2, pred=side_pred, step_size=0.1)
```

---

## 11. Key Parameters for Forex

| Parameter | Typical Forex Value | Rationale |
|-----------|-------------------|-----------|
| `pt_sl` | [1,1] to [2,1] | Symmetric or 2:1 reward/risk |
| `target` | ewm(span=50).std() | 50-bar exponential volatility |
| `min_ret` | 0.005 (50 pips majors) | Filter noise-level moves |
| `num_days` (vertical) | 1-10 | Max holding period |
| `cusum_threshold` | daily_vol.mean() | 1-sigma triggers event |
| `frac_diff d` | 0.3-0.5 | Minimum for ADF stationarity |
| `n_splits` (CV) | 5-10 | Standard k-fold |
| `pct_embargo` | 0.01-0.05 | 1-5% after each test fold |
| `decay` (time weights) | 0.5 | Moderate recency emphasis |
| `step_size` (bet disc.) | 0.1 | 10% position increments |

---

## 12. Comparison with Our System

| Area | Our System (Phase 0) | mlfinlab | Recommendation |
|------|---------------------|---------|----------------|
| Labeling | None (no ML) | Triple barrier + meta-labeling | Adopt for Phase 1 ML |
| Feature engineering | Raw indicators | Fractional differentiation | Add as ML feature pipeline |
| Event sampling | Every bar | CUSUM filter | Adopt for informative samples |
| Cross-validation | None | Purged K-Fold with embargo | Critical for proper ML validation |
| Sample weights | None | Return-based + time-decay | Required for overlapping labels |
| Position sizing | ATR fixed fractional | Probability-based bet sizing | Add ML-confidence sizing |
| Walk-forward | Rolling train/test windows | Same + sequential bootstrap | Add sequential bootstrap |
| Regime detection | None | SADF + structural breaks | Add for strategy selection |

### Priority Adoptions for Phase 1 ML

1. **Triple barrier labeling** -- replace fixed-horizon labels
2. **CUSUM filter** -- event-driven sampling instead of every bar
3. **Purged cross-validation** -- eliminate data leakage in ML evaluation
4. **Fractional differentiation** -- stationary features preserving memory
5. **Meta-labeling** -- decouple side (existing strategies) from sizing (ML)
6. **Sample weights** -- handle overlapping labels properly
7. **Bet sizing** -- convert ML probability to position size
8. **SADF** -- detect regime changes for strategy switching
