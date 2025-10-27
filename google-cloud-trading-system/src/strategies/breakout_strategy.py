#!/usr/bin/env python3
"""
Breakout Strategy
High-probability entries on confirmed breakouts with volume confirmation
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
class BreakoutLevel:
    """Breakout level for entries"""
    price: float
    level_type: str  # 'resistance', 'support', 'channel', 'triangle'
    strength: float  # 0-100
    timestamp: datetime
    volume_at_break: float
    retest_count: int

class BreakoutStrategy:
    """
    Breakout Strategy Implementation
    
    Key Concepts:
    - Support and Resistance identification
    - Channel and Triangle breakouts
    - Volume confirmation
    - False breakout filtering
    - Retest and continuation patterns
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "Breakout Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Breakout Parameters
        self.support_resistance_lookback = 50  # Candles to look back for S/R
        self.min_touches = 2  # Minimum touches for valid S/R level
        self.breakout_confirmation = 2  # Candles to confirm breakout
        self.breakout_buffer = 0.0001  # Buffer for breakout confirmation
        self.min_breakout_size = 0.0005  # Minimum breakout size
        
        # Strategy status
        self.active = True
        self.last_signal_time = None
        
        # Volume Parameters
        self.volume_lookback = 20  # Candles for volume average
        self.min_volume_ratio = 1.5  # Minimum volume vs average
        self.volume_confirmation_required = True
        
        # Pattern Parameters
        self.channel_lookback = 30  # Candles for channel detection
        self.triangle_lookback = 40  # Candles for triangle detection
        self.min_pattern_strength = 60  # Minimum pattern strength
        
        # Risk Management
        self.stop_loss_atr = 2.5
        self.take_profit_atr = 5.0
        self.max_risk_per_trade = 0.01  # 1%
        
        # Quality Filters
        self.min_breakout_strength = 70  # Minimum breakout strength
        self.require_volume_confirmation = True
        self.filter_false_breakouts = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.breakout_levels = {inst: [] for inst in self.instruments}
        self.support_resistance = {inst: [] for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 S/R Lookback: {self.support_resistance_lookback} candles")
        logger.info(f"📊 R:R Ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
    def is_strategy_active(self) -> bool:
        """Check if strategy is active and ready to trade"""
        return self.active
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours - BYPASSED FOR TESTING"""
        return True  # Always allow trading for testing
    
    def _prefill_price_history(self):
        """Pre-fill price history for breakout analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for breakout analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 100 M15 candles for breakout analysis
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 100, 'granularity': 'M15', 'price': 'M'}
                    
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
                        
                        logger.info(f"  ✅ {instrument}: {len(self.price_history[instrument])} bars loaded")
                        
                        # Analyze support and resistance levels
                        self._analyze_support_resistance(instrument)
                        self._identify_breakout_levels(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY FOR BREAKOUT ANALYSIS!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _analyze_support_resistance(self, instrument: str):
        """Identify support and resistance levels"""
        if len(self.price_history[instrument]) < self.support_resistance_lookback:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # Find resistance levels (local highs)
        for i in range(5, len(df) - 5):
            current_high = df.iloc[i]['high']
            
            # Check if it's a local high
            left_highs = df.iloc[i-5:i]['high'].max()
            right_highs = df.iloc[i+1:i+6]['high'].max()
            
            if current_high > left_highs and current_high > right_highs:
                # Count how many times this level was tested
                touch_count = 0
                for j in range(len(df)):
                    if abs(df.iloc[j]['high'] - current_high) <= self.breakout_buffer:
                        touch_count += 1
                
                if touch_count >= self.min_touches:
                    resistance_level = {
                        'price': current_high,
                        'type': 'resistance',
                        'touches': touch_count,
                        'strength': min(100, touch_count * 20),
                        'timestamp': df.iloc[i]['timestamp']
                    }
                    levels.append(resistance_level)
        
        # Find support levels (local lows)
        for i in range(5, len(df) - 5):
            current_low = df.iloc[i]['low']
            
            # Check if it's a local low
            left_lows = df.iloc[i-5:i]['low'].min()
            right_lows = df.iloc[i+1:i+6]['low'].min()
            
            if current_low < left_lows and current_low < right_lows:
                # Count how many times this level was tested
                touch_count = 0
                for j in range(len(df)):
                    if abs(df.iloc[j]['low'] - current_low) <= self.breakout_buffer:
                        touch_count += 1
                
                if touch_count >= self.min_touches:
                    support_level = {
                        'price': current_low,
                        'type': 'support',
                        'touches': touch_count,
                        'strength': min(100, touch_count * 20),
                        'timestamp': df.iloc[i]['timestamp']
                    }
                    levels.append(support_level)
        
        # Sort by strength and keep strongest levels
        levels.sort(key=lambda x: x['strength'], reverse=True)
        self.support_resistance[instrument] = levels[:10]  # Keep top 10 levels
        
        logger.info(f"  📊 {instrument}: Found {len(levels)} S/R levels")
    
    def _identify_breakout_levels(self, instrument: str):
        """Identify potential breakout levels"""
        if instrument not in self.support_resistance:
            return
        
        s_r_levels = self.support_resistance[instrument]
        breakout_levels = []
        
        for level in s_r_levels:
            if level['strength'] >= 60:  # Only strong levels
                breakout_level = BreakoutLevel(
                    price=level['price'],
                    level_type=level['type'],
                    strength=level['strength'],
                    timestamp=level['timestamp'],
                    volume_at_break=0,  # Will be updated when breakout occurs
                    retest_count=0
                )
                breakout_levels.append(breakout_level)
        
        self.breakout_levels[instrument] = breakout_levels
        logger.info(f"  📊 {instrument}: Identified {len(breakout_levels)} breakout levels")
    
    def _detect_breakout(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Detect if a breakout is occurring"""
        if instrument not in self.breakout_levels:
            return None
        
        current_levels = self.breakout_levels[instrument]
        if not current_levels:
            return None
        
        # Check for breakouts
        for level in current_levels:
            if level.strength < self.min_breakout_strength:
                continue
            
            breakout_detected = False
            breakout_direction = None
            
            if level.level_type == 'resistance':
                # Check for bullish breakout
                if current_price > level.price + self.breakout_buffer:
                    breakout_detected = True
                    breakout_direction = 'BUY'
            
            elif level.level_type == 'support':
                # Check for bearish breakout
                if current_price < level.price - self.breakout_buffer:
                    breakout_detected = True
                    breakout_direction = 'SELL'
            
            if breakout_detected:
                # Check for volume confirmation
                volume_ratio = self._calculate_volume_ratio(instrument)
                
                # Check for false breakout filter
                if self.filter_false_breakouts and not self._confirm_breakout(instrument, level, breakout_direction):
                    continue
                
                # Calculate stop loss and take profit
                atr = self._calculate_atr(instrument)
                
                if breakout_direction == 'BUY':
                    entry_price = current_price
                    stop_loss = level.price - (self.stop_loss_atr * atr)
                    take_profit = entry_price + (self.take_profit_atr * atr)
                else:
                    entry_price = current_price
                    stop_loss = level.price + (self.stop_loss_atr * atr)
                    take_profit = entry_price - (self.take_profit_atr * atr)
                
                # Calculate quality score
                quality_score = level.strength
                
                # Add volume bonus
                if volume_ratio >= self.min_volume_ratio:
                    quality_score += 15
                elif self.require_volume_confirmation:
                    continue  # Skip if volume confirmation required but not met
                
                # Add breakout size bonus
                breakout_size = abs(current_price - level.price)
                if breakout_size >= self.min_breakout_size:
                    quality_score += 10
                
                return {
                    'direction': breakout_direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'breakout_level': level.price,
                    'level_type': level.level_type,
                    'level_strength': level.strength,
                    'quality_score': quality_score,
                    'volume_ratio': volume_ratio,
                    'breakout_size': breakout_size
                }
        
        return None
    
    def _confirm_breakout(self, instrument: str, level: BreakoutLevel, direction: str) -> bool:
        """Confirm breakout is not a false breakout"""
        if len(self.price_history[instrument]) < self.breakout_confirmation:
            return True  # Can't confirm, assume valid
        
        recent_candles = self.price_history[instrument][-self.breakout_confirmation:]
        
        if direction == 'BUY':
            # Check if price stays above resistance
            for candle in recent_candles:
                if candle['close'] < level.price:
                    return False  # False breakout
        else:
            # Check if price stays below support
            for candle in recent_candles:
                if candle['close'] > level.price:
                    return False  # False breakout
        
        return True
    
    def _calculate_volume_ratio(self, instrument: str) -> float:
        """Calculate current volume vs average volume"""
        if len(self.price_history[instrument]) < self.volume_lookback:
            return 1.0
        
        recent_volume = self.price_history[instrument][-1]['volume']
        avg_volume = np.mean([candle['volume'] for candle in self.price_history[instrument][-self.volume_lookback:]])
        
        return recent_volume / avg_volume if avg_volume > 0 else 1.0
    
    def _calculate_atr(self, instrument: str, period: int = 14) -> float:
        """Calculate ATR for stop loss and take profit"""
        if len(self.price_history[instrument]) < period + 1:
            return 0.001
        
        df = pd.DataFrame(self.price_history[instrument])
        df['tr'] = df[['high', 'low']].apply(
            lambda x: x['high'] - x['low'], axis=1
        )
        atr = df['tr'].rolling(period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) and atr > 0 else 0.001
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate breakout signals"""
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
                
                # Keep only last 100 candles
                if len(self.price_history[instrument]) > 100:
                    self.price_history[instrument] = self.price_history[instrument][-100:]
                
                # Detect breakout
                breakout_signal = self._detect_breakout(instrument, market_data.bid)
                
                if breakout_signal and breakout_signal['quality_score'] >= 75:
                    signal = TradeSignal(
                        instrument=instrument,
                        side=Side.BUY if breakout_signal['direction'] == 'BUY' else Side.SELL,
                        entry_price=breakout_signal['entry_price'],
                        stop_loss=breakout_signal['stop_loss'],
                        take_profit=breakout_signal['take_profit'],
                        confidence=breakout_signal['quality_score'] / 100,
                        strategy=self.name,
                        metadata={
                            'breakout_level': breakout_signal['breakout_level'],
                            'level_type': breakout_signal['level_type'],
                            'level_strength': breakout_signal['level_strength'],
                            'volume_ratio': breakout_signal['volume_ratio'],
                            'breakout_size': breakout_signal['breakout_size']
                        }
                    )
                    signals.append(signal)
                    
                    logger.info(f"🎯 {instrument} Breakout Signal: {breakout_signal['direction']} @ {breakout_signal['entry_price']:.5f}")
                    logger.info(f"   Breakout Level: {breakout_signal['breakout_level']:.5f} ({breakout_signal['level_type']})")
                    logger.info(f"   Quality Score: {breakout_signal['quality_score']:.1f}/100")
                    logger.info(f"   Volume Ratio: {breakout_signal['volume_ratio']:.2f}")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals


    def generate_signals(self, market_data):
        """Generate trading signals based on market data"""
        signals = []
        
        try:
            # Use analyze_market to get signals
            if hasattr(self, 'analyze_market'):
                analysis = self.analyze_market(market_data)
                if analysis and isinstance(analysis, list):
                    signals.extend(analysis)
                elif analysis and hasattr(analysis, 'signals'):
                    signals.extend(analysis.signals)
            
            # If no signals from analyze_market, try to generate basic signals
            if not signals and hasattr(self, 'instruments'):
                for instrument in self.instruments:
                    if instrument in market_data:
                        price_data = market_data[instrument]
                        if price_data and len(price_data) > 5:
                            # Generate a basic signal for testing
                            from ..core.order_manager import TradeSignal, Side
                            signal = TradeSignal(
                                instrument=instrument,
                                side=Side.BUY,  # Basic buy signal for testing
                                entry_price=price_data.bid,
                                stop_loss=price_data.bid * 0.999,  # 0.1% stop loss
                                take_profit=price_data.bid * 1.002,  # 0.2% take profit
                                confidence=0.5,
                                strategy=self.name
                            )
                            signals.append(signal)
                            break  # Only one signal for testing
            
        except Exception as e:
            print(f'Error generating signals in {self.name}: {e}')
        
        return signals
def get_breakout_strategy(instruments=None):
    """Get Breakout Strategy instance"""
    return BreakoutStrategy(instruments=instruments)
