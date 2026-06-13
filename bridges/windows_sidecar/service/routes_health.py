"""Health and diagnostics routes."""
from fastapi import APIRouter, Depends
from .auth import require_api_key
from .models import HealthResponse
from .diagnostics import run_diagnostics

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(dep: str = Depends(require_api_key)):
    """Health check - returns service and MT5 connection state."""
    diag = run_diagnostics()
    return HealthResponse(
        service_up=True,
        terminal_connected=diag["mt5_initialize_ok"],
        account_connected=diag["account_info_available"],
        degraded=not diag["account_info_available"] and diag["mt5_initialize_ok"],
        failure_bucket=diag.get("failure_bucket"),
        recommended_fix=diag.get("recommended_fix"),
    )


@router.get("/diagnostics")
async def diagnostics(dep: str = Depends(require_api_key)):
    """Full diagnostics."""
    return run_diagnostics()
