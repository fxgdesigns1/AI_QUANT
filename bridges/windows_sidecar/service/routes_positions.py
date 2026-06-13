"""Positions route."""
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .models import PositionsResponse
from .mt5_client import positions_get

router = APIRouter()


def _pos_to_dict(p) -> dict:
    return {
        "ticket": p.ticket,
        "symbol": p.symbol,
        "type": p.type,
        "volume": p.volume,
        "price_open": p.price_open,
        "price_current": p.price_current,
        "profit": p.profit,
        "sl": p.sl,
        "tp": p.tp,
    }


@router.get("/positions", response_model=PositionsResponse)
async def positions(dep: str = Depends(require_api_key)):
    """Get open positions."""
    poses = positions_get()
    items = [_pos_to_dict(p) for p in poses]
    return PositionsResponse(count=len(items), positions=items)
