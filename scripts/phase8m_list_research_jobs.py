#!/usr/bin/env python3
"""
Phase 8M: list ALPHA research jobs and latest imported result summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8m_contract import (  # noqa: E402
    DEFAULT_ALPHA_JOB_ROOT,
    DEFAULT_LATEST_RESULT_POINTER,
    list_jobs,
    read_json,
)


def _summarize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    params = job.get("params") or {}
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "job_type": job.get("job_type"),
        "created_at_utc": job.get("created_at_utc"),
        "updated_at_utc": job.get("updated_at_utc"),
        "instrument": params.get("instrument"),
        "granularity": params.get("granularity"),
        "lookback_days": params.get("lookback_days"),
        "recommendation_label": job.get("recommendation_label"),
        "result_import_manifest": job.get("result_import_manifest"),
        "failure_reason": job.get("failure_reason"),
        "path": job.get("_path"),
    }


def list_research_jobs(*, job_root: Path, latest_result_pointer: Path) -> Dict[str, Any]:
    raw = list_jobs(job_root)
    summarized: Dict[str, List[Dict[str, Any]]] = {
        key: [_summarize_job(j) for j in vals] for key, vals in raw.items()
    }
    latest = None
    if latest_result_pointer.is_file():
        latest = read_json(latest_result_pointer)
    return {
        "ok": True,
        "job_root": str(job_root),
        "counts": {k: len(v) for k, v in summarized.items()},
        "jobs": summarized,
        "latest_result": latest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List Phase 8M research jobs.")
    parser.add_argument("--job-root", type=Path, default=DEFAULT_ALPHA_JOB_ROOT)
    parser.add_argument("--latest-result-pointer", type=Path, default=DEFAULT_LATEST_RESULT_POINTER)
    args = parser.parse_args()
    try:
        print(json.dumps(list_research_jobs(job_root=args.job_root, latest_result_pointer=args.latest_result_pointer), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

