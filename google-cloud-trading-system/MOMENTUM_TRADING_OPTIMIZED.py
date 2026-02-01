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
        # OPTIMIZED: Enhanced instrument list with proven winners
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD', 
                           'EUR_JPY', 'GBP_JPY', 'AUD_JPY']
        
        # ===============================================
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY
        # ===============================================
        self.momentum_period = 14     # Period for momentum calculations
        self.volume_period = 20       # Period for volume analysis
        self.atr_period = 14          # Period for ATR calculation
        self.adx_period = 14          # Period for ADX calculation
        
        # OPTIMIZED: Higher quality requirements
        self.min_adx = 25             # OPTIMIZED: Only very strong trends
        self.min_momentum = 0.40      # OPTIMIZED: Only strong momentum
        self.min_volume = 0.30        # OPTIMIZED: Only high volume
        
        # OPTIMIZED: Better R:R ratios
        self.stop_loss_atr = 1.2      # OPTIMIZED: Reasonable stop loss
        self.take_profit_atr = 6.0    # OPTIMIZED: Better target = 1:5.0 R:R
        
        self.max_trades_per_day = 10  # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0     # NO FORCED TRADES - only strong signals
        
        # ===============================================
        # OPTIMIZED QUALITY FILTERS
        # ===============================================
        self.max_daily_quality_trades = 5    # Top 5 quality trades per day
        self.quality_score_threshold = 0.85  # High quality threshold
        self.daily_trade_ranking = True      # Rank and select best
        self.require_multiple_confirmations = True
        self.min_confirmations = 3           # At least 3 confirmations
        
        # ===============================================
        # ENHANCED ENTRY CONDITIONS
        # ===============================================
        self.require_trend_alignment = True
        self.trend_timeframes = ['5M', '15M', '1H', '4H']  # ALL must align
        self.trend_strength_min = 0.75                      # Strong trend required
        self.only_trade_london_ny = True                    # High volume sessions
        self.min_volatility_threshold = 0.00006             # Higher volatility required
        self.max_spread_threshold = 0.8                     # Reasonable spreads
        
        # ===============================================
        # ENHANCED SESSION FILTERING
        # ===============================================
        self.london_session_start = 7                       # 07:00 UTC
        self.london_session_end = 16                        # 16:00 UTC
        self.ny_session_start = 13                          # 13:00 UTC
        self.ny_session_end = 21                            # 21:00 UTC
        self.prefer_london_ny_overlap = True                # Prefer 13:00-16:00 UTC
        
        # ===============================================
        # EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.0015               # Close at +0.15% profit
        self.early_close_loss_pct = -0.003                 # Close at -0.3% loss
        self.max_hold_time_minutes = 120                   # Max 2 hours hold
        self.trailing_stop_enabled = True                  # Enable trailing stops
        self.trailing_stop_distance = 0.001                # 0.1% trailing distance
        
        # ===============================================
        # DATA STORAGE
        # ===============================================
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.volume_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.atr_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.daily_signals = []  # Store all signals for ranking
        self.selected_trades = []  # Quality trades selected
        
        # ===============================================
        # PERFORMANCE TRACKING
        # ===============================================
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        # ===============================================
        # NEWS INTEGRATION
        # ===============================================
        self.news_enabled = NEWS_AVAILABLE and safe_news_integration.enabled if NEWS_AVAILABLE else False
        if self.news_enabled:
            logger.info("✅ News integration enabled - confirming momentum with sentiment")
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
    
    def _calculate_adx(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average Directional Index (simplified)"""
        if len(prices) < period + 1:
            return 0.0
        
        # Simplified ADX calculation
        price_changes = []
        for i in range(1, len(prices)):
            change = abs(prices[i] - prices[i-1])
            price_changes.append(change)
        
        if len(price_changes) < period:
            return 0.0
        
        # Calculate directional movement
        avg_change = np.mean(price_changes[-period:])
        price_std = np.std(prices[-period:])
        
        if price_std == 0:
            return 0.0
        
        # Simplified ADX (normalized)
        adx = min(avg_change / price_std * 100, 100)
        return adx
    
    def _calculate_momentum(self, prices: List[float], period: int = 14) -> float:
        """Calculate momentum score"""
        if len(prices) < period + 1:
            return 0.0
        
        current_price = prices[-1]
        past_price = prices[-period-1]
        
        if past_price == 0:
            return 0.0
        
        momentum = (current_price - past_price) / past_price
        return momentum
    
    def _calculate_volume_score(self, volumes: List[float], period: int = 20) -> float:
        """Calculate volume score"""
        if len(volumes) < period:
            return 0.0
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-period:])
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / avg_volume
        return min(volume_ratio, 2.0) / 2.0  # Normalize to 0-1
    
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
        
        logger.info(f"📈 Selected {len(best_trades)} best momentum trades from {len(self.daily_signals)} signals")
        
        return best_trades
    
    def _generate_momentum_signal(self, instrument: str) -> MomentumSignal:
        """Generate momentum signal"""
        prices = self.price_history.get(instrument, [])
        volumes = self.volume_history.get(instrument, [])
        
        if len(prices) < max(self.momentum_period, self.adx_period):
            return MomentumSignal(instrument, 'NEUTRAL', 0.0, 0.0, 0.0, datetime.now(), 0.0, 0.0)
        
        # Calculate indicators
        momentum_score = self._calculate_momentum(prices, self.momentum_period)
        atr = self._calculate_atr(prices, self.atr_period)
        adx = self._calculate_adx(prices, self.adx_period)
        
        volume_score = 0.5  # Default volume score
        if len(volumes) >= self.volume_period:
            volume_score = self._calculate_volume_score(volumes, self.volume_period)
        
        # Determine trend direction
        if momentum_score > self.min_momentum and adx > self.min_adx:
            trend = 'BULLISH'
            strength = min((momentum_score + adx/100) / 2, 1.0)
        elif momentum_score < -self.min_momentum and adx > self.min_adx:
            trend = 'BEARISH'
            strength = min((abs(momentum_score) + adx/100) / 2, 1.0)
        else:
            trend = 'NEUTRAL'
            strength = 0.0
        
        return MomentumSignal(
            instrument=instrument,
            trend=trend,
            momentum_score=momentum_score,
            volume_score=volume_score,
            strength=strength,
            timestamp=datetime.now(),
            atr=atr,
            adx=adx
        )
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Check session
        if self.only_trade_london_ny and not self._is_london_or_ny_session():
            logger.info("⏰ Skipping trade: outside London/NY sessions")
            return []
        
        trade_signals = []
        
        for instrument, data in market_data.items():
            if instrument not in self.instruments:
                continue
            
            # Update price history
            if instrument not in self.price_history:
                self.price_history[instrument] = []
            
            self.price_history[instrument].append(data.price)
            
            # Update volume history
            if instrument not in self.volume_history:
                self.volume_history[instrument] = []
            
            current_volume = getattr(data, 'volume', 1000000)
            self.volume_history[instrument].append(current_volume)
            
            # Keep only recent data
            if len(self.price_history[instrument]) > 100:
                self.price_history[instrument] = self.price_history[instrument][-100:]
            if len(self.volume_history[instrument]) > 100:
                self.volume_history[instrument] = self.volume_history[instrument][-100:]
            
            # Check minimum data
            if len(self.price_history[instrument]) < max(self.momentum_period, self.adx_period):
                continue
            
            # Generate momentum signal
            momentum_signal = self._generate_momentum_signal(instrument)
            
            # Check signal strength
            if momentum_signal.strength < 0.6:  # Minimum strength threshold
                continue
            
            # Check ADX requirement
            if momentum_signal.adx < self.min_adx:
                continue
            
            # Check momentum requirement
            if abs(momentum_signal.momentum_score) < self.min_momentum:
                continue
            
            # Check volume requirement
            if momentum_signal.volume_score < self.min_volume:
                continue
            
            # Volatility filter
            recent_prices = self.price_history[instrument][-20:]
            volatility = np.std(recent_prices) / np.mean(recent_prices)
            if volatility < self.min_volatility_threshold:
                continue
            
            # Spread filter
            if hasattr(data, 'spread') and data.spread > self.max_spread_threshold:
                continue
            
            # Multiple confirmations check
            confirmations = 0
            if momentum_signal.adx >= self.min_adx:
                confirmations += 1
            if abs(momentum_signal.momentum_score) >= self.min_momentum:
                confirmations += 1
            if momentum_signal.volume_score >= self.min_volume:
                confirmations += 1
            if volatility >= self.min_volatility_threshold:
                confirmations += 1
            if self._is_london_ny_overlap():
                confirmations += 1  # Bonus for overlap session
            
            if confirmations < self.min_confirmations:
                continue
            
            # Generate trade signal
            if momentum_signal.trend in ['BULLISH', 'BEARISH']:
                side = OrderSide.BUY if momentum_signal.trend == 'BULLISH' else OrderSide.SELL
                
                # OPTIMIZED: Enhanced position sizing for JPY pairs (proven winners)
                position_size = 150000 if instrument.endswith('JPY') else 100000
                
                # Calculate stop loss and take profit using ATR
                atr_value = momentum_signal.atr
                
                if side == OrderSide.BUY:
                    stop_loss = data.price - (self.stop_loss_atr * atr_value)
                    take_profit = data.price + (self.take_profit_atr * atr_value)
                else:
                    stop_loss = data.price + (self.stop_loss_atr * atr_value)
                    take_profit = data.price - (self.take_profit_atr * atr_value)
                
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=side,
                    units=position_size,
                    entry_price=data.price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=momentum_signal.strength,
                    strength=momentum_signal.strength,
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
        
        # Quality filtering and ranking
        if trade_signals:
            trade_signals = self._select_best_daily_trades(trade_signals)
            self.daily_trade_count += len(trade_signals)
        
        # News integration (optional, non-breaking)
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
                        logger.info(f"📈 News boost applied to {signal.instrument}: {boost:.2f}x")
                    elif boost < 1.0:
                        logger.info(f"📉 News reduction applied to {signal.instrument}: {boost:.2f}x")
                
            except Exception as e:
                logger.warning(f"⚠️  News integration error: {e}")
        
        return trade_signals
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        return {
            'name': self.name,
            'instruments': self.instruments,
            'daily_trades': self.daily_trade_count,
            'max_daily_trades': self.max_trades_per_day,
            'trades_remaining': self.max_trades_per_day - self.daily_trade_count,
            'parameters': {
                'momentum_period': self.momentum_period,
                'volume_period': self.volume_period,
                'atr_period': self.atr_period,
                'adx_period': self.adx_period,
                'min_adx': self.min_adx,
                'min_momentum': self.min_momentum,
                'min_volume': self.min_volume,
                'stop_loss_atr': self.stop_loss_atr,
                'take_profit_atr': self.take_profit_atr,
                'rr_ratio': self.take_profit_atr / self.stop_loss_atr,
                'max_quality_trades': self.max_daily_quality_trades,
                'early_close_profit_pct': self.early_close_profit_pct,
                'early_close_loss_pct': self.early_close_loss_pct,
                'max_hold_time_minutes': self.max_hold_time_minutes
            },
            'news_enabled': self.news_enabled,
            'last_reset_date': self.last_reset_date.isoformat()
        }
