# 🎯 UPDATED STRATEGY CONFIGURATIONS - ULTRA CONSERVATIVE V2

## 📋 **CONFIGURATION FILE UPDATES - ULTRA CONSERVATIVE**

### **1. oanda_config.env Updates - ULTRA LOW LIMITS**

```bash
# ===============================================
# OVERTRADING FIX - ULTRA CONSERVATIVE LIMITS
# MAXIMUM 10 TRADES PER DAY TOTAL
# ===============================================

# Risk Management Settings - Primary Account (Ultra Strict Forex)
PRIMARY_MAX_RISK_PER_TRADE=0.02
PRIMARY_MAX_PORTFOLIO_RISK=0.75
PRIMARY_MAX_POSITIONS=5
PRIMARY_DAILY_TRADE_LIMIT=3   # ULTRA CONSERVATIVE: Max 3/day (was 50)

# Risk Management Settings - Gold Scalping Account
GOLD_MAX_RISK_PER_TRADE=0.015
GOLD_MAX_PORTFOLIO_RISK=0.75
GOLD_MAX_POSITIONS=3
GOLD_DAILY_TRADE_LIMIT=4      # ULTRA CONSERVATIVE: Max 4/day (was 100)

# Risk Management Settings - Strategy Alpha Account (Momentum)
ALPHA_MAX_RISK_PER_TRADE=0.025
ALPHA_MAX_PORTFOLIO_RISK=0.75
ALPHA_MAX_POSITIONS=7
ALPHA_DAILY_TRADE_LIMIT=3     # ULTRA CONSERVATIVE: Max 3/day (was 30)

# ===============================================
# ULTRA CONSERVATIVE EARLY CLOSURE SETTINGS
# ===============================================
EARLY_CLOSE_PROFIT_PCT=0.001    # Close at +0.1% profit
EARLY_CLOSE_LOSS_PCT=-0.002     # Close at -0.2% loss
MAX_HOLD_TIME_MINUTES=30        # Max 30 minutes hold (ULTRA QUICK)
TRAILING_STOP_ENABLED=true      # Enable trailing stops
TRAILING_STOP_DISTANCE=0.0005   # 0.05% trailing distance (ULTRA TIGHT)

# ===============================================
# ULTRA CONSERVATIVE QUALITY FILTER SETTINGS
# ===============================================
MAX_DAILY_QUALITY_TRADES=1      # Only TOP 1 per strategy per day
MIN_SIGNAL_STRENGTH=0.90        # ULTRA HIGH - only perfect setups
QUALITY_SCORE_THRESHOLD=0.95    # ULTRA HIGH - only flawless setups
DAILY_TRADE_RANKING=true        # Rank and select ONLY the best
ULTRA_SELECTIVE_MODE=true       # Ultra selective trading mode

# ===============================================
# ULTRA CONSERVATIVE SESSION SETTINGS
# ===============================================
ONLY_TRADE_LONDON_NY_OVERLAP=true  # Only 13:00-16:00 UTC overlap
LONDON_NY_OVERLAP_START=13         # 13:00 UTC
LONDON_NY_OVERLAP_END=16           # 16:00 UTC
MIN_VOLATILITY_THRESHOLD=0.0001    # Ultra high volatility required
MAX_SPREAD_THRESHOLD=0.5           # Ultra tight spreads only
```

### **2. app.yaml Updates - ULTRA LOW LIMITS**

