"""Account route."""
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .models import AccountResponse
from .mt5_client import account_info

router = APIRouter()


@router.get("/account", response_model=AccountResponse)
async def account(dep: str = Depends(require_api_key)):
    """Get MT5 account info."""
    acc = account_info()
    if not acc:
        return AccountResponse()
    return AccountResponse(
        login=acc.login,
        server=acc.server or "",
        company=acc.company or "",
        balance=acc.balance,
        equity=acc.equity,
        margin=acc.margin,
        margin_free=acc.margin_free,
        margin_level=acc.margin_level,
        profit=acc.profit,
        currency=acc.currency or "",
        leverage=acc.leverage,
        trade_allowed=acc.trade_allowed,
        trade_expert=acc.trade_expert,
    )
