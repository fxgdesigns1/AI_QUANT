"""Control Plane API - FastAPI service for dashboard integration

SECURITY:
- Bearer token auth required for POST endpoints
- Never returns secrets in responses
- Serves dashboard static files
- SSE log streaming with redaction
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Security, status, Request
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config_store import ConfigStore
from .log_stream import LogStream
from .strategy_registry import get_strategy_registry, validate_strategy_key
from .status_snapshot import get_status_snapshot
from .trade_ledger import get_trade_ledger


# Environment config
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN", "")
BIND_HOST = os.getenv("CONTROL_PLANE_HOST", "127.0.0.1")
BIND_PORT = int(os.getenv("CONTROL_PLANE_PORT", "8787"))

# Initialize components
config_store = ConfigStore()
log_stream = LogStream()
status_snapshot = get_status_snapshot()
security = HTTPBearer(auto_error=False)

# Create FastAPI app
app = FastAPI(
    title="AI_QUANT Control Plane",
    description="Dashboard API & Config Management (Safe by Default)",
    version="1.0.0"
)

# CORS - disabled by default (same-origin only)
# Uncomment if needed for development with separate frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # Add your frontend URL
#     allow_credentials=True,
#     allow_methods=["GET", "POST"],
#     allow_headers=["*"],
# )


# Request/Response models
class ConfigUpdateRequest(BaseModel):
    """Partial config update request"""
    active_strategy_key: Optional[str] = Field(None, description="Strategy to activate")
    scan_interval_seconds: Optional[int] = Field(None, ge=1, le=3600)
    risk: Optional[Dict[str, Any]] = Field(None, description="Risk settings")
    execution_policy: Optional[Dict[str, Any]] = Field(None, description="Execution policy (advisory)")
    news_integration_enabled: Optional[bool] = None
    ui_theme: Optional[str] = None


class StrategyActivateRequest(BaseModel):
    """Strategy activation request"""
    strategy_key: str = Field(..., description="Strategy key to activate")
    scope: str = Field("global", description="Scope: global or account_id")


class StatusResponse(BaseModel):
    """System status response"""
    mode: str  # paper|live
    execution_enabled: bool
    accounts_loaded: int
    accounts_execution_capable: int
    active_strategy_key: str
    last_scan_at: Optional[str] = None
    last_signals_generated: int = 0
    last_executed_count: int = 0
    weekend_indicator: bool
    config_mtime: float


# Auth helper
def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    """Verify bearer token for POST endpoints"""
    if not CONTROL_PLANE_TOKEN:
        # If no token configured, allow (for local dev only)
        # In production, always set CONTROL_PLANE_TOKEN
        return True
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != CONTROL_PLANE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


# Dashboard static files (mount if directory exists)
dashboard_path = Path(__file__).parent.parent.parent / "dashboard"
if dashboard_path.exists():
    app.mount("/static", StaticFiles(directory=str(dashboard_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve Forensic Command dashboard (canonical UI)"""
    # Serve Forensic Command dashboard from root templates/
    forensic_dashboard = Path(__file__).parent.parent.parent / "templates" / "forensic_command.html"
    if forensic_dashboard.exists():
        return FileResponse(forensic_dashboard, headers={"Cache-Control": "no-store"})
    
    # Fallback: advanced dashboard
    advanced_dashboard = Path(__file__).parent.parent.parent / "templates" / "dashboard_advanced.html"
    if advanced_dashboard.exists():
        return FileResponse(advanced_dashboard, headers={"Cache-Control": "no-store"})
    
    # Fallback: control plane dashboard
    control_plane_dashboard = dashboard_path / "control_plane.html"
    if control_plane_dashboard.exists():
        return FileResponse(control_plane_dashboard, headers={"Cache-Control": "no-store"})
    
    # Last resort: simple message
    return HTMLResponse("""
    <html>
        <head><title>AI_QUANT Control Plane</title></head>
        <body>
            <h1>AI_QUANT Control Plane API</h1>
            <p>API is running. Dashboard files not found.</p>
            <p>API docs: <a href="/docs">/docs</a></p>
            <p>Try: <a href="/api/status">/api/status</a></p>
        </body>
    </html>
    """, headers={"Cache-Control": "no-store"})