```yaml
# ===============================================
# OVERTRADING FIX - ULTRA CONSERVATIVE LIMITS
# MAXIMUM 10 TRADES PER DAY TOTAL
# ===============================================

# Risk Management Settings - Primary Account (Ultra Strict Forex)
PRIMARY_MAX_RISK_PER_TRADE: "0.02"
PRIMARY_MAX_PORTFOLIO_RISK: "0.75"
PRIMARY_MAX_POSITIONS: "5"
PRIMARY_DAILY_TRADE_LIMIT: "3"     # ULTRA CONSERVATIVE: Max 3/day

# Risk Management Settings - Gold Scalping Account
GOLD_MAX_RISK_PER_TRADE: "0.015"
GOLD_MAX_PORTFOLIO_RISK: "0.75"
GOLD_MAX_POSITIONS: "3"
GOLD_DAILY_TRADE_LIMIT: "4"        # ULTRA CONSERVATIVE: Max 4/day

# Risk Management Settings - Strategy Alpha Account (Momentum)
ALPHA_MAX_RISK_PER_TRADE: "0.025"
ALPHA_MAX_PORTFOLIO_RISK: "0.75"
ALPHA_MAX_POSITIONS: "7"
ALPHA_DAILY_TRADE_LIMIT: "3"       # ULTRA CONSERVATIVE: Max 3/day

# ===============================================
# ULTRA CONSERVATIVE EARLY CLOSURE SETTINGS
# ===============================================
EARLY_CLOSE_PROFIT_PCT: "0.001"
EARLY_CLOSE_LOSS_PCT: "-0.002"
MAX_HOLD_TIME_MINUTES: "30"        # ULTRA QUICK: 30 minutes max
TRAILING_STOP_ENABLED: "true"
TRAILING_STOP_DISTANCE: "0.0005"   # ULTRA TIGHT: 0.05%

# ===============================================
# ULTRA CONSERVATIVE QUALITY FILTER SETTINGS
# ===============================================
MAX_DAILY_QUALITY_TRADES: "1"      # Only TOP 1 per strategy
MIN_SIGNAL_STRENGTH: "0.90"        # ULTRA HIGH
QUALITY_SCORE_THRESHOLD: "0.95"    # ULTRA HIGH
DAILY_TRADE_RANKING: "true"
ULTRA_SELECTIVE_MODE: "true"

# ===============================================
# ULTRA CONSERVATIVE SESSION SETTINGS
# ===============================================
ONLY_TRADE_LONDON_NY_OVERLAP: "true"
LONDON_NY_OVERLAP_START: "13"
LONDON_NY_OVERLAP_END: "16"
MIN_VOLATILITY_THRESHOLD: "0.0001"
MAX_SPREAD_THRESHOLD: "0.5"
```

---

## 🔧 **STRATEGY FILE UPDATES - ULTRA CONSERVATIVE**

### **3. Ultra Strict Forex Strategy Updates - MAX 3/DAY**

```python
class UltraStrictForexStrategy:
    def __init__(self):
        # ... existing code ...
        
        # ===============================================
        # ULTRA CONSERVATIVE LIMITS - MAX 3/DAY
        # ===============================================
        self.max_trades_per_day = 3    # ULTRA CONSERVATIVE: Max 3/day
        self.min_trades_today = 0      # NO FORCED TRADES EVER
        
        # ===============================================
        # ULTRA CONSERVATIVE R:R RATIOS
        # ===============================================
        self.stop_loss_pct = 0.003     # ULTRA TIGHT: 0.3% stop
        self.take_profit_pct = 0.015   # CONSERVATIVE: 1.5% target
        # New R:R = 1:5.0 (ULTRA CONSERVATIVE)
        
        # ===============================================
        # ULTRA HIGH SIGNAL QUALITY
        # ===============================================
        self.min_signal_strength = 0.90   # ULTRA HIGH: Only perfect setups
        self.max_daily_quality_trades = 1  # ULTRA SELECTIVE: Only TOP 1
        self.quality_score_threshold = 0.95  # ULTRA HIGH: Only flawless
        
        # ===============================================
        # ULTRA QUICK EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.001    # Close at +0.1% profit
        self.early_close_loss_pct = -0.002     # Close at -0.2% loss
        self.max_hold_time_minutes = 30        # ULTRA QUICK: 30 min max
        self.trailing_stop_enabled = True      # Enable trailing stops
        self.trailing_stop_distance = 0.0005   # ULTRA TIGHT: 0.05%
        
        # ===============================================
        # ULTRA SELECTIVE ENTRY FILTERS
        # ===============================================
        self.require_trend_alignment = True
        self.trend_timeframes = ['5M', '15M', '1H', '4H']  # ALL must align
        self.trend_strength_min = 0.8                      # Ultra strong trend
        self.only_trade_london_ny_overlap = True           # Only overlap period
        self.min_volatility_threshold = 0.0001             # Ultra high volatility
        self.max_spread_threshold = 0.5                    # Ultra tight spreads
        self.require_volume_confirmation = True            # Volume must confirm
        self.require_news_alignment = True                 # News must align
        
        # ===============================================
        # ULTRA SELECTIVE DAILY TRADE SYSTEM
        # ===============================================
        self.daily_trade_ranking = True
        self.ultra_selective_mode = True
        self.daily_signals = []  # Store all signals for ranking
        self.selected_trades = []  # Only TOP 1 trade selected
        
        # ... rest of existing code ...
    
    def _select_best_daily_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Select only the TOP 1 trade for the day"""
        if not self.daily_trade_ranking:
            return signals
        
        # Add to daily signals
        self.daily_signals.extend(signals)
        
        # Sort by confidence and strength (highest first)
        self.daily_signals.sort(key=lambda x: (x.confidence, x.strength), reverse=True)
        
        # Select ONLY the TOP 1 trade
        best_trades = self.daily_signals[:1]  # Only TOP 1
        
        logger.info(f"🎯 ULTRA SELECTIVE: Selected {len(best_trades)} trade from {len(self.daily_signals)} signals")
        
        return best_trades
```

