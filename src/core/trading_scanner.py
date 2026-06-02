"""
Minimal compatibility shim for trading_scanner.

This allows the runner to start in paper mode for status/scanning only.
"""

class TradingScanner:
    def __init__(self):
        pass
    
    def scan_opportunities(self):
        """Return empty opportunities for paper mode"""
        return []
    
    def get_market_status(self):
        """Return basic market status"""
        return {"status": "paper_mode", "opportunities": 0}