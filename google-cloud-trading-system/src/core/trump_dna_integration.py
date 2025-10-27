#!/usr/bin/env python3
"""
TRUMP DNA INTEGRATION MODULE
Provides Trump DNA framework features to any strategy

Features:
- Weekly/daily planning
- Sniper entry zones (S/R levels)
- Fixed tight stops
- Multi-stage exits
- Quick exit timers
- News awareness
- Trend alignment
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class WeeklyPlan:
    """Weekly trading plan for a strategy"""
    strategy_name: str
    instruments: List[str]
    weekly_target: float  # Dollar target
    daily_targets: Dict[str, float]  # Mon-Fri breakdown
    
    # Entry zones per instrument
    entry_zones: Dict[str, List[Dict]]  # {instrument: [{level, type, action}]}
    
    # Fixed risk parameters
    fixed_stop_pips: float
    fixed_tp_stages: List[Tuple[float, float]]  # [(pips, close_pct)]
    
    # Limits
    max_trades_per_day: int
    max_hold_hours: float
    
    # News events
    news_events: List[Dict]  # [{day, time, event, impact}]
    avoid_times: List[Dict]  # [{start, end, reason}]
    
    # Market bias
    weekly_bias: str  # BULLISH, BEARISH, NEUTRAL
    volatility_forecast: str


class TrumpDNAIntegration:
    """
    Trump DNA framework integration for strategies
    Adds structure, planning, and discipline to any strategy
    """
    
    def __init__(self, strategy_name: str, instruments: List[str]):
        self.strategy_name = strategy_name
        self.instruments = instruments
        self.weekly_plan = None
        
        # Tracking
        self.trades_today = 0
        self.profit_today = 0.0
        self.profit_this_week = 0.0
        self.trade_start_times = {}  # {trade_id: start_time}
        
        logger.info(f"✅ Trump DNA integration initialized for {strategy_name}")
    
    def create_weekly_plan(self) -> WeeklyPlan:
        """Create weekly plan based on strategy and instruments"""
        
        # Determine weekly target based on strategy type
        if "75" in self.strategy_name or "Champion" in self.strategy_name:
            weekly_target = 2500.0
            max_trades_day = 5
            fixed_stop = 8.0
        elif "70" in self.strategy_name or "Weather" in self.strategy_name:
            weekly_target = 4000.0  # Updated for current gold prices
            max_trades_day = 5
            fixed_stop = 10.0
        elif "Strict" in self.strategy_name:
            weekly_target = 4000.0  # Updated for current gold prices
            max_trades_day = 5
            fixed_stop = 10.0
        elif "Momentum" in self.strategy_name:
            weekly_target = 2500.0
            max_trades_day = 10
            fixed_stop = 12.0
        else:
            weekly_target = 4000.0  # Updated for current gold prices
            max_trades_day = 10
            fixed_stop = 10.0
        
        # Daily breakdown (favor Wed/Thu - typically high volatility)
        daily_targets = {
            'Monday': weekly_target * 0.15,     # 15% - Conservative start
            'Tuesday': weekly_target * 0.20,    # 20% - Build momentum
            'Wednesday': weekly_target * 0.30,  # 30% - Mid-week high volatility
            'Thursday': weekly_target * 0.20,   # 20% - Follow-through
            'Friday': weekly_target * 0.15,     # 15% - Finish strong
        }
        
        # Multi-stage exit targets (Trump DNA style)
        fixed_tp_stages = [
            (15.0, 0.30),  # +15 pips: close 30%
            (30.0, 0.30),  # +30 pips: close 30%
            (50.0, 0.20),  # +50 pips: close 20%
            # Trail last 20%
        ]
        
        # Economic events (hardcoded for this week)
        news_events = [
            {'day': 'Monday', 'time': '14:00', 'event': 'Various', 'impact': 'LOW'},
            {'day': 'Tuesday', 'time': '13:30', 'event': 'US Data', 'impact': 'MEDIUM'},
            {'day': 'Wednesday', 'time': '13:30', 'event': 'FOMC/CPI', 'impact': 'HIGH'},
            {'day': 'Thursday', 'time': '13:30', 'event': 'Jobless Claims', 'impact': 'MEDIUM'},
            {'day': 'Friday', 'time': '13:30', 'event': 'NFP/GDP', 'impact': 'HIGH'},
        ]
        
        # Avoid times (15 min before high impact news)
        avoid_times = [
            {'start': '13:15', 'end': '13:45', 'reason': 'High impact US data'},
            {'start': '14:15', 'end': '14:45', 'reason': 'FOMC minutes'},
        ]
        
        # Entry zones - will be populated per instrument
        entry_zones = self._calculate_entry_zones()
        
        # Weekly bias - simple trend detection
        weekly_bias = self._determine_weekly_bias()
        
        plan = WeeklyPlan(
            strategy_name=self.strategy_name,
            instruments=self.instruments,
            weekly_target=weekly_target,
            daily_targets=daily_targets,
            entry_zones=entry_zones,
            fixed_stop_pips=fixed_stop,
            fixed_tp_stages=fixed_tp_stages,
            max_trades_per_day=max_trades_day,
            max_hold_hours=2.0,  # Trump DNA: quick exits
            news_events=news_events,
            avoid_times=avoid_times,
            weekly_bias=weekly_bias,
            volatility_forecast="MODERATE"
        )
        
        self.weekly_plan = plan
        logger.info(f"📅 Weekly plan created: ${weekly_target} target, {max_trades_day} max trades/day")
        
        return plan
    
    def _calculate_entry_zones(self) -> Dict[str, List[Dict]]:
        """Calculate support/resistance entry zones for each instrument"""
        zones = {}
        
        for instrument in self.instruments:
            if instrument == 'XAU_USD':
                # Gold zones (approximate - should be updated weekly)
                zones[instrument] = [
                    {'level': 2600.0, 'type': 'support', 'action': 'BUY'},
                    {'level': 2620.0, 'type': 'support', 'action': 'BUY'},
                    {'level': 2650.0, 'type': 'resistance', 'action': 'SELL'},
                    {'level': 2670.0, 'type': 'resistance', 'action': 'SELL'},
                ]
            elif instrument == 'EUR_USD':
                zones[instrument] = [
                    {'level': 1.0800, 'type': 'support', 'action': 'BUY'},
                    {'level': 1.0850, 'type': 'pivot', 'action': 'BUY'},
                    {'level': 1.0900, 'type': 'resistance', 'action': 'SELL'},
                    {'level': 1.0950, 'type': 'resistance', 'action': 'SELL'},
                ]
            elif instrument == 'GBP_USD':
                zones[instrument] = [
                    {'level': 1.2800, 'type': 'support', 'action': 'BUY'},
                    {'level': 1.2850, 'type': 'support', 'action': 'BUY'},
                    {'level': 1.2900, 'type': 'resistance', 'action': 'SELL'},
                    {'level': 1.2950, 'type': 'resistance', 'action': 'SELL'},
                ]
            elif instrument == 'USD_JPY':
                zones[instrument] = [
                    {'level': 149.00, 'type': 'support', 'action': 'BUY'},
                    {'level': 150.00, 'type': 'support', 'action': 'BUY'},
                    {'level': 152.00, 'type': 'resistance', 'action': 'SELL'},
                    {'level': 153.00, 'type': 'resistance', 'action': 'SELL'},
                ]
            else:
                # Generic zones
                zones[instrument] = []
        
        return zones
    
    def _determine_weekly_bias(self) -> str:
        """Determine weekly market bias (simplified)"""
        # In production, this would analyze recent price action
        # For now, return NEUTRAL to trade both directions
        return "NEUTRAL"
    
    def is_near_entry_zone(self, instrument: str, current_price: float, 
                          tolerance_pips: float = 5.0) -> Optional[Dict]:
        """Check if current price is near a sniper entry zone"""
        
        if not self.weekly_plan or instrument not in self.weekly_plan.entry_zones:
            return None
        
        zones = self.weekly_plan.entry_zones[instrument]
        
        for zone in zones:
            level = zone['level']
            
            # Calculate distance
            if 'XAU' in instrument:
                distance = abs(current_price - level)
                tolerance = 5.0  # $5 tolerance for gold
            elif 'JPY' in instrument:
                distance = abs(current_price - level) * 100
                tolerance = tolerance_pips
            else:
                distance = abs(current_price - level) * 10000
                tolerance = tolerance_pips
            
            # If within tolerance
            if distance <= tolerance:
                return {
                    'zone': zone,
                    'distance': distance,
                    'current_price': current_price,
                    'zone_level': level
                }
        
        return None
    
    def should_trade_now(self) -> Tuple[bool, str]:
        """Check if we should trade right now based on Trump DNA rules"""
        
        if not self.weekly_plan:
            return False, "No weekly plan"
        
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        today = now.strftime('%A')
        
        # Check if daily target already hit
        daily_target = self.weekly_plan.daily_targets.get(today, 0)
        if self.profit_today >= daily_target:
            return False, f"Daily target ${daily_target:.0f} achieved!"
        
        # Check if weekly target hit
        if self.profit_this_week >= self.weekly_plan.weekly_target:
            return False, f"Weekly target ${self.weekly_plan.weekly_target:.0f} achieved!"
        
        # Check avoid times (news)
        for avoid in self.weekly_plan.avoid_times:
            if avoid['start'] <= current_time <= avoid['end']:
                return False, f"Paused: {avoid['reason']}"
        
        # Check max trades per day
        if self.trades_today >= self.weekly_plan.max_trades_per_day:
            return False, f"Max {self.weekly_plan.max_trades_per_day} trades/day reached"
        
        # Check trading session (London/NY)
        hour = now.hour
        london_session = 7 <= hour < 17  # 07:00-17:00 UTC
        ny_session = 13 <= hour < 21     # 13:00-21:00 UTC
        
        if not (london_session or ny_session):
            return False, "Outside London/NY sessions"
        
        return True, "Clear to trade"
    
    def check_trade_alignment(self, signal_direction: str) -> bool:
        """Check if signal aligns with weekly bias"""
        
        if not self.weekly_plan:
            return True  # Allow if no plan
        
        bias = self.weekly_plan.weekly_bias
        
        if bias == "NEUTRAL":
            return True  # Trade both directions
        elif bias == "BULLISH" and signal_direction == "BUY":
            return True
        elif bias == "BEARISH" and signal_direction == "SELL":
            return True
        else:
            return False
    
    def get_fixed_stop_loss(self, instrument: str, entry_price: float, 
                           direction: str) -> float:
        """Get fixed stop loss (Trump DNA: fixed pips, not ATR)"""
        
        if not self.weekly_plan:
            stop_pips = 10.0  # Default
        else:
            stop_pips = self.weekly_plan.fixed_stop_pips
        
        # Convert pips to price
        if 'XAU' in instrument:
            stop_distance = stop_pips  # Direct dollars for gold
        elif 'JPY' in instrument:
            stop_distance = stop_pips / 100.0
        else:
            stop_distance = stop_pips / 10000.0
        
        if direction == "BUY":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def get_multi_stage_targets(self, instrument: str, entry_price: float, 
                                direction: str) -> List[Dict]:
        """Get multi-stage take profit targets (Trump DNA style)"""
        
        if not self.weekly_plan:
            stages = [(15.0, 0.30), (30.0, 0.30), (50.0, 0.40)]
        else:
            stages = self.weekly_plan.fixed_tp_stages
        
        targets = []
        
        for pips, close_pct in stages:
            # Convert pips to price
            if 'XAU' in instrument:
                distance = pips  # Direct dollars
            elif 'JPY' in instrument:
                distance = pips / 100.0
            else:
                distance = pips / 10000.0
            
            if direction == "BUY":
                target_price = entry_price + distance
            else:
                target_price = entry_price - distance
            
            targets.append({
                'pips': pips,
                'price': target_price,
                'close_pct': close_pct,
                'description': f"+{pips} pips: close {close_pct*100:.0f}%"
            })
        
        return targets
    
    def check_max_hold_time(self, trade_id: str) -> Tuple[bool, float]:
        """Check if trade exceeded max hold time"""
        
        if trade_id not in self.trade_start_times:
            return False, 0.0
        
        start_time = self.trade_start_times[trade_id]
        elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600.0
        
        max_hold = self.weekly_plan.max_hold_hours if self.weekly_plan else 2.0
        
        if elapsed_hours > max_hold:
            return True, elapsed_hours
        
        return False, elapsed_hours
    
    def register_trade(self, trade_id: str):
        """Register new trade for tracking"""
        self.trades_today += 1
        self.trade_start_times[trade_id] = datetime.now()
        logger.info(f"📝 Trade registered: {trade_id} (#{self.trades_today} today)")
    
    def update_profit(self, trade_profit: float):
        """Update profit tracking"""
        self.profit_today += trade_profit
        self.profit_this_week += trade_profit
        logger.info(f"💰 Profit updated: +${trade_profit:.2f} (Today: ${self.profit_today:.2f}, Week: ${self.profit_this_week:.2f})")
    
    def reset_daily(self):
        """Reset daily counters (call at start of new day)"""
        self.trades_today = 0
        self.profit_today = 0.0
        logger.info("🔄 Daily counters reset")
    
    def reset_weekly(self):
        """Reset weekly counters (call at start of new week)"""
        self.profit_this_week = 0.0
        self.weekly_plan = self.create_weekly_plan()  # Regenerate plan
        logger.info("🔄 Weekly counters reset, new plan created")
    
    def get_progress_report(self) -> Dict:
        """Get current progress vs targets"""
        
        if not self.weekly_plan:
            return {}
        
        today = datetime.now().strftime('%A')
        daily_target = self.weekly_plan.daily_targets.get(today, 0)
        weekly_target = self.weekly_plan.weekly_target
        
        return {
            'strategy': self.strategy_name,
            'trades_today': self.trades_today,
            'profit_today': self.profit_today,
            'daily_target': daily_target,
            'daily_progress_pct': (self.profit_today / daily_target * 100) if daily_target > 0 else 0,
            'profit_this_week': self.profit_this_week,
            'weekly_target': weekly_target,
            'weekly_progress_pct': (self.profit_this_week / weekly_target * 100) if weekly_target > 0 else 0,
            'max_trades_per_day': self.weekly_plan.max_trades_per_day,
            'trades_remaining_today': max(0, self.weekly_plan.max_trades_per_day - self.trades_today)
        }


# Global registry
_trump_dna_instances = {}

def get_trump_dna_integration(strategy_name: str, instruments: List[str]) -> TrumpDNAIntegration:
    """Get Trump DNA integration instance for a strategy"""
    global _trump_dna_instances
    
    key = f"{strategy_name}_{','.join(instruments)}"
    
    if key not in _trump_dna_instances:
        integration = TrumpDNAIntegration(strategy_name, instruments)
        integration.create_weekly_plan()
        _trump_dna_instances[key] = integration
    
    return _trump_dna_instances[key]



