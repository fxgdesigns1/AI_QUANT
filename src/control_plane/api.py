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
import requests
import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Security, status, Request, Header, Query
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
import hashlib
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config_store import ConfigStore
from .log_stream import LogStream
from .strategy_registry import get_strategy_registry, validate_strategy_key
from .status_snapshot import get_status_snapshot
from .trade_ledger import get_trade_ledger
from .news_provider import fetch_news_with_registry
try:
    from news_manager import NewsManager
except Exception:
    NewsManager = None
from .audit_log import get_audit_log
from .outlook_engine import get_outlook_engine
from .structural_scanner import get_structural_scanner
from src.core.truth_envelope import TruthEnvelope

# Import Adaptive Components for Market Overview
try:
    from src.core.market_regime import MarketRegimeDetector
    HAS_ADAPTIVE = True
except ImportError:
    HAS_ADAPTIVE = False


# Environment config
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN", "")
BIND_HOST = os.getenv("CONTROL_PLANE_HOST", "0.0.0.0")
BIND_PORT = int(os.getenv("CONTROL_PLANE_PORT", "8787"))
NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "300"))

# Initialize components
config_store = ConfigStore()
log_stream = LogStream()
status_snapshot = get_status_snapshot()
audit_log = get_audit_log()
outlook_engine = get_outlook_engine()
structural_scanner = get_structural_scanner()
security = HTTPBearer(auto_error=False)

if HAS_ADAPTIVE:
    regime_detector = MarketRegimeDetector()
else:
    regime_detector = None

# Simple in-memory cache for news provider calls (rate-limit safe)
_news_cache: List[Dict[str, Any]] = []
_news_cache_status: Dict[str, Any] = {}
_news_cache_ts: float = 0.0

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
class StrategyAssignmentRequest(BaseModel):
    """Strategy assignment request model"""
    account_id: str = Field(..., description="OANDA account ID")
    strategy_key: str = Field(..., description="Strategy key from registry")
    enabled: bool = Field(True, description="Whether assignment is enabled")


class ConfigUpdateRequest(BaseModel):
    """Partial config update request"""
    active_strategy_key: Optional[str] = Field(None, description="Strategy to activate (legacy, used only when strategy_assignments is empty)")
    strategy_assignments: Optional[List[StrategyAssignmentRequest]] = Field(None, description="Multi-account strategy assignments (up to 10)")
    max_strategy_assignments: Optional[int] = Field(None, ge=1, le=10, description="Maximum strategy assignments (default 10)")
    scan_interval_seconds: Optional[int] = Field(None, ge=1, le=3600)
    risk: Optional[Dict[str, Any]] = Field(None, description="Risk settings")
    account_risk_limits: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Per-account risk limits (account_id -> {max_daily_trades, enabled})")
    execution_policy: Optional[Dict[str, Any]] = Field(None, description="Execution policy (advisory)")
    news_integration_enabled: Optional[bool] = None
    ui_theme: Optional[str] = None


class StrategyActivateRequest(BaseModel):
    """Strategy activation request"""
    strategy_key: str = Field(..., description="Strategy key to activate")
    scope: str = Field("global", description="Scope: global or account_id")


class ExecutionGuardStatus(BaseModel):
    """Execution guard status (no secrets)"""
    allowed: bool
    reason_code: str
    mode: str  # paper|live


class StatusResponse(BaseModel):
    """System status response
    
    Contract compliance (v1):
    - accounts_loaded: Total accounts loaded (filtered by allowlist)
    - accounts_with_strategy: Accounts that have strategy assignments (alias for assigned_accounts_count)
    - accounts_execution_enabled: Accounts that can execute (alias for accounts_execution_capable)
    - daily_limit_current: Current daily limit per account (from config, dict format)
    - daily_trades_today: Current daily trades count per account (dict format)
    """
    mode: str  # paper|live
    execution_enabled: bool
    accounts_loaded: int
    accounts_execution_capable: int
    active_strategy_key: str
    active_strategy_assignments_count: int = 0  # Number of enabled strategy assignments
    assigned_accounts_count: int = 0  # Number of accounts with assigned strategies
    last_scan_at: Optional[str] = None
    last_status_write_at: Optional[str] = None
    last_signals_generated: int = 0
    last_executed_count: int = 0
    weekend_indicator: bool
    status_write_ok: bool = True
    last_status_write_error_reason: Optional[str] = None
    config_mtime: float
    execution_guard: ExecutionGuardStatus  # Guard status with reason codes
    system_label: str = "UNKNOWN"  # ALPHA, BETA, UNKNOWN
    # Contract-required fields (v1)
    accounts_with_strategy: int = 0  # Alias for assigned_accounts_count (contract compliance)
    accounts_execution_enabled: int = 0  # Alias for accounts_execution_capable (contract compliance)
    daily_limit_current: Optional[Dict[str, int]] = None  # account_id -> limit (0=unlimited, None=use global)
    daily_trades_today: Optional[Dict[str, int]] = None  # account_id -> count (resets daily)
    
    # Observability (v1.1)
    price_sanity_blocks_per_account: Optional[Dict[str, int]] = None
    price_integrity_blocks_per_account: Optional[Dict[str, int]] = None  # NEW
    tp_omitted_per_account: Optional[Dict[str, int]] = None
    throttle_skips_per_account: Optional[Dict[str, int]] = None
    oanda_cancel_reasons_per_account: Optional[Dict[str, Dict[str, int]]] = None
    execution_suspended_accounts: Optional[Dict[str, Dict[str, Any]]] = None


def _freshness_ms_from_timestamp_utc(ts: Optional[Any]) -> Optional[int]:
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, timezone.utc)
        elif isinstance(ts, str):
            cleaned = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        else:
            return None
        now = datetime.now(timezone.utc)
        delta = now - dt
        ms = int(delta.total_seconds() * 1000)
        return ms if ms >= 0 else 0
    except Exception:
        return None


def _truth_wrap(
    payload: Any,
    *,
    complete: bool,
    source: str = "control_plane",
    assumptions: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    last_verified_at: Optional[str] = None,
    freshness_ms: Optional[int] = None,
) -> Dict[str, Any]:
    envelope_source = "live" if complete else "none"
    if complete:
        truth = TruthEnvelope.live(
            source=envelope_source,
            freshness_ms=freshness_ms,
            last_verified_at=last_verified_at,
            assumptions=assumptions,
            warnings=warnings,
        )
    else:
        truth = TruthEnvelope.none(
            source=envelope_source,
            reason=(warnings[0] if warnings else None),
            assumptions=assumptions,
            warnings=warnings,
            last_verified_at=last_verified_at,
        )
    return {"data": payload, "truth": truth.to_dict()}


