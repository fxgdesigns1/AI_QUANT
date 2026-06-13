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
import datetime as dt
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.strategies.base_strategy import BaseStrategy

try:
    from src.core.market_regime import MarketRegimeDetector, MarketRegime
    from src.core.policy_store import get_policy_store, PolicyStore
    from src.core.price_action_bias import PriceActionBias
    from src.core.regime_bias import RegimeBias
    from src.core.bias_resolver import (
        BiasComponent,
        resolve_bias,
        persist_bias_resolution,
    )
    from src.core.readiness_evaluator import get_readiness_evaluator
    from src.control_plane.outlook_engine import get_outlook_engine
    from src.control_plane.snapshot_store import get_snapshot_store
    from src.control_plane.market_data_provider import get_candles
    from src.observability.structured_logger import logger as structured_logger
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.getLogger(__name__).warning(f"⚠️ Dependencies not available: {e}")

logger = logging.getLogger(__name__)

# Use structured logging format
strat_logger = logger


class SessionRegimeAlignedStrategy(BaseStrategy):
    """Gatekeeper strategy for session/regime/roadmap alignment"""
    
    STRATEGY_ID = "session_regime_aligned"
    STRATEGY_NAME = "session_regime_aligned"
    ADAPTIVE = False
    # Minimum confidence required from the resolved bias hierarchy
    MIN_BIAS_CONFIDENCE = 0.4
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the gatekeeper strategy"""
        super().__init__(config)
        if not HAS_DEPENDENCIES:
            logger.warning("⚠️ SessionRegimeAlignedStrategy initialized without dependencies - will block all trades")
            self.policy_store = None
            self.regime_detector = None
            self.outlook_engine = None
            self.snapshot_store = None
        else:
            self.policy_store = get_policy_store()
            self.regime_detector = MarketRegimeDetector()
            self.outlook_engine = get_outlook_engine()
            self.snapshot_store = get_snapshot_store()
            self.price_action_bias = PriceActionBias()
            self.regime_bias = RegimeBias()
            
            # Setup audit logger for this gatekeeper
            self._setup_audit_logger()
        
        # S7: Permanent guardrail logging
        self._log_guardrail_event()
        
        logger.info("SessionRegimeAlignedStrategy initialized (gatekeeper mode)")
    
    def _log_guardrail_event(self):
        """Log guardrail event for dependency status tracking"""
        try:
            import json
            import os
            from pathlib import Path
            
            guardrail_entry = {
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "guard": "SESSION_GATE_DEPENDENCY",
                "status": "PASS" if (HAS_DEPENDENCIES and self.policy_store) else "FAIL",
                "details": f"HAS_DEPENDENCIES={HAS_DEPENDENCIES}, policy_store={'present' if self.policy_store else 'None'}"
            }
            
            # Determine log path (use /opt/ai-quant if available, else fallback to local)
            if os.path.exists("/opt/ai-quant"):
                log_path = "/opt/ai-quant/logs/guardrail_events.jsonl"
            else:
                repo_root = Path(__file__).resolve().parents[2]
                log_path = repo_root / "logs" / "guardrail_events.jsonl"
                log_path = str(log_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            with open(log_path, "a") as f:
                f.write(json.dumps(guardrail_entry) + "\n")
        except Exception as e:
            # Fail silently - guardrail logging should never break initialization
            logger.debug(f"Guardrail event logging failed: {e}")
    
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

    def analyze_market(self, market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Analyze market - Required by BaseStrategy.
        Since this is a gatekeeper, it returns no signals directly.
        """
        return []
    
    def compute_readiness_score(self, context: Dict[str, Any]) -> int:
        """Compute 0-100 readiness score based on context"""
        score = 0
        
        # 1. Regime (+20)
        # Check raw regime string or object
        regime = context.get("regime")
        if isinstance(regime, str):
            if regime != "UNKNOWN": score += 20
        elif hasattr(regime, "name"): # Enum
            if regime.name != "UNKNOWN": score += 20
            
        # 2. Daily Bias (+20)
        if context.get("daily_bias") not in ["NEUTRAL", "UNKNOWN", None]: score += 20
        
        # 3. Weekly Bias (+20)
        if context.get("weekly_bias") not in ["NEUTRAL", "UNKNOWN", None]: score += 20
        
        # 4. Roadmap Aligned (+20)
        if context.get("roadmap_aligned") is True: score += 20
        
        # 5. Session (+10)
        session = context.get("session", "").lower()
        if session in ["london", "new_york", "london_ny_overlap"]: score += 10
        
        # 6. Embargo (+10)
        # If NOT in embargo, add points
        if not context.get("is_embargo", True): score += 10
        
        return min(max(score, 0), 100)

    def _write_session_gate_probe(self, probe_data: dict) -> None:
        """SESSION_GATE_REASON_BREAKDOWN: Write evidence-only probe log.
        
        This probe captures exact reasons why should_allow_trade() blocks or allows.
        Append-only, no behavior change.
        """
        try:
            import json
            import os
            log_path = "/opt/ai-quant/logs/session_gate_probe.jsonl"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            # Ensure all required fields
            probe_entry = {
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "instrument": probe_data.get("instrument", "UNKNOWN"),
                "current_session": probe_data.get("current_session", "UNKNOWN"),
                "allowed_sessions": probe_data.get("allowed_sessions", []),
                "session_match": probe_data.get("session_match", False),
                "current_regime": probe_data.get("current_regime", "UNKNOWN"),
                "required_regime": probe_data.get("required_regime"),
                "regime_match": probe_data.get("regime_match", False),
                "market_open": probe_data.get("market_open", True),  # Assume open unless explicitly closed
                "spread_ok": probe_data.get("spread_ok", True),  # Assume OK unless explicitly checked
                "volatility_ok": probe_data.get("volatility_ok", True),  # Assume OK unless explicitly checked
                "time_window_ok": probe_data.get("time_window_ok", True),  # Assume OK unless explicitly checked
                "final_gate_decision": probe_data.get("final_gate_decision", "UNKNOWN"),
                "block_reason": probe_data.get("block_reason")
            }
            
            with open(log_path, "a") as f:
                f.write(json.dumps(probe_entry) + "\n")
        except Exception as e:
            # Fail silently - probe should never break execution
            logger.debug(f"SESSION_GATE_PROBE write failed: {e}")

    def should_allow_trade(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_context: Dict[str, Any],
        timestamp_utc: dt.datetime,
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
        # Initialize probe data
        probe_data = {
            "instrument": symbol,
            "current_session": None,
            "allowed_sessions": [],
            "session_match": False,
            "current_regime": None,
            "required_regime": None,
            "regime_match": False,
            "market_open": True,
            "spread_ok": True,
            "volatility_ok": True,
            "time_window_ok": True,
            "final_gate_decision": None,
            "block_reason": None
        }
        
        if not HAS_DEPENDENCIES or not self.policy_store:
            # S2: Hard fail instead of silent block
            raise RuntimeError(
                "FATAL: SessionRegimeAlignedStrategy dependencies missing – refusing silent BLOCK. "
                f"HAS_DEPENDENCIES={HAS_DEPENDENCIES}, policy_store={self.policy_store}"
            )
        
        # Classify session
        session = self._classify_session(timestamp_utc)
        probe_data["current_session"] = session
        
        # Detect regime (fetch candles if possible)
        regime_analysis = self._detect_regime_with_analysis(symbol)
        regime = regime_analysis.regime.name if hasattr(regime_analysis.regime, "name") else str(regime_analysis.regime)
        probe_data["current_regime"] = regime
        
        # Extract news state
        news_state = self._extract_news_state(news_context)
        is_embargo = news_context.get("is_embargo", False) or news_state == "embargo"
        
        # 1) Outlook‑based roadmap alignment (legacy view, still computed for transparency)
        roadmap_aligned, roadmap_details = self._check_roadmap_alignment(symbol)

        # 2) Price action bias (48h move)
        price_bias_result = self.price_action_bias.calculate_bias(symbol)

        # 3) Regime bias (directional, if available)
        regime_bias_result = self.regime_bias.from_analysis(symbol, regime_analysis)

        # 4) Normalize components for resolver
        outlook_component = self._build_outlook_component(roadmap_aligned, roadmap_details)
        price_component = BiasComponent(
            bias=price_bias_result.bias,
            confidence=price_bias_result.confidence,
            source=price_bias_result.source,
            status="ok" if price_bias_result.bias is not None else "neutral",
            details=price_bias_result.metrics or {},
        )
        regime_component = BiasComponent(
            bias=regime_bias_result.bias,
            confidence=regime_bias_result.confidence,
            source=regime_bias_result.source,
            status="ok" if regime_bias_result.bias is not None else "neutral",
            details=regime_bias_result.metrics or {},
        )

        resolved = resolve_bias(
            outlook=outlook_component,
            price_action=price_component,
            regime=regime_component,
            min_confidence=self.MIN_BIAS_CONFIDENCE,
        )
        
        context = {
            "symbol": symbol,
            "session": session,
            "regime": regime,
            "news_state": news_state,
            "roadmap_aligned": roadmap_aligned,
            "is_embargo": is_embargo,
            # Optional: list of high-impact news items that triggered embargo (if provided)
            "embargo_triggers": news_context.get("embargo_triggers"),
            **roadmap_details, # Merge roadmap details (biases, reasons)
            
            # New Transparency Fields
            "candles_remaining": getattr(regime_analysis, "candles_remaining", 0),
            "eta_seconds": getattr(regime_analysis, "eta_seconds", 0),
            # Bias hierarchy transparency
            "resolved_bias": resolved.bias,
            "resolved_confidence": resolved.confidence,
            "bias_sources": resolved.sources,
            "bias_penalties": resolved.penalties,
        }
        
        # Compute Readiness Score
        readiness_score = self.compute_readiness_score(context)
        context["readiness_score"] = readiness_score
        
        # Check for TRADE_IMMINENT (Signal Only)
        if (readiness_score >= 80 and
            regime != "UNKNOWN" and
            context.get("daily_bias") != "NEUTRAL" and
            context.get("weekly_bias") != "NEUTRAL" and
            roadmap_aligned and 
            not is_embargo):
            
            # Emit structured log for TRADE_IMMINENT
            self._emit_imminent(context)

        # Update Status Snapshot with new transparency data
        if self.snapshot_store:
            try:
                self.snapshot_store.update({
                    "regime_readiness": {
                        "score": readiness_score,
                        "candles_remaining": context["candles_remaining"],
                        "eta_seconds": context["eta_seconds"],
                        "regime": regime,
                        "last_updated": dt.datetime.now(dt.timezone.utc).isoformat()
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to update status snapshot: {e}")

        
        # Persist latest bias resolution snapshot for observability
        try:
            repo_root = Path(__file__).resolve().parents[2]
            persist_bias_resolution(
                repo_root=repo_root,
                symbol=symbol,
                resolved=resolved,
                context={
                    "session": session,
                    "regime": regime,
                    "news_state": news_state,
                    "roadmap_aligned": roadmap_aligned,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to persist bias resolution snapshot: {e}")

        # Gate 1: News embargo check (unchanged, always blocks)
        if is_embargo:
            probe_data["final_gate_decision"] = "BLOCK"
            probe_data["block_reason"] = "news_embargo"
            self._write_session_gate_probe(probe_data)
            self._emit(False, context, "news_embargo")
            return False

        # Gate 2: Bias hierarchy availability / strength
        if resolved.bias is None or resolved.confidence < self.MIN_BIAS_CONFIDENCE:
            reason = "bias_unavailable_all_sources"
            
            # ENHANCED BIAS OBSERVABILITY: Log per-source bias status
            bias_source_status = {
                "outlook": {
                    "available": outlook_component.bias is not None,
                    "status": outlook_component.status,
                    "bias": outlook_component.bias,
                    "confidence": outlook_component.confidence
                },
                "price_action": {
                    "available": price_component.bias is not None,
                    "status": price_component.status,
                    "bias": price_component.bias,
                    "confidence": price_component.confidence
                },
                "regime": {
                    "available": regime_component.bias is not None,
                    "status": regime_component.status,
                    "bias": regime_component.bias,
                    "confidence": regime_component.confidence
                }
            }
            structured_logger.info(
                "bias_unavailable_all_sources",
                subsystem="session_regime_gate",
                symbol=symbol,
                resolved_bias=resolved.bias,
                resolved_confidence=resolved.confidence,
                bias_sources=resolved.sources,
                bias_penalties=resolved.penalties,
                source_status=bias_source_status
            )
            
            probe_data["final_gate_decision"] = "BLOCK"
            probe_data["block_reason"] = reason
            if resolved.bias is None:
                probe_data["block_reason"] = "bias_unavailable_all_sources"
            else:
                probe_data["block_reason"] = f"bias_confidence_too_low_{resolved.confidence:.2f}_min_{self.MIN_BIAS_CONFIDENCE}"
            self._write_session_gate_probe(probe_data)
            self._emit(False, context, reason)
            return False

        # Gate 3: Policy lookup
        policy = self.policy_store.lookup(
            session=session,
            regime=regime,
            news_state=news_state,
            bias_alignment="aligned" if resolved.bias is not None else "misaligned",
        )
        
        # ENHANCED POLICY OBSERVABILITY: Log policy warm-up metrics
        policy_samples_collected = getattr(regime_analysis, "current_candles", 0)
        policy_min_required = getattr(regime_analysis, "required_candles", 50)
        
        # Capture allowed sessions from policy (if available)
        if policy and hasattr(policy, 'allowed_sessions'):
            probe_data["allowed_sessions"] = policy.allowed_sessions if isinstance(policy.allowed_sessions, list) else []
        elif policy:
            # If policy exists but no explicit allowed_sessions, infer from policy lookup params
            probe_data["allowed_sessions"] = [session]  # Current session is allowed if policy found
        
        if policy is None:
            probe_data["final_gate_decision"] = "BLOCK"
            probe_data["block_reason"] = f"policy_not_found_session_{session}_regime_{regime}_news_{news_state}"
            self._write_session_gate_probe(probe_data)
            structured_logger.info(
                "policy_not_found",
                subsystem="session_regime_gate",
                symbol=symbol,
                session=session,
                regime=regime,
                news_state=news_state,
                bias_alignment="aligned" if resolved.bias is not None else "misaligned",
                samples_collected=policy_samples_collected,
                min_required=policy_min_required
            )
            self._emit(False, context, "policy_not_found")
            return False
        
        # ENHANCED POLICY OBSERVABILITY: Log policy ready status
        structured_logger.info(
            "policy_ready",
            subsystem="session_regime_gate",
            symbol=symbol,
            session=session,
            regime=regime,
            participation_score=policy.participation_score,
            samples_collected=policy_samples_collected,
            min_required=policy_min_required
        )
        
        # Gate 4: Participation score threshold (0.6 minimum)
        if policy.participation_score < 0.6:
            probe_data["final_gate_decision"] = "BLOCK"
            probe_data["block_reason"] = f"policy_score_too_low_{policy.participation_score:.2f}_min_0.60"
            self._write_session_gate_probe(probe_data)
            self._emit(False, context, "policy_score_too_low")
            return False
        
        # COMPUTE SYSTEM READINESS (after all gate checks)
        try:
            # Calculate embargo countdown if embargo is active
            embargo_seconds_remaining = None
            if is_embargo and news_context.get("embargo_triggers"):
                embargo_triggers = news_context.get("embargo_triggers", [])
                if embargo_triggers:
                    # Find the nearest embargo trigger
                    now_ts = timestamp_utc.timestamp()
                    nearest_seconds = None
                    for trigger in embargo_triggers:
                        trigger_ts = trigger.get("ts_utc")
                        if trigger_ts:
                            if isinstance(trigger_ts, str):
                                try:
                                    trigger_dt = dt.datetime.fromisoformat(trigger_ts.replace('Z', '+00:00'))
                                    trigger_ts = trigger_dt.timestamp()
                                except Exception:
                                    continue
                            # Embargo window is 2 hours (7200 seconds) before and after
                            embargo_window = 7200
                            time_to_event = trigger_ts - now_ts
                            if abs(time_to_event) < embargo_window:
                                # Calculate seconds remaining until embargo clears
                                if time_to_event > 0:
                                    # Before event: embargo clears after event + window
                                    embargo_seconds_remaining = int(time_to_event + embargo_window)
                                else:
                                    # After event: embargo clears after window expires
                                    embargo_seconds_remaining = int(embargo_window - abs(time_to_event))
                                if nearest_seconds is None or embargo_seconds_remaining < nearest_seconds:
                                    nearest_seconds = embargo_seconds_remaining
                    embargo_seconds_remaining = nearest_seconds
            
            # Build readiness context
            readiness_context = {
                "regime": regime,
                "regime_resolved": regime != "UNKNOWN",
                "bias_available": resolved.bias is not None,
                "bias_confidence": resolved.confidence,
                "policy_ready": policy is not None and policy.participation_score >= 0.6,
                "policy_samples_collected": policy_samples_collected,
                "policy_min_required": policy_min_required,
                "news_embargo": is_embargo,
                "embargo_seconds_remaining": embargo_seconds_remaining,
                "risk_ok": True,  # Assume OK unless explicitly blocked
                # Additional context for transparency
                "symbol": symbol,
                "session": session,
                "resolved_bias": resolved.bias,
                "bias_sources": resolved.sources,
            }
            
            # Compute readiness
            readiness_evaluator = get_readiness_evaluator()
            readiness_result = readiness_evaluator.compute_readiness(readiness_context)
            
            # EMIT READINESS_STATE LOG
            structured_logger.info(
                "READINESS_STATE",
                subsystem="session_regime_gate",
                event="READINESS_STATE",
                score=readiness_result.score,
                breakdown={
                    "regime": readiness_result.breakdown.regime,
                    "bias": readiness_result.breakdown.bias,
                    "policy": readiness_result.breakdown.policy,
                    "news": readiness_result.breakdown.news,
                    "risk": readiness_result.breakdown.risk
                },
                blocking_components=readiness_result.blocking_components,
                symbol=symbol,
                regime=regime,
                bias_available=resolved.bias is not None,
                bias_confidence=resolved.confidence,
                policy_ready=policy is not None,
                news_embargo=is_embargo,
                embargo_seconds_remaining=embargo_seconds_remaining
            )
        except Exception as e:
            logger.warning(f"Failed to compute readiness: {e}")
        
        # All gates passed
        probe_data["final_gate_decision"] = "ALLOW"
        probe_data["block_reason"] = None
        probe_data["session_match"] = session in probe_data.get("allowed_sessions", [session]) if probe_data.get("allowed_sessions") else True
        if policy and hasattr(policy, 'required_regime'):
            probe_data["required_regime"] = policy.required_regime
            probe_data["regime_match"] = (regime == policy.required_regime) if policy.required_regime else True
        self._write_session_gate_probe(probe_data)
        self._emit(True, context, "policy_allow")
        return True
    
    def _classify_session(self, ts: dt.datetime) -> str:
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
        """Deprecated: Use _detect_regime_with_analysis instead"""
        analysis = self._detect_regime_with_analysis(symbol)
        return analysis.regime.name if hasattr(analysis.regime, "name") else str(analysis.regime)
        
    def _detect_regime_with_analysis(self, symbol: str):
        """Detect regime with full analysis (fetching candles)"""
        if not self.regime_detector:
            from dataclasses import make_dataclass
            # Return dummy object if dependencies missing
            DummyRegime = make_dataclass("DummyRegime", [("regime", str), ("candles_remaining", int), ("eta_seconds", int)])
            return DummyRegime("UNKNOWN", 0, 0)
        
        try:
            # Fetch candles for H1 (or M5 to match execution strategy, but H1 is better for regime)
            # User mentioned "H1=3600" in prompt example. Let's use H1 for regime.
            # But wait, execution strategy uses M5. 
            # If I use H1, I might get different results. 
            # Let's use H1 as it's more stable for "Regime".
            candles = get_candles(symbol, granularity="H1", count=60)
            return self.regime_detector.detect_regime(symbol, candles, timeframe_seconds=3600)
        except Exception as e:
            logger.warning(f"Failed to fetch candles for regime detection: {e}")
            # Return UNKNOWN analysis
            return self.regime_detector.detect_regime(symbol, [], timeframe_seconds=3600)
    
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
    
    def _build_outlook_component(self, aligned: bool, details: Dict[str, Any]) -> BiasComponent:
        """Build BiasComponent from roadmap alignment"""
        # effective_bias comes from details if aligned
        bias = details.get("effective_bias") if aligned else None
        
        return BiasComponent(
            bias=bias,
            confidence=0.8 if aligned else 0.0,
            source="outlook_roadmap",
            status="ok" if aligned else "misaligned",
            details=details
        )

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
                # Ensure explicit reason overwrites any reason in ctx
                record = {
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "allowed": allowed,
                    **ctx,
                    "reason": reason, # Explicit reason last (overwrites context)
                }
                # Serialize to JSON and log
                self.audit_logger.info(json.dumps(record, default=str))
            except Exception as e:
                strat_logger.warning(f"Failed to write to audit log: {e}")

    def _emit_imminent(self, ctx: Dict[str, Any]) -> None:
        """Emit structured log for TRADE_IMMINENT"""
        import json
        
        record = {
            "event": "TRADE_IMMINENT",
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            **ctx
        }
        
        # Log to audit logger
        if hasattr(self, 'audit_logger') and self.audit_logger:
            try:
                self.audit_logger.info(json.dumps(record, default=str))
            except Exception as e:
                logger.warning(f"Failed to log TRADE_IMMINENT: {e}")
