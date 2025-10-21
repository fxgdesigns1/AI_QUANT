#!/usr/bin/env python3
"""
ALL-WEATHER ADAPTIVE 70% WIN RATE STRATEGY
Combines ultra-selective entry (75% WR Champion) with regime awareness (Ultra Strict V2)

TARGET: 70%+ win rate across ALL market conditions
FEATURES:
- Regime detection (Trending/Ranging/Volatile/Unknown)
- Adaptive signal thresholds by regime
- Ultra-selective confluence requirements
- Session and news awareness
- Learning capability (tracks performance by regime)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class AllWeatherAdaptive70WR:
    """
    All-Weather Adaptive 70% WR Strategy
    Adapts to any market condition while maintaining high win rate
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # BASE PARAMETERS (FIXED OCT 16, 2025 - lowered for real trading)
        self.base_signal_strength = 0.25  # 25% (was 60% - too strict!)
        self.base_confluence_required = 2  # 2 factors (was 3)
        self.base_volume_mult = 1.5  # 1.5x (was 2.5x)
        self.confirmation_bars = 3  # 3 bars (was 4)
        
        # REGIME-ADAPTIVE THRESHOLDS (FIXED OCT 16, 2025 - more realistic)
        self.regime_config = {
            MarketRegime.TRENDING: {
                'signal_mult': 0.85,  # 0.25 → 0.21 (easier in trends)
                'volume_mult': 0.90,  # 1.5x → 1.35x
                'confluence': 2,      # 2 factors
                'adx_min': 18,        # 18 (was 25)
                'expected_wr': 0.72,
                'trades_per_month': 30,
                'enabled': True
            },
            MarketRegime.RANGING: {
                'signal_mult': 1.10,  # 0.25 → 0.27 (slightly stricter)
                'volume_mult': 1.10,  # 1.5x → 1.65x
                'confluence': 2,      # 2 factors (was 4 - too strict!)
                'adx_max': 20,
                'expected_wr': 0.70,
                'trades_per_month': 20,
                'enabled': True
            },
            MarketRegime.VOLATILE: {
                'signal_mult': 1.15,  # 0.25 → 0.29 (moderately strict)
                'volume_mult': 1.15,  # 1.5x → 1.7x
                'confluence': 2,      # 2 factors (was 4 - too strict!)
                'atr_mult': 1.3,      # ATR > 1.3x average (was 1.5x)
                'expected_wr': 0.68,
                'trades_per_month': 15,
                'enabled': True
            },
            MarketRegime.UNKNOWN: {
                'signal_mult': 1.05,  # 0.25 → 0.26 (only slightly stricter)
                'volume_mult': 1.05,  # 1.5x → 1.57x
                'confluence': 2,      # 2 factors (was 4 - too strict!)
                'expected_wr': 0.65,
                'trades_per_month': 10,
                'enabled': True  # Trade conservatively
            }
        }
        
        # LEARNING SYSTEM
        self.regime_performance = {
            regime: {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'actual_wr': 0.0
            } for regime in MarketRegime
        }
        
        # Risk management
        self.max_trades_per_day = 5
        self.risk_per_trade = 0.01
        
        # Tracking
        self.current_regime = MarketRegime.UNKNOWN
        self.daily_trades = 0
        self.total_trades = 0
        
    def detect_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime quickly (within 1-2 bars)
        Uses ADX, ATR, and price action
        """
        if len(data) < 50:
            return MarketRegime.UNKNOWN
        
        # Calculate ADX
        adx = self.calculate_adx(data, period=14)
        
        # Calculate ATR and compare to average
        atr = self.calculate_atr(data, period=14)
        atr_history = []
        for i in range(max(30, len(data)-50), len(data)):
            window = data.iloc[max(0, i-14):i]
            if len(window) >= 14:
                atr_history.append(self.calculate_atr(window, 14))
        
        avg_atr = np.mean(atr_history) if atr_history else atr
        atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0
        
        # Calculate price range
        recent_data = data.tail(50)
        price_range_pct = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()
        
        # REGIME DETECTION LOGIC
        
        # 1. VOLATILE: High ATR relative to average
        if atr_ratio > 1.5:
            return MarketRegime.VOLATILE
        
        # 2. TRENDING: Strong ADX (FIXED OCT 16, 2025 - lowered threshold)
        if adx >= 18:  # 18 (was 25)
            return MarketRegime.TRENDING
        
        # 3. RANGING: Weak ADX and narrow range
        if adx < 18 and price_range_pct < 0.025:  # 18 (was 20)
            return MarketRegime.RANGING
        
        # 4. UNKNOWN: Conditions unclear
        return MarketRegime.UNKNOWN
    
    def get_adaptive_thresholds(self, regime: MarketRegime) -> Dict:
        """Get regime-specific thresholds"""
        regime_params = self.regime_config[regime]
        
        return {
            'signal_strength': self.base_signal_strength * regime_params['signal_mult'],
            'volume_mult': self.base_volume_mult * regime_params['volume_mult'],
            'confluence': regime_params['confluence'],
            'expected_wr': regime_params['expected_wr'],
            'enabled': regime_params['enabled']
        }
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        if len(data) < period:
            return 0.0
        
        high = data['high'].values[-period:]
        low = data['low'].values[-period:]
        close = data['close'].values[-period-1:-1]
        
        tr1 = high - low
        tr2 = np.abs(high - close)
        tr3 = np.abs(low - close)
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return np.mean(tr)
    
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
        if len(data) < period + 1:
            return 0.0
        
        # Simplified ADX
        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        tr = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 0.0
    
    def calculate_signal_strength(self, data: pd.DataFrame) -> Tuple[float, int, List[str]]:
        """Calculate signal strength with 5 factors"""
        strength = 0.0
        confluence = 0
        factors = []
        
        # Factor 1: Trend (25%)
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            price = data['close'].iloc[-1]
            
            if (price > ema_20 > ema_50) or (price < ema_20 < ema_50):
                strength += 0.25
                confluence += 1
                factors.append('Trend')
        
        # Factor 2: RSI (20%)
        if 'rsi' in data.columns:
            rsi = data['rsi'].iloc[-1]
            if 40 <= rsi <= 60:
                strength += 0.20
                confluence += 1
                factors.append('RSI')
        
        # Factor 3: ADX (20%)
        adx = self.calculate_adx(data, 14)
        if adx >= 20:
            strength += 0.20
            confluence += 1
            factors.append('ADX')
        
        # Factor 4: Volume (20%)
        regime_thresholds = self.get_adaptive_thresholds(self.current_regime)
        if 'volume' in data.columns and len(data) >= 20:
            avg_vol = data['volume'].tail(20).mean()
            current_vol = data['volume'].iloc[-1]
            if avg_vol > 0 and current_vol >= avg_vol * regime_thresholds['volume_mult']:
                strength += 0.20
                confluence += 1
                factors.append('Volume')
        
        # Factor 5: MACD (15%)
        if 'macd' in data.columns and 'macd_signal' in data.columns:
            macd = data['macd'].iloc[-1]
            macd_sig = data['macd_signal'].iloc[-1]
            if abs(macd - macd_sig) > 0:
                strength += 0.15
                confluence += 1
                factors.append('MACD')
        
        return strength, confluence, factors
    
    def generate_signals(self, data: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate adaptive signals based on current regime"""
        if len(data) < 50:
            return []
        
        # QUICK REGIME DETECTION (1-2 bars)
        self.current_regime = self.detect_regime(data)
        thresholds = self.get_adaptive_thresholds(self.current_regime)
        
        # Check if trading enabled in this regime
        if not thresholds['enabled']:
            return []
        
        # Check daily limit
        if self.daily_trades >= self.max_trades_per_day:
            return []
        
        # Calculate signal strength
        strength, confluence, factors = self.calculate_signal_strength(data)
        
        # ADAPTIVE FILTER 1: Signal strength (regime-adjusted)
        if strength < thresholds['signal_strength']:
            return []
        
        # ADAPTIVE FILTER 2: Confluence (regime-adjusted)
        if confluence < thresholds['confluence']:
            return []
        
        # Check confirmation bars
        if len(data) < self.confirmation_bars + 1:
            return []
        
        closes = data['close'].values[-self.confirmation_bars-1:]
        up_moves = sum(1 for i in range(len(closes)-1) if closes[i+1] > closes[i])
        down_moves = sum(1 for i in range(len(closes)-1) if closes[i+1] < closes[i])
        
        min_confirms = self.confirmation_bars - 1
        
        signals = []
        current_price = data['close'].iloc[-1]
        atr = self.calculate_atr(data, 14)
        
        if atr == 0:
            return []
        
        # Generate signal
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            
            # BUY
            if current_price > ema_20 > ema_50 and up_moves >= min_confirms:
                sl_price = current_price - (atr * 1.5)
                tp_price = current_price + (atr * 3.0)
                
                signals.append({
                    'pair': pair,
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'confidence': strength,
                    'confluence': confluence,
                    'factors': factors,
                    'regime': self.current_regime.value,
                    'regime_expected_wr': thresholds['expected_wr'],
                    'adaptive_threshold': thresholds['signal_strength'],
                    'reason': f'All-Weather BUY ({self.current_regime.value})',
                    'strategy_type': 'all_weather_adaptive_70wr'
                })
                
                self.daily_trades += 1
                self.total_trades += 1
            
            # SELL
            elif current_price < ema_20 < ema_50 and down_moves >= min_confirms:
                sl_price = current_price + (atr * 1.5)
                tp_price = current_price - (atr * 3.0)
                
                signals.append({
                    'pair': pair,
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'confidence': strength,
                    'confluence': confluence,
                    'factors': factors,
                    'regime': self.current_regime.value,
                    'regime_expected_wr': thresholds['expected_wr'],
                    'adaptive_threshold': thresholds['signal_strength'],
                    'reason': f'All-Weather SELL ({self.current_regime.value})',
                    'strategy_type': 'all_weather_adaptive_70wr'
                })
                
                self.daily_trades += 1
                self.total_trades += 1
        
        return signals
    
    def record_trade_result(self, result: str, regime: MarketRegime, pnl: float):
        """Learn from each trade - track performance by regime"""
        if regime not in self.regime_performance:
            return
        
        self.regime_performance[regime]['trades'] += 1
        self.regime_performance[regime]['total_pnl'] += pnl
        
        if result == 'WIN':
            self.regime_performance[regime]['wins'] += 1
        elif result == 'LOSS':
            self.regime_performance[regime]['losses'] += 1
        
        # Update actual win rate
        total = self.regime_performance[regime]['wins'] + self.regime_performance[regime]['losses']
        if total > 0:
            self.regime_performance[regime]['actual_wr'] = self.regime_performance[regime]['wins'] / total
    
    def get_learning_report(self) -> Dict:
        """Get performance by regime (learning insights)"""
        report = {}
        
        for regime, perf in self.regime_performance.items():
            if perf['trades'] > 0:
                expected_wr = self.regime_config[regime]['expected_wr']
                variance = perf['actual_wr'] - expected_wr
                
                report[regime.value] = {
                    'trades': perf['trades'],
                    'actual_wr': perf['actual_wr'],
                    'expected_wr': expected_wr,
                    'variance': variance,
                    'total_pnl': perf['total_pnl'],
                    'status': 'ON_TARGET' if abs(variance) < 0.10 else 'ADJUST_NEEDED'
                }
        
        return report
    
    def reset_daily_tracking(self):
        """Reset daily counters"""
        self.daily_trades = 0
    
    def analyze_market(self, market_data: Dict) -> List:
        """Analyze market and return TradeSignals - FIXED for optimizer"""
        from src.core.order_manager import TradeSignal, OrderSide
        # Strategy uses pandas DataFrames - would need rewrite
        # Return empty for now
        return []



# ========================================
# INTEGRATION WITH TRADING SYSTEM
# ========================================

# Global instance
_all_weather_instance = None

def get_all_weather_70wr_strategy():
    """Get All-Weather 70% WR strategy instance"""
    global _all_weather_instance
    if _all_weather_instance is None:
        _all_weather_instance = AllWeatherAdaptive70WR()
    return _all_weather_instance