def _csv_from_rows(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    fieldnames = sorted({key for row in rows for key in row.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


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
        content = forensic_dashboard.read_bytes()
        digest = hashlib.sha256(content).hexdigest()[:12]
        html = content.decode("utf-8", errors="ignore").replace("__UI_HASH__", digest)
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-UI-Version": digest,
        }
        return HTMLResponse(html, headers=headers)
    
    # Truth mode: do not serve alternate dashboard templates
    return HTMLResponse("""
    <html>
        <head><title>AI_QUANT Control Plane</title></head>
        <body>
            <h1>AI_QUANT Control Plane API</h1>
            <p>Forensic dashboard template not found.</p>
            <p>API docs: <a href="/docs">/docs</a></p>
            <p>Try: <a href="/api/status">/api/status</a></p>
        </body>
    </html>
    """, headers={"Cache-Control": "no-store"})


@app.get("/api/ui/version")
async def get_ui_version():
    """Expose current UI template hash for cache verification."""
    forensic_dashboard = Path(__file__).parent.parent.parent / "templates" / "forensic_command.html"
    if not forensic_dashboard.exists():
        return _truth_wrap(
            {"ok": False, "reason": "template_missing"},
            complete=False,
            source="control_plane",
            warnings=["template_missing"],
        )
    content = forensic_dashboard.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:12]
    payload = {
        "ok": True,
        "ui_hash": digest,
        "mtime": forensic_dashboard.stat().st_mtime,
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="control_plane",
    )


@app.get("/advanced", response_class=HTMLResponse)
async def serve_advanced_dashboard():
    """Serve advanced dashboard (fallback UI)"""
    # Truth mode: advanced dashboard disabled unless truth-certified
    return HTMLResponse("""
    <html>
        <head><title>Advanced Dashboard Not Found</title></head>
        <body>
            <h1>Advanced Dashboard</h1>
            <p>Advanced dashboard disabled in truth mode. <a href="/">Return to main dashboard</a></p>
        </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/v1/audit")
async def get_audit_log(limit: int = 100):
    """Get recent audit log entries (append-only ledger)
    
    Returns last N entries.
    Safe: No secrets returned (sanitized at write time).
    """
    # Enforce reasonable limit
    limit = min(max(1, limit), 1000)
    
    entries = audit_log.read_tail(n=limit)
    payload = {
        "ok": True,
        "entries": entries,
        "count": len(entries),
        "limit": limit,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="audit_log",
    )


@app.get("/api/v1/outlook/{horizon}")
async def get_outlook(horizon: str):
    """Get market outlook for horizon (daily/weekly/monthly)
    
    Returns latest computed snapshot.
    Deterministic and Read-Only.
    """
    if horizon not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid horizon")
        
    snapshot = outlook_engine.get_latest(horizon)
    if not snapshot:
        # If missing, try to recompute on the fly (it's fast and safe)
        try:
            snapshot = outlook_engine.compute(horizon)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate outlook: {str(e)}")
            
    payload = {
        "ok": True,
        "horizon": horizon,
        "outlook": snapshot,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="outlook_engine",
    )


@app.post("/api/v1/outlook/recompute")
async def recompute_outlook(
    request: Request,
    authenticated: bool = Security(verify_token)
):
    """Force recompute of outlook snapshots (Admin Gated)"""
    try:
        # Recompute all horizons
        results = {}
        for h in ["daily", "weekly", "monthly"]:
            results[h] = outlook_engine.compute(h)
            
        audit_log.log(
            actor="admin",
            action="recompute_outlook",
            status="success",
            details={"path": "/api/v1/outlook/recompute", "method": "POST", "note": "Recomputed all outlook horizons"}
        )
        
        payload = {
            "ok": True,
            "message": "Outlook recomputed successfully",
            "horizons_updated": list(results.keys()),
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="outlook_engine",
        )
    except Exception as e:
        audit_log.log(
            actor="admin",
            action="recompute_outlook",
            status="failure",
            details={"path": "/api/v1/outlook/recompute", "method": "POST", "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/scanner/structural")
async def get_structural_scan():
    """Get structural scanner results (Read-Only)"""
    try:
        results = structural_scanner.scan()
        payload = {
            "ok": True,
            "data": results,
            "results": results.get("results", []),  # Also include at top level for UI
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="structural_scanner",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scanner failed: {str(e)}")


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


def _filter_accounts_by_allowlist(accounts: list, account_id_prefix: str, allowlist: list[str]) -> list:
    """Filter accounts based on suffix allowlist"""
    if not allowlist:
        return accounts  # No filtering if allowlist is empty
    
    filtered = []
    for acc in accounts:
        # Extract account ID (could be full ID or masked)
        acc_id = acc.get("id") or acc.get("id_masked") or acc.get("account_id") or ""
        if not acc_id:
            continue
        
        # If masked (last 4 chars), check suffix directly
        if len(acc_id) <= 4:
            suffix = acc_id
            if suffix in allowlist:
                filtered.append(acc)
        else:
            # Full ID: check if ends with prefix + allowed suffix
            if acc_id.startswith(account_id_prefix):
                suffix = acc_id[len(account_id_prefix):]
                if suffix in allowlist:
                    filtered.append(acc)
    return filtered


@app.get("/api/status")
async def get_status():
    """Get current system status (NO SECRETS)
    
    Reads from runner status snapshot if available, otherwise returns safe defaults.
    Includes execution guard status with reason codes.
    Includes system_label for dashboard identity.
    """
    from src.core.execution_gate import ExecutionGuard
    from src.core.settings import settings
    
    config = config_store.load()
    guard = ExecutionGuard()
    guard_status = guard.get_guard_status()
    
    # Get system label (from settings, fallback to hostname)
    system_label = settings.system_label
    if system_label == "UNKNOWN":
        import socket
        hostname = socket.gethostname()
        if "alpha" in hostname.lower() or "paper" in hostname.lower():
            system_label = "ALPHA"
        elif "beta" in hostname.lower() or "novstyle" in hostname.lower():
            system_label = "BETA"
    
    # Try to read runner snapshot first
    snapshot = status_snapshot.read(max_age_seconds=120)
    
    # If snapshot read fails or is stale, ensure we don't return null for last_status_write_at if we can help it
    # (But really, if snapshot is None, we don't know the write time)
    
    if snapshot:
        # Filter accounts by allowlist if configured
        accounts_raw = snapshot.get("accounts", [])
        accounts_filtered = _filter_accounts_by_allowlist(
            accounts_raw,
            settings.account_id_prefix,
            settings.account_suffix_allowlist
        )
        
        # Filter strategy assignments by allowlist too
        assignments_count = 0
        assigned_accounts = set()
        if config.strategy_assignments:
            for assignment in config.strategy_assignments:
                if not assignment.enabled:
                    continue
                # Check if account matches allowlist
                acc_id = assignment.account_id
                if settings.account_suffix_allowlist:
                    if acc_id.startswith(settings.account_id_prefix):
                        suffix = acc_id[len(settings.account_id_prefix):]
                        if suffix not in settings.account_suffix_allowlist:
                            continue  # Skip this assignment
                assignments_count += 1
                assigned_accounts.add(assignment.account_id)
        
        # Recalculate accounts_loaded from filtered accounts
        accounts_loaded_count = len(accounts_filtered) if accounts_filtered else snapshot.get("accounts_total", 0)
        
        # Filter daily limits and trades by allowlist
        daily_limit_current = snapshot.get("daily_limit_current", {})
        daily_trades_today = snapshot.get("daily_trades_today", {})
        price_sanity_blocks = snapshot.get("price_sanity_blocks_per_account", {})
        price_integrity_blocks = snapshot.get("price_integrity_blocks_per_account", {})  # NEW
        tp_omitted = snapshot.get("tp_omitted_per_account", {})
        throttle_skips = snapshot.get("throttle_skips_per_account", {})
        oanda_cancels = snapshot.get("oanda_cancel_reasons_per_account", {})
        
        # Filter to only accounts in allowlist
        if settings.account_suffix_allowlist and settings.account_id_prefix:
            def filter_dict(d):
                res = {}
                for k, v in d.items():
                    if k.startswith(settings.account_id_prefix):
                        suffix = k[len(settings.account_id_prefix):]
                        if suffix in settings.account_suffix_allowlist:
                            res[k] = v
                return res

            daily_limit_current = filter_dict(daily_limit_current)
            daily_trades_today = filter_dict(daily_trades_today)
            price_sanity_blocks = filter_dict(price_sanity_blocks)
            tp_omitted = filter_dict(tp_omitted)
            throttle_skips = filter_dict(throttle_skips)
            oanda_cancels = filter_dict(oanda_cancels)
        
        # Use data from runner
        status_payload = StatusResponse(
            mode=snapshot.get("mode", "paper"),
            execution_enabled=snapshot.get("execution_enabled", False),
            accounts_loaded=accounts_loaded_count,
            accounts_execution_capable=snapshot.get("accounts_execution_capable", 0),
            active_strategy_key=snapshot.get("active_strategy_key", config.active_strategy_key),
            active_strategy_assignments_count=assignments_count,
            assigned_accounts_count=len(assigned_accounts),
            last_scan_at=snapshot.get("last_scan_iso"),
            last_status_write_at=snapshot.get("last_status_write_at"),
            last_signals_generated=snapshot.get("last_signals_generated", 0),
            last_executed_count=snapshot.get("last_executed_count", 0),
            weekend_indicator=snapshot.get("market_closed", False),
            config_mtime=config_store.get_mtime(),
            execution_guard=ExecutionGuardStatus(**guard_status),
            system_label=system_label,
            status_write_ok=True,
            last_status_write_error_reason=None,
            # Contract compliance (v1)
            accounts_with_strategy=len(assigned_accounts),
            accounts_execution_enabled=snapshot.get("accounts_execution_capable", 0),
            daily_limit_current=daily_limit_current if daily_limit_current else None,
            daily_trades_today=daily_trades_today if daily_trades_today else None,
            # Observability (v1.1)
            price_sanity_blocks_per_account=price_sanity_blocks if price_sanity_blocks else None,
            price_integrity_blocks_per_account=price_integrity_blocks if price_integrity_blocks else None,  # NEW
            tp_omitted_per_account=tp_omitted if tp_omitted else None,
            throttle_skips_per_account=throttle_skips if throttle_skips else None,
            oanda_cancel_reasons_per_account=oanda_cancels if oanda_cancels else None,
            execution_suspended_accounts=snapshot.get("execution_suspended_accounts"),
        ).dict()
        last_verified_at = snapshot.get("last_status_write_at") or snapshot.get("last_scan_iso")
        return _truth_wrap(
            status_payload,
            complete=True,
            source="status_snapshot",
            last_verified_at=last_verified_at,
            freshness_ms=_freshness_ms_from_timestamp_utc(last_verified_at),
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
    
    # Compute assignment counts from config
    assignments_count = 0
    assigned_accounts = set()
    if config.strategy_assignments:
        for assignment in config.strategy_assignments:
            if assignment.enabled:
                assignments_count += 1
                assigned_accounts.add(assignment.account_id)
    
    # Build daily limit map from config (fallback when runner not connected)
    daily_limit_current = {}
    if config.account_risk_limits:
        for account_id, limits in config.account_risk_limits.items():
            if limits.max_daily_trades is not None:
                daily_limit_current[account_id] = limits.max_daily_trades
            else:
                daily_limit_current[account_id] = config.risk.max_daily_trades_per_account
    
    status_payload = StatusResponse(
        mode=mode,
        execution_enabled=execution_enabled,
        accounts_loaded=0,
        accounts_execution_capable=0,
        active_strategy_key=config.active_strategy_key,
        active_strategy_assignments_count=assignments_count,
        assigned_accounts_count=len(assigned_accounts),
        last_scan_at=None,
        last_status_write_at=None,  # Runner not connected, no snapshot writes
        last_signals_generated=0,
        last_executed_count=0,
        weekend_indicator=weekend_indicator,
        config_mtime=config_store.get_mtime(),
        execution_guard=ExecutionGuardStatus(**guard_status),
        system_label=system_label,
        status_write_ok=False,  # Runner not connected, assume write failed
        last_status_write_error_reason="Runner not connected (no status snapshot available)",
        # Contract compliance (v1)
        accounts_with_strategy=len(assigned_accounts),
        accounts_execution_enabled=0,  # Unknown when runner not connected
        daily_limit_current=daily_limit_current if daily_limit_current else None,
        daily_trades_today=None,  # Unknown when runner not connected
        price_sanity_blocks_per_account=None,
        tp_omitted_per_account=None,
        throttle_skips_per_account=None,
        oanda_cancel_reasons_per_account=None,
        execution_suspended_accounts=None,
    ).dict()
    return _truth_wrap(
        status_payload,
        complete=False,
        source="status_snapshot",
        warnings=["Runner not connected (no status snapshot available)"],
        last_verified_at=None,
        freshness_ms=None,
    )


@app.get("/api/truth/status")
async def get_truth_status():
    """Aggregate backend truth status for dashboard gating."""
    snapshot = status_snapshot.read(max_age_seconds=120)
    audit_entries = audit_log.read_tail(n=1)
    outlook_daily = outlook_engine.get_latest("daily")

    checks = {
        "status_snapshot": bool(snapshot),
        "audit_log": audit_entries is not None,
        "outlook_daily": bool(outlook_daily),
        "structural_scanner": structural_scanner is not None,
        "trade_ledger": get_trade_ledger() is not None,
    }

    any_ok = any(checks.values())
    all_ok = all(checks.values())
    system_truth_state = "FULL" if all_ok else ("PARTIAL" if any_ok else "NONE")

    payload = {
        "system_truth_state": system_truth_state,
        "checks": checks,
        "ts_utc": time.time(),
    }
    return _truth_wrap(
        payload,
        complete=all_ok,
        source="control_plane",
        warnings=None if all_ok else ["One or more truth sources unavailable"],
    )


@app.get("/api/trades/active")
async def get_active_trades():
    """Get active trades/open positions for all accounts (read-only, NO SECRETS)
    
    TRUTHY: Queries OANDA directly for each account in ACCOUNT_SUFFIX_ALLOWLIST.
    Returns exactly one entry per allowlisted account, never silently omits accounts.
    Includes account_suffix, open_trades_count, open_positions_count, lastTransactionID, error.
    """
    import requests
    from datetime import datetime, timezone
    
    from src.core.settings import settings
    
    # Get system label
    system_label = settings.system_label
    if system_label == "UNKNOWN":
        import socket
        hostname = socket.gethostname()
        if "alpha" in hostname.lower() or "paper" in hostname.lower():
            system_label = "ALPHA"
        elif "beta" in hostname.lower() or "novstyle" in hostname.lower():
            system_label = "BETA"
    
    # Get OANDA credentials
    oanda_api_key = settings.oanda_api_key
    oanda_base_url = os.getenv("OANDA_BASE_URL", "")
    if not oanda_base_url:
        env = settings.oanda_env
        if env == "live":
            oanda_base_url = "https://api-fxtrade.oanda.com"
        else:
            oanda_base_url = "https://api-fxpractice.oanda.com"
    
    # Get account suffixes from allowlist (REQUIRED - never silently return empty)
    account_suffixes = settings.account_suffix_allowlist
    if not account_suffixes:
        # If allowlist is empty, return error but still return empty accounts array (not None)
        payload = {
            "ok": False,
            "error": "ACCOUNT_SUFFIX_ALLOWLIST not configured",
            "system_label": system_label,
            "refreshed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "accounts": []
        }
        return _truth_wrap(
            payload,
            complete=False,
            source="oanda",
            warnings=["ACCOUNT_SUFFIX_ALLOWLIST not configured"],
        )
    
    if not oanda_api_key:
        # If OANDA key missing, still return all allowlisted accounts with error field
        account_results = []
        for account_suffix in account_suffixes:
            account_results.append({
                "account_suffix": account_suffix,
                "open_trades_count": None,
                "open_positions_count": None,
                "lastTransactionID": None,
                "error": "OANDA_API_KEY not configured"
            })
        payload = {
            "ok": False,
            "error": "OANDA_API_KEY not configured",
            "system_label": system_label,
            "refreshed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "accounts": account_results
        }
        return _truth_wrap(
            payload,
            complete=False,
            source="oanda",
            warnings=["OANDA_API_KEY not configured"],
        )
    
    headers = {
        "Authorization": f"Bearer {oanda_api_key}",
        "Content-Type": "application/json"
    }
    
    account_results = []
    overall_ok = False
    
    # Query OANDA directly for each allowlisted account
    for account_suffix in account_suffixes:
        account_id = f"{settings.account_id_prefix}{account_suffix}"
        account_id_masked = f"{account_id[:3]}***{account_id[-3:]}" if len(account_id) > 6 else "***"
        
        account_result = {
            "account_suffix": account_suffix,
            "account_id_masked": account_id_masked,
            "open_trades_count": 0,
            "open_positions_count": 0,
            "lastTransactionID": None,
            "trades": [],  # Include trades array for dashboard display
            "error": None
        }
        
        try:
            # Get account summary (includes lastTransactionID)
            summary_url = f"{oanda_base_url}/v3/accounts/{account_id}/summary"
            summary_r = requests.get(summary_url, headers=headers, timeout=20)
            
            if summary_r.status_code == 200:
                summary_data = summary_r.json()
                account_info = summary_data.get("account", {})
                account_result["lastTransactionID"] = account_info.get("lastTransactionID")
                # Add account balance metrics
                account_result["balance"] = float(account_info.get("balance", 0))
                account_result["equity"] = float(account_info.get("NAV", 0))  # NAV is equity
                account_result["margin_used"] = float(account_info.get("marginUsed", 0))
                account_result["margin_available"] = float(account_info.get("marginAvailable", 0))
                account_result["currency"] = account_info.get("currency", "USD")
            elif summary_r.status_code == 401:
                account_result["error"] = f"OANDA auth failed (401) for account {account_suffix}"
                account_results.append(account_result)
                continue
            else:
                account_result["error"] = f"OANDA summary failed: {summary_r.status_code}"
                # Continue to try openTrades anyway
            
            # Get open trades
            trades_url = f"{oanda_base_url}/v3/accounts/{account_id}/openTrades"
            trades_r = requests.get(trades_url, headers=headers, timeout=20)
            
            if trades_r.status_code == 200:
                trades_data = trades_r.json()
                raw_trades = trades_data.get("trades", [])
                # Normalize trade fields for frontend (currentUnits -> units)
                normalized_trades = []
                for trade in raw_trades:
                    normalized_trade = {
                        "id": trade.get("id"),
                        "instrument": trade.get("instrument"),
                        "price": trade.get("price"),
                        "units": trade.get("currentUnits") or trade.get("units") or "0",  # Map currentUnits -> units
                        "unrealizedPL": trade.get("unrealizedPL") or "0.0000",
                        "openTime": trade.get("openTime"),
                        "state": trade.get("state"),
                        "initialUnits": trade.get("initialUnits"),
                        "realizedPL": trade.get("realizedPL") or "0.0000",
                    }
                    normalized_trades.append(normalized_trade)
                account_result["open_trades_count"] = len(normalized_trades)
                # Include normalized trades array for dashboard display
                account_result["trades"] = normalized_trades
                overall_ok = True
            elif trades_r.status_code == 401:
                account_result["error"] = f"OANDA auth failed (401) for account {account_suffix}"
            else:
                account_result["error"] = f"OANDA openTrades failed: {trades_r.status_code}"
            
            # Get open positions
            positions_url = f"{oanda_base_url}/v3/accounts/{account_id}/openPositions"
            positions_r = requests.get(positions_url, headers=headers, timeout=20)
            
            if positions_r.status_code == 200:
                positions_data = positions_r.json()
                positions = positions_data.get("positions", [])
                # Count only positions with non-zero units
                account_result["open_positions_count"] = len([p for p in positions if float(p.get("long", {}).get("units", "0") or "0") != 0 or float(p.get("short", {}).get("units", "0") or "0") != 0])
            elif positions_r.status_code != 401:  # 401 already set above
                if not account_result["error"]:
                    account_result["error"] = f"OANDA openPositions failed: {positions_r.status_code}"
            
        except Exception as e:
            account_result["error"] = str(e)[:200]
        
        account_results.append(account_result)
    
    payload = {
        "ok": overall_ok,
        "system_label": system_label,
        "refreshed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "accounts": account_results
    }
    return _truth_wrap(
        payload,
        complete=overall_ok,
        source="oanda",
        warnings=None if overall_ok else ["Partial or failed OANDA fetch"],
    )


@app.get("/api/market/overview")
async def get_market_overview():
    """Get read-only Market Overview (prices + last signal/scan metadata + REGIME)
    
    Returns bid/ask prices for configured instruments, system metadata, and adaptive regime info.
    Does NOT place orders or execute trades.
    Resilient: shows error status per instrument if OANDA auth fails.
    """
    from src.control_plane.market_data_provider import get_latest_price, get_candles, MarketDataError
    from src.core.settings import settings
    
    # Get system label
    system_label = settings.system_label
    if system_label == "UNKNOWN":
        import socket
        hostname = socket.gethostname()
        if "alpha" in hostname.lower() or "paper" in hostname.lower():
            system_label = "ALPHA"
        elif "beta" in hostname.lower() or "novstyle" in hostname.lower():
            system_label = "BETA"
    
    # Default instruments (can be extended via config later)
    instruments = ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY"]
    
    # Get last scan/signal metadata from status snapshot
    status_data = status_snapshot.read(max_age_seconds=120) or {}
    last_scan_at = status_data.get("last_scan_at")
    last_signals_generated = status_data.get("last_signals_generated", 0)
    last_executed_count = status_data.get("last_executed_count", 0)
    
    # Fetch prices and regimes for each instrument
    instrument_results = []
    for instrument in instruments:
        try:
            # 1. Get Price
            price_data = get_latest_price(instrument, timeout_s=5.0)
            
            # 2. Get Regime (if adaptive system enabled)
            regime_info = {"regime": "UNKNOWN", "desc": "N/A", "adx": 0}
            if HAS_ADAPTIVE and regime_detector:
                try:
                    # Get recent candles for regime analysis
                    candles = get_candles(instrument, granularity="M5", count=60)
                    if candles and len(candles) > 50:
                        analysis = regime_detector.detect_regime(instrument, candles)
                        regime_info = {
                            "regime": analysis.regime.value,
                            "desc": analysis.description,
                            "adx": round(analysis.adx, 1)
                        }
                except Exception as e:
                    # Don't fail the whole request if regime fails
                    regime_info = {"regime": "ERROR", "desc": str(e)[:20], "adx": 0}

            instrument_results.append({
                "instrument": instrument,
                "bid": price_data.bid,
                "ask": price_data.ask,
                "mid": price_data.mid,
                "time": datetime.fromtimestamp(price_data.ts_utc, tz=timezone.utc).isoformat() + "Z",
                "status": "ok",
                "regime": regime_info
            })
        except MarketDataError as e:
            instrument_results.append({
                "instrument": instrument,
                "bid": None,
                "ask": None,
                "mid": None,
                "time": None,
                "status": "error",
                "error": str(e)[:200],  # Truncate error, no secrets
                "regime": None
            })
        except Exception as e:
            instrument_results.append({
                "instrument": instrument,
                "bid": None,
                "ask": None,
                "mid": None,
                "time": None,
                "status": "error",
                "error": f"Unexpected error: {str(e)[:200]}",
                "regime": None
            })
    
    payload = {
        "system_label": system_label,
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "instruments": instrument_results,
        "metadata": {
            "last_scan_at": last_scan_at,
            "last_signals_generated": last_signals_generated,
            "last_executed_count": last_executed_count
        }
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="market_data_provider",
        last_verified_at=payload["ts_utc"],
    )


@app.get("/api/config")
async def get_config():
    """Get runtime config (SANITIZED - NO SECRETS)
    
    Returns:
        - ok: boolean (true if config loaded successfully, false if error)
        - error_reason: string | null (error message if ok=false, null if ok=true)
        - risk: object (risk config section)
        - account_risk_limits_count: int (count of per-account limits)
        - ... (other config fields)
    """
    try:
        config = config_store.load()
        config_dict = config.to_dict()
        
        # Double-check: remove any secret-like keys (paranoid mode)
        sanitized = {k: v for k, v in config_dict.items() 
                     if not any(secret in k.lower() for secret in ["api_key", "password", "secret", "token"])}
        
        # Extract risk section
        risk = sanitized.get("risk", {})
        
        # Count account risk limits
        account_risk_limits = sanitized.get("account_risk_limits", {})
        if isinstance(account_risk_limits, dict):
            account_risk_limits_count = len(account_risk_limits)
        elif isinstance(account_risk_limits, list):
            account_risk_limits_count = len(account_risk_limits)
        else:
            account_risk_limits_count = 0
        
        # Remove system fields from sanitized dict to prevent overwrites
        sanitized.pop("ok", None)
        sanitized.pop("error_reason", None)
        sanitized.pop("account_risk_limits_count", None)
        
        # Return with ok=true (always boolean, never null)
        payload = {
            "ok": True,
            "error_reason": None,
            "risk": risk,
            "account_risk_limits_count": account_risk_limits_count,
            **sanitized
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="config_store",
        )
    except Exception as e:
        # On any error, return ok=false with error_reason
        error_reason = str(e)[:200]  # Bounded string, no secrets
        payload = {
            "ok": False,
            "error_reason": error_reason,
            "risk": {},
            "account_risk_limits_count": 0
        }
        return _truth_wrap(
            payload,
            complete=False,
            source="config_store",
            warnings=[error_reason],
        )


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
    
    strategies_payload = []
    for key, info in strategies.items():
        item_key = getattr(info, "key", None) or getattr(info, "strategy_key", None) or key
        name = getattr(info, "name", None) or getattr(info, "display_name", None) or str(item_key)
        description = getattr(info, "description", None) or ""
        instruments = getattr(info, "instruments", None) or []
        risk_level = getattr(info, "risk_level", None) or "unknown"
        session_preference = getattr(info, "session_preference", None) or "any"
        strategies_payload.append({
            "key": item_key,
            "name": name,
            "description": description,
            "instruments": instruments,
            "risk_level": risk_level,
            "session_preference": session_preference,
        })

    payload = {
        "ok": True,
        "allowed": allowed_keys,
        "default": config.active_strategy_key if config.active_strategy_key in allowed_keys else allowed_keys[0] if allowed_keys else None,
        # Also include full metadata for backward compatibility
        "strategies": strategies_payload
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="strategy_registry",
    )


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
    
    # Convert strategy_assignments from Pydantic models to dicts
    if "strategy_assignments" in update_dict:
        update_dict["strategy_assignments"] = [
            item.dict() if hasattr(item, "dict") else item
            for item in update_dict["strategy_assignments"]
        ]
    
    try:
        new_config = config_store.save(partial_update=update_dict)
        
        # Audit log
        audit_log.log(
            actor="admin" if authenticated else "unknown",
            action="update_config",
            status="success",
            details={"path": "/api/config", "method": "POST", "updated_keys": list(update_dict.keys())}
        )
        
        payload = {
            "status": "ok",
            "message": "Config updated successfully",
            "config": new_config.to_dict()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="config_store",
        )
    except ValueError as e:
        audit_log.log(
            actor="admin" if authenticated else "unknown",
            action="update_config",
            status="failure",
            details={"path": "/api/config", "method": "POST", "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config: {str(e)}"
        )
    except Exception as e:
        audit_log.log(
            actor="admin" if authenticated else "unknown",
            action="update_config",
            status="failure",
            details={"path": "/api/config", "method": "POST", "error": str(e)}
        )
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
    
    try:
        # Load current config to update it
        current = config_store.load()
        
        # If scope is specific account, update assignment
        # For simplicity in this version, we update global active_strategy_key
        # A more complex implementation would handle per-account assignments here
        
        update_payload = {"active_strategy_key": request.strategy_key}
        new_config = config_store.save(partial_update=update_payload)
        
        audit_log.log(
            actor="admin" if authenticated else "unknown",
            action="activate_strategy",
            status="success",
            details={"strategy": request.strategy_key, "scope": request.scope}
        )
        
        payload = {
            "ok": True,
            "active_strategy": new_config.active_strategy_key,
            "message": f"Strategy {request.strategy_key} activated"
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="config_store",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate strategy: {str(e)}")

# ============================================================================
# MARKET DATA ENDPOINTS (RESTORED for Verification)
# ============================================================================

@app.get("/api/market/prices")
async def get_market_prices(instruments: str = Query(..., description="Comma-separated instruments")):
    """Get latest prices for specific instruments (Verification API)"""
    from src.control_plane.market_data_provider import get_latest_price, MarketDataError
    
    inst_list = [i.strip() for i in instruments.split(",") if i.strip()]
    results = []
    
    for instrument in inst_list:
        try:
            price = get_latest_price(instrument, timeout_s=5.0, validate=False)
            from .market_data_provider import validate_price_integrity
            integrity = validate_price_integrity(price, source_path="api.get_market_prices")
            
            results.append({
                "instrument": instrument,
                "bid": price.bid,
                "ask": price.ask,
                "mid": price.mid,
                "ts_utc": price.ts_utc,
                "status": "ok",
                "integrity": {
                    "ok": integrity.ok,
                    "violation_code": integrity.violation_code,
                    "reason": integrity.reason
                }
            })
        except MarketDataError:
            results.append({
                "instrument": instrument,
                "status": "error",
                "error": "unavailable"
            })
        except Exception as e:
            results.append({
                "instrument": instrument,
                "status": "error",
                "error": str(e)
            })
            
    payload = {
        "ok": True,
        "prices": results,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="market_data_provider",
    )


def _normalize_chart_symbol(symbol: str) -> str:
    if not symbol:
        return ""
    sym = symbol.strip()
    if ":" in sym:
        sym = sym.split(":", 1)[1]
    sym = sym.upper()
    if "_" in sym:
        return sym
    if len(sym) == 6:
        return f"{sym[:3]}_{sym[3:]}"
    return sym


@app.get("/api/market/chart")
async def get_market_chart(
    instrument: str = Query(..., description="Instrument symbol (e.g. OANDA:XAUUSD)"),
    count: int = Query(60, ge=10, le=200),
    granularity: str = Query("M5")
):
    """Return lightweight SVG chart from real candles (truth-wrapped)."""
    from src.control_plane.market_data_provider import get_candles, MarketDataError

    inst = _normalize_chart_symbol(instrument)
    if not inst:
        payload = {"instrument": instrument, "svg": None, "points": 0}
        return _truth_wrap(payload, complete=False, source="market_data_provider", warnings=["Invalid instrument"])

    try:
        candles = get_candles(inst, granularity=granularity, count=count, timeout_s=10.0)
    except MarketDataError as e:
        payload = {"instrument": inst, "svg": None, "points": 0, "error": str(e)[:200]}
        return _truth_wrap(payload, complete=False, source="market_data_provider", warnings=["Market data unavailable"])
    except Exception as e:
        payload = {"instrument": inst, "svg": None, "points": 0, "error": str(e)[:200]}
        return _truth_wrap(payload, complete=False, source="market_data_provider", warnings=["Chart render failed"])

    closes = [c.c for c in candles if getattr(c, "c", None) is not None]
    if len(closes) < 2:
        payload = {"instrument": inst, "svg": None, "points": len(closes)}
        return _truth_wrap(payload, complete=False, source="market_data_provider", warnings=["Insufficient data"])

    width = 640
    height = 240
    pad = 10
    min_v = min(closes)
    max_v = max(closes)
    span = max_v - min_v if max_v != min_v else 1.0

    points = []
    for i, val in enumerate(closes):
        x = pad + (i / (len(closes) - 1)) * (width - pad * 2)
        y = pad + (1 - ((val - min_v) / span)) * (height - pad * 2)
        points.append(f"{x:.2f},{y:.2f}")

    svg = (
        f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' xmlns='http://www.w3.org/2000/svg'>"
        f"<rect width='{width}' height='{height}' fill='rgba(10,11,13,0.8)' />"
        f"<polyline fill='none' stroke='#00ff88' stroke-width='2' points='{' '.join(points)}' />"
        f"</svg>"
    )

    payload = {
        "instrument": inst,
        "svg": svg,
        "points": len(closes),
        "granularity": granularity,
    }
    return _truth_wrap(payload, complete=True, source="market_data_provider")


@app.get("/api/sidebar/live-prices")
async def get_sidebar_prices():
    """Get live prices for sidebar (Verification API)"""
    from src.control_plane.market_data_provider import get_latest_price, MarketDataError
    
    instruments = ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY"]
    prices = {}
    
    for instrument in instruments:
        try:
            price = get_latest_price(instrument, timeout_s=2.0)
            prices[instrument] = {
                "bid": price.bid,
                "ask": price.ask,
                "mid": price.mid,
                "change_pct": None
            }
        except Exception:
            pass
            
    payload = {
        "prices": prices,
        "warning": None if prices else "no_prices_available"
    }
    return _truth_wrap(
        payload,
        complete=bool(prices),
        source="market_data_provider",
        warnings=None if prices else ["no_prices_available"],
    )


# ============================================================================
# NEWS STATUS ENDPOINTS (RESTORED for Verification)
# ============================================================================

@app.get("/api/news/status")
async def get_news_status():
    """Get news provider status (Verification API)"""
    from src.core.settings import settings
    
    providers = {}
    if settings.marketaux_keys:
        providers["marketaux"] = "configured"
    if settings.finnhub_keys:
        providers["finnhub"] = "configured"
    if settings.polygon_keys:
        providers["polygon"] = "configured"
    if settings.newsapi_api_key:
        providers["newsapi"] = "configured"
        
    payload = {
        "ok": True,
        "providers": providers,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="news_provider",
    )


@app.get("/api/news/assess")
async def get_news_assess():
    """Assess news availability and provide AI-driven sentiment (Verification API)"""
    # Try snapshot first
    snapshot = status_snapshot.read()
    news_items = snapshot.get("recent_news", []) if snapshot else []
    
    # If no news in snapshot, fetch from provider (same as /api/news does)
    if not news_items:
        try:
            # Use the same logic as /api/news to get actual news
            news_items, _ = fetch_news_with_registry(
                query="forex OR currency OR central bank OR interest rate",
                threshold="medium",
                max_items=30
            )
        except Exception:
            news_items = []
    
    news_count = len(news_items)
    
    # Analyze sentiment and provide summary if news items exist
    summary = "No news items available for analysis."
    sentiment = "neutral"
    impact_score = 5
    
    if news_count > 0:
        # Simple heuristic analysis if real AI engine not connected
        # In production, this would call a real LLM/Sentiment engine
        bullish_keywords = ["surge", "up", "gain", "bullish", "recovery", "positive", "strong"]
        bearish_keywords = ["plunge", "down", "loss", "bearish", "crash", "negative", "weak"]
        
        bullish_count = 0
        bearish_count = 0
        
        all_text = " ".join([item.get("title", "") + " " + item.get("summary", "") for item in news_items]).lower()
        
        for word in bullish_keywords:
            bullish_count += all_text.count(word)
        for word in bearish_keywords:
            bearish_count += all_text.count(word)
            
        if bullish_count > bearish_count * 1.5:
            sentiment = "positive"
            impact_score = min(9, 5 + (bullish_count - bearish_count) // 2)
            summary = f"Aggregated sentiment is BULLISH based on {news_count} recent news items. Positive momentum detected in market discourse."
        elif bearish_count > bullish_count * 1.5:
            sentiment = "negative"
            impact_score = min(9, 5 + (bearish_count - bullish_count) // 2)
            summary = f"Aggregated sentiment is BEARISH based on {news_count} recent news items. Downward pressure noted in recent reports."
        else:
            sentiment = "neutral"
            impact_score = 5
            summary = f"Market sentiment remains NEUTRAL across {news_count} analyzed news items. No clear directional bias detected."
            
    payload = {
        "ok": True,
        "news_count": news_count,
        "summary": summary,
        "sentiment": sentiment,
        "impact_score": impact_score,
        "provider": "AI_QUANT_INTERNAL",
        "timestamp": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="news_provider",
    )

# ============================================================================
# DASHBOARD COMPATIBILITY ENDPOINTS (RESTORED)
# ============================================================================

@app.get("/api/accounts")
async def get_accounts():
    """Get accounts list (dashboard compatibility)"""
    snapshot = status_snapshot.read()
    config = config_store.load()
    
    if snapshot:
        accounts_data = snapshot.get("accounts", [])
        execution_capable = snapshot.get("accounts_execution_capable", 0)
    else:
        accounts_data = []
        execution_capable = 0
    
    payload = {
        "ok": True,
        "accounts": accounts_data,
        "execution_capable": execution_capable,
        "mode": snapshot.get("mode", "paper") if snapshot else "paper",
        "execution_enabled": snapshot.get("execution_enabled", False) if snapshot else False,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=bool(snapshot),
        source="status_snapshot",
        warnings=None if snapshot else ["No status snapshot available"],
    )


@app.get("/api/strategies/overview")
async def get_strategies_overview():
    """Get strategies overview (dashboard compatibility)"""
    config = config_store.load()
    snapshot = status_snapshot.read()
    
    active_key = snapshot.get("active_strategy_key", config.active_strategy_key) if snapshot else config.active_strategy_key
    strategies = get_strategy_registry()
    
    strategies_list = []
    for key, info in strategies.items():
        item_key = getattr(info, "key", None) or getattr(info, "strategy_key", None) or key
        name = getattr(info, "name", None) or getattr(info, "display_name", None) or str(item_key)
        description = getattr(info, "description", None) or ""
        instruments = getattr(info, "instruments", None) or []
        risk_level = getattr(info, "risk_level", None) or "unknown"
        session_preference = getattr(info, "session_preference", None) or "any"
        strategies_list.append({
            "key": item_key,
            "name": name,
            "description": description,
            "instruments": instruments,
            "risk_level": risk_level,
            "session_preference": session_preference,
            "active": item_key == active_key
        })
    
    payload = {
        "ok": True,
        "active_strategy": active_key,
        "strategies": strategies_list,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="strategy_registry",
    )


@app.get("/api/positions")
async def get_positions():
    """Get open positions (dashboard compatibility)"""
    snapshot = status_snapshot.read()
    positions = snapshot.get("positions", []) if snapshot else []
    
    payload = {
        "ok": True,
        "positions": positions,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=bool(snapshot),
        source="status_snapshot",
        warnings=None if snapshot else ["No status snapshot available"],
    )


@app.get("/api/signals/pending")
async def get_signals_pending():
    """Get pending signals (dashboard compatibility)"""
    snapshot = status_snapshot.read()
    config = config_store.load()
    
    if snapshot:
        signals = snapshot.get("recent_signals", [])
        active_strategy = snapshot.get("active_strategy_key", config.active_strategy_key)
        last_scan = snapshot.get("last_scan_iso")
    else:
        signals = []
        active_strategy = config.active_strategy_key
        last_scan = None
    
    payload = {
        "ok": True,
        "signals": signals,
        "active_strategy": active_strategy,
        "last_scan_utc": last_scan,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=bool(snapshot),
        source="status_snapshot",
        warnings=None if snapshot else ["No status snapshot available"],
        last_verified_at=last_scan,
        freshness_ms=_freshness_ms_from_timestamp_utc(last_scan),
    )


@app.get("/api/trade_selection/preview")
async def get_trade_selection_preview(
    limit: Optional[int] = Query(None, ge=1, le=50)
):
    """
    Preview current trade selection pool (what the system is 'thinking').

    Returns the top-N candidates from the runner's status snapshot, allowing
    callers to adjust `limit` up or down without changing execution behavior.
    """
    snapshot = status_snapshot.read(max_age_seconds=120)

    candidates: List[Dict[str, Any]] = []
    last_scan = None
    last_status_write_at = None

    if snapshot:
        raw_pool = snapshot.get("trade_selection_pool", []) or []

        # Optional per-request limit on top of runner-side limit
        if limit is not None:
            candidates = raw_pool[: limit]
        else:
            candidates = raw_pool

        last_scan = snapshot.get("last_scan_iso") or snapshot.get("last_scan_at")
        last_status_write_at = snapshot.get("last_status_write_at")

    payload = {
        "ok": bool(snapshot),
        "candidates": candidates,
        "count": len(candidates),
        "limit": limit,
        "ts_utc": time.time(),
    }

    last_verified = last_status_write_at or last_scan
    return _truth_wrap(
        payload,
        complete=bool(snapshot),
        source="status_snapshot",
        warnings=None if snapshot else ["No status snapshot available"],
        last_verified_at=last_verified,
        freshness_ms=_freshness_ms_from_timestamp_utc(last_verified) if last_verified else None,
    )


@app.get("/api/trades/pending")
async def get_trades_pending():
    """Get pending trades (dashboard compatibility)"""
    snapshot = status_snapshot.read()
    trades = snapshot.get("pending_trades", []) if snapshot else []
    
    payload = {
        "ok": True,
        "trades": trades,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=bool(snapshot),
        source="status_snapshot",
        warnings=None if snapshot else ["No status snapshot available"],
    )


@app.get("/api/journal/trades")
async def get_journal_trades(limit: int = 50, offset: int = 0):
    """Get executed trades from ledger (journal)"""
    ledger = get_trade_ledger()
    trades = ledger.read_trades(limit=limit, offset=offset)
    total_count = ledger.count_trades()
    
    payload = {
        "ok": True,
        "trades": trades,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=trades is not None,
        source="trade_ledger",
    )


@app.get("/api/journal/trades/export")
async def export_journal_trades():
    """Export journal trades as server-generated CSV (truth-wrapped)."""
    ledger = get_trade_ledger()
    trades = ledger.read_trades(limit=10000, offset=0)
    csv_text = _csv_from_rows(trades)
    payload = {
        "filename": "journal_trades.csv",
        "csv": csv_text,
        "count": len(trades),
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="trade_ledger",
    )


@app.get("/api/performance/summary")
async def get_performance_summary(days: int = 30):
    """Get performance summary computed from trade ledger"""
    ledger = get_trade_ledger()
    all_trades = ledger.read_trades(limit=10000, offset=0)
    
    # Simple metrics calculation
    closed_trades = [t for t in all_trades if t.get("status") == "closed" and t.get("pnl") is not None]
    
    if not closed_trades:
        payload = {
            "ok": True,
            "status": "NO_DATA",
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0.0,
            "note": "No closed trades found in ledger.",
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="trade_ledger",
        )
        
    winning_trades = [t for t in closed_trades if float(t.get("pnl", 0)) > 0]
    total_pnl = sum(float(t.get("pnl", 0)) for t in closed_trades)
    
    payload = {
        "ok": True,
        "status": "OK",
        "total_trades": len(closed_trades),
        "win_rate": len(winning_trades) / len(closed_trades) if closed_trades else 0,
        "total_pnl": round(total_pnl, 2),
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="trade_ledger",
    )


def calculate_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics from a list of trades"""
    if not trades:
        return {
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0
        }
    
    # Filter for closed trades with PnL
    valid_trades = [t for t in trades if t.get("pnl") is not None]
    if not valid_trades:
        return calculate_metrics([])
        
    wins = [float(t.get("pnl", 0)) for t in valid_trades if float(t.get("pnl", 0)) > 0]
    losses = [float(t.get("pnl", 0)) for t in valid_trades if float(t.get("pnl", 0)) <= 0]
    pnl_sequence = [float(t.get("pnl", 0)) for t in valid_trades]
    
    total_pnl = sum(pnl_sequence)
    total_trades = len(valid_trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
    
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    
    import statistics
    stdev = statistics.stdev(pnl_sequence) if len(pnl_sequence) > 1 else 0
    sharpe = (sum(pnl_sequence) / len(pnl_sequence)) / stdev if stdev > 0 else 0
    
    max_dd = 0.0
    peak = -999999999.0
    running_pnl = 0.0
    equity = [0.0]
    for pnl in pnl_sequence:
        equity.append(equity[-1] + pnl)
    
    peak = equity[0]
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            
    return {
        "total_trades": total_trades,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2)
    }


@app.get("/api/performance/strategies")
async def get_performance_strategies(days: int = 30):
    """Get performance metrics grouped by strategy"""
    ledger = get_trade_ledger()
    all_trades = ledger.read_trades(limit=10000)
    
    strategies = {}
    for t in all_trades:
        key = t.get("strategy_key") or t.get("strategy") or "unknown"
        if key not in strategies:
            strategies[key] = []
        strategies[key].append(t)
        
    results = []
    for key, trades in strategies.items():
        metrics = calculate_metrics(trades)
        metrics["strategy_key"] = key
        results.append(metrics)
        
    payload = {"ok": True, "strategies": results, "ts_utc": time.time()}
    return _truth_wrap(
        payload,
        complete=True,
        source="trade_ledger",
    )


@app.get("/api/performance/accounts")
async def get_performance_accounts(days: int = 30):
    """Get performance metrics grouped by account"""
    ledger = get_trade_ledger()
    all_trades = ledger.read_trades(limit=10000)
    
    accounts = {}
    for t in all_trades:
        key = t.get("account_id_redacted") or t.get("account_id") or "unknown"
        if key not in accounts:
            accounts[key] = []
        accounts[key].append(t)
        
    results = []
    for key, trades in accounts.items():
        metrics = calculate_metrics(trades)
        metrics["account_id"] = key
        results.append(metrics)
        
    payload = {"ok": True, "accounts": results, "ts_utc": time.time()}
    return _truth_wrap(
        payload,
        complete=True,
        source="trade_ledger",
    )


@app.get("/api/performance/ai-evaluation")
async def get_performance_ai_eval(days: int = 30):
    """Get AI evaluation of performance based on ledger data"""
    ledger = get_trade_ledger()
    all_trades = ledger.read_trades(limit=1000)
    closed_trades = [t for t in all_trades if t.get("status") == "closed"]
    
    if not closed_trades:
        payload = {
            "ok": True,
            "status": "NO_DATA",
            "summary": "AI evaluation requires at least 5 executed trades to generate meaningful insights.",
            "recommendation": "CONTINUE_MONITORING",
            "best_strategy": None,
            "best_account": None,
            "evaluations": [],
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="trade_ledger",
        )

    def _score_metrics(metrics: Dict[str, Any]) -> int:
        """Compute a 0-100 score from real metrics"""
        win_rate = max(0.0, min(1.0, float(metrics.get("win_rate", 0.0))))
        profit_factor = max(0.0, min(3.0, float(metrics.get("profit_factor", 0.0))))
        sharpe = max(0.0, min(3.0, float(metrics.get("sharpe_ratio", 0.0))))
        # Weighted score: win_rate 50%, profit_factor 25%, sharpe 25%
        score = (win_rate * 50.0) + ((profit_factor / 3.0) * 25.0) + ((sharpe / 3.0) * 25.0)
        return int(round(max(0.0, min(100.0, score))))

    def _recommendation(score: int) -> str:
        if score >= 75:
            return "SCALE_UP"
        if score >= 55:
            return "MAINTAIN"
        if score >= 35:
            return "MONITOR"
        return "DECREASE"

    def _reasons(metrics: Dict[str, Any]) -> List[str]:
        return [
            f"Win rate {metrics.get('win_rate', 0.0) * 100:.1f}%",
            f"Profit factor {metrics.get('profit_factor', 0.0):.2f}",
            f"Sharpe {metrics.get('sharpe_ratio', 0.0):.2f}",
        ]

    # Group trades by strategy and account using real metrics
    strategies: Dict[str, List[Dict[str, Any]]] = {}
    accounts: Dict[str, List[Dict[str, Any]]] = {}
    for t in closed_trades:
        strat_key = t.get("strategy_key") or t.get("strategy") or "unknown"
        acc_key = t.get("account_id_redacted") or t.get("account_id") or "unknown"
        strategies.setdefault(strat_key, []).append(t)
        accounts.setdefault(acc_key, []).append(t)

    evaluations: List[Dict[str, Any]] = []

    def _build_evals(grouped: Dict[str, List[Dict[str, Any]]], group_type: str) -> List[Dict[str, Any]]:
        out = []
        for key, trades in grouped.items():
            metrics = calculate_metrics(trades)
            score = _score_metrics(metrics)
            out.append({
                "type": group_type,
                "identifier": key,
                "score": score,
                "recommendation": _recommendation(score),
                "reasons": _reasons(metrics),
            })
        return out

    evaluations.extend(_build_evals(strategies, "strategy"))
    evaluations.extend(_build_evals(accounts, "account"))

    # Determine best strategy/account by score (fallback to total_pnl if tied)
    best_strategy = None
    best_account = None
    if strategies:
        strategy_evals = [e for e in evaluations if e["type"] == "strategy"]
        best_strategy = sorted(strategy_evals, key=lambda e: (e["score"], e["identifier"]), reverse=True)[0] if strategy_evals else None
    if accounts:
        account_evals = [e for e in evaluations if e["type"] == "account"]
        best_account = sorted(account_evals, key=lambda e: (e["score"], e["identifier"]), reverse=True)[0] if account_evals else None

    payload = {
        "ok": True,
        "status": "COMPUTED",
        "summary": f"Computed evaluation from {len(closed_trades)} closed trades.",
        "best_strategy": best_strategy,
        "best_account": best_account,
        "evaluations": evaluations,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="trade_ledger",
    )


@app.get("/api/news")
async def get_news():
    """Get news feed (dashboard compatibility)"""
    global _news_cache_ts, _news_cache, _news_cache_status
    snapshot = status_snapshot.read()
    news_items = snapshot.get("recent_news", []) if snapshot else []
    if news_items:
        payload = {
            "ok": True,
            "news": news_items,
            "source_mode": "snapshot",
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="status_snapshot",
        )

    # Fallback to live provider registry (real data only).
    now_ts = time.time()
    if _news_cache and (now_ts - _news_cache_ts) < NEWS_CACHE_TTL:
        payload = {
            "ok": True,
            "news": _news_cache,
            "provider_status": _news_cache_status,
            "source_mode": "provider_registry_cached",
            "ts_utc": now_ts
        }
        warnings = []
        if _news_cache_status.get("reason"):
            warnings.append(_news_cache_status["reason"])
        return _truth_wrap(
            payload,
            complete=bool(_news_cache),
            source="news_provider",
            warnings=warnings or None,
        )
    def _is_forex_relevant(item: Dict[str, Any]) -> bool:
        import re
        title = (item.get("title") or "").lower()
        summary = (item.get("summary") or "").lower()
        text = f"{title} {summary}"
        if re.search(r"\b(forex|fx|currency)\b", text):
            return True
        if re.search(r"\b(usd|eur|gbp|jpy|aud|cad|nzd|xau|xag)\b", text):
            return True
        if re.search(r"\bxau\b", text) or re.search(r"\bxag\b", text):
            return True
        if re.search(r"\bgold\b", text) and re.search(r"\b(price|prices|bullion|spot|ounce|oz|metal|precious|xau)\b", text):
            return True
        if re.search(r"\bsilver\b", text) and re.search(r"\b(price|prices|bullion|spot|ounce|oz|metal|precious|xag)\b", text):
            return True
        if re.search(r"\b(central bank|rate decision|interest rate|fomc|federal reserve|fed|ecb|boe|boj|rba|boc|snb|bank of england|bank of japan|bank of canada|reserve bank)\b", text):
            return True
        symbols = [str(s).upper() for s in (item.get("symbols") or [])]
        return any(s in {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "XAU", "XAG"} for s in symbols)

    query = "forex OR FX OR currency OR USD OR EUR OR GBP OR JPY OR XAU OR gold OR central bank OR rate decision OR inflation OR CPI OR jobs report OR NFP"
    news_items, provider_status = fetch_news_with_registry(query=query, threshold="medium", max_items=30)
    filtered_items = [item for item in news_items if _is_forex_relevant(item)]
    if filtered_items:
        news_items = filtered_items
    else:
        provider_status["filtered_out"] = len(news_items)
        if news_items:
            provider_status["reason"] = "no_forex_news_after_filter"
        news_items = []
    warnings = []
    if not news_items and NewsManager is not None:
        try:
            manager = NewsManager()
            if manager.is_enabled():
                now = datetime.utcnow()
                events = manager.get_upcoming_high_impact(within_minutes=240)
                calendar_items = []
                for event in events:
                    minutes = max(0, int((event.time_utc - now).total_seconds() // 60))
                    title = f"{event.currency} {event.title} in {minutes}m"
                    summary = f"Impact: {event.impact} | Forecast: {event.forecast} | Actual: {event.actual}"
                    calendar_items.append({
                        "id": f"cal-{event.currency}-{int(event.time_utc.timestamp())}",
                        "ts_utc": event.time_utc.timestamp(),
                        "source": "economic_calendar",
                        "title": title,
                        "url": "",
                        "summary": summary,
                        "symbols": [event.currency],
                        "impact": event.impact or "high",
                    })
                if calendar_items:
                    news_items = calendar_items
                    provider_status["calendar_used"] = True
                    provider_status.pop("reason", None)
        except Exception:
            pass

    if provider_status.get("reason"):
        warnings.append(provider_status["reason"])
    payload = {
        "ok": True,
        "news": news_items,
        "provider_status": provider_status,
        "source_mode": "provider_registry",
        "ts_utc": now_ts
    }
    _news_cache.clear()
    _news_cache.extend(news_items)
    _news_cache_status.clear()
    _news_cache_status.update(provider_status)
    _news_cache_ts = now_ts
    return _truth_wrap(
        payload,
        complete=bool(news_items),
        source="news_provider",
        warnings=warnings or None,
    )


@app.get("/api/economic_calendar")
async def get_economic_calendar():
    """Get upcoming economic calendar events (dashboard compatibility)"""
    config = config_store.load()
    if not config.news_integration_enabled:
        return _truth_wrap(
            {"ok": True, "events": [], "reason": "news_integration_disabled"},
            complete=False,
            source="config_store",
            warnings=["News integration is disabled in config"],
        )

    if NewsManager is None:
        return _truth_wrap(
            {"ok": True, "events": [], "reason": "news_manager_unavailable"},
            complete=False,
            source="news_provider",
            warnings=["NewsManager not available"],
        )

    manager = NewsManager()
    if not manager.is_enabled():
        return _truth_wrap(
            {"ok": True, "events": [], "reason": "no_calendar_api_keys"},
            complete=False,
            source="news_provider",
            warnings=["No TradingEconomics or Finnhub API keys configured for calendar"],
        )

    now = datetime.utcnow()
    events = manager.get_upcoming_high_impact(within_minutes=240)
    formatted_events = []
    for event in events:
        formatted_events.append({
            "time_utc": event.time_utc.isoformat() + "Z",
            "country": event.country,
            "title": event.title,
            "impact": event.impact,
            "currency": event.currency,
            "forecast": event.forecast,
            "actual": event.actual,
            "countdown_seconds": int((event.time_utc - now).total_seconds())
        })

    payload = {
        "ok": True,
        "events": formatted_events,
        "ts_utc": time.time()
    }
    return _truth_wrap(
        payload,
        complete=True,
        source="news_provider",
    )

# ============================================================================
# SESSION REGIME GATE ENDPOINTS (Read-Only Observability)
# ============================================================================

@app.get("/api/session-regime-gate/decisions")
async def get_session_regime_gate_decisions(limit: int = Query(100, ge=1, le=1000)):
    """Get recent session regime gate decisions (read-only)"""
    try:
        from src.dashboard.panels.session_regime_gate_panel import load_recent_gate_events
        events = load_recent_gate_events(limit=limit)
        payload = {
            "ok": True,
            "decisions": events,
            "count": len(events),
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=bool(events),
            source="session_regime_gate_panel",
        )
    except Exception as e:
        return _truth_wrap(
            {"ok": False, "decisions": [], "error": str(e)[:200]},
            complete=False,
            source="session_regime_gate_panel",
            warnings=[f"Error loading gate decisions: {str(e)[:200]}"],
        )


@app.get("/api/session-regime-gate/statistics")
async def get_session_regime_gate_statistics():
    """Get session regime gate statistics (read-only)"""
    try:
        from src.dashboard.panels.session_regime_gate_panel import get_gate_statistics
        stats = get_gate_statistics()
        payload = {
            "ok": True,
            "statistics": stats,
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="session_regime_gate_panel",
        )
    except Exception as e:
        return _truth_wrap(
            {"ok": False, "statistics": {}, "error": str(e)[:200]},
            complete=False,
            source="session_regime_gate_panel",
            warnings=[f"Error loading gate statistics: {str(e)[:200]}"],
        )


@app.get("/api/session-regime-gate/snapshot")
async def get_session_regime_gate_snapshot():
    """Get current session/regime snapshot (read-only)"""
    from datetime import datetime, timezone
    from src.dashboard.panels.session_regime_gate_panel import load_recent_gate_events
    
    try:
        # Get most recent decision for current state
        events = load_recent_gate_events(limit=1)
        current_time = datetime.now(timezone.utc)
        
        # Classify current session
        h = current_time.hour
        if h >= 22 or h < 6:
            current_session = "asia"
        elif 6 <= h < 12:
            current_session = "london"
        elif 12 <= h < 16:
            current_session = "london_ny_overlap"
        elif 16 <= h < 21:
            current_session = "new_york"
        else:
            current_session = "transition"
        
        # Get last known regime and policy key from most recent event
        last_event = events[0] if events else None
        last_regime = last_event.get("regime", "UNKNOWN") if last_event else "UNKNOWN"
        last_policy_key = None
        if last_event:
            session = last_event.get("session", "unknown")
            regime = last_event.get("regime", "UNKNOWN")
            news_state = last_event.get("news_state", "normal")
            bias_alignment = "aligned" if last_event.get("roadmap_aligned", False) else "misaligned"
            last_policy_key = f"{session}|{regime}|{news_state}|{bias_alignment}"
        
        payload = {
            "ok": True,
            "current_session": current_session,
            "current_time_utc": current_time.isoformat(),
            "last_known_regime": last_regime,
            "last_policy_key": last_policy_key,
            "ts_utc": time.time()
        }
        return _truth_wrap(
            payload,
            complete=True,
            source="session_regime_gate_panel",
        )
    except Exception as e:
        return _truth_wrap(
            {"ok": False, "error": str(e)[:200]},
            complete=False,
            source="session_regime_gate_panel",
            warnings=[f"Error loading gate snapshot: {str(e)[:200]}"],
        )


def run():
    """Run the API server"""
    import uvicorn
    print(f"🚀 AI_QUANT Control Plane starting on http://{BIND_HOST}:{BIND_PORT}")
    print(f"   Dashboard: http://{BIND_HOST}:{BIND_PORT}/")
    print(f"   API Docs: http://{BIND_HOST}:{BIND_PORT}/docs")
    if CONTROL_PLANE_TOKEN:
        print(f"   Auth: Bearer token required for POST endpoints")
    else:
        print(f"   ⚠️  Warning: No CONTROL_PLANE_TOKEN set - authentication disabled")
    
    uvicorn.run(
        app,
        host=BIND_HOST,
        port=BIND_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    run()
