#!/usr/bin/env python3
"""
Phase 8J: Import a verified compact 5950X result pack into ALPHA artifacts.

Hard constraints:
- Must verify pack contract + safety flags before import
- Import is write-only into ARTIFACTS/performance/imports/phase8j/<timestamp>/
- Must not touch runtime/config.yaml or any execution paths
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8j_verify_5950x_result_pack import (  # noqa: E402
    VerificationError,
    verify_result_pack,
)


DEFAULT_IMPORT_ROOT = Path("ARTIFACTS/performance/imports/phase8j")
LATEST_IMPORT_MANIFEST = Path("ARTIFACTS/performance/latest_phase8j_5950x_import_manifest.json")


def _utc_stamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _extract_into(archive: Path, dst_dir: Path) -> None:
    _ensure_dir(dst_dir)
    with tarfile.open(archive, mode="r:gz") as tf:
        tf.extractall(path=dst_dir)


def _find_payload_root(extract_dir: Path) -> Path:
    # Accept either a single top-level directory or flat extraction.
    children = list(extract_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="Path to phase8j_5950x_result_pack.tar.gz")
    parser.add_argument("--import-root", type=Path, default=DEFAULT_IMPORT_ROOT)
    parser.add_argument("--max-pack-size-mb", type=int, default=25)
    args = parser.parse_args()

    repo_root = REPO_ROOT
    archive = args.archive.expanduser().resolve()

    try:
        _ = verify_result_pack(archive, max_size_mb=args.max_pack_size_mb)
    except VerificationError as e:
        print(json.dumps({"ok": False, "reason": "verification_failed", "error": str(e)}, indent=2))
        return 1

    import_root = (repo_root / args.import_root).resolve()
    ts = _utc_stamp_compact()
    dest_dir = import_root / ts
    _ensure_dir(dest_dir)

    staging = dest_dir / "_staging_extract"
    _ensure_dir(staging)
    _extract_into(archive, staging)
    payload_root = _find_payload_root(staging)

    # Copy allowed payload files into dest_dir root (flat)
    allowed = [
        "phase8j_replay_summary.json",
        "phase8j_replay_samples_compact.jsonl",
        "phase8j_monthly_persistence.json",
        "phase8j_recommendation.json",
        "phase8j_run_manifest.json",
        "checksums.sha256",
    ]
    copied: List[str] = []
    sha_by_file: Dict[str, str] = {}
    for name in allowed:
        src = payload_root / name
        if not src.is_file():
            # samples jsonl may be missing (contract allows minimal)
            if name == "phase8j_replay_samples_compact.jsonl":
                continue
            print(json.dumps({"ok": False, "reason": "missing_required_payload_file", "file": name}, indent=2))
            return 1
        dst = dest_dir / name
        dst.write_bytes(src.read_bytes())
        copied.append(name)
        sha_by_file[name] = _sha256_file(dst)

    # Write import manifest + latest pointer
    import_manifest: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 8J",
        "classification": "IMPORTED_5950X_RESULT_PACK",
        "source_archive_path": str(archive),
        "import_dir": str(dest_dir),
        "copied_files": copied,
        "sha256_by_file": sha_by_file,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    (dest_dir / "phase8j_import_manifest.json").write_text(json.dumps(import_manifest, indent=2), encoding="utf-8")

    latest = (repo_root / LATEST_IMPORT_MANIFEST).resolve()
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(import_manifest, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "import_dir": str(dest_dir), "latest_import_manifest": str(latest)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

