"""
Dashboard Panel - Session Regime Gate Decisions (Read-Only)

Displays recent gatekeeper decisions from audit log.
NO control surface - read-only observability only.
"""

from pathlib import Path
import json
from typing import List, Dict, Any


AUDIT_PATH = Path("logs/session_regime_gate_audit.jsonl")


def load_recent_gate_events(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Load recent gatekeeper decisions from audit log.
    
    Args:
        limit: Maximum number of events to return (default: 100)
    
    Returns:
        List of gate decision dictionaries, most recent first
    """
    if not AUDIT_PATH.exists():
        return []
    
    try:
        with AUDIT_PATH.open("r") as f:
            lines = f.readlines()
            # Get last N lines (most recent first)
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            # Parse JSON and reverse to show most recent first
            events = [json.loads(line.strip()) for line in recent_lines if line.strip()]
            events.reverse()  # Most recent first
            return events
    except Exception as e:
        # Fail gracefully - don't break dashboard
        return []


def get_gate_statistics() -> Dict[str, Any]:
    """
    Get aggregate statistics from gate decisions.
    
    Returns:
        Dictionary with counts, rates, and breakdowns
    """
    events = load_recent_gate_events(limit=1000)  # Get more for stats
    
    if not events:
        return {
            "total_decisions": 0,
            "allowed_count": 0,
            "blocked_count": 0,
            "allow_rate": 0.0,
            "by_reason": {},
            "by_session": {},
            "by_regime": {},
        }
    
    total = len(events)
    allowed_count = sum(1 for e in events if e.get("allowed", False))
    blocked_count = total - allowed_count
    
    # Count by reason
    by_reason = {}
    for event in events:
        reason = event.get("reason", "unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    
    # Count by session
    by_session = {}
    for event in events:
        session = event.get("session", "unknown")
        by_session[session] = by_session.get(session, 0) + 1
    
    # Count by regime
    by_regime = {}
    for event in events:
        regime = event.get("regime", "unknown")
        by_regime[regime] = by_regime.get(regime, 0) + 1
    
    return {
        "total_decisions": total,
        "allowed_count": allowed_count,
        "blocked_count": blocked_count,
        "allow_rate": round(allowed_count / total if total > 0 else 0.0, 3),
        "by_reason": by_reason,
        "by_session": by_session,
        "by_regime": by_regime,
    }


def get_current_session_regime_snapshot() -> Dict[str, Any]:
    """
    Get current session/regime snapshot and last policy key.
    
    Returns:
        Dictionary with current session, last known regime, and last policy key
    """
    from datetime import datetime, timezone
    
    events = load_recent_gate_events(limit=1)
    current_time = datetime.now(timezone.utc)
    
    # Classify current session
    h = current_time.hour
    if h >= 22 or h < 6:
        current_session = "asia"
    elif 6 <= h < 12:
        current_session = "london"
    elif 12 <= h < 16:
        current_session = "london_ny_overlap"
    elif 16 <= h < 21:
        current_session = "new_york"
    else:
        current_session = "transition"
    
    # Get last known values from most recent event
    last_event = events[0] if events else None
    last_regime = last_event.get("regime", "UNKNOWN") if last_event else "UNKNOWN"
    last_policy_key = None
    
    if last_event:
        session = last_event.get("session", "unknown")
        regime = last_event.get("regime", "UNKNOWN")
        news_state = last_event.get("news_state", "normal")
        bias_alignment = "aligned" if last_event.get("roadmap_aligned", False) else "misaligned"
        last_policy_key = f"{session}|{regime}|{news_state}|{bias_alignment}"
    
    return {
        "current_session": current_session,
        "current_time_utc": current_time.isoformat(),
        "last_known_regime": last_regime,
        "last_policy_key": last_policy_key,
        "has_recent_events": bool(events),
    }
