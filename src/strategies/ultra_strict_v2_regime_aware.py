import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class UltraStrictV2RegimeAware:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_signal_strength = self.config.get('min_signal_strength', 0.40)
        self.regime_adjustments = {
            MarketRegime.TRENDING: {
                'signal_strength_mult': 0.95,
                'enabled': True,
                'description': 'Trend following works well'
            },
            MarketRegime.RANGING: {
                'signal_strength_mult': 1.15,
                'enabled': True,
                'description': 'Need very high quality in ranges'
            },
            MarketRegime.VOLATILE: {
                'signal_strength_mult': 1.25,
                'enabled': True,
                'description': 'Extra caution in volatility'
            },
            MarketRegime.UNKNOWN: {
                'signal_strength_mult': 1.10,
                'enabled': False,
                'description': 'Wait for clarity'
            }
        }
        self.regime_lookback = self.config.get('regime_lookback', 50)
        self.adx_period = self.config.get('adx_period', 14)
        self.adx_trend_threshold = self.config.get('adx_trend_threshold', 25)
        self.atr_volatile_mult = self.config.get('atr_volatile_mult', 1.5)
        self.max_trades_per_day = self.config.get('max_trades_per_day', 5)
        self.risk_per_trade = self.config.get('risk_per_trade', 0.02)
        self.daily_trades = 0
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = []
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
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
        if len(data) < period + 1:
            return 0.0
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
        return adx.iloc[-1] if len(adx) > 0 else 0.0
    def detect_regime(self, data: pd.DataFrame) -> MarketRegime:
        if len(data) < self.regime_lookback:
            return MarketRegime.UNKNOWN
        adx = self.calculate_adx(data, self.adx_period)
        atr = self.calculate_atr(data, period=14)
        if len(data) >= 50:
            atr_data = []
            for i in range(30, len(data)):
                window = data.iloc[i-14:i]
                atr_data.append(self.calculate_atr(window, period=14))
            avg_atr = np.mean(atr_data) if atr_data else atr
        else:
            avg_atr = atr
        recent_data = data.tail(self.regime_lookback)
        price_high = recent_data['high'].max()
        price_low = recent_data['low'].min()
        price_range = (price_high - price_low) / recent_data['close'].mean()
        if avg_atr > 0 and atr / avg_atr > self.atr_volatile_mult:
            return MarketRegime.VOLATILE
        if adx > self.adx_trend_threshold:
            return MarketRegime.TRENDING
        if adx < 20 and price_range < 0.03:
            return MarketRegime.RANGING
        return MarketRegime.UNKNOWN
    def get_regime_adjusted_threshold(self, regime: MarketRegime) -> float:
        adjustment = self.regime_adjustments[regime]
        adjusted_threshold = self.base_signal_strength * adjustment['signal_strength_mult']
        return adjusted_threshold
    def can_trade_in_regime(self, regime: MarketRegime) -> bool:
        return self.regime_adjustments[regime]['enabled']
    def calculate_signal_strength(self, data: pd.DataFrame) -> float:
        if len(data) < 50:
            return 0.0
        strength = 0.0
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            price = data['close'].iloc[-1]
            if price > ema_20 > ema_50 or price < ema_20 < ema_50:
                strength += 0.30
        if 'rsi' in data.columns:
            rsi = data['rsi'].iloc[-1]
            if 40 <= rsi <= 60:
                strength += 0.25
        if 'macd' in data.columns and 'macd_signal' in data.columns:
            macd = data['macd'].iloc[-1]
            macd_signal = data['macd_signal'].iloc[-1]
            if abs(macd - macd_signal) > 0:
                strength += 0.25
        if 'volume' in data.columns and len(data) >= 20:
            avg_volume = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            if current_volume > avg_volume * 1.2:
                strength += 0.20
        return min(strength, 1.0)
    def generate_signals(self, data: pd.DataFrame, pair: str) -> List[Dict]:
        if len(data) < self.regime_lookback:
            return []
        if self.daily_trades >= self.max_trades_per_day:
            return []
        self.current_regime = self.detect_regime(data)
        self.regime_history.append({
            'time': data.index[-1],
            'regime': self.current_regime.value
        })
        if not self.can_trade_in_regime(self.current_regime):
            return []
        adjusted_threshold = self.get_regime_adjusted_threshold(self.current_regime)
        signal_strength = self.calculate_signal_strength(data)
        if signal_strength < adjusted_threshold:
            return []
        signals = []
        current_price = data['close'].iloc[-1]
        atr = self.calculate_atr(data, period=14)
        if atr == 0:
            return []
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            if current_price > ema_20 > ema_50:
                sl_price = current_price - (atr * 2.0)
                tp_price = current_price + (atr * 5.0)
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
            elif current_price < ema_20 < ema_50:
                sl_price = current_price + (atr * 2.0)
                tp_price = current_price - (atr * 5.0)
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
        self.daily_trades = 0
    def get_regime_statistics(self) -> Dict:
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
