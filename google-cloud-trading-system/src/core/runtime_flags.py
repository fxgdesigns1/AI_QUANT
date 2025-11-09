#!/usr/bin/env python3
"""
Runtime configuration flags for the trading system.

This module centralises all feature toggles so that the application can run in
different modes (eg. verification, staging, production) without code changes.
Defaults favour safety: live trading, background jobs and external API calls are
disabled unless explicitly enabled with environment variables.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _env_flag(name: str, default: bool = False) -> bool:
    """
    Read a boolean flag from the environment.

    Accepted truthy values: '1', 'true', 'yes', 'on' (case-insensitive).
    Accepted falsy values: '0', 'false', 'no', 'off'.
    Missing values fall back to the provided default.
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    # Unknown tokens fall back to default but loggable by callers if needed.
    return default


@lru_cache(maxsize=1)
def get_runtime_mode() -> str:
    """
    Return the current runtime mode.

    Supported values (case-insensitive):
      - verification (default)
      - staging
      - production
    """
    return os.getenv("SYSTEM_MODE", "verification").strip().lower()


def is_production_mode() -> bool:
    """True when SYSTEM_MODE=production."""
    return get_runtime_mode() == "production"


def is_verification_mode() -> bool:
    """True when running in the default verification mode."""
    return get_runtime_mode() in {"verification", "verify", "test", "testing"}


def is_live_trading_enabled() -> bool:
    """
    Whether trade execution and real-money integrations are enabled.

    Defaults to False unless running in production *and* the flag is explicitly
    enabled. This prevents accidental trade placement during verification.
    """
    default = is_production_mode()
    return _env_flag("ENABLE_LIVE_TRADING", default=default)


def is_market_data_enabled() -> bool:
    """
    Whether the system should pull live market data (eg. OANDA pricing).
    """
    default = is_production_mode()
    return _env_flag("ENABLE_MARKET_DATA", default=default)


def is_scheduler_enabled() -> bool:
    """
    Whether APScheduler background jobs (scanner, snapshots, etc.) should run.
    """
    default = is_production_mode()
    return _env_flag("ENABLE_SCHEDULER", default=default)


def is_dashboard_warmup_enabled() -> bool:
    """
    Whether the dashboard should pre-initialise itself in a background thread.
    """
    return _env_flag("ENABLE_DASHBOARD_WARMUP", default=False)


def is_monitoring_enabled() -> bool:
    """
    Whether the daily monitoring background thread should run.
    """
    default = is_production_mode()
    return _env_flag("ENABLE_MONITORING", default=default)


def is_socketio_enabled() -> bool:
    """
    Whether realtime Socket.IO features should be initialised.

    Defaults to False unless explicitly enabled. Google App Engine standard
    does not support WebSocket upgrades, so verification environments should
    leave this disabled to avoid endless 400 responses.
    """
    default = is_production_mode()
    return _env_flag("ENABLE_SOCKETIO", default=default)


def require_env_var(name: str) -> str:
    """
    Retrieve an environment variable or raise a helpful error.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not configured. Set it via Secret Manager or environment variables."
        )
    return value

