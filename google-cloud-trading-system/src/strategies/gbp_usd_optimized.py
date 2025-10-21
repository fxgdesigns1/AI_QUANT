#!/usr/bin/env python3
"""
GBP/USD Optimized Strategies - TOP 3 PERFORMING STRATEGIES
Based on optimization results from October 2, 2025
Real backtest data: 3+ years, 9,642+ trades
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ..core.order_manager import TradeSignal, OrderSide, get_order_manager
from ..core.data_feed import MarketData, get_data_feed

# News integration for GBP economic data (ADDED OCT 14, 2025)
try:
    from ..core.news_integration import safe_news_integration
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False
    import logging
    logging.warning("⚠️ News integration not available - trading without news filter")


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
class OptimizedSignal:
    """Optimized trading signal with performance metrics"""
    instrument: str
    ema_3: float
    ema_12: float
    rsi: float
    atr: float
    signal: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-1
    confidence: float  # 0-1
    timestamp: datetime
    strategy_rank: int

class GBP_USD_Optimized_Strategy:
    """Base class for optimized GBP/USD strategies"""
    
    def __init__(self, rank: int, strategy_params: Dict):
        """Initialize optimized strategy"""
        self.rank = rank
        self.name = f"GBP_USD_5m_Strategy_Rank_{rank}"
        self.instrument = 'GBP_USD'
        
        # Strategy-specific parameters
        self.ema_fast = strategy_params.get('ema_fast_period', 3)
        self.ema_slow = strategy_params.get('ema_slow_period', 12)
        self.rsi_period = strategy_params.get('rsi_period', 14)
        self.rsi_oversold = strategy_params.get('rsi_oversold', 20)
        self.rsi_overbought = strategy_params.get('rsi_overbought', 80)
        self.atr_period = strategy_params.get('atr_period', 14)
        self.atr_multiplier = strategy_params.get('atr_multiplier', 1.5)
        self.risk_reward_ratio = strategy_params.get('take_profit_ratio', 3.0)
        
        # Performance targets (from backtest)
        self.target_sharpe = strategy_params.get('target_sharpe', 35.0)
        self.target_win_rate = strategy_params.get('target_win_rate', 80.0)
        self.max_drawdown_limit = strategy_params.get('max_drawdown_limit', 0.006)
        
        # Risk management
        self.max_risk_per_trade = strategy_params.get('max_risk_per_trade', 0.015)
        self.max_positions = strategy_params.get('max_positions', 5)
        self.max_daily_trades = strategy_params.get('max_daily_trades', 100)
        
        # Data storage
        self.price_history: List[float] = []
        self.ema_history: Dict[int, List[float]] = {self.ema_fast: [], self.ema_slow: []}
        self.rsi_history: List[float] = []
        self.atr_history: List[float] = []
        self.signals: List[TradeSignal] = []
        
        # Performance tracking
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        # Trading sessions (from backtest analysis)
        self.london_start = 8    # 08:00 UTC
        self.london_end = 17     # 17:00 UTC
        self.ny_start = 13       # 13:00 UTC  
        self.ny_end = 20         # 20:00 UTC
        
        # News integration (ADDED OCT 14, 2025)
        self.news_enabled = NEWS_AVAILABLE and safe_news_integration.enabled if NEWS_AVAILABLE else False
        if self.news_enabled:
            logger.info("✅ News integration enabled for GBP trading protection")
        else:
            logger.warning("⚠️ Trading without news integration - CAUTION on UK data releases")
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Target Sharpe: {self.target_sharpe}, Win Rate: {self.target_win_rate}%")
        logger.info(f"📊 RSI: {self.rsi_oversold}/{self.rsi_overbought}, ATR: {self.atr_multiplier}x")
    
    def _reset_daily_counters(self):
        """Reset daily counters if new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = current_date
            logger.info("🔄 Daily counters reset")
    
    def _is_trading_session(self) -> bool:
        """Check if current time is optimal trading session"""
        now = datetime.now()
        current_hour = now.hour
        
        # London session: 08:00-17:00 UTC
        london_session = self.london_start <= current_hour < self.london_end
        
        # NY session: 13:00-20:00 UTC  
        ny_session = self.ny_start <= current_hour < self.ny_end
        
        return london_session or ny_session
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        df = pd.Series(prices)
        return df.ewm(span=period, adjust=False).mean().iloc[-1]
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        df = pd.Series(prices)
        delta = df.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range (simplified)"""
        if len(prices) < period + 1:
            return 0.0001  # Default small value
        
        df = pd.Series(prices)
        # Simplified ATR calculation using price volatility
        returns = df.pct_change().dropna()
        volatility = returns.std()
        return volatility * df.iloc[-1] if volatility > 0 else 0.0001
    
    def _update_indicators(self, market_data: MarketData):
        """Update all technical indicators"""
        # Use mid price
        mid_price = (market_data.bid + market_data.ask) / 2
        self.price_history.append(mid_price)
        
        # Keep only last 100 prices for efficiency
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
        
        # Calculate EMAs
        if len(self.price_history) >= self.ema_slow:
            ema_fast = self._calculate_ema(self.price_history, self.ema_fast)
            ema_slow = self._calculate_ema(self.price_history, self.ema_slow)
            
            self.ema_history[self.ema_fast].append(ema_fast)
            self.ema_history[self.ema_slow].append(ema_slow)
            
            # Keep only last 50 values
            if len(self.ema_history[self.ema_fast]) > 50:
                self.ema_history[self.ema_fast] = self.ema_history[self.ema_fast][-50:]
                self.ema_history[self.ema_slow] = self.ema_history[self.ema_slow][-50:]
        
        # Calculate RSI
        if len(self.price_history) >= self.rsi_period + 1:
            rsi = self._calculate_rsi(self.price_history, self.rsi_period)
            self.rsi_history.append(rsi)
            
            if len(self.rsi_history) > 50:
                self.rsi_history = self.rsi_history[-50:]
        
        # Calculate ATR
        if len(self.price_history) >= self.atr_period + 1:
            atr = self._calculate_atr(self.price_history, self.atr_period)
            self.atr_history.append(atr)
            
            if len(self.atr_history) > 50:
                self.atr_history = self.atr_history[-50:]
    
    def _generate_signal(self, market_data: MarketData) -> Optional[OptimizedSignal]:
        """Generate optimized trading signal"""
        if len(self.ema_history[self.ema_fast]) < 2 or len(self.rsi_history) < 1 or len(self.atr_history) < 1:
            return None
        
        # Get current values
        ema_fast_current = self.ema_history[self.ema_fast][-1]
        ema_fast_previous = self.ema_history[self.ema_fast][-2]
        ema_slow_current = self.ema_history[self.ema_slow][-1]
        ema_slow_previous = self.ema_history[self.ema_slow][-2]
        rsi_current = self.rsi_history[-1]
        atr_current = self.atr_history[-1]
        
        # Check for EMA crossover
        fast_above_slow = ema_fast_current > ema_slow_current
        fast_was_below = ema_fast_previous <= ema_slow_previous
        fast_below_slow = ema_fast_current < ema_slow_current
        fast_was_above = ema_fast_previous >= ema_slow_previous
        
        signal = 'HOLD'
        strength = 0.0
        confidence = 0.0
        
        # BUY Signal: EMA fast crosses above EMA slow + RSI not overbought
        if fast_above_slow and fast_was_below and rsi_current < self.rsi_overbought:
            signal = 'BUY'
            # Calculate strength based on EMA separation and RSI
            ema_separation = (ema_fast_current - ema_slow_current) / ema_slow_current
            rsi_strength = (self.rsi_overbought - rsi_current) / self.rsi_overbought
            strength = min(1.0, ema_separation * 100 + rsi_strength * 0.5)
            confidence = min(1.0, strength * 0.8 + 0.2)  # Base confidence 20%
            
        # SELL Signal: EMA fast crosses below EMA slow + RSI not oversold  
        elif fast_below_slow and fast_was_above and rsi_current > self.rsi_oversold:
            signal = 'SELL'
            # Calculate strength based on EMA separation and RSI
            ema_separation = (ema_slow_current - ema_fast_current) / ema_slow_current
            rsi_strength = (rsi_current - self.rsi_oversold) / (100 - self.rsi_oversold)
            strength = min(1.0, ema_separation * 100 + rsi_strength * 0.5)
            confidence = min(1.0, strength * 0.8 + 0.2)  # Base confidence 20%
        
        if signal != 'HOLD':
            return OptimizedSignal(
                instrument=self.instrument,
                ema_3=ema_fast_current,
                ema_12=ema_slow_current,
                rsi=rsi_current,
                atr=atr_current,
                signal=signal,
                strength=strength,
                confidence=confidence,
                timestamp=datetime.now(),
                strategy_rank=self.rank
            )
        
        return None
    
    def _create_trade_signal(self, optimized_signal: OptimizedSignal, market_data: MarketData) -> TradeSignal:
        """Create TradeSignal from OptimizedSignal"""
        # Calculate stop loss and take profit
        if optimized_signal.signal == 'BUY':
            entry_price = market_data.ask
            stop_loss = entry_price - (optimized_signal.atr * self.atr_multiplier)
            take_profit = entry_price + (optimized_signal.atr * self.atr_multiplier * self.risk_reward_ratio)
        else:  # SELL
            entry_price = market_data.bid
            stop_loss = entry_price + (optimized_signal.atr * self.atr_multiplier)
            take_profit = entry_price - (optimized_signal.atr * self.atr_multiplier * self.risk_reward_ratio)
        
        return TradeSignal(
            instrument=self.instrument,
            side=OrderSide.BUY if optimized_signal.signal == 'BUY' else OrderSide.SELL,
            units=100000,  # Standard lot size
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=optimized_signal.confidence,
            strength=optimized_signal.strength,
            timestamp=datetime.now(),
            strategy_name=self.name
        )
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate trading signals"""
        try:
            self._reset_daily_counters()
            
            # Check for high-impact GBP news (ADDED OCT 14, 2025)
            if self.news_enabled and NEWS_AVAILABLE:
                try:
                    if safe_news_integration.should_pause_trading([self.instrument]):
                        logger.warning(f"🚫 {self.name} - Trading paused due to major {self.instrument} news event")
                        return []
                except Exception as e:
                    logger.warning(f"⚠️ News check failed: {e}, continuing without news filter")
            
            # Check daily trade limit
            if self.daily_trade_count >= self.max_daily_trades:
                return []
            
            # Check if it's our instrument
            if self.instrument not in market_data:
                return []
            
            current_data = market_data[self.instrument]
            
            # Check trading session
            if not self._is_trading_session():
                return []
            
            # Update indicators
            self._update_indicators(current_data)
            
            # Generate signal
            optimized_signal = self._generate_signal(current_data)
            
            if optimized_signal and optimized_signal.confidence >= 0.3:  # Minimum confidence threshold
                trade_signal = self._create_trade_signal(optimized_signal, current_data)
                self.signals.append(trade_signal)
                self.daily_trade_count += 1
                
                logger.info(f"🎯 {self.name} generated {optimized_signal.signal} signal")
                logger.info(f"   📈 Confidence: {optimized_signal.confidence:.2f}, Strength: {optimized_signal.strength:.2f}")
                logger.info(f"   📊 RSI: {optimized_signal.rsi:.1f}, ATR: {optimized_signal.atr:.5f}")
                
                return [trade_signal]
            
            return []
            
        except Exception as e:
            logger.error(f"❌ {self.name} analysis error: {e}")
            return []
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        self._reset_daily_counters()
        
        return {
            'name': self.name,
            'rank': self.rank,
            'instrument': self.instrument,
            'daily_trades': self.daily_trade_count,
            'max_daily_trades': self.max_daily_trades,
            'trades_remaining': self.max_daily_trades - self.daily_trade_count,
            'parameters': {
                'ema_fast': self.ema_fast,
                'ema_slow': self.ema_slow,
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'atr_multiplier': self.atr_multiplier,
                'risk_reward_ratio': self.risk_reward_ratio
            },
            'targets': {
                'sharpe_ratio': self.target_sharpe,
                'win_rate': self.target_win_rate,
                'max_drawdown': self.max_drawdown_limit
            },
            'last_update': datetime.now().isoformat()
        }

    def scan_for_signal(self, candles_data, current_price):
        """Quick scan for auto-trading scanner - SNIPER QUALITY ENTRIES ONLY"""
        try:
            self._reset_daily_counters()
            
            # Daily trade limit check
            if self.daily_trade_count >= self.max_daily_trades:
                return None
            
            # Trading session check (sniper timing)
            if not self._is_trading_session():
                return None
            
            # Data validation
            if not candles_data or 'candles' not in candles_data:
                return None
            
            candles = candles_data.get('candles', [])
            if len(candles) < self.ema_slow + 5:  # Need extra candles for confirmation
                return None
            
            # Extract prices from candles
            prices = []
            for c in candles:
                if 'mid' in c:
                    prices.append(float(c['mid']['c']))
                elif 'c' in c:
                    prices.append(float(c['c']))
            
            if len(prices) < self.ema_slow + 5:
                return None
            
            # Update price history
            self.price_history = prices[-100:]
            
            # Calculate indicators
            ema_fast = self._calculate_ema(self.price_history, self.ema_fast)
            ema_slow = self._calculate_ema(self.price_history, self.ema_slow)
            rsi = self._calculate_rsi(self.price_history, self.rsi_period)
            atr = self._calculate_atr(self.price_history, self.atr_period)
            
            # Store indicator history
            self.ema_history[self.ema_fast].append(ema_fast)
            self.ema_history[self.ema_slow].append(ema_slow)
            self.rsi_history.append(rsi)
            self.atr_history.append(atr)
            
            # Need at least 3 data points for crossover confirmation
            if len(self.ema_history[self.ema_fast]) < 3:
                return None
            
            # Get current and previous EMA values
            ema_fast_curr = self.ema_history[self.ema_fast][-1]
            ema_fast_prev = self.ema_history[self.ema_fast][-2]
            ema_fast_prev2 = self.ema_history[self.ema_fast][-3]
            ema_slow_curr = self.ema_history[self.ema_slow][-1]
            ema_slow_prev = self.ema_history[self.ema_slow][-2]
            ema_slow_prev2 = self.ema_history[self.ema_slow][-3]  # Need for proper crossover confirmation
            
            # ===================================================================
            # SNIPER ENTRY CONDITIONS - VERY STRICT
            # ===================================================================
            
            # Calculate price volatility (for quality filter)
            recent_prices = self.price_history[-20:]
            price_volatility = np.std(recent_prices) / np.mean(recent_prices)
            
            # Minimum volatility required (avoid ranging markets)
            min_volatility = 0.00005  # 0.005%
            if price_volatility < min_volatility:
                return None
            
            # Calculate spread quality
            spread = abs(current_price.ask - current_price.bid)
            max_spread = 0.00030  # 3 pips maximum
            if spread > max_spread:
                return None
            
            # Calculate EMA separation (strength)
            ema_separation = abs(ema_fast_curr - ema_slow_curr) / ema_slow_curr
            min_separation = 0.0001  # Minimum 0.01% separation for strong signal
            
            # Check RSI momentum alignment
            if len(self.rsi_history) >= 3:
                rsi_curr = self.rsi_history[-1]
                rsi_prev = self.rsi_history[-2]
                rsi_momentum = rsi_curr - rsi_prev
            else:
                return None
            
            signal = None
            
            # ===================================================================
            # BUY SIGNAL: Clean EMA crossover + RSI confirmation + momentum
            # ===================================================================
            if (ema_fast_curr > ema_slow_curr and           # Fast above slow (NOW)
                ema_fast_prev <= ema_slow_prev and          # Crossover just happened
                ema_fast_prev2 < ema_slow_prev2 and         # Confirm upward direction
                rsi < self.rsi_overbought and               # Not overbought
                rsi_momentum > 0 and                        # RSI rising (momentum)
                ema_separation >= min_separation):          # Strong enough signal
                
                # Calculate confidence score (sniper quality)
                confidence = 0.0
                confidence += min(0.4, ema_separation * 1000)  # EMA strength (max 40%)
                confidence += min(0.3, (self.rsi_overbought - rsi) / 100)  # RSI room (max 30%)
                confidence += min(0.2, rsi_momentum / 10)  # Momentum (max 20%)
                confidence += 0.1  # Base confidence
                
                # Only signal if confidence is high enough (70%+ for sniper quality)
                if confidence >= 0.70:
                    signal = type('Signal', (), {
                        'signal': 'BUY',
                        'confidence': confidence,
                        'rsi': rsi,
                        'atr': atr,
                        'ema_separation': ema_separation,
                        'volatility': price_volatility
                    })()
                    self.daily_trade_count += 1
                    logger.info(f"🎯 SNIPER BUY: Confidence={confidence:.1%}, RSI={rsi:.1f}, Sep={ema_separation*10000:.1f}bp")
            
            # ===================================================================
            # SELL SIGNAL: Clean EMA crossover + RSI confirmation + momentum
            # ===================================================================
            elif (ema_fast_curr < ema_slow_curr and         # Fast below slow (NOW)
                  ema_fast_prev >= ema_slow_prev and        # Crossover just happened
                  ema_fast_prev2 > ema_slow_prev2 and       # Confirm downward direction
                  rsi > self.rsi_oversold and               # Not oversold
                  rsi_momentum < 0 and                      # RSI falling (momentum)
                  ema_separation >= min_separation):        # Strong enough signal
                
                # Calculate confidence score (sniper quality)
                confidence = 0.0
                confidence += min(0.4, ema_separation * 1000)  # EMA strength (max 40%)
                confidence += min(0.3, (rsi - self.rsi_oversold) / 100)  # RSI room (max 30%)
                confidence += min(0.2, abs(rsi_momentum) / 10)  # Momentum (max 20%)
                confidence += 0.1  # Base confidence
                
                # Only signal if confidence is high enough (70%+ for sniper quality)
                if confidence >= 0.70:
                    signal = type('Signal', (), {
                        'signal': 'SELL',
                        'confidence': confidence,
                        'rsi': rsi,
                        'atr': atr,
                        'ema_separation': ema_separation,
                        'volatility': price_volatility
                    })()
                    self.daily_trade_count += 1
                    logger.info(f"🎯 SNIPER SELL: Confidence={confidence:.1%}, RSI={rsi:.1f}, Sep={ema_separation*10000:.1f}bp")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ scan_for_signal error: {e}")
            return None


