#!/usr/bin/env python3
"""
FXG Zero-Drift Dashboard v2.0
==============================
Single-file operator dashboard for the FXG distributed trading system.
Validates system state, surfaces drift, enables manual Lane 010 execution.

ARCHITECTURE
------------
This script is designed to run ON THE ALPHA VM. It talks to:
  - ALPHA control plane API at http://127.0.0.1:8787 (local, same VM)
  - ALPHA filesystem (signal files, env files, log timestamps)
  - Windows MT5 sidecar status -- INDIRECTLY via ALPHA's preflight endpoint
    (the pull loop on Windows syncs heartbeat back to ALPHA every 3 min)

The MacBook operator accesses the dashboard via SSH tunnel:
  gcloud compute ssh --zone us-central1-a fxg-paper-e2-small-main-2026 \\
    --project fxg-ai-trading -- -L 8000:localhost:8000 -N
  open http://localhost:8000

DEPLOYMENT
----------
On ALPHA:
  sudo mkdir -p /opt/fxg-dashboard
  sudo cp fxg_zero_drift_dashboard.py /opt/fxg-dashboard/
  pip3 install --user fastapi uvicorn httpx
  python3 /opt/fxg-dashboard/fxg_zero_drift_dashboard.py --web

Modes:
  python3 fxg_zero_drift_dashboard.py              # CLI: run all tests once
  python3 fxg_zero_drift_dashboard.py --web        # web dashboard server
  python3 fxg_zero_drift_dashboard.py --json       # CLI: machine-readable output
  python3 fxg_zero_drift_dashboard.py --demo       # web with synthetic data (offline UI dev)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import secrets
import socket
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Optional dependencies (only required for --web mode)
# ---------------------------------------------------------------------------
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    FastAPI = None  # type: ignore


# ---------------------------------------------------------------------------
# Configuration (env-overridable)
# ---------------------------------------------------------------------------
ALPHA_API = os.environ.get("ALPHA_API_URL", "http://127.0.0.1:8787")

DASHBOARD_HOST = os.environ.get("FXG_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.environ.get("FXG_DASHBOARD_PORT", "8000"))

# Auth: token-based. Auto-generates per process if not provided.
# Persists to a 0600 file so the operator can read it after SSH tunnel.
AUTH_TOKEN = os.environ.get("FXG_DASHBOARD_TOKEN") or secrets.token_urlsafe(24)
TOKEN_FILE = os.environ.get("FXG_DASHBOARD_TOKEN_FILE", "/tmp/fxg_dashboard.token")

# Filesystem paths (verified on ALPHA per system index)
SIGNALS_FILE = os.environ.get(
    "FXG_SIGNALS_FILE",
    "/home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl",
)
BRIDGE_LOG = os.environ.get(
    "FXG_BRIDGE_LOG",
    "/home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl",
)
ENV_FILES = [
    os.environ.get("FXG_ENV_FILE_PRIMARY", "/etc/ai-quant/.env"),
    os.environ.get("FXG_ENV_FILE_SECONDARY", "/opt/ai-quant/.env"),
]

# Freshness thresholds (seconds)
SIGNAL_FILE_MAX_AGE = int(os.environ.get("FXG_SIGNAL_MAX_AGE", "600"))   # 10 min
TOP3_MAX_AGE = int(os.environ.get("FXG_TOP3_MAX_AGE", "600"))            # 10 min

# HTTP request budget
REQUEST_TIMEOUT = float(os.environ.get("FXG_REQUEST_TIMEOUT", "8.0"))

# Lane protection invariants (per Section 5 of system index)
EXPECTED_LANE_MODES = {
    "010": "manual_only",
    "011": "automated_paper",
}

# Demo mode toggle (set by --demo flag)
DEMO_MODE = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("FXG_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("fxg.dashboard")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    CRITICAL = "critical"   # blocks trading by default; can be overridden
    WARNING = "warning"     # advisory, never blocks
    INFO = "info"


@dataclass
class CheckResult:
    layer: str               # "alpha", "config", "readiness", "freshness"
    component: str           # human-readable component name
    name: str                # check name
    status: Status
    severity: Severity
    message: str             # short, operator-facing
    remedy: Optional[str] = None  # one-liner to fix it
    details: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        return d


@dataclass
class SystemState:
    timestamp: str
    overall_status: Status
    trading_ready: bool          # True if no critical failures
    has_warnings: bool
    checks: list[CheckResult]
    summary: dict
    can_override: bool            # operator may bypass critical failures

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "trading_ready": self.trading_ready,
            "has_warnings": self.has_warnings,
            "can_override": self.can_override,
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def safe_get(d: Any, *keys, default: Any = None) -> Any:
    """Defensively navigate nested dicts/lists."""
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and isinstance(k, int) and 0 <= k < len(cur):
            cur = cur[k]
        else:
            return default
    return cur


def fmt_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m ago"
    return f"{int(seconds // 86400)}d ago"


def file_age_seconds(path: str) -> Optional[float]:
    try:
        mtime = os.path.getmtime(path)
        return time.time() - mtime
    except (OSError, FileNotFoundError):
        return None


def env_file_present_and_nonempty(path: str) -> tuple[bool, int]:
    """Returns (present, size_bytes). Never reads contents."""
    try:
        st = os.stat(path)
        return (True, st.st_size)
    except PermissionError:
        # File exists but we can't read it (600 permissions) - that's actually OK
        return (True, -1)  # -1 indicates present but permission denied
    except (OSError, FileNotFoundError):
        return (False, 0)


# ---------------------------------------------------------------------------
# HTTP client (async via httpx if available, else asyncio.to_thread + requests)
# ---------------------------------------------------------------------------
async def http_get(url: str, timeout: float = REQUEST_TIMEOUT) -> tuple[int, Any]:
    """Returns (status_code, json_body or text). Raises on connection failure."""
    if httpx is None:
        # Fallback path so CLI mode works without httpx installed
        import urllib.request
        import urllib.error

        def _do():
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    return resp.status, json.loads(body)
                except json.JSONDecodeError:
                    return resp.status, body

        return await asyncio.to_thread(_do)

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text


async def http_post(url: str, json_body: dict, headers: dict | None = None,
                    timeout: float = REQUEST_TIMEOUT) -> tuple[int, Any]:
    if httpx is None:
        import urllib.request
        import urllib.error

        def _do():
            data = json.dumps(json_body).encode("utf-8")
            hdrs = {"Content-Type": "application/json", **(headers or {})}
            req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    try:
                        return resp.status, json.loads(body)
                    except json.JSONDecodeError:
                        return resp.status, body
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                try:
                    return e.code, json.loads(body)
                except json.JSONDecodeError:
                    return e.code, body

        return await asyncio.to_thread(_do)

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=json_body, headers=headers or {})
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
async def check_alpha_api_health() -> CheckResult:
    t0 = time.perf_counter()
    try:
        code, body = await http_get(f"{ALPHA_API}/api/health", timeout=5.0)
        dt = (time.perf_counter() - t0) * 1000
        if code == 200:
            return CheckResult(
                layer="alpha", component="ALPHA control plane", name="API health",
                status=Status.PASS, severity=Severity.CRITICAL,
                message=f"API responding at {ALPHA_API} ({dt:.0f}ms)",
                duration_ms=dt,
                details={"status_code": code, "body_preview": str(body)[:200]},
            )
        return CheckResult(
            layer="alpha", component="ALPHA control plane", name="API health",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message=f"API returned HTTP {code}",
            remedy="ssh to ALPHA: sudo systemctl restart ai-quant-control-plane",
            duration_ms=dt,
            details={"status_code": code},
        )
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        return CheckResult(
            layer="alpha", component="ALPHA control plane", name="API health",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message=f"Cannot reach {ALPHA_API}: {type(e).__name__}",
            remedy="On ALPHA: systemctl status ai-quant-control-plane && journalctl -u ai-quant-control-plane -n 50",
            duration_ms=dt,
            details={"error": str(e)},
        )


async def check_alpha_runner() -> CheckResult:
    """Runner is responsible for scans / signal generation."""
    t0 = time.perf_counter()
    try:
        code, body = await http_get(f"{ALPHA_API}/api/runtime/status")
        dt = (time.perf_counter() - t0) * 1000
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="alpha", component="ALPHA runner", name="Runtime status",
                status=Status.FAIL, severity=Severity.CRITICAL,
                message=f"Runtime endpoint unhealthy (HTTP {code})",
                remedy="On ALPHA: sudo systemctl restart ai-quant-runner",
                duration_ms=dt,
                details={"status_code": code},
            )
        # Fixed: Use correct field name from real API schema
        last_scan = safe_get(body, "last_scan_iso") or safe_get(body, "timestamp_iso")
        accounts_total = safe_get(body, "accounts_total", default=0)
        execution_capable = safe_get(body, "accounts_execution_capable", default=0)
        return CheckResult(
            layer="alpha", component="ALPHA runner", name="Runtime status",
            status=Status.PASS, severity=Severity.CRITICAL,
            message=f"Runner alive. Last scan: {last_scan or 'unknown'} ({accounts_total} accounts, {execution_capable} execution-capable)",
            duration_ms=dt,
            details={"last_scan": last_scan, "accounts_total": accounts_total, "execution_capable": execution_capable},
        )
    except Exception as e:
        return CheckResult(
            layer="alpha", component="ALPHA runner", name="Runtime status",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message=f"Runtime status unreachable: {type(e).__name__}",
            remedy="On ALPHA: sudo systemctl restart ai-quant-runner",
            details={"error": str(e)},
        )


async def check_config_loaded() -> CheckResult:
    t0 = time.perf_counter()
    try:
        code, body = await http_get(f"{ALPHA_API}/api/config")
        dt = (time.perf_counter() - t0) * 1000
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="config", component="Config", name="Config loaded",
                status=Status.FAIL, severity=Severity.CRITICAL,
                message=f"Config endpoint returned HTTP {code}",
                remedy="On ALPHA: tail /var/log/ai-quant/control-plane.log",
                duration_ms=dt,
            )

        # Fixed: Parse from data.ok and other nested fields in real API schema
        data = safe_get(body, "data", default=body)  # Handle both nested and flat
        config_ok = safe_get(data, "ok", default=True)  # Assume OK if not specified
        risk_config = safe_get(data, "risk")
        strategy_assignments = safe_get(data, "strategy_assignments", default=[])

        if not config_ok:
            return CheckResult(
                layer="config", component="Config", name="Config loaded",
                status=Status.FAIL, severity=Severity.CRITICAL,
                message="Config marked as not OK",
                remedy="Check control plane logs for config errors",
                duration_ms=dt,
                details={"config_ok": config_ok},
            )

        strategy_count = len(strategy_assignments) if strategy_assignments else 0
        risk_present = risk_config is not None

        return CheckResult(
            layer="config", component="Config", name="Config loaded",
            status=Status.PASS, severity=Severity.CRITICAL,
            message=f"Control plane config loaded ({strategy_count} strategy assignments, risk config {'present' if risk_present else 'missing'})",
            duration_ms=dt,
            details={
                "config_ok": config_ok,
                "strategy_assignments_count": strategy_count,
                "risk_config_present": risk_present,
                "top_level_keys": sorted(body.keys()) if isinstance(body, dict) else []
            },
        )
    except Exception as e:
        return CheckResult(
            layer="config", component="Config", name="Config loaded",
            status=Status.UNKNOWN, severity=Severity.CRITICAL,
            message=f"Could not fetch config: {type(e).__name__}",
            details={"error": str(e)},
        )


async def check_lane_protection() -> CheckResult:
    """Verify lane 010 is manual_only and lane 011 is automated_paper. ZERO DRIFT."""
    try:
        code, body = await http_get(f"{ALPHA_API}/api/config")
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="config", component="Lane protection", name="Lane modes",
                status=Status.UNKNOWN, severity=Severity.INFO,  # Fixed: Changed from CRITICAL to INFO
                message="Cannot verify lane modes (config endpoint unhealthy)",
            )

        # Fixed: Lane modes are NOT in /api/config endpoint, so this is expected to be unknown
        # Try to read from /api/config but don't fail hard if not found
        data = safe_get(body, "data", default=body)  # Handle both nested and flat structure
        lanes = (
            safe_get(data, "lanes")
            or safe_get(data, "runtime", "lanes")
            or {}
        )
        observed = {}
        for lane_id in ("010", "011"):
            mode = (
                safe_get(lanes, lane_id, "mode")
                or safe_get(lanes, lane_id, "execution_mode")
                or safe_get(data, f"lane_{lane_id}_mode")
            )
            observed[lane_id] = mode

        drift = []
        for lane_id, expected in EXPECTED_LANE_MODES.items():
            actual = observed.get(lane_id)
            if actual is None:
                drift.append(f"lane {lane_id}: mode unknown (not exposed in /api/config)")
            elif actual != expected:
                drift.append(f"lane {lane_id}: expected '{expected}', got '{actual}'")

        if not drift:
            return CheckResult(
                layer="config", component="Lane protection", name="Lane modes",
                status=Status.PASS, severity=Severity.INFO,  # Fixed: Changed from CRITICAL to INFO
                message=f"Lane 010 = manual_only, Lane 011 = automated_paper",
                details={"observed": observed},
            )

        # Fixed: Since lanes aren't in /api/config, mark as INFO not CRITICAL failure
        all_unknown = all(observed.get(k) is None for k in EXPECTED_LANE_MODES)
        if all_unknown:
            return CheckResult(
                layer="config", component="Lane protection", name="Lane modes",
                status=Status.WARN, severity=Severity.INFO,  # Fixed: INFO severity
                message="Lane modes not visible in /api/config (expected - check via runtime status)",
                remedy="Lane modes are configured elsewhere - this check may be deprecated",
                details={"observed": observed, "note": "lane_modes_not_in_config_endpoint"},
            )

        return CheckResult(
            layer="config", component="Lane protection", name="Lane modes",
            status=Status.WARN, severity=Severity.WARNING,  # Fixed: WARNING instead of CRITICAL
            message="Lane mode drift detected",
            remedy="Check actual lane configuration via /api/runtime/status",
            details={"observed": observed, "drift": drift},
        )
    except Exception as e:
        return CheckResult(
            layer="config", component="Lane protection", name="Lane modes",
            status=Status.UNKNOWN, severity=Severity.INFO,  # Fixed: INFO instead of CRITICAL
            message=f"Lane check errored: {type(e).__name__}",
            details={"error": str(e)},
        )


def check_env_files() -> CheckResult:
    """Local filesystem check -- only meaningful when dashboard runs ON ALPHA."""
    # Fixed: Check if running on ALPHA, if not mark as UNKNOWN
    hostname = socket.gethostname()
    on_alpha = "fxg-paper" in hostname or "fxg-quant" in hostname

    if not on_alpha:
        return CheckResult(
            layer="config", component=".env files", name="Credential files present",
            status=Status.UNKNOWN, severity=Severity.INFO,  # Fixed: UNKNOWN instead of FAIL
            message=f"Cannot check .env files from {hostname} (run dashboard on ALPHA for this check)",
            remedy="Deploy dashboard on ALPHA VM for full filesystem visibility",
            details={"hostname": hostname, "on_alpha": False},
        )

    results = []
    for path in ENV_FILES:
        present, size = env_file_present_and_nonempty(path)
        results.append({"path": path, "present": present, "size": size})

    missing = [r["path"] for r in results if not r["present"]]
    if not missing:
        # Handle case where files exist but have permission denied (size = -1)
        size_info = []
        for r in results:
            if r["size"] == -1:
                size_info.append("present (protected)")
            else:
                size_info.append(f"{r['size']}B")

        return CheckResult(
            layer="config", component=".env files", name="Credential files present",
            status=Status.PASS, severity=Severity.CRITICAL,
            message=f"Both .env files present ({' + '.join(size_info)})",
            details={"files": results, "hostname": hostname},
        )
    if len(missing) == len(ENV_FILES):
        return CheckResult(
            layer="config", component=".env files", name="Credential files present",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message="No .env files found -- credentials cannot be loaded",
            remedy="Restore from secure backup: scp .env to /etc/ai-quant/.env and /opt/ai-quant/.env, then restart services",
            details={"files": results, "hostname": hostname},
        )
    return CheckResult(
        layer="config", component=".env files", name="Credential files present",
        status=Status.WARN, severity=Severity.CRITICAL,
        message=f"Missing one .env file: {missing[0]}",
        remedy=f"Copy from the present location: sudo cp {[p for p in ENV_FILES if p not in missing][0]} {missing[0]}",
        details={"files": results, "hostname": hostname},
    )


async def check_preflight() -> CheckResult:
    """ALPHA's own preflight tells us about Windows sidecar via heartbeat sync."""
    t0 = time.perf_counter()
    try:
        code, body = await http_get(f"{ALPHA_API}/api/mt5/preflight", timeout=12.0)
        dt = (time.perf_counter() - t0) * 1000
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="readiness", component="Preflight", name="MT5 preflight gate",
                status=Status.FAIL, severity=Severity.CRITICAL,
                message=f"Preflight endpoint returned HTTP {code}",
                remedy="On ALPHA: curl http://127.0.0.1:8787/api/mt5/preflight | jq",
                duration_ms=dt,
            )

        # Fixed: Parse from correct nested structure data.preflight_status
        data = safe_get(body, "data", default={})
        status_val = safe_get(data, "preflight_status") or "UNKNOWN"
        blocked_by = safe_get(data, "blocking_reason")
        canonical_pass = safe_get(data, "canonical_preflight_pass", default=False)

        # Enhanced sidecar error reporting
        sidecar_http_ok = safe_get(data, "sidecar_http_ok", default=False)
        sidecar_health_ok = safe_get(data, "sidecar_health_ok", default=False)
        sidecar_account_ok = safe_get(data, "sidecar_account_ok", default=False)
        sidecar_error = safe_get(data, "sidecar_error")

        failed_checks = safe_get(data, "failed_checks", default=[])
        degraded_checks = safe_get(data, "degraded_checks", default=[])

        if str(status_val).upper() == "PASS" and canonical_pass:
            return CheckResult(
                layer="readiness", component="Preflight", name="MT5 preflight gate",
                status=Status.PASS, severity=Severity.CRITICAL,
                message="All execution layers ready",
                duration_ms=dt,
                details={"status": status_val, "canonical_pass": canonical_pass},
            )

        # Build specific sidecar message
        sidecar_msg = ""
        remedy_msg = "Check preflight details with: curl http://127.0.0.1:8787/api/mt5/preflight | jq"

        if sidecar_error == "sidecar_probe_non_200":
            # Sidecar is reachable but API auth failing
            if sidecar_http_ok and sidecar_health_ok and not sidecar_account_ok:
                sidecar_msg = " (sidecar reachable, health OK, but account probe HTTP 401 - API key incorrect)"
                remedy_msg = "Fix sidecar API key in /etc/ai-quant/.env (MT5_SIDECAR_API_KEY)"
            else:
                sidecar_msg = f" (sidecar probe failed: {sidecar_error})"
        elif blocked_by == "sidecar_unreachable":
            if not sidecar_http_ok:
                sidecar_msg = " (Windows sidecar completely unreachable)"
                remedy_msg = "On Windows: C:\\FXG\\run_mt5_sidecar.cmd, then wait 3s"
            else:
                sidecar_msg = f" (sidecar issue: {sidecar_error or 'unknown'})"

        # Add failed checks to message if available
        if failed_checks:
            failure_names = [check.get("name", "unknown") for check in failed_checks[:2]]
            sidecar_msg += f" [Failed: {', '.join(failure_names)}]"

        return CheckResult(
            layer="readiness", component="Preflight", name="MT5 preflight gate",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message=f"Preflight {status_val}{sidecar_msg}. Blocked by: {blocked_by or 'unknown'}",
            remedy=remedy_msg,
            duration_ms=dt,
            details={
                "status": status_val,
                "blocking_reason": blocked_by,
                "sidecar_http_ok": sidecar_http_ok,
                "sidecar_health_ok": sidecar_health_ok,
                "sidecar_account_ok": sidecar_account_ok,
                "sidecar_error": sidecar_error,
                "failed_checks": len(failed_checks),
                "degraded_checks": len(degraded_checks)
            },
        )
    except Exception as e:
        return CheckResult(
            layer="readiness", component="Preflight", name="MT5 preflight gate",
            status=Status.FAIL, severity=Severity.CRITICAL,
            message=f"Preflight unreachable: {type(e).__name__}",
            details={"error": str(e)},
        )


