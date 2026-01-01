# COMPLETE TRADING SYSTEM BREAKDOWN
**System:** AI-Powered Multi-Account Trading System  
**Deployment:** Google Cloud Platform (GCP)  
**Last Updated:** January 2025

---

## 📋 EXECUTIVE SUMMARY

This is a fully automated, multi-account paper trading system that:
- Manages **7+ separate OANDA demo accounts** simultaneously
- Executes **different trading strategies** per account
- Uses **live market data** from OANDA API
- Applies **risk management** with position sizing, stop-loss, and take-profit
- Integrates **news sentiment analysis** to halt trading during high-impact events
- Provides **Telegram bot interface** for monitoring and control
- Runs **24/7 on Google Cloud** with adaptive parameter learning

**Key Design Principle:** Each strategy account operates **completely independently** - no aggregation, no cross-contamination. Each strategy is evaluated on its own merits with isolated performance metrics.

---

## 🏗️ SYSTEM ARCHITECTURE

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM STARTUP                            │
│  1. Load accounts.yaml (account → strategy mapping)         │
│  2. Load strategy registry (strategy key → Python class)   │
│  3. Initialize AITradingSystem instance per account         │
│  4. Start Telegram command processor (thread)              │
│  5. Start adaptive learning loop (thread)                   │
│  6. Start top-down analysis scheduler (thread)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MAIN TRADING LOOP (Every 60 seconds)          │
│                                                              │
│  For each active account:                                   │
│    ├─ Apply news halts (check upcoming events)             │
│    ├─ Apply sentiment throttle (check market sentiment)    │
│    ├─ Get current prices (OANDA API)                        │
│    ├─ Generate trading signals (strategy-specific logic)   │
│    ├─ Execute trades (with risk checks)                    │
│    ├─ Monitor existing positions (partial scaling)         │
│    └─ Enforce position caps (cancel excess orders)          │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
ai_trading_system.py (Main Engine)
├── AITradingSystem (per account)
│   ├── Strategy (loaded from registry)
│   ├── NewsManager (sentiment/events)
│   ├── TradeDatabase (blotter logging)
│   └── AdaptiveStore (parameter learning)
│
├── Strategy Registry
│   └── Maps strategy keys → Python classes
│
├── Configuration System
│   ├── accounts.yaml (account → strategy mapping)
│   ├── LIVE_TRADING_CONFIG_UNIFIED.yaml (global settings)
│   └── Strategy YAML configs (per-strategy params)
│
└── External Services
    ├── OANDA API (market data + execution)
    ├── Telegram Bot (alerts + commands)
    └── Marketaux API (news sentiment)
```

---

## 📥 INPUTS & CONFIGURATION

### 1. Account Configuration (`accounts.yaml`)

**Location:** `/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml`

**Structure:**
```yaml
accounts:
  account_name:
    account_id: "101-004-30719775-XXX"  # OANDA account ID
    name: "Display Name"
    strategy: "strategy_key"            # Links to registry
    trading_pairs: ["EUR_USD", "XAU_USD"]
    risk_settings:
      max_risk_per_trade: 0.012         # 1.2% of balance
      max_daily_risk: 0.03              # 3% daily cap
      max_positions: 1                  # Concurrent positions
      max_daily_trades: 30              # Daily trade limit
      position_size_multiplier: 1.0     # Optional multiplier
      enable_partial_scaling: true      # Enable 0.8R/1R/1.5R exits
    active: true                         # Enable/disable account
