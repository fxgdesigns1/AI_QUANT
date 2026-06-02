from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# POSIX-only; project runs on macOS/Linux (CI/VM). For Windows, we'd need portalocker.
import fcntl


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge src into dst (mutates dst), preserving unknown keys.

    Rules:
      - dict + dict => recurse
      - otherwise => overwrite
    """
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)  # type: ignore[index]
        else:
            dst[k] = v
    return dst


@dataclass(frozen=True)
class SnapshotStore:
    path: Path

    def read(self, max_age_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Read snapshot, optionally checking freshness"""
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8', errors='ignore') or "{}")
            
            # Check freshness if requested (compatibility with StatusSnapshot.read)
            if max_age_seconds is not None:
                timestamp = data.get("timestamp_utc") or data.get("_meta", {}).get("ts_utc", 0)
                age = time.time() - timestamp
                if age > max_age_seconds:
                    return {}
            
            return data
        except Exception:
            # Corrupt/partial file should not crash callers; return empty and let writers repopulate.
            return {}

    def update(self, patch: Dict[str, Any], *, actor: str = "unknown") -> Dict[str, Any]:
        """Lock, read current snapshot, deep-merge patch, and atomically write.

        Returns the merged snapshot.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Lock file is the snapshot path itself. This prevents concurrent writers.
        with open(self.path, 'a+', encoding='utf-8') as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                lockf.seek(0)
                raw = lockf.read()
                try:
                    cur = json.loads(raw or "{}")
                except Exception:
                    cur = {}

                # add/update metadata
                ts_now = time.time()
                meta = {
                    "ts_utc": ts_now,
                    "last_writer": actor,
                }
                if isinstance(cur.get("_meta"), dict):
                    cur["_meta"].update(meta)  # type: ignore[union-attr]
                else:
                    cur["_meta"] = meta
                
                # Also write timestamp_utc at root level for StatusSnapshot.read() compatibility
                cur["timestamp_utc"] = ts_now

                merged = _deep_merge(cur, patch)
                
                # Ensure timestamp_utc is always updated from _meta.ts_utc (after merge)
                if "_meta" in merged and "ts_utc" in merged["_meta"]:
                    merged["timestamp_utc"] = merged["_meta"]["ts_utc"]

                # Atomic write: write to temp then replace
                tmp_dir = str(self.path.parent)
                fd, tmp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=tmp_dir)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                        json.dump(merged, tf, ensure_ascii=False, indent=2, sort_keys=True)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(tmp_name, self.path)
                finally:
                    try:
                        if os.path.exists(tmp_name):
                            os.remove(tmp_name)
                    except Exception:
                        pass

                return merged
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def get_snapshot_store(snapshot_path: Optional[str] = None) -> SnapshotStore:
    """Get snapshot store instance using the same path as StatusSnapshot"""
    if snapshot_path is None:
        # Use same logic as StatusSnapshot to derive path
        _repo_root = Path(__file__).resolve().parents[2]
        _runtime_dir = _repo_root / "runtime"
        _runtime_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = str(_runtime_dir / "status.json")
    else:
        snapshot_path = os.getenv("STATUS_SNAPSHOT_PATH", snapshot_path)
    
    return SnapshotStore(path=Path(snapshot_path))
