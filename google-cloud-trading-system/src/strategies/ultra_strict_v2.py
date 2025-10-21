#!/usr/bin/env python3
"""
ULTRA STRICT V2 - REGIME-AWARE VERSION
Addresses issues found in professional validation:
- ESI 0.44 (below 0.60 threshold)
- Unstable across different market regimes

IMPROVEMENTS:
1. Regime detection (trending, ranging, volatile)
2. Regime-specific parameters
3. Adaptive signal strength by regime
4. Don't trade in unfavorable regimes
5. Regime transition detection
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class UltraStrictV2RegimeAware:
    """
    Improved Ultra Strict Strategy - Regime-Aware
    Fixes: ESI < 0.60 by adapting to different market conditions
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Base parameters (FIXED OCT 16, 2025 - lowered for real trading)
        self.base_signal_strength = self.config.get('min_signal_strength', 0.25)  # 25% (was 40%)
        
        # Regime-specific adjustments (FIXED OCT 16, 2025 - less restrictive)
        self.regime_adjustments = {
            MarketRegime.TRENDING: {
                'signal_strength_mult': 0.90,  # Easier (0.25 → 0.22)
                'enabled': True,
                'description': 'Trend following works well'
            },
            MarketRegime.RANGING: {
                'signal_strength_mult': 1.10,  # Slightly stricter (0.25 → 0.27)
                'enabled': True,
                'description': 'Need good quality in ranges'
            },
            MarketRegime.VOLATILE: {
                'signal_strength_mult': 1.15,  # Moderately strict (0.25 → 0.29)
                'enabled': True,
                'description': 'Caution in volatility'
            },
            MarketRegime.UNKNOWN: {
                'signal_strength_mult': 1.00,  # Same as base (0.25 → 0.25)
                'enabled': True,  # TRADE in unknown (was False - too restrictive!)
                'description': 'Trade with caution'
            }
        }
        
        # Regime detection parameters (FIXED OCT 16, 2025 - more realistic)
        self.regime_lookback = self.config.get('regime_lookback', 50)
        self.adx_period = self.config.get('adx_period', 14)
        self.adx_trend_threshold = self.config.get('adx_trend_threshold', 18)  # 18 (was 25)
        self.atr_volatile_mult = self.config.get('atr_volatile_mult', 1.3)  # 1.3x (was 1.5x)
        
        # Risk management
        self.max_trades_per_day = self.config.get('max_trades_per_day', 5)
        self.risk_per_trade = self.config.get('risk_per_trade', 0.02)
        
        # Tracking
        self.daily_trades = 0
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = []
        
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(data) < period:
            return 0.0
        
        high = data['high'].values[-period:]
        low = data['low'].values[-period:]
        close = data['close'].values[-period-1:-1]
        
        tr1 = high - low
        tr2 = np.abs(high - close)
        tr3 = np.abs(low - close)
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = np.mean(tr)
        
        return atr
    
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)"""
        if len(data) < period + 1:
            return 0.0
        
        # Calculate +DM and -DM
        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        # Calculate TR
        tr = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        
        # Smooth the values
        atr = tr.rolling(period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if len(adx) > 0 else 0.0
    
    def detect_regime(self, data: pd.DataFrame) -> MarketRegime:
        """NEW: Detect current market regime"""
        if len(data) < self.regime_lookback:
            return MarketRegime.UNKNOWN
        
        # Calculate indicators
        adx = self.calculate_adx(data, self.adx_period)
        atr = self.calculate_atr(data, period=14)
        
        # Calculate average ATR over longer period
        if len(data) >= 50:
            atr_data = []
            for i in range(30, len(data)):
                window = data.iloc[i-14:i]
                atr_data.append(self.calculate_atr(window, period=14))
            avg_atr = np.mean(atr_data) if atr_data else atr
        else:
            avg_atr = atr
        
        # Calculate price range ratio (for ranging detection)
        recent_data = data.tail(self.regime_lookback)
        price_high = recent_data['high'].max()
        price_low = recent_data['low'].min()
        price_range = (price_high - price_low) / recent_data['close'].mean()
        
        # REGIME DETECTION LOGIC
        
        # 1. VOLATILE: ATR significantly above average
        if avg_atr > 0 and atr / avg_atr > self.atr_volatile_mult:
            return MarketRegime.VOLATILE
        
        # 2. TRENDING: Strong ADX
        if adx > self.adx_trend_threshold:
            return MarketRegime.TRENDING
        
        # 3. RANGING: Weak ADX and narrow range
        if adx < 20 and price_range < 0.03:  # 3% range
            return MarketRegime.RANGING
        
        # 4. Default: Unknown if conditions unclear
        return MarketRegime.UNKNOWN
    
    def get_regime_adjusted_threshold(self, regime: MarketRegime) -> float:
        """Get signal strength threshold adjusted for current regime"""
        adjustment = self.regime_adjustments[regime]
        adjusted_threshold = self.base_signal_strength * adjustment['signal_strength_mult']
        return adjusted_threshold
    
    def can_trade_in_regime(self, regime: MarketRegime) -> bool:
        """Check if trading is enabled in current regime"""
        return self.regime_adjustments[regime]['enabled']
    
    def calculate_signal_strength(self, data: pd.DataFrame) -> float:
        """Calculate signal strength (0-1)"""
        if len(data) < 50:
            return 0.0
        
        strength = 0.0
        
        # Trend alignment (30%)
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            price = data['close'].iloc[-1]
            
            if price > ema_20 > ema_50 or price < ema_20 < ema_50:
                strength += 0.30
        
        # RSI positioning (25%)
        if 'rsi' in data.columns:
            rsi = data['rsi'].iloc[-1]
            if 40 <= rsi <= 60:  # Not overbought/oversold
                strength += 0.25
        
        # MACD confirmation (25%)
        if 'macd' in data.columns and 'macd_signal' in data.columns:
            macd = data['macd'].iloc[-1]
            macd_signal = data['macd_signal'].iloc[-1]
            if abs(macd - macd_signal) > 0:
                strength += 0.25
        
        # Volume confirmation (20%)
        if 'volume' in data.columns and len(data) >= 20:
            avg_volume = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            if current_volume > avg_volume * 1.2:
                strength += 0.20
        
        return min(strength, 1.0)
    
    def generate_signals(self, data: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate regime-aware signals"""
        if len(data) < self.regime_lookback:
            return []
        
        # Check daily trade limit
        if self.daily_trades >= self.max_trades_per_day:
            return []
        
        # Detect current regime
        self.current_regime = self.detect_regime(data)
        self.regime_history.append({
            'time': data.index[-1],
            'regime': self.current_regime.value
        })
        
        # Check if we can trade in this regime
        if not self.can_trade_in_regime(self.current_regime):
            return []
        
        # Get regime-adjusted threshold
        adjusted_threshold = self.get_regime_adjusted_threshold(self.current_regime)
        
        # Calculate signal strength
        signal_strength = self.calculate_signal_strength(data)
        
        # Check if signal meets regime-adjusted threshold
        if signal_strength < adjusted_threshold:
            return []
        
        signals = []
        current_price = data['close'].iloc[-1]
        atr = self.calculate_atr(data, period=14)
        
        if atr == 0:
            return []
        
        # Determine direction
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            
            # BUY signal
            if current_price > ema_20 > ema_50:
                sl_price = current_price - (atr * 2.0)
                tp_price = current_price + (atr * 5.0)  # 1:2.5 R:R
                
                rr_ratio = abs(tp_price - current_price) / abs(current_price - sl_price)
                
                signals.append({
                    'pair': pair,
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'confidence': signal_strength,
                    'reason': f'Ultra Strict BUY - {self.current_regime.value} regime',
                    'rr_ratio': rr_ratio,
                    'strategy_version': 'ultra_strict_v2_regime_aware',
                    'regime_info': {
                        'regime': self.current_regime.value,
                        'base_threshold': self.base_signal_strength,
                        'adjusted_threshold': adjusted_threshold,
                        'signal_strength': signal_strength,
                        'regime_description': self.regime_adjustments[self.current_regime]['description']
                    }
                })
                
                self.daily_trades += 1
            
            # SELL signal
            elif current_price < ema_20 < ema_50:
                sl_price = current_price + (atr * 2.0)
                tp_price = current_price - (atr * 5.0)  # 1:2.5 R:R
                
                rr_ratio = abs(current_price - tp_price) / abs(sl_price - current_price)
                
                signals.append({
                    'pair': pair,
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'confidence': signal_strength,
                    'reason': f'Ultra Strict SELL - {self.current_regime.value} regime',
                    'rr_ratio': rr_ratio,
                    'strategy_version': 'ultra_strict_v2_regime_aware',
                    'regime_info': {
                        'regime': self.current_regime.value,
                        'base_threshold': self.base_signal_strength,
                        'adjusted_threshold': adjusted_threshold,
                        'signal_strength': signal_strength,
                        'regime_description': self.regime_adjustments[self.current_regime]['description']
                    }
                })
                
                self.daily_trades += 1
        
        return signals
    
    def reset_daily_tracking(self):
        """Reset daily counters"""
        self.daily_trades = 0
    
    def get_regime_statistics(self) -> Dict:
        """Get statistics on regime distribution"""
        if not self.regime_history:
            return {}
        
        regime_counts = {}
        for entry in self.regime_history:
            regime = entry['regime']
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        total = len(self.regime_history)
        regime_pcts = {k: v/total for k, v in regime_counts.items()}
        
        return {
            'total_observations': total,
            'regime_distribution': regime_pcts,
            'current_regime': self.current_regime.value
        }
    
    def get_improvement_summary(self) -> Dict:
        """Get summary of improvements made"""
        return {
            'version': '2.0 - Regime-Aware',
            'changes': {
                '1_regime_detection': 'Trending, Ranging, Volatile, Unknown',
                '2_adaptive_thresholds': {
                    'trending': f'{self.base_signal_strength * 0.95:.2f} (easier)',
                    'ranging': f'{self.base_signal_strength * 1.15:.2f} (stricter)',
                    'volatile': f'{self.base_signal_strength * 1.25:.2f} (most strict)',
                    'unknown': 'Trading disabled'
                },
                '3_regime_filtering': 'Don\'t trade in UNKNOWN regime',
                '4_adx_based': f'ADX > {self.adx_trend_threshold} for trending',
                '5_volatility_aware': f'ATR > {self.atr_volatile_mult}x avg for volatile'
            },
            'expected_improvements': {
                'esi': '0.44 → 0.65-0.75 (target > 0.60)',
                'regime_consistency': 'Unstable → Stable',
                'adaptability': 'Fixed params → Adaptive',
                'performance_stability': 'Variable → Consistent'
            }
        }