```

**Key Inputs:**
- **Account ID:** OANDA demo account identifier
- **Strategy Key:** Must exist in strategy registry
- **Risk Settings:** Per-account risk limits
- **Trading Pairs:** Instruments this account trades
- **Active Flag:** Whether account participates in trading

### 2. Strategy Registry (`registry.py`)

**Location:** `src/strategies/registry.py`

**Purpose:** Maps strategy keys to Python factory functions

**Example:**
```python
STRATEGY_REGISTRY = {
    "gold_scalping_winrate": StrategyDefinition(
        key="gold_scalping_winrate",
        display_name="Gold Scalper (Winrate)",
        factory=get_gold_scalping_winrate_strategy,
        description="Gold scalper optimized for maximum win rate"
    )
}
```

**Key Inputs:**
- **Strategy Key:** Unique identifier (matches `accounts.yaml`)
- **Factory Function:** Python function that returns strategy instance
- **Display Name:** Human-readable name

### 3. Strategy Configuration Files

**Location:** `AI_QUANT_credentials/strategy_configs/*.yaml`

**Example:** `trade_with_pat_orb_dual_session.yaml`

**Structure:**
```yaml
strategies:
  trade_with_pat_orb_dual:
    parameters:
      range_window_minutes: 15
      session_templates:
        london_open:
          window: "08:00-08:15"
          per_session_trade_cap: 2
        ny_open:
          window: "13:00-13:15"
          per_session_trade_cap: 2
      ema_filter:
        enabled: true
        period: 200
      momentum_filter:
        enabled: true
        ema_stack: [3, 8, 21]
```

**Key Inputs:**
- **Session Windows:** Time ranges for entry evaluation
- **Technical Indicators:** EMA periods, ATR periods, filters
- **Risk Overrides:** Strategy-specific risk adjustments

### 4. Environment Variables

**Key Variables:**
- `OANDA_API_KEY`: OANDA practice API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID
- `XAU_EMA_PERIOD`: Default EMA period for gold (default: 50)
- `XAU_ATR_PERIOD`: Default ATR period for gold (default: 14)
- `XAU_K_ATR`: ATR multiplier for gold bands (default: 1.5)
- `MIN_EXPECTED_R`: Minimum R-multiple for TP (default: 0.5)
- `MIN_ABS_PROFIT_USD`: Minimum absolute profit in USD (default: 0.5)

### 5. Market Data Inputs (Real-Time)

**Source:** OANDA REST API v3

**Data Retrieved:**
- **Current Prices:** Bid/Ask/Mid for all instruments
- **Candlestick Data:** Historical OHLC (M5, M15, H1, etc.)
- **Account Info:** Balance, unrealized P&L, margin
- **Open Positions:** Current positions and P&L
- **Open Trades:** Active trades with brackets

**Update Frequency:**
- Price data: Every 60 seconds (trading cycle)
- Candlestick data: On-demand for indicator calculation
- Account info: Every cycle for position sizing

---

## 🔄 HOW THE SYSTEM WORKS

### Phase 1: Initialization

1. **Load Configuration**
   - Read `accounts.yaml` to get all account definitions
   - Load strategy registry to map keys to classes
   - Initialize `YAMLManager` for config access

2. **Create Trading Systems**
   - For each active account in `accounts.yaml`:
     - Create `AITradingSystem` instance
     - Load strategy from registry using `strategy` key
     - Apply account-specific risk settings
     - Initialize `NewsManager` (if available)
     - Initialize `TradeDatabase` for blotter logging
     - Initialize `AdaptiveStore` for parameter learning

3. **Start Background Threads**
   - **Telegram Command Processor:** Listens for `/status`, `/stop_trading`, etc.
   - **Adaptive Learning Loop:** Adjusts parameters every 30 minutes
   - **Top-Down Analysis Scheduler:** Sends daily briefings (6 AM / 9:30 PM London)

### Phase 2: Trading Cycle (Every 60 Seconds)

For each active account, the system executes:

#### Step 1: Apply Safety Guards

**News Halts:**
```python
# Check for upcoming high-impact events (next 60 minutes)
upcoming_events = news_manager.get_upcoming_high_impact(within_minutes=60)
if upcoming_events:
    # Halt 15 minutes before until 30 minutes after
    news_halt_until = event_time + 30 minutes
```

**Sentiment Throttle:**
```python
# Fetch sentiment from Marketaux (last 10 minutes)
sentiment = news_manager.fetch_sentiment(window_minutes=10)
if sentiment['avg_score'] <= threshold and count >= 3:
    # Reduce risk to 50% and halt new entries for 15 minutes
    risk_per_trade = base_risk * 0.5
    throttle_until = now + 15 minutes
```

**Price Verification:**
```python
# Check if prices are fresh (< 30 seconds old)
if price_age > 30 seconds or status != 'tradeable':
    # Halt new entries for 5 minutes
    news_halt_until = now + 5 minutes
```

#### Step 2: Get Market Data

```python
# Fetch current prices for all instruments
prices = get_current_prices()
# Returns: {instrument: {bid, ask, mid, spread}}

# Fetch candlestick data for indicators
candles = fetch_candles(instrument, granularity='M5', count=200)
```

#### Step 3: Generate Trading Signals

**Strategy-Specific Logic:**

**Example: EMA/ATR Breakout Strategy**
```python
# Calculate indicators
ema = compute_ema(close_prices, period=50)
atr = compute_atr(high, low, close, period=14)
upper_band = ema + (k_atr * atr)  # k_atr typically 1.0-1.5
lower_band = ema - (k_atr * atr)

# Check breakout conditions
if price > upper_band and confirm_above >= 2 and slope_up:
    signal = {
        'instrument': instrument,
        'side': 'BUY',
        'entry_price': ask_price,
        'stop_loss': mid_price - (sl_mult * atr),
        'take_profit': mid_price + (tp_mult * atr),
        'confidence': 75
    }
```

**Example: Open Range Breakout Strategy**
```python
# Calculate range from session window (e.g., 08:00-08:15)
range_high = max(high_prices_in_window)
range_low = min(low_prices_in_window)
range_width = range_high - range_low

# Check if range is valid (5-35 pips)
if min_range <= range_width <= max_range:
    # Check breakout
    if current_price > range_high + buffer:
        signal = {
            'side': 'BUY',
            'stop_loss': range_low - buffer,
            'take_profit': entry + (range_width * 0.8)
        }
```

#### Step 4: Risk Checks (Before Execution)

**Daily Limits:**
```python
if daily_trade_count >= max_daily_trades:
    return False  # Skip trade
```

**Concurrent Position Limits:**
```python
live_counts = get_live_counts()  # positions + pending orders
if live_counts['positions'] + live_counts['pending'] >= max_concurrent_trades:
    return False  # Skip trade
```

**Per-Symbol Limits:**
```python
if live_counts['by_symbol'][instrument] >= max_per_symbol:
    return False  # Skip trade
```

**Diversification Guard:**
```python
# Reserve slots for diversification if low on capacity
if open_slots <= reserve_slots and distinct_symbols < 2:
    if current_symbol in existing_symbols:
        return False  # Skip trade
```

**Second Position Rule:**
```python
# Allow 2nd position only if existing position is >= 0.5R profit
if symbol_count >= 1:
    for existing_trade in active_trades:
        r_multiple = (current_price - entry) / stop_distance
        if r_multiple < 0.5:
            return False  # Skip trade
```

**Minimum Profit Checks:**
```python
# Require TP >= 0.5R * SL distance
if take_profit_distance < (0.5 * stop_loss_distance):
    return False  # Skip trade

# Require minimum absolute profit (e.g., $0.50)
expected_profit = units * take_profit_distance
if expected_profit < 0.50:
    return False  # Skip trade
```

#### Step 5: Calculate Position Size

**Formula:**
```python
# Risk amount = account_balance * risk_per_trade
risk_amount = balance * max_risk_per_trade  # e.g., $100,000 * 0.012 = $1,200

# Stop distance = |entry_price - stop_loss|
stop_distance = abs(entry_price - stop_loss)

# Units = risk_amount / stop_distance
units = int(risk_amount / stop_distance)

# Apply position size multiplier (if configured)
if position_size_multiplier > 1.0:
    units = int(units * position_size_multiplier)

# Cap at instrument maximum
units = min(units, max_units_per_instrument[instrument])
```

**Example Calculation:**
```
Account Balance: $100,000
Risk Per Trade: 1.2% = $1,200
Entry Price: 1.2500 (GBP_USD)
Stop Loss: 1.2480 (20 pips = 0.0020)
Stop Distance: 0.0020

Units = $1,200 / 0.0020 = 600,000 units (6 standard lots)

With 5x multiplier: 600,000 * 5 = 3,000,000 units (30 lots)
```

#### Step 6: Execute Trade

**Order Creation:**
```python
order_data = {
    "order": {
        "type": "MARKET",  # or "LIMIT"
        "instrument": instrument,
        "units": str(units),  # Negative for SELL
        "timeInForce": "FOK",  # Fill or Kill
        "stopLossOnFill": {"price": str(stop_loss)},
        "takeProfitOnFill": {"price": str(take_profit)}
    }
}

response = requests.post(
    f"{OANDA_BASE_URL}/v3/accounts/{account_id}/orders",
    headers=headers,
    json=order_data
)
```

**Post-Execution:**
- Track trade in `active_trades` dictionary
- Increment `daily_trade_count`
- Send Telegram alert
- Log to `TradeDatabase` (blotter)
- Verify brackets attached (retry if missing)

#### Step 7: Monitor Existing Positions

**Partial Scaling Logic:**

```python
for position in open_positions:
    entry = position['entry_price']
    stop = position['stop_loss']
    current = current_price
    
    # Calculate R-multiple
    r_distance = abs(entry - stop)
    r_multiple = (current - entry) / r_distance  # For BUY
    
    # 0.8R: Close 25% of position
    if r_multiple >= 0.8 and not tp25_done:
        close_units = int(position_units * 0.25)
        close_position(instrument, close_units)
        tp25_done = True
    
    # 1.0R: Close 50% of remaining
    if r_multiple >= 1.0 and not tp50_done:
        close_units = int(remaining_units * 0.50)
        close_position(instrument, close_units)
        tp50_done = True
    
    # 1.5R: Close all remaining
    if r_multiple >= 1.5 and not full_exit_done:
        close_position(instrument, "ALL")
        full_exit_done = True
```

**Bracket Verification:**
```python
# Check if live trades have SL/TP brackets
for trade in list_open_trades():
    if not trade_has_brackets(trade):
        # Attach brackets server-side
        attach_brackets(trade_id, instrument, side, entry_price)
```

#### Step 8: Enforce Position Caps

```python
# Cancel excess pending orders if over cap
live_counts = get_live_counts()
if live_counts['positions'] + live_counts['pending'] > max_concurrent_trades:
    excess = total - max_concurrent_trades
    # Cancel oldest entry orders (LIMIT/STOP only)
    cancel_oldest_pending_orders(count=excess)
```

---

## 🧮 CALCULATION DETAILS

### 1. EMA (Exponential Moving Average)

**Formula:**
```python
k = 2 / (period + 1)  # Smoothing factor
ema = first_value
for value in remaining_values:
    ema = (value * k) + (ema * (1 - k))
```

**Default Periods:**
- XAU_USD: 50 (configurable via `XAU_EMA_PERIOD`)
- Forex pairs: 50 (configurable via `EMA_PERIOD_DEFAULT`)
- Strategy-specific: Varies (e.g., 200 for trend filter)

### 2. ATR (Average True Range)

**True Range Calculation:**
```python
tr1 = high - low
tr2 = abs(high - prev_close)
tr3 = abs(low - prev_close)
true_range = max(tr1, tr2, tr3)
```

**ATR Calculation (Wilder's Smoothing):**
```python
# Initial ATR = average of first N periods
atr = sum(true_ranges[:period]) / period

# Subsequent: ATR = ((ATR_prev * (N-1)) + TR_current) / N
for tr in true_ranges[period:]:
    atr = ((atr * (period - 1)) + tr) / period
```

**Default Periods:**
- XAU_USD: 14 (configurable via `XAU_ATR_PERIOD`)
- Forex pairs: 14 (configurable via `ATR_PERIOD_DEFAULT`)

### 3. Position Sizing

**Base Calculation:**
```python
risk_amount = account_balance * risk_per_trade
stop_distance = abs(entry_price - stop_loss)
units = int(risk_amount / stop_distance)
```

**Adjustments:**
- **Position Multiplier:** `units *= position_size_multiplier`
- **Instrument Caps:** `units = min(units, max_units_per_instrument[instrument])`
- **Volatility Reduction:** For XAU during high volatility, `units *= 0.5`
- **Chase Prevention:** For XAU after >0.6% jump, `units *= 0.5`

**Instrument Maximums:**
- EUR_USD, GBP_USD, AUD_USD: 200,000 units (2 lots)
- USD_JPY: 400,000 units (4 lots)
- XAU_USD: 2,000 units (2 lots)

### 4. Stop Loss / Take Profit Calculation

**ATR-Based (Default):**
```python
sl_mult = adaptive_store.get('sl_mult', 0.5)  # Default 0.5
tp_mult = adaptive_store.get('tp_mult', 1.0)  # Default 1.0

stop_loss = entry_price - (sl_mult * atr)  # For BUY
take_profit = entry_price + (tp_mult * atr)  # For BUY
```

**Range-Based (ORB Strategy):**
```python
range_width = range_high - range_low
tp_multiple = 0.8  # 80% of range width
take_profit = entry_price + (range_width * tp_multiple)
stop_loss = range_low - buffer  # For BUY breakout
```

**Spread-Aware TP Boost:**
```python
# If spread is tight (<= 25% of ATR), boost TP
if spread <= (0.25 * atr):
    tp_mult = max(tp_mult, 1.5)  # Boost to 1.5x ATR
```

### 5. R-Multiple Calculation

**For Open Positions:**
```python
# For BUY position
r_distance = entry_price - stop_loss
current_r = (current_price - entry_price) / r_distance

# For SELL position
r_distance = stop_loss - entry_price
current_r = (entry_price - current_price) / r_distance
```

**R-Multiple Thresholds:**
- **0.5R:** Minimum for allowing 2nd position in same symbol
- **0.8R:** Close 25% of position (partial profit)
- **1.0R:** Close 50% of remaining position
- **1.5R:** Close all remaining position (full exit)

### 6. Adaptive Parameter Learning

**Update Frequency:** Every 30 minutes

**Performance Scoring:**
```python
# Look back 6 hours
recent_events = performance_events[last_6_hours]

# Score events
score = 0.0
for event in recent_events:
    if event == 'tp25': score += 0.25
    elif event == 'tp50': score += 0.50
    elif event == 'full_exit': score += 1.00

avg_r = score / len(events)
```

**Parameter Adjustments:**
```python
if avg_r > 0.35:  # Good performance
    k_atr = max(0.9, k_atr - 0.05)  # Tighten bands (more selective)
    tp_mult = min(2.0, tp_mult + 0.1)  # Increase TP (let winners run)

elif avg_r < 0.1:  # Poor performance
    k_atr = min(2.0, k_atr + 0.1)  # Widen bands (less selective)
    tp_mult = max(0.8, tp_mult - 0.1)  # Reduce TP (take profits faster)
```

---

## 📊 DATA FLOW

### Input Data Sources

1. **OANDA API**
   - Real-time prices (bid/ask/mid)
   - Historical candlesticks (OHLC)
   - Account information (balance, margin)
   - Open positions and trades

2. **Marketaux API** (via NewsManager)
   - News articles with sentiment scores
   - Economic calendar events
   - Entity extraction (USD, EUR, GBP, etc.)

3. **Configuration Files**
   - `accounts.yaml`: Account definitions
   - Strategy YAML files: Strategy parameters
   - Environment variables: System settings

### Processing Pipeline

```
Market Data → Indicators → Signal Generation → Risk Checks → Position Sizing → Execution
     ↓              ↓              ↓                ↓              ↓              ↓
  Prices      EMA/ATR      Breakout/ORB      Daily/Position    Units Calc    OANDA Order
  Candles     Bands        Filters          Caps              Multipliers   Brackets
```

### Output Data

1. **Trade Execution**
   - OANDA order creation
   - Telegram alerts
   - Blotter logging (TradeDatabase)

2. **Monitoring**
   - Position updates
   - Partial scaling events
   - Performance metrics

3. **Adaptive Learning**
   - Parameter adjustments
   - Performance events log

---

## 🎯 STRATEGY TYPES

### 1. EMA/ATR Breakout Strategy

**Logic:**
- Calculate EMA(50) and ATR(14)
- Create bands: `EMA ± (k * ATR)`
- Enter when price breaks above/below band with confirmation
- Require 2+ confirmations (price above/below band in last 3 candles)
- Check M15 EMA alignment for trend confirmation

**Instruments:** EUR_USD, GBP_USD, USD_JPY, AUD_USD, XAU_USD

**Special Rules:**
- XAU_USD: Only trade during London session (8 AM - 5 PM UTC)
- XAU_USD: Halt on volatility spikes (>1.5x recent ATR)
- Forex pairs: Minimum k_atr = 1.25 for EUR/GBP/AUD

### 2. Open Range Breakout (ORB) Strategy

**Logic:**
- Calculate range from session window (e.g., 08:00-08:15 London)
- Range must be 5-35 pips wide
- Enter on breakout above/below range with buffer
- Apply EMA(200) trend filter
- Apply momentum filter (EMA stack: 3, 8, 21)

**Sessions:**
- London Open: 08:00-08:15 London time
- NY Open: 13:00-13:15 London time (08:00-08:15 ET)

**Instruments:** GBP_USD, EUR_USD, XAU_USD, SPX500_USD, NAS100_USD

### 3. Gold Scalping Strategy

**Variants:**
- `gold_scalping_winrate`: Optimized for maximum win rate
- `gold_scalping_strict1`: Stricter entry filters
- `gold_scalping_topdown`: Includes top-down analysis

**Common Features:**
- XAU_USD only
- London session only
- Stricter spread limits outside overlap
- Anti-chasing logic (skip after >0.6% jumps)

---

## 🛡️ RISK MANAGEMENT

### Per-Trade Risk

**Calculation:**
```
Risk Amount = Account Balance × Risk Per Trade
```

**Default:** 0.5% - 2.0% per trade (configurable per account)

### Daily Risk Limits

**Caps:**
- `max_daily_trades`: Maximum trades per day (e.g., 30)
- `max_daily_risk`: Maximum cumulative risk per day (e.g., 3%)

**Reset:** UTC midnight

### Position Limits

**Concurrent Positions:**
- `max_positions`: Maximum concurrent positions per account (e.g., 1-3)
- `max_per_symbol`: Maximum positions per instrument (typically 1)

**Global Cap:** System-wide maximum (from global config)

### Diversification

**Rules:**
- Reserve slots for diversification when capacity is low
- Prefer different instruments over multiple positions in same symbol
- Allow 2nd position only if existing position is >= 0.5R profit

### Spread Limits

**Per-Instrument:**
- EUR_USD: 0.00025 (2.5 pips)
- GBP_USD: 0.00030 (3 pips)
- USD_JPY: 0.025 (2.5 pips)
- XAU_USD: 1.00 (outside overlap), 0.60 (during overlap)

**Action:** Skip trade if spread exceeds limit

### News-Based Halts

**High-Impact Events:**
- Halt 15 minutes before event
- Resume 30 minutes after event
- Applied automatically based on economic calendar

**Sentiment Throttle:**
- If sentiment score <= threshold (default: -0.4)
- And count >= 3 articles (corroboration)
- Reduce risk to 50% and halt new entries for 15 minutes

---

## 📱 TELEGRAM INTERFACE

### Commands

**Status & Info:**
- `/status` - System status (all accounts)
- `/balance` - Account balance
- `/positions` - Open positions
- `/trades` - Recent trades
- `/performance` - Performance summary
- `/market` - Market analysis

**Trading Control:**
- `/start_trading` - Enable trading
- `/stop_trading` - Disable trading
- `/emergency_stop` - Emergency stop all trading

**Risk Management:**
- `/risk 0.01` - Set risk per trade (1%)

**News & Analysis:**
- `/news` or `/brief` - News summary with sentiment
- `/news_mode off|lite|normal|strict` - Set news filtering mode
- `/sentiment_threshold -0.40` - Set sentiment threshold
- `/halt 30` - Halt new entries for 30 minutes

### Automated Alerts

**Trade Execution:**
- Entry alerts with instrument, side, units, prices
- Partial scaling alerts (0.8R, 1R, 1.5R)
- Full exit alerts

**System Status:**
- Startup notification
- Daily status updates (when trades executed)
- Marketaux API alerts (rate limits, errors)

**Scheduled Briefings:**
- Morning briefing: 6:00 AM London time
- End-of-day summary: 9:30 PM London time

---

## 🔧 ADAPTIVE LEARNING

### Parameter Store

**Stored Parameters (per instrument):**
- `ema`: EMA period
- `atr`: ATR period
- `k_atr`: ATR multiplier for bands
- `sl_mult`: Stop loss multiplier
- `tp_mult`: Take profit multiplier

### Learning Algorithm

**Update Cycle:** Every 30 minutes

**Performance Window:** Last 6 hours

**Scoring:**
- `tp25` event: +0.25R
- `tp50` event: +0.50R
- `full_exit` event: +1.00R

**Adjustments:**
- If avg_r > 0.35: Tighten bands, increase TP
- If avg_r < 0.1: Widen bands, decrease TP
- Bounded adjustments (±0.05 to ±0.1 per cycle)

**Notification:** Telegram alert when parameters change

---

## 📈 PERFORMANCE TRACKING

### Trade Database

**Stored Events:**
- `TRADE_OPEN`: Trade entry
- `TRADE_CLOSE`: Trade exit
- `PARTIAL_CLOSE`: Partial scaling event

**Metadata:**
- Account ID
- Strategy name
- Instrument, side, units
- Entry/exit prices
- Stop loss, take profit
- Order ID

### Blotter Files

**Location:** `backtest_blotter_sync/`

**Files:**
- `live_trade_blotter.json`: JSON format
- `live_trade_blotter_trades.csv`: CSV format
- `all_accounts_blotter.json`: Combined view

**Sync:** Blotter syncs to backtesting system for analysis

---

## 🌐 DEPLOYMENT

### Google Cloud Platform

**VM Instance:**
- Name: `ai-quant-trading-vm`
- Zone: `us-central1-a`
- External IP: `35.226.221.66`

**Service:**
- `ai_trading.service` (systemd)
- Auto-starts on boot
- Runs `ai_trading_system.py` as main process

**Working Directory:**
- `/opt/quant_system_clean`

### Configuration Location

**On GCP:**
- `/opt/quant_system_clean/google-cloud-trading-system/`

**Local Development:**
- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/`

---

## 🔍 KEY DESIGN DECISIONS

### 1. Multi-Account Isolation

**Why:** Each strategy needs independent evaluation
- No cross-contamination of performance
- Independent risk settings per account
- Easy to compare strategy performance

### 2. Strategy Registry Pattern

**Why:** Decouple configuration from implementation
- Change strategy without code changes
- Easy to add new strategies
- Centralized strategy management

### 3. Adaptive Parameter Learning

**Why:** Markets change, parameters should adapt
- Online learning from recent performance
- Bounded adjustments prevent overfitting
- Per-instrument customization

### 4. News Integration

**Why:** High-impact events cause volatility spikes
- Automatic halts prevent bad entries
- Sentiment analysis provides market context
- Reduces drawdowns during news events

### 5. Partial Scaling

**Why:** Lock in profits while letting winners run
- 0.8R: Lock 25% (breakeven+)
- 1.0R: Lock 50% (1R profit)
- 1.5R: Close all (let remaining run to TP)

---

## 📝 SUMMARY

### What It Does
- Automated paper trading on 7+ OANDA demo accounts
- Multiple strategies running simultaneously
- Real-time risk management and position sizing
- News-based trading halts
- Telegram monitoring and control

### How It Works
- 60-second trading cycles
- Strategy-specific signal generation
- Multi-layer risk checks before execution
- Adaptive parameter learning
- Partial profit scaling

### Key Inputs
- Account configuration (YAML)
- Strategy registry (Python)
- Market data (OANDA API)
- News data (Marketaux API)
- Environment variables

### Key Calculations
- Position size: `risk_amount / stop_distance`
- Indicators: EMA, ATR (Wilder's smoothing)
- R-multiple: `(price - entry) / stop_distance`
- Adaptive learning: Performance-based parameter adjustment

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**System Version:** GCloud Trading System v2.0






