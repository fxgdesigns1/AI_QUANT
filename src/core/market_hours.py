"""
Minimal compatibility shim for market_hours.

Basic market hours functionality.
"""

from datetime import datetime

def is_fx_market_open(dt=None):
    """Basic FX market hours check"""
    # FX market is generally open 24/5
    if dt is None:
        dt = datetime.now()
    weekday = dt.weekday()
    # Monday = 0, Sunday = 6
    # FX closed on weekends
    return weekday < 5  # Monday through Friday