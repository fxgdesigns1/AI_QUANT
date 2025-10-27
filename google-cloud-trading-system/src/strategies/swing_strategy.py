#!/usr/bin/env python3
"""
Swing Trading Strategy
Medium-term trading strategy for capturing larger price movements
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..core.data_feed import MarketData
from ..core.order_manager import TradeSignal, Side

logger = logging.getLogger(__name__)

@dataclass
class SwingLevel:
    """Swing trading level for analysis"""
    price: float
    strength: float
    timestamp: datetime
    type: str  # 'support', 'resistance', 'trendline'
    touches: int

@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    direction: str  # 'uptrend', 'downtrend', 'sideways'
    strength: float
    duration: int
    slope: float

class SwingStrategy:
    """
    Swing Trading Strategy Implementation
    
    Key Concepts:
    - Medium-term positions (1-5 days)
    - Larger profit targets (50-200 pips)
    - Trend following approach
    - Support/resistance levels
    - Moving average crossovers
    - Chart pattern recognition
    - Risk-reward ratio focus (1:2 or better)
    - Market structure analysis
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "Swing Trading Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Swing Parameters
        self.swing_timeframe = 'H4'  # 4-hour swing trading
        self.max_hold_time = 5  # Maximum hold time in days
        self.min_profit_pips = 50  # Minimum profit target in pips
        self.max_profit_pips = 200  # Maximum profit target in pips
        self.stop_loss_pips = 30  # Stop loss in pips
        self.trailing_stop_pips = 20  # Trailing stop in pips
        
        # Trend Analysis
        self.trend_period = 20  # Period for trend analysis
        self.trend_strength_threshold = 0.6  # Minimum trend strength
        self.ma_fast = 10  # Fast moving average
        self.ma_slow = 20  # Slow moving average
        self.ma_trend = 50  # Trend moving average
        
        # Support/Resistance
        self.level_lookback = 100  # Candles to look back for levels
        self.min_level_touches = 2  # Minimum touches for valid level
        self.level_tolerance = 0.0005  # Tolerance for level identification
        
        # Risk Management
        self.max_risk_per_trade = 0.02  # 2% per trade
        self.max_daily_trades = 3  # Maximum trades per day
        self.max_concurrent_positions = 2  # Maximum concurrent positions
        self.min_risk_reward = 2.0  # Minimum risk-reward ratio
        
        # Quality Filters
        self.min_quality_score = 70  # Minimum quality score
        self.require_trend_confirmation = True
        self.require_level_confirmation = True
        self.require_volume_confirmation = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.swing_levels = {inst: [] for inst in self.instruments}
        self.trend_analysis = {inst: None for inst in self.instruments}
        
        # Trade tracking
        self.daily_trades = {inst: 0 for inst in self.instruments}
        self.last_trade_time = {inst: None for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Timeframe: {self.swing_timeframe}")
        logger.info(f"📊 Max Hold Time: {self.max_hold_time} days")
        logger.info(f"📊 Profit Target: {self.min_profit_pips}-{self.max_profit_pips} pips")
        logger.info(f"📊 Min R:R Ratio: 1:{self.min_risk_reward}")
    
    def _prefill_price_history(self):
        """Pre-fill price history for swing trading analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for swing trading analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 200 H4 candles for swing analysis
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 200, 'granularity': 'H4', 'price': 'M'}
                    
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        candles = data.get('candles', [])
                        
                        for candle in candles:
                            # Handle OANDA bid/ask format
                            if 'mid' in candle and isinstance(candle['mid'], dict):
                                close = float(candle['mid'].get('c', 0))
                                high = float(candle['mid'].get('h', 0))
                                low = float(candle['mid'].get('l', 0))
                                open_price = float(candle['mid'].get('o', 0))
                            elif 'bid' in candle and isinstance(candle['bid'], dict):
                                close = float(candle['bid'].get('c', 0))
                                high = float(candle['bid'].get('h', 0))
                                low = float(candle['bid'].get('l', 0))
                                open_price = float(candle['bid'].get('o', 0))
                            else:
                                continue
                                
                            if close > 0:
                                self.price_history[instrument].append({
                                    'timestamp': candle.get('time', ''),
                                    'open': open_price,
                                    'high': high,
                                    'low': low,
                                    'close': close,
                                    'volume': candle.get('volume', 0)
                                })
                        
                        logger.info(f"  ✅ {instrument}: {len(self.price_history[instrument])} H4 bars loaded")
                        
                        # Calculate swing levels and trend analysis
                        self._calculate_swing_levels(instrument)
                        self._analyze_trend(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total H4 bars - READY FOR SWING TRADING!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _calculate_swing_levels(self, instrument: str):
        """Calculate swing trading levels (support/resistance)"""
        if len(self.price_history[instrument]) < self.level_lookback:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # Find swing highs and lows
        for i in range(10, len(df) - 10):
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']
            
            # Check for swing high
            left_highs = [df.iloc[j]['high'] for j in range(i-10, i)]
            right_highs = [df.iloc[j]['high'] for j in range(i+1, i+11)]
            
            if current_high > max(left_highs) and current_high > max(right_highs):
                # Count touches
                touches = 0
                for j in range(len(df)):
                    if abs(df.iloc[j]['high'] - current_high) <= self.level_tolerance:
                        touches += 1
                
                if touches >= self.min_level_touches:
                    level = SwingLevel(
                        price=current_high,
                        strength=touches,
                        timestamp=df.iloc[i]['timestamp'],
                        type='resistance',
                        touches=touches
                    )
                    levels.append(level)
            
            # Check for swing low
            left_lows = [df.iloc[j]['low'] for j in range(i-10, i)]
            right_lows = [df.iloc[j]['low'] for j in range(i+1, i+11)]
            
            if current_low < min(left_lows) and current_low < min(right_lows):
                # Count touches
                touches = 0
                for j in range(len(df)):
                    if abs(df.iloc[j]['low'] - current_low) <= self.level_tolerance:
                        touches += 1
                
                if touches >= self.min_level_touches:
                    level = SwingLevel(
                        price=current_low,
                        strength=touches,
                        timestamp=df.iloc[i]['timestamp'],
                        type='support',
                        touches=touches
                    )
                    levels.append(level)
        
        # Keep only strong levels
        strong_levels = [l for l in levels if l.strength >= self.min_level_touches]
        self.swing_levels[instrument] = strong_levels[-20:]  # Keep last 20 levels
        
        logger.info(f"  📊 {instrument}: Found {len(strong_levels)} swing levels")
    
    def _analyze_trend(self, instrument: str):
        """Analyze trend direction and strength"""
        if len(self.price_history[instrument]) < self.trend_period:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        
        # Calculate moving averages
        df['ma_fast'] = df['close'].rolling(self.ma_fast).mean()
        df['ma_slow'] = df['close'].rolling(self.ma_slow).mean()
        df['ma_trend'] = df['close'].rolling(self.ma_trend).mean()
        
        # Calculate trend slope
        recent_prices = df['close'].tail(self.trend_period)
        slope = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        
        # Determine trend direction
        current_price = df['close'].iloc[-1]
        ma_fast_current = df['ma_fast'].iloc[-1]
        ma_slow_current = df['ma_slow'].iloc[-1]
        ma_trend_current = df['ma_trend'].iloc[-1]
        
        if (current_price > ma_fast_current > ma_slow_current > ma_trend_current and slope > 0):
            direction = 'uptrend'
            strength = min(1.0, abs(slope) * 10000)
        elif (current_price < ma_fast_current < ma_slow_current < ma_trend_current and slope < 0):
            direction = 'downtrend'
            strength = min(1.0, abs(slope) * 10000)
        else:
            direction = 'sideways'
            strength = 0.3
        
        # Calculate trend duration
        duration = 0
        for i in range(len(df) - 1, 0, -1):
            if direction == 'uptrend' and df.iloc[i]['close'] > df.iloc[i-1]['close']:
                duration += 1
            elif direction == 'downtrend' and df.iloc[i]['close'] < df.iloc[i-1]['close']:
                duration += 1
            else:
                break
        
        self.trend_analysis[instrument] = TrendAnalysis(
            direction=direction,
            strength=strength,
            duration=duration,
            slope=slope
        )
        
        logger.info(f"  📊 {instrument}: {direction} (strength: {strength:.2f}, duration: {duration})")
    
    def _check_swing_conditions(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Check if swing trading conditions are met"""
        if instrument not in self.swing_levels:
            return None
        
        # Check if we can trade (daily limits)
        if self.daily_trades[instrument] >= self.max_daily_trades:
            return None
        
        # Check time since last trade
        if (self.last_trade_time[instrument] and 
            (datetime.now() - self.last_trade_time[instrument]).total_seconds() < 3600):  # 1 hour gap
            return None
        
        # Check trend
        trend = self.trend_analysis[instrument]
        if not trend or trend.strength < self.trend_strength_threshold:
            return None
        
        # Check for level interaction
        level_signal = self._check_level_interaction(instrument, current_price, trend.direction)
        if not level_signal:
            return None
        
        return {
            'trend': trend,
            'level_signal': level_signal,
            'current_price': current_price
        }
    
    def _check_level_interaction(self, instrument: str, current_price: float, trend_direction: str) -> Optional[Dict]:
        """Check for level interaction signals"""
        levels = self.swing_levels[instrument]
        if not levels:
            return None
        
        # Look for pullback to support in uptrend
        if trend_direction == 'uptrend':
            for level in levels:
                if (level.type == 'support' and 
                    abs(current_price - level.price) <= self.level_tolerance and
                    current_price >= level.price):
                    
                    return {
                        'direction': 'BUY',
                        'level_price': level.price,
                        'level_strength': level.strength,
                        'level_type': level.type,
                        'interaction_type': 'support_bounce'
                    }
        
        # Look for pullback to resistance in downtrend
        elif trend_direction == 'downtrend':
            for level in levels:
                if (level.type == 'resistance' and 
                    abs(current_price - level.price) <= self.level_tolerance and
                    current_price <= level.price):
                    
                    return {
                        'direction': 'SELL',
                        'level_price': level.price,
                        'level_strength': level.strength,
                        'level_type': level.type,
                        'interaction_type': 'resistance_rejection'
                    }
        
        return None
    
    def _calculate_swing_targets(self, instrument: str, direction: str, entry_price: float, level_price: float) -> Tuple[float, float]:
        """Calculate swing trading targets"""
        # Calculate pip value
        pip_value = 0.0001 if 'JPY' not in instrument else 0.01
        
        if direction == 'BUY':
            # Target next resistance level or minimum profit
            take_profit = entry_price + (self.min_profit_pips * pip_value)
            stop_loss = entry_price - (self.stop_loss_pips * pip_value)
        else:
            # Target next support level or minimum profit
            take_profit = entry_price - (self.min_profit_pips * pip_value)
            stop_loss = entry_price + (self.stop_loss_pips * pip_value)
        
        return take_profit, stop_loss
    
    def _calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, take_profit: float) -> float:
        """Calculate risk-reward ratio"""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        return reward / risk if risk > 0 else 0
    
    def _calculate_quality_score(self, conditions: Dict, level_signal: Dict) -> float:
        """Calculate swing trading quality score"""
        score = 50  # Base score
        
        # Trend strength bonus
        trend_strength = conditions['trend'].strength
        score += min(25, trend_strength * 25)
        
        # Level strength bonus
        level_bonus = level_signal['level_strength'] * 5
        score += min(15, level_bonus)
        
        # Trend duration bonus
        duration_bonus = min(10, conditions['trend'].duration * 0.5)
        score += duration_bonus
        
        # Level interaction bonus
        if level_signal['interaction_type'] in ['support_bounce', 'resistance_rejection']:
            score += 10
        
        return min(100, score)
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate swing trading signals"""
        signals = []
        
        # Pre-fill price history if needed
        if not any(self.price_history.values()):
            self._prefill_price_history()
        
        for instrument, market_data in market_data_dict.items():
            if instrument not in self.instruments:
                continue
            
            try:
                # Add current price to history
                current_candle = {
                    'timestamp': market_data.timestamp,
                    'open': market_data.bid,
                    'high': market_data.bid,
                    'low': market_data.bid,
                    'close': market_data.bid,
                    'volume': 0
                }
                self.price_history[instrument].append(current_candle)
                
                # Keep only last 200 candles
                if len(self.price_history[instrument]) > 200:
                    self.price_history[instrument] = self.price_history[instrument][-200:]
                
                # Check swing conditions
                conditions = self._check_swing_conditions(instrument, market_data.bid)
                
                if conditions:
                    level_signal = conditions['level_signal']
                    quality_score = self._calculate_quality_score(conditions, level_signal)
                    
                    if quality_score >= self.min_quality_score:
                        # Calculate targets
                        take_profit, stop_loss = self._calculate_swing_targets(
                            instrument, level_signal['direction'], market_data.bid, level_signal['level_price']
                        )
                        
                        # Check risk-reward ratio
                        risk_reward = self._calculate_risk_reward_ratio(market_data.bid, stop_loss, take_profit)
                        
                        if risk_reward >= self.min_risk_reward:
                            signal = TradeSignal(
                                instrument=instrument,
                                side=Side.BUY if level_signal['direction'] == 'BUY' else Side.SELL,
                                entry_price=market_data.bid,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                confidence=quality_score / 100,
                                strategy=self.name,
                                metadata={
                                    'trend_direction': conditions['trend'].direction,
                                    'trend_strength': conditions['trend'].strength,
                                    'trend_duration': conditions['trend'].duration,
                                    'level_price': level_signal['level_price'],
                                    'level_strength': level_signal['level_strength'],
                                    'level_type': level_signal['level_type'],
                                    'interaction_type': level_signal['interaction_type'],
                                    'risk_reward_ratio': risk_reward,
                                    'max_hold_time': self.max_hold_time,
                                    'swing_type': 'trend_following'
                                }
                            )
                            signals.append(signal)
                            
                            # Update trade tracking
                            self.daily_trades[instrument] += 1
                            self.last_trade_time[instrument] = datetime.now()
                            
                            logger.info(f"📈 {instrument} Swing Signal: {level_signal['direction']} @ {market_data.bid:.5f}")
                            logger.info(f"   Trend: {conditions['trend'].direction} (strength: {conditions['trend'].strength:.2f})")
                            logger.info(f"   Level: {level_signal['level_type']} @ {level_signal['level_price']:.5f}")
                            logger.info(f"   R:R Ratio: 1:{risk_reward:.1f}")
                            logger.info(f"   Quality Score: {quality_score:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals

def get_swing_strategy(instruments=None):
    """Get Swing Strategy instance"""
    return SwingStrategy(instruments=instruments)
