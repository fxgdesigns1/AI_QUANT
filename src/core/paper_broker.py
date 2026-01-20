"""
Minimal compatibility shim for paper_broker.

Paper trading uses OANDA Practice API (real prices, paper account).
"""

from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Price:
    """Price data structure"""

    bid: float
    ask: float
    mid: float
    ts_utc: float = 0.0

class PaperBroker:
    def __init__(self):
        self.paper_balance = 10000.0  # $10k paper money
        self.paper_positions = []
    
    def get_balance(self):
        """Return paper balance"""
        return self.paper_balance
    
    def place_trade(self, trade_data):
        """Simulate paper trade"""
        print(f"PAPER TRADE: {trade_data}")
        return {"status": "paper_filled", "trade_id": "paper_456"}
    
    def get_positions(self):
        """Return paper positions"""
        return self.paper_positions
    
    def get_current_prices(self, instruments: List[str]) -> Dict[str, Price]:
        """Get current prices for instruments from OANDA API (NOT synthetic)
        
        CRITICAL: Uses real OANDA prices to prevent stale price issues.
        Paper trading uses OANDA Practice API with real current prices.
        
        Args:
            instruments: List of instrument names (e.g., ['EUR_USD', 'GBP_USD'])
        
        Returns:
            Dictionary mapping instrument names to Price objects
        """
        result = {}
        
        # Use market_data_provider to get REAL current prices
        try:
            from src.control_plane.market_data_provider import get_latest_price
            
            for instrument in instruments:
                try:
                    price_obj = get_latest_price(instrument, timeout_s=5.0, validate=False)
                    result[instrument] = Price(
                        bid=price_obj.bid,
                        ask=price_obj.ask,
                        mid=price_obj.mid,
                        ts_utc=price_obj.ts_utc
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch price for {instrument}: {e}")
                    # Fail closed: skip this instrument rather than using stale data
                    continue
            
            if result:
                logger.debug(f"✅ Fetched {len(result)} real prices from OANDA")
            else:
                logger.warning(f"⚠️ No prices fetched for instruments {instruments}")
        
        except ImportError:
            # Fallback if market_data_provider not available (should not happen)
            logger.error("❌ market_data_provider not available - cannot fetch real prices")
            # Return empty dict (fail closed)
            return {}
        
        return result
