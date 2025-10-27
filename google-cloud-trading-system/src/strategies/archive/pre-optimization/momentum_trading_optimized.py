#!/usr/bin/env python3
"""
Momentum Trading Strategy - OPTIMIZED VERSION
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
class MomentumSignal:
    """Momentum trading signal"""
    instrument: str
    trend: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    momentum_score: float  # -1 to 1
    volume_score: float  # 0 to 1
    strength: float  # 0 to 1
    timestamp: datetime
    atr: float  # Average True Range
    adx: float  # Average Directional Index

class MomentumTradingStrategy:
    """OPTIMIZED Momentum Trading Strategy - MAX 10 TRADES/DAY"""
    
    def __init__(self):
        """Initialize optimized strategy"""
        self.name = "Momentum Trading - Optimized"
        # SCALED UP: Added JPY pairs (USD_JPY was the big winner!)
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD', 
                           'EUR_JPY', 'GBP_JPY', 'AUD_JPY']
        
        # ===============================================
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY
        # ===============================================
        self.stop_loss_atr = 1.2             # OPTIMIZED: 1.2 ATR stop loss
        self.take_profit_atr = 6.0           # OPTIMIZED: 6.0 ATR take profit = 1:5.0 R:R
        self.min_signal_strength = 0.85      # OPTIMIZED: Very high quality
        self.max_trades_per_day = 10         # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0            # NO FORCED TRADES - only high-quality setups
        
        # ===============================================
        # ENHANCED MOMENTUM FILTERS - ELITE SETUPS ONLY
        # ===============================================
        self.min_adx = 25                    # OPTIMIZED: Stronger ADX requirement
        self.min_momentum = 0.008            # FIXED: 0.8% over 14 periods (was 0.40 = 40%!!! INSANE!)
        self.min_volume = 0.35               # OPTIMIZED: Above-average volume (was 0.30)
        self.momentum_period = 14            # Period for momentum calculation
        self.adx_period = 14                 # Period for ADX calculation
        self.volume_period = 20              # Period for volume analysis
        
        # ===============================================
        # OPTIMIZED QUALITY FILTERS
        # ===============================================
        self.max_daily_quality_trades = 5    # Top 5 quality trades per day
        self.quality_score_threshold = 0.90  # Very high quality threshold
        self.daily_trade_ranking = True      # Rank and select best
        self.require_multiple_confirmations = True
        self.min_confirmations = 4           # At least 4 confirmations (more strict)
        
        # ===============================================
        # ENHANCED ENTRY CONDITIONS
        # ===============================================
        self.only_trade_london_ny = True     # High volume sessions only
        self.london_session_start = 7        # 07:00 UTC
        self.london_session_end = 16         # 16:00 UTC
        self.ny_session_start = 13           # 13:00 UTC
        self.ny_session_end = 21             # 21:00 UTC
        self.min_time_between_trades_minutes = 60  # Space out trades more
        self.require_trend_continuation = True     # Must continue existing trend
        self.trend_continuation_periods = 5        # Last 5 periods must show continuation
        
        # ===============================================
        # EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.0015    # Close at +0.15% profit
        self.early_close_loss_pct = -0.0025     # Close at -0.25% loss
        self.max_hold_time_minutes = 150        # Max 2.5 hours hold
        self.trailing_stop_enabled = True       # Enable trailing stops
        self.trailing_stop_distance = 0.001     # 0.1% trailing distance
        
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
        logger.info(f"📊 R:R ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
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
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(prices) < period + 1:
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
    
    def _calculate_adx(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average Directional Index"""
        if len(prices) < period * 2:
            return 0.0
        
        df = pd.Series(prices)
        high = df
        low = df
        close = df.shift(1)
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)
        
        # Calculate smoothed values
        tr_smooth = tr.rolling(window=period).mean()
        dm_plus_smooth = dm_plus.rolling(window=period).mean()
        dm_minus_smooth = dm_minus.rolling(window=period).mean()
        
        # Calculate DI+ and DI-
        di_plus = 100 * (dm_plus_smooth / tr_smooth)
        di_minus = 100 * (dm_minus_smooth / tr_smooth)
        
        # Calculate ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean().iloc[-1]
        
        return adx if not pd.isna(adx) else 0.0
    
    def _check_trend_continuation(self, prices: List[float], direction: str) -> bool:
        """Check if trend is continuing"""
        if len(prices) < self.trend_continuation_periods + 1:
            return True
        
        recent_prices = prices[-self.trend_continuation_periods:]
        
        if direction == 'BULLISH':
            # Check if prices are generally increasing
            increasing_periods = sum(1 for i in range(1, len(recent_prices)) 
                                   if recent_prices[i] > recent_prices[i-1])
            return increasing_periods >= (len(recent_prices) * 0.6)  # 60% of periods
        
        elif direction == 'BEARISH':
            # Check if prices are generally decreasing
            decreasing_periods = sum(1 for i in range(1, len(recent_prices)) 
                                   if recent_prices[i] < recent_prices[i-1])
            return decreasing_periods >= (len(recent_prices) * 0.6)  # 60% of periods
        
        return True
    
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
            if instrument not in market_data or len(self.price_history[instrument]) < 30:
                continue
            
            current_data = market_data[instrument]
            prices = self.price_history[instrument]
            
            # Calculate indicators
            atr = self._calculate_atr(prices, self.momentum_period)
            adx = self._calculate_adx(prices, self.adx_period)
            
            if atr == 0 or adx == 0:
                continue
            
            # ADX filter - must be strong trend
            if adx < self.min_adx:
                logger.info(f"⏰ Skipping {instrument}: ADX too weak ({adx:.1f})")
                continue
            
            # Calculate momentum
            recent_prices = prices[-self.momentum_period:]
            momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            if abs(momentum) < self.min_momentum:
                logger.info(f"⏰ Skipping {instrument}: momentum too weak ({momentum:.4f})")
                continue
            
            # Volume confirmation (simplified)
            volume_score = 0.5  # Default volume score
            if hasattr(current_data, 'volume'):
                current_volume = current_data.volume
                avg_volume = np.mean([getattr(d, 'volume', 1000000) for d in market_data.values()])
                volume_score = min(1.0, current_volume / avg_volume)
            
            if volume_score < self.min_volume:
                logger.info(f"⏰ Skipping {instrument}: volume too low ({volume_score:.2f})")
                continue
            
            # Determine trend direction
            if momentum > 0:
                trend = 'BULLISH'
                side = OrderSide.BUY
            else:
                trend = 'BEARISH'
                side = OrderSide.SELL
            
            # Trend continuation check
            if self.require_trend_continuation and not self._check_trend_continuation(prices, trend):
                logger.info(f"⏰ Skipping {instrument}: trend not continuing")
                continue
            
            # Multiple confirmations check
            confirmations = 0
            if adx >= self.min_adx:
                confirmations += 1
            if abs(momentum) >= self.min_momentum:
                confirmations += 1
            if volume_score >= self.min_volume:
                confirmations += 1
            if atr > 0:
                confirmations += 1
            
            if confirmations < self.min_confirmations:
                continue
            
            # Calculate position size (JPY pairs get larger size)
            position_size = 150000 if instrument.endswith('JPY') else 100000
            
            # Generate trade signal
            trade_signal = TradeSignal(
                instrument=instrument,
                side=side,
                units=position_size,
                entry_price=current_data.ask if side == OrderSide.BUY else current_data.bid,
                stop_loss=(current_data.ask if side == OrderSide.BUY else current_data.bid) + 
                         (-self.stop_loss_atr * atr if side == OrderSide.BUY else self.stop_loss_atr * atr),
                take_profit=(current_data.ask if side == OrderSide.BUY else current_data.bid) + 
                           (self.take_profit_atr * atr if side == OrderSide.BUY else -self.take_profit_atr * atr),
                confidence=min(1.0, (adx / 100) * abs(momentum) * volume_score),
                strength=min(1.0, adx / 50),
                timestamp=datetime.now(),
                strategy_name=self.name
            )
            trade_signals.append(trade_signal)
            logger.info(f"✅ {trend} signal generated for {instrument}: ADX={adx:.1f}, momentum={momentum:.4f}, volume={volume_score:.2f}")
        
        # Quality filtering and ranking
        if trade_signals:
            trade_signals = self._select_best_daily_trades(trade_signals)
            self.daily_trade_count += len(trade_signals)
            self.last_trade_time = datetime.now()  # Update last trade time
        
        # News integration for momentum confirmation
        if self.news_enabled and NEWS_AVAILABLE and trade_signals:
            try:
                if safe_news_integration.should_pause_trading(self.instruments):
                    logger.warning("🚫 Momentum trading paused - conflicting high-impact news")
                    return []
                
                news_analysis = safe_news_integration.get_news_analysis(self.instruments)
                
                for signal in trade_signals:
                    boost = safe_news_integration.get_news_boost_factor(
                        signal.side.value,
                        [signal.instrument]
                    )
                    signal.confidence = signal.confidence * boost
                    
                    # Extra boost if momentum + news align strongly
                    if abs(news_analysis.get('overall_sentiment', 0)) > 0.3:
                        if ((signal.side.value == 'BUY' and news_analysis['overall_sentiment'] > 0) or
                            (signal.side.value == 'SELL' and news_analysis['overall_sentiment'] < 0)):
                            signal.confidence *= 1.05  # Small additional boost for alignment
                            logger.info(f"🎯 Strong momentum+news alignment: "
                                      f"{signal.instrument} {signal.side.value}")
                    
                    if boost > 1.0:
                        logger.info(f"📈 Momentum news boost applied to {signal.instrument}: {boost:.2f}x")
                    elif boost < 1.0:
                        logger.info(f"📉 Momentum news reduction applied to {signal.instrument}: {boost:.2f}x")
                
            except Exception as e:
                logger.warning(f"⚠️  News integration error: {e}")
        
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
                'stop_loss_atr': self.stop_loss_atr,
                'take_profit_atr': self.take_profit_atr,
                'min_signal_strength': self.min_signal_strength,
                'min_adx': self.min_adx,
                'min_momentum': self.min_momentum
            },
            'last_update': datetime.now().isoformat()
        }

# Global strategy instance
momentum_trading = MomentumTradingStrategy()

def get_momentum_trading_strategy() -> MomentumTradingStrategy:
    """Get the global Momentum Trading strategy instance"""
    return momentum_trading
