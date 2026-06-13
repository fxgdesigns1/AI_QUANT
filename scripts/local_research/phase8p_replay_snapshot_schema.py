#!/usr/bin/env python3
"""
Phase 8P replay-ready forward evidence snapshot schema.

This module is intentionally stdlib-only and research-only. It builds stable,
sanitized, self-contained records from paper-review rows plus read-only
control-plane payloads.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

PHASE = "Phase 8P"
UTC = timezone.utc

REQUIRED_SNAPSHOT_FIELDS = (
    "snapshot_id",
    "snapshot_hash",
    "generated_at_utc",
    "instrument",
    "session_bucket",
    "side",
    "entry",
    "stop_loss",
    "take_profit",
    "confidence",
    "strategy",
    "top3_rank",
    "score",
    "news_snapshot",
    "news_assess_snapshot",
    "calendar_snapshot",
    "provider_status_snapshot",
    "source_artifact_paths",
    "replay_ready_exact",
    "missing_fields",
)

CORE_REPLAY_FIELDS = (
    "instrument",
    "session_bucket",
    "side",
    "entry",
    "stop_loss",
    "take_profit",
)

REQUIRED_CONTEXT_FIELDS = (
    "news_snapshot",
    "news_assess_snapshot",
    "calendar_snapshot",
    "provider_status_snapshot",
)

FIELD_ALIASES = {
    "instrument": ("instrument", "pair", "symbol"),
    "session_bucket": ("session_bucket", "session", "session_key"),
    "side": ("side", "direction", "signal_side"),
    "entry": ("entry", "entry_price", "open_price", "price"),
    "stop_loss": ("stop_loss", "sl"),
    "take_profit": ("take_profit", "tp"),
    "confidence": ("confidence", "model_confidence", "probability"),
    "strategy": ("strategy", "strategy_name", "candidate_source"),
    "top3_rank": ("top3_rank", "rank", "candidate_rank"),
    "score": ("score", "candidate_score"),
}

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "credential",
    "env",
    "header",
    "key",
    "password",
    "secret",
    "token",
)


def utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _field_value(row: Mapping[str, Any], name: str) -> Any:
    for alias in FIELD_ALIASES.get(name, (name,)):
        value = row.get(alias)
        if value is not None and str(value) != "":
            return value
    return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            skey = str(key)
            lowered = skey.lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                out[skey] = "[REDACTED]"
            else:
                out[skey] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return _jsonable(value)


def degraded_snapshot(*, endpoint: str, http_status: Optional[int], error_class: str, captured_at_utc: Optional[str] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "endpoint": endpoint,
        "http_status": http_status,
        "error_class": error_class,
        "captured_at_utc": captured_at_utc or utc_now_iso_z(),
    }


def canonical_json(obj: Mapping[str, Any]) -> str:
    return json.dumps(_jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    payload = {str(k): v for k, v in snapshot.items() if k != "snapshot_hash"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_snapshot_hash(snapshot: Mapping[str, Any]) -> bool:
    expected = snapshot.get("snapshot_hash")
    return isinstance(expected, str) and expected == compute_snapshot_hash(snapshot)


def context_is_missing(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return True
    if not value:
        return True
    if value.get("ok") is False:
        return True
    if value.get("error_class") or value.get("error"):
        return True
    return False


def missing_fields_for(snapshot: Mapping[str, Any]) -> List[str]:
    missing: List[str] = []
    for field in CORE_REPLAY_FIELDS:
        value = snapshot.get(field)
        if value is None or str(value) == "":
            missing.append(field)
    for field in REQUIRED_CONTEXT_FIELDS:
        if context_is_missing(snapshot.get(field)):
            missing.append(field)
    return missing


def build_replay_snapshot(
    row: Mapping[str, Any],
    *,
    news_snapshot: Optional[Mapping[str, Any]] = None,
    news_assess_snapshot: Optional[Mapping[str, Any]] = None,
    calendar_snapshot: Optional[Mapping[str, Any]] = None,
    provider_status_snapshot: Optional[Mapping[str, Any]] = None,
    source_artifact_paths: Optional[Iterable[str]] = None,
    generated_at_utc: Optional[str] = None,
) -> Dict[str, Any]:
    generated = generated_at_utc or utc_now_iso_z()
    base: Dict[str, Any] = {
        "phase": PHASE,
        "classification": "REPLAY_READY_FORWARD_CAPTURE_ENABLED",
        "generated_at_utc": generated,
        "instrument": _field_value(row, "instrument"),
        "session_bucket": _field_value(row, "session_bucket"),
        "side": _field_value(row, "side"),
        "entry": _field_value(row, "entry"),
        "stop_loss": _field_value(row, "stop_loss"),
        "take_profit": _field_value(row, "take_profit"),
        "confidence": _field_value(row, "confidence"),
        "strategy": _field_value(row, "strategy"),
        "top3_rank": _field_value(row, "top3_rank"),
        "score": _field_value(row, "score"),
        "news_snapshot": redact_secrets(news_snapshot or {}),
        "news_assess_snapshot": redact_secrets(news_assess_snapshot or {}),
        "calendar_snapshot": redact_secrets(calendar_snapshot or {}),
        "provider_status_snapshot": redact_secrets(provider_status_snapshot or {}),
        "source_artifact_paths": sorted(str(p) for p in (source_artifact_paths or [])),
        "live_trading_changed": False,
        "execution_paths_changed": False,
        "ny_live_enabled": False,
        "runner_restart_required": False,
    }
    missing = missing_fields_for(base)
    seed = {
        "generated_at_utc": generated,
        "instrument": base.get("instrument"),
        "session_bucket": base.get("session_bucket"),
        "side": base.get("side"),
        "entry": base.get("entry"),
        "stop_loss": base.get("stop_loss"),
        "take_profit": base.get("take_profit"),
        "score": base.get("score"),
    }
    base["snapshot_id"] = "phase8p_" + hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()[:20]
    base["replay_ready_exact"] = not missing
    base["missing_fields"] = missing
    for field in REQUIRED_SNAPSHOT_FIELDS:
        base.setdefault(field, None)
    base["snapshot_hash"] = compute_snapshot_hash(base)
    return base


def extract_snapshot(row: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = row.get("phase8p_replay_snapshot") if isinstance(row.get("phase8p_replay_snapshot"), Mapping) else row
    return dict(snapshot)
