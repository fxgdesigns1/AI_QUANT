#!/usr/bin/env python3
"""
OPTIMAL CONDITIONS CHECKER FOR 75% WR CHAMPION
Monitors market and notifies when conditions are OPTIMAL vs POOR

This allows the 75% WR Champion to tell you:
- 🟢 GREEN: Deploy now! (optimal conditions)
- 🟡 YELLOW: Can trade but not ideal (expect 65-70% WR)
- 🔴 RED: Don't trade, use adaptive strategies instead
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple
from enum import Enum

class ConditionStatus(Enum):
    """Market condition status for 75% WR Champion"""
    OPTIMAL = "optimal"  # 🟢 Green
    SUBOPTIMAL = "suboptimal"  # 🟡 Yellow
    POOR = "poor"  # 🔴 Red

class OptimalConditionsChecker:
    """
    Checks if current market conditions are optimal for 75% WR Champion
    Provides real-time notifications
    """
    
    def __init__(self):
        # Optimal criteria (all must be met for GREEN)
        self.optimal_criteria = {
            'adx_min': 40,  # Strong trend
            'volume_mult_min': 3.0,  # High institutional participation
            'signal_strength_min': 0.65,  # High confidence
            'confluence_min': 5,  # All 5 factors present
            'confirmation_bars': 5  # Full confirmation
        }
        
        # Suboptimal criteria (acceptable but not ideal)
        self.suboptimal_criteria = {
            'adx_min': 30,
            'volume_mult_min': 2.5,
            'signal_strength_min': 0.60,
            'confluence_min': 3,
            'confirmation_bars': 4
        }
        
        # Tracking
        self.conditions_history = []
        
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
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
        
        return adx.iloc[-1] if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 0.0
    
    def check_volume_surge(self, data: pd.DataFrame, period: int = 20) -> float:
        """Check volume multiplier"""
        if 'volume' not in data.columns or len(data) < period:
            return 1.0
        
        avg_volume = data['volume'].tail(period).mean()
        current_volume = data['volume'].iloc[-1]
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def calculate_signal_strength(self, data: pd.DataFrame) -> Tuple[float, int]:
        """Calculate signal strength and confluence count"""
        strength = 0.0
        confluence = 0
        
        # Factor 1: Trend
        if 'ema_20' in data.columns and 'ema_50' in data.columns:
            ema_20 = data['ema_20'].iloc[-1]
            ema_50 = data['ema_50'].iloc[-1]
            price = data['close'].iloc[-1]
            
            if (price > ema_20 > ema_50) or (price < ema_20 < ema_50):
                strength += 0.25
                confluence += 1
        
        # Factor 2: RSI
        if 'rsi' in data.columns:
            rsi = data['rsi'].iloc[-1]
            if 40 <= rsi <= 60:
                strength += 0.20
                confluence += 1
        
        # Factor 3: ADX
        adx = self.calculate_adx(data, 14)
        if adx >= 20:
            strength += 0.20
            confluence += 1
        
        # Factor 4: Volume
        volume_mult = self.check_volume_surge(data, 20)
        if volume_mult >= 2.0:
            strength += 0.20
            confluence += 1
        
        # Factor 5: MACD
        if 'macd' in data.columns and 'macd_signal' in data.columns:
            macd = data['macd'].iloc[-1]
            macd_sig = data['macd_signal'].iloc[-1]
            if abs(macd - macd_sig) > 0:
                strength += 0.15
                confluence += 1
        
        return strength, confluence
    
    def check_confirmation_bars(self, data: pd.DataFrame, bars: int = 5) -> int:
        """Check how many bars confirm direction"""
        if len(data) < bars + 1:
            return 0
        
        closes = data['close'].values[-bars-1:]
        up_moves = sum(1 for i in range(len(closes)-1) if closes[i+1] > closes[i])
        down_moves = sum(1 for i in range(len(closes)-1) if closes[i+1] < closes[i])
        
        return max(up_moves, down_moves)
    
    def is_trading_session(self, dt: datetime) -> bool:
        """Check if London or NY session"""
        hour = dt.hour
        london = 8 <= hour < 17
        ny = 13 <= hour < 22
        return london or ny
    
    def check_conditions(self, data: pd.DataFrame, current_time: datetime = None) -> Dict:
        """
        Check current market conditions and return status + notification
        
        Returns:
        {
            'status': 'optimal' | 'suboptimal' | 'poor',
            'notification': '🟢 message' | '🟡 message' | '🔴 message',
            'deploy': True | False,
            'metrics': {...},
            'recommendation': 'Deploy 75% WR' | 'Use alternative strategy'
        }
        """
        if len(data) < 50:
            return {
                'status': ConditionStatus.POOR,
                'notification': '🔴 INSUFFICIENT DATA',
                'deploy': False,
                'recommendation': 'Wait for more data'
            }
        
        if current_time is None:
            current_time = data.index[-1]
        
        # Calculate all metrics
        adx = self.calculate_adx(data, 14)
        volume_mult = self.check_volume_surge(data, 20)
        signal_strength, confluence = self.calculate_signal_strength(data)
        confirmation_bars = self.check_confirmation_bars(data, 5)
        in_session = self.is_trading_session(current_time)
        
        metrics = {
            'adx': adx,
            'volume_multiplier': volume_mult,
            'signal_strength': signal_strength,
            'confluence_count': confluence,
            'confirmation_bars': confirmation_bars,
            'in_session': in_session
        }
        
        # Check OPTIMAL conditions (GREEN)
        optimal_checks = [
            adx >= self.optimal_criteria['adx_min'],
            volume_mult >= self.optimal_criteria['volume_mult_min'],
            signal_strength >= self.optimal_criteria['signal_strength_min'],
            confluence >= self.optimal_criteria['confluence_min'],
            confirmation_bars >= self.optimal_criteria['confirmation_bars'],
            in_session
        ]
        
        if all(optimal_checks):
            return {
                'status': ConditionStatus.OPTIMAL,
                'notification': '🟢 OPTIMAL CONDITIONS - Deploy 75% WR Champion NOW!',
                'deploy': True,
                'expected_wr': 0.75,
                'metrics': metrics,
                'recommendation': 'DEPLOY - All ideal conditions met',
                'details': [
                    f'ADX: {adx:.1f} (target: 40+) ✅',
                    f'Volume: {volume_mult:.1f}x (target: 3.0x+) ✅',
                    f'Signal: {signal_strength:.2f} (target: 0.65+) ✅',
                    f'Confluence: {confluence}/5 (target: 5/5) ✅',
                    f'Confirmation: {confirmation_bars}/5 bars ✅',
                    'Session: London/NY ✅'
                ]
            }
        
        # Check SUBOPTIMAL conditions (YELLOW)
        suboptimal_checks = [
            adx >= self.suboptimal_criteria['adx_min'],
            volume_mult >= self.suboptimal_criteria['volume_mult_min'],
            signal_strength >= self.suboptimal_criteria['signal_strength_min'],
            confluence >= self.suboptimal_criteria['confluence_min'],
            confirmation_bars >= self.suboptimal_criteria['confirmation_bars'] - 1
        ]
        
        if sum(suboptimal_checks) >= 4:  # At least 4 out of 5
            return {
                'status': ConditionStatus.SUBOPTIMAL,
                'notification': '🟡 SUBOPTIMAL - Can trade but expect 65-70% WR (not 75%)',
                'deploy': True,
                'expected_wr': 0.67,
                'metrics': metrics,
                'recommendation': 'CAN TRADE - But conditions not ideal. Consider All-Weather strategy instead.',
                'details': [
                    f'ADX: {adx:.1f} (ideal: 40+) {"✅" if adx >= 40 else "⚠️"}',
                    f'Volume: {volume_mult:.1f}x (ideal: 3.0x+) {"✅" if volume_mult >= 3.0 else "⚠️"}',
                    f'Signal: {signal_strength:.2f} (ideal: 0.65+) {"✅" if signal_strength >= 0.65 else "⚠️"}',
                    f'Confluence: {confluence}/5 (ideal: 5/5) {"✅" if confluence >= 5 else "⚠️"}',
                    f'Confirmation: {confirmation_bars}/5 bars {"✅" if confirmation_bars >= 5 else "⚠️"}'
                ]
            }
        
        # POOR conditions (RED)
        return {
            'status': ConditionStatus.POOR,
            'notification': '🔴 POOR CONDITIONS - Do NOT trade with 75% WR Champion',
            'deploy': False,
            'expected_wr': 0.45,  # Would drop to baseline
            'metrics': metrics,
            'recommendation': 'SWITCH STRATEGY - Use account 101-004-30719775-002 (All-Weather) or 101-004-30719775-004 (Ultra Strict V2)',
            'details': [
                f'ADX: {adx:.1f} (need: 30+) {"❌" if adx < 30 else "⚠️"}',
                f'Volume: {volume_mult:.1f}x (need: 2.5x+) {"❌" if volume_mult < 2.5 else "⚠️"}',
                f'Signal: {signal_strength:.2f} (need: 0.60+) {"❌" if signal_strength < 0.60 else "⚠️"}',
                f'Confluence: {confluence}/5 (need: 3+) {"❌" if confluence < 3 else "⚠️"}',
                f'Market: Likely ranging/choppy - NOT suitable for this strategy'
            ],
            'alternative_strategies': [
                {'account': '101-004-30719775-002', 'name': 'All-Weather Adaptive', 'reason': 'Adapts to any regime'},
                {'account': '101-004-30719775-004', 'name': 'Ultra Strict V2', 'reason': 'Regime-aware, works in ranges'},
            ]
        }
    
    def get_conditions_summary(self, lookback_hours: int = 24) -> Dict:
        """
        Get summary of conditions over last N hours
        Shows % of time conditions were optimal
        """
        if not self.conditions_history:
            return {'message': 'No data yet'}
        
        recent = [c for c in self.conditions_history if c['hours_ago'] <= lookback_hours]
        
        if not recent:
            return {'message': 'No recent data'}
        
        optimal_count = sum(1 for c in recent if c['status'] == ConditionStatus.OPTIMAL)
        suboptimal_count = sum(1 for c in recent if c['status'] == ConditionStatus.SUBOPTIMAL)
        poor_count = sum(1 for c in recent if c['status'] == ConditionStatus.POOR)
        
        total = len(recent)
        
        return {
            'lookback_hours': lookback_hours,
            'total_checks': total,
            'optimal_pct': optimal_count / total * 100,
            'suboptimal_pct': suboptimal_count / total * 100,
            'poor_pct': poor_count / total * 100,
            'recommendation': self._get_deployment_recommendation(optimal_count / total)
        }
    
    def _get_deployment_recommendation(self, optimal_pct: float) -> str:
        """Get deployment recommendation based on conditions"""
        if optimal_pct >= 0.60:  # 60%+ optimal
            return '🟢 DEPLOY - Conditions have been optimal 60%+ of time'
        elif optimal_pct >= 0.30:  # 30-60% optimal
            return '🟡 SELECTIVE - Deploy only when optimal notifications occur'
        else:  # < 30% optimal
            return '🔴 USE ALTERNATIVE - Conditions rarely optimal, use All-Weather or Ultra Strict V2'
    
    def should_trade_now(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """
        Simple yes/no: Should we trade with 75% WR Champion now?
        
        Returns:
            (True/False, 'reason')
        """
        conditions = self.check_conditions(data)
        
        if conditions['status'] == ConditionStatus.OPTIMAL:
            return True, "🟢 OPTIMAL - All conditions perfect, deploy now!"
        
        elif conditions['status'] == ConditionStatus.SUBOPTIMAL:
            return True, "🟡 ACCEPTABLE - Can trade but not ideal (expect 65-70% WR)"
        
        else:  # POOR
            return False, f"🔴 POOR - {conditions['recommendation']}"
    
    def get_realtime_notification(self, data: pd.DataFrame) -> str:
        """
        Get real-time notification message for your live system
        Call this every bar (1 hour) to get current status
        """
        conditions = self.check_conditions(data)
        
        message = f"{conditions['notification']}\n\n"
        message += f"Expected Win Rate: {conditions['expected_wr']*100:.0f}%\n"
        message += f"Recommendation: {conditions['recommendation']}\n\n"
        message += "Current Conditions:\n"
        
        for detail in conditions['details']:
            message += f"  {detail}\n"
        
        if conditions['status'] == ConditionStatus.POOR and 'alternative_strategies' in conditions:
            message += "\nAlternative Strategies:\n"
            for alt in conditions['alternative_strategies']:
                message += f"  - {alt['account']}: {alt['name']} ({alt['reason']})\n"
        
        return message

# ========================================
# USAGE IN LIVE TRADING SYSTEM
# ========================================
"""
# In your live trading loop (every 1 hour):

from optimal_conditions_checker import OptimalConditionsChecker

checker = OptimalConditionsChecker()

# Every bar/hour:
conditions = checker.check_conditions(current_data)

if conditions['status'] == 'optimal':
    print("🟢 DEPLOY 75% WR Champion - Conditions perfect!")
    enable_strategy('101-004-30719775-005')
    
elif conditions['status'] == 'suboptimal':
    print("🟡 Can trade but not ideal - Consider All-Weather instead")
    # Option 1: Still trade with 75% WR (but expect 65-70% WR)
    # Option 2: Switch to All-Weather (101-004-30719775-002)
    
else:  # poor
    print("🔴 DON'T USE 75% WR Champion")
    print(f"Switch to: {conditions['recommendation']}")
    disable_strategy('101-004-30719775-005')
    enable_strategy('101-004-30719775-002')  # All-Weather

# Get notification message
notification = checker.get_realtime_notification(current_data)
send_alert(notification)  # Send to your dashboard/alerts
"""

