"""
Minimal compatibility shim for order_manager.

Paper-mode only - no actual order execution.
"""

class OrderManager:
    def __init__(self):
        self.paper_mode = True
    
    def place_order(self, order_data):
        """Paper mode - log order but don't execute"""
        print(f"PAPER MODE: Would place order {order_data}")
        return {"status": "paper", "order_id": "paper_123"}
    
    def get_open_orders(self):
        """Return empty orders for paper mode"""
        return []