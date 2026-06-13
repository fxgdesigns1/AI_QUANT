"""
Research Settings Helper
Allows cached research mode without OANDA env vars.
"""

import os
from typing import Optional


def is_research_mode() -> bool:
    """Check if running in research mode (cached candles, no live OANDA)"""
    return os.getenv("RESEARCH_MODE", "false").lower() == "true"


def use_cached_candles() -> bool:
    """Check if should use cached candles"""
    if is_research_mode():
        return True
    return os.getenv("USE_CACHED_CANDLES", "false").lower() == "true"


def require_oanda_for_research() -> bool:
    """Check if OANDA is required (False for cached research)"""
    if use_cached_candles():
        return False
    return True


def get_research_artifacts_root() -> Optional[str]:
    """Get research artifacts root path"""
    return os.getenv("LOCAL_ARTIFACTS_ROOT") or os.getenv("ARTIFACTS_ROOT")


def get_research_runtime_root() -> Optional[str]:
    """Get research runtime root path"""
    return os.getenv("LOCAL_RUNTIME_ROOT") or os.getenv("RUNTIME_PATH", "runtime")