# STRATEGY INSTANCES - TOP 3 PERFORMING

# Strategy #1: Best Sharpe Ratio (35.90)
strategy_rank_1 = GBP_USD_Optimized_Strategy(
    rank=1,
    strategy_params={
        'ema_fast_period': 3,
        'ema_slow_period': 12,
        'rsi_period': 14,
        'rsi_oversold': 20,
        'rsi_overbought': 80,
        'atr_period': 14,
        'atr_multiplier': 1.5,
        'take_profit_ratio': 3.0,
        'target_sharpe': 35.90,
        'target_win_rate': 80.3,
        'max_drawdown_limit': 0.006
    }
)

# Strategy #2: Second Best (35.55)
strategy_rank_2 = GBP_USD_Optimized_Strategy(
    rank=2,
    strategy_params={
        'ema_fast_period': 3,
        'ema_slow_period': 12,
        'rsi_period': 14,
        'rsi_oversold': 25,  # More conservative
        'rsi_overbought': 80,
        'atr_period': 14,
        'atr_multiplier': 1.5,
        'take_profit_ratio': 3.0,
        'target_sharpe': 35.55,
        'target_win_rate': 80.1,
        'max_drawdown_limit': 0.006
    }
)

# Strategy #3: Third Best (35.18) - Lowest Drawdown
strategy_rank_3 = GBP_USD_Optimized_Strategy(
    rank=3,
    strategy_params={
        'ema_fast_period': 3,
        'ema_slow_period': 12,
        'rsi_period': 14,
        'rsi_oversold': 30,  # Most conservative
        'rsi_overbought': 80,
        'atr_period': 14,
        'atr_multiplier': 1.5,
        'take_profit_ratio': 3.0,
        'target_sharpe': 35.18,
        'target_win_rate': 79.8,
        'max_drawdown_limit': 0.004  # Lowest drawdown
    }
)

# STRATEGY GETTER FUNCTIONS
def get_strategy_rank_1() -> GBP_USD_Optimized_Strategy:
    """Get Strategy #1 - Best Sharpe Ratio"""
    return strategy_rank_1

def get_strategy_rank_2() -> GBP_USD_Optimized_Strategy:
    """Get Strategy #2 - Second Best"""
    return strategy_rank_2

def get_strategy_rank_3() -> GBP_USD_Optimized_Strategy:
    """Get Strategy #3 - Third Best, Lowest Drawdown"""
    return strategy_rank_3
