"""
Minimal compatibility shim for paper_broker.

Paper trading simulation - no real money involved.
"""

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