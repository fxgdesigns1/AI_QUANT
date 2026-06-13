"""
Cache-first + monthly budget wrapper for paid calendar HTTP calls (research / Phase 8R / Phase 8O).

Does not log secrets. Ledger events contain fingerprints only.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from scripts.phase8s_calendar_budget_guard import (
    append_ledger,
    evaluate_budget,
    request_fingerprint,
    usage_report_path,
    write_cache_manifest,
    write_usage_report,
)

UTC = timezone.utc

CACHE_SUBDIR = Path("ARTIFACTS") / "performance" / "calendar_http_cache"


def cache_dir(repo_root: Path) -> Path:
    d = (repo_root / CACHE_SUBDIR).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(repo_root: Path, provider: str, fp: str) -> Path:
    safe = provider.replace("/", "_")
    return cache_dir(repo_root) / f"{safe}_{fp}.json"


def _is_stale(path: Path, *, ttl_days: int) -> bool:
    if not path.is_file():
        return True
    age = datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return age > timedelta(days=ttl_days)


def fetch_calendar_with_budget(
    *,
    repo_root: Path,
    provider: str,
    date_from: str,
    date_to: str,
    countries: str,
    session_remaining_paid_calls: List[int],
    ttl_days: int = 365,
    inner: Callable[[], Tuple[List[Dict[str, Any]], Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    session_remaining_paid_calls: single-element list mutated as shared counter (allows 0).
    """
    fp = request_fingerprint(provider, date_from, date_to, countries)
    meta: Dict[str, Any] = {
        "provider": provider,
        "request_fingerprint": fp,
        "cache_hit": False,
        "budget_blocked": False,
        "paid_call_made": False,
        "inner": {},
    }
    cpath = _cache_path(repo_root, provider, fp)
    if cpath.is_file() and not _is_stale(cpath, ttl_days=ttl_days):
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = None
        rows = data.get("rows") if isinstance(data, dict) else None
        if isinstance(rows, list):
            append_ledger(
                repo_root,
                {
                    "event": "calendar_cache_hit",
                    "provider": provider,
                    "fingerprint": fp,
                },
            )
            meta["cache_hit"] = True
            write_usage_report(repo_root)
            return rows, meta

    dec = evaluate_budget(repo_root)
    if not dec.allowed:
        append_ledger(
            repo_root,
            {
                "event": "budget_blocked",
                "provider": provider,
                "fingerprint": fp,
                "reason": dec.reason,
            },
        )
        meta["budget_blocked"] = True
        meta["inner"] = {"failure_reason": dec.reason}
        write_usage_report(repo_root)
        return [], meta

    if session_remaining_paid_calls[0] <= 0:
        append_ledger(
            repo_root,
            {
                "event": "budget_blocked",
                "provider": provider,
                "fingerprint": fp,
                "reason": "session_call_cap_exceeded",
            },
        )
        meta["budget_blocked"] = True
        meta["inner"] = {"failure_reason": "session_call_cap_exceeded"}
        write_usage_report(repo_root)
        return [], meta

    try:
        rows, inner_meta = inner()
    except Exception as exc:
        meta["inner"] = {"failure_reason": f"inner_exception:{type(exc).__name__}"}
        append_ledger(
            repo_root,
            {
                "event": "calendar_inner_exception",
                "provider": provider,
                "fingerprint": fp,
                "exc_type": type(exc).__name__,
            },
        )
        write_usage_report(repo_root)
        return [], meta
    meta["inner"] = {k: inner_meta[k] for k in inner_meta if k != "api_error"}
    status_code = inner_meta.get("http_status")
    if status_code is not None:
        session_remaining_paid_calls[0] -= 1
        append_ledger(
            repo_root,
            {
                "event": "paid_calendar_call",
                "provider": provider,
                "fingerprint": fp,
                "http_status": status_code,
            },
        )
        meta["paid_call_made"] = True
        if int(status_code) == 200:
            cpath.write_text(
                json.dumps(
                    {
                        "saved_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        "provider": provider,
                        "fingerprint": fp,
                        "rows": rows,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    write_usage_report(repo_root)
    _refresh_manifest(repo_root)
    return rows, meta


def _refresh_manifest(repo_root: Path) -> None:
    base = cache_dir(repo_root)
    entries: List[Dict[str, Any]] = []
    if base.is_dir():
        for p in sorted(base.glob("*.json"))[:500]:
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            entries.append({"file": p.name, "size_bytes": int(sz)})
    write_cache_manifest(repo_root, base, entries)


def merge_usage_into_dashboard_patch(repo_root: Path) -> Dict[str, Any]:
    """Small dict safe to merge into Phase 8P dashboard JSON."""
    path = usage_report_path(repo_root)
    if not path.is_file():
        return {
            "calendar_usage_report_present": False,
            "calendar_budget_dashboard_stub": True,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"calendar_usage_report_present": False}
    return {
        "calendar_calls_this_month": data.get("calendar_calls_this_month"),
        "calendar_budget_remaining": data.get("calendar_budget_remaining"),
        "calendar_cache_hit_rate": data.get("calendar_cache_hit_rate"),
        "last_calendar_api_call_utc": data.get("last_calendar_api_call_utc"),
        "calendar_budget_remaining_cap": data.get("calendar_budget_monthly_cap"),
        "calendar_usage_report_present": True,
        "providers_blocked_by_budget": not data.get("next_paid_call_allowed", True),
        "calendar_budget_reason": data.get("budget_decision_reason"),
    }
