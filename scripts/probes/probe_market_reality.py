#!/usr/bin/env python3
"""
Probe Step 1: Market Reality Check
Verify that backend market data actually reflects the 2% XAUUSD move.
"""
import sys
import os
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.control_plane.market_data_provider import get_candles, MarketDataError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_market_reality")

def probe_market_reality():
    instrument = "XAU_USD"
    logger.info(f"Probing market reality for {instrument}...")
    
    try:
        # Fetch last 24h candles (M15 granularity to cover 24h with reasonable count)
        # 24h * 4 = 96 candles. Let's get 100.
        candles = get_candles(instrument, granularity="M15", count=100)
        
        if not candles:
            logger.error(f"No candles returned for {instrument}")
            return
        
        # Calculate 24h High/Low
        highs = [c.h for c in candles]
        lows = [c.l for c in candles]
        
        max_h = max(highs)
        min_l = min(lows)
        
        move_pct = ((max_h - min_l) / min_l) * 100.0
        
        logger.info(f"Analysis Period: {candles[0].time} to {candles[-1].time}")
        logger.info(f"24h High: {max_h}")
        logger.info(f"24h Low: {min_l}")
        logger.info(f"Move %: {move_pct:.2f}%")
        
        if move_pct > 2.0:
            logger.info("VERIFIED: Market data reflects > 2.0% move.")
        elif move_pct > 1.5:
             logger.warning("PARTIAL: Market data reflects > 1.5% move but < 2.0%.")
        else:
            logger.error("FAILURE: Market data shows < 1.5% move. Data pipeline suspect.")
            
    except MarketDataError as e:
        logger.error(f"Market Data Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    probe_market_reality()
