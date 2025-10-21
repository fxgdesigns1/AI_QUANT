#!/usr/bin/env python3
"""
TRUMP DNA FRAMEWORK - Weekly Planning & Sniper Trading
Each strategy/pair gets a weekly roadmap with sniper-tight execution
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

@dataclass
class WeeklyPairPlan:
    """Weekly roadmap for a specific pair"""
    pair: str
    strategy_name: str
    
    # Weekly Planning (Trump DNA Core)
    weekly_target_dollars: float          # Weekly profit target
    daily_targets: Dict[str, float]       # Mon-Fri targets
    key_events: List[Dict]                # Economic events this week
    best_trading_days: List[str]          # Which days to focus
    avoid_times: List[Dict]               # When to pause (news)
    
    # Sniper Execution (Tight & Precise)
    entry_zones: List[Dict]               # Exact price zones to enter
    stop_loss_pips: float                 # Fixed tight stop
    take_profit_pips: float               # Fixed target
    max_trades_per_day: int               # Stay selective
    max_hold_hours: float                 # Quick exits
    
    # Market Roadmap
    support_levels: List[float]           # Key supports
    resistance_levels: List[float]        # Key resistances
    trend_direction: str                  # Week's bias
    volatility_forecast: str              # Expected movement
    
    # Performance Tracking
    current_week_profit: float            # Track vs target
    trades_this_week: int                 # Monitor volume
    win_rate_this_week: float             # Quality control


class TrumpDNAPlanner:
    """
    Creates weekly roadmaps for each strategy/pair combination
    Trump DNA = Plan the week, stay tight, be a sniper
    """
    
    def __init__(self):
        self.name = "TrumpDNAPlanner"
        self.weekly_plans: Dict[str, WeeklyPairPlan] = {}
        self.week_start = self._get_week_start()
        
        logger.info("✅ Trump DNA Framework initialized")
    
    def _get_week_start(self):
        """Get start of current trading week (Monday)"""
        now = datetime.now()
        days_since_monday = now.weekday()  # 0=Monday, 6=Sunday
        week_start = now - timedelta(days=days_since_monday)
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def create_weekly_plan_gold(self) -> WeeklyPairPlan:
        """Create weekly plan for GOLD (XAU_USD)"""
        return WeeklyPairPlan(
            pair='XAU_USD',
            strategy_name='Gold Scalping',
            
            # Weekly Planning
            weekly_target_dollars=2000.0,  # $2K/week target
            daily_targets={
                'Monday': 300.0,      # Conservative (US holiday often)
                'Tuesday': 400.0,     # Normal
                'Wednesday': 600.0,   # CPI day - BIGGEST
                'Thursday': 400.0,    # Follow-through
                'Friday': 300.0,      # Profit-taking
            },
            key_events=[
                {'day': 'Wednesday', 'time': '13:30', 'event': 'U.S. CPI', 'impact': 'EXTREME'},
                {'day': 'Thursday', 'time': '13:30', 'event': 'U.S. Retail Sales', 'impact': 'HIGH'},
            ],
            best_trading_days=['Wednesday', 'Thursday'],  # CPI + Retail = volatility
            avoid_times=[
                {'start': '13:15', 'end': '13:30', 'reason': 'Pre-CPI pause'},
            ],
            
            # Sniper Execution
            entry_zones=[
                {'level': 4125.0, 'type': 'support', 'action': 'BUY'},
                {'level': 4115.0, 'type': 'support', 'action': 'BUY'},
                {'level': 4145.0, 'type': 'resistance', 'action': 'SELL'},
                {'level': 4155.0, 'type': 'resistance', 'action': 'SELL'},
            ],
            stop_loss_pips=6.0,        # TIGHT
            take_profit_pips=24.0,     # CLEAR TARGET
            max_trades_per_day=10,     # SELECTIVE
            max_hold_hours=1.5,        # QUICK
            
            # Market Roadmap
            support_levels=[4100.0, 4115.0, 4125.0],
            resistance_levels=[4145.0, 4155.0, 4175.0],
            trend_direction='BULLISH',              # Fed rate cuts
            volatility_forecast='HIGH (CPI week)',
            
            # Tracking
            current_week_profit=0.0,
            trades_this_week=0,
            win_rate_this_week=0.0
        )
    
    def create_weekly_plan_gbp(self, strategy_rank: int) -> WeeklyPairPlan:
        """Create weekly plan for GBP/USD"""
        return WeeklyPairPlan(
            pair='GBP_USD',
            strategy_name=f'GBP Rank #{strategy_rank}',
            
            # Weekly Planning
            weekly_target_dollars=3000.0,  # $3K/week target
            daily_targets={
                'Monday': 400.0,
                'Tuesday': 500.0,     # PPI day
                'Wednesday': 800.0,   # CPI day - BIGGEST
                'Thursday': 800.0,    # UK GDP - MAJOR
                'Friday': 500.0,
            },
            key_events=[
                {'day': 'Tuesday', 'time': '13:30', 'event': 'U.S. PPI', 'impact': 'MEDIUM'},
                {'day': 'Wednesday', 'time': '13:30', 'event': 'U.S. CPI', 'impact': 'EXTREME'},
                {'day': 'Thursday', 'time': '07:00', 'event': 'UK GDP', 'impact': 'EXTREME'},
            ],
            best_trading_days=['Wednesday', 'Thursday'],  # CPI + UK GDP
            avoid_times=[
                {'start': '13:15', 'end': '13:30', 'reason': 'Pre-CPI pause'},
                {'start': '06:45', 'end': '07:15', 'reason': 'UK GDP pause'},
            ],
            
            # Sniper Execution  
            entry_zones=[
                {'level': 1.3260, 'type': 'support', 'action': 'BUY'},
                {'level': 1.3300, 'type': 'support', 'action': 'BUY'},
                {'level': 1.3350, 'type': 'resistance', 'action': 'SELL'},
                {'level': 1.3400, 'type': 'resistance', 'action': 'SELL'},
            ],
            stop_loss_pips=20.0,       # TIGHT FIXED (not ATR)
            take_profit_pips=60.0,     # CLEAR TARGET
            max_trades_per_day=15,     # SELECTIVE (not 100!)
            max_hold_hours=2.0,        # QUICK
            
            # Market Roadmap
            support_levels=[1.3200, 1.3260, 1.3300],
            resistance_levels=[1.3350, 1.3400, 1.3450],
            trend_direction='NEUTRAL_BULLISH',
            volatility_forecast='HIGH (UK GDP + CPI week)',
            
            # Tracking
            current_week_profit=0.0,
            trades_this_week=0,
            win_rate_this_week=0.0
        )
    
    def create_weekly_plan_eur(self) -> WeeklyPairPlan:
        """Create weekly plan for EUR/USD"""
        return WeeklyPairPlan(
            pair='EUR_USD',
            strategy_name='Ultra Strict Forex',
            
            # Weekly Planning
            weekly_target_dollars=2000.0,  # $2K/week
            daily_targets={
                'Monday': 300.0,
                'Tuesday': 350.0,     # Germany ZEW
                'Wednesday': 600.0,   # CPI - BIGGEST
                'Thursday': 400.0,    # Follow-through
                'Friday': 350.0,
            },
            key_events=[
                {'day': 'Tuesday', 'time': '10:00', 'event': 'Germany ZEW', 'impact': 'MEDIUM'},
                {'day': 'Wednesday', 'time': '13:30', 'event': 'U.S. CPI', 'impact': 'EXTREME'},
            ],
            best_trading_days=['Wednesday'],
            avoid_times=[
                {'start': '13:15', 'end': '13:30', 'reason': 'Pre-CPI pause'},
            ],
            
            # Sniper Execution
            entry_zones=[
                {'level': 1.1550, 'type': 'support', 'action': 'BUY'},
                {'level': 1.1600, 'type': 'pivot', 'action': 'BUY'},
                {'level': 1.1650, 'type': 'resistance', 'action': 'SELL'},
            ],
            stop_loss_pips=20.0,       # TIGHT FIXED
            take_profit_pips=50.0,     # CLEAR
            max_trades_per_day=10,     # SELECTIVE
            max_hold_hours=2.0,        # QUICK
            
            # Market Roadmap
            support_levels=[1.1500, 1.1550, 1.1600],
            resistance_levels=[1.1650, 1.1700, 1.1750],
            trend_direction='NEUTRAL',
            volatility_forecast='HIGH (CPI week)',
            
            # Tracking
            current_week_profit=0.0,
            trades_this_week=0,
            win_rate_this_week=0.0
        )
    
    def create_weekly_plan_usdjpy(self) -> WeeklyPairPlan:
        """Create weekly plan for USD/JPY"""
        return WeeklyPairPlan(
            pair='USD_JPY',
            strategy_name='Momentum Trading',
            
            # Weekly Planning
            weekly_target_dollars=2500.0,  # $2.5K/week
            daily_targets={
                'Monday': 400.0,
                'Tuesday': 450.0,     # PPI
                'Wednesday': 700.0,   # CPI - BIGGEST
                'Thursday': 550.0,    # Retail Sales
                'Friday': 400.0,
            },
            key_events=[
                {'day': 'Tuesday', 'time': '13:30', 'event': 'U.S. PPI', 'impact': 'MEDIUM'},
                {'day': 'Wednesday', 'time': '13:30', 'event': 'U.S. CPI', 'impact': 'EXTREME'},
                {'day': 'Thursday', 'time': '13:30', 'event': 'Retail Sales', 'impact': 'HIGH'},
            ],
            best_trading_days=['Wednesday', 'Thursday'],
            avoid_times=[
                {'start': '13:15', 'end': '13:30', 'reason': 'Pre-data pause'},
            ],
            
            # Sniper Execution
            entry_zones=[
                {'level': 151.00, 'type': 'support', 'action': 'BUY'},
                {'level': 151.50, 'type': 'support', 'action': 'BUY'},
                {'level': 152.50, 'type': 'resistance', 'action': 'BUY'},  # Breakout
                {'level': 153.00, 'type': 'resistance', 'action': 'BUY'},
            ],
            stop_loss_pips=30.0,       # TIGHT FIXED (not ATR)
            take_profit_pips=80.0,     # CLEAR TARGET
            max_trades_per_day=12,     # SELECTIVE
            max_hold_hours=2.0,        # QUICK
            
            # Market Roadmap
            support_levels=[150.50, 151.00, 151.50],
            resistance_levels=[152.50, 153.00, 153.50],
            trend_direction='BULLISH',              # BoJ dovish
            volatility_forecast='HIGH (US data week)',
            
            # Tracking
            current_week_profit=0.0,
            trades_this_week=0,
            win_rate_this_week=0.0
        )
    
    def generate_all_weekly_plans(self) -> Dict[str, WeeklyPairPlan]:
        """Generate weekly plans for ALL strategy/pair combinations"""
        
        plans = {}
        
        # Gold
        plans['XAU_USD_Gold'] = self.create_weekly_plan_gold()
        
        # GBP (3 strategies)
        for rank in [1, 2, 3]:
            plans[f'GBP_USD_Rank{rank}'] = self.create_weekly_plan_gbp(rank)
        
        # EUR
        plans['EUR_USD_UltraStrict'] = self.create_weekly_plan_eur()
        
        # USD/JPY
        plans['USD_JPY_Momentum'] = self.create_weekly_plan_usdjpy()
        
        logger.info(f"✅ Generated {len(plans)} weekly roadmaps")
        
        return plans
    
    def get_daily_plan(self, pair: str, strategy_name: str) -> Dict:
        """Get today's specific plan for a pair/strategy"""
        plan_key = f"{pair}_{strategy_name.replace(' ', '_')}"
        
        if plan_key not in self.weekly_plans:
            return None
        
        plan = self.weekly_plans[plan_key]
        today = datetime.now().strftime('%A')  # Monday, Tuesday, etc.
        
        return {
            'pair': pair,
            'strategy': strategy_name,
            'today': today,
            'target_today': plan.daily_targets.get(today, 0),
            'entry_zones': plan.entry_zones,
            'stop_loss': plan.stop_loss_pips,
            'take_profit': plan.take_profit_pips,
            'max_trades': plan.max_trades_per_day,
            'max_hold_hours': plan.max_hold_hours,
            'key_events_today': [e for e in plan.key_events if e['day'] == today],
            'support_levels': plan.support_levels,
            'resistance_levels': plan.resistance_levels,
            'trend': plan.trend_direction,
            'current_profit': plan.current_week_profit,
            'weekly_target': plan.weekly_target_dollars,
            'progress': f"{(plan.current_week_profit / plan.weekly_target_dollars * 100):.1f}%"
        }
    
    def should_trade_now(self, pair: str, strategy_name: str) -> tuple[bool, str]:
        """Check if we should trade this pair right now based on weekly roadmap"""
        plan_key = f"{pair}_{strategy_name.replace(' ', '_')}"
        
        if plan_key not in self.weekly_plans:
            return False, "No weekly plan"
        
        plan = self.weekly_plans[plan_key]
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        # Check avoid times (news events)
        for avoid in plan.avoid_times:
            if avoid['start'] <= current_time <= avoid['end']:
                return False, f"Paused for {avoid['reason']}"
        
        # Check if we hit daily target
        today = now.strftime('%A')
        daily_target = plan.daily_targets.get(today, 0)
        
        # Check if we've hit weekly target (pause if yes)
        if plan.current_week_profit >= plan.weekly_target_dollars:
            return False, f"Weekly target ${plan.weekly_target_dollars} achieved!"
        
        # Check max trades
        if plan.trades_this_week >= plan.max_trades_per_day * 5:  # Weekly limit
            return False, "Weekly trade limit reached"
        
        return True, "Clear to trade"
    
    def get_entry_signal(self, pair: str, current_price: float, strategy_name: str) -> Optional[Dict]:
        """Get sniper entry signal based on weekly roadmap"""
        plan_key = f"{pair}_{strategy_name.replace(' ', '_')}"
        
        if plan_key not in self.weekly_plans:
            return None
        
        plan = self.weekly_plans[plan_key]
        
        # Check each entry zone
        for zone in plan.entry_zones:
            level = zone['level']
            action = zone['action']
            zone_type = zone['type']
            
            # Calculate distance to zone (in pips for forex, dollars for gold)
            if 'XAU' in pair:
                distance = abs(current_price - level)
                tolerance = 3.0  # $3 tolerance
            else:
                distance = abs(current_price - level) * 10000
                tolerance = 5.0  # 5 pips tolerance
            
            # If within tolerance of entry zone
            if distance <= tolerance:
                return {
                    'pair': pair,
                    'action': action,
                    'entry_price': current_price,
                    'entry_zone': level,
                    'zone_type': zone_type,
                    'stop_loss': current_price - plan.stop_loss_pips if action == 'BUY' else current_price + plan.stop_loss_pips,
                    'take_profit': current_price + plan.take_profit_pips if action == 'BUY' else current_price - plan.take_profit_pips,
                    'max_hold_hours': plan.max_hold_hours,
                    'reason': f'{zone_type} at {level}'
                }
        
        return None
    
    def log_weekly_roadmap(self):
        """Log the complete weekly roadmap"""
        logger.info("=" * 80)
        logger.info("📅 WEEKLY TRADING ROADMAP - TRUMP DNA")
        logger.info("=" * 80)
        
        total_weekly_target = 0
        
        for plan_key, plan in self.weekly_plans.items():
            total_weekly_target += plan.weekly_target_dollars
            
            logger.info(f"\n{plan.pair} - {plan.strategy_name}")
            logger.info(f"  Weekly Target: ${plan.weekly_target_dollars}")
            logger.info(f"  Best Days: {', '.join(plan.best_trading_days)}")
            logger.info(f"  Sniper Setup: {plan.stop_loss_pips} pips SL → {plan.take_profit_pips} pips TP")
            logger.info(f"  Max Trades/Day: {plan.max_trades_per_day}")
            logger.info(f"  Max Hold: {plan.max_hold_hours} hours")
            logger.info(f"  Entry Zones: {len(plan.entry_zones)} precise levels")
            logger.info(f"  Trend This Week: {plan.trend_direction}")
        
        logger.info(f"\n💰 TOTAL WEEKLY TARGET: ${total_weekly_target}")
        logger.info("=" * 80)


# Global instance
_trump_dna_planner = None

def get_trump_dna_planner() -> TrumpDNAPlanner:
    """Get Trump DNA planner instance"""
    global _trump_dna_planner
    if _trump_dna_planner is None:
        _trump_dna_planner = TrumpDNAPlanner()
        _trump_dna_planner.weekly_plans = _trump_dna_planner.generate_all_weekly_plans()
        _trump_dna_planner.log_weekly_roadmap()
    return _trump_dna_planner



