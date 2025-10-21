#!/usr/bin/env python3
"""
Fibonacci Retracement Strategy
High-probability entries at key Fibonacci levels with confluence
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
class FibonacciLevel:
    """Fibonacci retracement level"""
    price: float
    level: float  # 0.236, 0.382, 0.5, 0.618, 0.786
    level_type: str  # 'retracement', 'extension'
    strength: float  # 0-100
    timestamp: datetime
    swing_high: float
    swing_low: float

class FibonacciStrategy:
    """
    Fibonacci Retracement Strategy Implementation
    
    Key Concepts:
    - Swing High/Low identification
    - Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%)
    - Fibonacci extension levels (127.2%, 161.8%, 261.8%)
    - Confluence with support/resistance
    - Price action confirmation at Fib levels
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "Fibonacci Retracement Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Fibonacci Parameters
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]  # Retracement levels
        self.fib_extensions = [1.272, 1.618, 2.618]  # Extension levels
        self.swing_lookback = 20  # Candles to look back for swing points
        self.min_swing_size = 0.001  # Minimum swing size
        self.fib_tolerance = 0.0001  # Tolerance for Fib level hits
        
        # Confluence Parameters
        self.require_confluence = True
        self.min_confluence_levels = 2  # Minimum confluent levels
        self.support_resistance_lookback = 50  # Lookback for S/R levels
        
        # Risk Management
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 4.0
        self.max_risk_per_trade = 0.01  # 1%
        
        # Quality Filters
        self.min_fib_strength = 70  # Minimum Fib level strength
        self.require_price_action_confirmation = True
        self.min_swing_quality = 60  # Minimum swing quality score
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.fibonacci_levels = {inst: [] for inst in self.instruments}
        self.swing_points = {inst: [] for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Fib Levels: {self.fib_levels}")
        logger.info(f"📊 R:R Ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
    def _prefill_price_history(self):
        """Pre-fill price history for Fibonacci analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for Fibonacci analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 100 M15 candles for Fibonacci analysis
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
                        
                        # Analyze swing points and Fibonacci levels
                        self._analyze_swing_points(instrument)
                        self._calculate_fibonacci_levels(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY FOR FIBONACCI ANALYSIS!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _analyze_swing_points(self, instrument: str):
        """Identify swing highs and lows"""
        if len(self.price_history[instrument]) < self.swing_lookback * 2:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        swing_points = []
        
        # Find swing highs
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            current_high = df.iloc[i]['high']
            
            # Check if it's higher than surrounding highs
            left_highs = df.iloc[i-self.swing_lookback:i]['high'].max()
            right_highs = df.iloc[i+1:i+self.swing_lookback+1]['high'].max()
            
            if current_high > left_highs and current_high > right_highs:
                swing_high = {
                    'type': 'high',
                    'price': current_high,
                    'timestamp': df.iloc[i]['timestamp'],
                    'index': i,
                    'strength': self._calculate_swing_strength(df, i, 'high')
                }
                swing_points.append(swing_high)
        
        # Find swing lows
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            current_low = df.iloc[i]['low']
            
            # Check if it's lower than surrounding lows
            left_lows = df.iloc[i-self.swing_lookback:i]['low'].min()
            right_lows = df.iloc[i+1:i+self.swing_lookback+1]['low'].min()
            
            if current_low < left_lows and current_low < right_lows:
                swing_low = {
                    'type': 'low',
                    'price': current_low,
                    'timestamp': df.iloc[i]['timestamp'],
                    'index': i,
                    'strength': self._calculate_swing_strength(df, i, 'low')
                }
                swing_points.append(swing_low)
        
        # Sort by timestamp and keep only recent ones
        swing_points.sort(key=lambda x: x['timestamp'])
        self.swing_points[instrument] = swing_points[-10:]  # Keep last 10 swing points
        
        logger.info(f"  📊 {instrument}: Found {len(swing_points)} swing points")
    
    def _calculate_swing_strength(self, df: pd.DataFrame, index: int, swing_type: str) -> float:
        """Calculate strength of a swing point"""
        if swing_type == 'high':
            current_price = df.iloc[index]['high']
            # Calculate how much higher it is than surrounding prices
            surrounding_prices = df.iloc[max(0, index-10):index+11]['high']
            avg_surrounding = surrounding_prices.mean()
            strength = min(100, ((current_price - avg_surrounding) / avg_surrounding) * 1000)
        else:
            current_price = df.iloc[index]['low']
            # Calculate how much lower it is than surrounding prices
            surrounding_prices = df.iloc[max(0, index-10):index+11]['low']
            avg_surrounding = surrounding_prices.mean()
            strength = min(100, ((avg_surrounding - current_price) / avg_surrounding) * 1000)
        
        return max(0, strength)
    
    def _calculate_fibonacci_levels(self, instrument: str):
        """Calculate Fibonacci retracement and extension levels"""
        if len(self.swing_points[instrument]) < 2:
            return
        
        swing_points = self.swing_points[instrument]
        fib_levels = []
        
        # Calculate Fibonacci levels between recent swing points
        for i in range(len(swing_points) - 1):
            swing1 = swing_points[i]
            swing2 = swing_points[i + 1]
            
            # Determine which is high and which is low
            if swing1['type'] == 'high' and swing2['type'] == 'low':
                swing_high = swing1['price']
                swing_low = swing2['price']
                direction = 'bearish'  # Price moving down
            elif swing1['type'] == 'low' and swing2['type'] == 'high':
                swing_low = swing1['price']
                swing_high = swing2['price']
                direction = 'bullish'  # Price moving up
            else:
                continue  # Skip if not a valid swing pair
            
            swing_range = swing_high - swing_low
            
            if swing_range < self.min_swing_size:
                continue  # Skip small swings
            
            # Calculate Fibonacci retracement levels
            for fib_level in self.fib_levels:
                if direction == 'bullish':
                    # Retracement from high to low
                    fib_price = swing_high - (swing_range * fib_level)
                else:
                    # Retracement from low to high
                    fib_price = swing_low + (swing_range * fib_level)
                
                # Calculate strength based on swing quality and confluence
                strength = (swing1['strength'] + swing2['strength']) / 2
                
                # Add bonus for key Fibonacci levels
                if fib_level in [0.382, 0.618]:
                    strength += 10
                elif fib_level == 0.5:
                    strength += 5
                
                fib_level_obj = FibonacciLevel(
                    price=fib_price,
                    level=fib_level,
                    level_type='retracement',
                    strength=min(100, strength),
                    timestamp=swing2['timestamp'],
                    swing_high=swing_high,
                    swing_low=swing_low
                )
                fib_levels.append(fib_level_obj)
        
        self.fibonacci_levels[instrument] = fib_levels
        logger.info(f"  📊 {instrument}: Calculated {len(fib_levels)} Fibonacci levels")
    
    def _find_fibonacci_entry(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Find Fibonacci entry opportunity"""
        if instrument not in self.fibonacci_levels:
            return None
        
        current_levels = self.fibonacci_levels[instrument]
        if not current_levels:
            return None
        
        # Find closest Fibonacci level
        best_fib = None
        min_distance = float('inf')
        
        for fib_level in current_levels:
            if fib_level.strength >= self.min_fib_strength:
                distance = abs(current_price - fib_level.price)
                if distance < min_distance and distance <= self.fib_tolerance:
                    min_distance = distance
                    best_fib = fib_level
        
        if best_fib is None:
            return None
        
        # Determine direction based on Fibonacci level and price action
        if current_price <= best_fib.price:
            # Price at or below Fib level - potential bullish entry
            direction = 'BUY'
            entry_price = current_price
        else:
            # Price above Fib level - potential bearish entry
            direction = 'SELL'
            entry_price = current_price
        
        # Calculate stop loss and take profit
        atr = self._calculate_atr(instrument)
        
        if direction == 'BUY':
            stop_loss = entry_price - (self.stop_loss_atr * atr)
            take_profit = entry_price + (self.take_profit_atr * atr)
        else:
            stop_loss = entry_price + (self.stop_loss_atr * atr)
            take_profit = entry_price - (self.take_profit_atr * atr)
        
        # Calculate quality score
        quality_score = best_fib.strength
        
        # Add confluence bonus
        confluence_count = self._count_confluent_levels(instrument, best_fib.price)
        if confluence_count >= self.min_confluence_levels:
            quality_score += 15
        
        # Add price action confirmation bonus
        if self._check_price_action_confirmation(instrument, best_fib.price, direction):
            quality_score += 10
        
        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'fib_level': best_fib.price,
            'fib_ratio': best_fib.level,
            'quality_score': quality_score,
            'confluence_count': confluence_count
        }
    
    def _count_confluent_levels(self, instrument: str, price: float) -> int:
        """Count confluent levels near the Fibonacci level"""
        if not self.require_confluence:
            return 1
        
        confluence_count = 0
        tolerance = self.fib_tolerance * 2
        
        # Check other Fibonacci levels
        for fib_level in self.fibonacci_levels[instrument]:
            if abs(fib_level.price - price) <= tolerance:
                confluence_count += 1
        
        # Check support/resistance levels (simplified)
        if len(self.price_history[instrument]) >= self.support_resistance_lookback:
            df = pd.DataFrame(self.price_history[instrument])
            recent_highs = df.tail(self.support_resistance_lookback)['high']
            recent_lows = df.tail(self.support_resistance_lookback)['low']
            
            # Check for nearby highs/lows
            for high in recent_highs:
                if abs(high - price) <= tolerance:
                    confluence_count += 0.5
            
            for low in recent_lows:
                if abs(low - price) <= tolerance:
                    confluence_count += 0.5
        
        return int(confluence_count)
    
    def _check_price_action_confirmation(self, instrument: str, fib_price: float, direction: str) -> bool:
        """Check for price action confirmation at Fibonacci level"""
        if not self.require_price_action_confirmation:
            return True
        
        if len(self.price_history[instrument]) < 5:
            return False
        
        recent_candles = self.price_history[instrument][-5:]
        
        if direction == 'BUY':
            # Look for bullish reversal patterns
            for candle in recent_candles:
                if (candle['low'] <= fib_price <= candle['high'] and
                    candle['close'] > candle['open']):  # Bullish candle
                    return True
        else:
            # Look for bearish reversal patterns
            for candle in recent_candles:
                if (candle['low'] <= fib_price <= candle['high'] and
                    candle['close'] < candle['open']):  # Bearish candle
                    return True
        
        return False
    
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
        """Analyze market and generate Fibonacci signals"""
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
                
                # Find Fibonacci entry
                fib_entry = self._find_fibonacci_entry(instrument, market_data.bid)
                
                if fib_entry and fib_entry['quality_score'] >= 75:
                    signal = TradeSignal(
                        instrument=instrument,
                        side=Side.BUY if fib_entry['direction'] == 'BUY' else Side.SELL,
                        entry_price=fib_entry['entry_price'],
                        stop_loss=fib_entry['stop_loss'],
                        take_profit=fib_entry['take_profit'],
                        confidence=fib_entry['quality_score'] / 100,
                        strategy=self.name,
                        metadata={
                            'fib_level': fib_entry['fib_level'],
                            'fib_ratio': fib_entry['fib_ratio'],
                            'confluence_count': fib_entry['confluence_count'],
                            'fib_type': 'retracement'
                        }
                    )
                    signals.append(signal)
                    
                    logger.info(f"🎯 {instrument} Fibonacci Signal: {fib_entry['direction']} @ {fib_entry['entry_price']:.5f}")
                    logger.info(f"   Fib Level: {fib_entry['fib_level']:.5f} ({fib_entry['fib_ratio']*100:.1f}%)")
                    logger.info(f"   Quality Score: {fib_entry['quality_score']:.1f}/100")
                    logger.info(f"   Confluence: {fib_entry['confluence_count']} levels")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals
