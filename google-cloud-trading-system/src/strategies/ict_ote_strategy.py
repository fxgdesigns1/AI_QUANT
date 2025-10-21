#!/usr/bin/env python3
"""
ICT OTE (Optimal Trade Entry) Strategy
Based on Inner Circle Trader concepts for high-probability entries
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
class ICTLevel:
    """ICT level for OTE entries"""
    price: float
    level_type: str  # 'OTE', 'FVG', 'OB', 'OS'
    strength: float  # 0-100
    timestamp: datetime

class ICTOTEStrategy:
    """
    ICT OTE Strategy Implementation
    
    Key Concepts:
    - Order Blocks (OB): Previous high/low areas where institutions placed large orders
    - Fair Value Gaps (FVG): 3-candle gaps in price action
    - Optimal Trade Entry (OTE): 50-79% retracement of previous move
    - Market Structure: Break of Structure (BOS) and Change of Character (CHoCH)
    """
    
    def __init__(self, instruments: List[str] = None):
        self.name = "ICT OTE Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # ICT Parameters
        self.ote_min_retracement = 0.50  # 50% minimum retracement
        self.ote_max_retracement = 0.79  # 79% maximum retracement
        self.fvg_min_size = 0.0005  # Minimum FVG size
        self.ob_lookback = 20  # Candles to look back for order blocks
        self.bos_confirmation = 3  # Candles to confirm BOS
        
        # Risk Management
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 4.0
        self.max_risk_per_trade = 0.01  # 1%
        
        # Quality Filters
        self.min_ote_strength = 70  # Minimum OTE strength (0-100)
        self.min_fvg_strength = 60  # Minimum FVG strength
        self.require_market_structure = True
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.ict_levels = {inst: [] for inst in self.instruments}
        self.market_structure = {inst: {'trend': 'neutral', 'last_bos': None} for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
        logger.info(f"📊 OTE Range: {self.ote_min_retracement*100}%-{self.ote_max_retracement*100}%")
        logger.info(f"📊 R:R Ratio: 1:{self.take_profit_atr/self.stop_loss_atr:.1f}")
    
    def _prefill_price_history(self):
        """Pre-fill price history for ICT analysis"""
        try:
            import os
            import requests
            
            logger.info("📥 Pre-filling price history for ICT analysis...")
            
            # Get credentials from environment
            api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get last 100 M15 candles for ICT analysis
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
                        
                        # Analyze ICT levels
                        self._analyze_ict_levels(instrument)
                        
                    else:
                        logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"  ⚠️ {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY FOR ICT ANALYSIS!")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not prefill price history: {e}")
    
    def _analyze_ict_levels(self, instrument: str):
        """Analyze ICT levels (Order Blocks, FVGs, OTE zones)"""
        if len(self.price_history[instrument]) < 50:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # 1. Find Order Blocks (OB)
        for i in range(2, len(df) - 2):
            # Bullish OB: Previous high before a strong move down
            if (df.iloc[i-1]['high'] > df.iloc[i]['high'] and 
                df.iloc[i]['close'] < df.iloc[i-1]['low'] and
                df.iloc[i+1]['close'] < df.iloc[i]['close']):
                
                ob_level = ICTLevel(
                    price=df.iloc[i-1]['high'],
                    level_type='OB',
                    strength=80,
                    timestamp=df.iloc[i]['timestamp']
                )
                levels.append(ob_level)
            
            # Bearish OB: Previous low before a strong move up
            elif (df.iloc[i-1]['low'] < df.iloc[i]['low'] and 
                  df.iloc[i]['close'] > df.iloc[i-1]['high'] and
                  df.iloc[i+1]['close'] > df.iloc[i]['close']):
                
                ob_level = ICTLevel(
                    price=df.iloc[i-1]['low'],
                    level_type='OB',
                    strength=80,
                    timestamp=df.iloc[i]['timestamp']
                )
                levels.append(ob_level)
        
        # 2. Find Fair Value Gaps (FVG)
        for i in range(1, len(df) - 1):
            # Bullish FVG: Gap between candle 1 high and candle 3 low
            if (df.iloc[i-1]['high'] < df.iloc[i+1]['low']):
                fvg_size = df.iloc[i+1]['low'] - df.iloc[i-1]['high']
                if fvg_size > self.fvg_min_size:
                    fvg_level = ICTLevel(
                        price=(df.iloc[i-1]['high'] + df.iloc[i+1]['low']) / 2,
                        level_type='FVG',
                        strength=min(100, fvg_size * 1000),  # Scale strength
                        timestamp=df.iloc[i]['timestamp']
                    )
                    levels.append(fvg_level)
            
            # Bearish FVG: Gap between candle 1 low and candle 3 high
            elif (df.iloc[i-1]['low'] > df.iloc[i+1]['high']):
                fvg_size = df.iloc[i-1]['low'] - df.iloc[i+1]['high']
                if fvg_size > self.fvg_min_size:
                    fvg_level = ICTLevel(
                        price=(df.iloc[i-1]['low'] + df.iloc[i+1]['high']) / 2,
                        level_type='FVG',
                        strength=min(100, fvg_size * 1000),
                        timestamp=df.iloc[i]['timestamp']
                    )
                    levels.append(fvg_level)
        
        # 3. Find OTE Zones (50-79% retracements)
        for i in range(20, len(df) - 5):
            # Look for significant moves
            move_start = i - 20
            move_end = i
            
            high_point = df.iloc[move_start:move_end]['high'].max()
            low_point = df.iloc[move_start:move_end]['low'].min()
            move_size = high_point - low_point
            
            if move_size > self.fvg_min_size * 2:  # Significant move
                # Calculate retracement levels
                for retracement in [0.50, 0.618, 0.79]:
                    if df.iloc[move_end]['close'] > low_point:  # Bullish move
                        ote_price = high_point - (move_size * retracement)
                        if low_point <= ote_price <= high_point:
                            ote_level = ICTLevel(
                                price=ote_price,
                                level_type='OTE',
                                strength=100 - (retracement * 50),  # 50% = 75 strength, 79% = 60 strength
                                timestamp=df.iloc[move_end]['timestamp']
                            )
                            levels.append(ote_level)
                    
                    elif df.iloc[move_end]['close'] < high_point:  # Bearish move
                        ote_price = low_point + (move_size * retracement)
                        if low_point <= ote_price <= high_point:
                            ote_level = ICTLevel(
                                price=ote_price,
                                level_type='OTE',
                                strength=100 - (retracement * 50),
                                timestamp=df.iloc[move_end]['timestamp']
                            )
                            levels.append(ote_level)
        
        self.ict_levels[instrument] = levels
        logger.info(f"  📊 {instrument}: Found {len(levels)} ICT levels")
    
    def _detect_market_structure(self, instrument: str, current_price: float) -> str:
        """Detect market structure (BOS, CHoCH)"""
        if len(self.price_history[instrument]) < 10:
            return 'neutral'
        
        df = pd.DataFrame(self.price_history[instrument])
        recent_highs = df.tail(10)['high'].max()
        recent_lows = df.tail(10)['low'].min()
        
        # Simple BOS detection
        if current_price > recent_highs:
            self.market_structure[instrument]['trend'] = 'bullish'
            self.market_structure[instrument]['last_bos'] = 'bullish'
        elif current_price < recent_lows:
            self.market_structure[instrument]['trend'] = 'bearish'
            self.market_structure[instrument]['last_bos'] = 'bearish'
        
        return self.market_structure[instrument]['trend']
    
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
    
    def _find_ote_entry(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Find optimal OTE entry based on ICT levels"""
        if instrument not in self.ict_levels:
            return None
        
        current_levels = self.ict_levels[instrument]
        if not current_levels:
            return None
        
        # Find closest OTE level
        best_ote = None
        min_distance = float('inf')
        
        for level in current_levels:
            if level.level_type == 'OTE' and level.strength >= self.min_ote_strength:
                distance = abs(current_price - level.price)
                if distance < min_distance:
                    min_distance = distance
                    best_ote = level
        
        if best_ote is None:
            return None
        
        # Determine direction based on price relative to OTE
        if current_price <= best_ote.price:
            # Price at or below OTE - potential bullish entry
            direction = 'BUY'
            entry_price = current_price
            stop_loss = entry_price - (self.stop_loss_atr * self._calculate_atr(instrument))
            take_profit = entry_price + (self.take_profit_atr * self._calculate_atr(instrument))
        else:
            # Price above OTE - potential bearish entry
            direction = 'SELL'
            entry_price = current_price
            stop_loss = entry_price + (self.stop_loss_atr * self._calculate_atr(instrument))
            take_profit = entry_price - (self.take_profit_atr * self._calculate_atr(instrument))
        
        # Calculate quality score
        quality_score = best_ote.strength
        
        # Add market structure bonus
        market_structure = self._detect_market_structure(instrument, current_price)
        if market_structure == 'bullish' and direction == 'BUY':
            quality_score += 10
        elif market_structure == 'bearish' and direction == 'SELL':
            quality_score += 10
        
        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'ote_level': best_ote.price,
            'ote_strength': best_ote.strength,
            'quality_score': quality_score,
            'market_structure': market_structure
        }
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate ICT OTE signals"""
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
                
                # Find OTE entry
                ote_entry = self._find_ote_entry(instrument, market_data.bid)
                
                if ote_entry and ote_entry['quality_score'] >= 70:
                    signal = TradeSignal(
                        instrument=instrument,
                        side=Side.BUY if ote_entry['direction'] == 'BUY' else Side.SELL,
                        entry_price=ote_entry['entry_price'],
                        stop_loss=ote_entry['stop_loss'],
                        take_profit=ote_entry['take_profit'],
                        confidence=ote_entry['quality_score'] / 100,
                        strategy=self.name,
                        metadata={
                            'ote_level': ote_entry['ote_level'],
                            'ote_strength': ote_entry['ote_strength'],
                            'market_structure': ote_entry['market_structure'],
                            'ict_type': 'OTE'
                        }
                    )
                    signals.append(signal)
                    
                    logger.info(f"🎯 {instrument} ICT OTE Signal: {ote_entry['direction']} @ {ote_entry['entry_price']:.5f}")
                    logger.info(f"   OTE Level: {ote_entry['ote_level']:.5f} (Strength: {ote_entry['ote_strength']:.1f})")
                    logger.info(f"   Quality Score: {ote_entry['quality_score']:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals
