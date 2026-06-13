#!/usr/bin/env python3
"""
Phase 8M: verify and import a compact 5950X research-job result pack into ALPHA artifacts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    DEFAULT_ALPHA_JOB_ROOT,
    DEFAULT_ALPHA_RESULT_IMPORT_ROOT,
    DEFAULT_LATEST_RESULT_POINTER,
    find_job_file,
    move_job,
    read_json,
    utc_now_iso_z,
    verify_research_result_pack,
    write_json,
)


def _extractall_safe(tf: tarfile.TarFile, path: Path) -> None:
    try:
        tf.extractall(path=path, filter="data")
    except TypeError:
        tf.extractall(path=path)


def _find_payload_root(extract_dir: Path) -> Path:
    children = list(extract_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def import_research_result(
    *,
    archive: Path,
    job_root: Path,
    import_root: Path,
    latest_pointer: Path,
    max_pack_size_mb: int = 25,
) -> Dict[str, Any]:
    archive = archive.expanduser().resolve()
    verify = verify_research_result_pack(archive, max_size_mb=max_pack_size_mb)
    job_id = verify.job_id
    dest_dir = import_root / job_id
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    staging = dest_dir / "_staging_extract"
    staging.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, mode="r:gz") as tf:
        _extractall_safe(tf, staging)
    payload_root = _find_payload_root(staging)

    imported: List[str] = []
    for name in verify.files_present:
        src = payload_root / name
        if src.is_file():
            dst = dest_dir / name
            dst.write_bytes(src.read_bytes())
            imported.append(name)

    summary = read_json(dest_dir / "backtest_summary.json")
    recommendation = read_json(dest_dir / "recommendation.json")
    result_manifest = read_json(dest_dir / "research_job_result_manifest.json")

    import_manifest: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": "Phase 8M",
        "classification": "IMPORTED_RESEARCH_JOB_RESULT",
        "alpha_hostname": socket.gethostname(),
        "job_id": job_id,
        "job_type": summary.get("job_type"),
        "source_result_pack": str(archive),
        "result_pack_size_bytes": verify.pack_size_bytes,
        "max_result_pack_size_mb": int(max_pack_size_mb),
        "import_dir": str(dest_dir),
        "files_imported": imported,
        "sha256_verified": verify.sha256_verified,
        "summary": summary,
        "recommendation": recommendation,
        "result_manifest": result_manifest,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    write_json(dest_dir / "phase8m_import_manifest.json", import_manifest)
    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    write_json(latest_pointer, import_manifest)

    found = find_job_file(job_root, job_id)
    if found is not None:
        job = read_json(found)
        status = str(job.get("status") or "").upper()
        updates = {
            "updated_at_utc": utc_now_iso_z(),
            "result_import_manifest": str(dest_dir / "phase8m_import_manifest.json"),
            "recommendation_label": recommendation.get("recommendation_label"),
        }
        if status == "RUNNING":
            move_job(job_root, job, "RUNNING", "DONE", updates=updates)
        elif status == "PENDING":
            move_job(job_root, job, "PENDING", "DONE", updates=updates)

    return {"ok": True, "job_id": job_id, "import_manifest": str(dest_dir / "phase8m_import_manifest.json"), "latest_pointer": str(latest_pointer)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Phase 8M compact research result pack on ALPHA.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--job-root", type=Path, default=DEFAULT_ALPHA_JOB_ROOT)
    parser.add_argument("--import-root", type=Path, default=DEFAULT_ALPHA_RESULT_IMPORT_ROOT)
    parser.add_argument("--latest-pointer", type=Path, default=DEFAULT_LATEST_RESULT_POINTER)
    parser.add_argument("--max-pack-size-mb", type=int, default=25)
    args = parser.parse_args()
    try:
        res = import_research_result(
            archive=args.archive,
            job_root=args.job_root,
            import_root=args.import_root,
            latest_pointer=args.latest_pointer,
            max_pack_size_mb=int(args.max_pack_size_mb),
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

