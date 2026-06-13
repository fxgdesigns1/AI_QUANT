"""
Strategy Readiness Evaluator - Read-Only Diagnostic Layer

Computes readiness score (0-100) and blocking reasons for each strategy.
AUTHORITATIVE TRUTH - NO MOCKS - READ-ONLY DIAGNOSTICS
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class BiasAlignment(Enum):
    """Bias alignment status"""
    ALIGNED = "ALIGNED"  # Daily and weekly match (both BULLISH or both BEARISH)
    CONFLICT = "CONFLICT"  # Daily and weekly conflict (one BULLISH, one BEARISH)
    NEUTRAL = "NEUTRAL"  # One or both are NEUTRAL
    MISSING = "MISSING"  # Bias data unavailable


@dataclass
class StrategyReadiness:
    """Strategy readiness evaluation result"""
    strategy_id: str
    instrument: str
    readiness_score: int  # 0-100
    blocking_reasons: List[str]
    bias_alignment: BiasAlignment
    estimated_time_to_entry_minutes: Optional[int]
    last_signal_ts: Optional[float]
    regime: str
    volatility_pct: float
    embargo_active: bool
    daily_bias: str
    weekly_bias: str
    execution_allowed: bool
    cooldown_remaining_minutes: Optional[int]
    signal_confidence: Optional[float]
    details: Dict[str, Any]


class StrategyReadinessEvaluator:
    """Evaluates strategy readiness for trading"""
    
    def __init__(self):
        """Initialize evaluator"""
        pass
    
    def compute_strategy_readiness(
        self,
        strategy_id: str,
        instrument: str,
        daily_bias: Optional[str] = None,
        weekly_bias: Optional[str] = None,
        regime: Optional[str] = None,
        volatility_pct: Optional[float] = None,
        news_embargo: bool = False,
        execution_allowed: bool = True,
        cooldown_remaining_minutes: Optional[int] = None,
        signal_confidence: Optional[float] = None,
        last_signal_ts: Optional[float] = None,
        **kwargs
    ) -> StrategyReadiness:
        """
        Compute readiness score and blocking reasons for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            instrument: Trading instrument
            daily_bias: Daily bias (BULLISH, BEARISH, NEUTRAL, or None)
            weekly_bias: Weekly bias (BULLISH, BEARISH, NEUTRAL, or None)
            regime: Market regime (TRENDING, RANGING, CHOPPY, SHOCK, or None)
            volatility_pct: Volatility percentage (ATR percentile or similar)
            news_embargo: Whether news embargo is active
            execution_allowed: Whether execution gate allows trading
            cooldown_remaining_minutes: Minutes remaining in cooldown period
            signal_confidence: Last signal confidence (0.0-1.0)
            last_signal_ts: Timestamp of last signal generated
            **kwargs: Additional context
        
        Returns:
            StrategyReadiness object with score and blocking reasons
        """
        # Normalize inputs
        daily_bias = (daily_bias or "NEUTRAL").upper()
        weekly_bias = (weekly_bias or "NEUTRAL").upper()
        regime = (regime or "UNKNOWN").upper()
        volatility_pct = volatility_pct or 0.0
        signal_confidence = signal_confidence or 0.0
        
        # Determine bias alignment
        bias_alignment = self._determine_bias_alignment(daily_bias, weekly_bias)
        
        # Initialize score and blocking reasons
        score = 0
        blocking_reasons = []
        
        # Scoring model
        # 1. Bias alignment (+30 aligned | -30 conflict | 0 neutral)
        if bias_alignment == BiasAlignment.ALIGNED:
            score += 30
        elif bias_alignment == BiasAlignment.CONFLICT:
            score -= 30
            blocking_reasons.append(f"Bias conflict: Daily {daily_bias}, Weekly {weekly_bias}")
        elif bias_alignment == BiasAlignment.MISSING:
            blocking_reasons.append("Bias data unavailable")
        
        # 2. Regime trending (+20)
        if regime == "TRENDING":
            score += 20
        elif regime == "SHOCK":
            score -= 20
            blocking_reasons.append(f"Regime SHOCK detected")
        elif regime == "RANGING":
            blocking_reasons.append("Regime RANGING (trending preferred)")
        
        # 3. Volatility OK (+15)
        # Assume volatility is OK if between 20-80 percentile (not extreme)
        if 20.0 <= volatility_pct <= 80.0:
            score += 15
        elif volatility_pct > 95.0:
            score -= 15
            blocking_reasons.append(f"High volatility: {volatility_pct:.1f}% percentile")
        elif volatility_pct < 5.0:
            blocking_reasons.append(f"Low volatility: {volatility_pct:.1f}% percentile")
        
        # 4. Signal confidence (confidence * 20)
        if signal_confidence > 0:
            score += int(signal_confidence * 20)
        else:
            blocking_reasons.append("No recent signals generated")
        
        # 5. No embargo (+10)
        if not news_embargo:
            score += 10
        else:
            score = min(score, 40)  # Hard blocker caps at 40
            blocking_reasons.append("News embargo active")
        
        # 6. Execution allowed (+5)
        if execution_allowed:
            score += 5
        else:
            score = min(score, 40)  # Hard blocker caps at 40
            blocking_reasons.append("Execution gate blocked")
        
        # 7. Cooldown clear (+10)
        if cooldown_remaining_minutes is None or cooldown_remaining_minutes <= 0:
            score += 10
        else:
            blocking_reasons.append(f"Cooldown active: {cooldown_remaining_minutes}m remaining")
        
        # Apply constraints
        # - Bias conflict caps score at <=60
        if bias_alignment == BiasAlignment.CONFLICT:
            score = min(score, 60)
        
        # - Hard blockers cap score at <=40
        if news_embargo or not execution_allowed:
            score = min(score, 40)
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        # Estimate time to entry
        estimated_time_to_entry = self._estimate_time_to_entry(
            blocking_reasons=blocking_reasons,
            cooldown_remaining_minutes=cooldown_remaining_minutes,
            bias_alignment=bias_alignment,
            regime=regime,
            embargo_active=news_embargo
        )
        
        return StrategyReadiness(
            strategy_id=strategy_id,
            instrument=instrument,
            readiness_score=score,
            blocking_reasons=blocking_reasons,
            bias_alignment=bias_alignment,
            estimated_time_to_entry_minutes=estimated_time_to_entry,
            last_signal_ts=last_signal_ts,
            regime=regime,
            volatility_pct=volatility_pct,
            embargo_active=news_embargo,
            daily_bias=daily_bias,
            weekly_bias=weekly_bias,
            execution_allowed=execution_allowed,
            cooldown_remaining_minutes=cooldown_remaining_minutes,
            signal_confidence=signal_confidence,
            details=kwargs
        )
    
    def _determine_bias_alignment(self, daily_bias: str, weekly_bias: str) -> BiasAlignment:
        """Determine bias alignment status"""
        # Handle missing/None
        if not daily_bias or not weekly_bias or daily_bias == "None" or weekly_bias == "None":
            return BiasAlignment.MISSING
        
        # Normalize to uppercase
        daily_bias = daily_bias.upper()
        weekly_bias = weekly_bias.upper()
        
        # Check for NEUTRAL
        if daily_bias == "NEUTRAL" or weekly_bias == "NEUTRAL":
            if daily_bias == "NEUTRAL" and weekly_bias == "NEUTRAL":
                return BiasAlignment.NEUTRAL
            # One is neutral, one is directional
            return BiasAlignment.NEUTRAL
        
        # Check if both are directional and match
        if daily_bias == weekly_bias:
            # Both BULLISH or both BEARISH
            return BiasAlignment.ALIGNED
        
        # One BULLISH, one BEARISH (conflict)
        return BiasAlignment.CONFLICT
    
    def _estimate_time_to_entry(
        self,
        blocking_reasons: List[str],
        cooldown_remaining_minutes: Optional[int],
        bias_alignment: BiasAlignment,
        regime: str,
        embargo_active: bool
    ) -> Optional[int]:
        """
        Estimate time to entry in minutes.
        Returns None if estimation not possible or too uncertain.
        """
        # Hard blockers - cannot estimate
        if embargo_active:
            return None  # Embargo duration unknown
        
        # Cooldown - exact time known
        if cooldown_remaining_minutes and cooldown_remaining_minutes > 0:
            return cooldown_remaining_minutes
        
        # Bias conflict - could resolve on next candle (5-15 min for M5, 60 min for H1)
        if bias_alignment == BiasAlignment.CONFLICT:
            return 15  # Conservative estimate
        
        # Regime RANGING - could transition on next candle
        if regime == "RANGING":
            return 30  # Conservative estimate
        
        # No blocking reasons - ready now (0 minutes)
        if not blocking_reasons:
            return 0
        
        # Other blockers - uncertain
        return None


# Singleton instance
_READINESS_EVALUATOR = None


def get_readiness_evaluator() -> StrategyReadinessEvaluator:
    """Get singleton readiness evaluator"""
    global _READINESS_EVALUATOR
    if _READINESS_EVALUATOR is None:
        _READINESS_EVALUATOR = StrategyReadinessEvaluator()
    return _READINESS_EVALUATOR
