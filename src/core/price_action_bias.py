"""Price Action Bias - Detects strong directional moves from raw price data.

Logic:
- Analyzes 48h of price history (H1 candles).
- Computes return % and linear regression slope.
- Returns BULLISH/BEARISH if move is significant (>2%) and consistent.
"""

from __future__ import annotations

import logging
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.control_plane.market_data_provider import get_candles

logger = logging.getLogger(__name__)

@dataclass
class PriceBiasResult:
    bias: Optional[str]  # "BULLISH", "BEARISH", or None
    confidence: float
    source: str = "price_action"
    metrics: Dict[str, Any] = None
    timestamp: Optional[str] = None

class PriceActionBias:
    """Detects bias from pure price action (48h momentum)."""
    
    def __init__(self):
        pass

    def calculate_bias(self, symbol: str) -> PriceBiasResult:
        """Calculate bias based on 48h price action."""
        try:
            # Fetch 48 hours of H1 candles + buffer
            # 48 candles
            candles = get_candles(symbol, granularity="H1", count=50)
            
            if not candles or len(candles) < 48:
                return PriceBiasResult(None, 0.0, metrics={"error": "insufficient_data"})

            # Use last 48 candles
            relevant_candles = candles[-48:]
            closes = np.array([c.c for c in relevant_candles])
            
            # 1. Calculate 48h Return
            start_price = closes[0]
            end_price = closes[-1]
            pct_change = ((end_price - start_price) / start_price) * 100.0
            
            # 2. Calculate Slope (Linear Regression)
            x = np.arange(len(closes))
            slope, _ = np.polyfit(x, closes, 1)
            
            # Normalize slope relative to price to make it comparable across instruments?
            # Or just check sign.
            # pct_change gives magnitude. Slope gives consistency of direction.
            
            # 3. ATR Expansion (Optional, per prompt spec just "ATR expansion" mentioned but return rule is specific)
            # "If abs(48h_return) >= 2.0% AND slope agrees"
            
            bias = None
            confidence = 0.0
            
            # Thresholds
            STRONG_MOVE_THRESHOLD = 2.0  # 2% move in 48h is significant for Forex/Gold
            
            if pct_change >= STRONG_MOVE_THRESHOLD and slope > 0:
                bias = "BULLISH"
                # Confidence scales with magnitude, capped at 1.0 (but usually lower than Outlook)
                # Let's say 2% = 0.6, 4% = 0.8
                confidence = min(0.6 + (pct_change - 2.0) * 0.1, 0.9)
                
            elif pct_change <= -STRONG_MOVE_THRESHOLD and slope < 0:
                bias = "BEARISH"
                confidence = min(0.6 + (abs(pct_change) - 2.0) * 0.1, 0.9)
            
            metrics = {
                "48h_return_pct": round(pct_change, 2),
                "slope": float(slope),
                "start_price": start_price,
                "end_price": end_price,
                "candles_count": len(relevant_candles)
            }
            
            return PriceBiasResult(
                bias=bias,
                confidence=round(confidence, 2),
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.error(f"Error calculating price action bias for {symbol}: {e}")
            return PriceBiasResult(None, 0.0, metrics={"error": str(e)})
