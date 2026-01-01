from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class MarketData:
    instrument: str
    bid: float
    ask: float
    mid: float
    spread: float
    timestamp: datetime
    volume: float = 0.0

    def __init__(
        self,
        instrument: str,
        bid: float,
        ask: float,
        mid: Optional[float] = None,
        spread: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        volume: float = 0.0,
    ) -> None:
        self.instrument = instrument
        self.bid = float(bid)
        self.ask = float(ask)
        self.mid = float(mid) if mid is not None else (self.bid + self.ask) / 2.0
        self.spread = float(spread) if spread is not None else (self.ask - self.bid)
        self.timestamp = timestamp or datetime.utcnow()
        self.volume = float(volume)

class _NullDataFeed:
    def get_snapshot(self, instrument: str) -> Optional[MarketData]:
        return None

    def get_batch(self, instruments: list[str]) -> Dict[str, MarketData]:
        return {}

def get_data_feed(*args: Any, **kwargs: Any) -> _NullDataFeed:
    return _NullDataFeed()
