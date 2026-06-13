"""Orders route (read-only)."""
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .models import OrdersResponse
from .mt5_client import orders_get

router = APIRouter()


def _order_to_dict(o) -> dict:
    return {
        "ticket": o.ticket,
        "symbol": o.symbol,
        "type": o.type,
        "volume_current": o.volume_current,
        "price_open": o.price_open,
        "sl": o.sl,
        "tp": o.tp,
        "time_setup": getattr(o, "time_setup", None),
    }


@router.get("/orders", response_model=OrdersResponse)
async def orders(dep: str = Depends(require_api_key)):
    """Get pending orders."""
    ords = orders_get()
    items = [_order_to_dict(o) for o in ords]
    return OrdersResponse(count=len(items), orders=items)