@app.get("/advanced", response_class=HTMLResponse)
async def serve_advanced_dashboard():
    """Serve advanced dashboard (fallback UI)"""
    # Serve advanced dashboard from root templates/
    advanced_dashboard = Path(__file__).parent.parent.parent / "templates" / "dashboard_advanced.html"
    if advanced_dashboard.exists():
        return FileResponse(advanced_dashboard)
    
    # Fallback: dashboard/templates/
    fallback_dashboard = dashboard_path / "templates" / "dashboard_advanced.html"
    if fallback_dashboard.exists():
        return FileResponse(fallback_dashboard)
    
    # Last resort: redirect to main
    return HTMLResponse("""
    <html>
        <head><title>Advanced Dashboard Not Found</title></head>
        <body>
            <h1>Advanced Dashboard</h1>
            <p>Advanced dashboard not found. <a href="/">Return to main dashboard</a></p>
        </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": time.time()}


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon (204 No Content to stop browser 404 noise)"""
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/socket.io/{path:path}")
@app.get("/socket.io/")
@app.post("/socket.io/{path:path}")
@app.post("/socket.io/")
async def socket_io_noise_shim(path: str = ""):
    """Noise shim for /socket.io requests (returns 204 to stop 404 spam)
    
    This is an anti-noise shim only. Does NOT implement websocket functionality.
    TradingView widget and other external scripts may attempt socket.io connections.
    Handles both GET (polling transport) and POST (upgrade attempts).
    """
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/insights")
@app.get("/api/insights/{path:path}")
async def insights_noise_shim(path: str = ""):
    """Noise shim for /api/insights requests (returns 204 to stop 404 spam)
    
    This endpoint is blocked in our dashboard code. If external code attempts it,
    return 204 to reduce server log noise. Never fabricate payload.
    """
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/trade_ideas")
@app.get("/api/trade_ideas/{path:path}")
async def trade_ideas_noise_shim(path: str = ""):
    """Noise shim for /api/trade_ideas requests (returns 204 to stop 404 spam)
    
    This endpoint is blocked in our dashboard code. If external code attempts it,
    return 204 to reduce server log noise. Never fabricate payload.
    """
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=300"})


@app.post("/tasks/full_scan")
async def full_scan_noise_shim():
    """Noise shim for POST /tasks/full_scan (returns 204 to stop 404 spam)
    
    This endpoint is blocked in our dashboard code. If external code attempts it,
    return 204 to reduce server log noise. Never fabricate payload.
    """
    return Response(status_code=204, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current system status (NO SECRETS)
    
    Reads from runner status snapshot if available, otherwise returns safe defaults.
    """
    config = config_store.load()
    
    # Try to read runner snapshot first
    snapshot = status_snapshot.read(max_age_seconds=120)
    
    if snapshot:
        # Use data from runner
        return StatusResponse(
            mode=snapshot.get("mode", "paper"),
            execution_enabled=snapshot.get("execution_enabled", False),
            accounts_loaded=snapshot.get("accounts_total", 0),
            accounts_execution_capable=snapshot.get("accounts_execution_capable", 0),
            active_strategy_key=snapshot.get("active_strategy_key", config.active_strategy_key),
            last_scan_at=snapshot.get("last_scan_iso"),
            last_signals_generated=snapshot.get("last_signals_generated", 0),
            last_executed_count=snapshot.get("last_executed_count", 0),
            weekend_indicator=snapshot.get("market_closed", False),
            config_mtime=config_store.get_mtime()
        )
    
    # Fallback: compute from environment (runner not connected)
    trading_mode = os.getenv("TRADING_MODE", "paper").lower()
    paper_execution = os.getenv("PAPER_EXECUTION_ENABLED", "false").lower() == "true"
    live_trading = os.getenv("LIVE_TRADING", "false").lower() == "true"
    live_confirm = os.getenv("LIVE_TRADING_CONFIRM", "false").lower() == "true"
    
    if trading_mode == "live":
        execution_enabled = live_trading and live_confirm
        mode = "live" if execution_enabled else "paper"
    else:
        execution_enabled = paper_execution
        mode = "paper"
    
    # Weekend check (use proper FX market hours)
    from src.core.market_hours import is_fx_market_open
    now_utc = datetime.now(timezone.utc)
    market_open = is_fx_market_open(now_utc)
    weekend_indicator = not market_open  # True if market is closed
    
    return StatusResponse(
        mode=mode,
        execution_enabled=execution_enabled,
        accounts_loaded=0,
        accounts_execution_capable=0,
        active_strategy_key=config.active_strategy_key,
        last_scan_at=None,
        last_signals_generated=0,
        last_executed_count=0,
        weekend_indicator=weekend_indicator,
        config_mtime=config_store.get_mtime()
    )


@app.get("/api/config")
async def get_config():
    """Get runtime config (SANITIZED - NO SECRETS)"""
    config = config_store.load()
    config_dict = config.to_dict()
    
    # Double-check: remove any secret-like keys (paranoid mode)
    sanitized = {k: v for k, v in config_dict.items() 
                 if not any(secret in k.lower() for secret in ["api_key", "password", "secret", "token"])}
    
    return sanitized


@app.get("/api/strategies")
async def get_strategies():
    """Get available strategies (authoritative source of allowed keys)
    
    Returns allowed strategy keys derived from the same registry used for validation.
    This endpoint has NO auth requirement - it's safe to expose allowed keys.
    """
    strategies = get_strategy_registry()
    config = config_store.load()
    
    # Return simple format with allowed keys (authoritative source)
    allowed_keys = sorted(strategies.keys())
    
    return {
        "ok": True,
        "allowed": allowed_keys,
        "default": config.active_strategy_key if config.active_strategy_key in allowed_keys else allowed_keys[0] if allowed_keys else None,
        # Also include full metadata for backward compatibility
        "strategies": [
            {
                "key": info.key,
                "name": info.name,
                "description": info.description,
                "instruments": info.instruments,
                "risk_level": info.risk_level,
                "session_preference": info.session_preference,
            }
            for info in strategies.values()
        ]
    }


@app.post("/api/config")
async def update_config(
    request: ConfigUpdateRequest,
    authenticated: bool = Security(verify_token)
):
    """Update runtime config (ATOMIC with validation)
    
    Requires authentication token
    """
    # Convert request to dict, removing None values
    update_dict = {k: v for k, v in request.dict().items() if v is not None}
    
    try:
        new_config = config_store.save(partial_update=update_dict)
        return {
            "status": "ok",
            "message": "Config updated successfully",
            "config": new_config.to_dict()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save config: {str(e)}"
        )


@app.post("/api/strategy/activate")
async def activate_strategy(
    request: StrategyActivateRequest,
    authenticated: bool = Security(verify_token)
):
    """Activate a strategy (persist to config)
    
    Requires authentication token
    """
    # Validate strategy key
    if not validate_strategy_key(request.strategy_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy key: {request.strategy_key}"
        )
    
    # Update config
    try:
        new_config = config_store.save(partial_update={
            "active_strategy_key": request.strategy_key
        })
        return {
            "status": "ok",
            "message": f"Strategy '{request.strategy_key}' activated",
            "active_strategy": request.strategy_key,
            "config_updated": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate strategy: {str(e)}"
        )


@app.get("/api/logs/stream")
async def stream_logs():
    """Stream logs via SSE (with secret redaction)"""
    
    async def event_generator():
        """Generate SSE events from log stream"""
        # Send initial buffered logs
        initial_lines = await log_stream.tail(num_lines=50)
        for line in initial_lines:
            yield f"data: {line}\n\n"
        
        # Stream new lines
        async for event_data in log_stream.stream():
            yield event_data
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get("/api/contextual/{instrument}")
async def get_contextual_info(instrument: str):
    """Get contextual info for instrument (MINIMAL STUB for existing dashboard compatibility)
    
    The existing dashboard expects this endpoint. We provide a minimal safe response.
    Full contextual data would require integrating with runner state.
    """
    # Safe stub response (no secrets, truthful about limitations)
    return {
        "instrument": instrument,
        "status": "available",
        "note": "Contextual data integration in progress. Use /api/status for system-wide info.",
        "price_available": False,
        "insights_available": False,
        "recommendations": [],
        "metadata": {
            "source": "control_plane_stub",
            "timestamp": time.time()
        }
    }


@app.post("/api/execution/arm")
async def arm_execution(
    authenticated: bool = Security(verify_token)
):
    """Arm execution (ADVISORY - does NOT bypass dual-confirm gate)
    
    This endpoint CANNOT enable live trading alone.
    Live trading still requires LIVE_TRADING=true + LIVE_TRADING_CONFIRM=true in environment.
    
    This is here for completeness but is effectively a no-op for safety.
    """
    return {
        "status": "advisory_only",
        "message": "Execution arming is advisory only. Live trading requires dual-confirm environment variables.",
        "warning": "LIVE_TRADING=true and LIVE_TRADING_CONFIRM=true must be set in runner environment."
    }


# ============================================================================
# DASHBOARD COMPATIBILITY ENDPOINTS
# ============================================================================

@app.get("/api/accounts")
async def get_accounts():
    """Get accounts list (dashboard compatibility)
    
    Returns configured accounts with execution capability status.
    Truthful in signals-only mode: execution_capable=0 when disabled.
    """
    snapshot = status_snapshot.read()
    config = config_store.load()
    
    # Build response from snapshot if available
    if snapshot:
        accounts_data = snapshot.get("accounts", [])
        execution_capable = snapshot.get("accounts_execution_capable", 0)
    else:
        accounts_data = []
        execution_capable = 0
    
    return {
        "ok": True,
        "accounts": accounts_data,
        "execution_capable": execution_capable,
        "mode": snapshot.get("mode", "paper") if snapshot else "paper",
        "execution_enabled": snapshot.get("execution_enabled", False) if snapshot else False,
        "note": "Signals-only mode" if execution_capable == 0 else "Execution enabled",
        "ts_utc": time.time()
    }


@app.get("/api/strategies/overview")
async def get_strategies_overview():
    """Get strategies overview (dashboard compatibility)
    
    Returns strategy registry with active strategy marked.
    """
    config = config_store.load()
    snapshot = status_snapshot.read()
    
    active_key = snapshot.get("active_strategy_key", config.active_strategy_key) if snapshot else config.active_strategy_key
    
    strategies = get_strategy_registry()
    
    strategies_list = [
        {
            "key": info.key,
            "name": info.name,
            "description": info.description,
            "instruments": info.instruments,
            "risk_level": info.risk_level,
            "session_preference": info.session_preference,
            "active": info.key == active_key
        }
        for info in strategies.values()
    ]
    
    return {
        "ok": True,
        "active_strategy": active_key,
        "strategies": strategies_list,
        "ts_utc": time.time()
    }


@app.get("/api/positions")
async def get_positions():
    """Get open positions (dashboard compatibility)
    
    Truthful: returns empty in signals-only mode.
    """
    snapshot = status_snapshot.read()
    
    execution_enabled = snapshot.get("execution_enabled", False) if snapshot else False
    positions = snapshot.get("positions", []) if snapshot else []
    
    return {
        "ok": True,
        "positions": positions,
        "execution_enabled": execution_enabled,
        "source": "signals-only" if not execution_enabled else "live",
        "reason": "Execution disabled - signals-only mode" if not execution_enabled else "Live execution enabled",
        "ts_utc": time.time()
    }


@app.get("/api/signals/pending")
async def get_signals_pending():
    """Get pending signals (dashboard compatibility)
    
    Returns signals generated by scanner. In signals-only mode, these are NOT executed.
    """
    snapshot = status_snapshot.read()
    config = config_store.load()
    
    if snapshot:
        signals = snapshot.get("recent_signals", [])
        active_strategy = snapshot.get("active_strategy_key", config.active_strategy_key)
        last_scan = snapshot.get("last_scan_iso")
        execution_enabled = snapshot.get("execution_enabled", False)
    else:
        signals = []
        active_strategy = config.active_strategy_key
        last_scan = None
        execution_enabled = False
    
    return {
        "ok": True,
        "signals": signals,
        "active_strategy": active_strategy,
        "last_scan_utc": last_scan,
        "execution_enabled": execution_enabled,
        "note": "Signals generated but NOT executed (signals-only)" if not execution_enabled else "Signals will be executed",
        "ts_utc": time.time()
    }


@app.get("/api/trades/pending")
async def get_trades_pending():
    """Get pending trades (dashboard compatibility)
    
    Truthful: returns empty in signals-only mode.
    """
    snapshot = status_snapshot.read()
    
    execution_enabled = snapshot.get("execution_enabled", False) if snapshot else False
    trades = snapshot.get("pending_trades", []) if snapshot else []
    
    return {
        "ok": True,
        "trades": trades,
        "execution_enabled": execution_enabled,
        "reason": "No execution in signals-only mode" if not execution_enabled else "Live execution enabled",
        "ts_utc": time.time()
    }


@app.get("/api/journal/trades")
async def get_journal_trades(limit: int = 50, offset: int = 0):
    """Get executed trades from ledger (journal)
    
    Args:
        limit: Maximum number of trades to return (default: 50)
        offset: Number of trades to skip for pagination (default: 0)
    
    Returns:
        List of executed trades from ledger (most recent first)
    """
    ledger = get_trade_ledger()
    
    # Get status to check if any trades executed
    snapshot = status_snapshot.read()
    last_executed_count = snapshot.get("last_executed_count", 0) if snapshot else 0
    
    # Read trades from ledger
    trades = ledger.read_trades(limit=limit, offset=offset)
    total_count = ledger.count_trades()
    
    return {
        "ok": True,
        "trades": trades,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
        "last_executed_count": last_executed_count,
        "note": "No trades executed yet" if last_executed_count == 0 and total_count == 0 else f"{total_count} trades in ledger",
        "ts_utc": time.time()
    }


@app.get("/api/performance/summary")
async def get_performance_summary(days: int = 30):
    """Get performance summary computed from trade ledger
    
    Args:
        days: Number of days to analyze (default: 30)
    
    Returns:
        Performance metrics computed from ledger
    """
    ledger = get_trade_ledger()
    
    # Read all trades (for now - for large ledgers would need date filtering)
    all_trades = ledger.read_trades(limit=10000, offset=0)  # Read up to 10k trades
    
    # Filter by date if needed (for now just use all)
    from datetime import datetime, timezone, timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    filtered_trades = []
    for trade in all_trades:
        # Parse logged_at or entry_time
        trade_time_str = trade.get("logged_at") or trade.get("entry_time")
        if trade_time_str:
            try:
                trade_time = datetime.fromisoformat(trade_time_str.replace('Z', '+00:00'))
                if trade_time >= cutoff_date:
                    filtered_trades.append(trade)
            except (ValueError, AttributeError):
                # If can't parse date, include it (conservative)
                filtered_trades.append(trade)
        else:
            # If no date, include it
            filtered_trades.append(trade)
    
    # Compute metrics
    closed_trades = [t for t in filtered_trades if t.get("status") == "closed" and t.get("pnl") is not None]
    winning_trades = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in closed_trades if t.get("pnl", 0) < 0]
    
    total_trades = len(closed_trades)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    
    win_rate = (win_count / total_trades) if total_trades > 0 else 0.0
    
    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
    gross_profit = sum(t.get("pnl", 0) for t in winning_trades)
    gross_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    
    # Max drawdown (simplified - would need proper calculation)
    running_pnl = 0
    max_pnl = 0
    max_drawdown = 0.0
    for trade in sorted(closed_trades, key=lambda t: t.get("logged_at", "")):
        running_pnl += trade.get("pnl", 0)
        max_pnl = max(max_pnl, running_pnl)
        drawdown = max_pnl - running_pnl
        max_drawdown = max(max_drawdown, drawdown)
    
    return {
        "ok": True,
        "period_days": days,
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sample_size": len(filtered_trades),
        "note": "Metrics computed from trade ledger",
        "ts_utc": time.time()
    }


@app.get("/api/news")
async def get_news():
    """Get news feed (dashboard compatibility)
    
    Returns news if integration enabled, otherwise empty with reason.
    """
    config = config_store.load()
    snapshot = status_snapshot.read()
    
    news_enabled = config.news_integration_enabled
    news_items = snapshot.get("recent_news", []) if snapshot else []
    
    return {
        "ok": True,
        "enabled": news_enabled,
        "items": news_items,
        "reason": "News integration disabled" if not news_enabled else "News integration active",
        "ts_utc": time.time()
    }


@app.get("/api/sidebar/live-prices")
async def get_sidebar_prices():
    """Get live sidebar prices (dashboard compatibility)
    
    Returns current instrument prices if available from snapshot.
    """
    snapshot = status_snapshot.read()
    
    prices = snapshot.get("live_prices", {}) if snapshot else {}
    
    return {
        "success": True,
        "prices": prices,
        "ts_utc": time.time()
    }


# In-memory opportunity store (no persistence, no execution side effects)
_opportunities_store: Dict[str, Dict[str, Any]] = {}


@app.get("/api/opportunities")
async def get_opportunities():
    """Get trading opportunities (dashboard compatibility)
    
    Returns pending opportunities/signals. In signals-only mode, these are NOT executed.
    Safe: approve/dismiss only updates state; does NOT trigger execution.
    """
    snapshot = status_snapshot.read()
    
    # Get opportunities from store (user-approved/dismissed state)
    opportunities_list = list(_opportunities_store.values())
    
    # If snapshot has recent signals, add them as opportunities (if not already in store)
    if snapshot:
        recent_signals = snapshot.get("recent_signals", [])
        for signal in recent_signals[:10]:  # Limit to recent 10
            signal_id = signal.get("id") or f"signal_{signal.get('instrument', 'unknown')}"
            if signal_id not in _opportunities_store:
                _opportunities_store[signal_id] = {
                    "id": signal_id,
                    "instrument": signal.get("instrument", "UNKNOWN"),
                    "side": signal.get("side", "UNKNOWN"),
                    "status": "pending",
                    "source": "signal"
                }
                opportunities_list.append(_opportunities_store[signal_id])
    
    execution_enabled = snapshot.get("execution_enabled", False) if snapshot else False
    
    return {
        "ok": True,
        "opportunities": opportunities_list,
        "execution_enabled": execution_enabled,
        "note": "Opportunities are informational. Approval does NOT execute trades (signals-only mode)" if not execution_enabled else "Opportunities available",
        "ts_utc": time.time()
    }


@app.post("/api/opportunities/approve")
async def approve_opportunity(
    request: Dict[str, Any],
    authenticated: bool = Security(verify_token)
):
    """Approve an opportunity (dashboard compatibility)
    
    SAFE: This does NOT execute trades. Only updates opportunity state.
    Execution requires environment-based gates (LIVE_TRADING + LIVE_TRADING_CONFIRM).
    """
    opportunity_id = request.get("id") or request.get("opportunity_id")
    
    if not opportunity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing opportunity id"
        )
    
    # Update state in store (no execution side effects)
    if opportunity_id not in _opportunities_store:
        _opportunities_store[opportunity_id] = {"id": opportunity_id, "status": "pending"}
    
    _opportunities_store[opportunity_id]["status"] = "approved"
    _opportunities_store[opportunity_id]["approved_at"] = time.time()
    
    return {
        "ok": True,
        "status": "approved",
        "opportunity_id": opportunity_id,
        "note": "Opportunity approved (state only). Trade execution requires environment-based gates.",
        "warning": "This endpoint does NOT execute trades. Execution requires LIVE_TRADING=true + LIVE_TRADING_CONFIRM=true"
    }


@app.post("/api/opportunities/dismiss")
async def dismiss_opportunity(
    request: Dict[str, Any],
    authenticated: bool = Security(verify_token)
):
    """Dismiss an opportunity (dashboard compatibility)
    
    SAFE: Only updates state; no execution side effects.
    """
    opportunity_id = request.get("id") or request.get("opportunity_id")
    reason = request.get("reason", "User dismissed")
    
    if not opportunity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing opportunity id"
        )
    
    # Update state in store
    if opportunity_id not in _opportunities_store:
        _opportunities_store[opportunity_id] = {"id": opportunity_id, "status": "pending"}
    
    _opportunities_store[opportunity_id]["status"] = "dismissed"
    _opportunities_store[opportunity_id]["dismissed_at"] = time.time()
    _opportunities_store[opportunity_id]["dismiss_reason"] = reason
    
    return {
        "ok": True,
        "status": "dismissed",
        "opportunity_id": opportunity_id,
        "reason": reason
    }


# Startup message
@app.on_event("startup")
async def startup_event():
    """Print startup info"""
    print(f"🚀 AI_QUANT Control Plane starting on http://{BIND_HOST}:{BIND_PORT}")
    print(f"   Dashboard: http://{BIND_HOST}:{BIND_PORT}/")
    print(f"   API Docs: http://{BIND_HOST}:{BIND_PORT}/docs")
    if CONTROL_PLANE_TOKEN:
        print(f"   Auth: Bearer token required for POST endpoints")
    else:
        print(f"   ⚠️  Warning: No CONTROL_PLANE_TOKEN set - authentication disabled")


def run():
    """Run the API server"""
    import uvicorn
    uvicorn.run(
        app,
        host=BIND_HOST,
        port=BIND_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    run()
