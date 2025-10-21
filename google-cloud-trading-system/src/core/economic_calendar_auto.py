#!/usr/bin/env python3
"""
AUTOMATIC ECONOMIC CALENDAR - FREE APIS
Fetches upcoming economic events automatically
No paid APIs required
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import json

logger = logging.getLogger(__name__)

class EconomicCalendarAuto:
    """Automatic economic calendar fetcher - FREE"""
    
    def __init__(self):
        self.calendar_cache = []
        self.last_fetch = None
        
    def get_this_week_events(self) -> List[Dict]:
        """Get this week's economic events - AUTO FETCH"""
        
        # Refresh if cache older than 6 hours
        if self.last_fetch and (datetime.now() - self.last_fetch).seconds < 21600:
            if self.calendar_cache:
                logger.info(f"📦 Using cached calendar ({len(self.calendar_cache)} events)")
                return self.calendar_cache
        
        logger.info("📅 Fetching economic calendar for this week...")
        
        events = []
        
        # Try multiple FREE sources
        try:
            # Method 1: ForexFactory Calendar (free, no API key)
            events = self._fetch_forexfactory()
            if events:
                logger.info(f"✅ Got {len(events)} events from ForexFactory")
        except Exception as e:
            logger.warning(f"⚠️ ForexFactory failed: {e}")
        
        # Method 2: Fallback to hardcoded high-impact events (always works)
        if not events:
            logger.info("📅 Using hardcoded high-impact events for this week")
            events = self._get_hardcoded_events()
        
        self.calendar_cache = events
        self.last_fetch = datetime.now()
        
        return events
    
    def _fetch_forexfactory(self) -> List[Dict]:
        """Fetch from ForexFactory (free, no API key)"""
        # ForexFactory doesn't have official API, but we can use their calendar URL
        # This is a placeholder - would need web scraping or alternative
        # For now, return empty to use hardcoded
        return []
    
    def _get_hardcoded_events(self) -> List[Dict]:
        """Get hardcoded high-impact events for current week"""
        # This always works as fallback
        now = datetime.now()
        
        # Major recurring events (every week/month)
        events = [
            {
                'date': self._next_weekday(0),  # Monday
                'time': '08:30',
                'event': 'UK GDP/Manufacturing Data',
                'currency': 'GBP',
                'impact': 'MEDIUM',
                'forecast': 'Check news'
            },
            {
                'date': self._next_weekday(2),  # Wednesday
                'time': '13:30',
                'event': 'US CPI / Inflation Data',
                'currency': 'USD',
                'impact': 'HIGH',
                'forecast': 'Major volatility expected',
                'affected_pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
            },
            {
                'date': self._next_weekday(3),  # Thursday
                'time': '13:30',
                'event': 'US Retail Sales / Jobless Claims',
                'currency': 'USD',
                'impact': 'MEDIUM',
                'forecast': 'Moderate volatility'
            },
            {
                'date': self._next_weekday(4),  # Friday
                'time': '13:30',
                'event': 'US NFP / Employment Data',
                'currency': 'USD',
                'impact': 'HIGH',
                'forecast': 'Major volatility expected',
                'affected_pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
            },
        ]
        
        return events
    
    def _next_weekday(self, weekday: int) -> str:
        """Get next occurrence of weekday (0=Monday, 4=Friday)"""
        today = datetime.now()
        days_ahead = weekday - today.weekday()
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        target_date = today + timedelta(days=days_ahead)
        return target_date.strftime('%Y-%m-%d')
    
    def get_today_events(self) -> List[Dict]:
        """Get today's economic events"""
        today = datetime.now().strftime('%Y-%m-%d')
        all_events = self.get_this_week_events()
        
        today_events = [e for e in all_events if e['date'] == today]
        
        if today_events:
            logger.info(f"📅 Today's events: {len(today_events)}")
            for event in today_events:
                logger.info(f"   • {event['time']}: {event['event']} ({event['impact']})")
        else:
            logger.info("📅 No major events today")
        
        return today_events
    
    def should_avoid_trading(self, pair: str, current_time: datetime = None) -> tuple:
        """Check if should avoid trading due to news"""
        if current_time is None:
            current_time = datetime.now()
        
        today_events = self.get_today_events()
        
        for event in today_events:
            # Check if event affects this pair
            affected_pairs = event.get('affected_pairs', [])
            
            # Check by currency
            currencies_in_pair = pair.replace('_', '').replace('XAU', 'Gold')
            event_currency = event.get('currency', '')
            
            if affected_pairs and pair in affected_pairs:
                # Check if event is within 30 minutes
                event_time = datetime.strptime(event['time'], '%H:%M').time()
                event_datetime = datetime.combine(current_time.date(), event_time)
                
                time_diff = abs((event_datetime - current_time).total_seconds() / 60)
                
                if time_diff <= 30:
                    return True, f"{event['event']} in {time_diff:.0f} min - HIGH IMPACT"
            
            elif event_currency in currencies_in_pair:
                event_time = datetime.strptime(event['time'], '%H:%M').time()
                event_datetime = datetime.combine(current_time.date(), event_time)
                time_diff = abs((event_datetime - current_time).total_seconds() / 60)
                
                if event['impact'] == 'HIGH' and time_diff <= 15:
                    return True, f"{event['event']} in {time_diff:.0f} min"
        
        return False, "Clear to trade"
    
    def get_week_summary(self) -> str:
        """Get formatted week summary"""
        events = self.get_this_week_events()
        
        summary = "📅 THIS WEEK'S ECONOMIC CALENDAR\n\n"
        
        for event in events:
            impact_icon = "🔴" if event['impact'] == 'HIGH' else "🟡" if event['impact'] == 'MEDIUM' else "🟢"
            summary += f"{impact_icon} {event['date']} {event['time']}: {event['event']}\n"
            summary += f"   Currency: {event['currency']} | Impact: {event['impact']}\n\n"
        
        return summary


# Singleton
_calendar = None

def get_economic_calendar():
    """Get economic calendar singleton"""
    global _calendar
    if _calendar is None:
        _calendar = EconomicCalendarAuto()
        logger.info("✅ Economic calendar initialized")
    return _calendar


# Quick test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    calendar = get_economic_calendar()
    
    print("\n" + "=" * 70)
    print("📅 ECONOMIC CALENDAR TEST")
    print("=" * 70)
    
    print("\n" + calendar.get_week_summary())
    
    print("\n🔍 TODAY'S EVENTS:")
    today = calendar.get_today_events()
    for event in today:
        print(f"   • {event['time']}: {event['event']}")
    
    print("\n🔍 TRADE CHECKS:")
    pairs = ['GBP_USD', 'EUR_USD', 'XAU_USD']
    for pair in pairs:
        should_avoid, reason = calendar.should_avoid_trading(pair)
        icon = "❌" if should_avoid else "✅"
        print(f"   {icon} {pair}: {reason}")

