"""Pydantic models for Windows Sidecar API responses."""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

BRIDGE_ID = "parallel_windows_sidecar_bridge_v1"


def ts_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthResponse(BaseModel):
    service_up: bool = True
    ts_utc: str = Field(default_factory=ts_utc)
    version: str = "1.0.0"
    terminal_connected: bool = False
    account_connected: bool = False
    degraded: bool = False
    failure_bucket: Optional[str] = None
    recommended_fix: Optional[str] = None
    bridge_id: str = BRIDGE_ID


class DiagnosticsResponse(BaseModel):
    service_status: str = "unknown"
    python_process_ok: bool = True
    mt5_initialize_ok: bool = False
    terminal_detected: bool = False
    login_state: str = "unknown"
    account_info_available: bool = False
    last_error_code: Optional[int] = None
    last_error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    failure_bucket: Optional[str] = None
    recommended_fix: Optional[str] = None
    bridge_id: str = BRIDGE_ID
    ts_utc: str = Field(default_factory=ts_utc)


class AccountResponse(BaseModel):
    login: int = 0
    server: str = ""
    company: str = ""
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    margin_free: float = 0.0
    margin_level: float = 0.0
    profit: float = 0.0
    currency: str = ""
    leverage: int = 0
    trade_allowed: bool = False
    trade_expert: bool = False
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID


class PositionsResponse(BaseModel):
    count: int = 0
    positions: list[dict[str, Any]] = Field(default_factory=list)
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID


class OrdersResponse(BaseModel):
    count: int = 0
    orders: list[dict[str, Any]] = Field(default_factory=list)
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID


class TickResponse(BaseModel):
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    spread_points: int = 0
    spread_price: float = 0.0
    tick_time: Optional[str] = None
    tick_age_ms: Optional[int] = None
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID
    failure_bucket: Optional[str] = None
    recommended_fix: Optional[str] = None
    broker_symbol_actual: Optional[str] = None  # When symbol_name_mismatch, the broker's actual symbol


class SymbolSpecResponse(BaseModel):
    symbol: str = ""
    digits: int = 0
    point: float = 0.0
    trade_contract_size: int = 0
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0
    trade_stops_level: int = 0
    trade_freeze_level: int = 0
    execution_mode: int = 0
    currency_base: str = ""
    currency_profit: str = ""
    currency_margin: str = ""
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID


class SymbolsOverviewRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])


class SymbolsOverviewResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    ts_utc: str = Field(default_factory=ts_utc)
    bridge_id: str = BRIDGE_ID
