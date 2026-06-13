"""History route - scaffolding for future read-only history."""
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .config import BRIDGE_ID
from .models import ts_utc

router = APIRouter()


@router.get("/history")
async def history(dep: str = Depends(require_api_key)):
    """History read scaffolding. Deferred scope - returns empty for now."""
    return {
        "count": 0,
        "deals": [],
        "ts_utc": ts_utc(),
        "bridge_id": BRIDGE_ID,
        "note": "History endpoint scaffolding - deferred scope",
    }
