#!/usr/bin/env python3
"""
Historical Data Fetcher
Get recent historical candles from OANDA for strategy validation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

from .oanda_client import get_oanda_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """
    Fetch recent historical candles from OANDA for validation
    Use REAL recent market data to test strategies before deployment
    """
    
    def __init__(self):
        """Initialize historical data fetcher"""
        import os
        
        # Get credentials from environment or use defaults
        api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
        account_id = os.environ.get('OANDA_ACCOUNT_ID', '101-004-30719775-011')
        
        # Import OandaClient directly
        from .oanda_client import OandaClient
        self.client = OandaClient(api_key=api_key, account_id=account_id)
        
        logger.info("✅ Historical Data Fetcher initialized")
    
    def fetch_candles(self, instrument: str, count: int = 48, 
                     granularity: str = 'M5') -> List[Dict]:
        """
        Fetch last N candles from OANDA
        
        Args:
            instrument: e.g., 'EUR_USD'
            count: Number of candles (48 @ M5 = 4 hours)
            granularity: 'M5' (5-min), 'M15' (15-min), 'H1' (1-hour)
        
        Returns:
            List of candle dicts with OHLC data
        """
        try:
            # Use OANDA client's internal method
            url = f"{self.client.base_url}/v3/instruments/{instrument}/candles"
            
            params = {
                'count': count,
                'granularity': granularity,
                'price': 'MBA'  # Mid, Bid, Ask
            }
            
            headers = {
                'Authorization': f'Bearer {self.client.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                candles = data.get('candles', [])
                logger.info(f"✅ Fetched {len(candles)} candles for {instrument}")
                return candles
            else:
                logger.error(f"❌ Failed to fetch candles for {instrument}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error fetching candles for {instrument}: {e}")
            return []
    
    def build_market_data_timeline(self, instruments: List[str], 
                                   hours: int = 4,
                                   granularity: str = 'M5') -> Dict:
        """
        Build complete market data timeline for multiple instruments
        
        Args:
            instruments: List of instruments to fetch
            hours: How many hours of history (default 4)
            granularity: Candle size (default M5)
        
        Returns:
            Dict with timestamp → {instrument → candle_data}
        """
        # Calculate how many candles needed
        if granularity == 'M5':
            count = hours * 12  # 12 candles per hour at 5-min
        elif granularity == 'M15':
            count = hours * 4   # 4 candles per hour at 15-min
        elif granularity == 'H1':
            count = hours       # 1 candle per hour
        else:
            count = hours * 12  # Default to M5
        
        candles_per_instrument = {}
        
        logger.info(f"📥 Fetching {hours}-hour history for {len(instruments)} instruments...")
        
        for instrument in instruments:
            candles = self.fetch_candles(instrument, count=count, granularity=granularity)
            candles_per_instrument[instrument] = candles
        
        # Organize by timestamp for easier strategy processing
        timeline = {}
        
        for instrument, candles in candles_per_instrument.items():
            for candle in candles:
                timestamp = candle.get('time')
                if timestamp not in timeline:
                    timeline[timestamp] = {}
                
                # Extract mid prices for strategy
                mid_data = candle.get('mid', {})
                bid_data = candle.get('bid', {})
                ask_data = candle.get('ask', {})
                
                timeline[timestamp][instrument] = {
                    'time': timestamp,
                    'open': float(mid_data.get('o', 0)),
                    'high': float(mid_data.get('h', 0)),
                    'low': float(mid_data.get('l', 0)),
                    'close': float(mid_data.get('c', 0)),
                    'bid': float(bid_data.get('c', 0)) if bid_data else float(mid_data.get('c', 0)),
                    'ask': float(ask_data.get('c', 0)) if ask_data else float(mid_data.get('c', 0)),
                    'volume': int(candle.get('volume', 1000))
                }
        
        logger.info(f"✅ Built timeline with {len(timeline)} timestamps")
        return timeline
    
    def get_recent_data_for_strategy(self, instruments: List[str], 
                                     hours: int = 4) -> Dict[str, List[Dict]]:
        """
        Get recent historical data formatted for strategy consumption
        
        Returns:
            Dict[instrument → List[price_points]]
        """
        timeline = self.build_market_data_timeline(instruments, hours)
        
        # Convert timeline to instrument-indexed format
        instrument_data = {inst: [] for inst in instruments}
        
        # Sort timestamps
        sorted_times = sorted(timeline.keys())
        
        for timestamp in sorted_times:
            for instrument in instruments:
                if instrument in timeline[timestamp]:
                    instrument_data[instrument].append(timeline[timestamp][instrument])
        
        return instrument_data


# Global instance
_historical_fetcher = None

def get_historical_fetcher() -> HistoricalDataFetcher:
    """Get the global historical data fetcher instance"""
    global _historical_fetcher
    if _historical_fetcher is None:
        _historical_fetcher = HistoricalDataFetcher()
    return _historical_fetcher

