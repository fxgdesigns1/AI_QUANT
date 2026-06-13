#!/usr/bin/env python3
"""
Phase 8M: create a validated research job under ARTIFACTS/research_jobs/queue/pending.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    DEFAULT_ALPHA_JOB_ROOT,
    build_job,
    ensure_job_dirs,
    job_file_for,
    write_json,
)


def create_job(
    *,
    job_root: Path,
    job_type: str,
    instrument: str,
    granularity: str,
    lookback_days: int,
    session_bucket: str,
    session_window_utc: str,
    requested_by: str | None = None,
) -> Dict[str, Any]:
    ensure_job_dirs(job_root)
    job = build_job(
        job_type=job_type,
        requested_by=requested_by,
        params={
            "instrument": instrument,
            "granularity": granularity,
            "lookback_days": lookback_days,
            "session_bucket": session_bucket,
            "session_window_utc": session_window_utc,
            "mode": "research_only",
        },
    )
    path = job_file_for(job_root, "PENDING", job["job_id"])
    if path.exists():
        raise ContractError(f"job_already_exists:{path}")
    write_json(path, job)
    return {"ok": True, "job_id": job["job_id"], "job_path": str(path), "job": job}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Phase 8M research job on ALPHA.")
    parser.add_argument("--job-root", type=Path, default=DEFAULT_ALPHA_JOB_ROOT)
    parser.add_argument("--job-type", choices=("phase8l_backtest", "phase8k_replay"), default="phase8l_backtest")
    parser.add_argument("--instrument", default="EUR_USD")
    parser.add_argument("--granularity", default="M15")
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--session-bucket", default="NY_OPEN_SECONDARY_PROPOSED")
    parser.add_argument("--session-window-utc", default="13:30-16:00")
    parser.add_argument("--requested-by", default=None)
    args = parser.parse_args()

    lookback = int(args.lookback_days if args.lookback_days is not None else (180 if args.job_type == "phase8k_replay" else 14))
    try:
        res = create_job(
            job_root=args.job_root,
            job_type=args.job_type,
            instrument=args.instrument,
            granularity=args.granularity,
            lookback_days=lookback,
            session_bucket=args.session_bucket,
            session_window_utc=args.session_window_utc,
            requested_by=args.requested_by,
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

