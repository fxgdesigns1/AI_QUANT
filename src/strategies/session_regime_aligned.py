"""Session Regime Aligned Strategy - Gatekeeper for trade execution

This strategy acts as a gatekeeper, checking:
1. Session classification (Asia, London, London-NY overlap, NY, Transition)
2. Market regime alignment (TRENDING, RANGING, CHOPPY)
3. News state (normal, elevated, embargo)
4. Roadmap alignment (daily/weekly/monthly bias alignment)

FAIL-CLOSED: If any check fails, trading is blocked.
READ-ONLY: No execution side effects.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.policy_store import get_policy_store, PolicyStore
    from src.control_plane.outlook_engine import get_outlook_engine
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.getLogger(__name__).warning(f"⚠️ Dependencies not available: {e}")

logger = logging.getLogger(__name__)

# Use structured logging format
strat_logger = logger


class SessionRegimeAlignedStrategy:
    """Gatekeeper strategy for session/regime/roadmap alignment"""
    
    STRATEGY_NAME = "session_regime_aligned"
    ADAPTIVE = False
    
    def __init__(self):
        """Initialize the gatekeeper strategy"""
        if not HAS_DEPENDENCIES:
            logger.warning("⚠️ SessionRegimeAlignedStrategy initialized without dependencies - will block all trades")
            self.policy_store = None
            self.regime_detector = None
            self.outlook_engine = None
        else:
            self.policy_store = get_policy_store()
            self.regime_detector = MarketRegimeDetector()
            self.outlook_engine = get_outlook_engine()
            
            # Setup audit logger for this gatekeeper
            self._setup_audit_logger()
        
        logger.info("SessionRegimeAlignedStrategy initialized (gatekeeper mode)")
    
    def _setup_audit_logger(self):
        """Setup JSONL audit logger for gate decisions"""
        import os
        from pathlib import Path
        import logging
        
        try:
            repo_root = Path(__file__).resolve().parents[2]
            logs_dir = repo_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_file = logs_dir / "session_regime_gate_audit.jsonl"
            
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            
            # Configure a separate logger that doesn't propagate to root
            self.audit_logger = logging.getLogger("session_regime_gate_audit")
            self.audit_logger.setLevel(logging.INFO)
            self.audit_logger.addHandler(handler)
            self.audit_logger.propagate = False
            
        except Exception as e:
            logger.warning(f"Failed to setup audit logger: {e}")
            self.audit_logger = None
    
    def should_allow_trade(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_context: Dict[str, Any],
        timestamp_utc: datetime,
    ) -> bool:
        """Check if trade should be allowed based on session/regime/roadmap alignment
        
        Args:
            symbol: Trading instrument (e.g., "EUR_USD")
            market_data: Market data dict (must contain Price objects)
            news_context: News context dict with 'state', 'is_embargo', etc.
            timestamp_utc: Current UTC timestamp
            
        Returns:
            True if trade allowed, False if blocked
        """
        if not HAS_DEPENDENCIES or not self.policy_store:
            self._emit(False, {"symbol": symbol, "reason": "dependencies_missing"}, "dependencies_missing")
            return False
        
        # Classify session
        session = self._classify_session(timestamp_utc)
        
        # Detect regime (requires candles - simplified for now)
        regime = self._detect_regime_simple(symbol, market_data)
        
        # Extract news state
        news_state = self._extract_news_state(news_context)
        is_embargo = news_context.get("is_embargo", False) or news_state == "embargo"
        
        # Check roadmap alignment
        roadmap_aligned, roadmap_details = self._check_roadmap_alignment(symbol)
        
        context = {
            "symbol": symbol,
            "session": session,
            "regime": regime,
            "news_state": news_state,
            "roadmap_aligned": roadmap_aligned,
            "is_embargo": is_embargo,
            # Optional: list of high-impact news items that triggered embargo (if provided)
            "embargo_triggers": news_context.get("embargo_triggers"),
            **roadmap_details # Merge roadmap details (biases, reasons)
        }
        
        # Gate 1: News embargo check
        if is_embargo:
            self._emit(False, context, "news_embargo")
            return False
        
        # Gate 2: Roadmap alignment check
        if not roadmap_aligned:
            reason = roadmap_details.get("reason", "roadmap_misaligned")
            self._emit(False, context, reason)
            return False
        
        # Gate 3: Policy lookup
        policy = self.policy_store.lookup(
            session=session,
            regime=regime,
            news_state=news_state,
            bias_alignment="aligned" if roadmap_aligned else "misaligned",
        )
        
        if policy is None:
            self._emit(False, context, "policy_not_found")
            return False
        
        # Gate 4: Participation score threshold (0.6 minimum)
        if policy.participation_score < 0.6:
            self._emit(False, context, "policy_score_too_low")
            return False
        
        # All gates passed
        self._emit(True, context, "policy_allow")
        return True
    
    def _classify_session(self, ts: datetime) -> str:
        """Classify trading session based on UTC hour
        
        Sessions:
        - asia: 22:00-05:59 UTC (Tokyo/Sydney)
        - london: 06:00-11:59 UTC
        - london_ny_overlap: 12:00-15:59 UTC
        - new_york: 16:00-20:59 UTC
        - transition: 21:00-21:59 UTC (wrap to next day)
        """
        h = ts.hour
        if h >= 22 or h < 6:
            return "asia"
        elif 6 <= h < 12:
            return "london"
        elif 12 <= h < 16:
            return "london_ny_overlap"
        elif 16 <= h < 21:
            return "new_york"
        else:
            return "transition"
    
    def _detect_regime_simple(self, symbol: str, market_data: Dict[str, Any]) -> str:
        """Simplified regime detection (requires candles for full detection)
        
        For now, returns UNKNOWN if candles not available.
        In production, would fetch candles and use regime_detector.detect_regime().
        """
        if not self.regime_detector:
            return "UNKNOWN"
        
        # Simplified: Without candles, we can't detect regime accurately
        # Return UNKNOWN which will likely block trading (fail-closed)
        # Full implementation would fetch candles here
        return "UNKNOWN"
    
    def _extract_news_state(self, news_context: Dict[str, Any]) -> str:
        """Extract news state from news context"""
        # Check for explicit embargo
        if news_context.get("is_embargo", False):
            return "embargo"
        
        # Check news state field
        state = news_context.get("state", "normal")
        
        # Map to policy store format
        if state in ("elevated", "high_volatility", "central_bank_event"):
            return "elevated"
        elif state in ("embargo", "blackout"):
            return "embargo"
        else:
            return "normal"
    
    def _check_roadmap_alignment(self, symbol: str) -> tuple[bool, dict]:
        """Check if daily/weekly/monthly biases are aligned
        
        Returns: (is_aligned, details_dict)
        """
        if not self.outlook_engine:
            # Without outlook engine, cannot verify alignment - fail closed
            return False, {"reason": "dependencies_missing"}
        
        try:
            # Get outlooks for the symbol
            daily_outlook = self.outlook_engine.get_latest("daily")
            weekly_outlook = self.outlook_engine.get_latest("weekly")
            monthly_outlook = self.outlook_engine.get_latest("monthly")
            
            if not (daily_outlook and weekly_outlook and monthly_outlook):
                # Missing outlooks - fail closed
                return False, {"reason": "outlooks_missing"}
            
            # Find instrument in each outlook
            biases = {}
            for horizon, data in [("daily", daily_outlook), ("weekly", weekly_outlook), ("monthly", monthly_outlook)]:
                for outlook in data.get("outlooks", []):
                    if outlook.get("instrument") == symbol:
                        biases[horizon] = {
                            "bias": outlook.get("bias", "NEUTRAL"),
                            "reason": outlook.get("bias_reason", "unknown")
                        }
                        break
                if horizon not in biases:
                    return False, {f"{horizon}_bias": "missing", "reason": f"{horizon}_outlook_missing_symbol"}

            daily = biases["daily"]["bias"]
            weekly = biases["weekly"]["bias"]
            monthly = biases["monthly"]["bias"]
            
            details = {
                "daily_bias": daily,
                "daily_reason": biases["daily"]["reason"],
                "weekly_bias": weekly,
                "weekly_reason": biases["weekly"]["reason"],
                "monthly_bias": monthly,
                "monthly_reason": biases["monthly"]["reason"]
            }
            
            # Check alignment: all must be BULLISH or all BEARISH (daily and weekly)
            # Monthly is context, but daily/weekly are required to match
            
            if daily == "NEUTRAL" or weekly == "NEUTRAL":
                details["reason"] = "daily_or_weekly_neutral"
                return False, details
            
            if daily == weekly:
                details["effective_bias"] = daily
                return True, details
            else:
                details["reason"] = "daily_weekly_misaligned"
                return False, details
            
        except Exception as e:
            logger.warning(f"Error checking roadmap alignment for {symbol}: {e}")
            return False, {"reason": f"error: {str(e)}"}
    
    def _emit(self, allowed: bool, ctx: Dict[str, Any], reason: str) -> None:
        """Emit structured log entry for gate decision"""
        import json
        
        # Log to standard logger
        strat_logger.info(
            "SESSION_REGIME_GATE",
            extra={
                "allowed": allowed,
                "reason": reason,
                **ctx,
            }
        )
        
        # Log to audit JSONL file
        if hasattr(self, 'audit_logger') and self.audit_logger:
            try:
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "allowed": allowed,
                    "reason": reason,
                    **ctx
                }
                # Serialize to JSON and log
                self.audit_logger.info(json.dumps(record, default=str))
            except Exception as e:
                strat_logger.warning(f"Failed to write to audit log: {e}")
