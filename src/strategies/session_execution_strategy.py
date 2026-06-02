"""Session Execution Strategy - Hybrid Direction Logic (Phase 2)

This strategy executes trades ONLY during:
- London session (6-12 UTC)
- London-NY overlap (12-16 UTC)

And ONLY when:
- News embargo is not active
- Roadmap is aligned (Daily/Weekly/Monthly biases match)
- Market regime is TRENDING
- EMA structure confirms Roadmap bias

HARD BOUND: Routes orders ONLY to account suffix 006.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

try:
    from src.strategies.momentum_trading import TradeSignal, TradeSide
    from src.strategies.indicators import calculate_ema as ema
    from src.core.market_regime import MarketRegime, MarketRegimeDetector
    from src.control_plane.outlook_engine import get_outlook_engine
    from src.control_plane.market_data_provider import get_candles
    from src.core.audit_logger import append_audit
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.getLogger(__name__).warning(f"⚠️ Dependencies not available: {e}")

logger = logging.getLogger(__name__)

class SessionExecutionStrategy:
    """Session-based execution strategy for account 006 with Hybrid Direction Logic"""
    
    STRATEGY_NAME = "session_execution"
    ACCOUNT_SUFFIX = "006"  # HARD BIND
    ADAPTIVE = False
    
    def __init__(self):
        """Initialize the session execution strategy"""
        self.ready = False
        if HAS_DEPENDENCIES:
            try:
                self.outlook_engine = get_outlook_engine()
                self.regime_detector = MarketRegimeDetector()
                
                # Verify they are not None
                if self.outlook_engine and self.regime_detector:
                    self.ready = True
                    logger.info(f"SessionExecutionStrategy initialized (bound to account {self.ACCOUNT_SUFFIX}) - READY")
                else:
                    logger.warning("SessionExecutionStrategy dependencies returned None")
                    self.outlook_engine = None
                    self.regime_detector = None
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize dependencies: {e}")
                self.outlook_engine = None
                self.regime_detector = None
        else:
            self.outlook_engine = None
            self.regime_detector = None
            logger.warning("SessionExecutionStrategy initialized without dependencies (HAS_DEPENDENCIES=False)")
    
    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Analyze market and generate signals based on session/regime/roadmap alignment.
        """
        if not self.ready:
            return []
            
        signals = []
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        # Session filter: London + London-NY overlap only (6-16 UTC)
        session_ok = 6 <= hour < 16
        if not session_ok:
            # We don't audit every tick outside session to avoid log spam, 
            # unless we want to track why it's silent.
            # But the prompt audit implies checking per scan.
            # We'll log only if debug enabled or throttle.
            pass
            
        # We iterate instruments to audit each relevant one
        for symbol, price_data in market_data.items():
            try:
                # 1. Session Check
                if not session_ok:
                    self._audit(symbol, False, "outside_session", None, None)
                    continue

                # 2. News Embargo Check
                is_embargo = False
                if news_data:
                    is_embargo = news_data.get("is_embargo", False) or news_data.get("state") == "embargo"
                
                if is_embargo:
                    self._audit(symbol, False, "news_embargo", None, None)
                    continue

                # 3. Roadmap Alignment Check
                is_aligned, daily_bias, roadmap_data = self._check_roadmap_alignment(symbol)
                if not is_aligned:
                    self._audit(symbol, False, "roadmap_misaligned", roadmap_data, None)
                    continue

                # 4. Fetch Candles & Regime Check
                # Need candles for both Regime and EMA
                try:
                    candles = get_candles(symbol, granularity="M5", count=200) # Need 200 for EMA200
                except Exception as e:
                    logger.debug(f"Could not fetch candles for {symbol}: {e}")
                    continue

                regime_analysis = self.regime_detector.detect_regime(symbol, candles)
                market_regime = regime_analysis.regime
                
                if market_regime != MarketRegime.TRENDING:
                    self._audit(symbol, False, "regime_not_trending", roadmap_data, str(market_regime))
                    continue

                # 5. Hybrid Direction Logic (EMA structure)
                direction = self._determine_direction(candles, daily_bias)
                if direction is None:
                    self._audit(symbol, False, "direction_unclear", roadmap_data, str(market_regime))
                    continue

                # 6. Generate Signal
                entry_price = float(price_data.ask) if direction == TradeSide.BUY else float(price_data.bid)
                
                # Dynamic SL/TP based on direction
                if direction == TradeSide.BUY:
                    stop_loss = entry_price * 0.998  # 0.2% SL
                    take_profit = entry_price * 1.004  # 0.4% TP (1:2 R:R)
                else:
                    stop_loss = entry_price * 1.002  # 0.2% SL
                    take_profit = entry_price * 0.996  # 0.4% TP
                
                signal = TradeSignal(
                    instrument=symbol,
                    side=direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'strategy': self.STRATEGY_NAME,
                        'account_suffix': self.ACCOUNT_SUFFIX,
                        'session': 'london' if hour < 12 else 'london_ny_overlap',
                        'hour_utc': hour,
                        'regime': str(market_regime),
                        'roadmap_bias': daily_bias
                    }
                )
                
                self._audit(symbol, True, f"enter_{direction.value}", roadmap_data, str(market_regime))
                signals.append(signal)
                logger.info(f"📊 SessionExecutionStrategy: Signal generated for {symbol} ({direction.value})")
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
                
        return signals

    def _determine_direction(self, candles: List[Any], daily_bias: str) -> Optional[TradeSide]:
        """Determine direction based on EMA structure and Roadmap Bias"""
        closes = [c.c for c in candles]
        if len(closes) < 200:
            return None
            
        ema_fast = ema(closes, period=50)
        ema_slow = ema(closes, period=200)

        if ema_fast is None or ema_slow is None:
            return None

        # Hybrid Rule: Bias + Structure
        if daily_bias == "BULLISH" and ema_fast > ema_slow:
            return TradeSide.BUY

        if daily_bias == "BEARISH" and ema_fast < ema_slow:
            return TradeSide.SELL

        return None

    def _check_roadmap_alignment(self, symbol: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Check roadmap alignment and return (is_aligned, daily_bias, audit_data)"""
        if not self.outlook_engine:
            return False, None, {}

        try:
            daily_outlook = self.outlook_engine.get_latest("daily")
            weekly_outlook = self.outlook_engine.get_latest("weekly")
            monthly_outlook = self.outlook_engine.get_latest("monthly")
            
            if not (daily_outlook and weekly_outlook):
                return False, None, {}

            biases = {}
            for horizon, data in [("daily", daily_outlook), ("weekly", weekly_outlook)]:
                for outlook in data.get("outlooks", []):
                    if outlook.get("instrument") == symbol:
                        biases[horizon] = {
                            "bias": outlook.get("bias", "NEUTRAL"),
                            "reason": outlook.get("bias_reason", "unknown")
                        }
                        break
                if horizon not in biases:
                    return False, None, {} # Missing bias for horizon

            daily = biases["daily"]["bias"]
            daily_reason = biases["daily"]["reason"]
            weekly = biases["weekly"]["bias"]
            weekly_reason = biases["weekly"]["reason"]
            
            # Monthly is context only, not required for alignment
            monthly = None
            if monthly_outlook:
                for outlook in monthly_outlook.get("outlooks", []):
                    if outlook.get("instrument") == symbol:
                        monthly = outlook.get("bias", "NEUTRAL")
                        break
            
            # STRICT ALIGNMENT REQUIRED: Both daily AND weekly must be directional and aligned.
            # 
            # SAFETY RULE: Daily bias MUST be BULLISH or BEARISH (not NEUTRAL).
            # This ensures we only trade when there's clear directional momentum on BOTH timeframes.
            #
            # Rules:
            # - Daily MUST be BULLISH or BEARISH (NEUTRAL blocks trading)
            # - Weekly MUST be BULLISH or BEARISH (NEUTRAL blocks trading)
            # - Daily and weekly MUST match (both BULLISH or both BEARISH)
            # - All other combinations block trading (fail-closed for safety)
            
            # Check that both are directional (not NEUTRAL)
            if daily == "NEUTRAL" or weekly == "NEUTRAL":
                return False, None, {
                    "daily_bias": daily,
                    "daily_reason": daily_reason,
                    "weekly_bias": weekly,
                    "weekly_reason": weekly_reason,
                    "monthly_bias": monthly,
                    "reason": "daily_or_weekly_neutral"
                }
            
            # Check that they align (same direction)
            if daily == weekly:
                return True, daily, {
                    "daily_bias": daily,
                    "daily_reason": daily_reason,
                    "weekly_bias": weekly,
                    "weekly_reason": weekly_reason,
                    "monthly_bias": monthly,
                    "effective_bias": daily
                }
            else:
                # Misaligned (e.g., daily BULLISH / weekly BEARISH)
                return False, None, {
                    "daily_bias": daily,
                    "daily_reason": daily_reason,
                    "weekly_bias": weekly,
                    "weekly_reason": weekly_reason,
                    "monthly_bias": monthly,
                    "reason": "daily_weekly_misaligned"
                }
            
        except Exception:
            return False, None, {}

    def _audit(self, symbol, allowed, reason, roadmap_data, regime):
        """Audit log helper"""
        event = {
            "strategy": self.STRATEGY_NAME,
            "symbol": symbol,
            "allowed": allowed,
            "reason": reason,
            "regime": regime
        }
        if roadmap_data:
            event.update(roadmap_data)
            
        append_audit(event)