### **4. Gold Scalping Strategy Updates - MAX 4/DAY**

```python
class GoldScalpingStrategy:
    def __init__(self):
        # ... existing code ...
        
        # ===============================================
        # ULTRA CONSERVATIVE LIMITS - MAX 4/DAY
        # ===============================================
        self.max_trades_per_day = 4    # ULTRA CONSERVATIVE: Max 4/day
        self.min_trades_today = 0      # NO FORCED TRADES EVER
        
        # ===============================================
        # ULTRA CONSERVATIVE R:R RATIOS
        # ===============================================
        self.stop_loss_pips = 5        # ULTRA TIGHT: 5 pips stop
        self.take_profit_pips = 20     # CONSERVATIVE: 20 pips target
        # New R:R = 1:4.0 (ULTRA CONSERVATIVE)
        
        # ===============================================
        # ULTRA HIGH SIGNAL QUALITY
        # ===============================================
        self.min_signal_strength = 0.90   # ULTRA HIGH: Only perfect setups
        self.max_daily_quality_trades = 1  # ULTRA SELECTIVE: Only TOP 1
        self.quality_score_threshold = 0.95  # ULTRA HIGH: Only flawless
        
        # ===============================================
        # ULTRA QUICK EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.001    # Close at +0.1% profit
        self.early_close_loss_pct = -0.002     # Close at -0.2% loss
        self.max_hold_time_minutes = 30        # ULTRA QUICK: 30 min max
        self.trailing_stop_enabled = True      # Enable trailing stops
        self.trailing_stop_distance = 0.0005   # ULTRA TIGHT: 0.05%
        
        # ===============================================
        # ULTRA SELECTIVE ENTRY FILTERS
        # ===============================================
        self.require_pullback = True           # Keep pullback requirement
        self.pullback_ema_period = 21          # Must pull back to 21 EMA
        self.only_trade_london_ny_overlap = True  # Only overlap period
        self.min_time_between_trades_minutes = 60  # Increased spacing
        self.min_volatility = 0.0001           # Ultra high volatility
        self.max_spread = 0.5                  # Ultra tight spreads
        self.min_atr_for_entry = 2.0           # Higher ATR required
        self.require_volume_confirmation = True  # Volume must confirm
        self.require_news_alignment = True     # News must align
        
        # ===============================================
        # ULTRA SELECTIVE DAILY TRADE SYSTEM
        # ===============================================
        self.daily_trade_ranking = True
        self.ultra_selective_mode = True
        self.daily_signals = []  # Store all signals for ranking
        self.selected_trades = []  # Only TOP 1 trade selected
        
        # ... rest of existing code ...
    
    def _select_best_daily_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Select only the TOP 1 trade for the day"""
        if not self.daily_trade_ranking:
            return signals
        
        # Add to daily signals
        self.daily_signals.extend(signals)
        
        # Sort by confidence and strength (highest first)
        self.daily_signals.sort(key=lambda x: (x.confidence, x.strength), reverse=True)
        
        # Select ONLY the TOP 1 trade
        best_trades = self.daily_signals[:1]  # Only TOP 1
        
        logger.info(f"🥇 ULTRA SELECTIVE: Selected {len(best_trades)} gold trade from {len(self.daily_signals)} signals")
        
        return best_trades
```

