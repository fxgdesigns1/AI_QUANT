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
        self.min_volatility = 0.00008  # OPTIMIZED: Higher volatility required
        self.max_spread = 0.6          # OPTIMIZED: Tighter spreads
        self.stop_loss_pips = 8        # OPTIMIZED: Tight stop loss
        self.take_profit_pips = 32     # OPTIMIZED: Better R:R = 1:4.0
        self.min_signal_strength = 0.80  # OPTIMIZED: High quality required
        self.max_trades_per_day = 10   # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0      # NO FORCED TRADES
        
        # ===============================================
        # ENHANCED ENTRY TIMING
        # ===============================================
        self.min_time_between_trades_minutes = 45  # OPTIMIZED: Increased spacing
        self.require_pullback = True               # Wait for pullback (don't chase)
        self.pullback_ema_period = 21              # Must pull back to 21 EMA
        self.only_trade_london_ny = True           # High volume sessions only
        
        # ===============================================
        # ENHANCED BREAKOUT CONFIGURATION
        # ===============================================
        self.breakout_lookback = 20                # OPTIMIZED: Longer lookback
        self.breakout_threshold = 0.003            # OPTIMIZED: 0.3% move required
        self.min_atr_for_entry = 2.0               # OPTIMIZED: Higher ATR required
        
        # ===============================================
        # OPTIMIZED QUALITY FILTERS
        # ===============================================
        self.max_daily_quality_trades = 5          # Top 5 quality trades per day
        self.quality_score_threshold = 0.85        # High quality threshold
        self.daily_trade_ranking = True            # Rank and select best
        self.require_multiple_confirmations = True
        self.min_confirmations = 3                 # At least 3 confirmations
        
        # ===============================================
        # ENHANCED SESSION FILTERING
        # ===============================================
        self.london_session_start = 7              # 07:00 UTC
        self.london_session_end = 16               # 16:00 UTC
        self.ny_session_start = 13                 # 13:00 UTC
        self.ny_session_end = 21                   # 21:00 UTC
        self.prefer_london_ny_overlap = True       # Prefer 13:00-16:00 UTC
        
        # ===============================================
        # EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.0015       # Close at +0.15% profit
        self.early_close_loss_pct = -0.003         # Close at -0.3% loss
        self.max_hold_time_minutes = 90            # Max 1.5 hours hold
        self.trailing_stop_enabled = True          # Enable trailing stops
        self.trailing_stop_distance = 0.0008       # 0.08% trailing distance
        
        # ===============================================
        # DATA STORAGE
        # ===============================================
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.volatility_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
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
            logger.info("✅ News integration enabled - monitoring gold-related events")
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
            logger.info("🔄 Daily counters reset")
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA for given period"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        prices_array = np.array(prices)
        alpha = 2.0 / (period + 1)
        ema = prices_array[0]
        
        for price in prices_array[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(prices) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = abs(prices[i] - prices[i-1])
            true_ranges.append(high_low)
        
        if len(true_ranges) < period:
            return np.mean(true_ranges) if true_ranges else 0.0
        
        return np.mean(true_ranges[-period:])
    
    def _check_pullback_to_ema(self, prices: List[float]) -> bool:
        """Check if price has pulled back to EMA"""
        if len(prices) < self.pullback_ema_period:
            return False
        
        current_price = prices[-1]
        ema = self._calculate_ema(prices, self.pullback_ema_period)
        
        # Check if price is near EMA (within 0.1% for gold)
        price_diff_pct = abs(current_price - ema) / ema
        return price_diff_pct <= 0.001  # 0.1% tolerance
    
    def _is_london_or_ny_session(self) -> bool:
        """Check if current time is London or NY session"""
        now = datetime.now()
        current_hour = now.hour
        
        # London session: 07:00-16:00 UTC
        london_session = self.london_session_start <= current_hour < self.london_session_end
        
        # NY session: 13:00-21:00 UTC
        ny_session = self.ny_session_start <= current_hour < self.ny_session_end
        
        return london_session or ny_session
    
    def _is_london_ny_overlap(self) -> bool:
        """Check if current time is London/NY overlap"""
        now = datetime.now()
        current_hour = now.hour
        
        # London/NY overlap: 13:00-16:00 UTC
        return self.london_session_start <= current_hour < self.ny_session_start
    
    def _can_trade_now(self) -> bool:
        """Check if we can trade now (time spacing)"""
        if self.last_trade_time is None:
            return True
        
        time_since_last = datetime.now() - self.last_trade_time
        return time_since_last.total_seconds() / 60 >= self.min_time_between_trades_minutes
    
    def _check_breakout_condition(self, prices: List[float]) -> Tuple[bool, str]:
        """Check for breakout condition"""
        if len(prices) < self.breakout_lookback + 1:
            return False, "insufficient_data"
        
        current_price = prices[-1]
        lookback_prices = prices[-self.breakout_lookback-1:-1]
        
        if not lookback_prices:
            return False, "no_lookback_data"
        
        # Calculate breakout threshold
        avg_price = np.mean(lookback_prices)
        breakout_threshold_price = avg_price * self.breakout_threshold
        
        # Check for breakout
        price_change = abs(current_price - avg_price)
        
        if price_change >= breakout_threshold_price:
            if current_price > avg_price:
                return True, "bullish_breakout"
            else:
                return True, "bearish_breakout"
        
        return False, "no_breakout"
    
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
        
        logger.info(f"🥇 Selected {len(best_trades)} best gold trades from {len(self.daily_signals)} signals")
        
        return best_trades
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Check time spacing
        if not self._can_trade_now():
            logger.info(f"⏰ Skipping trade: minimum {self.min_time_between_trades_minutes}min gap required")
            return []
        
        # Check session
        if self.only_trade_london_ny and not self._is_london_or_ny_session():
            logger.info("⏰ Skipping trade: outside London/NY sessions")
            return []
        
        trade_signals = []
        min_strength = self.min_signal_strength
        
        for instrument, data in market_data.items():
            if instrument not in self.instruments:
                continue
            
            # Update price history
            if instrument not in self.price_history:
                self.price_history[instrument] = []
            
            self.price_history[instrument].append(data.price)
            
            # Keep only recent prices
            if len(self.price_history[instrument]) > 100:
                self.price_history[instrument] = self.price_history[instrument][-100:]
            
            # Check minimum data
            if len(self.price_history[instrument]) < self.breakout_lookback:
                continue
            
            # Calculate volatility
            recent_prices = self.price_history[instrument][-20:]
            volatility = np.std(recent_prices) / np.mean(recent_prices)
            
            # Volatility filter
            if volatility < self.min_volatility:
                continue
            
            # Spread filter
            if hasattr(data, 'spread') and data.spread > self.max_spread:
                continue
            
            # ATR filter
            atr = self._calculate_atr(self.price_history[instrument])
            if atr < self.min_atr_for_entry:
                continue
            
            # Check breakout condition
            breakout_detected, breakout_type = self._check_breakout_condition(self.price_history[instrument])
            
            if not breakout_detected:
                continue
            
            # Pullback requirement
            if self.require_pullback and not self._check_pullback_to_ema(self.price_history[instrument]):
                logger.info(f"⏰ Waiting for pullback on {instrument}")
                continue
            
            # Multiple confirmations check
            confirmations = 0
            if breakout_detected:
                confirmations += 1
            if volatility >= self.min_volatility:
                confirmations += 1
            if atr >= self.min_atr_for_entry:
                confirmations += 1
            if self._is_london_ny_overlap():
                confirmations += 1  # Bonus for overlap session
            
            if confirmations < self.min_confirmations:
                continue
            
            # Generate signal based on breakout type
            if breakout_type == "bullish_breakout":
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.BUY,
                    units=50000,  # 0.5 lots for gold
                    entry_price=data.price,
                    stop_loss=data.price - (self.stop_loss_pips * 0.01),  # Convert pips to price
                    take_profit=data.price + (self.take_profit_pips * 0.01),
                    confidence=min(volatility * 100, 1.0),  # Scale volatility to confidence
                    strength=min(volatility * 100, 1.0),
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
                
            elif breakout_type == "bearish_breakout":
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.SELL,
                    units=50000,  # 0.5 lots for gold
                    entry_price=data.price,
                    stop_loss=data.price + (self.stop_loss_pips * 0.01),  # Convert pips to price
                    take_profit=data.price - (self.take_profit_pips * 0.01),
                    confidence=min(volatility * 100, 1.0),  # Scale volatility to confidence
                    strength=min(volatility * 100, 1.0),
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
        
        # Quality filtering and ranking
        if trade_signals:
            trade_signals = self._select_best_daily_trades(trade_signals)
            self.daily_trade_count += len(trade_signals)
            self.last_trade_time = datetime.now()  # Update last trade time
        
        # News integration (optional, non-breaking)
        if self.news_enabled and NEWS_AVAILABLE and trade_signals:
            try:
                # GOLD-SPECIFIC: Pause during high-impact gold events (Fed, rates, inflation)
                if safe_news_integration.should_pause_trading(['XAU_USD']):
                    logger.warning("🚫 Gold trading paused - high-impact monetary news")
                    return []
                
                # Apply news sentiment boost/reduction to signals
                news_analysis = safe_news_integration.get_news_analysis(['XAU_USD'])
                
                for signal in trade_signals:
                    boost = safe_news_integration.get_news_boost_factor(
                        signal.side.value,
                        [signal.instrument]
                    )
                    signal.confidence = signal.confidence * boost
                    
                    if boost > 1.0:
                        logger.info(f"📈 News boost applied to {signal.instrument}: {boost:.2f}x")
                    elif boost < 1.0:
                        logger.info(f"📉 News reduction applied to {signal.instrument}: {boost:.2f}x")
                
            except Exception as e:
                logger.warning(f"⚠️  News check failed (trading anyway): {e}")
        
        return trade_signals if trade_signals else []
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        return {
            'name': self.name,
            'instruments': self.instruments,
            'daily_trades': self.daily_trade_count,
            'max_daily_trades': self.max_trades_per_day,
            'trades_remaining': self.max_trades_per_day - self.daily_trade_count,
            'parameters': {
                'min_volatility': self.min_volatility,
                'max_spread': self.max_spread,
                'stop_loss_pips': self.stop_loss_pips,
                'take_profit_pips': self.take_profit_pips,
                'rr_ratio': self.take_profit_pips / self.stop_loss_pips,
                'min_signal_strength': self.min_signal_strength,
                'max_quality_trades': self.max_daily_quality_trades,
                'min_time_between_trades_minutes': self.min_time_between_trades_minutes,
                'early_close_profit_pct': self.early_close_profit_pct,
                'early_close_loss_pct': self.early_close_loss_pct,
                'max_hold_time_minutes': self.max_hold_time_minutes
            },
            'news_enabled': self.news_enabled,
            'last_reset_date': self.last_reset_date.isoformat()
        }
