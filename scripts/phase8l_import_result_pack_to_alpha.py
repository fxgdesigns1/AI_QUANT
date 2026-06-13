#!/usr/bin/env python3
"""
Phase 8L: Import verified compact result pack into ALPHA ARTIFACTS/performance/imports/phase8l.

Does not edit the VM runtime configuration file or execution paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8l_verify_result_pack import VerificationError, verify_result_pack  # noqa: E402


DEFAULT_IMPORT_ROOT = Path("ARTIFACTS/performance/imports/phase8l")
LATEST_MANIFEST = Path("ARTIFACTS/performance/latest_phase8l_research_result_manifest.json")
LATEST_SUMMARY = Path("ARTIFACTS/performance/latest_phase8l_backtest_summary.json")
LATEST_REC = Path("ARTIFACTS/performance/latest_phase8l_recommendation.json")


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
        try:
            tf.extractall(path=dst_dir, filter="data")
        except TypeError:
            tf.extractall(path=dst_dir)


def _find_payload_root(extract_dir: Path) -> Path:
    children = list(extract_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def _macbook_pull_commands() -> List[str]:
    return [
        "mkdir -p ~/fxg-phase8l-results",
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" '
        '"fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_research_result_manifest.json" '
        "~/fxg-phase8l-results/",
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" '
        '"fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_backtest_summary.json" '
        "~/fxg-phase8l-results/",
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" '
        '"fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8l_recommendation.json" '
        "~/fxg-phase8l-results/",
        "python3 -m json.tool ~/fxg-phase8l-results/latest_phase8l_backtest_summary.json",
        "python3 -m json.tool ~/fxg-phase8l-results/latest_phase8l_recommendation.json",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="Path to phase8l_result_pack.tar.gz on ALPHA")
    parser.add_argument("--import-root", type=Path, default=DEFAULT_IMPORT_ROOT)
    parser.add_argument("--max-pack-size-mb", type=int, default=25)
    args = parser.parse_args()

    repo_root = REPO_ROOT
    archive = args.archive.expanduser().resolve()

    try:
        vr = verify_result_pack(archive, max_size_mb=args.max_pack_size_mb)
    except VerificationError as e:
        print(json.dumps({"ok": False, "reason": "verification_failed", "error": str(e)}, indent=2))
        return 1

    import_root = (repo_root / args.import_root).resolve()
    ts = _utc_stamp_compact()
    dest_dir = import_root / f"phase8l_import_{ts}"
    _ensure_dir(dest_dir)

    staging = dest_dir / "_staging_extract"
    _ensure_dir(staging)
    _extract_into(archive, staging)
    payload_root = _find_payload_root(staging)

    allowed = [
        "phase8l_backtest_summary.json",
        "phase8l_replay_samples_compact.jsonl",
        "phase8l_monthly_persistence.json",
        "phase8l_daily_persistence.json",
        "phase8l_recommendation.json",
        "phase8l_run_manifest.json",
        "checksums.sha256",
    ]
    copied: List[str] = []
    sha_by_file: Dict[str, str] = {}
    for name in allowed:
        src = payload_root / name
        if not src.is_file():
            if name == "phase8l_replay_samples_compact.jsonl":
                continue
            print(json.dumps({"ok": False, "reason": "missing_required_payload_file", "file": name}, indent=2))
            return 1
        dst = dest_dir / name
        dst.write_bytes(src.read_bytes())
        copied.append(name)
        sha_by_file[name] = _sha256_file(dst)

    summary = json.loads((dest_dir / "phase8l_backtest_summary.json").read_text(encoding="utf-8"))
    rec = json.loads((dest_dir / "phase8l_recommendation.json").read_text(encoding="utf-8"))

    summary_metrics = {
        "expectancy_r": summary.get("expectancy_r"),
        "profit_factor_r": summary.get("profit_factor_r"),
        "max_loss_streak": summary.get("max_loss_streak"),
        "drawdown_proxy_r": summary.get("drawdown_proxy_r"),
        "resolved_count": summary.get("resolved_count"),
        "replay_mode": summary.get("replay_mode"),
    }

    import_manifest: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase": "Phase 8L",
        "classification": "IMPORTED_RESEARCH_RESULT_PACK",
        "source_machine_role": "5950X",
        "alpha_hostname": socket.gethostname(),
        "import_dir": str(dest_dir),
        "source_result_pack": str(archive),
        "result_pack_size_bytes": int(archive.stat().st_size),
        "max_result_pack_size_mb": int(args.max_pack_size_mb),
        "sha256_verified": bool(vr.sha256_verified),
        "files_imported": copied,
        "latest_summary_pointer": str((repo_root / LATEST_SUMMARY).resolve()),
        "latest_recommendation_pointer": str((repo_root / LATEST_REC).resolve()),
        "latest_manifest_pointer": str((repo_root / LATEST_MANIFEST).resolve()),
        "summary_metrics": summary_metrics,
        "recommendation_label": rec.get("recommendation_label"),
        "macbook_pull_commands": _macbook_pull_commands(),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    (dest_dir / "phase8l_alpha_import_manifest.json").write_text(
        json.dumps(import_manifest, indent=2), encoding="utf-8"
    )

    latest_m = (repo_root / LATEST_MANIFEST).resolve()
    latest_s = (repo_root / LATEST_SUMMARY).resolve()
    latest_r = (repo_root / LATEST_REC).resolve()
    for p in (latest_m.parent, latest_s.parent, latest_r.parent):
        p.mkdir(parents=True, exist_ok=True)

    latest_m.write_text(json.dumps(import_manifest, indent=2), encoding="utf-8")
    latest_s.write_bytes((dest_dir / "phase8l_backtest_summary.json").read_bytes())
    latest_r.write_bytes((dest_dir / "phase8l_recommendation.json").read_bytes())

    print(
        json.dumps(
            {
                "ok": True,
                "import_dir": str(dest_dir),
                "latest_phase8l_research_result_manifest": str(latest_m),
                "latest_phase8l_backtest_summary": str(latest_s),
                "latest_phase8l_recommendation": str(latest_r),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
