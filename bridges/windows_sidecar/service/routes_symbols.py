"""Symbols routes - tick, spec, overview."""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .models import TickResponse, SymbolSpecResponse, SymbolsOverviewRequest, SymbolsOverviewResponse
from .mt5_client import (
    _find_broker_symbol_variant,
    get_mt5,
    initialize_mt5,
    symbol_info,
    symbol_info_tick,
    symbol_info_tick_with_auto_select,
)

router = APIRouter()


@router.get("/symbols/{symbol}/tick", response_model=TickResponse)
async def symbol_tick(symbol: str, dep: str = Depends(require_api_key)):
    """Get tick for symbol. Auto-selects symbol in Market Watch if needed (read-only safe)."""
    tick, failure_bucket, recommended_fix, broker_symbol_actual = symbol_info_tick_with_auto_select(symbol)
    if not tick or failure_bucket:
        return TickResponse(
            symbol=symbol,
            failure_bucket=failure_bucket or "symbol_not_selected",
            recommended_fix=recommended_fix or "Ensure symbol is visible in Market Watch",
            broker_symbol_actual=broker_symbol_actual,
        )
    now = datetime.now(timezone.utc)
    tick_time = getattr(tick, "time", None)
    tick_age_ms = None
    if tick_time:
        try:
            diff = now - tick_time
            tick_age_ms = int(diff.total_seconds() * 1000)
        except Exception:
            pass
    spread_price = float(tick.ask) - float(tick.bid)
    spread_points = int(round(spread_price * 10000)) if spread_price else 0
    return TickResponse(
        symbol=symbol,
        bid=tick.bid,
        ask=tick.ask,
        last=tick.last,
        spread_points=spread_points,
        spread_price=spread_price,
        tick_time=str(tick_time) if tick_time else None,
        tick_age_ms=tick_age_ms,
    )


@router.get("/symbols/probe/{base_symbol}")
async def symbols_probe(base_symbol: str, dep: str = Depends(require_api_key)):
    """Discover broker symbol variants for a base symbol (e.g. EURUSD -> [EURUSDm, EURUSD.a]).
    Use when symbol_not_found or symbol_name_mismatch to find the actual tradeable symbol."""
    mt5 = get_mt5()
    if not mt5:
        return {"base_symbol": base_symbol, "variants": [], "failure_bucket": "mt5_not_initialized"}
    ok, _, _ = initialize_mt5()
    if not ok:
        return {"base_symbol": base_symbol, "variants": [], "failure_bucket": "mt5_not_initialized"}
    all_syms = mt5.symbols_get() or []
    base_upper = base_symbol.upper()
    variants = [s.name for s in all_syms if base_upper in (getattr(s, "name", "") or "").upper()]
    broker_symbol_actual = _find_broker_symbol_variant(base_symbol, mt5)
    return {
        "base_symbol": base_symbol,
        "variants": sorted(variants)[:20],
        "broker_symbol_actual": broker_symbol_actual,
        "recommended_fix": f"Use /symbols/{broker_symbol_actual}/tick" if broker_symbol_actual else None,
    }


@router.get("/symbols/{symbol}/spec", response_model=SymbolSpecResponse)
async def symbol_spec(symbol: str, dep: str = Depends(require_api_key)):
    """Get symbol specification."""
    info = symbol_info(symbol)
    if not info:
        return SymbolSpecResponse(symbol=symbol)
    return SymbolSpecResponse(
        symbol=info.name,
        digits=info.digits,
        point=info.point,
        trade_contract_size=info.trade_contract_size,
        volume_min=info.volume_min,
        volume_max=info.volume_max,
        volume_step=info.volume_step,
        trade_stops_level=info.trade_stops_level,
        trade_freeze_level=info.trade_freeze_level,
        execution_mode=getattr(info, "trade_execution_mode", getattr(info, "execution_mode", 0)),
        currency_base=info.currency_base or "",
        currency_profit=info.currency_profit or "",
        currency_margin=info.currency_margin or "",
    )


@router.post("/symbols/overview", response_model=SymbolsOverviewResponse)
async def symbols_overview(
    req: SymbolsOverviewRequest,
    dep: str = Depends(require_api_key),
):
    """Get tick overview for multiple symbols."""
    items = []
    for sym in req.symbols or ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]:
        tick = symbol_info_tick(sym)
        if tick:
            items.append({
                "symbol": sym,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": int(round((float(tick.ask) - float(tick.bid)) * 10000)) if tick.ask and tick.bid else 0,
            })
    return SymbolsOverviewResponse(items=items)
