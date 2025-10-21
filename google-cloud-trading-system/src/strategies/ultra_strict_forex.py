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
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY (FIXED OCT 16, 2025)
        # ===============================================
        self.ema_periods = [3, 8, 21]
        self.stop_loss_pct = 0.004    # OPTIMIZED: 0.4% stop loss
        self.take_profit_pct = 0.020  # OPTIMIZED: 2.0% take profit = 1:5.0 R:R
        self.min_signal_strength = 0.20  # LOWERED FOR REAL MARKET: 20% minimum (was 0.25)
        self.max_trades_per_day = 10  # OPTIMIZED: Max 10 trades per day
        self.min_trades_today = 0     # NO FORCED TRADES - only high-quality setups
        
        # ===============================================
        # SIMPLIFIED TREND CONFIRMATION (FIXED OCT 16, 2025)
        # ===============================================
        self.require_trend_alignment = True
        self.trend_lookback_long = 50
        self.trend_lookback_short = 20
        self.trend_timeframes = ['15M']  # Just 1 timeframe (was 4 - impossible!)
        self.trend_strength_min = 0.50  # Moderate trend OK (was 0.75)
        
        # ===============================================
        # REALISTIC QUALITY FILTERS (FIXED OCT 16, 2025)
        # ===============================================
        self.max_daily_quality_trades = 5    # Top 5 quality trades per day
        self.quality_score_threshold = 0.50  # LOWERED FOR REAL MARKET (was 0.60)
        self.daily_trade_ranking = True      # Rank and select best
        self.require_multiple_confirmations = True
        self.min_confirmations = 2           # 2 confirmations (was 3)
        
        # ===============================================
        # ENHANCED ENTRY CONDITIONS
        # ===============================================
        self.only_trade_london_ny = True     # High volume sessions only
        self.london_session_start = 7        # 07:00 UTC
        self.london_session_end = 16         # 16:00 UTC
        self.ny_session_start = 13           # 13:00 UTC
        self.ny_session_end = 21             # 21:00 UTC
        self.min_volatility_threshold = 0.00001  # REALISTIC: Low bar (was 0.00003)
        self.max_spread_threshold = 3.0      # REALISTIC: Wider spreads OK (was 1.5)
        self.require_volume_confirmation = False  # DISABLED: Too restrictive (was True)
        self.min_volume_multiplier = 1.2     # 1.2x average volume (was 1.5)
        
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
        
        # Pre-fill price history for immediate trading
        self._prefill_price_history()
    
    def _prefill_price_history(self):
        """Pre-fill price history with recent data so strategy is ready immediately"""
        try:
            from ..core.historical_fetcher import get_historical_fetcher
            fetcher = get_historical_fetcher()
            
            logger.info("📥 Pre-filling price history from OANDA...")
            
            # Get 50 bars of M15 data (12.5 hours of history)
            for instrument in self.instruments:
                try:
                    candles = fetcher.client.get_candles(
                        instrument=instrument,
                        count=50,
                        granularity='M15'
                    )
                    
                    if candles:
                        for candle in candles:
                            # Handle OANDA bid/ask format instead of mid
                            if 'mid' in candle and isinstance(candle['mid'], dict):
                                close_price = float(candle['mid'].get('c', 0))
                            elif 'bid' in candle and isinstance(candle['bid'], dict):
                                close_price = float(candle['bid'].get('c', 0))
                            elif 'ask' in candle and isinstance(candle['ask'], dict):
                                close_price = float(candle['ask'].get('c', 0))
                            else:
                                continue
                                
                            if close_price > 0:
                                self.price_history[instrument].append(close_price)
                        
                        logger.info(f"  ✅ {instrument}: {len(self.price_history[instrument])} bars loaded")
                except Exception as e:
                    logger.warning(f"  ⚠️  Could not prefill {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY TO TRADE!")
        except Exception as e:
            logger.warning(f"⚠️  Could not prefill price history: {e}")
    
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
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        # Use pandas for EMA calculation
        df = pd.Series(prices)
        return df.ewm(span=period, adjust=False).mean().iloc[-1]
    
    def _check_higher_timeframe_trend(self, prices: List[float], signal_direction: str) -> bool:
        """Check if signal aligns with higher timeframe trend"""
        if len(prices) < max(self.trend_lookback_long, self.trend_lookback_short):
            # FIXED OCT 14, 2025: Changed from True to False
            # Reason: Multi-timeframe confirmation should REJECT trades when insufficient data,
            # not allow them. This prevents taking wrong-direction trades during warmup period.
            return False  # Not enough data, REJECT trade
        
        try:
            # Calculate EMAs for trend analysis
            long_term_ema = self._calculate_ema(prices, self.trend_lookback_long)
            short_term_ema = self._calculate_ema(prices, self.trend_lookback_short)
            current_price = prices[-1]
            
            # Determine higher TF trend
            if current_price > long_term_ema and short_term_ema > long_term_ema:
                higher_tf_trend = 'BUY'
            elif current_price < long_term_ema and short_term_ema < long_term_ema:
                higher_tf_trend = 'SELL'
            else:
                higher_tf_trend = 'NEUTRAL'
            
            # Signal must align with higher TF
            if signal_direction == higher_tf_trend:
                logger.info(f"✅ Multi-timeframe alignment confirmed: {signal_direction}")
                return True
            else:
                logger.info(f"⏰ Multi-timeframe conflict: Signal={signal_direction}, HTF={higher_tf_trend}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Multi-timeframe check failed: {e}")
            return False
    
    def _is_london_or_ny_session(self) -> bool:
        """Check if current time is London or NY session"""
        now = datetime.now()
        current_hour = now.hour
        
        # London session: 07:00-16:00 UTC
        london_session = self.london_session_start <= current_hour < self.london_session_end
        
        # NY session: 13:00-21:00 UTC
        ny_session = self.ny_session_start <= current_hour < self.ny_session_end
        
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
    
    def _calculate_ema_signals(self) -> Dict[str, EMASignal]:
        """Calculate EMA crossover signals"""
        ema_signals = {}
        
        for instrument in self.instruments:
            if len(self.price_history[instrument]) < 8:  # Reduced from 21 to 8
                continue
            
            prices = self.price_history[instrument]
            
            # Calculate EMAs
            ema_3 = self._calculate_ema(prices, 3)
            ema_8 = self._calculate_ema(prices, 8)
            ema_21 = self._calculate_ema(prices, 21)
            
            # Determine signal and strength
            signal = 'HOLD'
            strength = 0.0
            
            # Bullish: EMA 3 > EMA 8 > EMA 21
            if ema_3 > ema_8 > ema_21:
                signal = 'BUY'
                strength = min(1.0, (ema_3 - ema_21) / ema_21)
            
            # Bearish: EMA 3 < EMA 8 < EMA 21
            elif ema_3 < ema_8 < ema_21:
                signal = 'SELL'
                strength = min(1.0, (ema_21 - ema_3) / ema_21)
            
            ema_signals[instrument] = EMASignal(
                instrument=instrument,
                ema_3=ema_3,
                ema_8=ema_8,
                ema_21=ema_21,
                signal=signal,
                strength=strength,
                timestamp=datetime.now()
            )
        
        return ema_signals
    
    def _calculate_momentum_signals(self) -> Dict[str, MomentumSignal]:
        """Calculate momentum confirmation signals"""
        momentum_signals = {}
        
        for instrument in self.instruments:
            if len(self.price_history[instrument]) < 14:
                continue
            
            prices = self.price_history[instrument]
            
            # Calculate RSI
            df = pd.Series(prices)
            delta = df.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            
            # Calculate MACD
            ema_12 = df.ewm(span=12).mean()
            ema_26 = df.ewm(span=26).mean()
            macd = ema_12 - ema_26
            macd_signal = macd.ewm(span=9).mean()
            
            macd_val = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0
            macd_sig = macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else 0
            
            # Determine momentum and strength
            momentum = 'NEUTRAL'
            strength = 0.0
            
            # Bullish momentum: RSI > 50, MACD > Signal
            if rsi > 50 and macd_val > macd_sig:
                momentum = 'BULLISH'
                strength = min(1.0, (rsi - 50) / 50 + (macd_val - macd_sig) / abs(macd_sig) if macd_sig != 0 else 0)
            
            # Bearish momentum: RSI < 50, MACD < Signal
            elif rsi < 50 and macd_val < macd_sig:
                momentum = 'BEARISH'
                strength = min(1.0, (50 - rsi) / 50 + (macd_sig - macd_val) / abs(macd_sig) if macd_sig != 0 else 0)
            
            momentum_signals[instrument] = MomentumSignal(
                instrument=instrument,
                rsi=rsi,
                macd=macd_val,
                macd_signal=macd_sig,
                momentum=momentum,
                strength=strength,
                timestamp=datetime.now()
            )
        
        return momentum_signals
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals with enhanced quality filters"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Update price history
        self._update_price_history(market_data)
        
        # Calculate signals
        ema_signals = self._calculate_ema_signals()
        momentum_signals = self._calculate_momentum_signals()
        
        trade_signals = []
        min_strength = self.min_signal_strength
        
        # Session filter
        if self.only_trade_london_ny and not self._is_london_or_ny_session():
            return []
        
        for instrument in self.instruments:
            if instrument not in ema_signals or instrument not in momentum_signals:
                continue
            
            ema_signal = ema_signals[instrument]
            momentum_signal = momentum_signals[instrument]
            
            # Volatility filter
            if len(self.price_history[instrument]) >= 20:
                recent_prices = self.price_history[instrument][-20:]
                volatility = np.std(recent_prices) / np.mean(recent_prices)
                if volatility < self.min_volatility_threshold:
                    continue
            
            # Spread filter
            if instrument in market_data:
                current_data = market_data[instrument]
                spread = current_data.ask - current_data.bid
                if spread > self.max_spread_threshold:
                    continue
                
                # Volume confirmation (DISABLED OCT 16 - was too restrictive)
                # if self.require_volume_confirmation:
                #     current_volume = getattr(current_data, 'volume', 1000000)
                #     if not self._check_volume_confirmation(instrument, current_volume):
                #         continue
            
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
                    entry_price=current_data.ask,
                    stop_loss=current_data.ask * (1 - self.stop_loss_pct),
                    take_profit=current_data.ask * (1 + self.take_profit_pct),
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
                    entry_price=current_data.bid,
                    stop_loss=current_data.bid * (1 + self.stop_loss_pct),
                    take_profit=current_data.bid * (1 - self.take_profit_pct),
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
                'ema_periods': self.ema_periods,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'min_signal_strength': self.min_signal_strength
            },
            'last_update': datetime.now().isoformat()
        }

# Global strategy instance
ultra_strict_forex = UltraStrictForexStrategy()

def get_ultra_strict_forex_strategy() -> UltraStrictForexStrategy:
    """Get the global Ultra Strict Forex strategy instance"""
    return ultra_strict_forex