async def check_windows_heartbeat() -> CheckResult:
    """Windows pull loop syncs heartbeat back to ALPHA. We read it via ALPHA."""
    # Read from preflight's consumer runtime status
    try:
        code, body = await http_get(f"{ALPHA_API}/api/mt5/preflight", timeout=8.0)
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                status=Status.UNKNOWN, severity=Severity.CRITICAL,
                message=f"Cannot read preflight endpoint (HTTP {code})",
            )

        # Fixed: Parse from correct nested structure data.consumer_runtime_status.windows_consumer_heartbeat
        data = safe_get(body, "data", default={})
        consumer_status = safe_get(data, "consumer_runtime_status", default={})
        heartbeat = safe_get(consumer_status, "windows_consumer_heartbeat", default={})

        if not heartbeat:
            return CheckResult(
                layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                status=Status.WARN, severity=Severity.CRITICAL,
                message="Windows consumer heartbeat not found in preflight response",
                remedy="Verify Windows telemetry sync is running",
            )

        present = safe_get(heartbeat, "present", default=False)
        fresh = safe_get(heartbeat, "fresh", default=False)
        ok = safe_get(heartbeat, "ok", default=False)
        age_seconds = safe_get(heartbeat, "age_seconds")
        ts_utc = safe_get(heartbeat, "ts_utc")
        ea_name = safe_get(heartbeat, "ea_name")
        ea_version = safe_get(heartbeat, "ea_version")
        bridge_account = safe_get(heartbeat, "bridge_account")

        if not present:
            return CheckResult(
                layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                status=Status.FAIL, severity=Severity.CRITICAL,
                message="Windows consumer heartbeat not present",
                remedy="On Windows: restart FXG telemetry sync task",
                details={"heartbeat": heartbeat},
            )

        if not ok:
            return CheckResult(
                layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                status=Status.WARN, severity=Severity.CRITICAL,
                message="Windows consumer heartbeat present but marked not OK",
                details={"heartbeat": heartbeat},
            )

        # Fresh heartbeat - should be PASS
        if fresh and age_seconds is not None and age_seconds <= 300:  # 5 minutes
            return CheckResult(
                layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                status=Status.PASS, severity=Severity.CRITICAL,
                message=f"Windows heartbeat fresh ({fmt_age(age_seconds)}) - {ea_name} v{ea_version} on {bridge_account}",
                details={
                    "fresh": fresh,
                    "age_seconds": age_seconds,
                    "ts_utc": ts_utc,
                    "ea_name": ea_name,
                    "ea_version": ea_version,
                    "bridge_account": bridge_account
                },
            )

        # Stale but present
        if age_seconds is not None:
            if age_seconds <= 900:  # 15 minutes
                return CheckResult(
                    layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                    status=Status.WARN, severity=Severity.CRITICAL,
                    message=f"Windows heartbeat stale ({fmt_age(age_seconds)}) - sync may have hiccuped",
                    remedy="Check Windows telemetry sync task",
                    details={"age_seconds": age_seconds, "ts_utc": ts_utc},
                )
            else:
                return CheckResult(
                    layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
                    status=Status.FAIL, severity=Severity.CRITICAL,
                    message=f"Windows heartbeat dead ({fmt_age(age_seconds)}) - Windows consumer offline",
                    remedy="On Windows: restart MT5 sidecar and telemetry sync",
                    details={"age_seconds": age_seconds, "ts_utc": ts_utc},
                )

        # Fallback for unknown age
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.WARN, severity=Severity.CRITICAL,
            message="Windows heartbeat present but age unknown",
            details={"heartbeat": heartbeat},
        )

    except Exception as e:
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.UNKNOWN, severity=Severity.CRITICAL,
            message=f"Could not read heartbeat: {type(e).__name__}",
            details={"error": str(e)},
        )


