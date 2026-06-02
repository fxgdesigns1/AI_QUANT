"""
Minimal compatibility shim for paper_broker.

Paper trading simulation - no real money involved.
"""

from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import time
import logging

# Try to import real market data provider
try:
    from src.control_plane.market_data_provider import get_latest_price
    HAS_MARKET_DATA = True
except ImportError:
    HAS_MARKET_DATA = False
    print("WARNING: PaperBroker could not import market_data_provider")

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
        """Get current prices for instruments (REAL OANDA PRICES)
        
        Args:
            instruments: List of instrument names (e.g., ['EUR_USD', 'GBP_USD'])
        
        Returns:
            Dictionary mapping instrument names to Price objects
        """
        result = {}
        
        if HAS_MARKET_DATA:
            for instrument in instruments:
                try:
                    # Fetch REAL price from OANDA
                    p = get_latest_price(instrument)
                    
                    # p from market_data_provider has ts_utc (float)
                    result[instrument] = Price(
                        bid=p.bid,
                        ask=p.ask,
                        mid=p.mid,
                        ts_utc=p.ts_utc
                    )
                except Exception as e:
                    # Log error but don't crash
                    print(f"PaperBroker: Failed to fetch price for {instrument}: {e}")
                    # Do NOT return fake data
                    continue
        else:
            print("PaperBroker: No market data provider available!")
            
        return result