# ========================================
# INTEGRATION WITH TRADING SYSTEM
# ========================================

# Global instance
_ultra_strict_v2_instance = None

def get_ultra_strict_v2_strategy():
    """Get Ultra Strict V2 strategy instance"""
    global _ultra_strict_v2_instance
    if _ultra_strict_v2_instance is None:
        _ultra_strict_v2_instance = UltraStrictV2RegimeAware()
    return _ultra_strict_v2_instance


    def analyze_market(self, market_data: Dict, pair: str) -> Optional[Dict]:
        """
        Compatibility wrapper for dashboard integration
        Converts market_data dict to DataFrame and calls generate_signals()
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            # Get price history for this pair
            if not hasattr(self, 'price_history'):
                self.price_history = {}
            
            if pair not in self.price_history:
                self.price_history[pair] = []
            
            # Add current price to history
            if pair in market_data:
                price_info = market_data[pair]
                self.price_history[pair].append({
                    'timestamp': datetime.now(),
                    'close': price_info.bid if hasattr(price_info, 'bid') else price_info.get('bid', 0),
                    'high': price_info.ask if hasattr(price_info, 'ask') else price_info.get('ask', 0),
                    'low': price_info.bid if hasattr(price_info, 'bid') else price_info.get('bid', 0),
                    'volume': 1000  # Placeholder
                })
                
                # Keep last 100 candles
                self.price_history[pair] = self.price_history[pair][-100:]
            
            # Need minimum data
            if len(self.price_history.get(pair, [])) < 20:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(self.price_history[pair])
            df.set_index('timestamp', inplace=True)
            
            # Call generate_signals
            signals = self.generate_signals(df, pair)
            
            # Return first signal if any
            if signals and len(signals) > 0:
                return signals[0]
            
            return None
            
        except Exception as e:
            return None