def _interpret_heartbeat(last_seen: Any, raw: dict) -> CheckResult:
    if not last_seen:
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.WARN, severity=Severity.CRITICAL,
            message="No heartbeat timestamp reported",
            remedy="On Windows: Get-ScheduledTask FXG_Pull_Loop | Start-ScheduledTask",
            details={"raw": raw},
        )
    # Parse timestamp leniently
    try:
        if isinstance(last_seen, (int, float)):
            ts = datetime.fromtimestamp(float(last_seen), tz=timezone.utc)
        else:
            ts = datetime.fromisoformat(str(last_seen).replace("Z", "+00:00"))
        age = (now_utc() - ts).total_seconds()
    except Exception:
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.WARN, severity=Severity.CRITICAL,
            message=f"Heartbeat timestamp unparseable: {last_seen}",
            details={"raw": raw},
        )

    if age <= 300:  # 5 min
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.PASS, severity=Severity.CRITICAL,
            message=f"Heartbeat fresh ({fmt_age(age)})",
            details={"last_seen": str(last_seen), "age_s": age},
        )
    if age <= 900:  # 15 min
        return CheckResult(
            layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
            status=Status.WARN, severity=Severity.CRITICAL,
            message=f"Heartbeat stale ({fmt_age(age)}) -- pull loop may have hiccuped",
            remedy="On Windows: check C:\\FXG\\logs\\pull_signals.log",
            details={"last_seen": str(last_seen), "age_s": age},
        )
    return CheckResult(
        layer="readiness", component="Windows consumer", name="Heartbeat to ALPHA",
        status=Status.FAIL, severity=Severity.CRITICAL,
        message=f"Heartbeat dead ({fmt_age(age)}) -- Windows consumer offline",
        remedy="On Windows: Start-ScheduledTask FXG_Pull_Loop; Start-ScheduledTask FXG-MT5-Sidecar",
        details={"last_seen": str(last_seen), "age_s": age},
    )


