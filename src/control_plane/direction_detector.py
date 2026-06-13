"""
FXG Direction Detector — canonical SMA 8/20 H1 bias
Single source of truth. No logic duplicated elsewhere.
"""
import time
import logging
from typing import Literal

logger = logging.getLogger(__name__)

_cache: dict = {}
CACHE_TTL = 300  # 5 minutes

def get_bias(instrument: str, oanda_client) -> Literal["LONG", "SHORT", "NEUTRAL"]:
    """
    Returns LONG, SHORT, or NEUTRAL based on SMA 8/20 crossover on H1.
    Cached for 5 minutes per instrument to limit OANDA API calls.
    instrument: OANDA format with underscore e.g. AUD_JPY
    """
    now = time.time()
    if instrument in _cache:
        cached_bias, cached_at = _cache[instrument]
        if now - cached_at < CACHE_TTL:
            return cached_bias
    try:
        candles = oanda_client.get_candles(instrument, granularity="H1", count=25)
        closes = [float(c["mid"]["c"]) for c in candles if c.get("complete")]
        if len(closes) < 21:
            logger.warning(f"direction_detector: insufficient H1 bars for {instrument}")
            return "NEUTRAL"
        fast = sum(closes[-8:]) / 8
        slow = sum(closes[-20:]) / 20
        if slow == 0:
            return "NEUTRAL"
        if fast > slow * 1.0001:
            bias = "LONG"
        elif fast < slow * 0.9999:
            bias = "SHORT"
        else:
            bias = "NEUTRAL"
        _cache[instrument] = (bias, now)
        logger.info(f"direction_detector: {instrument} → {bias} (fast={fast:.5f} slow={slow:.5f})")
        return bias
    except Exception as e:
        logger.error(f"direction_detector: error for {instrument}: {e}")
        return "NEUTRAL"
