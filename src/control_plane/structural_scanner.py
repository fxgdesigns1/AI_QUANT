"""Structural Scanner - REAL Market Structure Analysis (NO DUMMY DATA)

Scans instruments for structural characteristics using REAL market data.
READ-ONLY. Does not generate trade signals.
Uses actual OANDA historical data - NO STUBS, NO SIMULATIONS.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional
from .status_snapshot import get_status_snapshot
from .market_data_provider import (
    get_latest_price,
    get_candles,
    MarketDataError,
    PriceIntegrityError
)

logger = logging.getLogger(__name__)

class StructuralScanner:
    """Scans for market structure (read-only)"""
    
    def _analyze_structure(self, instrument: str) -> Dict[str, Any]:
        """Analyze market structure for a single instrument using REAL data"""
        try:
            # Get current price
            current_price = get_latest_price(instrument, timeout_s=5.0)
            current_mid = current_price.mid
            
            # Get historical candles (use daily for structure analysis)
            candles = get_candles(instrument, granularity="D", count=50, timeout_s=10.0)
            
            if len(candles) < 20:
                # Not enough data
                return {
                    "instrument": instrument,
                    "score": 30,  # Low score for insufficient data
                    "regime": "INSUFFICIENT_DATA",
                    "volatility": "UNKNOWN",
                    "key_levels": [],
                    "rationale": [f"Insufficient history: {len(candles)} candles (need 20+)"],
                    "warnings": [f"Only {len(candles)} daily candles available"]
                }
            
            # Calculate ATR (Average True Range) for volatility
            true_ranges = []
            for i in range(1, len(candles)):
                tr = max(
                    candles[i].h - candles[i].l,
                    abs(candles[i].h - candles[i-1].c),
                    abs(candles[i].l - candles[i-1].c)
                )
                true_ranges.append(tr)
            
            atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0
            atr_pct = (atr / current_mid) * 100 if current_mid > 0 else 0
            
            # Determine volatility regime
            if atr_pct > 2.0:
                volatility = "HIGH"
            elif atr_pct > 1.0:
                volatility = "MEDIUM"
            elif atr_pct > 0.3:
                volatility = "NORMAL"
            else:
                volatility = "LOW"
            
            # Calculate trend strength (simplified ADX-like)
            up_moves = []
            down_moves = []
            for i in range(1, len(candles)):
                move = candles[i].c - candles[i-1].c
                if move > 0:
                    up_moves.append(move)
                else:
                    down_moves.append(abs(move))
            
            avg_up = sum(up_moves) / len(up_moves) if up_moves else 0
            avg_down = sum(down_moves) / len(down_moves) if down_moves else 0
            total_move = avg_up + avg_down
            
            if total_move > 0:
                directional_movement = abs(avg_up - avg_down) / total_move
            else:
                directional_movement = 0
            
            # Determine regime
            if directional_movement > 0.6:
                if avg_up > avg_down:
                    regime = "UPTREND"
                    score = int(50 + (directional_movement * 30))
                else:
                    regime = "DOWNTREND"
                    score = int(50 - (directional_movement * 30))
            elif directional_movement > 0.3:
                regime = "WEAK_TREND"
                score = int(45 + (directional_movement * 10))
            else:
                regime = "RANGE_BOUND"
                score = int(40 + (atr_pct * 5))
            
            # Clamp score
            score = max(0, min(100, score))
            
            # Calculate key levels (pivot points)
            recent_highs = sorted([c.h for c in candles[-20:]], reverse=True)
            recent_lows = sorted([c.l for c in candles[-20:]])
            key_levels = []
            
            # Add significant highs/lows
            if recent_highs:
                key_levels.append(round(recent_highs[0], 5))  # Highest high
            if recent_lows:
                key_levels.append(round(recent_lows[0], 5))  # Lowest low
            
            # Rationale
            rationale = [
                f"Regime: {regime} (directional strength: {directional_movement:.1%})",
                f"Volatility: {volatility} (ATR: {atr_pct:.2f}%)",
                f"Price: {current_mid:.5f}",
                f"Analysis based on {len(candles)} daily candles"
            ]
            
            return {
                "instrument": instrument,
                "score": score,
                "regime": regime,
                "volatility": volatility,
                "key_levels": key_levels,
                "rationale": rationale,
                "warnings": []
            }
            
        except (MarketDataError, PriceIntegrityError) as e:
            logger.warning(f"Market data error for {instrument}: {e}")
            return {
                "instrument": instrument,
                "score": 0,
                "regime": "DATA_ERROR",
                "volatility": "UNKNOWN",
                "key_levels": [],
                "rationale": [f"Could not fetch market data: {str(e)[:100]}"],
                "warnings": [f"Market data error: {str(e)[:100]}"]
            }
        except Exception as e:
            logger.error(f"Unexpected error analyzing {instrument}: {e}", exc_info=True)
            return {
                "instrument": instrument,
                "score": 0,
                "regime": "ANALYSIS_ERROR",
                "volatility": "UNKNOWN",
                "key_levels": [],
                "rationale": [f"Analysis failed: {str(e)[:100]}"],
                "warnings": [f"Analysis error: {str(e)[:100]}"]
            }

    def scan(self) -> Dict[str, Any]:
        """Perform structural scan using REAL market data"""
        
        # Standard instrument set
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "AUD_USD"]
        
        results = []
        for inst in instruments:
            result = self._analyze_structure(inst)
            results.append(result)
            
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "timestamp": time.time(),
            "scanner_version": "2.0.0-real-data",
            "count": len(results),
            "results": results,
            "note": f"Real market data analysis - {len([r for r in results if r['score'] > 0])}/{len(results)} instruments analyzed"
        }

# Singleton
_scanner = None

def get_structural_scanner() -> StructuralScanner:
    global _scanner
    if _scanner is None:
        _scanner = StructuralScanner()
    return _scanner