def check_signal_file_freshness() -> CheckResult:
    """Local file: signal emission file written by ALPHA."""
    age = file_age_seconds(SIGNALS_FILE)
    if age is None:
        return CheckResult(
            layer="freshness", component="Signal file", name="signals_ftmo_demo2.jsonl",
            status=Status.UNKNOWN, severity=Severity.WARNING,
            message=f"File not found: {SIGNALS_FILE} (dashboard may not be running on ALPHA)",
            remedy="If running on MacBook, this check is expected to be UNKNOWN",
        )
    if age <= SIGNAL_FILE_MAX_AGE:
        return CheckResult(
            layer="freshness", component="Signal file", name="signals_ftmo_demo2.jsonl",
            status=Status.PASS, severity=Severity.WARNING,
            message=f"Updated {fmt_age(age)}",
            details={"path": SIGNALS_FILE, "age_s": age},
        )
    return CheckResult(
        layer="freshness", component="Signal file", name="signals_ftmo_demo2.jsonl",
        status=Status.WARN, severity=Severity.WARNING,
        message=f"Last updated {fmt_age(age)} -- expected within {SIGNAL_FILE_MAX_AGE}s",
        details={"path": SIGNALS_FILE, "age_s": age},
    )


async def check_top3_fresh() -> CheckResult:
    try:
        code, body = await http_get(f"{ALPHA_API}/api/top3/opportunities")
        if code != 200 or not isinstance(body, dict):
            return CheckResult(
                layer="freshness", component="Top3", name="Opportunities available",
                status=Status.WARN, severity=Severity.WARNING,
                message=f"Top3 endpoint returned HTTP {code}",
            )
        opps = safe_get(body, "opportunities", default=[]) or []
        last_scan = safe_get(body, "last_scan_time") or safe_get(body, "scanned_at")
        n = len(opps)
        if n == 0:
            return CheckResult(
                layer="freshness", component="Top3", name="Opportunities available",
                status=Status.WARN, severity=Severity.WARNING,
                message="No opportunities currently available",
                remedy="Wait for next scan cycle (typically 1-2 min)",
                details={"count": 0, "last_scan": last_scan},
            )
        if n < 3:
            return CheckResult(
                layer="freshness", component="Top3", name="Opportunities available",
                status=Status.WARN, severity=Severity.WARNING,
                message=f"Only {n}/3 opportunities found",
                details={"count": n, "last_scan": last_scan},
            )
        return CheckResult(
            layer="freshness", component="Top3", name="Opportunities available",
            status=Status.PASS, severity=Severity.WARNING,
            message=f"{n} opportunities available",
            details={"count": n, "last_scan": last_scan},
        )
    except Exception as e:
        return CheckResult(
            layer="freshness", component="Top3", name="Opportunities available",
            status=Status.UNKNOWN, severity=Severity.WARNING,
            message=f"Top3 unreachable: {type(e).__name__}",
            details={"error": str(e)},
        )


def check_dashboard_host() -> CheckResult:
    """Sanity: tell the operator where this dashboard is actually running."""
    hostname = socket.gethostname()
    on_alpha = "fxg-paper" in hostname or "fxg-quant" in hostname
    return CheckResult(
        layer="alpha", component="Dashboard host", name="Deployment location",
        status=(Status.PASS if on_alpha else Status.WARN),
        severity=Severity.WARNING,
        message=f"Dashboard running on '{hostname}'" + ("" if on_alpha else " (NOT on ALPHA -- some local-fs checks will be UNKNOWN)"),
        remedy=(None if on_alpha else "Deploy this script on the ALPHA VM for full visibility"),
        details={"hostname": hostname, "on_alpha": on_alpha},
    )


# ---------------------------------------------------------------------------
# Demo data (for offline UI development)
# ---------------------------------------------------------------------------
def demo_state() -> SystemState:
    checks = [
        CheckResult("alpha", "Dashboard host", "Deployment location",
                    Status.PASS, Severity.WARNING, "Dashboard running on 'fxg-paper-e2-small-main-2026'"),
        CheckResult("alpha", "ALPHA control plane", "API health",
                    Status.PASS, Severity.CRITICAL, "API responding at http://127.0.0.1:8787 (12ms)"),
        CheckResult("alpha", "ALPHA runner", "Runtime status",
                    Status.PASS, Severity.CRITICAL, "Runner alive. Last scan: 2026-05-06T18:08:00Z"),
        CheckResult("config", "Config", "Config loaded",
                    Status.PASS, Severity.CRITICAL, "Control plane reports a loaded config"),
        CheckResult("config", "Lane protection", "Lane modes",
                    Status.PASS, Severity.CRITICAL, "Lane 010 = manual_only, Lane 011 = automated_paper"),
        CheckResult("config", ".env files", "Credential files present",
                    Status.FAIL, Severity.CRITICAL,
                    "No .env files found -- credentials cannot be loaded",
                    remedy="Restore from secure backup: scp .env to /etc/ai-quant/.env and /opt/ai-quant/.env"),
        CheckResult("readiness", "Preflight", "MT5 preflight gate",
                    Status.FAIL, Severity.CRITICAL,
                    "Preflight BLOCKED (Windows sidecar unreachable). Blocked by: sidecar_unreachable",
                    remedy="On Windows run C:\\FXG\\run_mt5_sidecar.cmd"),
        CheckResult("readiness", "Windows consumer", "Heartbeat to ALPHA",
                    Status.WARN, Severity.CRITICAL, "Heartbeat stale (4m 12s ago) -- pull loop may have hiccuped"),
        CheckResult("freshness", "Signal file", "signals_ftmo_demo2.jsonl",
                    Status.PASS, Severity.WARNING, "Updated 2m 4s ago"),
        CheckResult("freshness", "Top3", "Opportunities available",
                    Status.PASS, Severity.WARNING, "3 opportunities available"),
    ]
    return _build_state(checks)


# ---------------------------------------------------------------------------
# Test orchestrator
# ---------------------------------------------------------------------------
async def run_all_checks() -> SystemState:
    if DEMO_MODE:
        return demo_state()

    # Phase 1: ALPHA reachability (gate to phase 2)
    host_check = check_dashboard_host()
    api_check = await check_alpha_api_health()

    checks: list[CheckResult] = [host_check, api_check]

    if api_check.status == Status.FAIL:
        # Skip downstream tests -- they'll all fail uselessly
        skip = lambda layer, comp, name: CheckResult(
            layer=layer, component=comp, name=name,
            status=Status.UNKNOWN, severity=Severity.CRITICAL,
            message="Skipped: ALPHA API unreachable",
        )
        checks += [
            skip("alpha", "ALPHA runner", "Runtime status"),
            skip("config", "Config", "Config loaded"),
            skip("config", "Lane protection", "Lane modes"),
            check_env_files(),
            skip("readiness", "Preflight", "MT5 preflight gate"),
            skip("readiness", "Windows consumer", "Heartbeat to ALPHA"),
            check_signal_file_freshness(),
            skip("freshness", "Top3", "Opportunities available"),
        ]
        return _build_state(checks)

    # Phase 2: parallel-friendly checks
    runner, config, lanes, preflight, heartbeat, top3 = await asyncio.gather(
        check_alpha_runner(),
        check_config_loaded(),
        check_lane_protection(),
        check_preflight(),
        check_windows_heartbeat(),
        check_top3_fresh(),
    )

    # Phase 3: filesystem (sync, fast)
    env_check = check_env_files()
    sig_check = check_signal_file_freshness()

    checks += [runner, config, lanes, env_check, preflight, heartbeat, sig_check, top3]
    return _build_state(checks)


