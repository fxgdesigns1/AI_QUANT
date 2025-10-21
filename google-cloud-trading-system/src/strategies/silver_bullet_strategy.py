#!/usr/bin/env python3
"""
Silver Bullet Strategy
High-probability reversal strategy based on market structure and liquidity
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..core.data_feed import MarketData
from ..core.order_manager import TradeSignal, Side

logger = logging.getLogger(__name__)

@dataclass
class LiquidityLevel:
    """Liquidity level for Silver Bullet entries"""
    price: float
    level_type: str  # 'EQH', 'EQL', 'PDH', 'PDL'
    strength: float  # 0-100
    timestamp: datetime
    volume: float

class SilverBulletStrategy:
    """
    Silver Bullet Strategy Implementation
    
    Key Concepts:
    - Equal Highs/Lows (EQH/EQL): Previous highs/lows at same price level
    - Previous Day High/Low (PDH/PDL): Key levels from previous session
    - Liquidity Sweep: Price breaks level then reverses
    - Market Structure: Break of Structure (BOS) and Change of Character (CHoCH)
    - Time-based entries: Specific times when reversals are more likely
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "Silver Bullet Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Silver Bullet Parameters
        self.eqh_eql_tolerance = 0.0001  # Tolerance for equal highs/lows
        self.pdh_pdl_lookback = 24  # Hours to look back for PDH/PDL
        self.liquidity_sweep_buffer = 0.0002  # Buffer for liquidity sweep
        self.min_liquidity_strength = 70  # Minimum liquidity level strength
        
        # Time-based filters
        self.london_open = 7  # 7 AM London time
        self.ny_open = 13  # 1 PM London time
        self.london_close = 16  # 4 PM London time
        self.ny_close = 21  # 9 PM London time
        
        # Risk Management
        self.stop_loss_atr = 1.5
        self.take_profit_atr = 3.0
        self.max_risk_per_trade = 0.01  # 1%
        
        # Quality Filters
        self.min_volume_ratio = 1.5  # Minimum volume vs average
        self.require_liquidity_sweep = True
        self.require_time_filter = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.liquidity_levels = {inst: [] for inst in self.instruments}
        self.market_structure = {inst: {'trend': 'neutral', 'last_bos': None} for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 EQH/EQL Tolerance: {self.eqh_eql_tolerance}")
        logger.info(f"📊 R:R Ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
    def _prefill_price_history(self):
        """Pre-fill price history for Silver Bullet analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for Silver Bullet analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 200 M15 candles for liquidity analysis
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 200, 'granularity': 'M15', 'price': 'M'}
                    
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
                        
                        # Analyze liquidity levels
                        self._analyze_liquidity_levels(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY FOR SILVER BULLET ANALYSIS!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _analyze_liquidity_levels(self, instrument: str):
        """Analyze liquidity levels (EQH, EQL, PDH, PDL)"""
        if len(self.price_history[instrument]) < 50:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # 1. Find Equal Highs (EQH)
        for i in range(10, len(df) - 10):
            current_high = df.iloc[i]['high']
            
            # Look for similar highs in the past
            similar_highs = 0
            for j in range(max(0, i-50), i):
                if abs(df.iloc[j]['high'] - current_high) <= self.eqh_eql_tolerance:
                    similar_highs += 1
            
            if similar_highs >= 2:  # At least 2 equal highs
                eqh_level = LiquidityLevel(
                    price=current_high,
                    level_type='EQH',
                    strength=min(100, similar_highs * 20),  # More equal highs = stronger
                    timestamp=df.iloc[i]['timestamp'],
                    volume=df.iloc[i]['volume']
                )
                levels.append(eqh_level)
        
        # 2. Find Equal Lows (EQL)
        for i in range(10, len(df) - 10):
            current_low = df.iloc[i]['low']
            
            # Look for similar lows in the past
            similar_lows = 0
            for j in range(max(0, i-50), i):
                if abs(df.iloc[j]['low'] - current_low) <= self.eqh_eql_tolerance:
                    similar_lows += 1
            
            if similar_lows >= 2:  # At least 2 equal lows
                eql_level = LiquidityLevel(
                    price=current_low,
                    level_type='EQL',
                    strength=min(100, similar_lows * 20),
                    timestamp=df.iloc[i]['timestamp'],
                    volume=df.iloc[i]['volume']
                )
                levels.append(eql_level)
        
        # 3. Find Previous Day High (PDH)
        current_time = datetime.now()
        yesterday_start = current_time - timedelta(days=1)
        
        # Get yesterday's high
        yesterday_data = df[df['timestamp'] >= yesterday_start.strftime('%Y-%m-%d')]
        if len(yesterday_data) > 0:
            pdh = yesterday_data['high'].max()
            pdh_level = LiquidityLevel(
                price=pdh,
                level_type='PDH',
                strength=85,  # PDH/PDL are strong levels
                timestamp=yesterday_start,
                volume=yesterday_data['volume'].mean()
            )
            levels.append(pdh_level)
        
        # 4. Find Previous Day Low (PDL)
        if len(yesterday_data) > 0:
            pdl = yesterday_data['low'].min()
            pdl_level = LiquidityLevel(
                price=pdl,
                level_type='PDL',
                strength=85,
                timestamp=yesterday_start,
                volume=yesterday_data['volume'].mean()
            )
            levels.append(pdl_level)
        
        self.liquidity_levels[instrument] = levels
        logger.info(f"  📊 {instrument}: Found {len(levels)} liquidity levels")
    
    def _detect_liquidity_sweep(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Detect if price has swept liquidity and is reversing"""
        if instrument not in self.liquidity_levels:
            return None
        
        current_levels = self.liquidity_levels[instrument]
        if not current_levels:
            return None
        
        # Check for liquidity sweeps
        for level in current_levels:
            if level.strength < self.min_liquidity_strength:
                continue
            
            # Check if price swept the level
            if level.level_type in ['EQH', 'PDH']:
                # Price should have broken above and come back down
                if (current_price <= level.price + self.liquidity_sweep_buffer and
                    current_price >= level.price - self.liquidity_sweep_buffer):
                    
                    # Check recent price action for sweep
                    recent_prices = [candle['high'] for candle in self.price_history[instrument][-5:]]
                    if any(price > level.price + self.liquidity_sweep_buffer for price in recent_prices):
                        return {
                            'level': level,
                            'direction': 'SELL',  # Reversal from liquidity sweep
                            'entry_price': current_price,
                            'sweep_confirmed': True
                        }
            
            elif level.level_type in ['EQL', 'PDL']:
                # Price should have broken below and come back up
                if (current_price >= level.price - self.liquidity_sweep_buffer and
                    current_price <= level.price + self.liquidity_sweep_buffer):
                    
                    # Check recent price action for sweep
                    recent_prices = [candle['low'] for candle in self.price_history[instrument][-5:]]
                    if any(price < level.price - self.liquidity_sweep_buffer for price in recent_prices):
                        return {
                            'level': level,
                            'direction': 'BUY',  # Reversal from liquidity sweep
                            'entry_price': current_price,
                            'sweep_confirmed': True
                        }
        
        return None
    
    def _is_silver_bullet_time(self) -> bool:
        """Check if current time is optimal for Silver Bullet entries"""
        if not self.require_time_filter:
            return True
        
        current_hour = datetime.now().hour
        
        # Silver Bullet times (London time)
        silver_bullet_times = [
            (self.london_open, self.london_open + 2),  # London open
            (self.ny_open, self.ny_open + 2),  # NY open
            (self.london_close, self.london_close + 1),  # London close
            (self.ny_close, self.ny_close + 1)  # NY close
        ]
        
        for start_hour, end_hour in silver_bullet_times:
            if start_hour <= current_hour < end_hour:
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
    
    def _calculate_volume_ratio(self, instrument: str) -> float:
        """Calculate current volume vs average volume"""
        if len(self.price_history[instrument]) < 20:
            return 1.0
        
        recent_volume = self.price_history[instrument][-1]['volume']
        avg_volume = np.mean([candle['volume'] for candle in self.price_history[instrument][-20:]])
        
        return recent_volume / avg_volume if avg_volume > 0 else 1.0
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate Silver Bullet signals"""
        signals = []
        
        # Pre-fill price history if needed
        if not any(self.price_history.values()):
            self._prefill_price_history()
        
        # Check if it's Silver Bullet time
        if not self._is_silver_bullet_time():
            return signals
        
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
                
                # Check for liquidity sweep
                sweep_signal = self._detect_liquidity_sweep(instrument, market_data.bid)
                
                if sweep_signal and sweep_signal['sweep_confirmed']:
                    # Calculate stop loss and take profit
                    atr = self._calculate_atr(instrument)
                    
                    if sweep_signal['direction'] == 'BUY':
                        entry_price = sweep_signal['entry_price']
                        stop_loss = entry_price - (self.stop_loss_atr * atr)
                        take_profit = entry_price + (self.take_profit_atr * atr)
                    else:
                        entry_price = sweep_signal['entry_price']
                        stop_loss = entry_price + (self.stop_loss_atr * atr)
                        take_profit = entry_price - (self.take_profit_atr * atr)
                    
                    # Calculate quality score
                    quality_score = sweep_signal['level'].strength
                    
                    # Add volume bonus
                    volume_ratio = self._calculate_volume_ratio(instrument)
                    if volume_ratio >= self.min_volume_ratio:
                        quality_score += 10
                    
                    # Add time bonus
                    if self._is_silver_bullet_time():
                        quality_score += 5
                    
                    if quality_score >= 75:
                        signal = TradeSignal(
                            instrument=instrument,
                            side=Side.BUY if sweep_signal['direction'] == 'BUY' else Side.SELL,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            confidence=quality_score / 100,
                            strategy=self.name,
                            metadata={
                                'liquidity_level': sweep_signal['level'].price,
                                'level_type': sweep_signal['level'].level_type,
                                'level_strength': sweep_signal['level'].strength,
                                'volume_ratio': volume_ratio,
                                'silver_bullet_time': True
                            }
                        )
                        signals.append(signal)
                        
                        logger.info(f"🎯 {instrument} Silver Bullet Signal: {sweep_signal['direction']} @ {entry_price:.5f}")
                        logger.info(f"   Liquidity Level: {sweep_signal['level'].price:.5f} ({sweep_signal['level'].level_type})")
                        logger.info(f"   Quality Score: {quality_score:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals
