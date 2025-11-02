#!/usr/bin/env python3
"""
GOLD TRUMP WEEK STRATEGY - October 6-11, 2025
Specialized strategy to capitalize on Trump government shutdown chaos
Target: Maximize profits from gold's rally to $4,000+

This strategy is TIME-LIMITED and will auto-disable after October 11, 2025
"""

import logging
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.order_manager import TradeSignal, OrderSide
from src.core.data_feed import MarketData
from src.core.position_sizing import get_position_sizer
from src.core.news_integration import safe_news_integration
from src.core.oanda_client import get_oanda_client

logger = logging.getLogger(__name__)

@dataclass
class GoldLevel:
    """Gold price level with action"""
    price: float
    action: str  # 'ENTRY', 'PROFIT', 'STOP'
    strength: float  # 0-1

class GoldTrumpWeekStrategy:
    """
    GOLD TRUMP WEEK STRATEGY
    
    Specialized strategy for Oct 6-11, 2025 to capitalize on:
    - Trump government shutdown chaos
    - Record gold prices ($3,972+)
    - USD weakness from policy uncertainty
    - Target: $4,000-$4,050 by Friday
    
    Strategy:
    - Multiple entry zones (pullbacks + breakouts)
    - Aggressive position sizing (2% risk for high-confidence)
    - Scale in/out at key levels
    - Take profits at psychological levels
    - Close most positions before Friday close
    """
    
    def __init__(self):
        self.name = "Gold_Trump_Week_Strategy"
        self.description = "Aggressive gold strategy for Trump shutdown week (Oct 6-11)"
        self.instruments = ['XAU_USD']
        self.timeframe = '5m'
        
        # TIME-LIMITED: Strategy expires Friday Oct 11, 2025 at 5PM UTC
        self.strategy_end_date = datetime(2025, 10, 11, 17, 0, 0)
        
        # ENTRY ZONES (Buy on pullbacks or breakouts)
        self.entry_zones = [
            GoldLevel(3950.0, 'ENTRY', 1.0),   # Deep pullback (aggressive buy)
            GoldLevel(3960.0, 'ENTRY', 0.95),  # Medium pullback (strong buy)
            GoldLevel(3970.0, 'ENTRY', 0.85),  # Shallow pullback (buy)
            GoldLevel(3980.0, 'ENTRY', 0.90),  # Breakout level (buy)
            GoldLevel(3990.0, 'ENTRY', 0.80),  # Strong breakout (cautious buy)
        ]
        
        # PROFIT TARGETS (Take profits at these levels)
        self.profit_targets = [
            GoldLevel(3990.0, 'PROFIT', 0.33),   # Take 33% here
            GoldLevel(4000.0, 'PROFIT', 0.50),   # Take 50% here (psychological level)
            GoldLevel(4010.0, 'PROFIT', 0.75),   # Take 75% here
            GoldLevel(4025.0, 'PROFIT', 1.00),   # Close all remaining
        ]
        
        # STOP LOSS LEVELS
        self.initial_stop_atr_multiplier = 1.0  # Tighter stops for gold ($5-7)
        self.breakeven_trigger_pct = 0.30       # Move to BE after 30% to target
        self.trailing_stop_distance = 8.0       # $8 trailing stop
        
        # POSITION SIZING (More aggressive this week)
        self.risk_per_trade_pct = 2.0           # 2% risk (vs normal 1.5%)
        self.max_concurrent_gold_positions = 3   # Max 3 gold trades
        self.max_position_size = 2000           # Max 2000 units (0.02 lots)
        self.min_position_size = 500            # Min 500 units
        
        # SPREAD & QUALITY FILTERS
        self.max_spread_pips = 5.0              # Max 5 pips (gold can be wider)
        self.min_confidence = 0.75              # Lower threshold for more trades
        
        # TRUMP NEWS MULTIPLIER
        self.news_volatility_multiplier = 1.5   # 1.5x position on news spikes
        
        # TRADING HOURS (Best for gold)
        self.trading_hours = [
            (time(8, 0), time(11, 0)),   # London morning (best)
            (time(13, 0), time(16, 0)),  # NY morning (second best)
            (time(19, 0), time(22, 0)),  # NY afternoon
        ]
        
        # FRIDAY RISK MANAGEMENT
        self.friday_close_time = time(15, 0)    # Close 80% by 3PM Friday
        self.friday_position_reduction = 0.80    # Reduce to 20% before weekend
        
        # PERFORMANCE TRACKING
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
        # MARKET DATA
        self.price_history = []
        self.last_entry_price = 0
        self.last_entry_time = None
        
        logger.info(f"🥇 {self.name} initialized - ACTIVE until {self.strategy_end_date}")
        logger.info(f"   Target: $4,000-$4,050 by Friday")
        logger.info(f"   Risk: {self.risk_per_trade_pct}% per trade")
        logger.info(f"   Max positions: {self.max_concurrent_gold_positions}")
    
    def is_strategy_active(self) -> bool:
        """Check if strategy should still be active"""
        now = datetime.now()
        
        # Check if past expiry date
        if now > self.strategy_end_date:
            logger.warning(f"⚠️ {self.name} EXPIRED on {self.strategy_end_date}")
            return False
        
        # Check if it's Friday after closing time
        if now.weekday() == 4 and now.time() > self.friday_close_time:
            logger.warning(f"⚠️ {self.name} auto-disabled after Friday 3PM")
            return False
        
        return True
    
    def is_trading_hours(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within gold trading hours"""
        if current_time is None:
            current_time = datetime.now()
        
        current_hour_minute = current_time.time()
        
        for start, end in self.trading_hours:
            if start <= current_hour_minute <= end:
                return True
        
        return False
    
    def get_current_level(self, price: float) -> Optional[GoldLevel]:
        """Get the closest level to current price"""
        closest_level = None
        min_distance = float('inf')
        
        for level in self.entry_zones:
            distance = abs(price - level.price)
            if distance < min_distance:
                min_distance = distance
                closest_level = level
        
        return closest_level
    
    def should_enter(self, current_price: float, atr: float) -> tuple[bool, str, float]:
        """
        Determine if we should enter based on current price
        
        Returns:
            (should_enter: bool, reason: str, confidence: float)
        """
        # Check each entry zone
        for level in self.entry_zones:
            # Within $3 of entry level = trigger
            if abs(current_price - level.price) <= 3.0:
                
                # Determine entry type
                if current_price < 3970:
                    reason = f"PULLBACK to ${level.price:.0f} support"
                elif current_price >= 3980:
                    reason = f"BREAKOUT above ${level.price:.0f}"
                else:
                    reason = f"ENTRY ZONE at ${level.price:.0f}"
                
                return True, reason, level.strength
        
        # Check if breaking to new highs (momentum entry)
        if current_price >= 3995:
            return True, "MOMENTUM BREAKOUT - New highs", 0.85
        
        return False, "No entry signal", 0.0
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        account_balance: float,
        confidence: float
    ) -> int:
        """Calculate position size with aggressive sizing for high-confidence trades"""
        
        try:
            position_sizer = get_position_sizer()
            
            # Use 2% risk for this strategy
            risk_pct = self.risk_per_trade_pct
            
            # Increase risk for very high confidence (>0.9)
            if confidence >= 0.90:
                risk_pct = 2.5  # 2.5% for highest confidence
                logger.info(f"🔥 HIGH CONFIDENCE ({confidence:.2f}) - Using {risk_pct}% risk")
            
            pos_size = position_sizer.calculate_position_size(
                account_balance=account_balance,
                risk_percent=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                instrument='XAU_USD'
            )
            
            # Apply limits
            units = max(self.min_position_size, min(pos_size.units, self.max_position_size))
            
            return units
            
        except Exception as e:
            logger.error(f"❌ Position sizing error: {e}")
            return self.min_position_size
    
    def calculate_stop_loss(self, entry_price: float, side: OrderSide, atr: float) -> float:
        """Calculate stop loss based on ATR"""
        stop_distance = atr * self.initial_stop_atr_multiplier
        
        # Minimum $5 stop, maximum $10 stop
        stop_distance = max(5.0, min(stop_distance, 10.0))
        
        if side == OrderSide.BUY:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def calculate_take_profit(self, entry_price: float, side: OrderSide) -> float:
        """Calculate initial take profit target"""
        # First target is $4,000 (psychological level)
        if side == OrderSide.BUY:
            return 4000.0 if entry_price < 4000 else entry_price + 15.0
        else:
            return 3950.0 if entry_price > 3950 else entry_price - 15.0
    
    def _calculate_atr(self, period: int = 14) -> float:
        """Calculate ATR from price history"""
        if len(self.price_history) < period + 1:
            return 3.0  # Default ATR for gold
        
        true_ranges = []
        for i in range(1, len(self.price_history)):
            current = self.price_history[i]
            previous = self.price_history[i-1]
            
            tr1 = current['high'] - current['low']
            tr2 = abs(current['high'] - previous['close'])
            tr3 = abs(current['low'] - previous['close'])
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if len(true_ranges) < period:
            return 3.0
        
        return sum(true_ranges[-period:]) / period
    
    def _update_price_history(self, market_data: MarketData):
        """Update price history"""
        self.price_history.append({
            'timestamp': datetime.now(),
            'close': (market_data.bid + market_data.ask) / 2,
            'high': market_data.ask,
            'low': market_data.bid
        })
        
        # Keep only last 100 candles
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate gold trading signals"""
        signals = []
        
        # Check if strategy is still active
        if not self.is_strategy_active():
            logger.info(f"⚠️ {self.name} is no longer active")
            return signals
        
        # Check trading hours
        if not self.is_trading_hours():
            logger.debug(f"⏰ Outside gold trading hours")
            return signals
        
        # News-aware: Pause trading if high-impact negative news (do NOT skip gold)
        try:
            if safe_news_integration and safe_news_integration.enabled:
                if safe_news_integration.should_pause_trading(['XAU_USD'], ignore_skip=True):
                    logger.warning("🚫 Pausing gold trades due to high-impact negative news")
                    return signals
        except Exception as _:
            pass

        # Get gold market data
        gold_data = market_data.get('XAU_USD')
        if not gold_data:
            return signals
        
        # Update price history
        self._update_price_history(gold_data)
        
        try:
            current_price = (gold_data.bid + gold_data.ask) / 2
            spread = gold_data.ask - gold_data.bid
            spread_pips = spread * 10  # Gold pip calculation
            
            # Check spread
            if spread_pips > self.max_spread_pips:
                logger.warning(f"⚠️ Gold spread too wide: {spread_pips:.1f} pips > {self.max_spread_pips}")
                return signals
            
            # Calculate ATR
            atr = self._calculate_atr()
            
            # Check if we should enter
            should_enter, reason, confidence = self.should_enter(current_price, atr)
            
            if not should_enter:
                return signals
            
            # News-aware: boost/reduce confidence based on news analysis
            try:
                if safe_news_integration and safe_news_integration.enabled:
                    boost = safe_news_integration.get_news_boost_factor('BUY', ['XAU_USD'])
                    confidence *= boost
                    logger.info(f"📰 News factor applied to confidence: x{boost:.2f} → {confidence:.2f}")
            except Exception as _:
                pass

            # Check minimum confidence
            if confidence < self.min_confidence:
                logger.debug(f"⚠️ Confidence too low: {confidence:.2f} < {self.min_confidence}")
                return signals
            
            # Prevent over-trading (max 1 entry per 30 minutes)
            if self.last_entry_time:
                time_since_last = datetime.now() - self.last_entry_time
                if time_since_last < timedelta(minutes=30):
                    logger.debug(f"⏰ Too soon since last entry ({time_since_last.seconds//60} min)")
                    return signals
            
            # Create trade signal
            side = OrderSide.BUY  # Always long gold during chaos
            entry_price = gold_data.ask
            stop_loss = self.calculate_stop_loss(entry_price, side, atr)
            take_profit = self.calculate_take_profit(entry_price, side)
            
            # Get account balance for position sizing
            try:
                account_id = os.getenv('OANDA_ACCOUNT_ID', '101-004-30719775-007')
                client = get_oanda_client()
                account_info = client.get_account_summary()
                account_balance = float(account_info.get('balance', 95000))
            except:
                account_balance = 95000  # Fallback
            
            # Calculate position size
            position_size = self.calculate_position_size(
                entry_price, stop_loss, account_balance, confidence
            )
            
            # Create signal
            signal = TradeSignal(
                instrument='XAU_USD',
                side=side,
                units=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_name=self.name,
                confidence=confidence
            )
            
            signals.append(signal)
            
            # Update tracking
            self.last_entry_price = entry_price
            self.last_entry_time = datetime.now()
            self.daily_trades += 1
            
            logger.info(f"🥇 GOLD SIGNAL: {reason}")
            logger.info(f"   Entry: ${entry_price:.2f}")
            logger.info(f"   Stop: ${stop_loss:.2f}")
            logger.info(f"   Target: ${take_profit:.2f}")
            logger.info(f"   Size: {position_size} units")
            logger.info(f"   Confidence: {confidence:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error analyzing gold: {e}")
        
        return signals
    
    def get_strategy_info(self) -> Dict:
        """Get strategy information"""
        return {
            'name': self.name,
            'description': self.description,
            'instruments': self.instruments,
            'timeframe': self.timeframe,
            'active': self.is_strategy_active(),
            'expiry_date': self.strategy_end_date.isoformat(),
            'performance': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_profit': self.total_profit,
                'daily_trades': self.daily_trades
            },
            'parameters': {
                'risk_per_trade': f"{self.risk_per_trade_pct}%",
                'max_positions': self.max_concurrent_gold_positions,
                'max_spread': f"{self.max_spread_pips} pips",
                'entry_zones': [f"${level.price:.0f}" for level in self.entry_zones],
                'profit_targets': [f"${level.price:.0f}" for level in self.profit_targets]
            },
            'targets': {
                'week_target': '$4,000-$4,050',
                'profit_goal': '$10,000-$20,000',
                'expected_trades': '8-15 trades'
            }
        }

# Global instance
_gold_trump_strategy = None

def get_gold_trump_week_strategy():
    """Get Gold Trump Week Strategy instance"""
    global _gold_trump_strategy
    if _gold_trump_strategy is None:
        _gold_trump_strategy = GoldTrumpWeekStrategy()
    return _gold_trump_strategy





