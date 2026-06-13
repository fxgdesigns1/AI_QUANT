#!/usr/bin/env python3
"""
Phase 8Y: build shared context pack from cached/local artifacts only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
PERF_DIR = Path("ARTIFACTS") / "performance"
DEFAULT_OUTPUT_DIR = PERF_DIR / "phase8y_shared_context_pack"
DEFAULT_MANIFEST_OUT = PERF_DIR / "latest_phase8y_shared_context_pack_manifest.json"
DEFAULT_COVERAGE = PERF_DIR / "latest_phase8y_data_coverage_manifest.json"
DEFAULT_COST = PERF_DIR / "latest_phase8y_api_cost_estimate.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def build_pack(repo_root: Path, *, output_dir: Path, coverage_path: Path, cost_path: Path) -> Dict[str, Any]:
    coverage = _read_json(coverage_path)
    cost = _read_json(cost_path)
    if not coverage:
        raise RuntimeError("missing_phase8y_coverage_manifest")
    if not cost:
        raise RuntimeError("missing_phase8y_cost_estimate")

    if not bool(coverage.get("safe_to_run_batch")) or not bool(cost.get("safe_to_run_batch")):
        raise RuntimeError("phase8y_preflight_fail_closed_manifest_blocked")

    output_dir.mkdir(parents=True, exist_ok=True)
    staged_dir = output_dir / "pack"
    if staged_dir.exists():
        shutil.rmtree(staged_dir)
    staged_dir.mkdir(parents=True, exist_ok=True)

    required_sources = [
        coverage_path,
        cost_path,
        repo_root / PERF_DIR / "latest_calendar_api_usage_report.json",
        repo_root / PERF_DIR / "latest_calendar_cache_manifest.json",
        repo_root / PERF_DIR / "latest_phase8r_aligned_context_manifest.json",
        repo_root / PERF_DIR / "latest_phase8r_provider_capability_report.json",
        repo_root / PERF_DIR / "latest_phase8o_news_provider_diagnostics.json",
    ]
    copied: List[Dict[str, Any]] = []
    for src in required_sources:
        if not src.is_file():
            continue
        dst = staged_dir / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "file": dst.name,
                "sha256": _sha256(dst),
                "size_bytes": int(dst.stat().st_size),
            }
        )

    archive_base = output_dir / "phase8y_shared_context_pack"
    archive_path = Path(shutil.make_archive(str(archive_base), "gztar", root_dir=staged_dir))
    copied.append(
        {
            "file": archive_path.name,
            "sha256": _sha256(archive_path),
            "size_bytes": int(archive_path.stat().st_size),
        }
    )
    return {
        "generated_at_utc": _iso_now(),
        "phase": "Phase 8Y",
        "classification": "PHASE8Y_SHARED_CONTEXT_PACK_MANIFEST",
        "output_dir": str(output_dir),
        "pack_dir": str(staged_dir),
        "archive_path": str(archive_path),
        "files": copied,
        "safe_to_run_batch": True,
        "paper_review_only": True,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8Y shared context pack builder.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUT)
    parser.add_argument("--coverage-manifest", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--cost-estimate", type=Path, default=DEFAULT_COST)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else (repo_root / args.output_dir)
    manifest_output = args.manifest_output if args.manifest_output.is_absolute() else (repo_root / args.manifest_output)
    coverage_path = args.coverage_manifest if args.coverage_manifest.is_absolute() else (repo_root / args.coverage_manifest)
    cost_path = args.cost_estimate if args.cost_estimate.is_absolute() else (repo_root / args.cost_estimate)
    try:
        manifest = build_pack(repo_root, output_dir=output_dir, coverage_path=coverage_path, cost_path=cost_path)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_output), "archive": manifest.get("archive_path")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
