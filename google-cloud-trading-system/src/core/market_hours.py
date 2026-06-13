"""FX Market Hours — Accurate timezone-aware market open/close detection

FX markets open Sunday ~22:00 UTC and close Friday ~22:00 UTC.
This module provides authoritative market hours detection.

CRITICAL: Use timezone-aware UTC datetime for all calculations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def is_fx_market_open(now_utc: datetime | None = None) -> bool:
    """Check if FX market is currently open (timezone-aware UTC)
    
    FX Market Hours:
    - Opens: Sunday ~22:00 UTC (varies by DST; typically 21:00-23:00 UTC)
    - Closes: Friday ~22:00 UTC (varies by DST; typically 21:00-23:00 UTC)
    - Closed: Saturday all day, Sunday before ~22:00 UTC
    
    Args:
        now_utc: UTC datetime (timezone-aware). If None, uses datetime.utcnow().
    
    Returns:
        True if market is open, False if closed
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    else:
        # Ensure timezone-aware
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
    
    weekday = now_utc.weekday()  # 0=Monday, 6=Sunday
    hour = now_utc.hour
    
    # Saturday: always closed
    if weekday == 5:  # Saturday
        return False
    
    # Sunday: opens at ~22:00 UTC (use 21:30 UTC as conservative threshold)
    if weekday == 6:  # Sunday
        return hour >= 21  # Market opens Sunday 21:00-23:00 UTC (conservative: 21:00+)
    
    # Monday-Thursday: always open
    if weekday in (0, 1, 2, 3):  # Monday-Thursday
        return True
    
    # Friday: closes at ~22:00 UTC (use 21:30 UTC as conservative threshold)
    if weekday == 4:  # Friday
        return hour < 22  # Market closes Friday 21:00-23:00 UTC (conservative: before 22:00)
    
    return False


def get_market_status(now_utc: datetime | None = None) -> dict[str, any]:
    """Get detailed market status (timezone-aware UTC)
    
    Returns:
        Dict with keys:
        - market_open: bool
        - weekend_indicator: bool (True if weekend or market closed)
        - next_open: str | None (ISO timestamp of next market open)
        - next_close: str | None (ISO timestamp of next market close)
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    else:
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
    
    market_open = is_fx_market_open(now_utc)
    weekday = now_utc.weekday()
    hour = now_utc.hour
    
    # Weekend indicator: True if Saturday, Sunday before open, or Friday after close
    if weekday == 5:  # Saturday
        weekend_indicator = True
        next_open = (now_utc.replace(hour=21, minute=0, second=0, microsecond=0) 
                     + timedelta(days=1))  # Sunday 21:00 UTC
    elif weekday == 6 and hour < 21:  # Sunday before open
        weekend_indicator = True
        next_open = now_utc.replace(hour=21, minute=0, second=0, microsecond=0)
    elif weekday == 4 and hour >= 22:  # Friday after close
        weekend_indicator = True
        next_open = (now_utc.replace(hour=21, minute=0, second=0, microsecond=0) 
                     + timedelta(days=3))  # Monday (effectively Sunday 21:00 UTC)
    else:
        weekend_indicator = False
        if weekday == 4:  # Friday, market still open
            next_close = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
        else:
            next_close = (now_utc.replace(hour=22, minute=0, second=0, microsecond=0) 
                          + timedelta(days=(4 - weekday)))  # Next Friday 22:00 UTC
    
    return {
        "market_open": market_open,
        "weekend_indicator": weekend_indicator,
        "next_open": next_open.isoformat() if 'next_open' in locals() else None,
        "next_close": next_close.isoformat() if 'next_close' in locals() else None,
        "timestamp_utc": now_utc.isoformat()
    }
