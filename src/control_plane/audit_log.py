"""Append-only audit logger for tracking all mutating actions (SAFE)

SECURITY:
- Writes to repo/runtime/audit.jsonl (gitignored)
- Never logs secrets (sanitizes payloads)
- Atomic-ish append (thread-safe enough for single-process async)
- Includes correlation IDs for tracing
"""

from __future__ import annotations

import json
import os
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

class AuditLog:
    """Append-only audit logger"""
    
    def __init__(self, log_path: Optional[str] = None):
        if log_path is None:
            # repo/runtime/audit.jsonl
            _repo_root = Path(__file__).resolve().parents[2]
            _runtime_dir = _repo_root / "runtime"
            _runtime_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(_runtime_dir / "audit.jsonl")
        
        self.log_path = Path(log_path)
        self._ensure_log_exists()
    
    def _ensure_log_exists(self):
        if not self.log_path.exists():
            self.log_path.touch()
    
    def _sanitize(self, data: Any) -> Any:
        """Sanitize data to remove secrets"""
        if isinstance(data, dict):
            return {k: self._sanitize(v) for k, v in data.items() 
                    if not any(secret in k.lower() for secret in 
                             ['token', 'key', 'secret', 'password', 'auth'])}
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        else:
            return data

    def log(self, 
            actor: str, 
            action: str, 
            status: str, 
            details: Optional[Dict[str, Any]] = None,
            correlation_id: Optional[str] = None) -> str:
        """Log an action
        
        Args:
            actor: Who performed the action (e.g. 'user', 'system', 'admin')
            action: What happened (e.g. 'strategy.enable', 'config.update')
            status: Outcome ('success', 'failure', 'attempt')
            details: Context/payload (sanitized automatically)
            correlation_id: Trace ID (generated if missing)
            
        Returns:
            correlation_id used
        """
        if not correlation_id:
            correlation_id = f"req_{uuid.uuid4().hex[:8]}"
            
        entry = {
            "ts_iso": datetime.now(timezone.utc).isoformat(),
            "ts_unix": time.time(),
            "correlation_id": correlation_id,
            "actor": actor,
            "action": action,
            "status": status,
            "details": self._sanitize(details) if details else {},
            "payload_hash": hashlib.sha256(
                json.dumps(details or {}, sort_keys=True).encode()
            ).hexdigest()[:8]
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Fallback: print to stderr if log write fails (never crash app)
            print(f"CRITICAL: Failed to write audit log: {e}")
            
        return correlation_id

    def read_tail(self, n: int = 100) -> List[Dict[str, Any]]:
        """Read last N entries efficiently"""
        if not self.log_path.exists():
            return []
            
        # Basic implementation: read all lines (okay for <100MB logs)
        # For production scale, use `tail -n` subprocess or seek from end
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return [json.loads(line) for line in lines[-n:]]
        except Exception:
            return []

# Singleton instance
_audit_log = AuditLog()

def get_audit_log() -> AuditLog:
    return _audit_log
