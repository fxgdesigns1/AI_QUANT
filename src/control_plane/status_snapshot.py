"""Status snapshot writer/reader for bridging runner and API

The runner writes runtime/status.json atomically on each scan.
The API reads it to provide real-time system status.

NO SECRETS in snapshot - only operational metrics.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StatusSnapshot:
    """Atomic status snapshot for runner→API bridge
    
    Uses deterministic repo-root path: repo/runtime/status.json
    """
    
    def __init__(self, snapshot_path: Optional[str] = None):
        if snapshot_path is None:
            # Deterministic: compute repo root from this file's location
            # This file is at: repo/src/control_plane/status_snapshot.py
            # Repo root is: parents[2]
            _repo_root = Path(__file__).resolve().parents[2]
            _runtime_dir = _repo_root / "runtime"
            _runtime_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = str(_runtime_dir / "status.json")
        else:
            # Allow override via env or explicit path
            snapshot_path = os.getenv("STATUS_SNAPSHOT_PATH", snapshot_path)
        
        self.snapshot_path = Path(snapshot_path)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    
    def write(self, status: Dict[str, Any]) -> None:
        """Write status snapshot atomically (NO SECRETS)"""
        # Add timestamp
        status["timestamp_utc"] = time.time()
        status["timestamp_iso"] = datetime.utcnow().isoformat() + "Z"
        
        # Paranoid: remove any secret-like keys
        sanitized = self._sanitize(status)
        
        # Atomic write
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.snapshot_path.parent,
            prefix='.status_',
            suffix='.json.tmp',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(sanitized, tmp_file, indent=2, sort_keys=True)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        
        # Atomic rename
        tmp_path.replace(self.snapshot_path)
    
    def read(self, max_age_seconds: int = 120) -> Optional[Dict[str, Any]]:
        """Read status snapshot if fresh enough"""
        if not self.snapshot_path.exists():
            return None
        
        try:
            with open(self.snapshot_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check freshness
            timestamp = data.get("timestamp_utc", 0)
            age = time.time() - timestamp
            
            if age > max_age_seconds:
                return None  # Stale
            
            return data
        except Exception:
            return None
    
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any secret-like values (paranoid filter)"""
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Block secret-like keys
            if any(pattern in key_lower for pattern in [
                'api_key', 'token', 'secret', 'password', 'credential', 'bearer'
            ]):
                continue
            
            # Recursively sanitize nested dicts
            if isinstance(value, dict):
                sanitized[key] = self._sanitize(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


def get_status_snapshot() -> StatusSnapshot:
    """Get status snapshot instance"""
    return StatusSnapshot()
