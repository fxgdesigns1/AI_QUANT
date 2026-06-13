"""Diagnostics for Windows Sidecar bridge state."""
import time
from typing import Optional
from .mt5_client import initialize_mt5, account_info, get_mt5, last_error
from .config import MT5_TERMINAL_PATH, BRIDGE_ID

FAILURE_BUCKETS = [
    "sidecar_unreachable",
    "terminal_not_running",
    "mt5_initialize_failed",
    "account_not_logged_in",
    "account_info_unavailable",
    "symbol_not_selected",
    "symbol_not_found",
    "symbol_name_mismatch",
    "no_tick_data",
    "tick_stale",
    "history_unavailable",
    "write_guard_blocked",
    "broker_reject",
    "unknown_fail",
]


def run_diagnostics() -> dict:
    """Run full diagnostics and return structured result."""
    from .models import ts_utc
    start = time.perf_counter()
    result = {
        "service_status": "ok",
        "python_process_ok": True,
        "mt5_initialize_ok": False,
        "terminal_detected": bool(MT5_TERMINAL_PATH),
        "login_state": "unknown",
        "account_info_available": False,
        "last_error_code": None,
        "last_error_message": None,
        "latency_ms": None,
        "failure_bucket": None,
        "recommended_fix": None,
        "bridge_id": BRIDGE_ID,
        "ts_utc": ts_utc(),
    }

    if not MT5_TERMINAL_PATH:
        result["failure_bucket"] = "terminal_not_running"
        result["recommended_fix"] = "Set MT5_TERMINAL_PATH to MT5 terminal executable path"
        result["latency_ms"] = (time.perf_counter() - start) * 1000
        return result

    ok, err_code, err_msg = initialize_mt5()
    result["mt5_initialize_ok"] = ok
    result["last_error_code"] = err_code
    result["last_error_message"] = err_msg

    if not ok:
        result["failure_bucket"] = "mt5_initialize_failed"
        result["recommended_fix"] = err_msg or "Check MT5 terminal path and login"
        result["latency_ms"] = (time.perf_counter() - start) * 1000
        return result

    acc = account_info()
    if not acc:
        err = last_error()
        result["failure_bucket"] = "account_info_unavailable"
        result["recommended_fix"] = err[1] or "Ensure MT5 is logged in"
        result["login_state"] = "not_logged_in"
        result["latency_ms"] = (time.perf_counter() - start) * 1000
        return result

    result["account_info_available"] = True
    result["login_state"] = "logged_in"
    result["latency_ms"] = (time.perf_counter() - start) * 1000
    return result
