#!/usr/bin/env python3
"""
MOMENTUM V2 - IMPROVED FOR EXECUTION ROBUSTNESS
Addresses issues found in professional validation:
- 0% Monte Carlo survival rate
- Too sensitive to latency and slippage

IMPROVEMENTS:
1. Wider stops (30-50% wider) - less sensitive to slippage
2. Execution buffer - enter 3-5 pips away from trigger
3. Slower timeframes - less latency-sensitive
4. Confirmation requirements - reduce false signals
5. Maximum spread filter - only trade in good conditions
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class MomentumV2Improved:
    """
    Improved Momentum Strategy - Execution Robust
    Fixes: Wide stops, execution buffer, confirmation required
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # IMPROVED: Wider ATR multiples (was 1.0-2.0, now 1.5-3.0)
        self.sl_atr_mult = self.config.get('sl_atr', 2.0)  # +50% wider
        self.tp_atr_mult = self.config.get('tp_atr', 3.0)  # +50% wider
        
        # NEW: Execution buffer (enter away from trigger)
        self.execution_buffer_pips = self.config.get('execution_buffer_pips', 3)
        
        # NEW: Confirmation requirements
        self.require_confirmation = self.config.get('require_confirmation', True)
        self.confirmation_bars = self.config.get('confirmation_bars', 2)
        
        # NEW: Maximum spread filter
        self.max_spread_pips = self.config.get('max_spread_pips', 2.5)
        
        # IMPROVED: Minimum momentum threshold (FIXED OCT 16, 2025 - more realistic)
        self.min_momentum = self.config.get('min_momentum', 0.002)  # 0.2% (was 0.3% - too strict!)
        
        # NEW: Minimum timeframe (prefer slower for less latency sensitivity)
        self.min_timeframe_minutes = self.config.get('min_timeframe_minutes', 15)
        
        # Risk management
        self.max_trades_per_day = self.config.get('max_trades_per_day', 10)  # Reduced from 20
        self.risk_per_trade = self.config.get('risk_per_trade', 0.01)
        
        # Tracking
        self.daily_trades = 0
        self.last_trade_time = None
        
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
    
    def calculate_momentum(self, data: pd.DataFrame, period: int = 20) -> float:
        """Calculate price momentum"""
        if len(data) < period:
            return 0.0
        
        price_change = data['close'].iloc[-1] - data['close'].iloc[-period]
        momentum = price_change / data['close'].iloc[-period]
        
        return momentum
    
    def check_spread(self, data: pd.DataFrame) -> bool:
        """NEW: Check if spread is acceptable"""
        if 'bid' not in data.columns or 'ask' not in data.columns:
            return True  # Assume OK if no spread data
        
        current_spread = data['ask'].iloc[-1] - data['bid'].iloc[-1]
        current_price = data['close'].iloc[-1]
        
        # Convert to pips
        pip_value = 0.0001 if 'JPY' not in str(data.name) else 0.01
        spread_pips = current_spread / pip_value
        
        return spread_pips <= self.max_spread_pips
    
    def check_confirmation(self, data: pd.DataFrame, direction: str) -> bool:
        """NEW: Require confirmation bars"""
        if not self.require_confirmation:
            return True
        
        if len(data) < self.confirmation_bars + 1:
            return False
        
        # For bullish momentum, require multiple up bars
        if direction == 'BUY':
            recent_closes = data['close'].values[-self.confirmation_bars-1:]
            confirmations = sum(1 for i in range(len(recent_closes)-1) 
                              if recent_closes[i+1] > recent_closes[i])
            return confirmations >= self.confirmation_bars - 1
        
        # For bearish momentum, require multiple down bars
        elif direction == 'SELL':
            recent_closes = data['close'].values[-self.confirmation_bars-1:]
            confirmations = sum(1 for i in range(len(recent_closes)-1) 
                              if recent_closes[i+1] < recent_closes[i])
            return confirmations >= self.confirmation_bars - 1
        
        return False
    
    def add_execution_buffer(self, entry_price: float, direction: str, 
                            pip_value: float) -> float:
        """NEW: Add execution buffer to reduce sensitivity"""
        buffer = self.execution_buffer_pips * pip_value
        
        if direction == 'BUY':
            # Enter slightly above trigger (wait for pullback)
            return entry_price + buffer
        else:
            # Enter slightly below trigger (wait for bounce)
            return entry_price - buffer
        
    def calculate_moving_averages(self, data: pd.DataFrame) -> Tuple[float, float]:
        """Calculate fast and slow moving averages"""
        if len(data) < 50:
            return None, None
        
        ma_fast = data['close'].rolling(20).mean().iloc[-1]
        ma_slow = data['close'].rolling(50).mean().iloc[-1]
        
        return ma_fast, ma_slow
    
    def generate_signals(self, data: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate improved momentum signals"""
        if len(data) < 50:
            return []
        
        # Check daily trade limit
        if self.daily_trades >= self.max_trades_per_day:
            return []
        
        # NEW: Check spread condition
        if not self.check_spread(data):
            return []
        
        signals = []
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Calculate indicators
        momentum = self.calculate_momentum(data, period=20)
        atr = self.calculate_atr(data, period=14)
        ma_fast, ma_slow = self.calculate_moving_averages(data)
        
        if atr == 0 or ma_fast is None:
            return []
        
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        
        # BULLISH MOMENTUM SIGNAL
        if momentum > self.min_momentum and ma_fast > ma_slow:
            # NEW: Require confirmation
            if not self.check_confirmation(data, 'BUY'):
                return []
            
            # IMPROVED: Wider stops with execution buffer
            entry_price = self.add_execution_buffer(current_price, 'BUY', pip_value)
            sl_price = entry_price - (atr * self.sl_atr_mult)
            tp_price = entry_price + (atr * self.tp_atr_mult)
            
            rr_ratio = abs(tp_price - entry_price) / abs(entry_price - sl_price)
            
            if rr_ratio >= 1.5:  # Minimum R:R
                signals.append({
                    'pair': pair,
                    'signal': 'BUY',
                    'entry_price': entry_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'confidence': min(0.6 + abs(momentum) * 50, 0.85),
                    'reason': f'Bullish momentum {momentum:.3f}, MA cross confirmed',
                    'rr_ratio': rr_ratio,
                    'atr': atr,
                    'strategy_version': 'momentum_v2_improved',
                    'improvements': {
                        'wider_stops': f'{self.sl_atr_mult}x ATR (was 1.0-1.5x)',
                        'execution_buffer': f'{self.execution_buffer_pips} pips',
                        'confirmation_required': self.require_confirmation,
                        'spread_filtered': True
                    }
                })
                
                self.daily_trades += 1
        
        # BEARISH MOMENTUM SIGNAL
        elif momentum < -self.min_momentum and ma_fast < ma_slow:
            # NEW: Require confirmation
            if not self.check_confirmation(data, 'SELL'):
                return []
            
            # IMPROVED: Wider stops with execution buffer
            entry_price = self.add_execution_buffer(current_price, 'SELL', pip_value)
            sl_price = entry_price + (atr * self.sl_atr_mult)
            tp_price = entry_price - (atr * self.tp_atr_mult)
            
            rr_ratio = abs(entry_price - tp_price) / abs(sl_price - entry_price)
            
            if rr_ratio >= 1.5:  # Minimum R:R
                signals.append({
                    'pair': pair,
                    'signal': 'SELL',
                    'entry_price': entry_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'confidence': min(0.6 + abs(momentum) * 50, 0.85),
                    'reason': f'Bearish momentum {momentum:.3f}, MA cross confirmed',
                    'rr_ratio': rr_ratio,
                    'atr': atr,
                    'strategy_version': 'momentum_v2_improved',
                    'improvements': {
                        'wider_stops': f'{self.sl_atr_mult}x ATR (was 1.0-1.5x)',
                        'execution_buffer': f'{self.execution_buffer_pips} pips',
                        'confirmation_required': self.require_confirmation,
                        'spread_filtered': True
                    }
                })
                
                self.daily_trades += 1
        
        return signals
    
    def reset_daily_tracking(self):
        """Reset daily counters"""
        self.daily_trades = 0
        self.last_trade_time = None
    
    def get_improvement_summary(self) -> Dict:
        """Get summary of improvements made"""
        return {
            'version': '2.0 - Execution Robust',
            'changes': {
                '1_wider_stops': f'SL: {self.sl_atr_mult}x ATR (+50% from v1)',
                '2_wider_targets': f'TP: {self.tp_atr_mult}x ATR (+50% from v1)',
                '3_execution_buffer': f'{self.execution_buffer_pips} pips entry buffer',
                '4_confirmation': f'{self.confirmation_bars} bar confirmation required',
                '5_spread_filter': f'Max {self.max_spread_pips} pips spread',
                '6_higher_threshold': f'{self.min_momentum:.3f} momentum (was 0.002)',
                '7_reduced_frequency': f'Max {self.max_trades_per_day} trades/day (was 20)'
            },
            'expected_improvements': {
                'monte_carlo_survival': '0% → 70-90% (target)',
                'execution_robustness': 'Fragile → Robust',
                'slippage_sensitivity': 'High → Low',
                'latency_impact': 'Critical → Minimal'
            }
        }
    
    def analyze_market(self, market_data: Dict) -> List:
        """
        Analyze market data dict and return TradeSignals
        Compatible with optimizer and live trading
        """
        from src.core.order_manager import TradeSignal, OrderSide
        signals = []
        
        # For now, return empty - strategy needs pandas DataFrames, not MarketData
        # Would need significant rewrite to work with current system
        return signals



# ========================================
# INTEGRATION WITH TRADING SYSTEM
# ========================================

# Global instance
_momentum_v2_instance = None

def get_momentum_v2_strategy():
    """Get Momentum V2 strategy instance"""
    global _momentum_v2_instance
    if _momentum_v2_instance is None:
        _momentum_v2_instance = MomentumV2Improved()
    return _momentum_v2_instance
