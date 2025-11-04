<!-- 11e2a917-515e-447a-bdae-5ffea46f2b9b 143164cf-b097-4b62-9984-f7956671e51e -->
# Modular Trading System Rebuild Plan

## Executive Summary

Your current system has accumulated technical debt and architectural flaws causing recurring failures. This plan rebuilds from scratch with:

- **Modular architecture** - each component is independent and replaceable
- **Fault isolation** - one broken component doesn't crash the whole system
- **Clear separation** - data, strategies, execution, and risk are separate layers
- **Local-first development** - test and perfect locally before cloud deployment

## Critical Issues in Current System

### 1. **Configuration Hell** (Root Cause of Most Failures)

**Problem:** Three competing configuration systems fight each other:

- `accounts.yaml` (intended source of truth)
- Environment variables in `app.yaml` (overwrites YAML)
- Hardcoded values in multiple files (fallbacks that become defaults)

**Evidence:**

```python
# dynamic_account_manager.py loads from YAML
# order_manager.py loads from environment variables
# app.yaml has hardcoded values
# Result: System uses app.yaml, ignores accounts.yaml changes
```

**Impact:** Deployments fail, wrong instruments trade, settings don't apply

---

### 2. **Trend Detection Inversion** (Lost $7,983)

**Problem:** Momentum strategies trade AGAINST trends, not WITH them

**Evidence from SYSTEMIC_FAILURE_REPORT.md:**

- USD/CAD in STRONG UPTREND (rising)
- System entered 36 SELL trades (shorting the uptrend)
- All 36 lost money (-$7,983)

**Root cause in momentum_trading.py line 836-838:**

```python
# Checks if trend and momentum disagree but logic is backwards
# Allows counter-trend trades instead of blocking them
```

---

### 3. **No Concentration Limits** (Account 011: 25 positions in one pair!)

**Problem:** Risk manager doesn't enforce per-instrument limits

**Evidence:**

- Account 011: 25 USD/CAD positions (all losing)
- Account 006: 11 USD/CAD positions (all losing)
- No "max positions per instrument" check

---

### 4. **Duplicate/Conflicting Components**

**Current system has:**

- 2 data feed classes (`data_feed.py`, `streaming_data_feed.py`, `multi_account_data_feed.py`)
- 2 account managers (`account_manager.py`, `dynamic_account_manager.py`)
- 3 config loaders (`config_loader.py`, `yaml_manager.py`, `strategy_config_loader.py`)
- Multiple scanners fighting for control

**Result:** Unknown which component actually runs

---

### 5. **Monolithic Deployment**

**Problem:** 4,028-line `main.py` with everything tightly coupled

**Impact:**

- Breaks in dashboard crash trading engine
- Can't test components independently
- Cloud deployments fail mysteriously
- No graceful degradation

---

## New Architecture: Modular & Fault-Isolated

### Layer 1: Core Infrastructure (Reusable, Stable)

#### `core/broker_api.py` - Broker Interface

- **Purpose:** Single interface to OANDA API
- **Responsibilities:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Connection management
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Rate limiting
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Price fetching
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Order placement/cancellation
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Position/account queries
- **Configuration:** API key, account ID, environment (live/practice)
- **Error handling:** Retries, fallbacks, connection recovery
- **No dependencies:** Only uses OANDA v20 library

#### `core/market_data.py` - Market Data Feed

