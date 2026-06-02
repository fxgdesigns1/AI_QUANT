#!/usr/bin/env python3
"""Mock API server for safe dashboard development without live VM
Provides all dashboard API endpoints with realistic mock data
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime, timezone
import json
import random

app = FastAPI(
    title="AI_QUANT Control Plane (MOCK)",
    description="Mock API for dashboard development",
    version="1.0.0-MOCK"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if dashboard directory exists
dashboard_path = Path(__file__).parent.parent / "dashboard"
if dashboard_path.exists():
    app.mount("/static", StaticFiles(directory=str(dashboard_path)), name="static")

# Mock data generators
def mock_status():
    return {
        "data": {
            "runner_state": "running",
            "last_heartbeat_ts": datetime.now(timezone.utc).isoformat(),
            "accounts": [
                {"account_id": "001", "strategy_key": "session_regime_aligned", "mode": "paper", "execution_enabled": True},
                {"account_id": "002", "strategy_key": "momentum_trading", "mode": "paper", "execution_enabled": False},
            ],
            "strategies": [
                {"key": "session_regime_aligned", "active_accounts": 1, "instruments": ["EUR_USD", "GBP_USD"]},
                {"key": "momentum_trading", "active_accounts": 0, "instruments": ["XAU_USD"]},
            ],
        },
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

def mock_market_overview():
    instruments = ["EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD"]
    return {
        "data": [
            {
                "instrument": inst,
                "bid": round(random.uniform(1.0, 2.0), 5),
                "ask": round(random.uniform(1.0, 2.0), 5),
                "mid": round(random.uniform(1.0, 2.0), 5),
                "spread": round(random.uniform(0.0001, 0.001), 5),
                "change_pct": round(random.uniform(-1.0, 1.0), 2),
                "session": random.choice(["Asian", "European", "US"]),
            }
            for inst in instruments
        ],
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

def mock_news():
    return {
        "data": [
            {
                "source": "ForexFactory",
                "title": "ECB Interest Rate Decision",
                "impact": "High",
                "category": "Central Banks",
                "symbol": "EUR_USD",
                "ts_utc": datetime.now(timezone.utc).isoformat(),
            },
            {
                "source": "TradingView",
                "title": "USD Strengthens on Employment Data",
                "impact": "Medium",
                "category": "Economic",
                "symbol": "USD",
                "ts_utc": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

def mock_active_trades():
    return {
        "data": [
            {
                "id": "trade_001",
                "account_id": "001",
                "instrument": "EUR_USD",
                "side": "buy",
                "size": 1000,
                "entry_price": 1.08500,
                "sl": 1.08000,
                "tp": 1.09000,
                "unrealized_pnl": 25.50,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

def mock_strategies():
    return {
        "data": [
            {
                "key": "session_regime_aligned",
                "name": "Session Regime Aligned",
                "description": "Aligns trades with market sessions and regime",
                "default_instruments": ["EUR_USD", "GBP_USD"],
                "risk_profile": "moderate",
            },
            {
                "key": "momentum_trading",
                "name": "Momentum Trading",
                "description": "Captures momentum in trending markets",
                "default_instruments": ["XAU_USD"],
                "risk_profile": "high",
            },
        ],
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

# API Endpoints (mirroring real API structure)
@app.get("/health")
async def health():
    return {"status": "ok", "mode": "MOCK", "ts_utc": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
async def status():
    return mock_status()

@app.get("/api/truth/status")
async def truth_status():
    return mock_status()

@app.get("/api/market/overview")
async def market_overview():
    return mock_market_overview()

@app.get("/api/news")
async def news():
    return mock_news()

@app.get("/api/trades/active")
async def active_trades():
    return mock_active_trades()

@app.get("/api/strategies")
async def strategies():
    return mock_strategies()

@app.get("/api/strategies/overview")
async def strategies_overview():
    return {"data": {"strategies": mock_strategies()["data"]}, "complete": True}

@app.get("/api/accounts")
async def accounts():
    status_data = mock_status()["data"]
    return {
        "data": {
            "accounts": status_data["accounts"],
            "execution_capable": sum(1 for acc in status_data["accounts"] if acc.get("execution_enabled")),
        },
        "complete": True,
    }

@app.get("/api/performance/summary")
async def performance_summary():
    return {
        "data": {
            "equity_curve": [10000, 10100, 10200, 10150, 10250],
            "max_drawdown": -1.5,
            "win_rate": 0.65,
            "sharpe": 1.2,
            "trade_count": 150,
        },
        "complete": True,
    }

@app.get("/api/ui/version")
async def ui_version():
    return {
        "version": "1.0.0-MOCK",
        "build": "dev",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

# Serve dashboard from templates (if it exists)
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    template_path = Path(__file__).parent.parent / "templates" / "forensic_command.html"
    if template_path.exists():
        return HTMLResponse(template_path.read_text(), headers={"Cache-Control": "no-store"})
    return HTMLResponse("""
    <html>
        <head><title>AI_QUANT Control Plane (MOCK)</title></head>
        <body>
            <h1>AI_QUANT Control Plane API (MOCK MODE)</h1>
            <p>Mock API server for dashboard development</p>
            <p>API docs: <a href="/docs">/docs</a></p>
            <p>Try: <a href="/api/status">/api/status</a></p>
        </body>
    </html>
    """, headers={"Cache-Control": "no-store"})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MOCK API server on http://127.0.0.1:8787")
    print("   Use this for safe dashboard development without live VM")
    print("   Press Ctrl+C to stop")
    uvicorn.run(app, host="127.0.0.1", port=8787)
