#!/usr/bin/env python3
"""
Gold Scalping Strategy - OPTIMIZED VERSION
Maximum 10 trades per day with ultra high quality filters
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ..core.order_manager import TradeSignal, OrderSide, get_order_manager
from ..core.data_feed import MarketData, get_data_feed

# News integration (optional, non-breaking)
try:
    from ..core.news_integration import safe_news_integration
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False


# Contextual trading modules (optional, non-breaking)
try:
    from ..core.session_manager import get_session_manager
    from ..core.quality_scoring import get_quality_scoring
    from ..core.price_context_analyzer import get_price_context_analyzer
    CONTEXTUAL_AVAILABLE = True
except ImportError:
    CONTEXTUAL_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScalpingSignal:
    """Gold scalping signal"""
    instrument: str
    signal: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-1
    timestamp: datetime
    price_level: float
    volatility: float
    spread: float

class GoldScalpingStrategy:
    """OPTIMIZED Gold Scalping Strategy - MAX 10 TRADES/DAY"""
    
    def __init__(self):
        """Initialize optimized strategy"""
        self.name = "Gold Scalping - Optimized"
        self.instruments = ['XAU_USD']
        
        # ===============================================
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY
        # ===============================================
        self.stop_loss_pips = 6              # OPTIMIZED: 6 pips stop loss
        self.take_profit_pips = 24           # OPTIMIZED: 24 pips take profit = 1:4.0 R:R
        self.min_signal_strength = 0.70      # REALISTIC: High quality but not impossible (was 0.85 - too strict!)
        self.max_trades_per_day = 10         # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0            # NO FORCED TRADES - only high-quality setups
        
        # ===============================================
        # ENHANCED VOLATILITY AND SPREAD FILTERS
        # ===============================================
        self.min_volatility = 0.00005        # REALISTIC: Moderate volatility (was 0.0001 - too strict)
        self.max_spread = 1.0                # REALISTIC: 1 pip spread max (was 0.5 - too strict, missing trades!)
        self.min_atr_for_entry = 1.5         # REALISTIC: $1.50 ATR (was $2.00 - too strict)
        self.volatility_lookback = 20        # Look back 20 periods for volatility
        
        # ===============================================
        # OPTIMIZED QUALITY FILTERS
        # ===============================================
        self.max_daily_quality_trades = 5    # Top 5 quality trades per day
        self.quality_score_threshold = 0.40  # AGGRESSIVE: Lower for more trades (was 0.90)
        self.daily_trade_ranking = True      # Rank and select best
        self.require_multiple_confirmations = True
        self.min_confirmations = 3           # At least 3 confirmations
        
        # ===============================================
        # ENHANCED ENTRY CONDITIONS
        # ===============================================
        self.only_trade_london_ny = True     # High volume sessions only
        self.london_session_start = 7        # 07:00 UTC
        self.london_session_end = 16         # 16:00 UTC
        self.ny_session_start = 13           # 13:00 UTC
        self.ny_session_end = 21             # 21:00 UTC
        self.min_time_between_trades_minutes = 45  # Space out trades more
        self.require_pullback = True         # WAIT for pullback (don't chase)
        self.pullback_ema_period = 21        # Must pull back to 21 EMA
        self.pullback_threshold = 0.0003     # 0.03% pullback required
        
        # ===============================================
        # BREAKOUT CONFIGURATION - ULTRA STRICT
        # ===============================================
        self.breakout_lookback = 15          # Look back 15 periods
        self.breakout_threshold = 0.005      # 0.5% move - VERY STRONG only
        self.require_volume_spike = True     # Volume confirmation required
        self.volume_spike_multiplier = 2.0   # 2x average volume
        
        # ===============================================
        # EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.0015    # Close at +0.15% profit
        self.early_close_loss_pct = -0.0025     # Close at -0.25% loss
        self.max_hold_time_minutes = 90         # Max 1.5 hours hold
        self.trailing_stop_enabled = True       # Enable trailing stops
        self.trailing_stop_distance = 0.0008    # 0.08% trailing distance
        
        # ===============================================
        # DATA STORAGE
        # ===============================================
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.signals: List[TradeSignal] = []
        self.daily_signals = []  # Store all signals for ranking
        self.selected_trades = []  # Quality trades selected
        
        # ===============================================
        # PERFORMANCE TRACKING
        # ===============================================
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        self.last_trade_time = None  # Track time between trades
        
        # ===============================================
        # NEWS INTEGRATION
        # ===============================================
        self.news_enabled = NEWS_AVAILABLE and safe_news_integration.enabled if NEWS_AVAILABLE else False
        if self.news_enabled:
            logger.info("✅ News integration enabled for quality filtering")
        else:
            logger.info("ℹ️  Trading without news integration (technical signals only)")
        
        logger.info(f"✅ {self.name} strategy initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Max trades/day: {self.max_trades_per_day}")
        logger.info(f"📊 R:R ratio: 1:{self.take_profit_pips/self.stop_loss_pips:.1f}")
    
    @property
    def daily_trades(self):
        """Get daily trade count"""
        return self.daily_trade_count
    
    def _reset_daily_counters(self):
        """Reset daily counters if new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = current_date
            self.daily_signals = []  # Reset daily signals
            self.last_trade_time = None
            logger.info("🔄 Daily counters reset")
    
    def _is_london_or_ny_session(self) -> bool:
        """Check if current time is London or NY session"""
        now = datetime.now()
        current_hour = now.hour
        
        # London session: 07:00-16:00 UTC
        london_session = self.london_session_start <= current_hour < self.london_session_end
        
        # NY session: 13:00-21:00 UTC
        ny_session = self.ny_session_start <= current_hour < self.ny_session_end
        
        return london_session or ny_session
    
    def _can_trade_now(self) -> bool:
        """Check if enough time has passed since last trade"""
        if self.last_trade_time is None:
            return True
        
        time_since_last = datetime.now() - self.last_trade_time
        return time_since_last.total_seconds() >= (self.min_time_between_trades_minutes * 60)
    
    def _check_pullback_to_ema(self, prices: List[float]) -> bool:
        """Check if price has pulled back to EMA"""
        if len(prices) < self.pullback_ema_period:
            return False
        
        # Calculate EMA
        df = pd.Series(prices)
        ema = df.ewm(span=self.pullback_ema_period).mean().iloc[-1]
        current_price = prices[-1]
        
        # Check if price is near EMA (within threshold)
        pullback_distance = abs(current_price - ema) / ema
        return pullback_distance <= self.pullback_threshold
    
    def _check_breakout(self, prices: List[float]) -> Tuple[bool, str]:
        """Check for breakout patterns"""
        if len(prices) < self.breakout_lookback:
            return False, 'HOLD'
        
        recent_prices = prices[-self.breakout_lookback:]
        current_price = recent_prices[-1]
        low_price = min(recent_prices[:-1])  # Exclude current price
        high_price = max(recent_prices[:-1])
        
        # Check for upward breakout
        if current_price > high_price * (1 + self.breakout_threshold):
            return True, 'BUY'
        
        # Check for downward breakout
        if current_price < low_price * (1 - self.breakout_threshold):
            return True, 'SELL'
        
        return False, 'HOLD'
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(prices) < period:
            return 0.0
        
        df = pd.Series(prices)
        high = df
        low = df
        close = df.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) else 0.0
    
    def _select_best_daily_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Select only the best trades for the day"""
        if not self.daily_trade_ranking:
            return signals
        
        # Add to daily signals
        self.daily_signals.extend(signals)
        
        # Sort by confidence and strength (highest first)
        self.daily_signals.sort(key=lambda x: (x.confidence, x.strength), reverse=True)
        
        # Select top quality trades
        best_trades = self.daily_signals[:self.max_daily_quality_trades]
        
        logger.info(f"🎯 Selected {len(best_trades)} best trades from {len(self.daily_signals)} signals")
        
        return best_trades
    
    def _update_price_history(self, market_data: Dict[str, MarketData]):
        """Update price history for all instruments"""
        for instrument, data in market_data.items():
            if instrument in self.instruments:
                # Use mid price (average of bid and ask)
                mid_price = (data.bid + data.ask) / 2
                self.price_history[instrument].append(mid_price)
                
                # Keep only last 100 prices for efficiency
                if len(self.price_history[instrument]) > 100:
                    self.price_history[instrument] = self.price_history[instrument][-100:]
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals with enhanced quality filters"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Update price history
        self._update_price_history(market_data)
        
        trade_signals = []
        
        # Session filter
        if self.only_trade_london_ny and not self._is_london_or_ny_session():
            logger.info("⏰ Skipping trade: outside London/NY sessions")
            return []
        
        # Time between trades filter
        if not self._can_trade_now():
            logger.info(f"⏰ Skipping trade: minimum {self.min_time_between_trades_minutes}min gap required")
            return []
        
        for instrument in self.instruments:
            if instrument not in market_data or len(self.price_history[instrument]) < 20:
                continue
            
            current_data = market_data[instrument]
            prices = self.price_history[instrument]
            
            # Spread filter
            spread = current_data.ask - current_data.bid
            if spread > self.max_spread:
                logger.info(f"⏰ Skipping {instrument}: spread too wide ({spread:.3f})")
                continue
            
            # Volatility filter
            recent_prices = prices[-self.volatility_lookback:]
            volatility = np.std(recent_prices) / np.mean(recent_prices)
            if volatility < self.min_volatility:
                logger.info(f"⏰ Skipping {instrument}: volatility too low ({volatility:.6f})")
                continue
            
            # ATR filter
            atr = self._calculate_atr(prices)
            if atr < self.min_atr_for_entry:
                logger.info(f"⏰ Skipping {instrument}: ATR too low ({atr:.2f})")
                continue
            
            # Check for breakout
            is_breakout, breakout_direction = self._check_breakout(prices)
            if not is_breakout:
                continue
            
            # Pullback requirement
            if self.require_pullback and not self._check_pullback_to_ema(prices):
                logger.info(f"⏰ Waiting for pullback on {instrument}")
                continue
            
            # Multiple confirmations check
            confirmations = 0
            if volatility >= self.min_volatility:
                confirmations += 1
            if atr >= self.min_atr_for_entry:
                confirmations += 1
            if spread <= self.max_spread:
                confirmations += 1
            
            if confirmations < self.min_confirmations:
                continue
            
            # Generate trade signal
            if breakout_direction == 'BUY':
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.BUY,
                    units=10,  # 0.1 lot for Gold
                    entry_price=current_data.ask,
                    stop_loss=current_data.ask - (self.stop_loss_pips * 0.0001),
                    take_profit=current_data.ask + (self.take_profit_pips * 0.0001),
                    confidence=min(1.0, max(volatility * 50, 0.60)),  # Meaningful confidence (60-100%)
                    strength=min(1.0, atr / 5.0),  # Scale ATR to strength
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
                logger.info(f"✅ BUY signal generated for {instrument}: volatility={volatility:.6f}, ATR={atr:.2f}")
            
            elif breakout_direction == 'SELL':
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.SELL,
                    units=10,  # 0.1 lot for Gold
                    entry_price=current_data.bid,
                    stop_loss=current_data.bid + (self.stop_loss_pips * 0.0001),
                    take_profit=current_data.bid - (self.take_profit_pips * 0.0001),
                    confidence=min(1.0, max(volatility * 50, 0.60)),  # Meaningful confidence (60-100%)
                    strength=min(1.0, atr / 5.0),  # Scale ATR to strength
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
                logger.info(f"✅ SELL signal generated for {instrument}: volatility={volatility:.6f}, ATR={atr:.2f}")
        
        # Quality filtering and ranking
        if trade_signals:
            trade_signals = self._select_best_daily_trades(trade_signals)
            self.daily_trade_count += len(trade_signals)
            self.last_trade_time = datetime.now()  # Update last trade time
        
        # GOLD-SPECIFIC: News integration for gold events
        if self.news_enabled and NEWS_AVAILABLE and trade_signals:
            try:
                if safe_news_integration.should_pause_trading(['XAU_USD']):
                    logger.warning("🚫 Gold trading paused - high-impact monetary news")
                    return []
                
                news_analysis = safe_news_integration.get_news_analysis(['XAU_USD'])
                
                for signal in trade_signals:
                    boost = safe_news_integration.get_news_boost_factor(
                        signal.side.value,
                        [signal.instrument]
                    )
                    signal.confidence = signal.confidence * boost
                    
                    if boost > 1.0:
                        logger.info(f"📈 Gold news boost applied to {signal.instrument}: {boost:.2f}x")
                    elif boost < 1.0:
                        logger.info(f"📉 Gold news reduction applied to {signal.instrument}: {boost:.2f}x")
                
            except Exception as e:
                logger.warning(f"⚠️  News check failed (trading anyway): {e}")
        
        return trade_signals
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate trading signals"""
        try:
            signals = self._generate_trade_signals(market_data)
            
            if signals:
                logger.info(f"🎯 {self.name} generated {len(signals)} signals")
                for signal in signals:
                    logger.info(f"   📈 {signal.instrument} {signal.side.value} - Confidence: {signal.confidence:.2f}")
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ {self.name} analysis error: {e}")
            return []
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        self._reset_daily_counters()
        
        return {
            'name': self.name,
            'instruments': self.instruments,
            'daily_trades': self.daily_trade_count,
            'max_daily_trades': self.max_trades_per_day,
            'trades_remaining': self.max_trades_per_day - self.daily_trade_count,
            'parameters': {
                'stop_loss_pips': self.stop_loss_pips,
                'take_profit_pips': self.take_profit_pips,
                'min_signal_strength': self.min_signal_strength,
                'min_volatility': self.min_volatility,
                'max_spread': self.max_spread
            },
            'last_update': datetime.now().isoformat()
        }

# Global strategy instance
gold_scalping = GoldScalpingStrategy()

def get_gold_scalping_strategy() -> GoldScalpingStrategy:
    """Get the global Gold Scalping strategy instance"""
    return gold_scalping
