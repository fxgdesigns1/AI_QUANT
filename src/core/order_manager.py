from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    ERROR = "ERROR"


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
    """Minimal order manager shim - replace with real broker integration."""
    def __init__(self, accounts: Any = None):
        self.accounts = accounts or []

    def place_order(self, signal: TradeSignal) -> Any:
        return {
            "status": "queued",
            "instrument": signal.instrument,
            "side": signal.side.value,
            "units": signal.units,
            "timestamp": signal.timestamp.isoformat(),
        }


def get_order_manager(accounts: Any = None) -> OrderManager:
    return OrderManager(accounts)
