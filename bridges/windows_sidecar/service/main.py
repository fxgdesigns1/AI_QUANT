"""Windows Sidecar Bridge - parallel_windows_sidecar_bridge_v1.
FastAPI service: telemetry routes require API key; /control requires API key and write gate.
"""
import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from .config import (
    BRIDGE_ID,
    BIND_HOST,
    BIND_PORT,
    SIDECAR_API_KEY,
    SIDECAR_ENABLE_WRITE_ACTIONS,
)
from .routes_health import router as health_router
from .routes_account import router as account_router
from .routes_positions import router as positions_router
from .routes_orders import router as orders_router
from .routes_symbols import router as symbols_router
from .routes_history import router as history_router
from .routes_control import router as control_router

if not SIDECAR_API_KEY:
    raise ValueError("SIDECAR_API_KEY is required. Set in .env or environment.")

app = FastAPI(
    title="Windows Sidecar Bridge",
    description=(
        f"MT5 API ({BRIDGE_ID}). Telemetry routes always require API key; "
        "/control routes additionally require SIDECAR_ENABLE_WRITE_ACTIONS=true."
    ),
    version="1.0.0",
)

app.include_router(health_router, tags=["health"])
app.include_router(account_router, tags=["account"])
app.include_router(positions_router, tags=["positions"])
app.include_router(orders_router, tags=["orders"])
app.include_router(symbols_router, tags=["symbols"])
app.include_router(history_router, tags=["history"])
app.include_router(control_router)


@app.get("/")
async def root():
    return {
        "service": "windows_sidecar",
        "bridge_id": BRIDGE_ID,
        "read_only": not SIDECAR_ENABLE_WRITE_ACTIONS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bridges.windows_sidecar.service.main:app",
        host=BIND_HOST,
        port=BIND_PORT,
        reload=False,
    )
