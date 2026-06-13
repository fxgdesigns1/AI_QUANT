#!/usr/bin/env python3
"""
Phase 8L: Verify compact result pack (tar.gz) before copy-back to ALPHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_MAX_RESULT_PACK_SIZE_MB = 25

ALLOWED_FILES: Set[str] = {
    "phase8l_backtest_summary.json",
    "phase8l_replay_samples_compact.jsonl",
    "phase8l_monthly_persistence.json",
    "phase8l_daily_persistence.json",
    "phase8l_recommendation.json",
    "phase8l_run_manifest.json",
    "checksums.sha256",
}

FORBIDDEN_PATH_PREFIXES: Tuple[str, ...] = (
    "raw_candles/",
    "candle_cache/",
    "venv/",
    ".venv/",
    ".git/",
    "node_modules/",
)

FORBIDDEN_NAMES: Tuple[str, ...] = (
    ".env",
    "secrets",
)

SUMMARY_REQUIRED_FIELDS: Tuple[str, ...] = (
    "generated_at_utc",
    "phase",
    "classification",
    "machine_role",
    "dataset_start_utc",
    "dataset_end_utc",
    "instruments",
    "granularities",
    "session_window_utc",
    "replay_mode",
    "candidate_count",
    "resolved_count",
    "win_count",
    "loss_count",
    "breakeven_count",
    "win_rate",
    "expectancy_r",
    "profit_factor_r",
    "max_loss_streak",
    "drawdown_proxy_r",
    "news_reconstruction_available",
    "calendar_reconstruction_available",
    "recommendation_label",
    "paper_review_only",
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)

SAFETY_FLAGS_REQUIRED_FALSE: Tuple[str, ...] = (
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)


class VerificationError(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _safe_member_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _is_forbidden_path(name: str) -> bool:
    norm = _safe_member_name(name)
    if norm == "" or norm.endswith("/"):
        return True
    if ".." in norm.split("/"):
        return True
    if any(norm.startswith(p) for p in FORBIDDEN_PATH_PREFIXES):
        return True
    base = norm.split("/")[-1]
    if base in FORBIDDEN_NAMES:
        return True
    if "secret" in base.lower():
        return True
    return False


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise VerificationError(f"invalid_json:{path.name}:{str(e)[:200]}")


def _require_fields(obj: Dict[str, Any], required: Iterable[str], label: str) -> None:
    missing = [k for k in required if k not in obj]
    if missing:
        raise VerificationError(f"missing_required_fields:{label}:{missing}")


def _require_safety_flags(obj: Dict[str, Any], label: str) -> None:
    if obj.get("paper_review_only") is not True:
        raise VerificationError(f"safety_flag_violation:{label}:paper_review_only")
    for k in SAFETY_FLAGS_REQUIRED_FALSE:
        if obj.get(k) is not False:
            raise VerificationError(f"safety_flag_violation:{label}:{k}")


def _parse_checksums_sha256(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([a-fA-F0-9]{64})  (.+)$", line)
        if not m:
            raise VerificationError("invalid_checksums_format")
        out[m.group(2)] = m.group(1).lower()
    return out


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    pack_path: str
    pack_size_bytes: int
    files_present: List[str]
    sha256_verified: bool


def verify_result_pack(archive_path: Path, *, max_size_mb: int = DEFAULT_MAX_RESULT_PACK_SIZE_MB) -> VerifyResult:
    if not archive_path.is_file():
        raise VerificationError("archive_not_found")

    pack_size_bytes = int(archive_path.stat().st_size)
    if pack_size_bytes > int(max_size_mb) * 1024 * 1024:
        raise VerificationError(f"archive_size_exceeded:{pack_size_bytes}")

    with tarfile.open(archive_path, mode="r:gz") as tf:
        members = tf.getmembers()
        if not members:
            raise VerificationError("empty_archive")

        member_names = [_safe_member_name(m.name) for m in members if m.isfile()]
        if not member_names:
            raise VerificationError("no_files_in_archive")

        split = [n.split("/") for n in member_names]
        top = split[0][0] if split and split[0] else None
        if top and all(parts and parts[0] == top for parts in split):
            rel_files = ["/".join(parts[1:]) for parts in split if len(parts) > 1]
        else:
            rel_files = member_names

        rel_files = [f for f in rel_files if f]

        for f in rel_files:
            if _is_forbidden_path(f):
                raise VerificationError(f"forbidden_path:{f}")

        for f in rel_files:
            if "/" in f:
                raise VerificationError(f"nested_paths_not_allowed:{f}")
            if f not in ALLOWED_FILES:
                raise VerificationError(f"unexpected_file:{f}")

        missing = sorted([fn for fn in ALLOWED_FILES if fn != "phase8l_replay_samples_compact.jsonl" and fn not in rel_files])
        if missing:
            raise VerificationError(f"missing_required_files:{missing}")

        with tempfile.TemporaryDirectory() as td:
            extract_root = Path(td)
            try:
                tf.extractall(path=extract_root, filter="data")
            except TypeError:
                tf.extractall(path=extract_root)

            candidates = list(extract_root.iterdir())
            base = candidates[0] if len(candidates) == 1 and candidates[0].is_dir() else extract_root

            checksums_path = base / "checksums.sha256"
            sha256_verified = False
            if checksums_path.is_file():
                expected = _parse_checksums_sha256(checksums_path.read_text(encoding="utf-8"))
                for rel, digest in expected.items():
                    if rel == "checksums.sha256":
                        continue
                    p = base / rel
                    if not p.is_file():
                        raise VerificationError(f"checksums_missing_file:{rel}")
                    actual = _sha256_bytes(p.read_bytes())
                    if actual.lower() != digest.lower():
                        raise VerificationError(f"checksum_mismatch:{rel}")
                sha256_verified = True

            summary = _load_json(base / "phase8l_backtest_summary.json")
            _require_fields(summary, SUMMARY_REQUIRED_FIELDS, "summary")
            if str(summary.get("phase", "")) not in ("Phase 8L",):
                raise VerificationError("wrong_phase_summary")
            _require_safety_flags(summary, "summary")

            rec = _load_json(base / "phase8l_recommendation.json")
            _require_fields(
                rec,
                (
                    "generated_at_utc",
                    "phase",
                    "classification",
                    "recommendation_label",
                    "paper_review_only",
                    "live_permission",
                    "ny_live_enabled",
                    "send_trade_unlock_changed",
                    "execution_paths_changed",
                ),
                "recommendation",
            )
            if str(rec.get("phase", "")) not in ("Phase 8L",):
                raise VerificationError("wrong_phase_recommendation")
            _require_safety_flags(rec, "recommendation")

            _ = _load_json(base / "phase8l_run_manifest.json")
            _ = _load_json(base / "phase8l_monthly_persistence.json")
            _ = _load_json(base / "phase8l_daily_persistence.json")

            files_present = sorted([p.name for p in base.iterdir() if p.is_file()])
            return VerifyResult(
                ok=True,
                pack_path=str(archive_path),
                pack_size_bytes=pack_size_bytes,
                files_present=files_present,
                sha256_verified=sha256_verified,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="Path to phase8l_result_pack.tar.gz")
    parser.add_argument("--max-pack-size-mb", type=int, default=DEFAULT_MAX_RESULT_PACK_SIZE_MB)
    args = parser.parse_args()

    try:
        res = verify_result_pack(args.archive, max_size_mb=args.max_pack_size_mb)
        print(
            json.dumps(
                {
                    "ok": True,
                    "pack_path": res.pack_path,
                    "pack_size_bytes": res.pack_size_bytes,
                    "files_present": res.files_present,
                    "sha256_verified": res.sha256_verified,
                    "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
                indent=2,
            )
        )
        return 0
    except VerificationError as e:
        print(json.dumps({"ok": False, "error": str(e), "pack_path": str(args.archive)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
