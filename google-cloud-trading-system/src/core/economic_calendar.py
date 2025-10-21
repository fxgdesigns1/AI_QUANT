#!/usr/bin/env python3
"""
Economic Calendar - Hardcoded High-Impact Events
NO API KEYS NEEDED - Events hardcoded for the week ahead
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EconomicEvent:
    """Economic event details"""
    date: str          # 'YYYY-MM-DD'
    time: str          # 'HH:MM' in London time
    event_name: str
    currency: str      # 'USD', 'GBP', 'EUR', etc.
    impact: str        # 'EXTREME', 'HIGH', 'MEDIUM', 'LOW'
    affected_pairs: List[str]
    pause_before_minutes: int  # How many minutes before to pause
    pause_after_minutes: int   # How many minutes after to stay paused

class EconomicCalendar:
    """
    Hardcoded economic calendar
    Update this weekly with upcoming events - NO API NEEDED
    """
    
    def __init__(self):
        self.name = "EconomicCalendar"
        self.events = self._load_this_weeks_events()
        logger.info(f"✅ Economic Calendar loaded with {len(self.events)} events this week")
    
    def _load_this_weeks_events(self) -> List[EconomicEvent]:
        """Load this week's high-impact events - UPDATE WEEKLY"""
        
        # WEEK OF OCTOBER 14-18, 2025
        events = [
            # TUESDAY, OCTOBER 14
            EconomicEvent(
                date='2025-10-14',
                time='13:30',  # London time
                event_name='U.S. PPI (Producer Price Index)',
                currency='USD',
                impact='MEDIUM',
                affected_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
                pause_before_minutes=15,
                pause_after_minutes=15
            ),
            
            # WEDNESDAY, OCTOBER 15 - BIGGEST DAY
            EconomicEvent(
                date='2025-10-15',
                time='13:30',  # London time
                event_name='U.S. CPI (Consumer Price Index)',
                currency='USD',
                impact='EXTREME',
                affected_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD', 'NZD_USD'],
                pause_before_minutes=30,  # Pause 30 min before
                pause_after_minutes=15    # Resume 15 min after
            ),
            
            # THURSDAY, OCTOBER 16
            EconomicEvent(
                date='2025-10-16',
                time='07:00',  # London time
                event_name='UK GDP (Gross Domestic Product)',
                currency='GBP',
                impact='EXTREME',
                affected_pairs=['GBP_USD', 'GBP_JPY', 'EUR_GBP'],
                pause_before_minutes=15,
                pause_after_minutes=15
            ),
            
            EconomicEvent(
                date='2025-10-16',
                time='13:30',  # London time
                event_name='U.S. Retail Sales',
                currency='USD',
                impact='HIGH',
                affected_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
                pause_before_minutes=15,
                pause_after_minutes=10
            ),
            
            EconomicEvent(
                date='2025-10-16',
                time='13:30',  # London time
                event_name='U.S. Initial Jobless Claims',
                currency='USD',
                impact='MEDIUM',
                affected_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY'],
                pause_before_minutes=15,
                pause_after_minutes=10
            ),
            
            # FRIDAY, OCTOBER 17
            EconomicEvent(
                date='2025-10-17',
                time='02:00',  # London time (overnight)
                event_name='China GDP Q3',
                currency='CNY',
                impact='HIGH',
                affected_pairs=['AUD_USD', 'NZD_USD', 'XAU_USD'],
                pause_before_minutes=30,
                pause_after_minutes=30
            ),
        ]
        
        return events
    
    def should_pause_trading(self, pair: str, current_time: Optional[datetime] = None) -> tuple[bool, Optional[str]]:
        """
        Check if trading should be paused RIGHT NOW for this pair
        Returns: (should_pause, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        current_date = current_time.strftime('%Y-%m-%d')
        current_time_str = current_time.strftime('%H:%M')
        
        for event in self.events:
            # Check if event is today
            if event.date != current_date:
                continue
            
            # Check if this pair is affected
            if pair not in event.affected_pairs:
                continue
            
            # Calculate pause window
            event_datetime = datetime.strptime(f"{event.date} {event.time}", '%Y-%m-%d %H:%M')
            pause_start = event_datetime - timedelta(minutes=event.pause_before_minutes)
            pause_end = event_datetime + timedelta(minutes=event.pause_after_minutes)
            
            # Check if we're in pause window
            if pause_start <= current_time <= pause_end:
                minutes_to_event = (event_datetime - current_time).total_seconds() / 60
                
                if minutes_to_event > 0:
                    reason = f"{event.event_name} in {int(minutes_to_event)} min ({event.impact} impact)"
                else:
                    minutes_since = -minutes_to_event
                    reason = f"{event.event_name} just released ({int(minutes_since)} min ago, {event.impact} impact)"
                
                return True, reason
        
        return False, None
    
    def should_avoid_trading(self, pair: str, current_time: Optional[datetime] = None) -> tuple:
        """Alias for is_near_high_impact_news for backwards compatibility"""
        return self.is_near_high_impact_news(pair, current_time)
    
    def get_todays_events(self, pair: Optional[str] = None) -> List[EconomicEvent]:
        """Get today's events, optionally filtered by pair"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        todays_events = [e for e in self.events if e.date == current_date]
        
        if pair:
            todays_events = [e for e in todays_events if pair in e.affected_pairs]
        
        return todays_events
    
    def get_this_weeks_events(self) -> List[EconomicEvent]:
        """Get all events for the current week"""
        return self.events
    
    def get_next_event(self, pair: Optional[str] = None) -> Optional[EconomicEvent]:
        """Get the next upcoming event"""
        now = datetime.now()
        
        upcoming_events = []
        for event in self.events:
            event_time = datetime.strptime(f"{event.date} {event.time}", '%Y-%m-%d %H:%M')
            
            if event_time > now:
                if pair is None or pair in event.affected_pairs:
                    upcoming_events.append((event_time, event))
        
        if upcoming_events:
            upcoming_events.sort(key=lambda x: x[0])
            return upcoming_events[0][1]
        
        return None
    
    def log_weekly_calendar(self):
        """Log the complete weekly calendar"""
        logger.info("=" * 80)
        logger.info("📅 ECONOMIC CALENDAR - THIS WEEK")
        logger.info("=" * 80)
        
        for event in self.events:
            impact_emoji = "🔥" if event.impact == 'EXTREME' else "⚡" if event.impact == 'HIGH' else "📊"
            logger.info(
                f"{impact_emoji} {event.date} {event.time} | {event.event_name} ({event.currency}) | "
                f"Impact: {event.impact} | Pairs: {', '.join(event.affected_pairs[:3])}"
            )
        
        logger.info("=" * 80)


# Global instance
_economic_calendar = None

def get_economic_calendar() -> EconomicCalendar:
    """Get economic calendar instance"""
    global _economic_calendar
    if _economic_calendar is None:
        _economic_calendar = EconomicCalendar()
        _economic_calendar.log_weekly_calendar()
    return _economic_calendar



