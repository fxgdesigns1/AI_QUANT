"""Contract tests for Windows Sidecar API (parallel_windows_sidecar_bridge_v1)."""
import pytest

BRIDGE_ID = "parallel_windows_sidecar_bridge_v1"


def test_bridge_id_constant():
    assert BRIDGE_ID == "parallel_windows_sidecar_bridge_v1"


def test_forbidden_names_not_used():
    forbidden = ["bridge_v2", "new_bridge_final", "tmp_bridge", "mt5_bridge_fixed", "generic_mt5_bridge", "main_bridge_replacement"]
    assert BRIDGE_ID not in forbidden


def test_health_response_shape():
    """Health response must include bridge_id, ts_utc, service_up, etc."""
    from bridges.windows_sidecar.service.models import HealthResponse
    r = HealthResponse()
    assert hasattr(r, "bridge_id")
    assert r.bridge_id == BRIDGE_ID
    assert hasattr(r, "ts_utc")
    assert hasattr(r, "service_up")
    assert hasattr(r, "terminal_connected")
    assert hasattr(r, "account_connected")
    assert hasattr(r, "degraded")
    assert hasattr(r, "failure_bucket")
    assert hasattr(r, "recommended_fix")


def test_diagnostics_response_shape():
    """Diagnostics response must include bridge_id, failure_bucket, recommended_fix."""
    from bridges.windows_sidecar.service.models import DiagnosticsResponse
    # DiagnosticsResponse is used in diagnostics module, not as pydantic model directly
    from bridges.windows_sidecar.service.diagnostics import run_diagnostics
    diag = run_diagnostics()
    assert "bridge_id" in diag
    assert diag["bridge_id"] == BRIDGE_ID
    assert "failure_bucket" in diag
    assert "recommended_fix" in diag
    assert "ts_utc" in diag


def test_failure_buckets_include_symbol_types():
    """Tick failures must be classifiable: symbol_not_selected, symbol_name_mismatch, no_tick_data."""
    from bridges.windows_sidecar.service.diagnostics import FAILURE_BUCKETS
    required = ["symbol_not_selected", "symbol_name_mismatch", "symbol_not_found", "no_tick_data"]
    for b in required:
        assert b in FAILURE_BUCKETS, f"FAILURE_BUCKETS must include {b}"


def test_tick_response_has_broker_symbol_actual():
    """TickResponse supports broker_symbol_actual for symbol_name_mismatch."""
    from bridges.windows_sidecar.service.models import TickResponse
    r = TickResponse(symbol="EURUSD", failure_bucket="symbol_name_mismatch", broker_symbol_actual="EURUSDm")
    assert r.broker_symbol_actual == "EURUSDm"


def test_no_write_routes():
    """Verify no write endpoints in scope."""
    from bridges.windows_sidecar.service.main import app
    paths = []
    for r in app.routes:
        if hasattr(r, "path") and r.path:
            paths.append(r.path)
        if hasattr(r, "routes"):
            for sr in r.routes:
                if hasattr(sr, "path"):
                    paths.append((getattr(r, "path", "") or "") + sr.path)
    forbidden_paths = ["/orders/send", "/orders/preview", "/positions/close"]
    for p in forbidden_paths:
        found = any(p in str(path) for path in paths)
        assert not found, f"Write route {p} must not exist"
