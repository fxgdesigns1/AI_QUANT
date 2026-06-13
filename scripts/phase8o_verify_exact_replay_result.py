#!/usr/bin/env python3
"""
Phase 8O: verify compact exact replay result pack and optionally import it to ALPHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

PHASE = "Phase 8O"
DEFAULT_MAX_RESULT_PACK_SIZE_MB = 25

ALLOWED_FILES: Set[str] = {
    "phase8o_backtest_summary.json",
    "phase8o_replay_samples_compact.jsonl",
    "phase8o_monthly_persistence.json",
    "phase8o_daily_persistence.json",
    "phase8o_recommendation.json",
    "phase8o_run_manifest.json",
    "checksums.sha256",
}

SUMMARY_REQUIRED_FIELDS: Tuple[str, ...] = (
    "generated_at_utc",
    "phase",
    "classification",
    "replay_mode",
    "exact_strategy_replay",
    "instrument",
    "granularity",
    "lookback_days",
    "dataset_start_utc",
    "dataset_end_utc",
    "session_bucket",
    "candidate_count",
    "resolved_count",
    "clean_sample_count",
    "excluded_news_gated",
    "excluded_calendar_gated",
    "expectancy_r",
    "profit_factor_r",
    "win_rate",
    "max_loss_streak",
    "drawdown_proxy_r",
    "month_by_month_stats",
    "daily_stats",
    "recommendation_label",
    "news_reconstruction_available",
    "calendar_reconstruction_available",
    "paper_review_only",
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)

SAFETY_FALSE_FIELDS = (
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)

FORBIDDEN_PREFIXES = ("raw_candles/", "candle_cache/", ".git/", ".venv/", "venv/", "node_modules/")
FORBIDDEN_NAMES = (".env", "secrets")

LATEST_DISCOVERY = Path("ARTIFACTS/performance/latest_phase8o_strategy_discovery.json")
LATEST_SUMMARY = Path("ARTIFACTS/performance/latest_phase8o_backtest_summary.json")
LATEST_RESULT = Path("ARTIFACTS/performance/latest_phase8o_exact_replay_result.json")
LATEST_RECOMMENDATION = Path("ARTIFACTS/performance/latest_phase8o_recommendation.json")
DEFAULT_IMPORT_ROOT = Path("ARTIFACTS/performance/imports/phase8o")


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    pack_path: str
    pack_size_bytes: int
    files_present: List[str]
    sha256_verified: bool
    summary: Dict[str, Any]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def forbidden_path(name: str) -> bool:
    norm = safe_member_name(name)
    if not norm or norm.endswith("/"):
        return True
    if ".." in norm.split("/"):
        return True
    if any(norm.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    base = norm.split("/")[-1].lower()
    if base in FORBIDDEN_NAMES:
        return True
    return "secret" in base


def require_fields(obj: Dict[str, Any], required: Iterable[str], label: str) -> None:
    missing = [k for k in required if k not in obj]
    if missing:
        raise VerificationError(f"missing_required_fields:{label}:{missing}")


def require_safety(obj: Dict[str, Any], label: str) -> None:
    if obj.get("paper_review_only") is not True:
        raise VerificationError(f"safety_flag_violation:{label}:paper_review_only")
    for key in SAFETY_FALSE_FIELDS:
        if obj.get(key) is not False:
            raise VerificationError(f"safety_flag_violation:{label}:{key}")


def parse_checksums(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise VerificationError("invalid_checksums_format")
        out[parts[1]] = parts[0].lower()
    return out


def relative_files(member_names: List[str]) -> List[str]:
    split = [n.split("/") for n in member_names]
    top = split[0][0] if split and split[0] else None
    if top and all(parts and parts[0] == top for parts in split):
        return ["/".join(parts[1:]) for parts in split if len(parts) > 1]
    return member_names


def verify_result_pack(archive_path: Path, *, max_size_mb: int = DEFAULT_MAX_RESULT_PACK_SIZE_MB) -> VerifyResult:
    archive_path = archive_path.expanduser().resolve()
    if not archive_path.is_file():
        raise VerificationError("archive_not_found")
    pack_size = int(archive_path.stat().st_size)
    if pack_size > int(max_size_mb) * 1024 * 1024:
        raise VerificationError(f"archive_size_exceeded:{pack_size}")

    with tarfile.open(archive_path, mode="r:gz") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]
        names = [safe_member_name(m.name) for m in members]
        if any(forbidden_path(n) for n in names):
            raise VerificationError("forbidden_path_in_archive")
        rel_files = relative_files(names)
        if not set(rel_files).issubset(ALLOWED_FILES):
            raise VerificationError(f"unexpected_files:{sorted(set(rel_files) - ALLOWED_FILES)}")
        required = ALLOWED_FILES - {"phase8o_replay_samples_compact.jsonl"}
        if not required.issubset(set(rel_files)):
            raise VerificationError(f"missing_required_files:{sorted(required - set(rel_files))}")

        by_rel: Dict[str, bytes] = {}
        for member, rel_name in zip(members, rel_files):
            f = tf.extractfile(member)
            if f is None:
                continue
            by_rel[rel_name] = f.read()
        summary = json.loads(by_rel["phase8o_backtest_summary.json"].decode("utf-8"))
        recommendation = json.loads(by_rel["phase8o_recommendation.json"].decode("utf-8"))
        run_manifest = json.loads(by_rel["phase8o_run_manifest.json"].decode("utf-8"))
        require_fields(summary, SUMMARY_REQUIRED_FIELDS, "summary")
        require_safety(summary, "summary")
        require_safety(recommendation, "recommendation")
        require_safety(run_manifest, "run_manifest")
        if summary.get("phase") != PHASE:
            raise VerificationError("summary_phase_mismatch")
        if summary.get("classification", "").startswith("PASS_") and summary.get("exact_strategy_replay") is not True:
            raise VerificationError("pass_classification_requires_exact_strategy_replay_true")
        checksums = parse_checksums(by_rel["checksums.sha256"].decode("utf-8"))
        for name, digest in checksums.items():
            if name == "checksums.sha256":
                continue
            if name not in by_rel:
                raise VerificationError(f"checksum_file_missing:{name}")
            actual = sha256_bytes(by_rel[name])
            if actual != digest:
                raise VerificationError(f"checksum_mismatch:{name}")

    return VerifyResult(
        ok=True,
        pack_path=str(archive_path),
        pack_size_bytes=pack_size,
        files_present=sorted(rel_files),
        sha256_verified=True,
        summary=summary,
    )


def extract_safe(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:gz") as tf:
        try:
            tf.extractall(path=dest, filter="data")
        except TypeError:
            tf.extractall(path=dest)


def payload_root(extract_dir: Path) -> Path:
    children = list(extract_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def macbook_pull_commands() -> List[str]:
    return [
        "mkdir -p ~/fxg-phase8o-results",
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_strategy_discovery.json" ~/fxg-phase8o-results/',
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_backtest_summary.json" ~/fxg-phase8o-results/',
        'gcloud compute scp --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026:/opt/ai-quant/ARTIFACTS/performance/latest_phase8o_recommendation.json" ~/fxg-phase8o-results/',
        "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_strategy_discovery.json",
        "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_backtest_summary.json",
        "python3 -m json.tool ~/fxg-phase8o-results/latest_phase8o_recommendation.json",
    ]


def import_result_pack(
    *,
    archive: Path,
    repo_root: Path,
    import_root: Path = DEFAULT_IMPORT_ROOT,
    max_size_mb: int = DEFAULT_MAX_RESULT_PACK_SIZE_MB,
    discovery_report: Optional[Path] = None,
) -> Dict[str, Any]:
    verify = verify_result_pack(archive, max_size_mb=max_size_mb)
    repo_root = repo_root.expanduser().resolve()
    import_root_abs = (repo_root / import_root).resolve() if not import_root.is_absolute() else import_root.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = import_root_abs / f"phase8o_import_{stamp}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    staging = dest / "_staging_extract"
    extract_safe(archive.expanduser().resolve(), staging)
    root = payload_root(staging)

    copied: List[str] = []
    for name in ALLOWED_FILES:
        src = root / name
        if src.is_file():
            (dest / name).write_bytes(src.read_bytes())
            copied.append(name)

    summary = json.loads((dest / "phase8o_backtest_summary.json").read_text(encoding="utf-8"))
    recommendation = json.loads((dest / "phase8o_recommendation.json").read_text(encoding="utf-8"))
    manifest = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "IMPORTED_PHASE8O_EXACT_REPLAY_RESULT",
        "alpha_hostname": socket.gethostname(),
        "import_dir": str(dest),
        "source_result_pack": str(archive.expanduser().resolve()),
        "result_pack_size_bytes": verify.pack_size_bytes,
        "max_result_pack_size_mb": int(max_size_mb),
        "sha256_verified": verify.sha256_verified,
        "files_imported": sorted(copied),
        "summary_classification": summary.get("classification"),
        "recommendation_label": recommendation.get("recommendation_label"),
        "macbook_pull_commands": macbook_pull_commands(),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    (dest / "phase8o_alpha_import_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    pointers = {
        LATEST_SUMMARY: dest / "phase8o_backtest_summary.json",
        LATEST_RESULT: dest / "phase8o_backtest_summary.json",
        LATEST_RECOMMENDATION: dest / "phase8o_recommendation.json",
    }
    for pointer, src in pointers.items():
        dst = repo_root / pointer
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    if discovery_report and discovery_report.is_file():
        dst = repo_root / LATEST_DISCOVERY
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(discovery_report.read_bytes())

    return {
        "ok": True,
        "import_manifest": str(dest / "phase8o_alpha_import_manifest.json"),
        "latest_phase8o_backtest_summary": str(repo_root / LATEST_SUMMARY),
        "latest_phase8o_exact_replay_result": str(repo_root / LATEST_RESULT),
        "latest_phase8o_recommendation": str(repo_root / LATEST_RECOMMENDATION),
        "latest_phase8o_strategy_discovery": str(repo_root / LATEST_DISCOVERY) if discovery_report else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify/import Phase 8O exact replay result pack.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--max-pack-size-mb", type=int, default=DEFAULT_MAX_RESULT_PACK_SIZE_MB)
    parser.add_argument("--import-to-alpha", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--import-root", type=Path, default=DEFAULT_IMPORT_ROOT)
    parser.add_argument("--strategy-discovery", type=Path, default=None)
    args = parser.parse_args()

    try:
        if args.import_to_alpha:
            result = import_result_pack(
                archive=args.archive,
                repo_root=args.repo_root,
                import_root=args.import_root,
                max_size_mb=int(args.max_pack_size_mb),
                discovery_report=args.strategy_discovery,
            )
        else:
            verify = verify_result_pack(args.archive, max_size_mb=int(args.max_pack_size_mb))
            result = {
                "ok": verify.ok,
                "pack_path": verify.pack_path,
                "pack_size_bytes": verify.pack_size_bytes,
                "files_present": verify.files_present,
                "sha256_verified": verify.sha256_verified,
                "classification": verify.summary.get("classification"),
            }
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
