"""
Strategy Explanation Generator - Human-Readable Explanations

Generates deterministic explanation strings for why strategies are/aren't trading.
AUTHORITATIVE TRUTH - NO MOCKS - READ-ONLY DIAGNOSTICS
"""

from __future__ import annotations

import logging
from typing import List, Optional
from src.core.strategy_readiness import StrategyReadiness, BiasAlignment

logger = logging.getLogger(__name__)


def generate_explanation(readiness: StrategyReadiness) -> str:
    """
    Generate human-readable explanation for strategy readiness.
    
    Args:
        readiness: StrategyReadiness object
        
    Returns:
        Human-readable explanation string
    """
    if readiness.readiness_score >= 80:
        return _generate_ready_explanation(readiness)
    elif readiness.readiness_score >= 60:
        return _generate_waiting_explanation(readiness)
    elif readiness.readiness_score >= 40:
        return _generate_blocked_explanation(readiness)
    else:
        return _generate_critical_blocked_explanation(readiness)


def _generate_ready_explanation(readiness: StrategyReadiness) -> str:
    """Generate explanation for ready state (score >= 80)"""
    if not readiness.blocking_reasons:
        return "Ready: All conditions satisfied, awaiting candle close"
    
    # Even with high score, there might be minor blockers
    reasons = ", ".join(readiness.blocking_reasons[:2])
    return f"Ready: {reasons} (minor, not blocking)"


def _generate_waiting_explanation(readiness: StrategyReadiness) -> str:
    """Generate explanation for waiting state (score 60-79)"""
    explanations = []
    
    # Bias conflict
    if readiness.bias_alignment == BiasAlignment.CONFLICT:
        explanations.append(
            f"Bias conflict: Daily {readiness.daily_bias}, Weekly {readiness.weekly_bias}"
        )
    
    # Regime issues
    if readiness.regime == "RANGING":
        explanations.append("Regime RANGING (trending preferred)")
    elif readiness.regime == "SHOCK":
        explanations.append("Regime SHOCK detected")
    
    # Volatility
    if readiness.volatility_pct > 95.0:
        explanations.append(f"High volatility: {readiness.volatility_pct:.1f}% percentile")
    elif readiness.volatility_pct < 5.0:
        explanations.append(f"Low volatility: {readiness.volatility_pct:.1f}% percentile")
    
    # Cooldown
    if readiness.cooldown_remaining_minutes and readiness.cooldown_remaining_minutes > 0:
        explanations.append(f"Cooldown active: {readiness.cooldown_remaining_minutes}m remaining")
    
    # Signal confidence
    if readiness.signal_confidence is None or readiness.signal_confidence == 0:
        explanations.append("No recent signals generated")
    
    if explanations:
        return f"Waiting: {', '.join(explanations[:3])}"
    else:
        return "Waiting: Conditions improving, monitoring for entry"


def _generate_blocked_explanation(readiness: StrategyReadiness) -> str:
    """Generate explanation for blocked state (score 40-59)"""
    explanations = []
    
    # Hard blockers
    if readiness.embargo_active:
        explanations.append("News embargo active")
    
    if not readiness.execution_allowed:
        explanations.append("Execution gate blocked")
    
    # Bias conflict (caps at 60)
    if readiness.bias_alignment == BiasAlignment.CONFLICT:
        explanations.append(
            f"Bias conflict: Daily {readiness.daily_bias}, Weekly {readiness.weekly_bias}"
        )
    
    # Regime
    if readiness.regime == "SHOCK":
        explanations.append("Regime SHOCK detected")
    
    if explanations:
        return f"Blocked: {', '.join(explanations[:2])}"
    else:
        return "Blocked: Multiple conditions not met"


def _generate_critical_blocked_explanation(readiness: StrategyReadiness) -> str:
    """Generate explanation for critically blocked state (score < 40)"""
    explanations = []
    
    # Hard blockers first
    if readiness.embargo_active:
        explanations.append("News embargo active")
    
    if not readiness.execution_allowed:
        explanations.append("Execution gate blocked")
    
    # Missing bias
    if readiness.bias_alignment == BiasAlignment.MISSING:
        explanations.append("Bias data unavailable")
    
    # Regime shock
    if readiness.regime == "SHOCK":
        explanations.append("Regime SHOCK detected")
    
    # Bias conflict
    if readiness.bias_alignment == BiasAlignment.CONFLICT:
        explanations.append(
            f"Bias conflict: Daily {readiness.daily_bias}, Weekly {readiness.weekly_bias}"
        )
    
    if explanations:
        return f"Blocked: {', '.join(explanations[:2])}"
    else:
        return "Blocked: Critical conditions not met"


def generate_why_not_trading(readiness: StrategyReadiness) -> str:
    """
    Generate concise "why not trading" summary.
    
    Args:
        readiness: StrategyReadiness object
        
    Returns:
        Concise explanation string
    """
    if readiness.readiness_score >= 80:
        return "Ready - awaiting entry signal"
    
    if readiness.blocking_reasons:
        # Return first 2 blocking reasons
        return "; ".join(readiness.blocking_reasons[:2])
    
    return "Conditions not yet met"


def generate_bias_conflict_summary(readiness: StrategyReadiness) -> Optional[str]:
    """
    Generate bias conflict summary if conflict exists.
    
    Args:
        readiness: StrategyReadiness object
        
    Returns:
        Conflict summary string or None
    """
    if readiness.bias_alignment == BiasAlignment.CONFLICT:
        return f"D: {readiness.daily_bias} | W: {readiness.weekly_bias}"
    return None
