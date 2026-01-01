from __future__ import annotations

# Consolidation wrapper: import canonical order manager implementation
# and re-export its symbols so code importing either module gets the same types.
from typing import Any
try:
    from .order_manager import TradeSignal, OrderSide, OrderManager, get_order_manager  # canonical
except Exception:
    # Fallback minimal definitions (should not be used in normal operation)
    from dataclasses import dataclass
    from enum import Enum
    from datetime import datetime
    from typing import Optional

    class OrderSide(Enum):
        BUY = "BUY"
        SELL = "SELL"

    @dataclass
    class TradeSignal:
        instrument: str
        side: OrderSide
        units: int
        entry_price: float
        stop_loss: float
        take_profit: float
        confidence: float
        timestamp: datetime
        strategy_name: str
        account_id: Optional[str] = None

    class OrderManager:
        def __init__(self, accounts: Any = None):
            self.accounts = accounts or []

        def place_order(self, signal: TradeSignal) -> Any:
            return {"status": "queued", "instrument": signal.instrument}

    def get_order_manager(accounts: Any = None) -> OrderManager:
        return OrderManager(accounts)

# Re-export for compatibility
__all__ = ["TradeSignal", "OrderSide", "OrderManager", "get_order_manager"]


