#!/usr/bin/env python3
"""
Scalping Strategy
High-frequency trading strategy for quick profits from small price movements
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
class ScalpLevel:
    """Scalping level for analysis"""
    price: float
    strength: float
    timestamp: datetime
    type: str  # 'support', 'resistance', 'pivot'

class ScalpingStrategy:
    """
    Scalping Strategy Implementation
    
    Key Concepts:
    - Quick entries and exits (1-5 minute holds)
    - Small profit targets (5-15 pips)
    - Tight stop losses (3-8 pips)
    - High win rate focus (70%+)
    - Volume and spread analysis
    - Order flow patterns
    - Support/resistance levels
    - Momentum confirmation
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "Scalping Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Scalping Parameters
        self.scalp_timeframe = 'M1'  # 1-minute scalping
        self.max_hold_time = 5  # Maximum hold time in minutes
        self.min_profit_pips = 5  # Minimum profit target in pips
        self.max_profit_pips = 15  # Maximum profit target in pips
        self.stop_loss_pips = 8  # Stop loss in pips
        self.trailing_stop_pips = 3  # Trailing stop in pips
        
        # Entry Conditions
        self.min_momentum = 0.0001  # Minimum momentum for entry
        self.max_spread_pips = 2  # Maximum spread for entry
        self.min_volume_ratio = 1.2  # Minimum volume ratio
        self.require_breakout = True  # Require breakout confirmation
        
        # Risk Management
        self.max_risk_per_trade = 0.005  # 0.5% per trade
        self.max_daily_trades = 20  # Maximum trades per day
        self.max_concurrent_positions = 3  # Maximum concurrent positions
        
        # Quality Filters
        self.min_quality_score = 75  # Minimum quality score
        self.require_volume_confirmation = True
        self.require_momentum_confirmation = True
        self.require_level_confirmation = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.scalp_levels = {inst: [] for inst in self.instruments}
        self.volume_profile = {inst: [] for inst in self.instruments}
        
        # Trade tracking
        self.daily_trades = {inst: 0 for inst in self.instruments}
        self.last_trade_time = {inst: None for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 Max Hold Time: {self.max_hold_time} minutes")
        logger.info(f"📊 Profit Target: {self.min_profit_pips}-{self.max_profit_pips} pips")
        logger.info(f"📊 Stop Loss: {self.stop_loss_pips} pips")
    
    def _prefill_price_history(self):
        """Pre-fill price history for scalping analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for scalping analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 200 M1 candles for scalping analysis
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 200, 'granularity': 'M1', 'price': 'M'}
                    
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
                        
                        logger.info(f"  ✅ {instrument}: {len(self.price_history[instrument])} M1 bars loaded")
                        
                        # Calculate scalping levels and volume profile
                        self._calculate_scalp_levels(instrument)
                        self._calculate_volume_profile(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total M1 bars - READY FOR SCALPING!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _calculate_scalp_levels(self, instrument: str):
        """Calculate key scalping levels (support/resistance/pivots)"""
        if len(self.price_history[instrument]) < 20:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # Find pivot points
        for i in range(5, len(df) - 5):
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']
            
            # Check for pivot high
            left_highs = [df.iloc[j]['high'] for j in range(i-5, i)]
            right_highs = [df.iloc[j]['high'] for j in range(i+1, i+6)]
            
            if current_high > max(left_highs) and current_high > max(right_highs):
                level = ScalpLevel(
                    price=current_high,
                    strength=len([h for h in left_highs + right_highs if h < current_high * 0.999]),
                    timestamp=df.iloc[i]['timestamp'],
                    type='resistance'
                )
                levels.append(level)
            
            # Check for pivot low
            left_lows = [df.iloc[j]['low'] for j in range(i-5, i)]
            right_lows = [df.iloc[j]['low'] for j in range(i+1, i+6)]
            
            if current_low < min(left_lows) and current_low < min(right_lows):
                level = ScalpLevel(
                    price=current_low,
                    strength=len([l for l in left_lows + right_lows if l > current_low * 1.001]),
                    timestamp=df.iloc[i]['timestamp'],
                    type='support'
                )
                levels.append(level)
        
        # Keep only recent levels
        recent_levels = [l for l in levels if l.strength >= 3]
        self.scalp_levels[instrument] = recent_levels[-10:]  # Keep last 10 levels
        
        logger.info(f"  📊 {instrument}: Found {len(recent_levels)} scalping levels")
    
    def _calculate_volume_profile(self, instrument: str):
        """Calculate volume profile for scalping"""
        if len(self.price_history[instrument]) < 50:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        
        # Calculate volume-weighted average price (VWAP)
        df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
        
        # Calculate volume momentum
        df['volume_ma'] = df['volume'].rolling(10).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Store volume profile
        volume_data = []
        for i, row in df.iterrows():
            if not pd.isna(row['vwap']):
                volume_data.append({
                    'timestamp': row['timestamp'],
                    'vwap': row['vwap'],
                    'volume_ratio': row['volume_ratio'],
                    'price': row['close']
                })
        
        self.volume_profile[instrument] = volume_data
        logger.info(f"  📊 {instrument}: Calculated volume profile for {len(volume_data)} periods")
    
    def _check_scalp_conditions(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Check if scalping conditions are met"""
        if instrument not in self.scalp_levels:
            return None
        
        # Check if we can trade (daily limits)
        if self.daily_trades[instrument] >= self.max_daily_trades:
            return None
        
        # Check time since last trade
        if (self.last_trade_time[instrument] and 
            (datetime.now() - self.last_trade_time[instrument]).total_seconds() < 60):
            return None
        
        # Check spread
        spread = abs(current_price - (current_price * 0.999))  # Approximate spread
        if spread > self.max_spread_pips * 0.0001:
            return None
        
        # Check momentum
        momentum = self._calculate_momentum(instrument)
        if abs(momentum) < self.min_momentum:
            return None
        
        # Check volume
        volume_ratio = self._get_current_volume_ratio(instrument)
        if volume_ratio < self.min_volume_ratio:
            return None
        
        # Check for level breakout
        breakout_signal = self._check_level_breakout(instrument, current_price)
        if not breakout_signal:
            return None
        
        return {
            'momentum': momentum,
            'volume_ratio': volume_ratio,
            'breakout_signal': breakout_signal,
            'spread': spread
        }
    
    def _calculate_momentum(self, instrument: str, period: int = 5) -> float:
        """Calculate short-term momentum"""
        if len(self.price_history[instrument]) < period + 1:
            return 0.0
        
        recent_prices = [candle['close'] for candle in self.price_history[instrument][-period:]]
        momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        return momentum
    
    def _get_current_volume_ratio(self, instrument: str) -> float:
        """Get current volume ratio"""
        if not self.volume_profile[instrument]:
            return 1.0
        
        current_volume = self.volume_profile[instrument][-1]['volume_ratio']
        return current_volume if not pd.isna(current_volume) else 1.0
    
    def _check_level_breakout(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Check for level breakout"""
        levels = self.scalp_levels[instrument]
        if not levels:
            return None
        
        # Check for resistance breakout (bullish)
        for level in levels:
            if level.type == 'resistance' and current_price > level.price * 1.0001:
                return {
                    'direction': 'BUY',
                    'level_price': level.price,
                    'level_strength': level.strength,
                    'breakout_distance': current_price - level.price
                }
        
        # Check for support breakdown (bearish)
        for level in levels:
            if level.type == 'support' and current_price < level.price * 0.9999:
                return {
                    'direction': 'SELL',
                    'level_price': level.price,
                    'level_strength': level.strength,
                    'breakout_distance': level.price - current_price
                }
        
        return None
    
    def _calculate_scalp_targets(self, instrument: str, direction: str, entry_price: float) -> Tuple[float, float]:
        """Calculate scalping targets"""
        # Calculate pip value
        pip_value = 0.0001 if 'JPY' not in instrument else 0.01
        
        if direction == 'BUY':
            take_profit = entry_price + (self.min_profit_pips * pip_value)
            stop_loss = entry_price - (self.stop_loss_pips * pip_value)
        else:
            take_profit = entry_price - (self.min_profit_pips * pip_value)
            stop_loss = entry_price + (self.stop_loss_pips * pip_value)
        
        return take_profit, stop_loss
    
    def _calculate_quality_score(self, conditions: Dict, breakout_signal: Dict) -> float:
        """Calculate scalping quality score"""
        score = 50  # Base score
        
        # Momentum bonus
        momentum_strength = abs(conditions['momentum']) * 10000
        score += min(20, momentum_strength * 100)
        
        # Volume bonus
        volume_bonus = (conditions['volume_ratio'] - 1) * 10
        score += min(15, volume_bonus)
        
        # Level strength bonus
        level_bonus = breakout_signal['level_strength'] * 2
        score += min(15, level_bonus)
        
        # Breakout distance bonus
        distance_bonus = breakout_signal['breakout_distance'] * 10000
        score += min(10, distance_bonus)
        
        return min(100, score)
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate scalping signals"""
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
                
                # Check scalping conditions
                conditions = self._check_scalp_conditions(instrument, market_data.bid)
                
                if conditions:
                    breakout_signal = conditions['breakout_signal']
                    quality_score = self._calculate_quality_score(conditions, breakout_signal)
                    
                    if quality_score >= self.min_quality_score:
                        # Calculate targets
                        take_profit, stop_loss = self._calculate_scalp_targets(
                            instrument, breakout_signal['direction'], market_data.bid
                        )
                        
                        signal = TradeSignal(
                            instrument=instrument,
                            side=Side.BUY if breakout_signal['direction'] == 'BUY' else Side.SELL,
                            entry_price=market_data.bid,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            confidence=quality_score / 100,
                            strategy=self.name,
                            metadata={
                                'momentum': conditions['momentum'],
                                'volume_ratio': conditions['volume_ratio'],
                                'level_price': breakout_signal['level_price'],
                                'level_strength': breakout_signal['level_strength'],
                                'breakout_distance': breakout_signal['breakout_distance'],
                                'max_hold_time': self.max_hold_time,
                                'scalp_type': 'breakout'
                            }
                        )
                        signals.append(signal)
                        
                        # Update trade tracking
                        self.daily_trades[instrument] += 1
                        self.last_trade_time[instrument] = datetime.now()
                        
                        logger.info(f"⚡ {instrument} Scalping Signal: {breakout_signal['direction']} @ {market_data.bid:.5f}")
                        logger.info(f"   Momentum: {conditions['momentum']:.6f}")
                        logger.info(f"   Volume Ratio: {conditions['volume_ratio']:.2f}")
                        logger.info(f"   Level Strength: {breakout_signal['level_strength']}")
                        logger.info(f"   Quality Score: {quality_score:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals

def get_scalping_strategy(instruments=None):
    """Get Scalping Strategy instance"""
    return ScalpingStrategy(instruments=instruments)