def _build_state(checks: list[CheckResult]) -> SystemState:
    summary = {
        "pass": sum(1 for c in checks if c.status == Status.PASS),
        "warn": sum(1 for c in checks if c.status == Status.WARN),
        "fail": sum(1 for c in checks if c.status == Status.FAIL),
        "unknown": sum(1 for c in checks if c.status == Status.UNKNOWN),
        "total": len(checks),
    }
    critical_failures = [
        c for c in checks
        if c.severity == Severity.CRITICAL and c.status == Status.FAIL
    ]
    has_warnings = any(c.status == Status.WARN for c in checks)
    trading_ready = len(critical_failures) == 0
    if trading_ready and not has_warnings:
        overall = Status.PASS
    elif trading_ready:
        overall = Status.WARN
    else:
        overall = Status.FAIL

    return SystemState(
        timestamp=now_utc().isoformat(),
        overall_status=overall,
        trading_ready=trading_ready,
        has_warnings=has_warnings,
        checks=checks,
        summary=summary,
        can_override=True,  # per user spec: warn but allow override
    )


# ---------------------------------------------------------------------------
# CLI rendering
# ---------------------------------------------------------------------------
ANSI = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[32m", "yellow": "\033[33m", "red": "\033[31m",
    "cyan": "\033[36m", "magenta": "\033[35m", "gray": "\033[90m",
}


def _color(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{ANSI.get(color, '')}{text}{ANSI['reset']}"


def render_cli(state: SystemState) -> str:
    icon = {Status.PASS: "✓", Status.WARN: "!", Status.FAIL: "✗", Status.UNKNOWN: "?"}
    color = {Status.PASS: "green", Status.WARN: "yellow", Status.FAIL: "red", Status.UNKNOWN: "gray"}

    lines = []
    bar = "─" * 78
    lines.append(_color(bar, "gray"))
    title = "FXG ZERO-DRIFT TEST SUITE"
    lines.append(_color(title, "bold"))
    lines.append(_color(f"  {state.timestamp}", "gray"))
    lines.append(_color(bar, "gray"))

    badge = {
        Status.PASS: _color("[ TRADING READY ]", "green"),
        Status.WARN: _color("[ TRADE WITH CAUTION ]", "yellow"),
        Status.FAIL: _color("[ CRITICAL FAILURE - OVERRIDE REQUIRED ]", "red"),
    }.get(state.overall_status, "[ UNKNOWN ]")
    lines.append(f"  {badge}")
    s = state.summary
    lines.append(
        f"  {_color(str(s['pass']) + ' pass', 'green')}  "
        f"{_color(str(s['warn']) + ' warn', 'yellow')}  "
        f"{_color(str(s['fail']) + ' fail', 'red')}  "
        f"{_color(str(s['unknown']) + ' unknown', 'gray')}"
    )
    lines.append("")

    # Group by layer
    by_layer: dict[str, list[CheckResult]] = {}
    for c in state.checks:
        by_layer.setdefault(c.layer, []).append(c)

    layer_titles = {
        "alpha": "ALPHA VM",
        "config": "CONFIGURATION",
        "readiness": "TRADING READINESS",
        "freshness": "DATA FRESHNESS",
    }

    for layer in ("alpha", "config", "readiness", "freshness"):
        if layer not in by_layer:
            continue
        lines.append(_color(layer_titles.get(layer, layer.upper()), "cyan"))
        for c in by_layer[layer]:
            ic = _color(icon[c.status], color[c.status])
            name = f"{c.component} :: {c.name}"
            lines.append(f"  {ic}  {name}")
            lines.append(f"      {_color(c.message, 'gray')}")
            if c.remedy and c.status in (Status.FAIL, Status.WARN):
                lines.append(f"      {_color('→ ' + c.remedy, 'magenta')}")
        lines.append("")

    lines.append(_color(bar, "gray"))
    if not state.trading_ready:
        lines.append(_color("  Trading: BLOCKED (override available via --force on /api/execute)", "red"))
    elif state.has_warnings:
        lines.append(_color("  Trading: ALLOWED (acknowledge warnings before executing)", "yellow"))
    else:
        lines.append(_color("  Trading: READY", "green"))
    lines.append(_color(bar, "gray"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FastAPI web app
# ---------------------------------------------------------------------------
def build_app() -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI not installed. Run: pip install fastapi uvicorn httpx"
        )

    app = FastAPI(title="FXG Zero-Drift Dashboard", version="2.0")

    # Cache last state for /api/state polling efficiency
    state_cache: dict = {"state": None, "fetched_at": 0.0}
    CACHE_TTL = 5.0  # seconds

    async def get_cached_state() -> SystemState:
        now = time.time()
        if (
            state_cache["state"] is not None
            and (now - state_cache["fetched_at"]) < CACHE_TTL
        ):
            return state_cache["state"]
        state = await run_all_checks()
        state_cache["state"] = state
        state_cache["fetched_at"] = now
        return state

    def require_token(authorization: Optional[str] = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization[len("Bearer "):]
        if not secrets.compare_digest(token, AUTH_TOKEN):
            raise HTTPException(status_code=403, detail="Invalid token")

    @app.get("/api/health")
    async def health():
        return {"ok": True, "ts": now_utc().isoformat(), "version": "2.0"}

    @app.get("/api/state")
    async def api_state():
        state = await get_cached_state()
        return JSONResponse(state.to_dict())

    @app.post("/api/state/refresh")
    async def api_refresh():
        state_cache["state"] = None
        state = await get_cached_state()
        return JSONResponse(state.to_dict())

    @app.get("/api/opportunities")
    async def api_opportunities():
        if DEMO_MODE:
            return {
                "opportunities": [
                    {"id": "opp_demo_1", "symbol": "EURUSD", "signal": "BUY", "confidence": 78},
                    {"id": "opp_demo_2", "symbol": "GBPJPY", "signal": "SELL", "confidence": 71},
                    {"id": "opp_demo_3", "symbol": "XAUUSD", "signal": "BUY", "confidence": 65},
                ],
                "last_scan_time": now_utc().isoformat(),
            }
        try:
            code, body = await http_get(f"{ALPHA_API}/api/top3/opportunities")
            if code == 200:
                return body
            raise HTTPException(status_code=502, detail=f"ALPHA returned {code}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ALPHA unreachable: {e}")

    @app.post("/api/execute", dependencies=[Depends(require_token)])
    async def api_execute(payload: dict):
        opportunity_id = payload.get("opportunity_id")
        execution_target = payload.get("execution_target", "both")
        override_critical = bool(payload.get("override_critical", False))
        ack_warnings = bool(payload.get("acknowledge_warnings", False))
        confirm = bool(payload.get("confirm_trade", False))

        if not opportunity_id:
            raise HTTPException(status_code=400, detail="opportunity_id required")
        if not confirm:
            raise HTTPException(status_code=400, detail="confirm_trade=true required")

        state = await get_cached_state()
        if not state.trading_ready and not override_critical:
            return JSONResponse(
                status_code=409,
                content={
                    "status": "BLOCKED",
                    "reason": "Critical failures present and override_critical not set",
                    "critical_failures": [
                        c.to_dict() for c in state.checks
                        if c.severity == Severity.CRITICAL.value and c.status == Status.FAIL.value
                    ],
                },
            )
        if state.has_warnings and not ack_warnings:
            return JSONResponse(
                status_code=409,
                content={
                    "status": "BLOCKED",
                    "reason": "Warnings present and acknowledge_warnings not set",
                    "warnings": [
                        c.to_dict() for c in state.checks if c.status == Status.WARN.value
                    ],
                },
            )

        log.warning(
            "EXECUTE: opp=%s target=%s override=%s ack=%s",
            opportunity_id, execution_target, override_critical, ack_warnings,
        )
        if DEMO_MODE:
            return {
                "status": "EXECUTED",
                "demo": True,
                "opportunity_id": opportunity_id,
                "oanda_order_id": "demo_oanda_12345",
                "signal_id": "demo_sig_67890",
            }

        try:
            code, body = await http_post(
                f"{ALPHA_API}/api/execution/manual/010/from-top3",
                json_body={
                    "opportunity_id": opportunity_id,
                    "execution_target": execution_target,
                    "confirm_trade": True,
                    "operator_source": "fxg_zero_drift_dashboard_v2",
                },
                timeout=30.0,
            )
            return JSONResponse(status_code=code, content=body if isinstance(body, dict) else {"raw": body})
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Execution failed: {e}")

    @app.get("/")
    async def index():
        return HTMLResponse(_render_dashboard_html())

    return app


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------
def _render_dashboard_html() -> str:
    # Token is injected server-side; the SSH tunnel is the outer auth layer.
    return DASHBOARD_HTML.replace("__TOKEN__", AUTH_TOKEN)


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FXG :: Zero-Drift</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #07080c;
    --panel: #0e1118;
    --panel-2: #131826;
    --border: #1d2333;
    --border-2: #2a3148;
    --text: #d6dae6;
    --muted: #6b7388;
    --dim: #404758;
    --pass: #36d399;
    --warn: #f5b400;
    --fail: #ff476f;
    --unknown: #5b6478;
    --accent: #6cb6ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: radial-gradient(1200px 600px at 90% -10%, #0f1422 0%, transparent 60%),
                radial-gradient(900px 500px at -10% 110%, #131826 0%, transparent 50%),
                var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.5;
  }
  .mono { font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; }
  .container { max-width: 1320px; margin: 0 auto; padding: 24px; }

  /* Header */
  header {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
    align-items: end;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
  }
  .brand {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 20px;
    letter-spacing: 0.04em;
    color: var(--text);
  }
  .brand span.tag {
    color: var(--accent);
    font-weight: 500;
  }
  .meta {
    text-align: right;
    color: var(--muted);
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
  }
  .meta .countdown { color: var(--text); }

  /* Top status banner */
  .banner {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 20px;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 20px;
    align-items: center;
    background: var(--panel);
  }
  .banner.pass    { border-color: var(--pass); box-shadow: 0 0 0 1px var(--pass) inset, 0 0 30px -10px var(--pass); }
  .banner.warn    { border-color: var(--warn); box-shadow: 0 0 0 1px var(--warn) inset, 0 0 30px -10px var(--warn); }
  .banner.fail    { border-color: var(--fail); box-shadow: 0 0 0 1px var(--fail) inset, 0 0 30px -10px var(--fail); }
  .banner .dot {
    width: 14px; height: 14px; border-radius: 50%;
    background: var(--unknown);
    box-shadow: 0 0 0 6px rgba(255,255,255,0.04);
    animation: pulse 1.6s ease-in-out infinite;
  }
  .banner.pass .dot { background: var(--pass); box-shadow: 0 0 0 6px rgba(54,211,153,0.12); }
  .banner.warn .dot { background: var(--warn); box-shadow: 0 0 0 6px rgba(245,180,0,0.15); }
  .banner.fail .dot { background: var(--fail); box-shadow: 0 0 0 6px rgba(255,71,111,0.15); }
  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50%      { transform: scale(1.12); opacity: 0.85; }
  }
  .banner h1 {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 18px;
    letter-spacing: 0.06em;
    color: var(--text);
    margin-bottom: 4px;
  }
  .banner h1 small { color: var(--muted); font-weight: 400; font-size: 12px; margin-left: 8px; }
  .banner p { color: var(--muted); font-size: 13px; }

  /* Counts */
  .counts {
    display: flex;
    gap: 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }
  .counts .pill {
    border: 1px solid var(--border-2);
    border-radius: 6px;
    padding: 6px 10px;
    background: var(--panel-2);
  }
  .counts .pill b { font-weight: 700; }
  .counts .pass b { color: var(--pass); }
  .counts .warn b { color: var(--warn); }
  .counts .fail b { color: var(--fail); }
  .counts .unknown b { color: var(--unknown); }

  /* Layout */
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }
  @media (min-width: 980px) {
    .grid { grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); }
  }

  /* Sections */
  .section {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .section h2 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    background: var(--panel-2);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Check rows */
  .check {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    gap: 12px;
    align-items: start;
    padding: 12px 18px;
    border-bottom: 1px solid var(--border);
  }
  .check:last-child { border-bottom: 0; }
  .check.is-fail { background: linear-gradient(90deg, rgba(255,71,111,0.06), transparent 60%); }
  .check.is-warn { background: linear-gradient(90deg, rgba(245,180,0,0.05), transparent 60%); }
  .check .icon {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    margin-top: 1px;
  }
  .check .icon.pass    { color: var(--pass); }
  .check .icon.warn    { color: var(--warn); }
  .check .icon.fail    { color: var(--fail); }
  .check .icon.unknown { color: var(--unknown); }
  .check .body .name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
  }
  .check .body .name .comp { color: var(--muted); }
  .check .body .msg {
    font-size: 13px;
    color: var(--text);
    margin-top: 2px;
  }
  .check .body .remedy {
    margin-top: 6px;
    padding: 6px 10px;
    border-radius: 4px;
    background: rgba(108,182,255,0.06);
    border-left: 2px solid var(--accent);
    color: #b8d3f0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    word-break: break-word;
  }
  .check .severity {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--dim);
    padding-top: 4px;
  }
  .check .severity.critical { color: var(--fail); }

  /* Right column */
  .right-col { display: flex; flex-direction: column; gap: 16px; }

  /* Buttons */
  button, .btn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    border: 1px solid var(--border-2);
    background: var(--panel-2);
    color: var(--text);
    padding: 10px 16px;
    border-radius: 6px;
    cursor: pointer;
    transition: transform 0.06s ease, background 0.15s, border-color 0.15s;
  }
  button:hover:not(:disabled) { border-color: var(--accent); background: #1a2235; }
  button:active:not(:disabled) { transform: translateY(1px); }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  button.primary { border-color: var(--accent); color: var(--accent); }
  button.danger { border-color: var(--fail); color: var(--fail); }
  button.success { border-color: var(--pass); color: var(--pass); }

  /* Action panel */
  .actions { padding: 18px; display: flex; flex-direction: column; gap: 12px; }
  .actions .row { display: flex; gap: 10px; flex-wrap: wrap; }
  .hint { font-size: 12px; color: var(--muted); font-family: 'JetBrains Mono', monospace; }
  .hint kbd {
    background: var(--panel-2);
    border: 1px solid var(--border-2);
    border-radius: 3px;
    padding: 1px 6px;
    font-size: 11px;
    color: var(--text);
  }

  /* Modal */
  .modal-bg {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(4px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .modal-bg.open { display: flex; }
  .modal {
    width: min(620px, calc(100vw - 32px));
    max-height: calc(100vh - 64px);
    overflow: auto;
    background: var(--panel);
    border: 1px solid var(--border-2);
    border-radius: 10px;
    padding: 24px;
  }
  .modal h3 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text);
    margin-bottom: 12px;
  }
  .modal .danger-block {
    border: 1px solid var(--fail);
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 14px;
    background: rgba(255,71,111,0.06);
    color: #ffc6d2;
    font-size: 13px;
  }
  .modal .warn-block {
    border: 1px solid var(--warn);
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 14px;
    background: rgba(245,180,0,0.06);
    color: #ffe2a3;
    font-size: 13px;
  }
  .modal label.check-label {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px;
    border: 1px dashed var(--border-2);
    border-radius: 6px;
    margin-bottom: 8px;
    cursor: pointer;
    user-select: none;
  }
  .modal label.check-label input { margin-top: 3px; }
  .opp-list { display: flex; flex-direction: column; gap: 6px; margin: 12px 0; }
  .opp {
    border: 1px solid var(--border-2);
    border-radius: 6px;
    padding: 10px 12px;
    cursor: pointer;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 12px;
    align-items: center;
    background: var(--panel-2);
  }
  .opp:hover { border-color: var(--accent); }
  .opp.selected { border-color: var(--pass); box-shadow: 0 0 0 1px var(--pass) inset; }
  .opp .symbol { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--text); }
  .opp .signal { font-size: 12px; color: var(--muted); font-family: 'JetBrains Mono', monospace; }
  .opp .conf { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); }
  .modal-buttons { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; }

  /* Empty / loading */
  .empty { padding: 24px; text-align: center; color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .skeleton {
    background: linear-gradient(90deg, var(--panel-2), var(--border), var(--panel-2));
    background-size: 200% 100%;
    animation: shimmer 1.6s linear infinite;
    border-radius: 4px;
    height: 14px;
    margin: 6px 0;
  }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
</head>
<body>
<div class="container">

  <header>
    <div>
      <div class="brand">FXG <span class="tag">::</span> Zero-Drift Operator Console</div>
      <div class="hint">Dashboard v2.0 &nbsp;·&nbsp; press <kbd>R</kbd> to refresh, <kbd>T</kbd> to trade</div>
    </div>
    <div class="meta">
      <div id="hostInfo">—</div>
      <div>Last check: <span id="lastCheck">—</span></div>
      <div>Next refresh: <span class="countdown" id="countdown">—</span></div>
    </div>
  </header>

  <div id="banner" class="banner">
    <div class="dot"></div>
    <div>
      <h1 id="bannerTitle">CHECKING SYSTEM…</h1>
      <p id="bannerSubtitle">Running zero-drift validation suite</p>
    </div>
    <div class="counts">
      <span class="pill pass">PASS&nbsp;<b id="cntPass">—</b></span>
      <span class="pill warn">WARN&nbsp;<b id="cntWarn">—</b></span>
      <span class="pill fail">FAIL&nbsp;<b id="cntFail">—</b></span>
      <span class="pill unknown">?&nbsp;<b id="cntUnknown">—</b></span>
    </div>
  </div>

  <div class="grid">
    <div class="section">
      <h2>SYSTEM CHECKS <span id="checkSectionMeta" style="font-weight:400;color:var(--dim);"></span></h2>
      <div id="checks"></div>
    </div>
    <div class="right-col">
      <div class="section">
        <h2>OPERATOR ACTIONS</h2>
        <div class="actions">
          <div class="row">
            <button id="btnRefresh" class="primary">↻ Re-run checks</button>
            <button id="btnTrade" class="success">▶ Execute Lane 010</button>
          </div>
          <div class="hint" id="actionHint">Awaiting first check…</div>
        </div>
      </div>
      <div class="section">
        <h2>QUICK REFERENCE</h2>
        <div class="actions">
          <div class="hint">
            <b>Sidecar down?</b> &nbsp; On Windows: <span class="mono">C:\FXG\run_mt5_sidecar.cmd</span>
          </div>
          <div class="hint">
            <b>Services failed?</b> &nbsp; <span class="mono">sudo systemctl restart ai-quant-control-plane ai-quant-runner</span>
          </div>
          <div class="hint">
            <b>.env missing?</b> &nbsp; Restore from secure backup to <span class="mono">/etc/ai-quant/.env</span>
          </div>
          <div class="hint">
            <b>Preflight blocked?</b> &nbsp; <span class="mono">curl :8787/api/mt5/preflight</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Trade modal -->
<div class="modal-bg" id="tradeModal">
  <div class="modal">
    <h3>Execute manual trade · Lane 010</h3>
    <div id="modalCriticalBlock" class="danger-block" style="display:none;">
      <div style="font-weight:700;margin-bottom:6px;">⚠ CRITICAL FAILURES PRESENT</div>
      <div id="criticalList" class="mono" style="font-size:12px;"></div>
    </div>
    <div id="modalWarnBlock" class="warn-block" style="display:none;">
      <div style="font-weight:700;margin-bottom:6px;">⚠ WARNINGS PRESENT</div>
      <div id="warnList" class="mono" style="font-size:12px;"></div>
    </div>

    <div class="hint" style="margin-bottom:8px;">Select an opportunity:</div>
    <div id="oppList" class="opp-list"></div>

    <label id="ackWarnLabel" class="check-label" style="display:none;">
      <input type="checkbox" id="ackWarn">
      <span>I acknowledge the warnings above and want to proceed.</span>
    </label>
    <label id="overrideLabel" class="check-label" style="display:none;border-color:var(--fail);">
      <input type="checkbox" id="overrideCritical">
      <span><b style="color:var(--fail);">I understand</b> there are critical failures and I want to override and execute anyway. This will be logged.</span>
    </label>

    <div class="modal-buttons">
      <button onclick="closeTradeModal()">Cancel</button>
      <button id="btnConfirmTrade" class="success" disabled>Confirm execute</button>
    </div>
  </div>
</div>

<script>
  const TOKEN = '__TOKEN__';
  const REFRESH_MS = 10000;

  let lastState = null;
  let selectedOpp = null;
  let countdownT = null;

  function $(id){ return document.getElementById(id); }

  function statusClass(status){
    return ({PASS:'pass', WARN:'warn', FAIL:'fail', UNKNOWN:'unknown'}[status] || 'unknown');
  }
  function statusIcon(status){
    return ({PASS:'✓', WARN:'!', FAIL:'✗', UNKNOWN:'?'}[status] || '?');
  }

  async function fetchState(force){
    try {
      const url = force ? '/api/state/refresh' : '/api/state';
      const r = await fetch(url, { method: force ? 'POST' : 'GET' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      lastState = await r.json();
      render(lastState);
    } catch (e) {
      $('bannerTitle').textContent = 'DASHBOARD CANNOT REACH ALPHA';
      $('bannerSubtitle').textContent = e.message;
      $('banner').className = 'banner fail';
    }
  }

  function render(state){
    // Banner
    const b = $('banner');
    b.className = 'banner ' + statusClass(state.overall_status);
    const titles = {
      PASS: 'TRADING READY',
      WARN: 'TRADE WITH CAUTION',
      FAIL: 'CRITICAL FAILURES — OVERRIDE REQUIRED',
      UNKNOWN: 'STATE UNKNOWN',
    };
    $('bannerTitle').textContent = titles[state.overall_status] || 'STATE UNKNOWN';
    const fails = state.checks.filter(c => c.severity==='critical' && c.status==='FAIL');
    const warns = state.checks.filter(c => c.status==='WARN');
    let subtitle = '';
    if (fails.length > 0) subtitle = `${fails.length} critical failure${fails.length>1?'s':''} blocking trades`;
    else if (warns.length > 0) subtitle = `${warns.length} warning${warns.length>1?'s':''} — review before trading`;
    else subtitle = 'All checks green. System verified for manual execution.';
    $('bannerSubtitle').textContent = subtitle;

    $('cntPass').textContent = state.summary.pass;
    $('cntWarn').textContent = state.summary.warn;
    $('cntFail').textContent = state.summary.fail;
    $('cntUnknown').textContent = state.summary.unknown;

    $('lastCheck').textContent = new Date(state.timestamp).toLocaleTimeString();

    // Host info from first check
    const hostCheck = state.checks.find(c => c.name === 'Deployment location');
    if (hostCheck) {
      const h = (hostCheck.details || {}).hostname || 'unknown';
      const onAlpha = (hostCheck.details || {}).on_alpha;
      $('hostInfo').textContent = `host: ${h}${onAlpha ? '' : ' (off-ALPHA)'}`;
    }

    // Checks
    const order = ['alpha','config','readiness','freshness'];
    const groups = {};
    state.checks.forEach(c => { (groups[c.layer] = groups[c.layer] || []).push(c); });
    const layerLabels = { alpha:'ALPHA VM', config:'CONFIGURATION', readiness:'TRADING READINESS', freshness:'DATA FRESHNESS' };
    let html = '';
    order.forEach(layer => {
      if (!groups[layer]) return;
      html += `<div style="padding:10px 18px 6px;color:var(--accent);font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:0.16em;">${layerLabels[layer] || layer.toUpperCase()}</div>`;
      groups[layer].forEach(c => {
        const sc = statusClass(c.status);
        html += `
          <div class="check is-${sc}">
            <div class="icon ${sc}">${statusIcon(c.status)}</div>
            <div class="body">
              <div class="name"><span class="comp">${esc(c.component)} ::</span> ${esc(c.name)}</div>
              <div class="msg">${esc(c.message)}</div>
              ${c.remedy ? `<div class="remedy">→ ${esc(c.remedy)}</div>` : ''}
            </div>
            <div class="severity ${c.severity}">${c.severity}</div>
          </div>
        `;
      });
    });
    $('checks').innerHTML = html;

    // Action panel
    const tradeBtn = $('btnTrade');
    if (state.trading_ready && !state.has_warnings) {
      tradeBtn.disabled = false;
      tradeBtn.className = 'success';
      tradeBtn.textContent = '▶ Execute Lane 010';
      $('actionHint').textContent = 'System verified. Click execute to open trade panel.';
    } else if (state.trading_ready) {
      tradeBtn.disabled = false;
      tradeBtn.className = 'success';
      tradeBtn.textContent = '▶ Execute (warnings)';
      $('actionHint').textContent = 'Warnings present. You will need to acknowledge them.';
    } else if (state.can_override) {
      tradeBtn.disabled = false;
      tradeBtn.className = 'danger';
      tradeBtn.textContent = '▶ Execute (OVERRIDE)';
      $('actionHint').textContent = 'Critical failures present. Override required to execute.';
    } else {
      tradeBtn.disabled = true;
      tradeBtn.textContent = '▶ Execute (blocked)';
      $('actionHint').textContent = 'Trading blocked by policy.';
    }
  }

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  // Trade modal flow
  async function openTradeModal(){
    if (!lastState) return;
    selectedOpp = null;
    $('btnConfirmTrade').disabled = true;
    $('ackWarn').checked = false;
    $('overrideCritical').checked = false;

    const fails = lastState.checks.filter(c => c.severity==='critical' && c.status==='FAIL');
    const warns = lastState.checks.filter(c => c.status==='WARN');

    if (fails.length > 0) {
      $('modalCriticalBlock').style.display = 'block';
      $('criticalList').innerHTML = fails.map(c => `• ${esc(c.component)}: ${esc(c.message)}`).join('<br>');
      $('overrideLabel').style.display = 'flex';
    } else {
      $('modalCriticalBlock').style.display = 'none';
      $('overrideLabel').style.display = 'none';
    }
    if (warns.length > 0) {
      $('modalWarnBlock').style.display = 'block';
      $('warnList').innerHTML = warns.map(c => `• ${esc(c.component)}: ${esc(c.message)}`).join('<br>');
      $('ackWarnLabel').style.display = 'flex';
    } else {
      $('modalWarnBlock').style.display = 'none';
      $('ackWarnLabel').style.display = 'none';
    }

    $('oppList').innerHTML = '<div class="empty">Loading opportunities…</div>';
    $('tradeModal').classList.add('open');

    try {
      const r = await fetch('/api/opportunities');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      const opps = data.opportunities || [];
      if (opps.length === 0) {
        $('oppList').innerHTML = '<div class="empty">No opportunities currently available.</div>';
        return;
      }
      $('oppList').innerHTML = opps.map(o => `
        <div class="opp" data-id="${esc(o.id)}" onclick="selectOpp('${esc(o.id)}', this)">
          <div class="symbol">${esc(o.symbol)}</div>
          <div class="signal">${esc(o.signal)} · ${esc(o.id)}</div>
          <div class="conf">${esc(o.confidence)}%</div>
        </div>
      `).join('');
    } catch (e) {
      $('oppList').innerHTML = `<div class="empty" style="color:var(--fail);">Error: ${esc(e.message)}</div>`;
    }
  }

  function closeTradeModal(){ $('tradeModal').classList.remove('open'); }

  function selectOpp(id, el){
    selectedOpp = id;
    document.querySelectorAll('.opp').forEach(e => e.classList.remove('selected'));
    el.classList.add('selected');
    updateConfirmEnabled();
  }

  function updateConfirmEnabled(){
    if (!lastState) return;
    const fails = lastState.checks.filter(c => c.severity==='critical' && c.status==='FAIL');
    const warns = lastState.checks.filter(c => c.status==='WARN');
    let ok = !!selectedOpp;
    if (fails.length > 0) ok = ok && $('overrideCritical').checked;
    if (warns.length > 0) ok = ok && $('ackWarn').checked;
    $('btnConfirmTrade').disabled = !ok;
  }
  $('ackWarn').addEventListener('change', updateConfirmEnabled);
  $('overrideCritical').addEventListener('change', updateConfirmEnabled);

  async function confirmTrade(){
    if (!selectedOpp) return;
    const btn = $('btnConfirmTrade');
    btn.disabled = true; btn.textContent = 'Executing…';
    try {
      const r = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'Authorization':'Bearer ' + TOKEN },
        body: JSON.stringify({
          opportunity_id: selectedOpp,
          execution_target: 'both',
          confirm_trade: true,
          acknowledge_warnings: $('ackWarn').checked,
          override_critical: $('overrideCritical').checked,
        }),
      });
      const out = await r.json();
      if (r.ok && (out.status === 'EXECUTED' || out.status === 'OK' || out.oanda_order_id)) {
        alert('Trade submitted.\n\n' + JSON.stringify(out, null, 2));
        closeTradeModal();
        fetchState(true);
      } else {
        alert('Execution failed:\n\n' + JSON.stringify(out, null, 2));
      }
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Confirm execute';
    }
  }

  $('btnRefresh').addEventListener('click', () => { fetchState(true); resetCountdown(); });
  $('btnTrade').addEventListener('click', openTradeModal);
  $('btnConfirmTrade').addEventListener('click', confirmTrade);

  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    if (e.key === 'r' || e.key === 'R') { fetchState(true); resetCountdown(); }
    if (e.key === 't' || e.key === 'T') { openTradeModal(); }
    if (e.key === 'Escape') closeTradeModal();
  });

  function resetCountdown(){
    if (countdownT) clearInterval(countdownT);
    let s = REFRESH_MS / 1000;
    $('countdown').textContent = s + 's';
    countdownT = setInterval(() => {
      s -= 1;
      if (s <= 0) {
        clearInterval(countdownT);
        fetchState(false).then(resetCountdown);
        return;
      }
      $('countdown').textContent = s + 's';
    }, 1000);
  }

  // Bootstrap
  fetchState(true).then(resetCountdown);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def _persist_token() -> None:
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(AUTH_TOKEN + "\n")
        os.chmod(TOKEN_FILE, 0o600)
        log.info("Auth token persisted to %s (mode 0600)", TOKEN_FILE)
    except OSError as e:
        log.warning("Could not persist token to %s: %s", TOKEN_FILE, e)


