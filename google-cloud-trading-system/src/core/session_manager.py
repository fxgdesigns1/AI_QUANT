#!/usr/bin/env python3
"""
Session Manager - Trading Session Awareness
Tracks active market sessions and provides timezone-aware scheduling
"""

import logging
import pytz
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketSession(Enum):
    """Market session types"""
    SYDNEY = "Sydney"
    TOKYO = "Tokyo"
    LONDON = "London"
    NEWYORK = "New York"
    OVERLAP_LONDON_NY = "London-NY Overlap"
    OVERLAP_TOKYO_LONDON = "Tokyo-London Overlap"
    WEEKEND = "Weekend"
    OFF_HOURS = "Off Hours"

class SessionQuality(Enum):
    """Session quality for trading"""
    PRIME = 5    # Best liquidity and price action (London-NY overlap)
    HIGH = 4     # High liquidity (core London or NY)
    MEDIUM = 3   # Decent liquidity (early London, late NY)
    LOW = 2      # Lower liquidity (Tokyo)
    POOR = 1     # Poor liquidity (Sydney, late night)
    AVOID = 0    # Avoid trading (weekend, off-hours)

class SessionManager:
    """
    Manages market session information and timezone conversions
    Provides session quality scores and filters for trading decisions
    """
    
    def __init__(self):
        """Initialize session manager"""
        self.name = "Session Manager"
        
        # Primary timezone (London)
        self.primary_tz = pytz.timezone('Europe/London')
        
        # Session times in UTC
        # Sydney: 22:00-07:00 UTC
        # Tokyo: 00:00-09:00 UTC
        # London: 08:00-16:00 UTC
        # New York: 13:00-21:00 UTC
        self.session_times = {
            MarketSession.SYDNEY: (22, 7),    # 22:00-07:00 UTC
            MarketSession.TOKYO: (0, 9),      # 00:00-09:00 UTC
            MarketSession.LONDON: (8, 16),    # 08:00-16:00 UTC
            MarketSession.NEWYORK: (13, 21),  # 13:00-21:00 UTC
            MarketSession.OVERLAP_LONDON_NY: (13, 16),  # 13:00-16:00 UTC (prime trading hours)
            MarketSession.OVERLAP_TOKYO_LONDON: (8, 9)  # 08:00-09:00 UTC
        }
        
        # Session quality scores (0-100)
        self.session_quality_scores = {
            MarketSession.OVERLAP_LONDON_NY: 100,   # Prime trading hours
            MarketSession.LONDON: 85,               # London core
            MarketSession.NEWYORK: 80,              # NY core
            MarketSession.OVERLAP_TOKYO_LONDON: 65, # Tokyo-London overlap
            MarketSession.TOKYO: 50,                # Tokyo core
            MarketSession.SYDNEY: 40,               # Sydney core
            MarketSession.OFF_HOURS: 20,            # Off hours
            MarketSession.WEEKEND: 0                # Weekend - avoid
        }
        
        # Weekend days (5=Saturday, 6=Sunday)
        self.weekend_days = {5, 6}
        
        logger.info(f"✅ {self.name} initialized")
    
    def get_current_sessions(self, timestamp: Optional[datetime] = None) -> Set[MarketSession]:
        """
        Get currently active market sessions
        
        Args:
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            Set of active MarketSession enums
        """
        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
        elif timestamp.tzinfo is None:
            # Assume UTC if no timezone provided
            timestamp = pytz.UTC.localize(timestamp)
        else:
            # Convert to UTC
            timestamp = timestamp.astimezone(pytz.UTC)
        
        # Check if weekend
        if timestamp.weekday() in self.weekend_days:
            return {MarketSession.WEEKEND}
        
        # Get current hour in UTC
        current_hour = timestamp.hour
        
        # Find active sessions
        active_sessions = set()
        
        for session, (start_hour, end_hour) in self.session_times.items():
            # Handle sessions that cross midnight
            if start_hour > end_hour:
                if current_hour >= start_hour or current_hour < end_hour:
                    active_sessions.add(session)
            else:
                if start_hour <= current_hour < end_hour:
                    active_sessions.add(session)
        
        # If no sessions active, it's off-hours
        if not active_sessions:
            active_sessions.add(MarketSession.OFF_HOURS)
        
        return active_sessions
    
    def get_session_quality(self, timestamp: Optional[datetime] = None) -> Tuple[int, Set[MarketSession]]:
        """
        Get session quality score (0-100) for trading
        
        Args:
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            Tuple of (quality_score, active_sessions)
        """
        active_sessions = self.get_current_sessions(timestamp)
        
        # If weekend, quality is 0
        if MarketSession.WEEKEND in active_sessions:
            return 0, active_sessions
        
        # Get highest quality score from active sessions
        quality_score = max(self.session_quality_scores.get(session, 0) for session in active_sessions)
        
        return quality_score, active_sessions
    
    def is_session_active(self, session: MarketSession, timestamp: Optional[datetime] = None) -> bool:
        """
        Check if specific session is active
        
        Args:
            session: MarketSession to check
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            True if session is active
        """
        return session in self.get_current_sessions(timestamp)
    
    def is_prime_trading_time(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Check if current time is prime trading hours (London-NY overlap)
        
        Args:
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            True if prime trading time
        """
        return MarketSession.OVERLAP_LONDON_NY in self.get_current_sessions(timestamp)
    
    def should_trade_now(self, min_quality: int = 65, timestamp: Optional[datetime] = None) -> bool:
        """
        Determine if current session is suitable for trading
        
        Args:
            min_quality: Minimum quality score required (0-100)
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            True if session quality meets minimum requirement
        """
        quality, _ = self.get_session_quality(timestamp)
        return quality >= min_quality
    
    def get_next_session_time(self, session: MarketSession, from_time: Optional[datetime] = None) -> datetime:
        """
        Get next time when specified session starts
        
        Args:
            session: MarketSession to find start time for
            from_time: Optional start time (defaults to now)
            
        Returns:
            datetime of next session start
        """
        if from_time is None:
            from_time = datetime.now(pytz.UTC)
        elif from_time.tzinfo is None:
            from_time = pytz.UTC.localize(from_time)
        else:
            from_time = from_time.astimezone(pytz.UTC)
        
        # Get session start hour
        start_hour, _ = self.session_times.get(session, (0, 0))
        
        # Create target time for today
        target = from_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        # If target is in the past, move to next day
        if target <= from_time:
            target += timedelta(days=1)
        
        # If session is on weekend, move to Monday
        while target.weekday() in self.weekend_days:
            target += timedelta(days=1)
        
        return target
    
    def get_session_start_end(self, session: MarketSession, date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """
        Get start and end times for a specific session on a given date
        
        Args:
            session: MarketSession to get times for
            date: Optional date (defaults to today)
            
        Returns:
            Tuple of (session_start, session_end) datetimes
        """
        if date is None:
            date = datetime.now(pytz.UTC)
        elif date.tzinfo is None:
            date = pytz.UTC.localize(date)
        else:
            date = date.astimezone(pytz.UTC)
        
        # Get session hours
        start_hour, end_hour = self.session_times.get(session, (0, 0))
        
        # Create start and end times
        start_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        # Handle sessions that cross midnight
        if start_hour > end_hour:
            end_time = start_time.replace(hour=end_hour) + timedelta(days=1)
        else:
            end_time = start_time.replace(hour=end_hour)
        
        return start_time, end_time
    
    def get_session_progress(self, session: MarketSession, timestamp: Optional[datetime] = None) -> float:
        """
        Get progress through current session as percentage (0.0 - 1.0)
        
        Args:
            session: MarketSession to check progress for
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Progress as float (0.0 = just started, 1.0 = ending)
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
        elif timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(pytz.UTC)
        
        # Get session start/end times
        start_time, end_time = self.get_session_start_end(session, timestamp)
        
        # Calculate total session duration and elapsed time
        total_duration = (end_time - start_time).total_seconds()
        elapsed = (timestamp - start_time).total_seconds()
        
        # Calculate progress percentage (clamped to 0.0 - 1.0)
        progress = max(0.0, min(1.0, elapsed / total_duration if total_duration > 0 else 0.0))
        
        return progress
    
    def is_session_opening(self, session: MarketSession, timestamp: Optional[datetime] = None, threshold_minutes: int = 30) -> bool:
        """
        Check if within opening period of a session
        
        Args:
            session: MarketSession to check
            timestamp: Optional timestamp (defaults to now)
            threshold_minutes: Minutes from open to consider "opening" (default: 30)
            
        Returns:
            True if within opening period
        """
        if not self.is_session_active(session, timestamp):
            return False
        
        progress = self.get_session_progress(session, timestamp)
        threshold = threshold_minutes / (self.get_session_duration_minutes(session) or 60)
        
        return progress <= threshold
    
    def is_session_closing(self, session: MarketSession, timestamp: Optional[datetime] = None, threshold_minutes: int = 30) -> bool:
        """
        Check if within closing period of a session
        
        Args:
            session: MarketSession to check
            timestamp: Optional timestamp (defaults to now)
            threshold_minutes: Minutes from close to consider "closing" (default: 30)
            
        Returns:
            True if within closing period
        """
        if not self.is_session_active(session, timestamp):
            return False
        
        progress = self.get_session_progress(session, timestamp)
        threshold = threshold_minutes / (self.get_session_duration_minutes(session) or 60)
        
        return progress >= (1.0 - threshold)
    
    def get_session_duration_minutes(self, session: MarketSession) -> int:
        """
        Get session duration in minutes
        
        Args:
            session: MarketSession to get duration for
            
        Returns:
            Duration in minutes
        """
        start_hour, end_hour = self.session_times.get(session, (0, 0))
        
        # Handle sessions that cross midnight
        if start_hour > end_hour:
            duration_hours = (24 - start_hour) + end_hour
        else:
            duration_hours = end_hour - start_hour
        
        return duration_hours * 60
    
    def format_time_for_location(self, timestamp: datetime, timezone_str: str = 'Europe/London') -> str:
        """
        Format time for specific timezone (default: London)
        
        Args:
            timestamp: Datetime to format
            timezone_str: Timezone string (default: 'Europe/London')
            
        Returns:
            Formatted time string
        """
        if timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        
        local_time = timestamp.astimezone(pytz.timezone(timezone_str))
        return local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    
    def get_session_description(self, timestamp: Optional[datetime] = None) -> str:
        """
        Get human-readable description of current session
        
        Args:
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Session description string
        """
        active_sessions = self.get_current_sessions(timestamp)
        quality, _ = self.get_session_quality(timestamp)
        
        if MarketSession.WEEKEND in active_sessions:
            return "Weekend - Markets Closed"
        
        if MarketSession.OVERLAP_LONDON_NY in active_sessions:
            return "London-NY Overlap (Prime Trading Hours) - Excellent Liquidity"
        
        if MarketSession.LONDON in active_sessions and MarketSession.NEWYORK in active_sessions:
            return "London and New York Sessions - High Liquidity"
        
        if MarketSession.LONDON in active_sessions:
            return "London Session - Good Liquidity"
        
        if MarketSession.NEWYORK in active_sessions:
            return "New York Session - Good Liquidity"
        
        if MarketSession.TOKYO in active_sessions:
            return "Tokyo Session - Moderate Liquidity"
        
        if MarketSession.SYDNEY in active_sessions:
            return "Sydney Session - Lower Liquidity"
        
        return "Off Hours - Limited Liquidity"
    
    def get_next_prime_session(self) -> Tuple[datetime, str]:
        """
        Get next prime trading session start time
        
        Returns:
            Tuple of (next_session_start, description)
        """
        # Get next London-NY overlap session
        next_start = self.get_next_session_time(MarketSession.OVERLAP_LONDON_NY)
        
        # Format time in London timezone
        formatted_time = self.format_time_for_location(next_start)
        
        return next_start, f"Next prime trading session (London-NY Overlap): {formatted_time}"


# Global instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


if __name__ == "__main__":
    # Test session manager
    sm = get_session_manager()
    
    # Current time
    now = datetime.now(pytz.UTC)
    london_time = now.astimezone(pytz.timezone('Europe/London'))
    
    print(f"Current time (UTC): {now}")
    print(f"Current time (London): {london_time}")
    
    # Get active sessions
    active_sessions = sm.get_current_sessions()
    print(f"Active sessions: {active_sessions}")
    
    # Get session quality
    quality, _ = sm.get_session_quality()
    print(f"Session quality: {quality}/100")
    
    # Get session description
    description = sm.get_session_description()
    print(f"Session description: {description}")
    
    # Check if prime trading time
    is_prime = sm.is_prime_trading_time()
    print(f"Prime trading time: {is_prime}")
    
    # Get next prime session
    _, next_prime = sm.get_next_prime_session()
    print(next_prime)