### **5. Momentum Trading Strategy Updates - MAX 3/DAY**

```python
class MomentumTradingStrategy:
    def __init__(self):
        # ... existing code ...
        
        # ===============================================
        # ULTRA CONSERVATIVE LIMITS - MAX 3/DAY
        # ===============================================
        self.max_trades_per_day = 3    # ULTRA CONSERVATIVE: Max 3/day
        self.min_trades_today = 0      # NO FORCED TRADES EVER
        
        # ===============================================
        # ULTRA CONSERVATIVE R:R RATIOS
        # ===============================================
        self.stop_loss_atr = 1.0       # ULTRA TIGHT: 1.0 ATR stop
        self.take_profit_atr = 5.0     # CONSERVATIVE: 5.0 ATR target
        # New R:R = 1:5.0 (ULTRA CONSERVATIVE)
        
        # ===============================================
        # ULTRA HIGH SIGNAL QUALITY
        # ===============================================
        self.min_adx = 30              # ULTRA HIGH: Only very strong trends
        self.min_momentum = 0.40       # ULTRA HIGH: Only strong momentum
        self.min_volume = 0.35         # ULTRA HIGH: Only high volume
        self.max_daily_quality_trades = 1  # ULTRA SELECTIVE: Only TOP 1
        self.quality_score_threshold = 0.95  # ULTRA HIGH: Only flawless
        
        # ===============================================
        # ULTRA QUICK EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.001    # Close at +0.1% profit
        self.early_close_loss_pct = -0.002     # Close at -0.2% loss
        self.max_hold_time_minutes = 30        # ULTRA QUICK: 30 min max
        self.trailing_stop_enabled = True      # Enable trailing stops
        self.trailing_stop_distance = 0.0005   # ULTRA TIGHT: 0.05%
        
        # ===============================================
        # ULTRA SELECTIVE ENTRY FILTERS
        # ===============================================
        self.require_trend_alignment = True
        self.trend_timeframes = ['5M', '15M', '1H', '4H']  # ALL must align
        self.trend_strength_min = 0.8                      # Ultra strong trend
        self.only_trade_london_ny_overlap = True           # Only overlap period
        self.min_volatility_threshold = 0.0001             # Ultra high volatility
        self.max_spread_threshold = 0.5                    # Ultra tight spreads
        self.require_volume_confirmation = True            # Volume must confirm
        self.require_news_alignment = True                 # News must align
        
        # ===============================================
        # ULTRA SELECTIVE DAILY TRADE SYSTEM
        # ===============================================
        self.daily_trade_ranking = True
        self.ultra_selective_mode = True
        self.daily_signals = []  # Store all signals for ranking
        self.selected_trades = []  # Only TOP 1 trade selected
        
        # ... rest of existing code ...
    
    def _select_best_daily_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Select only the TOP 1 trade for the day"""
        if not self.daily_trade_ranking:
            return signals
        
        # Add to daily signals
        self.daily_signals.extend(signals)
        
        # Sort by confidence and strength (highest first)
        self.daily_signals.sort(key=lambda x: (x.confidence, x.strength), reverse=True)
        
        # Select ONLY the TOP 1 trade
        best_trades = self.daily_signals[:1]  # Only TOP 1
        
        logger.info(f"📈 ULTRA SELECTIVE: Selected {len(best_trades)} momentum trade from {len(self.daily_signals)} signals")
        
        return best_trades
```

---

## 🔄 **ULTRA QUICK EARLY CLOSURE SYSTEM**

### **6. Order Manager Updates - ULTRA QUICK**

