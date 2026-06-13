#!/usr/bin/env python3
"""
Phase 8Y: verify shared context pack checksums.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
PERF_DIR = Path("ARTIFACTS") / "performance"
DEFAULT_MANIFEST = PERF_DIR / "latest_phase8y_shared_context_pack_manifest.json"
DEFAULT_OUTPUT = PERF_DIR / "latest_phase8y_context_pack_verification.json"


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


def verify(manifest_path: Path) -> Dict[str, Any]:
    m = _read_json(manifest_path)
    if not m:
        return {
            "ok": False,
            "all_files_verified": False,
            "error": "missing_or_invalid_pack_manifest",
            "checked_files": [],
        }
    checks: List[Dict[str, Any]] = []
    all_ok = True
    output_dir = Path(m.get("output_dir") or "")
    for f in m.get("files") or []:
        if not isinstance(f, dict):
            continue
        name = str(f.get("file") or "")
        expected = str(f.get("sha256") or "")
        if not name:
            continue
        candidate = output_dir / "pack" / name
        if not candidate.is_file():
            candidate = output_dir / name
        exists = candidate.is_file()
        actual = _sha256(candidate) if exists else None
        ok = bool(exists and expected and actual == expected)
        checks.append(
            {
                "file": name,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "exists": exists,
                "ok": ok,
            }
        )
        all_ok = all_ok and ok

    return {
        "ok": all_ok,
        "all_files_verified": all_ok,
        "phase": "Phase 8Y",
        "classification": "PHASE8Y_SHARED_CONTEXT_PACK_VERIFICATION",
        "generated_at_utc": _iso_now(),
        "manifest_path": str(manifest_path),
        "checked_files": checks,
        "paper_review_only": True,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Phase 8Y shared context pack.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else (repo_root / args.manifest)
    output = args.output if args.output.is_absolute() else (repo_root / args.output)
    payload = verify(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": payload.get("ok"), "all_files_verified": payload.get("all_files_verified"), "output": str(output)}, indent=2))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
