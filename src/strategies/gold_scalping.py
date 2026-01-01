#!/usr/bin/env python3
"""
Gold Scalping Strategy
Production-ready gold scalping strategy for Google Cloud deployment
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

# Economic indicators integration (optional, non-breaking)
try:
    from ..core.economic_indicators import get_economic_indicators
    ECONOMIC_INDICATORS_AVAILABLE = True
except ImportError:
    ECONOMIC_INDICATORS_AVAILABLE = False

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
    """Production Gold Scalping Strategy"""
    
    def __init__(self):
        """Initialize strategy"""
        self.name = "Gold Scalping"
        self.instruments = ['XAU_USD']
        
        # Strategy parameters - FIXED FOR BETTER ENTRIES (No more chasing!)
        self.min_volatility = 0.00008  # Even higher - only volatile moves
        self.max_spread = 0.6  # TIGHTER - better execution quality
        self.stop_loss_pips = 8  # Keep tight
        self.take_profit_pips = 30  # INCREASED = 1:3.75 R:R (BETTER)
        self.min_signal_strength = 0.70  # VERY HIGH - only best setups
        self.max_trades_per_day = 20  # DRASTICALLY REDUCED (was 245!)
        self.min_trades_today = 0  # NO FORCED TRADES
        # Entry timing improvements
        self.min_time_between_trades_minutes = 30  # Space out trades
        self.require_pullback = True  # WAIT for pullback (don't chase)
        self.pullback_ema_period = 21  # Must pull back to 21 EMA
        self.only_trade_london_ny = True  # High volume sessions only
        # Breakout config: much stricter
        self.breakout_lookback = 15
        self.breakout_threshold = 0.004  # 0.4% move - VERY STRONG only
        self.min_atr_for_entry = 1.5  # Minimum $1.50 ATR required
        # Minimum warm-up prices for any decision-making - REDUCED for faster trading
        self.min_warmup_prices = 2
        
        # Price data storage
        self.price_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        self.volatility_history: Dict[str, List[float]] = {inst: [] for inst in self.instruments}
        
        # Performance tracking
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        self.last_trade_time = None  # Track time between trades
        
        # Per-instrument overrides (primarily min_signal_strength for now)
        self.per_instrument_overrides: Dict[str, Dict[str, float]] = {}
        
        # News integration for gold (checks for Fed, inflation, rate news)
        self.news_enabled = NEWS_AVAILABLE
        if self.news_enabled:
            logger.info("✅ News integration enabled - monitoring gold-related events")
        else:
            logger.info("ℹ️  Trading without news integration (technical signals only)")
        
        # Economic indicators for fundamental analysis
        self.economic_indicators_enabled = ECONOMIC_INDICATORS_AVAILABLE
        if self.economic_indicators_enabled:
            self.economic_service = get_economic_indicators()
            if self.economic_service.enabled:
                logger.info("✅ Economic indicators enabled - CPI, Fed Funds, Real Rates")
                logger.info("   Gold will use: Real Interest Rates, Inflation, Fed Policy")
            else:
                self.economic_indicators_enabled = False
                logger.info("ℹ️  Economic indicators API not available")
        else:
            logger.info("ℹ️  Trading without economic indicators")
        
        logger.info(f"✅ {self.name} strategy initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Stop loss: {self.stop_loss_pips} pips, Take profit: {self.take_profit_pips} pips")
    
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
            logger.info("🔄 Daily trade counters reset")
    
    def _calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate price volatility"""
        if len(prices) < period:
            return 0.0
        
        returns = pd.Series(prices).pct_change().dropna()
        return float(returns.std() * np.sqrt(252 * 1440))  # Annualized volatility
    
    def _calculate_support_resistance(self, prices: List[float], lookback: int = 100) -> Tuple[float, float]:
        """Calculate support and resistance levels"""
        if len(prices) < lookback:
            return prices[-1], prices[-1]
        
        recent_prices = prices[-lookback:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        return support, resistance
    
    def _check_pullback_to_ema(self, prices: List[float]) -> bool:
        """Check if price has pulled back to EMA (better entry)"""
        if len(prices) < self.pullback_ema_period + 5:
            return False
        
        try:
            # Calculate EMA
            ema = self._calculate_ema(prices, self.pullback_ema_period)
            current_price = prices[-1]
            
            # Check if price is near EMA (within 0.1%)
            distance_to_ema = abs(current_price - ema) / ema
            
            # Good pullback = price within 0.1% of EMA
            return distance_to_ema < 0.001
        except Exception:
            return False
    
    def _is_london_or_ny_session(self) -> bool:
        """Check if current time is London or NY session"""
        try:
            from datetime import datetime
            current_hour_utc = datetime.utcnow().hour
            
            # London: 7:00-16:00 UTC
            # NY: 13:00-21:00 UTC
            is_london = 7 <= current_hour_utc < 16
            is_ny = 13 <= current_hour_utc < 21
            
            return is_london or is_ny
        except Exception:
            return True  # If can't determine, allow trading
    
    def _can_trade_now(self) -> bool:
        """Check if enough time has passed since last trade"""
        if not self.last_trade_time:
            return True
        
        try:
            from datetime import datetime, timedelta
            time_since_last = datetime.now() - self.last_trade_time
            min_gap = timedelta(minutes=self.min_time_between_trades_minutes)
            
            return time_since_last >= min_gap
        except Exception:
            return True
    
    def _update_price_history(self, market_data: Dict[str, MarketData]):
        """Update price history for gold"""
        for instrument, data in market_data.items():
            if instrument in self.instruments:
                # Use mid price
                mid_price = (data.bid + data.ask) / 2
                self.price_history[instrument].append(mid_price)
                
                # Keep only last 1000 prices for efficiency
                if len(self.price_history[instrument]) > 1000:
                    self.price_history[instrument] = self.price_history[instrument][-1000:]
                
                # Calculate and store volatility
                volatility = self._calculate_volatility(self.price_history[instrument])
                self.volatility_history[instrument].append(volatility)
                
                if len(self.volatility_history[instrument]) > 100:
                    self.volatility_history[instrument] = self.volatility_history[instrument][-100:]
    
    def _generate_scalping_signals(self, market_data: Dict[str, MarketData]) -> Dict[str, ScalpingSignal]:
        """Generate scalping signals for gold"""
        signals = {}
        
        for instrument in self.instruments:
            if instrument not in market_data:
                continue
            
            data = market_data[instrument]
            prices = self.price_history[instrument]
            
            # Warm-up reduced so strong moves can be acted upon sooner
            if len(prices) < self.min_warmup_prices:
                logger.info(f"⏳ Skipping {instrument}: warm-up ({len(prices)}/{self.min_warmup_prices})")
                continue
            
            # Calculate current volatility
            volatility = self._calculate_volatility(prices)
            
            # Calculate support/resistance
            support, resistance = self._calculate_support_resistance(prices)
            
            # Current price and spread
            current_price = (data.bid + data.ask) / 2
            current_spread = data.ask - data.bid
            
            # Initialize signal
            signal = 'HOLD'
            strength = 0.0
            
            # Check if spread is acceptable
            if current_spread <= self.max_spread:
                # Near support - potential buy
                if abs(current_price - support) / support < 0.0005:  # Within 0.05% of support
                    signal = 'BUY'
                    strength = 1 - (current_price - support) / support
                
                # Near resistance - potential sell
                elif abs(resistance - current_price) / resistance < 0.0005:  # Within 0.05% of resistance
                    signal = 'SELL'
                    strength = 1 - (resistance - current_price) / resistance
            
            signals[instrument] = ScalpingSignal(
                instrument=instrument,
                signal=signal,
                strength=min(1.0, strength),
                timestamp=datetime.now(),
                price_level=current_price,
                volatility=volatility,
                spread=current_spread
            )
        
        return signals

    def _detect_breakout(self, instrument: str) -> Optional[ScalpingSignal]:
        prices = self.price_history.get(instrument, [])
        if len(prices) < max(self.breakout_lookback, 5):
            return None
        start = prices[-self.breakout_lookback]
        end = prices[-1]
        change = (end - start) / start
        if abs(change) >= self.breakout_threshold:
            side = 'BUY' if change > 0 else 'SELL'
            return ScalpingSignal(
                instrument=instrument,
                signal=side,
                strength=1.0,
                timestamp=datetime.now(),
                price_level=end,
                volatility=self._calculate_volatility(prices),
                spread=0.0
            )
        return None
    
    def _generate_trade_signals(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Generate trading signals with IMPROVED ENTRY TIMING.

        NEW: Waits for pullbacks, checks session, spaces out trades
        """
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_trades_per_day:
            return []
        
        # ENTRY IMPROVEMENT: Check if enough time since last trade
        if not self._can_trade_now():
            logger.info(f"⏰ Skipping trade: minimum {self.min_time_between_trades_minutes}min gap required")
            return []
        
        # ENTRY IMPROVEMENT: Only trade London/NY sessions (high volume)
        if self.only_trade_london_ny and not self._is_london_or_ny_session():
            logger.info("⏰ Skipping trade: outside London/NY sessions")
            return []
        
        # Update price history
        self._update_price_history(market_data)
        
        # Immediate impulse/momentum trigger: react to sharp move quickly
        try:
            inst = 'XAU_USD'
            if inst in self.instruments and inst in market_data:
                prices = self.price_history.get(inst, [])
                if len(prices) >= self.min_warmup_prices:
                    lookback = min(10, len(prices) - 1) if len(prices) > 1 else 0
                    if lookback >= 3:
                        start = prices[-lookback]
                        end = prices[-1]
                        change = (end - start) / start if start != 0 else 0.0
                        current_spread = market_data[inst].ask - market_data[inst].bid
                        if abs(change) >= 0.003 and current_spread <= 2.0:  # >= 0.3% move with acceptable spread
                            side = OrderSide.BUY if change > 0 else OrderSide.SELL
                            stop_loss = end * (1 - self.stop_loss_pips/10000) if side == OrderSide.BUY else end * (1 + self.stop_loss_pips/10000)
                            take_profit = end * (1 + self.take_profit_pips/10000) if side == OrderSide.BUY else end * (1 - self.take_profit_pips/10000)
                            self.daily_trade_count += 1
                            logger.info(f"⚡ Impulse trigger fired for {inst}: {side.value} change={change:.4f} spread={current_spread:.2f}")
                            return [TradeSignal(
                                instrument=inst,
                                side=side,
                                units=20000,  # 0.2 lots - INCREASED for better profits
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                strategy_name=self.name,
                                confidence=1.0
                            )]
                        elif abs(change) >= 0.003 and current_spread > 2.0:
                            logger.info(f"🚫 Impulse suppressed: spread too wide ({current_spread:.2f} > 2.0)")
        except Exception as e:
            logger.warning(f"⚠️ Impulse trigger check failed: {e}")
        
        # Generate base scalping signals (may be HOLD initially)
        base_signals = self._generate_scalping_signals(market_data)

        def momentum_direction(prices: List[float], lookback: int = 10) -> str:
            if len(prices) < max(lookback, 3):
                return 'BUY'  # default bias
            return 'BUY' if prices[-1] > prices[-lookback] else 'SELL'

        # Progressive relaxation levels - QUALITY FOCUSED
        levels = [
            { 'min_strength': float(self.min_signal_strength), 'min_vol': float(self.min_volatility), 'max_spread': float(self.max_spread), 'force': False },
            { 'min_strength': 0.50, 'min_vol': 0.00004, 'max_spread': 1.0, 'force': False },
            { 'min_strength': 0.45, 'min_vol': 0.00003, 'max_spread': 1.2, 'force': False },
        ]

        # Always start from highest quality level (no forced trades)
        start_idx = 0

        for idx in range(start_idx, len(levels)):
            cfg = levels[idx]
            trade_signals: List[TradeSignal] = []
            for instrument, sig in base_signals.items():
                prices = self.price_history.get(instrument, [])
                # Optionally fabricate a direction under force
                if sig.signal == 'HOLD' and cfg['force']:
                    sig.signal = momentum_direction(prices)
                    sig.strength = max(sig.strength, cfg['min_strength'])
                    logger.info(f"🚀 RELAXED/FORCED TRADE: {instrument} {sig.signal} (lvl {idx+1})")

                # Apply relaxed filters
                if sig.signal not in ['BUY', 'SELL']:
                    continue
                if sig.strength < cfg['min_strength'] and not cfg['force']:
                    continue
                if sig.volatility < cfg['min_vol'] and not cfg['force']:
                    continue
                if sig.spread > cfg['max_spread'] and not cfg['force']:
                    logger.info(f"🚫 Suppressed {instrument}: spread {sig.spread:.2f} > {cfg['max_spread']:.2f} (lvl {idx+1})")
                    continue

                # Construct order
                if sig.signal == 'BUY':
                    stop_loss = sig.price_level * (1 - self.stop_loss_pips/10000)
                    take_profit = sig.price_level * (1 + self.take_profit_pips/10000)
                    side = OrderSide.BUY
                else:
                    stop_loss = sig.price_level * (1 + self.stop_loss_pips/10000)
                    take_profit = sig.price_level * (1 - self.take_profit_pips/10000)
                    side = OrderSide.SELL

                trade_signals.append(TradeSignal(
                    instrument=instrument,
                    side=side,
                    units=7500,  # 0.075 lots for $600 risk (demo limit)
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy_name=self.name,
                    confidence=max(sig.strength, cfg['min_strength'])
                ))

                # ENTRY IMPROVEMENT: Check pullback requirement
                if self.require_pullback and trade_signals:
                    filtered_signals = []
                    for signal in trade_signals:
                        prices = self.price_history.get(signal.instrument, [])
                        if self._check_pullback_to_ema(prices):
                            filtered_signals.append(signal)
                            logger.info(f"✅ Pullback confirmed for {signal.instrument}")
                        else:
                            logger.info(f"⏰ Waiting for pullback on {signal.instrument}")
                    trade_signals = filtered_signals
                
                if trade_signals:
                    self.daily_trade_count += len(trade_signals)
                    self.last_trade_time = datetime.now()  # Update last trade time
                    logger.info(f"🎯 Relaxation level {idx+1} produced {len(trade_signals)} signal(s)")
                    return trade_signals

        # Final: breakout entry if present
        bo = self._detect_breakout('XAU_USD')
        if bo and bo.signal in ['BUY', 'SELL']:
            side = OrderSide.BUY if bo.signal == 'BUY' else OrderSide.SELL
            stop_loss = bo.price_level * (1 - self.stop_loss_pips/10000) if side == OrderSide.BUY else bo.price_level * (1 + self.stop_loss_pips/10000)
            take_profit = bo.price_level * (1 + self.take_profit_pips/10000) if side == OrderSide.BUY else bo.price_level * (1 - self.take_profit_pips/10000)
            self.daily_trade_count += 1
            logger.info("⚡ Breakout trigger fired for XAU_USD")
            return [TradeSignal(
                instrument='XAU_USD',
                side=side,
                units=20000,  # 0.2 lots - INCREASED for better profits
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_name=self.name,
                confidence=1.0
            )]

        # ECONOMIC INDICATORS: Fundamental analysis for gold
        if self.economic_indicators_enabled and trade_signals:
            try:
                fundamental = self.economic_service.get_gold_fundamental_score()
                
                logger.info(f"📊 Gold Fundamentals: {fundamental['recommendation']} "
                          f"(score: {fundamental['score']:.2f})")
                
                for signal in trade_signals:
                    # Apply fundamental boost/reduction
                    if fundamental['score'] > 0.3 and signal.side == OrderSide.BUY:
                        signal.confidence *= 1.25  # Strong bullish fundamentals
                        logger.info(f"💰 Strong econ boost: Real rate favors gold BUY")
                    elif fundamental['score'] > 0 and signal.side == OrderSide.BUY:
                        signal.confidence *= 1.15  # Moderate bullish
                        logger.info(f"💰 Econ boost: Fundamentals support gold BUY")
                    elif fundamental['score'] < -0.3 and signal.side == OrderSide.SELL:
                        signal.confidence *= 1.25  # Strong bearish fundamentals
                    elif fundamental['score'] < 0 and signal.side == OrderSide.SELL:
                        signal.confidence *= 1.15
                    
                    # Cap confidence at 1.0
                    signal.confidence = min(1.0, signal.confidence)
                
            except Exception as e:
                logger.warning(f"⚠️  Economic indicators failed: {e}")
        
        # GOLD-SPECIFIC: Pause during high-impact gold events (Fed, rates, inflation)
        if self.news_enabled and NEWS_AVAILABLE and trade_signals:
            try:
                # Gold is sensitive to rate news - pause during high impact events
                if safe_news_integration.should_pause_trading(['XAU_USD']):
                    logger.warning("🚫 Gold trading paused - high-impact monetary news")
                    return []
                
                # Boost signals that align with gold sentiment
                news_analysis = safe_news_integration.get_news_analysis(['XAU_USD'])
                
                for signal in trade_signals:
                    boost = safe_news_integration.get_news_boost_factor(
                        signal.side.value,
                        ['XAU_USD']
                    )
                    
                    original_confidence = signal.confidence
                    signal.confidence = original_confidence * boost
                    
                    if boost != 1.0:
                        logger.info(f"📰 Gold news factor: {original_confidence:.2f} → "
                                  f"{signal.confidence:.2f} (sentiment: "
                                  f"{news_analysis.get('overall_sentiment', 0):.2f})")
                
            except Exception as e:
                logger.warning(f"⚠️  News check failed (trading anyway): {e}")
        
        # Return signals (may be empty)
        return trade_signals if trade_signals else []
    
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
                'min_volatility': self.min_volatility,
                'max_spread': self.max_spread,
                'stop_loss_pips': self.stop_loss_pips,
                'take_profit_pips': self.take_profit_pips,
                'min_signal_strength': self.min_signal_strength
            },
            'last_update': datetime.now().isoformat()
        }

# Global strategy instance
gold_scalping = GoldScalpingStrategy()

def get_gold_scalping_strategy() -> GoldScalpingStrategy:
    """Get the global Gold Scalping strategy instance"""
    return gold_scalping

# Instance method for overrides
def _set_per_instrument_overrides(self, mapping: Dict[str, Dict[str, float]]) -> None:
    self.per_instrument_overrides = mapping or {}
    logger.info(f"✅ {self.name} overrides updated for {len(self.per_instrument_overrides)} instruments")

if not hasattr(GoldScalpingStrategy, 'set_per_instrument_overrides'):
    setattr(GoldScalpingStrategy, 'set_per_instrument_overrides', _set_per_instrument_overrides)
