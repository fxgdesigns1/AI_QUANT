#!/usr/bin/env python3
"""
Phase 8M: ALPHA-side data preparation for a queued research job.

Uses existing ALPHA environment credentials for historical/read-only data export only.
Produces a compact job input pack for the 5950X worker.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8l_alpha_export_research_data import run_export  # noqa: E402
from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    DEFAULT_ALPHA_JOB_ROOT,
    find_job_file,
    queue_dirs,
    read_json,
    utc_now_iso_z,
    validate_job,
    write_json,
)

_SERVICE_ENV_CANDIDATES = (Path("/etc/ai-quant/.env"), Path("/opt/ai-quant/.env"))


def _merge_service_env_file(path: Path) -> None:
    """Non-login sudo often has no OANDA_*; mirror shell `source` without printing values."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _load_job(job_root: Path, *, job_id: Optional[str], job_file: Optional[Path]) -> Dict[str, Any]:
    if job_file is not None:
        job = read_json(job_file)
    elif job_id:
        found = find_job_file(job_root, job_id)
        if not found:
            raise ContractError(f"job_not_found:{job_id}")
        job = read_json(found)
    else:
        raise ContractError("job_id_or_job_file_required")
    validate_job(job)
    return job


def _granularities_for_job(job: Dict[str, Any]) -> List[str]:
    params = job.get("params") or {}
    primary = str(params.get("granularity") or "M15").upper()
    if job.get("job_type") == "phase8l_backtest":
        ordered = [primary, "M5"]
        return list(dict.fromkeys(ordered))
    return [primary]


def prepare_job_data_export(
    *,
    job_root: Path,
    job_id: Optional[str] = None,
    job_file: Optional[Path] = None,
    max_export_size_mb: float = 50.0,
    max_context_rows: int = 400,
    overwrite: bool = False,
) -> Dict[str, Any]:
    for env_path in _SERVICE_ENV_CANDIDATES:
        _merge_service_env_file(env_path)
    job = _load_job(job_root, job_id=job_id, job_file=job_file)
    params = job.get("params") or {}
    job_id_s = str(job["job_id"])
    inputs_dir = queue_dirs(job_root)["inputs"] / job_id_s
    export_dir = inputs_dir / "alpha_export"
    pack_path = inputs_dir / "phase8m_job_input_pack.tar.gz"
    if inputs_dir.exists() and overwrite:
        shutil.rmtree(inputs_dir)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    write_json(inputs_dir / "phase8m_job.json", job)

    export_res = run_export(
        days=int(params.get("lookback_days") or 14),
        instruments=[str(params.get("instrument") or "EUR_USD").upper()],
        granularities=_granularities_for_job(job),
        output_dir=export_dir,
        max_export_size_bytes=int(float(max_export_size_mb) * 1024 * 1024),
        dry_run_plan=False,
        write_export=True,
        max_context_rows=int(max_context_rows),
    )
    if not export_res.get("ok"):
        raise ContractError(f"alpha_export_failed:{export_res}")

    input_manifest = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": "Phase 8M",
        "classification": "RESEARCH_JOB_INPUT_PACK",
        "job_id": job_id_s,
        "job_type": job.get("job_type"),
        "job_file": str(job_file) if job_file else None,
        "alpha_export_manifest": str(export_dir / "phase8l_alpha_export_manifest.json"),
        "pack_path": str(pack_path.resolve()),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    write_json(inputs_dir / "phase8m_job_input_manifest.json", input_manifest)

    with tarfile.open(pack_path, mode="w:gz") as tf:
        tf.add(inputs_dir / "phase8m_job.json", arcname="phase8m_job.json")
        tf.add(inputs_dir / "phase8m_job_input_manifest.json", arcname="phase8m_job_input_manifest.json")
        for p in sorted(export_dir.iterdir()):
            if p.is_file():
                tf.add(p, arcname=f"alpha_export/{p.name}")

    pack_path_abs = pack_path.resolve()
    input_manifest["pack_path"] = str(pack_path_abs)
    input_manifest["pack_size_bytes"] = int(pack_path_abs.stat().st_size)
    write_json(inputs_dir / "phase8m_job_input_manifest.json", input_manifest)
    return {"ok": True, "job_id": job_id_s, "input_pack": str(pack_path_abs), "input_manifest": input_manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase 8M job input export on ALPHA.")
    parser.add_argument("--job-root", type=Path, default=DEFAULT_ALPHA_JOB_ROOT)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--job-file", type=Path, default=None)
    parser.add_argument("--max-export-size-mb", type=float, default=50.0)
    parser.add_argument("--max-context-rows", type=int, default=400)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        res = prepare_job_data_export(
            job_root=args.job_root,
            job_id=args.job_id,
            job_file=args.job_file,
            max_export_size_mb=float(args.max_export_size_mb),
            max_context_rows=int(args.max_context_rows),
            overwrite=bool(args.overwrite),
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

