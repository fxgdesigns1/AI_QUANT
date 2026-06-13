#!/usr/bin/env python3
"""
Phase 8U: write redacted Stitch project inventory artifact.

Input is a local JSON snapshot generated from MCP `list_projects` / `list_screens`
output. This script avoids storing secrets and only keeps structural metadata.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = Path("artifacts/PHASE8U_STITCH_PROJECTS_SNAPSHOT.json")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _redact_projects(projects: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in projects:
        name = str(p.get("name") or "")
        out.append(
            {
                "project_name": name,
                "project_id": name.split("/")[-1] if "/" in name else name,
                "title": p.get("title"),
                "visibility": p.get("visibility"),
                "origin": p.get("origin"),
                "device_type": p.get("deviceType"),
                "project_type": p.get("projectType"),
                "update_time": p.get("updateTime"),
                "screen_instances_count": len(p.get("screenInstances") or []),
            }
        )
    return out


def _redact_screens(screens: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in screens:
        name = str(s.get("name") or "")
        out.append(
            {
                "screen_name": name,
                "screen_id": name.split("/")[-1] if "/" in name else name,
                "title": s.get("title"),
                "device_type": s.get("deviceType"),
                "width": s.get("width"),
                "height": s.get("height"),
                "html_mime_type": ((s.get("htmlCode") or {}).get("mimeType")),
                "has_html_download_url": bool((s.get("htmlCode") or {}).get("downloadUrl")),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Write redacted Phase 8U Stitch inventory artifact.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--snapshot-json", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()
    snapshot_path = args.snapshot_json if args.snapshot_json.is_absolute() else repo / args.snapshot_json
    if not snapshot_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_snapshot_json", "path": str(snapshot_path)}, indent=2))
        return 1

    snap = _read_json(snapshot_path)
    projects = _redact_projects(list(snap.get("projects") or []))
    screens = _redact_screens(list(snap.get("screens") or []))
    target_project_id = str(snap.get("target_project_id") or "")
    found = any(p.get("project_id") == target_project_id for p in projects)

    report = {
        "ok": True,
        "phase": "Phase 8U",
        "classification": "PHASE8U_STITCH_PROJECT_INVENTORY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target_project_id": target_project_id,
        "target_project_found": found,
        "projects": projects,
        "screens": screens,
        "notes": "Redacted inventory generated from Stitch MCP metadata. Secrets and auth values are excluded.",
    }

    out_path = repo / "artifacts" / f"PHASE8U_STITCH_PROJECT_INVENTORY_{_utc_stamp()}.json"
    if args.write:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "target_project_found": found,
                "projects_count": len(projects),
                "screens_count": len(screens),
                "inventory_path": str(out_path),
            },
            indent=2,
        )
    )
    return 0 if found else 2


if __name__ == "__main__":
    raise SystemExit(main())
