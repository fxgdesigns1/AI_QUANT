from enum import Enum
from typing import Any

# Minimal, clean compatibility shim for order_manager to deploy to VM.
class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeSignal:
    def __init__(self, *args, **kwargs):
        # allow multiple alias names used across the codebase
        self.account_id = kwargs.get("account_id") or kwargs.get("account") or kwargs.get("acct") or None
        self.instrument = kwargs.get("instrument") or kwargs.get("pair") or kwargs.get("symbol") or None
        self.side = kwargs.get("side") or kwargs.get("order_side") or None
        self.quantity = kwargs.get("quantity") or kwargs.get("qty") or kwargs.get("units") or None
        self.price = kwargs.get("price") or kwargs.get("entry_price") or None
        self.take_profit = kwargs.get("take_profit") or kwargs.get("tp") or None
        self.stop_loss = kwargs.get("stop_loss") or kwargs.get("sl") or None
        self.strategy_id = kwargs.get("strategy_id") or kwargs.get("strategy") or None

    def __repr__(self):
        return f"<TradeSignal instrument={self.instrument} side={self.side} qty={self.quantity} tp={self.take_profit} sl={self.stop_loss} account={self.account_id}>"

def get_order_manager(*args: Any, **kwargs: Any) -> Any:
    return None































