#!/usr/bin/env python3
"""
Phase 8X: write compact batch worker progress to ARTIFACTS/performance/latest_phase8x_batch_progress.json.

Reads ALPHA queue snapshot JSON (from phase8m_list_research_jobs.py) plus optional last worker cycle JSON.
No broker calls, no calendar API usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS = Path("ARTIFACTS/performance/latest_phase8x_batch_progress.json")


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    # utf-8-sig strips UTF-8 BOM if present (e.g. PowerShell Set-Content -Encoding utf8).
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_json_object(text: str) -> Dict[str, Any]:
    if text.startswith("\ufeff"):
        text = text[1:]
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no_json_object_in_text")
    return json.loads(text[start : end + 1])


def load_alpha_list_payload(raw: str | Path) -> Dict[str, Any]:
    if isinstance(raw, Path):
        return _read_json(raw)
    return _extract_json_object(raw)


def counts_from_alpha_list(payload: Mapping[str, Any]) -> Dict[str, int]:
    c = payload.get("counts") or {}
    return {
        "pending": int(c.get("pending") or 0),
        "running": int(c.get("running") or 0),
        "done": int(c.get("done") or 0),
        "failed": int(c.get("failed") or 0),
    }


def parse_last_worker(worker_arg: Optional[str]) -> Optional[Dict[str, Any]]:
    if not worker_arg or not str(worker_arg).strip():
        return None
    s = str(worker_arg).strip()
    if s.startswith("@"):
        return _read_json(Path(s[1:]).expanduser().resolve())
    return _extract_json_object(s)


def build_progress_document(
    *,
    alpha_list: Dict[str, Any],
    last_worker: Optional[Dict[str, Any]],
    stop_reason: str,
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    qc = counts_from_alpha_list(alpha_list)
    pending = qc["pending"]
    running = qc["running"]
    done = qc["done"]
    failed = qc["failed"]
    total = pending + running + done + failed
    percent_complete = round(100.0 * (done + failed) / total, 2) if total > 0 else 0.0

    started_at_utc = utc_now_iso_z()
    if previous and isinstance(previous.get("started_at_utc"), str):
        started_at_utc = str(previous["started_at_utc"])

    prev_last = None
    if previous and isinstance(previous.get("last_result_job_id"), str):
        prev_last = str(previous["last_result_job_id"])
    last_result_job_id: Optional[str] = prev_last
    current_job_id: Optional[str] = None
    if previous and isinstance(previous.get("current_job_id"), str):
        current_job_id = str(previous["current_job_id"])
    if last_worker:
        if last_worker.get("status") == "NO_PENDING_JOBS":
            current_job_id = None
        elif last_worker.get("ok") is False and isinstance(last_worker.get("error"), str):
            current_job_id = None
            stop_reason = f"WORKER_ERROR:{last_worker.get('error')}"
        elif last_worker.get("ok") and last_worker.get("job_id"):
            jid = str(last_worker["job_id"])
            current_job_id = jid
            last_result_job_id = jid

    return {
        "phase": "Phase 8X",
        "pending": pending,
        "running": running,
        "done": done,
        "failed": failed,
        "total": total,
        "percent_complete": percent_complete,
        "current_job_id": current_job_id,
        "started_at_utc": started_at_utc,
        "updated_at_utc": utc_now_iso_z(),
        "last_result_job_id": last_result_job_id,
        "stop_reason": str(stop_reason or ""),
        "alpha_job_root": alpha_list.get("job_root"),
    }


def write_progress(
    *,
    repo_root: Path,
    alpha_list_json: Path,
    last_worker_json: Optional[str],
    stop_reason: str,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    out = output_path or (repo_root / DEFAULT_PROGRESS)
    alpha_list = load_alpha_list_payload(alpha_list_json)
    if not alpha_list.get("ok"):
        raise ValueError(f"alpha_list_not_ok:{alpha_list}")

    prev: Optional[Dict[str, Any]] = None
    if out.is_file():
        try:
            prev = _read_json(out)
        except json.JSONDecodeError:
            prev = None

    last_worker = parse_last_worker(last_worker_json)
    doc = build_progress_document(
        alpha_list=alpha_list,
        last_worker=last_worker,
        stop_reason=stop_reason,
        previous=prev,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(out), "progress": doc}


def main() -> int:
    parser = argparse.ArgumentParser(description="Write Phase 8X batch progress JSON.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--alpha-list-json", type=Path, required=True, help="Path to phase8m_list_research_jobs JSON output.")
    parser.add_argument("--last-worker-json", default="", help="Inline JSON or @path to last worker cycle stdout.")
    parser.add_argument("--stop-reason", default="RUNNING")
    parser.add_argument("--output", type=Path, default=None, help="Defaults to ARTIFACTS/performance/latest_phase8x_batch_progress.json under repo-root.")
    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()
    alpha_path = args.alpha_list_json if args.alpha_list_json.is_absolute() else repo / args.alpha_list_json
    out_path = args.output
    if out_path is not None and not out_path.is_absolute():
        out_path = repo / out_path

    try:
        res = write_progress(
            repo_root=repo,
            alpha_list_json=alpha_path,
            last_worker_json=args.last_worker_json or None,
            stop_reason=args.stop_reason,
            output_path=out_path,
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
