#!/usr/bin/env python3
"""
Phase 8M shared contract helpers for the research-job queue.

Pure filesystem/schema logic only. No broker, execution, or runtime configuration imports.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import tarfile
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

PHASE = "Phase 8M"
DEFAULT_ALPHA_JOB_ROOT = Path("ARTIFACTS/research_jobs")
DEFAULT_ALPHA_RESULT_IMPORT_ROOT = Path("ARTIFACTS/performance/imports/research_jobs")
DEFAULT_LATEST_RESULT_POINTER = Path("ARTIFACTS/performance/latest_research_job_result.json")
DEFAULT_MAX_RESULT_PACK_SIZE_MB = 25

STATUS_VALUES: Tuple[str, ...] = ("PENDING", "RUNNING", "DONE", "FAILED")
JOB_TYPES: Tuple[str, ...] = ("phase8l_backtest", "phase8k_replay")

SAFETY_REQUIRED: Dict[str, Any] = {
    "research_only": True,
    "paper_review_only": True,
    "live_permission": False,
    "ny_live_enabled": False,
    "send_trade_unlock_changed": False,
    "execution_paths_changed": False,
}

DEFAULT_PARAMS: Dict[str, Dict[str, Any]] = {
    "phase8l_backtest": {
        "instrument": "EUR_USD",
        "granularity": "M15",
        "lookback_days": 14,
        "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
        "session_window_utc": "13:30-16:00",
        "mode": "research_only",
    },
    "phase8k_replay": {
        "instrument": "EUR_USD",
        "granularity": "M15",
        "lookback_days": 180,
        "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
        "session_window_utc": "13:30-16:00",
        "mode": "research_only",
    },
}

RESULT_REQUIRED_FILES: Set[str] = {
    "research_job_result_manifest.json",
    "backtest_summary.json",
    "recommendation.json",
    "monthly_persistence.json",
    "daily_persistence.json",
    "replay_samples_compact.jsonl",
    "checksums.sha256",
}

RESULT_SUMMARY_REQUIRED_FIELDS: Tuple[str, ...] = (
    "generated_at_utc",
    "job_id",
    "phase",
    "job_type",
    "classification",
    "machine_role",
    "instrument",
    "granularity",
    "lookback_days",
    "session_bucket",
    "session_window_utc",
    "replay_mode",
    "candidate_count",
    "expectancy_r",
    "profit_factor_r",
    "max_loss_streak",
    "drawdown_proxy_r",
    "recommendation_label",
    "paper_review_only",
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)

FORBIDDEN_PATH_PREFIXES: Tuple[str, ...] = (
    "raw_candles/",
    "candle_cache/",
    ".git/",
    ".venv/",
    "venv/",
    "node_modules/",
)

FORBIDDEN_NAMES: Tuple[str, ...] = (
    ".env",
    "secrets",
    "large_raw_replay_dump.jsonl",
)


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifyResearchResult:
    ok: bool
    pack_path: str
    pack_size_bytes: int
    job_id: str
    files_present: List[str]
    sha256_verified: bool
    summary: Dict[str, Any]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def queue_dirs(job_root: Path) -> Dict[str, Path]:
    q = job_root / "queue"
    return {
        "pending": q / "pending",
        "running": q / "running",
        "done": q / "done",
        "failed": q / "failed",
        "inputs": job_root / "inputs",
    }


def ensure_job_dirs(job_root: Path) -> None:
    for p in queue_dirs(job_root).values():
        p.mkdir(parents=True, exist_ok=True)


def new_job_id(job_type: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:10]
    return f"{stamp}_{job_type}_{suffix}"


def normalize_params(job_type: str, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    if job_type not in JOB_TYPES:
        raise ContractError(f"unsupported_job_type:{job_type}")
    params = dict(DEFAULT_PARAMS[job_type])
    for k, v in dict(overrides or {}).items():
        if v is not None:
            params[k] = v
    params["instrument"] = str(params.get("instrument") or "EUR_USD").upper()
    params["granularity"] = str(params.get("granularity") or "M15").upper()
    params["lookback_days"] = int(params.get("lookback_days") or DEFAULT_PARAMS[job_type]["lookback_days"])
    params["mode"] = "research_only"
    return params


def result_contract() -> Dict[str, Any]:
    return {
        "max_result_pack_size_mb": DEFAULT_MAX_RESULT_PACK_SIZE_MB,
        "required_files": sorted(RESULT_REQUIRED_FILES),
        "summary_required_fields": list(RESULT_SUMMARY_REQUIRED_FIELDS),
    }


def build_job(
    *,
    job_type: str,
    params: Optional[Mapping[str, Any]] = None,
    requested_by: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized = normalize_params(job_type, params)
    job = {
        "job_id": job_id or new_job_id(job_type),
        "created_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "job_type": job_type,
        "status": "PENDING",
        "params": normalized,
        "safety": dict(SAFETY_REQUIRED),
        "requested_by": requested_by or f"{os.getenv('USERNAME') or os.getenv('USER') or 'unknown'}@{socket.gethostname()}",
        "result_contract": result_contract(),
    }
    validate_job(job)
    return job


def require_fields(obj: Mapping[str, Any], fields: Iterable[str], label: str) -> None:
    missing = [f for f in fields if f not in obj]
    if missing:
        raise ContractError(f"missing_required_fields:{label}:{missing}")


def validate_safety(safety: Mapping[str, Any], *, label: str = "safety") -> None:
    for k, expected in SAFETY_REQUIRED.items():
        if safety.get(k) is not expected:
            raise ContractError(f"safety_flag_violation:{label}:{k}:{safety.get(k)!r}")


def validate_job(job: Mapping[str, Any]) -> None:
    require_fields(
        job,
        ("job_id", "created_at_utc", "phase", "job_type", "status", "params", "safety", "requested_by", "result_contract"),
        "job",
    )
    if job.get("phase") != PHASE:
        raise ContractError("wrong_phase")
    if job.get("job_type") not in JOB_TYPES:
        raise ContractError(f"unsupported_job_type:{job.get('job_type')}")
    if job.get("status") not in STATUS_VALUES:
        raise ContractError(f"invalid_status:{job.get('status')}")
    validate_safety(job.get("safety") or {})
    params = job.get("params") or {}
    if str(params.get("mode")) != "research_only":
        raise ContractError("params_mode_must_be_research_only")
    if int(params.get("lookback_days") or 0) <= 0:
        raise ContractError("lookback_days_must_be_positive")


def write_json(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def job_file_for(job_root: Path, status: str, job_id: str) -> Path:
    key = status.lower()
    dirs = queue_dirs(job_root)
    if key not in dirs:
        raise ContractError(f"invalid_queue_status:{status}")
    return dirs[key] / f"{job_id}.json"


def find_job_file(job_root: Path, job_id: str) -> Optional[Path]:
    dirs = queue_dirs(job_root)
    for key in ("pending", "running", "done", "failed"):
        p = dirs[key] / f"{job_id}.json"
        if p.is_file():
            return p
    return None


def list_jobs(job_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    ensure_job_dirs(job_root)
    out: Dict[str, List[Dict[str, Any]]] = {"pending": [], "running": [], "done": [], "failed": []}
    dirs = queue_dirs(job_root)
    for key in out:
        for p in sorted(dirs[key].glob("*.json")):
            try:
                job = read_json(p)
                job["_path"] = str(p)
                out[key].append(job)
            except Exception as exc:
                out[key].append({"_path": str(p), "error": str(exc)})
    return out


def move_job(job_root: Path, job: Mapping[str, Any], from_status: str, to_status: str, updates: Optional[Mapping[str, Any]] = None) -> Path:
    ensure_job_dirs(job_root)
    job_id = str(job.get("job_id"))
    src = job_file_for(job_root, from_status, job_id)
    if not src.is_file():
        raise ContractError(f"job_not_in_{from_status}:{job_id}")
    new_job = dict(job)
    new_job["status"] = to_status.upper()
    if updates:
        new_job.update(dict(updates))
    validate_job(new_job)
    dst = job_file_for(job_root, to_status, job_id)
    write_json(dst, new_job)
    src.unlink()
    return dst


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(root: Path, names: Sequence[str]) -> None:
    lines = []
    for n in sorted(names):
        if n == "checksums.sha256":
            continue
        p = root / n
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {n}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def safe_member_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def is_forbidden_result_path(name: str) -> bool:
    norm = safe_member_name(name)
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


def parse_checksums_sha256(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([a-fA-F0-9]{64})  (.+)$", line)
        if not m:
            raise ContractError("invalid_checksums_format")
        out[m.group(2)] = m.group(1).lower()
    return out


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _extractall_safe(tf: tarfile.TarFile, path: Path) -> None:
    try:
        tf.extractall(path=path, filter="data")
    except TypeError:
        tf.extractall(path=path)


def verify_research_result_pack(
    archive_path: Path,
    *,
    max_size_mb: int = DEFAULT_MAX_RESULT_PACK_SIZE_MB,
) -> VerifyResearchResult:
    if not archive_path.is_file():
        raise ContractError("archive_not_found")
    pack_size = int(archive_path.stat().st_size)
    if pack_size > int(max_size_mb) * 1024 * 1024:
        raise ContractError(f"archive_size_exceeded:{pack_size}")

    with tarfile.open(archive_path, mode="r:gz") as tf:
        members = tf.getmembers()
        if not members:
            raise ContractError("empty_archive")
        member_names = [safe_member_name(m.name) for m in members if m.isfile()]
        if not member_names:
            raise ContractError("no_files_in_archive")

        split = [n.split("/") for n in member_names]
        top = split[0][0] if split and split[0] else None
        if top and all(parts and parts[0] == top for parts in split):
            rel_files = ["/".join(parts[1:]) for parts in split if len(parts) > 1]
        else:
            rel_files = member_names
        rel_files = [f for f in rel_files if f]

        for f in rel_files:
            if is_forbidden_result_path(f):
                raise ContractError(f"forbidden_path:{f}")
            if "/" in f:
                raise ContractError(f"nested_paths_not_allowed:{f}")
            if f not in RESULT_REQUIRED_FILES:
                raise ContractError(f"unexpected_file:{f}")

        missing = sorted(RESULT_REQUIRED_FILES - set(rel_files))
        if missing:
            raise ContractError(f"missing_required_files:{missing}")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _extractall_safe(tf, root)
            children = list(root.iterdir())
            base = children[0] if len(children) == 1 and children[0].is_dir() else root

            expected = parse_checksums_sha256((base / "checksums.sha256").read_text(encoding="utf-8"))
            for rel, digest in expected.items():
                if rel == "checksums.sha256":
                    continue
                p = base / rel
                if not p.is_file():
                    raise ContractError(f"checksums_missing_file:{rel}")
                actual = _sha256_bytes(p.read_bytes())
                if actual.lower() != digest.lower():
                    raise ContractError(f"checksum_mismatch:{rel}")

            summary = read_json(base / "backtest_summary.json")
            require_fields(summary, RESULT_SUMMARY_REQUIRED_FIELDS, "backtest_summary")
            if summary.get("phase") != PHASE:
                raise ContractError("wrong_phase_summary")
            validate_safety(
                {
                    "research_only": True,
                    "paper_review_only": summary.get("paper_review_only"),
                    "live_permission": summary.get("live_permission"),
                    "ny_live_enabled": summary.get("ny_live_enabled"),
                    "send_trade_unlock_changed": summary.get("send_trade_unlock_changed"),
                    "execution_paths_changed": summary.get("execution_paths_changed"),
                },
                label="backtest_summary",
            )

            rec = read_json(base / "recommendation.json")
            validate_safety(
                {
                    "research_only": True,
                    "paper_review_only": rec.get("paper_review_only"),
                    "live_permission": rec.get("live_permission"),
                    "ny_live_enabled": rec.get("ny_live_enabled"),
                    "send_trade_unlock_changed": rec.get("send_trade_unlock_changed"),
                    "execution_paths_changed": rec.get("execution_paths_changed"),
                },
                label="recommendation",
            )
            _ = read_json(base / "research_job_result_manifest.json")
            _ = read_json(base / "monthly_persistence.json")
            _ = read_json(base / "daily_persistence.json")

            return VerifyResearchResult(
                ok=True,
                pack_path=str(archive_path),
                pack_size_bytes=pack_size,
                job_id=str(summary.get("job_id")),
                files_present=sorted([p.name for p in base.iterdir() if p.is_file()]),
                sha256_verified=True,
                summary=summary,
            )