- **Purpose:** Real-time price streaming
- **Responsibilities:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Subscribe to instrument prices
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Maintain price history (last 200 candles per instrument)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Calculate basic indicators (SMA, EMA, ATR)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Validate data freshness
- **Updates:** Every 5 seconds, force-refresh to avoid stale data
- **Storage:** In-memory ring buffers (no database for real-time data)
- **Fault tolerance:** If data feed fails, strategies pause (don't trade on stale data)

#### `core/risk_manager.py` - Risk Management Engine

- **Purpose:** Enforce ALL risk rules before any trade
- **Pre-trade checks:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                1. Account balance sufficient
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                2. Max positions not exceeded (global + per-instrument)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                3. Daily trade limit not hit
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                4. Margin available
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                5. Position size within limits
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                6. No excessive correlation (max 2 correlated pairs)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                7. Spread acceptable (<3 pips)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                8. Trading hours valid (London/NY sessions only)

- **Per-instrument limits:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Max 3 positions per instrument
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Max 30% account exposure per instrument
- **Circuit breaker:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If account loses >2% in one day → STOP ALL TRADING
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Send Telegram alert immediately
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Require manual re-enable

#### `core/order_executor.py` - Order Execution

- **Purpose:** Execute approved trades with broker
- **Flow:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                1. Receive signal from strategy
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                2. Pass through risk_manager (if rejected, log and return)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                3. Calculate position size based on risk
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                4. Place market order with SL/TP
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                5. Confirm execution
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                6. Log to database

- **Error handling:** If order fails, log reason, alert user, don't retry automatically
- **No strategy logic:** Pure execution, no decision-making

---

### Layer 2: Strategy Framework (Hot-swappable)

#### `strategies/base_strategy.py` - Strategy Interface

**All strategies inherit from this base class:**

```python
class BaseStrategy:
    def __init__(self, config: dict):
        self.name = config['name']
        self.instruments = config['instruments']
        self.timeframe = config['timeframe']
        self.enabled = True
        
    def analyze(self, market_data: dict) -> List[TradeSignal]:
        """Override this: return list of trade signals"""
        raise NotImplementedError
        
    def validate_signal(self, signal: TradeSignal) -> bool:
        """Optional: additional strategy-specific validation"""
        return True
```

**Why this works:**

- Each strategy is completely independent
- Strategy files are 200-300 lines max
- Easy to add/remove/modify strategies
- No strategy can crash another strategy
- Easy to backtest (same interface)

---

#### Individual Strategy Files (One per strategy)

**Gold Strategies:**

1. `strategies/gold_scalping.py` - Quick 5M scalps on gold
2. `strategies/gold_momentum.py` - Trend-following on gold
3. `strategies/gold_breakout.py` - Range breakouts on gold

**Forex Strategies:**

4. `strategies/gbp_usd_momentum.py` - GBP/USD trend following
5. `strategies/eur_usd_mean_reversion.py` - EUR/USD range trading
6. `strategies/jpy_pairs_breakout.py` - USD/JPY, EUR/JPY, GBP/JPY breakouts
7. `strategies/commodity_fx.py` - AUD/USD, NZD/USD, USD/CAD (oil-correlated)

**Multi-asset Strategies:**

8. `strategies/news_momentum.py` - Trade breakouts after high-impact news
9. `strategies/session_scalper.py` - London/NY open scalping
10. `strategies/swing_trader.py` - Multi-day position trading

**Each strategy file contains:**

- Entry logic (when to BUY/SELL)
- Exit logic (SL/TP calculation)
- Filters (trend, volume, session)
- Parameters (tunable via config)
- Backtest results (documented in file header)

---

### Layer 3: News & Context (External Intelligence)

#### `intelligence/news_aggregator.py` - News Feed

- **Purpose:** Fetch economic news from multiple sources
- **Sources:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Alpha Vantage (economic calendar)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Marketaux (forex news)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Economic calendar APIs
- **Data collected:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Event time, currency, impact (high/medium/low)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Sentiment (positive/negative/neutral)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Actual vs forecast vs previous
- **Update frequency:** Every 15 minutes
- **Storage:** SQLite database (news_events.db)

#### `intelligence/sentiment_analyzer.py` - News Sentiment

- **Purpose:** Determine if news is bullish/bearish for each currency
- **Logic:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Positive GDP → Bullish for that currency
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Rate hike → Bullish for that currency
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Poor employment → Bearish for that currency
- **Integration with strategies:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - High-impact news in next 30 min → Pause trading or tighten stops
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Sentiment conflicts with signal → Reduce position size 50%
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Strong sentiment aligns with signal → Increase confidence

#### `intelligence/market_regime.py` - Market State Detection

- **Purpose:** Detect if market is trending, ranging, or volatile
- **Indicators:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - ADX > 25 → Trending (use momentum strategies)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - ADX < 20 → Ranging (use mean reversion strategies)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - ATR > 2x average → Volatile (reduce position sizes)
- **Per-instrument:** Each pair has its own regime
- **Updates:** Every 5 minutes

---

### Layer 4: Orchestration (System Coordination)

#### `orchestrator/strategy_coordinator.py` - Strategy Manager

- **Purpose:** Run all active strategies and collect signals
- **Execution flow:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                1. Get latest market data from market_data.py
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                2. For each enabled strategy:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Call strategy.analyze(market_data)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Collect returned signals

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                1. Filter duplicates (same instrument from multiple strategies)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                2. Rank signals by confidence
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                3. Pass to position_manager for execution

- **Concurrency:** Strategies run in parallel (threadpool)
- **Timeout:** If strategy takes >10 seconds, skip it (don't block others)
- **Error handling:** If strategy crashes, log error, disable strategy, alert user

#### `orchestrator/position_manager.py` - Position Coordination

- **Purpose:** Manage all open positions across all accounts
- **Tracks:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Open positions per account
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Open positions per instrument
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - P&L per position
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Position age
- **Actions:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Break-even stops (move SL to entry after 20 pip profit)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Trailing stops (move SL every 15 pips in profit)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Force close weekend positions (Friday 9PM UTC)
- **Heartbeat:** Checks positions every 60 seconds

---

### Layer 5: Data & Persistence (Historical Record)

#### `database/trade_logger.py` - Trade Database

- **Storage:** SQLite (local), PostgreSQL (cloud)
- **Tables:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - trades (all executed trades)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - signals (all generated signals, even if not traded)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - account_snapshots (hourly account state)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - performance_metrics (daily stats)
- **Retention:** Keep all data forever (for backtesting improvements)

#### `database/backtest_engine.py` - Backtesting

- **Purpose:** Test strategies on historical data before going live
- **Process:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                1. Load historical candles from OANDA
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                2. Replay candles through strategy
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                3. Simulate order fills
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                4. Calculate P&L, win rate, max drawdown

- **Validation gate:** Strategy must show 55%+ win rate on 2 weeks of data before enabling

---

### Layer 6: Monitoring & Alerts (Human Oversight)

#### `monitoring/telegram_alerts.py` - Telegram Notifications

- **Real-time alerts:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Trade opened/closed (with P&L)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Risk limit hit
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Daily P&L summary (every day at 5PM UTC)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - System errors
- **Alert levels:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - 🟢 INFO: Trade executed
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - 🟡 WARNING: Risk limit approaching
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - 🔴 CRITICAL: Circuit breaker triggered, system stopped

#### `monitoring/dashboard_api.py` - Web Dashboard (Optional, Separate Process)

- **Purpose:** View system status in browser
- **Endpoints:**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `/api/status` - System health
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `/api/positions` - Open positions
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `/api/performance` - P&L charts
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `/api/strategies` - Strategy status
- **Isolation:** Dashboard runs in separate process
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If dashboard crashes, trading continues
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Dashboard reads from database, doesn't touch live trading

---

## Configuration: Single Source of Truth

### `config.yaml` - Master Configuration File

```yaml
# Accounts (One per strategy for fault isolation)
accounts:
 - id: "101-004-30719775-001"
    name: "Gold Scalping"
    strategy: "gold_scalping"
    instruments: ["XAU_USD"]
    enabled: true
    risk:
      max_risk_per_trade: 0.01  # 1%
      max_positions: 3
      daily_trade_limit: 15
      
 - id: "101-004-30719775-002"
    name: "GBP Momentum"
    strategy: "gbp_usd_momentum"
    instruments: ["GBP_USD"]
    enabled: true
    risk:
      max_risk_per_trade: 0.015  # 1.5%
      max_positions: 2
      daily_trade_limit: 10
      
  # ... 8 more accounts (one per strategy)

# Global Risk Settings
global_risk:
  circuit_breaker_loss_pct: 2.0  # Stop all trading if lose 2% in one day
  max_total_positions: 20
  max_positions_per_instrument: 3
  max_correlated_pairs: 2
  trading_sessions: ["london", "ny"]  # Only trade London/NY sessions

# News Integration
news:
  enabled: true
  pause_before_high_impact: 30  # minutes
  sentiment_threshold: 0.6
  sources: ["alpha_vantage", "marketaux"]

# Telegram
telegram:
  token: "your_token"
  chat_id: "your_chat_id"
  alerts: ["trades", "risks", "daily_summary", "errors"]
```

**Configuration loading:**

1. Read `config.yaml` on startup
2. Validate all fields
3. No environment variable overrides (YAML is truth)
4. Changes require restart (no hot-reload to avoid mid-session changes)

---

## File Structure: Clean & Organized

```
trading_system/
├── config.yaml                 # SINGLE source of truth
├── .env                        # API keys only (not checked into git)
├── main.py                     # Startup script (50 lines max)
├── requirements.txt            # Dependencies
│
├── core/                       # Core infrastructure (stable, rarely changes)
│   ├── __init__.py
│   ├── broker_api.py           # OANDA client
│   ├── market_data.py          # Price feed
│   ├── risk_manager.py         # Risk checks
│   └── order_executor.py       # Trade execution
│
├── strategies/                 # Trading strategies (hot-swappable)
│   ├── __init__.py
│   ├── base_strategy.py        # Base class
│   ├── gold_scalping.py        # 200 lines
│   ├── gold_momentum.py        # 200 lines
│   ├── gbp_usd_momentum.py     # 200 lines
│   ├── eur_usd_mean_reversion.py
│   ├── jpy_pairs_breakout.py
│   ├── commodity_fx.py
│   ├── news_momentum.py
│   ├── session_scalper.py
│   └── swing_trader.py
│
├── intelligence/               # External data (news, sentiment)
│   ├── __init__.py
│   ├── news_aggregator.py      # Fetch news
│   ├── sentiment_analyzer.py   # Analyze sentiment
│   └── market_regime.py        # Detect trending/ranging
│
├── orchestrator/               # System coordination
│   ├── __init__.py
│   ├── strategy_coordinator.py # Run strategies
│   └── position_manager.py     # Manage positions
│
├── database/                   # Data persistence
│   ├── __init__.py
│   ├── trade_logger.py         # Log trades
│   └── backtest_engine.py      # Backtest strategies
│
├── monitoring/                 # Alerts & dashboard
│   ├── __init__.py
│   ├── telegram_alerts.py      # Telegram bot
│   └── dashboard_api.py        # Web dashboard API
│
├── dashboard/                  # Full web dashboard (connected to monitoring)
│   ├── __init__.py
│   ├── app.py                  # Flask/FastAPI server
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css   # Modern, responsive styling
│   │   └── js/
│   │       └── dashboard.js    # Real-time updates via WebSocket
│   └── templates/
│       ├── index.html          # Main dashboard
│       ├── strategies.html     # Strategy control panel
│       ├── positions.html      # Live positions view
│       ├── performance.html    # P&L charts and analytics
│       └── settings.html       # System configuration
│
├── tests/                      # Unit tests
│   ├── test_risk_manager.py
│   ├── test_strategies.py
│   └── test_news.py
│
└── data/                       # Local data storage
    ├── trades.db               # SQLite database
    ├── news_events.db
    └── backtest_results/
```

**Total: ~2,500 lines of code** (vs current 20,000+)

---

## Development Workflow: Local First

### Phase 1: Build Core (Week 1)

1. Set up project structure
2. Implement `core/broker_api.py` - Test connection to OANDA
3. Implement `core/market_data.py` - Verify price streaming
4. Implement `core/risk_manager.py` - Test all risk checks
5. Implement `core/order_executor.py` - Test order placement (practice account)

**Validation:** Place 1 test trade manually, verify all components work

---

### Phase 2: Build Strategies (Week 2)

1. Implement `strategies/base_strategy.py` - Base class
2. Implement ONE gold strategy (`gold_momentum.py`)
3. Run backtest on 2 weeks of historical data
4. Tune parameters until 60%+ win rate
5. Run live for 2 days (small position sizes)
6. If profitable, implement 2 more gold strategies

**Validation:** 3 profitable days in a row with real money

---

### Phase 3: Scale Up (Week 3)

1. Add forex strategies (one at a time)
2. Backtest each before enabling
3. Run multiple strategies simultaneously
4. Monitor for conflicts/correlation
5. Implement `intelligence/news_aggregator.py`
6. Integrate news sentiment into strategies

**Validation:** 10 strategies running, all profitable, no conflicts

---

### Phase 4: Cloud Migration (Week 4)

1. Package system as Docker container
2. Deploy to Google Cloud Run
3. Use Cloud SQL for database
4. Secret Manager for API keys
5. Cloud Scheduler for health checks
6. Test cloud deployment thoroughly

**Validation:** Cloud system matches local system performance

---

## Key Lessons Applied

### 1. **Trend Alignment - ALWAYS trade WITH trend**

```python
# In every strategy:
def check_trend(prices):
    sma_50 = prices[-50:].mean()
    sma_200 = prices[-200:].mean()
    current = prices[-1]
    
    if current > sma_50 > sma_200:
        return "UPTREND"  # ONLY allow BUY
    elif current < sma_50 < sma_200:
        return "DOWNTREND"  # ONLY allow SELL
    else:
        return "NO_TRADE"  # Don't trade choppy markets
```

### 2. **Concentration Limits - Never overexpose**

```python
# In risk_manager.py:
MAX_POSITIONS_PER_INSTRUMENT = 3
MAX_EXPOSURE_PER_INSTRUMENT_PCT = 30  # 30% of account
```

### 3. **Circuit Breaker - Stop when losing**

```python
# In position_manager.py:
def check_daily_loss():
    daily_pl_pct = (current_balance - start_of_day_balance) / start_of_day_balance
    if daily_pl_pct < -0.02:  # Lost 2%
        STOP_ALL_TRADING()
        send_telegram_alert("🔴 CIRCUIT BREAKER: Lost 2% today. All trading stopped.")
```

### 4. **Quality Over Quantity - Fewer, better trades**

- Max 10-15 trades per strategy per day
- Require 70%+ signal confidence
- Wait for pullbacks (don't chase)

### 5. **Fault Isolation - One failure doesn't kill system**

- Each strategy in separate file
- Each account independent
- Dashboard separate from trading
- If news feed fails, strategies still run (with reduced confidence)

---

## Success Metrics

### Week 1 (Local Development)

- ✅ All core components working
- ✅ Can place test trades
- ✅ Risk manager blocks bad trades
- ✅ Market data streaming reliably

### Week 2 (Strategy Development)

- ✅ 3 strategies backtested at 60%+ win rate
- ✅ 3 profitable days live trading
- ✅ No system crashes
- ✅ All trades logged to database

### Week 3 (Scaling)

- ✅ 10 strategies running simultaneously
- ✅ Overall win rate 58%+
- ✅ No concentration violations
- ✅ Circuit breaker tested and working
- ✅ News integration functional

### Week 4 (Cloud Deployment)

- ✅ Cloud system deployed
- ✅ Cloud matches local performance
- ✅ Dashboard accessible
- ✅ Telegram alerts working
- ✅ Ready for production capital

---

## Risk Mitigation

### What if strategy loses money?

- **Action:** Disable that strategy (one line in config.yaml)
- **Impact:** Other 9 strategies continue
- **Recovery:** Backtest strategy on recent data, fix, re-enable

### What if OANDA API goes down?

- **Action:** System pauses, doesn't crash
- **Impact:** No new trades, existing positions safe
- **Recovery:** Retries every 60 seconds, resumes when API returns

### What if news feed fails?

- **Action:** Strategies continue with reduced confidence
- **Impact:** Fewer trades, smaller sizes, but system operational
- **Recovery:** Alert sent, manual fix

### What if you need to change a strategy?

- **Action:** Edit one strategy file, restart system
- **Impact:** Only that strategy affected
- **Testing:** Backtest changes before deploying

---

## Why This Will Work

1. **Modularity:** Each component independent, replaceable, testable
2. **Clarity:** Every file has one job, easy to understand
3. **Safety:** Risk manager blocks all bad trades before execution
4. **Visibility:** Telegram alerts for everything important
5. **Fault tolerance:** One component fails, others continue
6. **Local testing:** Perfect locally before touching cloud
7. **Proven strategies:** Only deploy after backtest validation
8. **Simple configuration:** One YAML file, no conflicts
9. **Clean slate:** No legacy code, no accumulated bugs
10. **Lessons learned:** All past failures addressed in design

This system will be **10x simpler**, **10x more reliable**, and **100x easier to maintain** than the current one.

### To-dos

- [ ] Create new project structure with clean directory layout and initialize git repository
- [ ] Implement core/broker_api.py - OANDA client with connection management, rate limiting, and error handling
- [ ] Implement core/market_data.py - Real-time price streaming with 200-candle history buffers
- [ ] Implement core/risk_manager.py - All pre-trade risk checks including circuit breaker, concentration limits, and correlation checks
- [ ] Implement core/order_executor.py - Order execution with SL/TP, confirmation, and logging
- [ ] Test all core components together - place 1 manual test trade and verify end-to-end flow
- [ ] Implement strategies/base_strategy.py - Base class with standard interface for all strategies
- [ ] Implement strategies/gold_momentum.py - First production strategy with proper trend alignment
- [ ] Implement database/backtest_engine.py - Historical backtesting with 2-week validation
- [ ] Backtest gold_momentum strategy on 2 weeks of data, tune parameters for 60%+ win rate
- [ ] Implement intelligence/news_aggregator.py - Fetch economic news from Alpha Vantage and Marketaux
- [ ] Implement intelligence/sentiment_analyzer.py - Analyze news sentiment and integrate with strategies
- [ ] Implement remaining 9 strategies (gold_scalping, gbp_usd_momentum, etc.) with backtesting validation
- [ ] Implement orchestrator/strategy_coordinator.py - Run all strategies in parallel and collect signals
- [ ] Implement orchestrator/position_manager.py - Manage positions, break-even stops, trailing stops
- [ ] Implement monitoring/telegram_alerts.py - Real-time notifications for trades, risks, and daily summaries
- [ ] Implement database/trade_logger.py - SQLite logging for all trades, signals, and account snapshots
- [ ] Run complete system locally with small position sizes for 3 profitable days
- [ ] Package system as Docker container with all dependencies
- [ ] Deploy to Google Cloud Run with Cloud SQL, Secret Manager, and health checks