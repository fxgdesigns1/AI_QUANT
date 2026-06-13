#!/usr/bin/env python3
"""
Phase 8P: compact retention cleanup for ALPHA imports and local 5950X caches.

Never deletes latest pointer files. Never touches broker state or execution paths.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

PHASE = "Phase 8P"
PERFORMANCE_ROOT = Path("ARTIFACTS/performance")
LATEST_POINTER_NAMES = {
    "latest_research_job_result.json",
    "latest_phase8o_strategy_discovery.json",
    "latest_phase8o_backtest_summary.json",
    "latest_phase8o_exact_replay_result.json",
    "latest_phase8o_recommendation.json",
    "latest_research_dashboard.json",
    "latest_weekend_research_diary.json",
}


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def _expired_children(root: Path, cutoff: datetime) -> Iterable[Path]:
    if not root.exists():
        return []
    out = []
    for child in root.iterdir():
        if child.name in LATEST_POINTER_NAMES:
            continue
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            out.append(child)
    return out


def cleanup(
    *,
    repo_root: Path,
    local_cache_root: Path | None = None,
    retain_alpha_imports_days: int = 180,
    retain_local_cache_days: int = 30,
    dry_run: bool = False,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    alpha_import_roots = [
        repo_root / PERFORMANCE_ROOT / "imports" / "research_jobs",
        repo_root / PERFORMANCE_ROOT / "imports" / "phase8o",
    ]
    deleted = []
    candidates = []
    alpha_cutoff = now - timedelta(days=int(retain_alpha_imports_days))
    for root in alpha_import_roots:
        for child in _expired_children(root, alpha_cutoff):
            candidates.append(child)
    if local_cache_root:
        local_cutoff = now - timedelta(days=int(retain_local_cache_days))
        for child in _expired_children(local_cache_root, local_cutoff):
            candidates.append(child)

    for path in candidates:
        deleted.append(str(path))
        if dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    report = {
        "ok": True,
        "phase": PHASE,
        "classification": "PHASE8P_RETENTION_CLEANUP",
        "generated_at_utc": utc_now_iso_z(),
        "dry_run": bool(dry_run),
        "retention_deleted_count": len(deleted),
        "retention_deleted_paths": deleted,
        "alpha_import_size_bytes": sum(_size_bytes(root) for root in alpha_import_roots),
        "dashboard_size_bytes": _size_bytes(repo_root / PERFORMANCE_ROOT / "latest_research_dashboard.json")
        + _size_bytes(repo_root / PERFORMANCE_ROOT / "research_dashboard"),
        "index_size_bytes": _size_bytes(repo_root / PERFORMANCE_ROOT / "research_results_index.json")
        + _size_bytes(repo_root / PERFORMANCE_ROOT / "research_results_index.jsonl"),
        "local_cache_size_bytes": _size_bytes(local_cache_root) if local_cache_root else 0,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 8P retention cleanup.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--local-cache-root", type=Path, default=None)
    parser.add_argument("--retain-alpha-imports-days", type=int, default=180)
    parser.add_argument("--retain-local-cache-days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = cleanup(
            repo_root=args.repo_root.expanduser().resolve(),
            local_cache_root=args.local_cache_root.expanduser().resolve() if args.local_cache_root else None,
            retain_alpha_imports_days=args.retain_alpha_imports_days,
            retain_local_cache_days=args.retain_local_cache_days,
            dry_run=args.dry_run,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
