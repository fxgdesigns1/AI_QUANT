#!/usr/bin/env python3
"""
RSI Divergence Strategy
High-probability reversal entries based on RSI divergence patterns
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
class DivergencePoint:
    """Divergence point for analysis"""
    price: float
    rsi: float
    timestamp: datetime
    index: int
    type: str  # 'high' or 'low'

class RSIDivergenceStrategy:
    """
    RSI Divergence Strategy Implementation
    
    Key Concepts:
    - RSI calculation with multiple timeframes
    - Bullish divergence: Price makes lower lows, RSI makes higher lows
    - Bearish divergence: Price makes higher highs, RSI makes lower highs
    - Hidden divergence: Continuation patterns
    - RSI overbought/oversold levels
    - Divergence confirmation with price action
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "RSI Divergence Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # RSI Parameters
        self.rsi_period = 14  # RSI calculation period
        self.rsi_overbought = 70  # Overbought level
        self.rsi_oversold = 30  # Oversold level
        self.rsi_extreme_overbought = 80  # Extreme overbought
        self.rsi_extreme_oversold = 20  # Extreme oversold
        
        # Divergence Parameters
        self.divergence_lookback = 50  # Candles to look back for divergence
        self.min_divergence_strength = 0.5  # Minimum divergence strength
        self.divergence_confirmation = 3  # Candles to confirm divergence
        self.price_tolerance = 0.0001  # Tolerance for price comparison
        self.rsi_tolerance = 2.0  # Tolerance for RSI comparison
        
        # Risk Management
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 4.0
        self.max_risk_per_trade = 0.01  # 1%
        
        # Quality Filters
        self.min_divergence_quality = 70  # Minimum divergence quality
        self.require_rsi_extreme = True  # Require RSI in extreme zones
        self.require_price_action_confirmation = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.rsi_data = {inst: [] for inst in self.instruments}
        self.divergence_points = {inst: [] for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 RSI Period: {self.rsi_period}")
        logger.info(f"📊 R:R Ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
    def _prefill_price_history(self):
        """Pre-fill price history for RSI divergence analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for RSI divergence analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 100 M15 candles for RSI analysis
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
                        
                        # Calculate RSI and find divergence points
                        self._calculate_rsi(instrument)
                        self._find_divergence_points(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY FOR RSI DIVERGENCE ANALYSIS!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _calculate_rsi(self, instrument: str):
        """Calculate RSI for the instrument"""
        if len(self.price_history[instrument]) < self.rsi_period + 1:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        
        # Calculate price changes
        df['price_change'] = df['close'].diff()
        
        # Separate gains and losses
        df['gain'] = df['price_change'].where(df['price_change'] > 0, 0)
        df['loss'] = -df['price_change'].where(df['price_change'] < 0, 0)
        
        # Calculate average gains and losses
        df['avg_gain'] = df['gain'].rolling(window=self.rsi_period).mean()
        df['avg_loss'] = df['loss'].rolling(window=self.rsi_period).mean()
        
        # Calculate RSI
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        # Store RSI data
        rsi_data = []
        for i, row in df.iterrows():
            if not pd.isna(row['rsi']):
                rsi_data.append({
                    'timestamp': row['timestamp'],
                    'rsi': row['rsi'],
                    'price': row['close'],
                    'index': i
                })
        
        self.rsi_data[instrument] = rsi_data
        logger.info(f"  📊 {instrument}: Calculated RSI for {len(rsi_data)} periods")
    
    def _find_divergence_points(self, instrument: str):
        """Find potential divergence points"""
        if len(self.rsi_data[instrument]) < self.divergence_lookback:
            return
        
        rsi_data = self.rsi_data[instrument]
        divergence_points = []
        
        # Find RSI highs and lows
        for i in range(5, len(rsi_data) - 5):
            current_rsi = rsi_data[i]['rsi']
            current_price = rsi_data[i]['price']
            
            # Check for RSI high
            left_rsi = [rsi_data[j]['rsi'] for j in range(i-5, i)]
            right_rsi = [rsi_data[j]['rsi'] for j in range(i+1, i+6)]
            
            if (current_rsi > max(left_rsi) and current_rsi > max(right_rsi) and
                current_rsi > self.rsi_overbought):
                
                divergence_point = DivergencePoint(
                    price=current_price,
                    rsi=current_rsi,
                    timestamp=rsi_data[i]['timestamp'],
                    index=i,
                    type='high'
                )
                divergence_points.append(divergence_point)
            
            # Check for RSI low
            elif (current_rsi < min(left_rsi) and current_rsi < min(right_rsi) and
                  current_rsi < self.rsi_oversold):
                
                divergence_point = DivergencePoint(
                    price=current_price,
                    rsi=current_rsi,
                    timestamp=rsi_data[i]['timestamp'],
                    index=i,
                    type='low'
                )
                divergence_points.append(divergence_point)
        
        self.divergence_points[instrument] = divergence_points
        logger.info(f"  📊 {instrument}: Found {len(divergence_points)} divergence points")
    
    def _detect_divergence(self, instrument: str, current_price: float, current_rsi: float) -> Optional[Dict]:
        """Detect RSI divergence patterns"""
        if instrument not in self.divergence_points:
            return None
        
        divergence_points = self.divergence_points[instrument]
        if len(divergence_points) < 2:
            return None
        
        # Look for recent divergence points
        recent_points = [p for p in divergence_points if p.index >= len(divergence_points) - 10]
        
        for i in range(len(recent_points) - 1):
            point1 = recent_points[i]
            point2 = recent_points[i + 1]
            
            # Check for bullish divergence (price lower lows, RSI higher lows)
            if (point1.type == 'low' and point2.type == 'low' and
                point2.price < point1.price - self.price_tolerance and
                point2.rsi > point1.rsi + self.rsi_tolerance):
                
                # Check if current RSI is in oversold zone
                if current_rsi <= self.rsi_oversold or (self.require_rsi_extreme and current_rsi <= self.rsi_extreme_oversold):
                    return self._create_divergence_signal(
                        instrument, current_price, current_rsi, 'BUY', point1, point2
                    )
            
            # Check for bearish divergence (price higher highs, RSI lower highs)
            elif (point1.type == 'high' and point2.type == 'high' and
                  point2.price > point1.price + self.price_tolerance and
                  point2.rsi < point1.rsi - self.rsi_tolerance):
                
                # Check if current RSI is in overbought zone
                if current_rsi >= self.rsi_overbought or (self.require_rsi_extreme and current_rsi >= self.rsi_extreme_overbought):
                    return self._create_divergence_signal(
                        instrument, current_price, current_rsi, 'SELL', point1, point2
                    )
        
        return None
    
    def _create_divergence_signal(self, instrument: str, current_price: float, current_rsi: float,
                                 direction: str, point1: DivergencePoint, point2: DivergencePoint) -> Dict:
        """Create divergence signal"""
        # Calculate stop loss and take profit
        atr = self._calculate_atr(instrument)
        
        if direction == 'BUY':
            entry_price = current_price
            stop_loss = entry_price - (self.stop_loss_atr * atr)
            take_profit = entry_price + (self.take_profit_atr * atr)
        else:
            entry_price = current_price
            stop_loss = entry_price + (self.stop_loss_atr * atr)
            take_profit = entry_price - (self.take_profit_atr * atr)
        
        # Calculate divergence strength
        price_diff = abs(point2.price - point1.price)
        rsi_diff = abs(point2.rsi - point1.rsi)
        divergence_strength = min(100, (rsi_diff / self.rsi_tolerance) * 20)
        
        # Calculate quality score
        quality_score = divergence_strength
        
        # Add RSI extreme bonus
        if direction == 'BUY' and current_rsi <= self.rsi_extreme_oversold:
            quality_score += 15
        elif direction == 'SELL' and current_rsi >= self.rsi_extreme_overbought:
            quality_score += 15
        
        # Add price action confirmation bonus
        if self._check_price_action_confirmation(instrument, direction):
            quality_score += 10
        
        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'current_rsi': current_rsi,
            'divergence_strength': divergence_strength,
            'quality_score': quality_score,
            'point1': point1,
            'point2': point2
        }
    
    def _check_price_action_confirmation(self, instrument: str, direction: str) -> bool:
        """Check for price action confirmation"""
        if not self.require_price_action_confirmation:
            return True
        
        if len(self.price_history[instrument]) < 3:
            return False
        
        recent_candles = self.price_history[instrument][-3:]
        
        if direction == 'BUY':
            # Look for bullish reversal patterns
            for candle in recent_candles:
                if candle['close'] > candle['open']:  # Bullish candle
                    return True
        else:
            # Look for bearish reversal patterns
            for candle in recent_candles:
                if candle['close'] < candle['open']:  # Bearish candle
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
    
    def _calculate_current_rsi(self, instrument: str) -> float:
        """Calculate current RSI value"""
        if len(self.price_history[instrument]) < self.rsi_period + 1:
            return 50.0  # Neutral RSI
        
        df = pd.DataFrame(self.price_history[instrument])
        
        # Calculate price changes
        df['price_change'] = df['close'].diff()
        
        # Separate gains and losses
        df['gain'] = df['price_change'].where(df['price_change'] > 0, 0)
        df['loss'] = -df['price_change'].where(df['price_change'] < 0, 0)
        
        # Calculate average gains and losses
        df['avg_gain'] = df['gain'].rolling(window=self.rsi_period).mean()
        df['avg_loss'] = df['loss'].rolling(window=self.rsi_period).mean()
        
        # Calculate RSI
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        current_rsi = df['rsi'].iloc[-1]
        return current_rsi if not pd.isna(current_rsi) else 50.0
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate RSI divergence signals"""
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
                
                # Calculate current RSI
                current_rsi = self._calculate_current_rsi(instrument)
                
                # Detect divergence
                divergence_signal = self._detect_divergence(instrument, market_data.bid, current_rsi)
                
                if divergence_signal and divergence_signal['quality_score'] >= self.min_divergence_quality:
                    signal = TradeSignal(
                        instrument=instrument,
                        side=Side.BUY if divergence_signal['direction'] == 'BUY' else Side.SELL,
                        entry_price=divergence_signal['entry_price'],
                        stop_loss=divergence_signal['stop_loss'],
                        take_profit=divergence_signal['take_profit'],
                        confidence=divergence_signal['quality_score'] / 100,
                        strategy=self.name,
                        metadata={
                            'current_rsi': divergence_signal['current_rsi'],
                            'divergence_strength': divergence_signal['divergence_strength'],
                            'point1_rsi': divergence_signal['point1'].rsi,
                            'point2_rsi': divergence_signal['point2'].rsi,
                            'point1_price': divergence_signal['point1'].price,
                            'point2_price': divergence_signal['point2'].price
                        }
                    )
                    signals.append(signal)
                    
                    logger.info(f"🎯 {instrument} RSI Divergence Signal: {divergence_signal['direction']} @ {divergence_signal['entry_price']:.5f}")
                    logger.info(f"   Current RSI: {divergence_signal['current_rsi']:.1f}")
                    logger.info(f"   Divergence Strength: {divergence_signal['divergence_strength']:.1f}")
                    logger.info(f"   Quality Score: {divergence_signal['quality_score']:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals
