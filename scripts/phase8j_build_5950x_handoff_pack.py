#!/usr/bin/env python3
"""
Phase 8J: Build a compact ALPHA->5950X research-offload handoff pack.

Hard constraints:
- Read-only export of compact evidence inputs only
- Enforce strict size cap (default 25 MB)
- Emit manifest + sha256 checksums + README
- Do NOT touch runtime/config.yaml or any execution paths
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]


PHASE = "Phase 8J"
CLASSIFICATION_PASS = "PASS_5950X_HANDOFF_READY"
CLASSIFICATION_FAIL = "FAIL_5950X_HANDOFF_INCOMPLETE"


DEFAULT_OUTPUT_DIR = Path("ARTIFACTS/performance/offloads")
DEFAULT_MAX_PACK_SIZE_MB = 25


SOURCE_ARTIFACTS: List[Dict[str, Any]] = [
    {
        "path": "ARTIFACTS/performance/latest_phase8g_lightweight_reconstruction_audit.json",
        "required": True,
        "purpose": "Latest ALPHA-safe audit and offload decision",
    },
    {
        "path": "ARTIFACTS/performance/latest_phase8g_reconstruction_accuracy_audit.json",
        "required": False,
        "purpose": "Detailed granularity/reconstruction audit if present",
    },
    {
        "path": "ARTIFACTS/performance/latest_phase8h_archived_candidate_inventory.json",
        "required": True,
        "purpose": "Archived candidate inventory and exact replay feasibility",
    },
    {
        "path": "ARTIFACTS/performance/latest_phase8i_forward_archive_completeness.json",
        "required": True,
        "purpose": "Forward archive completeness/readiness",
    },
    {
        "path": "ARTIFACTS/performance/latest_daily_evidence_journal.json",
        "required": True,
        "purpose": "Latest Phase 8C/8E forward evidence state",
    },
    {
        "path": "ARTIFACTS/performance/pair_session_scorecard.json",
        "required": True,
        "purpose": "Aggregate scorecard context (including old NY EUR_USD row)",
    },
    {
        "path": "ARTIFACTS/performance/pair_session_paper_review_log.jsonl",
        "required": True,
        "purpose": "Forward paper-review candidate log",
    },
    {
        "path": "ARTIFACTS/performance/pair_session_candidate_archive_index.json",
        "required": False,
        "purpose": "Optional compact candidate archive index if present",
    },
]


STRICT_RULES: List[str] = [
    "Do not place trades",
    "Do not call broker execution APIs for order placement",
    "Do not enable NY live execution",
    "Do not change Send Trade unlock logic",
    "Do not loosen fail-closed gates",
    "Do not modify lane 010 manual_only policy",
    "Do not degrade lane 011 automated paper behavior",
    "Do not edit runtime/config.yaml",
    "Do not restart ai-quant-runner",
    "Do not run heavy backtests on ALPHA",
    "Do not pull large OANDA historical datasets on ALPHA",
    "Do not run Monte Carlo or parameter sweeps on ALPHA",
    "Do not copy huge candle caches back to ALPHA",
    "Do not copy the entire ARTIFACTS tree blindly",
]


EXPECTED_5950X_OUTPUTS: List[str] = [
    "phase8j_replay_summary.json",
    "phase8j_replay_samples_compact.jsonl",
    "phase8j_monthly_persistence.json",
    "phase8j_recommendation.json",
    "phase8j_run_manifest.json",
    "checksums.sha256",
]


def _utc_stamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _bytes_total_under(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            total += int(p.stat().st_size)
    return total


@dataclass(frozen=True)
class CopiedArtifact:
    source_rel: str
    dest_rel: str
    required: bool
    purpose: str
    exists: bool
    size_bytes: Optional[int]


def _copy_artifacts(
    repo_root: Path, pack_dir: Path, source_artifacts: List[Dict[str, Any]]
) -> Tuple[List[CopiedArtifact], List[str], List[str]]:
    copied: List[CopiedArtifact] = []
    missing_required: List[str] = []
    optional_included: List[str] = []

    for item in source_artifacts:
        rel = str(item["path"])
        required = bool(item.get("required"))
        purpose = str(item.get("purpose") or "")
        src = repo_root / rel
        dest = pack_dir / rel
        if not src.is_file():
            copied.append(
                CopiedArtifact(
                    source_rel=rel,
                    dest_rel=str(Path(rel)),
                    required=required,
                    purpose=purpose,
                    exists=False,
                    size_bytes=None,
                )
            )
            if required:
                missing_required.append(rel)
            continue

        _ensure_parent(dest)
        dest.write_bytes(src.read_bytes())
        size = int(dest.stat().st_size)
        copied.append(
            CopiedArtifact(
                source_rel=rel,
                dest_rel=str(Path(rel)),
                required=required,
                purpose=purpose,
                exists=True,
                size_bytes=size,
            )
        )
        if not required:
            optional_included.append(rel)

    return copied, missing_required, optional_included


def _write_checksums_sha256(pack_dir: Path, files: List[Path]) -> Dict[str, str]:
    sha_by_rel: Dict[str, str] = {}
    lines: List[str] = []
    for p in sorted(files, key=lambda x: str(x)):
        rel = str(p.relative_to(pack_dir)).replace("\\", "/")
        digest = _sha256_file(p)
        sha_by_rel[rel] = digest
        lines.append(f"{digest}  {rel}")
    (pack_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sha_by_rel["checksums.sha256"] = _sha256_file(pack_dir / "checksums.sha256")
    return sha_by_rel


def _write_readme(pack_dir: Path, pack_name: str, manifest_rel: str) -> None:
    text = "\n".join(
        [
            f"{pack_name}",
            "",
            "This is a compact research-offload handoff pack for the 5950X research estate.",
            "It is evidence-only and does not grant any live permission.",
            "",
            "Contents:",
            f"- manifest: {manifest_rel}",
            "- checksums: checksums.sha256",
            "- compact source artifacts copied under ARTIFACTS/performance/",
            "",
            "Strict rules (non-negotiable):",
            *[f"- {r}" for r in STRICT_RULES],
            "",
            "Expected 5950X outputs (compact result pack contract):",
            *[f"- {n}" for n in EXPECTED_5950X_OUTPUTS],
            "",
        ]
    )
    (pack_dir / "README_5950X_HANDOFF.md").write_text(text + "\n", encoding="utf-8")


def build_manifest(
    *,
    repo_root: Path,
    pack_dir: Path,
    archive_path: Path,
    max_pack_size_mb: int,
    copied: List[CopiedArtifact],
    missing_required: List[str],
    optional_included: List[str],
    sha256_by_file: Dict[str, str],
    classification: str,
) -> Dict[str, Any]:
    pack_size_bytes = _bytes_total_under(pack_dir)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": PHASE,
        "classification": classification,
        "alpha_hostname": socket.gethostname(),
        "repo_path": str(repo_root),
        "pack_path": str(pack_dir),
        "archive_path": str(archive_path),
        "pack_size_bytes": int(pack_size_bytes),
        "max_pack_size_mb": int(max_pack_size_mb),
        "source_artifacts": [
            {
                "path": c.source_rel,
                "required": c.required,
                "purpose": c.purpose,
                "exists": c.exists,
                "size_bytes": c.size_bytes,
            }
            for c in copied
        ],
        "missing_required_artifacts": sorted(missing_required),
        "optional_artifacts_included": sorted(optional_included),
        "sha256_by_file": sha256_by_file,
        "recommended_5950x_target_dir": "~/fxg-research/phase8j_replay",
        "research_questions": [
            "Run heavy NY EUR_USD exact replay (or best-available proxy) on 5950X only.",
            "Determine whether exact replay is possible for archived NY EUR_USD candidates (33/41 row context) without large backfills on ALPHA.",
            "Produce a compact result pack meeting the Phase8J contract.",
        ],
        "strict_rules": STRICT_RULES,
        "copy_to_5950x_commands": [
            "mkdir -p ~/fxg-research/phase8j_replay && cd ~/fxg-research/phase8j_replay",
            "gcloud compute scp --zone <ACTIVE_ALPHA_ZONE> --project fxg-ai-trading <ACTIVE_ALPHA_VM>:/opt/ai-quant/ARTIFACTS/performance/offloads/<PACK>.tar.gz ./",
            "tar -xzf <PACK>.tar.gz",
            "python3 -m json.tool <PACK_DIR>/manifest.json",
        ],
        "expected_5950x_outputs": EXPECTED_5950X_OUTPUTS,
        "copy_back_to_alpha_rules": [
            "Copy back only a compact result pack tar.gz (<= 25 MB).",
            "Do not copy candle caches or raw datasets back to ALPHA.",
            "Do not modify ALPHA runtime config or execution paths.",
        ],
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _tar_gz_directory(src_dir: Path, archive_path: Path) -> None:
    _ensure_parent(archive_path)
    with tarfile.open(archive_path, mode="w:gz") as tf:
        # Store as a single top-level directory for deterministic extraction.
        tf.add(src_dir, arcname=src_dir.name, recursive=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root (for tests). Defaults to auto-detected repo root.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory under repo root (default: ARTIFACTS/performance/offloads).",
    )
    parser.add_argument("--max-pack-size-mb", type=int, default=DEFAULT_MAX_PACK_SIZE_MB)
    parser.add_argument("--pack-name", default=None, help="Optional explicit pack directory name.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve() if args.repo_root else REPO_ROOT
    out_dir = (repo_root / args.output_directory).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pack_name = args.pack_name or f"phase8j_5950x_handoff_pack_{_utc_stamp_compact()}"
    pack_dir = out_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)

    copied, missing_required, optional_included = _copy_artifacts(repo_root, pack_dir, SOURCE_ARTIFACTS)

    manifest_path = pack_dir / "manifest.json"
    _write_readme(pack_dir, pack_name, "manifest.json")

    # checksums cover README + manifest + copied inputs only (not the tar itself)
    checksum_candidates: List[Path] = []
    for p in pack_dir.rglob("*"):
        if p.is_file() and p.name != "checksums.sha256":
            checksum_candidates.append(p)
    sha_by_rel = _write_checksums_sha256(pack_dir, checksum_candidates)

    archive_path = out_dir / f"{pack_name}.tar.gz"
    _tar_gz_directory(pack_dir, archive_path)

    classification = CLASSIFICATION_PASS if not missing_required else CLASSIFICATION_FAIL
    manifest = build_manifest(
        repo_root=repo_root,
        pack_dir=pack_dir,
        archive_path=archive_path,
        max_pack_size_mb=args.max_pack_size_mb,
        copied=copied,
        missing_required=missing_required,
        optional_included=optional_included,
        sha256_by_file=sha_by_rel,
        classification=classification,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    pack_size_bytes = _bytes_total_under(pack_dir)
    if pack_size_bytes > int(args.max_pack_size_mb) * 1024 * 1024:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "pack_size_exceeded",
                    "pack_size_bytes": pack_size_bytes,
                    "max_pack_size_mb": args.max_pack_size_mb,
                    "pack_dir": str(pack_dir),
                },
                indent=2,
            )
        )
        return 1

    latest_manifest = repo_root / "ARTIFACTS/performance/latest_phase8j_5950x_handoff_manifest.json"
    _ensure_parent(latest_manifest)
    latest_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if missing_required:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "missing_required_artifacts",
                    "missing_required_artifacts": sorted(missing_required),
                    "manifest_path": str(manifest_path),
                    "archive_path": str(archive_path),
                },
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "classification": classification,
                "pack_dir": str(pack_dir),
                "archive_path": str(archive_path),
                "latest_manifest": str(latest_manifest),
                "pack_size_bytes": pack_size_bytes,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

