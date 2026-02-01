#!/usr/bin/env python3
"""
Ultra Strict Forex Trading Strategy - OPTIMIZED VERSION
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
class EMASignal:
    """EMA crossover signal"""
    instrument: str
    ema_3: float
    ema_8: float
    ema_21: float
    signal: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-1
    timestamp: datetime

@dataclass
class MomentumSignal:
    """Momentum confirmation signal"""
    instrument: str
    rsi: float
    macd: float
    macd_signal: float
    momentum: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    strength: float  # 0-1
    timestamp: datetime

class UltraStrictForexStrategy:
    """OPTIMIZED Ultra Strict Forex Trading Strategy - MAX 10 TRADES/DAY"""
    
    def __init__(self):
        """Initialize optimized strategy"""
        self.name = "Ultra Strict Forex - Optimized"
        self.instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        
        # ===============================================
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY
        # ===============================================
        self.ema_periods = [3, 8, 21]
        self.stop_loss_pct = 0.004    # OPTIMIZED: 0.4% stop loss
        self.take_profit_pct = 0.020  # OPTIMIZED: 2.0% take profit = 1:5.0 R:R
        self.min_signal_strength = 0.85  # OPTIMIZED: Very high quality
        self.max_trades_per_day = 10  # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0     # NO FORCED TRADES - only high-quality setups
        
        # ===============================================
        # ENHANCED MULTI-TIMEFRAME CONFIRMATION
        # ===============================================
        self.require_trend_alignment = True
        self.trend_lookback_long = 50
        self.trend_lookback_short = 20
        self.trend_timeframes = ['5M', '15M', '1H', '4H']  # ALL must align
        self.trend_strength_min = 0.75  # Strong trend required
        
        # ===============================================
        # OPTIMIZED QUALITY FILTERS
        # ===============================================
        self.max_daily_quality_trades = 5    # Top 5 quality trades per day
        self.quality_score_threshold = 0.90  # Very high quality threshold
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
        self.min_volatility_threshold = 0.00006  # Higher volatility required
        self.max_spread_threshold = 0.8      # Reasonable spreads
        self.require_volume_confirmation = True
        self.min_volume_multiplier = 1.5     # 1.5x average volume
        
        # ===============================================
        # EARLY CLOSURE SYSTEM
        # ===============================================
        self.early_close_profit_pct = 0.0015    # Close at +0.15% profit
        self.early_close_loss_pct = -0.003      # Close at -0.3% loss
        self.max_hold_time_minutes = 120        # Max 2 hours hold
        self.trailing_stop_enabled = True       # Enable trailing stops
        self.trailing_stop_distance = 0.001     # 0.1% trailing distance
        
        # ===============================================
        # DATA STORAGE
        # ===============================================
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.ema_history: Dict[str, Dict[int, List[float]]] = {
            inst: {period: [] for period in self.ema_periods} for inst in self.instruments
        }
        self.signals: List[TradeSignal] = []
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
            logger.info("✅ News integration enabled for quality filtering")
        else:
            logger.info("ℹ️  Trading without news integration (technical signals only)")
        
        logger.info(f"✅ {self.name} strategy initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Max trades/day: {self.max_trades_per_day}")
        logger.info(f"📊 R:R ratio: 1:{self.take_profit_pct/self.stop_loss_pct:.1f}")
    
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
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """Calculate MACD"""
        if len(prices) < 26:
            return 0.0, 0.0
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Simplified signal line (9-period EMA of MACD)
        macd_values = [ema_12 - ema_26]
        signal_line = self._calculate_ema(macd_values, 9)
        
        return macd_line, signal_line
    
    def _check_higher_timeframe_trend(self, prices: List[float], signal_direction: str) -> bool:
        """Check if signal aligns with higher timeframe trend"""
        if len(prices) < max(self.trend_lookback_long, self.trend_lookback_short):
            return True  # Not enough data, allow trade
        
        # Long-term trend (50 bars)
        long_trend_prices = prices[-self.trend_lookback_long:]
        long_trend = (long_trend_prices[-1] - long_trend_prices[0]) / long_trend_prices[0]
        
        # Short-term trend (20 bars)
        short_trend_prices = prices[-self.trend_lookback_short:]
        short_trend = (short_trend_prices[-1] - short_trend_prices[0]) / short_trend_prices[0]
        
        # Check alignment
        if signal_direction == 'BUY':
            return long_trend > 0.0001 and short_trend > 0.0001  # Both bullish
        elif signal_direction == 'SELL':
            return long_trend < -0.0001 and short_trend < -0.0001  # Both bearish
        
        return True
    
    def _is_london_or_ny_session(self) -> bool:
        """Check if current time is London or NY session"""
        now = datetime.now()
        current_hour = now.hour
        
        # London session: 07:00-16:00 UTC
        london_session = 7 <= current_hour < 16
        
        # NY session: 13:00-21:00 UTC
        ny_session = 13 <= current_hour < 21
        
        return london_session or ny_session
    
    def _check_volume_confirmation(self, instrument: str, current_volume: float) -> bool:
        """Check if volume confirms the signal"""
        # Simplified volume check - in real implementation, you'd have volume data
        return current_volume > (self.min_volume_multiplier * 1000000)  # 1.5M base volume
    
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
    
    def _generate_ema_signal(self, instrument: str) -> EMASignal:
        """Generate EMA crossover signal"""
        prices = self.price_history.get(instrument, [])
        if len(prices) < max(self.ema_periods):
            return EMASignal(instrument, 0, 0, 0, 'HOLD', 0.0, datetime.now())
        
        ema_3 = self._calculate_ema(prices, 3)
        ema_8 = self._calculate_ema(prices, 8)
        ema_21 = self._calculate_ema(prices, 21)
        
        # Store EMA values
        if instrument not in self.ema_history:
            self.ema_history[instrument] = {period: [] for period in self.ema_periods}
        
        self.ema_history[instrument][3].append(ema_3)
        self.ema_history[instrument][8].append(ema_8)
        self.ema_history[instrument][21].append(ema_21)
        
        # Determine signal
        if ema_3 > ema_8 > ema_21:
            signal = 'BUY'
            strength = min((ema_3 - ema_21) / ema_21, 1.0)
        elif ema_3 < ema_8 < ema_21:
            signal = 'SELL'
            strength = min((ema_21 - ema_3) / ema_21, 1.0)
        else:
            signal = 'HOLD'
            strength = 0.0
        
        return EMASignal(instrument, ema_3, ema_8, ema_21, signal, strength, datetime.now())
    
    def _generate_momentum_signal(self, instrument: str) -> MomentumSignal:
        """Generate momentum confirmation signal"""
        prices = self.price_history.get(instrument, [])
        if len(prices) < 26:
            return MomentumSignal(instrument, 50, 0, 0, 'NEUTRAL', 0.0, datetime.now())
        
        rsi = self._calculate_rsi(prices)
        macd, macd_signal = self._calculate_macd(prices)
        
        # Determine momentum
        if rsi > 60 and macd > macd_signal:
            momentum = 'BULLISH'
            strength = min((rsi - 50) / 50, 1.0)
        elif rsi < 40 and macd < macd_signal:
            momentum = 'BEARISH'
            strength = min((50 - rsi) / 50, 1.0)
        else:
            momentum = 'NEUTRAL'
            strength = 0.0
        
        return MomentumSignal(instrument, rsi, macd, macd_signal, momentum, strength, datetime.now())
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
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
            if len(self.price_history[instrument]) > 200:
                self.price_history[instrument] = self.price_history[instrument][-200:]
            
            # Generate signals
            ema_signal = self._generate_ema_signal(instrument)
            momentum_signal = self._generate_momentum_signal(instrument)
            
            # Session filter
            if self.only_trade_london_ny and not self._is_london_or_ny_session():
                continue
            
            # Volatility filter
            if len(self.price_history[instrument]) >= 20:
                recent_prices = self.price_history[instrument][-20:]
                volatility = np.std(recent_prices) / np.mean(recent_prices)
                if volatility < self.min_volatility_threshold:
                    continue
            
            # Spread filter
            if hasattr(data, 'spread') and data.spread > self.max_spread_threshold:
                continue
            
            # Volume confirmation
            if self.require_volume_confirmation:
                current_volume = getattr(data, 'volume', 1000000)
                if not self._check_volume_confirmation(instrument, current_volume):
                    continue
            
            # Generate BUY signals
            if (ema_signal.signal == 'BUY' and ema_signal.strength >= min_strength and
                (momentum_signal.momentum == 'BULLISH' or momentum_signal.momentum == 'NEUTRAL')):
                
                # Multi-timeframe confirmation
                if not self._check_higher_timeframe_trend(self.price_history[instrument], 'BUY'):
                    logger.info(f"⏰ Skipping {instrument} BUY: Higher TF not aligned")
                    continue
                
                # Multiple confirmations check
                confirmations = 0
                if ema_signal.strength >= min_strength:
                    confirmations += 1
                if momentum_signal.strength >= 0.3:
                    confirmations += 1
                if volatility >= self.min_volatility_threshold:
                    confirmations += 1
                
                if confirmations < self.min_confirmations:
                    continue
                
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.BUY,
                    units=100000,
                    entry_price=data.price,
                    stop_loss=data.price * (1 - self.stop_loss_pct),
                    take_profit=data.price * (1 + self.take_profit_pct),
                    confidence=ema_signal.strength * momentum_signal.strength,
                    strength=ema_signal.strength,
                    timestamp=datetime.now(),
                    strategy_name=self.name
                )
                trade_signals.append(trade_signal)
            
            # Generate SELL signals
            elif (ema_signal.signal == 'SELL' and ema_signal.strength >= min_strength and
                  (momentum_signal.momentum == 'BEARISH' or momentum_signal.momentum == 'NEUTRAL')):
                
                # Multi-timeframe confirmation
                if not self._check_higher_timeframe_trend(self.price_history[instrument], 'SELL'):
                    logger.info(f"⏰ Skipping {instrument} SELL: Higher TF not aligned")
                    continue
                
                # Multiple confirmations check
                confirmations = 0
                if ema_signal.strength >= min_strength:
                    confirmations += 1
                if momentum_signal.strength >= 0.3:
                    confirmations += 1
                if volatility >= self.min_volatility_threshold:
                    confirmations += 1
                
                if confirmations < self.min_confirmations:
                    continue
                
                trade_signal = TradeSignal(
                    instrument=instrument,
                    side=OrderSide.SELL,
                    units=100000,
                    entry_price=data.price,
                    stop_loss=data.price * (1 + self.stop_loss_pct),
                    take_profit=data.price * (1 - self.take_profit_pct),
                    confidence=ema_signal.strength * momentum_signal.strength,
                    strength=ema_signal.strength,
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
                # Check if high-impact negative news should pause trading
                if safe_news_integration.should_pause_trading(self.instruments):
                    logger.warning("🚫 Trading paused due to high-impact negative news")
                    return []
                
                # Apply news sentiment boost/reduction to signals
                news_analysis = safe_news_integration.get_news_analysis(self.instruments)
                
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
                logger.warning(f"⚠️  News integration error (continuing without news): {e}")
        
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
                'ema_periods': self.ema_periods,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'min_signal_strength': self.min_signal_strength,
                'rr_ratio': self.take_profit_pct / self.stop_loss_pct,
                'max_quality_trades': self.max_daily_quality_trades,
                'early_close_profit_pct': self.early_close_profit_pct,
                'early_close_loss_pct': self.early_close_loss_pct,
                'max_hold_time_minutes': self.max_hold_time_minutes
            },
            'news_enabled': self.news_enabled,
            'last_reset_date': self.last_reset_date.isoformat()
        }