```python
# Add to src/core/order_manager.py

class OrderManager:
    def __init__(self):
        # ... existing code ...
        
        # ===============================================
        # ULTRA QUICK EARLY CLOSURE SETTINGS
        # ===============================================
        self.early_close_profit_pct = float(os.getenv('EARLY_CLOSE_PROFIT_PCT', '0.001'))
        self.early_close_loss_pct = float(os.getenv('EARLY_CLOSE_LOSS_PCT', '-0.002'))
        self.max_hold_time_minutes = int(os.getenv('MAX_HOLD_TIME_MINUTES', '30'))  # ULTRA QUICK
        self.trailing_stop_enabled = os.getenv('TRAILING_STOP_ENABLED', 'true').lower() == 'true'
        self.trailing_stop_distance = float(os.getenv('TRAILING_STOP_DISTANCE', '0.0005'))  # ULTRA TIGHT
        
        # Track active trades for ultra quick closure
        self.active_trades = {}
        self.trailing_stops = {}
        
        # ... rest of existing code ...
    
    def check_early_close_conditions(self, trade_id: str, current_price: float) -> Optional[str]:
        """Check if trade should be closed ultra quickly"""
        if trade_id not in self.active_trades:
            return None
        
        trade = self.active_trades[trade_id]
        entry_price = trade['entry_price']
        entry_time = trade['entry_time']
        side = trade['side']
        
        # Calculate current P&L percentage
        if side == 'BUY':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SELL
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Check profit target (ULTRA QUICK)
        if pnl_pct >= self.early_close_profit_pct:
            return 'CLOSE_PROFIT'
        
        # Check loss limit (ULTRA QUICK)
        if pnl_pct <= self.early_close_loss_pct:
            return 'CLOSE_LOSS'
        
        # Check max hold time (ULTRA QUICK - 30 minutes)
        hold_time = datetime.now() - entry_time
        if hold_time.total_seconds() / 60 >= self.max_hold_time_minutes:
            return 'CLOSE_TIME'
        
        # Check trailing stop (ULTRA TIGHT)
        if self.trailing_stop_enabled and pnl_pct > 0.0005:  # After +0.05% profit
            if trade_id in self.trailing_stops:
                trailing_stop = self.trailing_stops[trade_id]
                if side == 'BUY' and current_price <= trailing_stop:
                    return 'TRAILING_STOP'
                elif side == 'SELL' and current_price >= trailing_stop:
                    return 'TRAILING_STOP'
            
            # Update trailing stop (ULTRA TIGHT)
            if side == 'BUY':
                self.trailing_stops[trade_id] = current_price - (current_price * self.trailing_stop_distance)
            else:  # SELL
                self.trailing_stops[trade_id] = current_price + (current_price * self.trailing_stop_distance)
        
        return None
    
    def execute_early_close(self, trade_id: str, reason: str) -> bool:
        """Execute ultra quick closure of trade"""
        try:
            # Implementation for closing trade
            logger.info(f"🔒 ULTRA QUICK closing trade {trade_id}: {reason}")
            
            # Remove from active trades
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
            if trade_id in self.trailing_stops:
                del self.trailing_stops[trade_id]
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to close trade {trade_id}: {e}")
            return False
```

---

## 📊 **ULTRA CONSERVATIVE IMPLEMENTATION SUMMARY**

### **Configuration Changes:**
1. ✅ **Fixed overtrading limits** to ultra low (3,4,3)
2. ✅ **Added ultra quick early closure settings** (30 min max)
3. ✅ **Added ultra selective quality filter settings** (TOP 1 only)
4. ✅ **Added ultra selective session settings** (London/NY overlap only)

### **Strategy Enhancements:**
1. ✅ **Ultra conservative R:R ratios** (1:4.0 to 1:5.0)
2. ✅ **Ultra high signal quality** (0.90+ strength)
3. ✅ **Ultra selective daily trade ranking** (TOP 1 only)
4. ✅ **Ultra quick early closure system** (30 min max hold)
5. ✅ **Ultra selective entry filters** (5M,15M,1H,4H alignment)

### **Expected Results:**
- **95-97% fewer trades** (0-10 per day total)
- **Ultra conservative R:R ratios** (1:4.0 to 1:5.0)
- **Ultra quick profit taking** (+0.1% profit, -0.2% loss)
- **TOP 1 trade per strategy per day** only
- **Multi-timeframe confirmation** required (5M,15M,1H,4H)

**MAXIMUM 10 TRADES PER DAY TOTAL - NO FORCED TRADING!**

**All ultra conservative updates are ready for implementation after your structural changes!**