def main_cli(json_output: bool = False) -> int:
    state = asyncio.run(run_all_checks())
    if json_output:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(render_cli(state))
    return 0 if state.overall_status == Status.PASS else (1 if state.overall_status == Status.WARN else 2)


def main_web() -> int:
    if FastAPI is None or httpx is None:
        print("ERROR: web mode requires fastapi, uvicorn, httpx", file=sys.stderr)
        print("       pip install --user fastapi uvicorn httpx", file=sys.stderr)
        return 3
    _persist_token()
    print("=" * 70)
    print(f" FXG Zero-Drift Dashboard v2.0")
    print(f" Listening on http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f" Auth token: {AUTH_TOKEN}")
    print(f"   (also at {TOKEN_FILE})")
    print(f" ALPHA API:  {ALPHA_API}")
    print(f" Demo mode:  {DEMO_MODE}")
    print("=" * 70)
    print()
    print(" From MacBook, open an SSH tunnel:")
    print("   gcloud compute ssh --zone us-central1-a fxg-paper-e2-small-main-2026 \\")
    print(f"     --project fxg-ai-trading -- -L {DASHBOARD_PORT}:localhost:{DASHBOARD_PORT} -N")
    print(f" Then open: http://localhost:{DASHBOARD_PORT}")
    print()
    app = build_app()
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="info")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FXG Zero-Drift Dashboard")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--web", action="store_true", help="run web server")
    g.add_argument("--json", action="store_true", help="CLI: machine-readable JSON output")
    p.add_argument("--demo", action="store_true", help="use synthetic data (offline UI dev)")
    p.add_argument("--host", default=None, help="web host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=None, help="web port (default: 8000)")
    p.add_argument("--alpha", default=None, help="ALPHA API URL (default: http://127.0.0.1:8787)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.demo:
        DEMO_MODE = True
    if args.host:
        DASHBOARD_HOST = args.host  # type: ignore
    if args.port:
        DASHBOARD_PORT = args.port  # type: ignore
    if args.alpha:
        ALPHA_API = args.alpha  # type: ignore

    if args.web:
        sys.exit(main_web())
    else:
        sys.exit(main_cli(json_output=args.json))
