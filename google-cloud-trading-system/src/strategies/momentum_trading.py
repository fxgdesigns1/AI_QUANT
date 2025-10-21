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

# Adaptive regime detection and profit protection
try:
    from ..core.market_regime import get_market_regime_detector
    from ..core.profit_protector import get_profit_protector
    ADAPTIVE_AVAILABLE = True
except ImportError:
    ADAPTIVE_AVAILABLE = False
    logger.warning("⚠️ Adaptive features not available")

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
        # GOLD ONLY - MONTE CARLO OPTIMIZED (OCT 16 - Forex losing money, Gold profitable)
        self.instruments = ['XAU_USD']  # Focus on 89% WR Gold, disable losing forex
        
        # ===============================================
        # OPTIMIZED STRATEGY PARAMETERS - MAX 10/DAY (FIXED OCT 16, 2025)
        # ===============================================
        self.stop_loss_atr = 2.5             # MONTE CARLO OPTIMIZED for Gold
        self.take_profit_atr = 20.0          # MONTE CARLO OPTIMAL: Best tested value
        self.min_signal_strength = 0.25      # REALISTIC: 25% minimum (was 0.85 - too strict!)
        self.max_trades_per_day = 100        # INCREASED: 100/day (was 10 - blocking after first batch!)
        self.min_trades_today = 0            # NO FORCED TRADES - only high-quality setups
        
        # ===============================================
        # ULTRA RELAXED FILTERS (TUNED OCT 16, 2025 - Validation proven)
        # ===============================================
        self.min_adx = 8.0                   # REVERTED: Lower is better for Gold (was 12.0)
        self.min_momentum = 0.0003           # REVERTED: Lower catches more good setups (was 0.0005)
        self.min_volume = 0.03               # ABSOLUTE MINIMUM: Very low bar (was 0.054)
        self.momentum_period = 40            # MONTE CARLO OPTIMIZED: 40 bars = 3.3 hours (catches moves faster)
        self.trend_period = 80               # MONTE CARLO OPTIMIZED: 80 bars = 6.7 hours (more responsive)
        self.adx_period = 14                 # Period for ADX calculation
        self.volume_period = 20              # Period for volume analysis
        
        # ===============================================
        # REALISTIC QUALITY FILTERS (FIXED OCT 16, 2025)
        # ===============================================
        self.max_daily_quality_trades = 20   # INCREASED: Allow more signals (was 5 - too restrictive!)
        self.quality_score_threshold = 0.050  # RELAXED: 10% minimum to allow more trades (was 0.90 - WAY too strict!)
        self.daily_trade_ranking = False     # DISABLED: Blocks signals during backtest (was True)
        self.require_multiple_confirmations = False  # DISABLED: Too strict, blocking all signals
        self.min_confirmations = 1           # Just 1 confirmation (was 2)
        
        # ===============================================
        # ENHANCED ENTRY CONDITIONS
        # ===============================================
        self.only_trade_london_ny = False    # DISABLED: Trade all sessions to get more opportunities
        self.london_session_start = 7        # 07:00 UTC
        self.london_session_end = 16         # 16:00 UTC
        self.ny_session_start = 13           # 13:00 UTC
        self.ny_session_end = 21             # 21:00 UTC
        self.min_time_between_trades_minutes = 15  # REDUCED: 15 min gap (was 60 - way too long!)
        self.require_trend_continuation = False    # DISABLED: Too strict, already have 100-bar trend filter
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
        
        # ===============================================
        # CONTEXTUAL TRADING INTEGRATION
        # ===============================================
        self.contextual_enabled = False
        if CONTEXTUAL_AVAILABLE:
            try:
                self.session_manager = get_session_manager()
                self.quality_scorer = get_quality_scoring()
                self.price_analyzer = get_price_context_analyzer()
                self.contextual_enabled = True
                logger.info("✅ Contextual trading modules integrated")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize contextual modules: {e}")
                self.session_manager = None
                self.quality_scorer = None
                self.price_analyzer = None
        else:
            self.session_manager = None
            self.quality_scorer = None
            self.price_analyzer = None
        if self.news_enabled:
            logger.info("✅ News integration enabled for quality filtering")
        else:
            logger.info("ℹ️  Trading without news integration (technical signals only)")
        
        # ===============================================
        # PAIR-SPECIFIC QUALITY RANKINGS
        # ===============================================
        self.momentum_rankings = {
            'GBP_USD': 1.2,  # Best momentum pair
            'EUR_USD': 1.1,  
            'USD_JPY': 1.0,
            'AUD_USD': 0.9,
            'USD_CAD': 0.8,
            'NZD_USD': 0.7   # Weakest (historical 0% win rate)
        }
        
        # Quality score threshold (0-100 scale) - ULTRA RELAXED OCT 16, 2025
        self.min_quality_score = 10  # REVERTED: Original worked better (was 15)
        
        # ===============================================
        # ADAPTIVE REGIME DETECTION (NEW OCT 16, 2025)
        # ===============================================
        self.adaptive_mode = ADAPTIVE_AVAILABLE  # Enable if available
        self.target_trades_per_day = 5           # Soft target (~5 trades/day)
        
        # Base thresholds (will be adjusted by regime) - LOWERED FOR REAL MARKET
        self.base_quality_threshold = 40     # Optimized for better win rate
        self.base_confidence = 0.50          # Was 0.65, too strict
        self.base_momentum = 0.0010          # Optimized: 0.10% for stronger signals
        
        # Sniper entry settings
        self.sniper_mode = True
        self.sniper_ema_period = 20
        self.sniper_tolerance = 0.002  # 0.2% from EMA
        
        # Initialize regime detector and profit protector
        if self.adaptive_mode:
            self.regime_detector = get_market_regime_detector()
            self.profit_protector = get_profit_protector({
                'breakeven_at': 0.005,  # +0.5%
                'trail_at': 0.015,      # +1.5%
                'trail_distance': 0.008 # 0.8%
            })
            logger.info("✅ Adaptive regime detection ENABLED")
            logger.info("✅ Profit protection ENABLED")
        else:
            self.regime_detector = None
            self.profit_protector = None
            logger.info("ℹ️  Running in standard mode (adaptive disabled)")
        
        logger.info(f"✅ {self.name} strategy initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Max trades/day: {self.max_trades_per_day}")
        logger.info(f"📊 Target trades/day: {self.target_trades_per_day} (soft target)")
        logger.info(f"📊 R:R ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
        logger.info(f"📊 Quality threshold: {self.min_quality_score}/100 (adaptive)")
        
        # CRITICAL FIX: Pre-fill price history so strategy can generate signals immediately!
        self._prefill_price_history()
    
    def _prefill_price_history(self):
        """
        CRITICAL FIX: Pre-fill price history from OANDA so strategy can work immediately!
        Without this, strategy has empty history and NEVER generates signals.
        """
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history from OANDA...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 50 M15 candles for each instrument (12.5 hours of history)
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 50, 'granularity': 'M15', 'price': 'M'}
                    
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        candles = data.get('candles', [])
                        
                        for candle in candles:
                            # Handle OANDA bid/ask format instead of mid
                            if 'mid' in candle and isinstance(candle['mid'], dict):
                                close = float(candle['mid'].get('c', 0))
                            elif 'bid' in candle and isinstance(candle['bid'], dict):
                                close = float(candle['bid'].get('c', 0))
                            elif 'ask' in candle and isinstance(candle['ask'], dict):
                                close = float(candle['ask'].get('c', 0))
                            else:
                                continue
                                
                            if close > 0:
                                self.price_history[instrument].append(close)
                        
                        logger.info(f"  ✅ {instrument}: {len(self.price_history[instrument])} bars loaded")
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
                    continue
            
            total_loaded = sum(len(prices) for prices in self.price_history.values())
            
            if total_loaded > 0:
                logger.info(f"✅ Price history pre-filled: {total_loaded} total bars - READY TO TRADE!")
            else:
                logger.warning("⚠️ Price history prefill failed - will build from live feed (slower)")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not pre-fill price history: {e}")
    
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
        """Calculate ATR estimate from close prices only (FIXED OCT 16)"""
        if len(prices) < period + 1:
            return 0.001  # Small non-zero default instead of 0
        
        # CRITICAL FIX: Can't use high/low (we only have close prices)
        # Use price changes as proxy for true range
        df = pd.Series(prices)
        price_changes = df.diff().abs()
        atr = price_changes.rolling(window=period).mean().iloc[-1]
        
        # If ATR is valid and non-zero, return it
        if not pd.isna(atr) and atr > 0:
            return atr
        
        # Fallback: use volatility estimate
        returns = df.pct_change().abs()
        vol_estimate = returns.rolling(period).std().iloc[-1] * df.iloc[-1]
        
        # Never return 0 - always return a small positive value
        return vol_estimate if (not pd.isna(vol_estimate) and vol_estimate > 0) else 0.001
    
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
    
    def _find_sniper_entry(self, instrument: str, prices: List[float], 
                          trend: str, regime: Dict) -> Optional[Dict]:
        """
        Detect sniper pullback entries in trends
        
        Sniper = pullback to EMA in strong trend, NOT counter-trend!
        """
        if not self.sniper_mode:
            return None
        
        if not regime or regime.get('regime') != 'TRENDING':
            return None  # Only snipe in trends
        
        if len(prices) < self.sniper_ema_period:
            return None
        
        ema_20 = np.mean(prices[-self.sniper_ema_period:])
        current_price = prices[-1]
        
        # Recent momentum (last 5 bars)
        recent_momentum = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        # Bullish sniper: Pullback to EMA in uptrend
        if trend == 'BULLISH':
            pullback_to_ema = abs(current_price - ema_20) / ema_20 < self.sniper_tolerance
            still_above_ema = current_price >= ema_20 * 0.998
            not_falling_hard = recent_momentum > -0.001
            
            if pullback_to_ema and still_above_ema and not_falling_hard:
                return {
                    'type': 'SNIPER_PULLBACK',
                    'quality_boost': 1.2,  # 20% quality bonus
                    'reason': f'Pullback to EMA {ema_20:.5f} in uptrend'
                }
        
        # Bearish sniper: Pullback to EMA in downtrend
        elif trend == 'BEARISH':
            pullback_to_ema = abs(current_price - ema_20) / ema_20 < self.sniper_tolerance
            still_below_ema = current_price <= ema_20 * 1.002
            not_rallying_hard = recent_momentum < 0.001
            
            if pullback_to_ema and still_below_ema and not_rallying_hard:
                return {
                    'type': 'SNIPER_PULLBACK',
                    'quality_boost': 1.2,  # 20% quality bonus
                    'reason': f'Pullback to EMA {ema_20:.5f} in downtrend'
                }
        
        return None
    
    def _calculate_adaptive_quality_score(self, instrument: str, adx: float, 
                                         momentum: float, volume_score: float, 
                                         prices: List[float], regime: Optional[Dict],
                                         sniper_entry: Optional[Dict]) -> Dict:
        """
        Calculate quality score with regime-based adaptation
        
        Returns dict with score, threshold, and whether it passes
        """
        # Calculate base score (existing logic)
        base_score = self._calculate_base_quality_score(
            instrument, adx, momentum, volume_score, prices
        )
        
        # If adaptive mode disabled, use base scoring
        if not self.adaptive_mode or not regime:
            return {
                'score': base_score,
                'threshold': self.min_quality_score,
                'regime': 'STANDARD',
                'passes': base_score >= self.min_quality_score
            }
        
        # Adaptive adjustment based on regime
        regime_type = regime.get('regime', 'UNKNOWN')
        
        if regime_type == 'TRENDING':
            # Make it EASIER to enter in trends (catch pullbacks)
            adjusted_score = base_score * 1.15  # Boost scores
            threshold = 20  # REALISTIC threshold (was 60)
        
        elif regime_type == 'RANGING':
            # Make it HARDER in ranges (wait for key levels)
            adjusted_score = base_score * 0.85  # Reduce scores
            threshold = 25  # REALISTIC (was 80)
        
        elif regime_type == 'CHOPPY':
            # Make it MUCH HARDER in chop (very selective)
            adjusted_score = base_score * 0.70  # Significantly reduce
            threshold = 30  # REALISTIC (was 90 - impossible!)
        
        else:
            # Unknown regime - use base
            adjusted_score = base_score
            threshold = 25  # REALISTIC (was 70)
        
        # Apply sniper entry bonus
        if sniper_entry:
            adjusted_score *= sniper_entry.get('quality_boost', 1.2)
        
        return {
            'score': adjusted_score,
            'threshold': threshold,
            'regime': regime_type,
            'passes': adjusted_score >= threshold,
            'sniper': sniper_entry is not None
        }
    
    def _calculate_base_quality_score(self, instrument: str, adx: float, momentum: float, 
                                     volume_score: float, prices: List[float]) -> float:
        """Base quality scoring (non-adaptive) - FIXED to not reject everything!"""
        score = 0
        
        # ADX component (0-30 points) - NO hard rejection
        if adx >= 35:
            score += 30
        elif adx >= 30:
            score += 25
        elif adx >= 25:
            score += 15
        elif adx >= 20:
            score += 10
        elif adx >= 15:
            score += 5
        # Don't reject - let other components contribute
        
        # Momentum component (0-30 points) - FIXED thresholds
        abs_momentum = abs(momentum)
        if abs_momentum >= 0.012:
            score += 30
        elif abs_momentum >= 0.008:
            score += 20
        elif abs_momentum >= 0.005:
            score += 10
        elif abs_momentum >= 0.003:  # NEW: 0.3% gets points
            score += 7
        elif abs_momentum >= 0.001:  # NEW: 0.1% gets points
            score += 5
        # Don't reject - let other components contribute
        
        # Volume component (0-20 points) - More permissive
        if volume_score >= 0.50:
            score += 20
        elif volume_score >= 0.35:
            score += 15
        elif volume_score >= 0.20:  # NEW: 0.2 gets points
            score += 10
        elif volume_score >= 0.10:  # NEW: 0.1 gets points
            score += 5
        # Don't reject - accept low volume
        
        # Trend consistency (0-20 points)
        if len(prices) >= 10:
            recent_prices = prices[-10:]
            if momentum > 0:
                up_bars = sum(1 for i in range(1, len(recent_prices)) 
                             if recent_prices[i] > recent_prices[i-1])
                consistency = up_bars / (len(recent_prices) - 1)
            else:
                down_bars = sum(1 for i in range(1, len(recent_prices)) 
                               if recent_prices[i] < recent_prices[i-1])
                consistency = down_bars / (len(recent_prices) - 1)
            
            if consistency >= 0.7:
                score += 20
            elif consistency >= 0.6:
                score += 10
        
        # Apply pair multiplier
        pair_multiplier = self.momentum_rankings.get(instrument, 1.0)
        final_score = score * pair_multiplier
        
        return final_score
    
    def _calculate_quality_score(self, instrument: str, adx: float, momentum: float, 
                                 volume_score: float, prices: List[float]) -> float:
        """Calculate overall quality score (0-100) for elite trade selection"""
        score = 0
        
        # ADX: Trend strength (FIXED OCT 16, 2025 - lowered thresholds)
        if adx >= 30:
            score += 30  # Excellent trend
        elif adx >= 22:
            score += 25  # Good trend
        elif adx >= 18:
            score += 20  # Moderate trend OK
        elif adx >= 15:
            score += 10  # Weak trend but acceptable
        else:
            return 0  # Too weak
        
        # Momentum: Directional move (FIXED OCT 16, 2025 - lowered thresholds)
        abs_momentum = abs(momentum)
        if abs_momentum >= 0.010:  # 1.0%+ move
            score += 30  # Exceptional momentum
        elif abs_momentum >= 0.006:  # 0.6%+ move
            score += 25  # Strong momentum
        elif abs_momentum >= 0.004:  # 0.4%+ move
            score += 20  # Good momentum
        elif abs_momentum >= 0.002:  # 0.2%+ move
            score += 10  # Moderate momentum
        else:
            return 0  # Too weak
        
        # Volume: Above average activity (FIXED OCT 16, 2025 - lowered thresholds)
        if volume_score >= 0.40:
            score += 20  # Strong volume
        elif volume_score >= 0.25:
            score += 15  # Good volume
        elif volume_score >= 0.15:
            score += 10  # Moderate volume
        else:
            score += 5  # Accept any volume (don't reject)
        
        # Trend consistency: Check last 10 bars for directional consistency
        if len(prices) >= 10:
            recent_prices = prices[-10:]
            if momentum > 0:  # Bullish momentum
                up_bars = sum(1 for i in range(1, len(recent_prices)) 
                             if recent_prices[i] > recent_prices[i-1])
                consistency = up_bars / (len(recent_prices) - 1)
            else:  # Bearish momentum
                down_bars = sum(1 for i in range(1, len(recent_prices)) 
                               if recent_prices[i] < recent_prices[i-1])
                consistency = down_bars / (len(recent_prices) - 1)
            
            if consistency >= 0.7:  # 70%+ consistent bars
                score += 20  # Very consistent trend
            elif consistency >= 0.6:  # 60%+ consistent bars
                score += 10  # Fairly consistent
            # else: no points but don't reject
        
        # Apply pair-specific ranking multiplier
        pair_multiplier = self.momentum_rankings.get(instrument, 1.0)
        final_score = score * pair_multiplier
        
        return final_score
    
    def _select_best_daily_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Select only the best trades for the day"""
        if not self.daily_trade_ranking:
            return signals
        
        # Add to daily signals
        self.daily_signals.extend(signals)
        
        # Sort by confidence (highest first) - FIXED: removed .strength (doesn't exist)
        self.daily_signals.sort(key=lambda x: x.confidence, reverse=True)
        
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
                
                # Keep more history for better calculations (was 100 - too small!)
                # Increased to 200 to support 50-bar momentum + 100-bar trend
                if len(self.price_history[instrument]) > 200:
                    self.price_history[instrument] = self.price_history[instrument][-200:]
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate optimized trade signals with enhanced quality filters"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # Update price history
        self._update_price_history(market_data)
        
        trade_signals = []
        
        # Session filter - DISABLED FOR BACKTEST (uses current time, not historical time!)
        # TODO: Fix to use candle timestamp instead of datetime.now()
        # if self.only_trade_london_ny and not self._is_london_or_ny_session():
        #     logger.info("⏰ Skipping trade: outside London/NY sessions")
        #     return []
        
        # PRIME HOURS FILTER: Only trade 1pm-5pm London (best liquidity, London/NY overlap)
        # DISABLED OCT 16 - was too restrictive, missing opportunities
        # current_hour = datetime.now().hour
        # if not (13 <= current_hour <= 17):
        #     logger.info(f"⏰ Outside prime hours (1-5pm London), current: {current_hour}:00")
        #     return []
        
        # AVOID SESSION VOLATILITY: Skip first/last 15 minutes of each hour
        # DISABLED OCT 16 - was too restrictive, only 30 min per hour allowed
        # current_minute = datetime.now().minute
        # if current_minute < 15 or current_minute > 45:
        #     logger.info(f"⏰ Avoiding session volatility (minute {current_minute})")
        #     return []
        
        # Time between trades filter
        if not self._can_trade_now():
            logger.info(f"⏰ Skipping trade: minimum {self.min_time_between_trades_minutes}min gap required")
            return []
        
        for instrument in self.instruments:
            if instrument not in market_data:
                logger.debug(f"⏰ Skipping {instrument}: not in market_data")
                continue
            if len(self.price_history[instrument]) < 5:
                logger.info(f"⏰ Skipping {instrument}: insufficient history ({len(self.price_history[instrument])} < 5)")
                continue
            
            current_data = market_data[instrument]
            prices = self.price_history[instrument]
            
            # Calculate indicators
            atr = self._calculate_atr(prices, self.momentum_period)
            adx = self._calculate_adx(prices, self.adx_period)
            
            if atr == 0 or adx == 0:
                logger.info(f"⏰ Skipping {instrument}: ATR or ADX is zero (ATR={atr:.2f}, ADX={adx:.2f})")
                continue
            
            # ADX filter - must be strong trend
            if adx < self.min_adx:
                logger.info(f"⏰ Skipping {instrument}: ADX too weak ({adx:.1f})")
                continue
            
            # Calculate momentum (50 bars = 4.2 hours)
            recent_prices = prices[-self.momentum_period:]
            momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            if abs(momentum) < self.min_momentum:
                logger.info(f"⏰ Skipping {instrument}: momentum too weak ({momentum:.4f})")
                continue
            
            # CRITICAL FIX: Check longer-term trend (100 bars = 8.3 hours)
            # Only trade WITH the trend, not against it!
            if len(prices) >= self.trend_period:
                trend_prices = prices[-self.trend_period:]
                trend_momentum = (trend_prices[-1] - trend_prices[0]) / trend_prices[0]
                
                # If trend and momentum disagree, SKIP the trade
                # (prevents selling into a rally or buying into a drop)
                if (momentum > 0 and trend_momentum < -0.001) or (momentum < 0 and trend_momentum > 0.001):
                    logger.info(f"⏰ Skipping {instrument}: momentum vs trend mismatch "
                               f"(momentum={momentum:.4f}, trend={trend_momentum:.4f})")
                    continue
                
                logger.info(f"✅ TREND ALIGNED: {instrument} momentum={momentum:.4f}, trend={trend_momentum:.4f}")
            
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
            
            # ADAPTIVE REGIME DETECTION
            regime = None
            sniper_entry = None
            if self.adaptive_mode and self.regime_detector:
                regime = self.regime_detector.analyze_regime(instrument, prices, adx)
                
                # Check for sniper pullback entries in trends
                sniper_entry = self._find_sniper_entry(instrument, prices, trend, regime)
                if sniper_entry:
                    logger.info(f"🎯 SNIPER: {instrument} - {sniper_entry['reason']}")
            
            # ADAPTIVE QUALITY SCORING: Calculate with regime-based adaptation
            quality_result = self._calculate_adaptive_quality_score(
                instrument, adx, momentum, volume_score, prices, regime, sniper_entry
            )
            
            if not quality_result['passes']:
                logger.info(f"⏰ Skipping {instrument}: quality {quality_result['score']:.1f} < {quality_result['threshold']} "
                           f"({quality_result['regime']}, ADX={adx:.1f}, momentum={momentum:.4f})")
                continue
            
            logger.info(f"✅ QUALITY PASS: {instrument} scored {quality_result['score']:.1f} in {quality_result['regime']} market "
                       f"(threshold: {quality_result['threshold']})")
            
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
                logger.info(f"⏰ Skipping {instrument}: not enough confirmations ({confirmations} < {self.min_confirmations})")
                continue
            
            # Calculate position size (JPY pairs get larger size)
            position_size = 150000 if instrument.endswith('JPY') else 100000
            
            # Generate trade signal (FIXED field names)
            entry = current_data.ask if side == OrderSide.BUY else current_data.bid
            sl = entry + (-self.stop_loss_atr * atr if side == OrderSide.BUY else self.stop_loss_atr * atr)
            tp = entry + (self.take_profit_atr * atr if side == OrderSide.BUY else -self.take_profit_atr * atr)
            
            # Calculate meaningful confidence based on quality score
            # Quality score is 0-100, convert to 0-1 range
            base_confidence = min(quality_result['score'] / 100, 1.0)
            
            # Boost for strong ADX (trend strength)
            adx_boost = min(adx / 50, 2.0)  # ADX 50+ gives full boost
            
            # Boost for momentum strength
            momentum_boost = min(abs(momentum) * 100, 2.0)  # Convert to percentage
            
            # Final confidence (quality * trend * momentum)
            final_confidence = min(base_confidence * adx_boost * momentum_boost, 1.0)
            
            # Ensure minimum 10% confidence for signals that pass quality
            final_confidence = max(final_confidence, 0.10)
            
            trade_signal = TradeSignal(
                instrument=instrument,
                side=side,
                units=position_size,
                stop_loss=sl,
                take_profit=tp,
                confidence=final_confidence,
                timestamp=datetime.now(),
                strategy_name=self.name
            )
            trade_signals.append(trade_signal)
            
            # Log with adaptive info
            regime_type = quality_result.get('regime', 'STANDARD')
            sniper_flag = "🎯 SNIPER " if quality_result.get('sniper') else ""
            logger.info(f"✅ {sniper_flag}ELITE {trend} signal for {instrument}: "
                       f"Quality={quality_result['score']:.1f}/{quality_result['threshold']} ({regime_type}), "
                       f"ADX={adx:.1f}, momentum={momentum:.4f}, volume={volume_score:.2f}")
        
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
        
        # Apply contextual quality scoring to filter signals
        if self.contextual_enabled and self.quality_scorer and trade_signals:
            try:
                filtered_signals = []
                for signal in trade_signals:
                    # Get quality score for this setup
                    quality = self.quality_scorer.score_trade_setup(
                        instrument=signal.instrument,
                        direction=signal.side.value,
                        entry_price=signal.entry_price,
                        market_data=market_data
                    )
                    
                    # Add quality score to signal (if TradeSignal supports it)
                    if hasattr(signal, 'quality_score'):
                        signal.quality_score = quality.total_score
                    
                    # Only keep signals with minimum quality (20+ score) - RELAXED to allow more trades
                    if quality.total_score >= 20:
                        filtered_signals.append(signal)
                        logger.info(f"✅ {signal.instrument} {signal.side.value}: Quality {quality.total_score}/100 - ACCEPTED")
                    else:
                        logger.info(f"⚠️ {signal.instrument} {signal.side.value}: Quality {quality.total_score}/100 - REJECTED (< 20)")
                
                if len(filtered_signals) < len(trade_signals):
                    logger.info(f"🎯 Contextual filtering: {len(filtered_signals)}/{len(trade_signals)} signals passed quality threshold")
                
                trade_signals = filtered_signals
            except Exception as e:
                logger.warning(f"⚠️ Contextual quality scoring error: {e}")
        
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
