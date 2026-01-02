#!/usr/bin/env python3
"""
API Usage Tracker - Individual API monitoring for dashboard
Tracks OANDA, Marketaux, and other APIs separately
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)

@dataclass
class APIUsageStats:
    """API usage statistics for a single API"""
    name: str
    calls_today: int = 0
    daily_limit: int = 10000
    last_call_time: Optional[datetime] = None
    warning_threshold: int = 8000
    
    def get_percentage_used(self) -> float:
        """Calculate percentage of daily limit used"""
        if self.daily_limit == 0:
            return 0.0
        return min(100.0, (self.calls_today / self.daily_limit) * 100)
    
    def get_remaining_calls(self) -> int:
        """Calculate remaining calls available"""
        return max(0, self.daily_limit - self.calls_today)
    
    def get_status_color(self) -> str:
        """Get status color based on usage (green/yellow/red)"""
        percentage = self.get_percentage_used()
        if percentage < 70:
            return "green"
        elif percentage < 90:
            return "yellow"
        else:
            return "red"

class APIUsageTracker:
    """Centralized API usage tracker"""
    
    def __init__(self):
        """Initialize tracker with default limits"""
        self.lock = threading.Lock()
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Initialize API stats with individual limits
        self.apis = {
            'oanda': APIUsageStats(
                name='OANDA',
                daily_limit=int(os.getenv('OANDA_API_LIMIT', '10000')),
                warning_threshold=int(os.getenv('OANDA_API_WARNING', '8000'))
            ),
            'marketaux': APIUsageStats(
                name='Marketaux News',
                daily_limit=int(os.getenv('MARKETAUX_API_LIMIT', '100')),
                warning_threshold=int(os.getenv('MARKETAUX_API_WARNING', '80'))
            ),
            'other': APIUsageStats(
                name='Other APIs',
                daily_limit=int(os.getenv('OTHER_API_LIMIT', '1000')),
                warning_threshold=int(os.getenv('OTHER_API_WARNING', '800'))
            )
        }
        
        # Start daily reset check thread
        self._start_reset_thread()
        logger.info("✅ API Usage Tracker initialized")
    
    def _start_reset_thread(self):
        """Start thread to reset daily counters at midnight"""
        def reset_check():
            ENABLE_BG = os.getenv("ENABLE_DASHBOARD_BACKGROUND_LOOPS", "false").lower() == "true"

            if ENABLE_BG:
                while True:
                    try:
                        import time
                        time.sleep(60)  # Check every minute
                        now = datetime.now()
                        if now.hour == 0 and now.minute == 0:
                            self.reset_daily_counts()
                    except Exception as e:
                        logger.error(f"Reset thread error: {e}")
        
        thread = threading.Thread(target=reset_check, daemon=True)
        thread.start()
    
    def reset_daily_counts(self):
        """Reset all daily API call counts at midnight"""
        with self.lock:
            for api_name, stats in self.apis.items():
                old_count = stats.calls_today
                stats.calls_today = 0
                stats.last_call_time = None
                logger.info(f"🔄 Reset {stats.name} API: {old_count} → 0 calls")
    
    def track_call(self, api_name: str, count: int = 1):
        """Track an API call for a specific API"""
        with self.lock:
            if api_name in self.apis:
                self.apis[api_name].calls_today += count
                self.apis[api_name].last_call_time = datetime.now()
                logger.debug(f"📊 {self.apis[api_name].name}: {self.apis[api_name].calls_today}/{self.apis[api_name].daily_limit}")
            else:
                # Track unknown APIs under 'other'
                self.apis['other'].calls_today += count
                self.apis['other'].last_call_time = datetime.now()
    
    def get_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics for specific API or all APIs"""
        with self.lock:
            if api_name and api_name in self.apis:
                stats = self.apis[api_name]
                return {
                    'name': stats.name,
                    'calls_today': stats.calls_today,
                    'daily_limit': stats.daily_limit,
                    'remaining': stats.get_remaining_calls(),
                    'percentage_used': round(stats.get_percentage_used(), 2),
                    'status_color': stats.get_status_color(),
                    'last_call': stats.last_call_time.isoformat() if stats.last_call_time else None
                }
            else:
                # Return all APIs
                return {
                    name: {
                        'name': stats.name,
                        'calls_today': stats.calls_today,
                        'daily_limit': stats.daily_limit,
                        'remaining': stats.get_remaining_calls(),
                        'percentage_used': round(stats.get_percentage_used(), 2),
                        'status_color': stats.get_status_color(),
                        'last_call': stats.last_call_time.isoformat() if stats.last_call_time else None
                    }
                    for name, stats in self.apis.items()
                }
    
    def update_limit(self, api_name: str, new_limit: int):
        """Update daily limit for an API"""
        with self.lock:
            if api_name in self.apis:
                self.apis[api_name].daily_limit = new_limit
                logger.info(f"🔧 Updated {self.apis[api_name].name} limit to {new_limit}")

# Global instance
_usage_tracker: Optional[APIUsageTracker] = None

def get_usage_tracker() -> APIUsageTracker:
    """Get or create global usage tracker instance"""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = APIUsageTracker()
    return _usage_tracker
