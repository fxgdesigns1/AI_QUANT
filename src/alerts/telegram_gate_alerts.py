"""
Telegram Alerts - Session Regime Gate Critical Events

Alerts ONLY on:
1. News embargo blocks
2. Roadmap misalignment blocks
3. Unexpected allow (rare)
4. Gate exception (should never happen)

Message format (human readable):
[SESSION GATE]
Symbol: XAU_USD
Session: London-NY Overlap
Regime: TRENDING
Decision: BLOCKED
Reason: news_embargo
Biases: D=BULL W=BULL M=BULL

Implementation MUST:
- Use env var TELEGRAM_BOT_TOKEN
- Use env var TELEGRAM_CHAT_ID
- Fail silently if missing
- NEVER block trading
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def send_gate_alert(
    symbol: str,
    session: str,
    regime: str,
    decision: str,  # "ALLOWED" or "BLOCKED"
    reason: str,
    daily_bias: Optional[str] = None,
    weekly_bias: Optional[str] = None,
    monthly_bias: Optional[str] = None,
    is_embargo: bool = False,
    roadmap_aligned: bool = False,
) -> None:
    """
    Send Telegram alert for critical gate events.
    
    Only sends for:
    - News embargo blocks
    - Roadmap misalignment blocks
    - Unexpected allows (rare)
    - Gate exceptions (should never happen)
    
    Fails silently if Telegram not configured or on any error.
    
    Args:
        symbol: Trading instrument (e.g., "XAU_USD")
        session: Trading session (e.g., "london_ny_overlap")
        regime: Market regime (e.g., "TRENDING")
        decision: Decision ("ALLOWED" or "BLOCKED")
        reason: Block/reason code
        daily_bias: Daily bias (optional)
        weekly_bias: Weekly bias (optional)
        monthly_bias: Monthly bias (optional)
        is_embargo: Whether news embargo active
        roadmap_aligned: Whether roadmap aligned
    """
    # Determine if this is a critical event worth alerting
    critical_reasons = [
        "news_embargo",
        "roadmap_misaligned",
        "dependencies_missing",
        "policy_lookup_error",
        "unexpected_allow",  # Rare - alert on allows that shouldn't happen
    ]
    
    # Only alert on critical events
    if reason not in critical_reasons and decision == "ALLOWED":
        # Don't alert on normal allows
        return
    
    try:
        # Import Telegram notifier (may not be available)
        try:
            from src.control_plane.telegram_notifier import send_telegram_message
        except ImportError:
            # Telegram notifier not available - fail silently
            logger.debug("Telegram notifier not available - skipping alert")
            return
        
        # Check if credentials configured
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        
        if not bot_token or not chat_id:
            # Not configured - fail silently
            logger.debug("Telegram credentials not configured - skipping alert")
            return
        
        # Format bias string
        bias_str = ""
        if daily_bias and weekly_bias and monthly_bias:
            bias_str = f"Biases: D={daily_bias[:4]} W={weekly_bias[:4]} M={monthly_bias[:4]}"
        elif any([daily_bias, weekly_bias, monthly_bias]):
            biases = []
            if daily_bias:
                biases.append(f"D={daily_bias[:4]}")
            if weekly_bias:
                biases.append(f"W={weekly_bias[:4]}")
            if monthly_bias:
                biases.append(f"M={monthly_bias[:4]}")
            bias_str = f"Biases: {' '.join(biases)}"
        
        # Format session name for readability
        session_names = {
            "asia": "Asia",
            "london": "London",
            "london_ny_overlap": "London-NY Overlap",
            "new_york": "New York",
            "transition": "Transition",
        }
        session_display = session_names.get(session, session)
        
        # Build message
        lines = [
            "[SESSION GATE]",
            f"Symbol: {symbol}",
            f"Session: {session_display}",
            f"Regime: {regime}",
            f"Decision: {decision}",
            f"Reason: {reason}",
        ]
        
        if bias_str:
            lines.append(bias_str)
        
        if is_embargo:
            lines.append("⚠️ News embargo active")
        
        if not roadmap_aligned:
            lines.append("⚠️ Roadmap misaligned")
        
        message = "\n".join(lines)
        
        # Send message (fail silently on error)
        try:
            send_telegram_message(message)
            logger.debug(f"Telegram alert sent: {reason} for {symbol}")
        except Exception as e:
            # Fail silently - don't break trading
            logger.warning(f"Failed to send Telegram alert: {e}")
            pass
        
    except Exception as e:
        # Fail silently - NEVER block trading
        logger.debug(f"Error in send_gate_alert: {e}")
        pass
