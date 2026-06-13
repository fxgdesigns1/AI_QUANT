"""
Execution trace helpers: scan canonical JSONL logs for signal_id.

Lane-010 bridge log for API traces uses CANONICAL_BRIDGE_LOG_STR / CANONICAL_BRIDGE_LOG_PATH only.

Bridge log detection MUST NOT be blocked by freshness/stale heuristics — if the
signal_id appears anywhere in the file, that is a hit.

Each scan opens the file anew (no reused file descriptors or read cursors).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# EA writes: {"type":"...","msg":"...","signal_id":"...","ts":"2026.04.07 12:34:56"}
_TS_FALLBACK = re.compile(r'"ts"\s*:\s*"([^"]+)"')

# Lane-010 execution trace: single VM path (operator-verified). No repo/home fallbacks.
CANONICAL_BRIDGE_LOG_STR = "/home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl"
CANONICAL_BRIDGE_LOG_PATH = Path(CANONICAL_BRIDGE_LOG_STR)


def _extract_timestamp(obj: Dict[str, Any], raw_line: str) -> Optional[str]:
    for key in ("ts", "timestamp", "time", "ts_utc"):
        v = obj.get(key)
        if v is not None and str(v).strip():
            return str(v)
    m = _TS_FALLBACK.search(raw_line)
    if m:
        return m.group(1)
    return None


def scan_jsonl_for_signal_id(path: Path, signal_id: str) -> Dict[str, Any]:
    """
    Full-file scan (line iterator). Counts every line read from the file.

    Match if signal_id appears in the raw line OR parsed JSON signal_id equals signal_id.
    Always opens a new file handle; reads to EOF (no tail-only or cached offsets).
    """
    out: Dict[str, Any] = {
        "path": str(path),
        "file_exists": path.is_file(),
        "lines_scanned": 0,
        "non_empty_lines": 0,
        "signal_id_matched": False,
        "first_match_line_number": None,
        "first_match_event_type": None,
        "last_line_timestamp": None,
        "scan_error": None,
    }
    if not path.is_file():
        return out
    last_ts: Optional[str] = None
    want = str(signal_id).strip()
    try:
        # Fresh handle every call — no shared FDs or read cursors.
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                out["lines_scanned"] += 1
                raw = line.strip()
                if not raw:
                    continue
                out["non_empty_lines"] += 1
                matched_here = False
                if want and want in raw:
                    matched_here = True
                obj: Optional[Dict[str, Any]] = None
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        obj = parsed
                        sid = obj.get("signal_id")
                        if sid is not None and str(sid) == want:
                            matched_here = True
                except (json.JSONDecodeError, TypeError):
                    pass
                line_ts: Optional[str] = None
                if obj is not None:
                    line_ts = _extract_timestamp(obj, raw)
                if line_ts is None:
                    m = _TS_FALLBACK.search(raw)
                    if m:
                        line_ts = m.group(1)
                if line_ts is not None:
                    last_ts = line_ts
                if matched_here:
                    out["signal_id_matched"] = True
                    if out["first_match_line_number"] is None:
                        out["first_match_line_number"] = out["lines_scanned"]
                        if obj is not None:
                            et = obj.get("type")
                            if et is not None:
                                out["first_match_event_type"] = str(et)
        out["last_line_timestamp"] = last_ts
    except OSError as e:
        out["scan_error"] = str(e)[:300]
    return out


def resolve_signal_log_scan_paths(project_root: Path) -> List[Path]:
    paths: List[Path] = []
    env_override = (os.getenv("SIGNAL_LOG_SCAN_PATH") or "").strip()
    if env_override:
        paths.append(Path(env_override).expanduser())
    home = Path.home()
    paths.extend(
        [
            home / "gcloud-system" / "logs" / "signals_ftmo_demo2.jsonl",
            project_root / "logs" / "signals_ftmo_demo2.jsonl",
        ]
    )
    seen: set[str] = set()
    unique: List[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def pick_first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.is_file():
            return p
    return None
