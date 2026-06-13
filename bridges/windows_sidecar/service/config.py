"""Configuration for Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BRIDGE_ID = "parallel_windows_sidecar_bridge_v1"
BIND_HOST = os.getenv("BIND_HOST", "127.0.0.1")
BIND_PORT = int(os.getenv("BIND_PORT", "8877"))
SIDECAR_API_KEY = os.getenv("SIDECAR_API_KEY", "")
MT5_TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH", "")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0")) if os.getenv("MT5_LOGIN") else None
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


# When false, POST /control/* returns 403. Default off for safety.
SIDECAR_ENABLE_WRITE_ACTIONS = _env_bool("SIDECAR_ENABLE_WRITE_ACTIONS", False)
SIDECAR_CONTROL_AUDIT_LOG_PATH = (os.getenv("SIDECAR_CONTROL_AUDIT_LOG_PATH") or "").strip()


def require_config() -> None:
    """Fail fast if required config is missing."""
    if not SIDECAR_API_KEY:
        raise ValueError("SIDECAR_API_KEY is required")
    if not MT5_TERMINAL_PATH:
        raise ValueError("MT5_TERMINAL_PATH is required")
