#!/usr/bin/env python3
"""
Phase 8P: deterministic exact replay from self-contained forward archive rows.

No external APIs are called. Rows must carry a valid Phase 8P snapshot hash
before R outcome replay is attempted.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.phase8k_replay_lib import simulate_trade_r  # noqa: E402
from scripts.local_research.phase8p_replay_snapshot_schema import (  # noqa: E402
    build_replay_snapshot,
    extract_snapshot,
    validate_snapshot_hash,
)

PHASE = "Phase 8P"
UTC = timezone.utc
DEFAULT_INPUT = Path("ARTIFACTS/performance/pair_session_paper_review_log.jsonl")
DEFAULT_OUTPUT = Path("ARTIFACTS/performance/latest_phase8p_exact_replay_from_archive.json")
DEFAULT_READINESS = Path("ARTIFACTS/performance/latest_phase8p_replay_readiness.json")


def utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError(f"jsonl_row_not_object:{line_no}")
            rows.append(obj)
    return rows


def _matches(snapshot: Mapping[str, Any], *, instrument: Optional[str], session_bucket: Optional[str]) -> bool:
    if instrument and str(snapshot.get("instrument") or "").upper() != instrument.upper():
        return False
    if session_bucket and session_bucket.lower() not in str(snapshot.get("session_bucket") or "").lower():
        return False
    return True


def _bars_from_row(row: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for key in ("future_bars", "future_price_bars", "bars_after_entry"):
        value = row.get(key)
        if isinstance(value, list):
            return [b for b in value if isinstance(b, Mapping)]
    for key in ("future_price_evidence", "outcome_evidence"):
        value = row.get(key)
        if isinstance(value, Mapping):
            bars = value.get("future_bars") or value.get("bars_after_entry") or value.get("bars")
            if isinstance(bars, list):
                return [b for b in bars if isinstance(b, Mapping)]
    return []


def replay_row(row: Mapping[str, Any], *, strict: bool) -> Dict[str, Any]:
    snapshot = extract_snapshot(row)
    if not snapshot.get("snapshot_hash"):
        if strict:
            return {
                "status": "REPLAY_REFUSED_MISSING_SNAPSHOT_HASH",
                "snapshot_id": snapshot.get("snapshot_id"),
                "missing_fields": ["snapshot_hash"],
            }
        snapshot = build_replay_snapshot(row, source_artifact_paths=[str(DEFAULT_INPUT)])

    if not validate_snapshot_hash(snapshot):
        return {
            "status": "REPLAY_REFUSED_INVALID_SNAPSHOT_HASH",
            "snapshot_id": snapshot.get("snapshot_id"),
            "snapshot_hash": snapshot.get("snapshot_hash"),
        }

    missing = list(snapshot.get("missing_fields") or [])
    if missing or snapshot.get("replay_ready_exact") is not True:
        return {
            "status": "REPLAY_BLOCKED_SNAPSHOT_NOT_READY",
            "snapshot_id": snapshot.get("snapshot_id"),
            "snapshot_hash": snapshot.get("snapshot_hash"),
            "missing_fields": missing,
        }

    if row.get("outcome") is not None and row.get("r_multiple") is not None:
        return {
            "status": "REPLAY_REUSED_ARCHIVED_OUTCOME",
            "snapshot_id": snapshot.get("snapshot_id"),
            "snapshot_hash": snapshot.get("snapshot_hash"),
            "outcome": row.get("outcome"),
            "r_multiple": row.get("r_multiple"),
        }

    bars = _bars_from_row(row)
    if not bars:
        return {
            "status": "REPLAY_BLOCKED_MISSING_OUTCOME_DATA",
            "snapshot_id": snapshot.get("snapshot_id"),
            "snapshot_hash": snapshot.get("snapshot_hash"),
            "missing_fields": ["future_price_or_outcome_evidence"],
        }

    outcome, exit_price, r_multiple = simulate_trade_r(
        side=str(snapshot.get("side")),
        entry=float(snapshot.get("entry")),
        stop_loss=float(snapshot.get("stop_loss")),
        take_profit=float(snapshot.get("take_profit")),
        bars_after_entry=bars,
    )
    return {
        "status": "REPLAY_COMPLETE",
        "snapshot_id": snapshot.get("snapshot_id"),
        "snapshot_hash": snapshot.get("snapshot_hash"),
        "outcome": outcome,
        "exit_price": exit_price,
        "r_multiple": r_multiple,
    }


def build_readiness(rows: Sequence[Mapping[str, Any]], *, generated_at_utc: Optional[str] = None) -> Dict[str, Any]:
    generated = generated_at_utc or utc_now_iso_z()
    missing_hist: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    ready_times: List[str] = []
    replay_ready_count = 0

    for row in rows:
        snapshot = extract_snapshot(row)
        if not snapshot.get("snapshot_hash"):
            snapshot = build_replay_snapshot(row, source_artifact_paths=[str(DEFAULT_INPUT)])
        valid_hash = validate_snapshot_hash(snapshot)
        missing = list(snapshot.get("missing_fields") or [])
        for field in missing:
            missing_hist[str(field)] += 1
        if not valid_hash:
            blockers["invalid_snapshot_hash"] += 1
        if missing:
            blockers["missing_required_fields"] += 1
        if snapshot.get("replay_ready_exact") is True and valid_hash and not missing:
            replay_ready_count += 1
            if snapshot.get("generated_at_utc"):
                ready_times.append(str(snapshot.get("generated_at_utc")))

    return {
        "ok": True,
        "phase": PHASE,
        "classification": "REPLAY_READY_FORWARD_CAPTURE_ENABLED",
        "generated_at_utc": generated,
        "row_count": len(rows),
        "replay_ready_exact_count": replay_ready_count,
        "replay_not_ready_count": len(rows) - replay_ready_count,
        "missing_fields_histogram": dict(sorted(missing_hist.items())),
        "first_replay_ready_at_utc": min(ready_times) if ready_times else None,
        "latest_replay_ready_at_utc": max(ready_times) if ready_times else None,
        "blocking_reasons": dict(sorted(blockers.items())),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def run_replay_from_archive(
    *,
    input_path: Path,
    output_path: Path,
    readiness_path: Path,
    instrument: Optional[str],
    session_bucket: Optional[str],
    limit: Optional[int],
    strict: bool,
) -> Dict[str, Any]:
    generated = utc_now_iso_z()
    if not input_path.is_file():
        result = {
            "ok": False,
            "phase": PHASE,
            "classification": "REPLAY_BLOCKED_ARCHIVE_INPUT_MISSING",
            "generated_at_utc": generated,
            "input": str(input_path),
            "status": "REPLAY_BLOCKED_ARCHIVE_INPUT_MISSING",
            "rows_considered": 0,
            "rows_replayed": 0,
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        readiness_path.parent.mkdir(parents=True, exist_ok=True)
        readiness_path.write_text(json.dumps(build_readiness([], generated_at_utc=generated), indent=2, sort_keys=True), encoding="utf-8")
        return result

    rows = load_jsonl(input_path)
    selected: List[Dict[str, Any]] = []
    for row in rows:
        snapshot = extract_snapshot(row)
        if not _matches(snapshot, instrument=instrument, session_bucket=session_bucket):
            continue
        selected.append(dict(row))
        if limit is not None and len(selected) >= limit:
            break

    replays = [replay_row(row, strict=strict) for row in selected]
    status_counts = Counter(str(r.get("status")) for r in replays)
    invalid_hash = status_counts.get("REPLAY_REFUSED_INVALID_SNAPSHOT_HASH", 0)
    missing_hash = status_counts.get("REPLAY_REFUSED_MISSING_SNAPSHOT_HASH", 0)
    ok = not (strict and (invalid_hash or missing_hash))
    result = {
        "ok": ok,
        "phase": PHASE,
        "classification": "PHASE8P_EXACT_REPLAY_FROM_ARCHIVE",
        "generated_at_utc": generated,
        "input": str(input_path),
        "instrument": instrument,
        "session_bucket": session_bucket,
        "strict": bool(strict),
        "rows_considered": len(selected),
        "rows_replayed": status_counts.get("REPLAY_COMPLETE", 0) + status_counts.get("REPLAY_REUSED_ARCHIVED_OUTCOME", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "replays": replays,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    readiness_path.parent.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text(json.dumps(build_readiness(rows, generated_at_utc=generated), indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay Phase 8P self-contained archive rows without external APIs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--instrument", default=None)
    parser.add_argument("--session-bucket", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = REPO_ROOT.resolve()
    result = run_replay_from_archive(
        input_path=_resolve(repo_root, args.input),
        output_path=_resolve(repo_root, args.output),
        readiness_path=_resolve(repo_root, DEFAULT_READINESS),
        instrument=args.instrument,
        session_bucket=args.session_bucket,
        limit=args.limit,
        strict=bool(args.strict),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
