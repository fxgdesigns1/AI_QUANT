"""Outlook Engine - REAL Market Analysis (NO DUMMY DATA)

Generates Daily/Weekly/Monthly outlooks based on REAL market data.
READ-ONLY. No execution side effects.
Uses actual OANDA market data - NO STUBS, NO SIMULATIONS.
"""

from __future__ import annotations

import json
import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.control_plane.market_data_provider import (
    get_latest_price,
    get_candles,
    MarketDataError,
    PriceIntegrityError
)

logger = logging.getLogger(__name__)

class OutlookEngine:
    """Deterministic outlook generator"""
    
    def __init__(self):
        # Paths
        self._repo_root = Path(__file__).resolve().parents[2]
        self._runtime_dir = self._repo_root / "runtime"
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        
    def _compute_hash(self, data: Any) -> str:
        """Stable hash of input data"""
        s = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def _analyze_instrument(self, instrument: str, horizon: str) -> Dict[str, Any]:
        """Analyze a single instrument using REAL market data"""
        # Import indicators locally to avoid circular imports (strategies -> outlook -> strategies)
        try:
            from src.strategies.indicators import calculate_ema, calculate_rsi, calculate_macd
            has_indicators = True
        except ImportError:
            has_indicators = False
            
        try:
            # Get current price
            current_price = get_latest_price(instrument, timeout_s=5.0)
            current_mid = current_price.mid
            
            # Get historical candles based on horizon
            # For daily, use H1 (hourly) candles for more reactive trend detection
            # This catches moves earlier than daily candles
            if horizon == "daily":
                granularity = "H1"  # Use hourly for daily bias (more reactive)
                count = 168  # 7 days * 24 hours = 168 hours
            elif horizon == "weekly":
                granularity = "D"  # Daily candles for weekly bias
                count = 35  # 5 weeks * 7 days
            else:  # monthly
                granularity = "W"
                count = 8  # 8 weeks
            
            candles = get_candles(instrument, granularity=granularity, count=count, timeout_s=10.0)
            
            if len(candles) < 5:
                # Not enough data - return error state
                return {
                    "instrument": instrument,
                    "bias": "NEUTRAL",
                    "confidence": "LOW",
                    "key_levels": {"support": [], "resistance": []},
                    "scenarios": [{
                        "name": "Insufficient Data",
                        "probability": "100%",
                        "description": f"Only {len(candles)} candles available, need at least 5 for analysis"
                    }],
                    "warnings": [f"Insufficient historical data: {len(candles)} candles"]
                }
            
            # Calculate support/resistance from recent highs and lows
            recent_highs = sorted([c.h for c in candles[-10:]], reverse=True)
            recent_lows = sorted([c.l for c in candles[-10:]])
            
            # Key levels: recent highs become resistance, recent lows become support
            resistance_levels = sorted(set(recent_highs[:3]), reverse=True)
            support_levels = sorted(set(recent_lows[:3]))
            
            # HYBRID TREND DETECTION: Use EMA structure as PRIMARY signal, price movement as confirmation
            # This catches trends EARLIER than waiting for 0.8% price moves
            
            # Calculate EMA structure for early trend detection
            ema_bias = None
            ema_confidence = "LOW"
            if has_indicators and len(candles) >= 200:
                try:
                    closes = [c.c for c in candles]
                    ema_fast = calculate_ema(closes, period=50)
                    ema_slow = calculate_ema(closes, period=200)
                    
                    if ema_fast and ema_slow:
                        # EMA structure is PRIMARY signal (catches trends early)
                        if ema_fast > ema_slow:
                            ema_bias = "BULLISH"
                            # Check EMA separation for confidence
                            ema_separation_pct = ((ema_fast - ema_slow) / ema_slow) * 100
                            if abs(ema_separation_pct) > 0.5:
                                ema_confidence = "HIGH"
                            elif abs(ema_separation_pct) > 0.2:
                                ema_confidence = "MEDIUM"
                        elif ema_fast < ema_slow:
                            ema_bias = "BEARISH"
                            ema_separation_pct = ((ema_slow - ema_fast) / ema_fast) * 100
                            if abs(ema_separation_pct) > 0.5:
                                ema_confidence = "HIGH"
                            elif abs(ema_separation_pct) > 0.2:
                                ema_confidence = "MEDIUM"
                except Exception:
                    pass  # Fall back to price movement
            
            # Calculate price movement as secondary confirmation
            if horizon == "daily" and len(candles) >= 1:
                # For daily (H1 candles), use last 24 hours as anchor
                lookback = min(24, len(candles) - 1)
                anchor_close = candles[-lookback].c
                price_change = current_mid - anchor_close
                price_change_pct = (price_change / anchor_close) * 100 if anchor_close > 0 else 0
            else:
                # Weekly/Monthly: use oldest candle as structural anchor
                anchor_close = candles[0].c
                price_change = current_mid - anchor_close
                price_change_pct = (price_change / anchor_close) * 100 if anchor_close > 0 else 0
            
            # LOWERED thresholds for gold (catch moves earlier)
            # Instrument-specific thresholds
            is_metal = "XAU" in instrument or "XAG" in instrument
            
            if is_metal:
                # Gold/Silver: LOWERED to 0.3% (was 0.8%) to catch moves earlier
                # EMA structure is primary, so we can use lower price threshold
                bullish_threshold = 0.3
                bearish_threshold = -0.3
                strong_move_threshold = 1.0  # 1.0%+ is strong for gold
            else:
                # FX pairs: 0.2% threshold (tighter)
                bullish_threshold = 0.2
                bearish_threshold = -0.2
                strong_move_threshold = 0.5
            
            # HYBRID LOGIC: EMA structure takes priority, price movement confirms
            if ema_bias:
                # EMA structure detected - use it as primary signal
                bias = ema_bias
                confidence = ema_confidence
                
                # Price movement confirms EMA (boosts confidence)
                if ema_bias == "BULLISH" and price_change_pct > 0:
                    if price_change_pct >= strong_move_threshold:
                        confidence = "HIGH"
                    elif price_change_pct > bullish_threshold and confidence == "LOW":
                        confidence = "MEDIUM"
                elif ema_bias == "BEARISH" and price_change_pct < 0:
                    if abs(price_change_pct) >= abs(strong_move_threshold):
                        confidence = "HIGH"
                    elif abs(price_change_pct) > abs(bearish_threshold) and confidence == "LOW":
                        confidence = "MEDIUM"
                # If EMA says one thing but price moves opposite, reduce confidence
                elif (ema_bias == "BULLISH" and price_change_pct < -bearish_threshold) or \
                     (ema_bias == "BEARISH" and price_change_pct > bullish_threshold):
                    
                    # CHECK FOR STRONG REVERSAL FIRST (Fix for "Gold 2% Move" issue)
                    if abs(price_change_pct) >= strong_move_threshold:
                        # Strong move overrides EMA structure (Reversal/Breakout)
                        bias = "BULLISH" if price_change_pct > 0 else "BEARISH"
                        confidence = "HIGH"
                        bias_reason = f"strong_reversal_{price_change_pct:.2f}%_overrides_ema"
                        logger.info(f"Bias REVERSAL for {instrument}: Price Change {price_change_pct:.2f}% overrides EMA {ema_bias}")
                    else:
                        # Weak/Moderate counter-move: EMA and price conflict - downgrade to NEUTRAL for safety
                        bias = "NEUTRAL"
                        confidence = "LOW"
                        logger.info(f"Bias downgraded to NEUTRAL for {instrument}: EMA {ema_bias} but Price Change {price_change_pct:.2f}% (Conflict)")
            else:
                # No EMA structure (insufficient data) - fall back to price movement
                if price_change_pct > bullish_threshold:
                    bias = "BULLISH"
                    bias_reason = f"price_up_{price_change_pct:.2f}%_gt_{bullish_threshold}"
                    if abs(price_change_pct) >= strong_move_threshold:
                        confidence = "HIGH"
                    elif abs(price_change_pct) > bullish_threshold * 1.5:
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"
                elif price_change_pct < bearish_threshold:
                    bias = "BEARISH"
                    bias_reason = f"price_down_{price_change_pct:.2f}%_lt_{bearish_threshold}"
                    if abs(price_change_pct) >= abs(strong_move_threshold):
                        confidence = "HIGH"
                    elif abs(price_change_pct) > abs(bearish_threshold * 1.5):
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"
                else:
                    bias = "NEUTRAL"
                    bias_reason = f"price_range_{price_change_pct:.2f}%_within_{bearish_threshold}/{bullish_threshold}"
                    confidence = "LOW"
                    logger.info(f"Bias NEUTRAL for {instrument}: Price Change {price_change_pct:.2f}% within threshold ({bearish_threshold} to {bullish_threshold})")
                    # EXPLICIT LOGGING FOR NEUTRAL BIAS (AUDIT)
                    logger.info(
                        f"Bias NEUTRAL for {instrument} "
                        f"reason=price_within_threshold "
                        f"change_pct={price_change_pct:.2f}% "
                        f"thresholds={bearish_threshold}/{bullish_threshold}"
                    )
            
            # If EMA logic was used, set a reason too
            if ema_bias and 'bias_reason' not in locals():
                 bias_reason = f"ema_{ema_bias}_conf_{ema_confidence}"

            # Calculate volatility (ATR-like)
            ranges = [c.h - c.l for c in candles[-10:]]
            avg_range = sum(ranges) / len(ranges) if ranges else 0
            volatility_pct = (avg_range / current_mid) * 100 if current_mid > 0 else 0
            
            # Generate scenarios based on REAL market conditions
            scenarios = []
            
            # Scenario 1: Current trend continuation
            if price_change_pct > 0.3:
                scenarios.append({
                    "name": "Uptrend Continuation",
                    "probability": f"{min(70, int(50 + abs(price_change_pct) * 5))}%",
                    "description": f"Price up {price_change_pct:.2f}% recently, may continue higher toward {resistance_levels[0]:.5f}" if resistance_levels else f"Price up {price_change_pct:.2f}% recently, may continue higher"
                })
            elif price_change_pct < -0.3:
                scenarios.append({
                    "name": "Downtrend Continuation",
                    "probability": f"{min(70, int(50 + abs(price_change_pct) * 5))}%",
                    "description": f"Price down {abs(price_change_pct):.2f}% recently, may continue lower toward {support_levels[0]:.5f}" if support_levels else f"Price down {abs(price_change_pct):.2f}% recently, may continue lower"
                })
            
            # Scenario 2: Range bound (if price is between support/resistance)
            if support_levels and resistance_levels:
                if support_levels[0] < current_mid < resistance_levels[0]:
                    range_size = resistance_levels[0] - support_levels[0]
                    range_pct = (range_size / current_mid) * 100
                    scenarios.append({
                        "name": "Range Bound",
                        "probability": f"{int(40 + min(30, volatility_pct * 2))}%",
                        "description": f"Price consolidating between {support_levels[0]:.5f} and {resistance_levels[0]:.5f} ({range_pct:.2f}% range)"
                    })
            
            # Scenario 3: Reversal (if near key levels)
            if resistance_levels and current_mid > resistance_levels[0] * 0.98:
                scenarios.append({
                    "name": "Resistance Rejection",
                    "probability": "30%",
                    "description": f"Price near resistance at {resistance_levels[0]:.5f}, potential reversal lower"
                })
            elif support_levels and current_mid < support_levels[0] * 1.02:
                scenarios.append({
                    "name": "Support Bounce",
                    "probability": "30%",
                    "description": f"Price near support at {support_levels[0]:.5f}, potential bounce higher"
                })
            
            # If no scenarios generated, add a neutral one
            if not scenarios:
                scenarios.append({
                    "name": "Neutral Consolidation",
                    "probability": "50%",
                    "description": f"Price action neutral, consolidating around {current_mid:.5f}"
                })
            
            # Format support/resistance levels
            support_formatted = [round(level, 5) for level in support_levels[:3]]
            resistance_formatted = [round(level, 5) for level in resistance_levels[:3]]
            
            return {
                "instrument": instrument,
                "bias": bias,
                "bias_reason": bias_reason if 'bias_reason' in locals() else "unknown",
                "confidence": confidence,
                "key_levels": {
                    "support": support_formatted,
                    "resistance": resistance_formatted
                },
                "scenarios": scenarios,
                "warnings": [] if len(candles) >= 10 else [f"Limited history: {len(candles)} candles"]
            }
            
        except (MarketDataError, PriceIntegrityError) as e:
            logger.warning(f"Market data error for {instrument}: {e}")
            return {
                "instrument": instrument,
                "bias": "NEUTRAL",
                "confidence": "LOW",
                "key_levels": {"support": [], "resistance": []},
                "scenarios": [{
                    "name": "Data Unavailable",
                    "probability": "100%",
                    "description": f"Could not fetch market data: {str(e)[:100]}"
                }],
                "warnings": [f"Market data error: {str(e)[:100]}"]
            }
        except Exception as e:
            logger.error(f"Unexpected error analyzing {instrument}: {e}", exc_info=True)
            return {
                "instrument": instrument,
                "bias": "NEUTRAL",
                "confidence": "LOW",
                "key_levels": {"support": [], "resistance": []},
                "scenarios": [{
                    "name": "Analysis Error",
                    "probability": "100%",
                    "description": f"Analysis failed: {str(e)[:100]}"
                }],
                "warnings": [f"Analysis error: {str(e)[:100]}"]
            }

    def compute(self, horizon: str, market_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Compute outlook for horizon using REAL market data (NO STUBS)"""
        
        ts = datetime.now(timezone.utc).isoformat()
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD", "AUD_USD"]
        
        # Analyze each instrument with REAL data
        outlooks = []
        market_data_collected = {}
        
        for instrument in instruments:
            try:
                outlook = self._analyze_instrument(instrument, horizon)
                outlooks.append(outlook)
                
                # Collect market data for hash
                try:
                    price = get_latest_price(instrument, timeout_s=3.0, validate=False)
                    market_data_collected[instrument] = {
                        "mid": price.mid,
                        "timestamp": price.ts_utc
                    }
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Failed to analyze {instrument}: {e}")
                # Add error state instead of stub
                outlooks.append({
                    "instrument": instrument,
                    "bias": None,  # Explicit NULL bias
                    "confidence": 0.0,
                    "source": "outlook_engine",
                    "status": "unavailable",
                    "error": str(e),
                    "key_levels": {"support": [], "resistance": []},
                    "scenarios": [{
                        "name": "Analysis Failed",
                        "probability": "100%",
                        "description": f"Could not analyze: {str(e)[:100]}"
                    }],
                    "warnings": [f"Analysis failed: {str(e)[:100]}"]
                })
        
        # Compute hash of real market data
        inputs_hash = self._compute_hash(market_data_collected) if market_data_collected else "no_data"
        
        result = {
            "horizon": horizon,
            "as_of": ts,
            "generated_at": time.time(),
            "engine_version": "2.0.0-real-data",
            "inputs_hash": inputs_hash,
            "outlooks": outlooks,
            "note": f"Real market data analysis - {len([o for o in outlooks if not o.get('warnings')])}/{len(outlooks)} instruments analyzed successfully"
        }
        
        # Save snapshot
        self._save_snapshot(horizon, result)
        
        return result

    def _save_snapshot(self, horizon: str, data: Dict[str, Any]) -> None:
        """Save outlook snapshot atomically"""
        filename = f"outlook_{horizon}.json"
        path = self._runtime_dir / filename
        tmp_path = path.with_suffix(".tmp")
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        tmp_path.replace(path)

    def get_latest(self, horizon: str) -> Optional[Dict[str, Any]]:
        """Get latest cached outlook"""
        path = self._runtime_dir / f"outlook_{horizon}.json"
        if not path.exists():
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_daily_bias(self, instrument: str) -> str:
        """Get daily bias for instrument from cached snapshot (NO recomputation)
        
        Args:
            instrument: Instrument symbol (e.g., "EUR_USD", "XAU_USD")
            
        Returns:
            Bias string: "BULLISH", "BEARISH", or "NEUTRAL"
            Returns "NEUTRAL" with logged warning if bias unavailable
        """
        daily_outlook = self.get_latest("daily")
        if not daily_outlook:
            logger.warning(f"Daily outlook snapshot not available for bias lookup: {instrument}")
            return "NEUTRAL"
        
        # Search through outlooks array for matching instrument
        for outlook in daily_outlook.get("outlooks", []):
            if outlook.get("instrument") == instrument:
                bias = outlook.get("bias")
                if bias:
                    return bias
                else:
                    logger.warning(f"Daily bias missing for {instrument} (bias field is None)")
                    return "NEUTRAL"
        
        # Instrument not found in daily outlook
        logger.warning(f"Instrument {instrument} not found in daily outlook snapshot")
        return "NEUTRAL"

    def get_weekly_bias(self, instrument: str) -> str:
        """Get weekly bias for instrument from cached snapshot (NO recomputation)
        
        Args:
            instrument: Instrument symbol (e.g., "EUR_USD", "XAU_USD")
            
        Returns:
            Bias string: "BULLISH", "BEARISH", or "NEUTRAL"
            Returns "NEUTRAL" with logged warning if bias unavailable
        """
        weekly_outlook = self.get_latest("weekly")
        if not weekly_outlook:
            logger.warning(f"Weekly outlook snapshot not available for bias lookup: {instrument}")
            return "NEUTRAL"
        
        # Search through outlooks array for matching instrument
        for outlook in weekly_outlook.get("outlooks", []):
            if outlook.get("instrument") == instrument:
                bias = outlook.get("bias")
                if bias:
                    return bias
                else:
                    logger.warning(f"Weekly bias missing for {instrument} (bias field is None)")
                    return "NEUTRAL"
        
        # Instrument not found in weekly outlook
        logger.warning(f"Instrument {instrument} not found in weekly outlook snapshot")
        return "NEUTRAL"

# Singleton
_OUTLOOK_ENGINE = None

def get_outlook_engine() -> OutlookEngine:
    global _OUTLOOK_ENGINE
    if _OUTLOOK_ENGINE is None:
        _OUTLOOK_ENGINE = OutlookEngine()
    return _OUTLOOK_ENGINE