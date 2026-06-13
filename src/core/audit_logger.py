"""
Audit Logger - Append-only truth log for gatekeeper decisions

Safety:
- Append-only (no overwrites)
- Best-effort (never raises exceptions)
- No runtime dependency (doesn't affect trading behavior)
- Fail silently if file missing or read-only
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

AUDIT_PATH = Path("logs/session_regime_gate_audit.jsonl")


def append_audit(event: Dict[str, Any]) -> None:
    """
    Append an audit event to the JSONL log file.
    
    Best-effort logging: never raises exceptions or affects trading behavior.
    If the file is missing, read-only, or any error occurs, silently continues.
    
    Args:
        event: Dictionary containing audit event data (allowed, reason, context, etc.)
    """
    try:
        # Ensure logs directory exists
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to file (mode='a' for append-only)
        with AUDIT_PATH.open("a") as f:
            record = {
                "ts_utc": datetime.now(timezone.utc).isoformat(),
                **event,
            }
            f.write(json.dumps(record) + "\n")
            f.flush()  # Ensure immediate write (optional but good practice)
    except Exception:
        # Fail silently: audit logging must never affect trading behavior
        # This includes: file permission errors, disk full, path issues, etc.
        pass
