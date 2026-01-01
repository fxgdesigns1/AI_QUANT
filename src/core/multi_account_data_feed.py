"""
Compatibility shim: provide get_multi_account_data_feed for strategies importing
src.core.multi_account_data_feed. Re-uses the optimized multi-account data feed
implemented in streaming_data_feed.py (get_optimized_data_feed).
"""
from typing import Any
try:
    from .streaming_data_feed import get_optimized_data_feed
except Exception:  # pragma: no cover - defensive
    get_optimized_data_feed = None  # type: ignore


def get_multi_account_data_feed() -> Any:
    """
    Return the optimized multi-account data feed instance. If the optimized
    implementation is unavailable, returns None.
    """
    if get_optimized_data_feed:
        return get_optimized_data_feed()
    return None


__all__ = ["get_multi_account_data_feed"]



