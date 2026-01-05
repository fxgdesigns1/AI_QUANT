"""
Minimal compatibility shim for market_hours.

Basic market hours functionality.
"""

from datetime import datetime

def is_fx_market_open():
    """Basic FX market hours check"""
    # FX market is generally open 24/5
    now = datetime.now()
    weekday = now.weekday()
    # Monday = 0, Sunday = 6
    # FX closed on weekends
    return weekday < 5  # Monday through Friday