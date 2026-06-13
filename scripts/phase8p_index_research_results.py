#!/usr/bin/env python3
"""
Phase 8P: build a compact canonical index of imported research results.

Reads only compact ALPHA result artifacts. It never reads raw candle caches, runtime
configuration, secrets, broker APIs, or execution paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8p_score_and_label_results import FAIL_CLOSED, score_row  # noqa: E402

PHASE = "Phase 8P"
PERFORMANCE_ROOT = Path("ARTIFACTS/performance")
DEFAULT_INDEX_JSON = PERFORMANCE_ROOT / "research_results_index.json"
DEFAULT_INDEX_JSONL = PERFORMANCE_ROOT / "research_results_index.jsonl"

ROW_FIELDS = [
    "run_id",
    "job_id",
    "generated_at_utc",
    "phase",
    "strategy_name",
    "strategy_source_path",
    "instrument",
    "session_bucket",
    "session_window_utc",
    "granularity",
    "lookback_days",
    "dataset_start_utc",
    "dataset_end_utc",
    "replay_mode",
    "exact_strategy_replay",
    "candidate_count",
    "clean_sample_count",
    "win_rate",
    "expectancy_r",
    "profit_factor_r",
    "max_loss_streak",
    "drawdown_proxy_r",
    "news_reconstruction_available",
    "calendar_reconstruction_available",
    "news_rows_count",
    "calendar_rows_count",
    "recommendation_label",
    "promotion_label",
    "decision_reason",
    "result_pack_size_bytes",
    "alpha_import_path",
    "latest_pointer_path",
    "paper_review_only",
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
]

SECRET_MARKERS = ("api_key", "apikey", "secret", "token", "password", "authorization", "bearer ")


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_first(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _safe_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def _row_has_secret_value(row: Mapping[str, Any]) -> bool:
    for value in row.values():
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if any(marker in lowered for marker in SECRET_MARKERS):
            return True
    return False


def _canonicalize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    clean = {field: row.get(field) for field in ROW_FIELDS}
    clean["paper_review_only"] = _safe_bool(clean.get("paper_review_only"), True)
    clean["live_permission"] = _safe_bool(clean.get("live_permission"), False)
    clean["ny_live_enabled"] = _safe_bool(clean.get("ny_live_enabled"), False)
    clean["send_trade_unlock_changed"] = _safe_bool(clean.get("send_trade_unlock_changed"), False)
    clean["execution_paths_changed"] = _safe_bool(clean.get("execution_paths_changed"), False)
    if _row_has_secret_value(clean):
        clean["promotion_label"] = FAIL_CLOSED
        clean["decision_reason"] = "secret_marker_detected_in_compact_row"
    return clean


def row_from_phase8m_import(path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
    try:
        manifest = read_json(path)
        summary = manifest.get("summary") or {}
        recommendation = manifest.get("recommendation") or {}
        if not isinstance(summary, Mapping):
            return None
        row = {
            "run_id": str(_get_first(summary.get("job_id"), manifest.get("job_id"), path.parent.name)),
            "job_id": str(_get_first(summary.get("job_id"), manifest.get("job_id"), "")),
            "generated_at_utc": _get_first(summary.get("generated_at_utc"), manifest.get("generated_at_utc")),
            "phase": _get_first(summary.get("phase"), manifest.get("phase")),
            "strategy_name": _get_first(summary.get("strategy_name"), summary.get("job_type"), manifest.get("job_type")),
            "strategy_source_path": summary.get("strategy_source_path"),
            "instrument": summary.get("instrument"),
            "session_bucket": summary.get("session_bucket"),
            "session_window_utc": summary.get("session_window_utc"),
            "granularity": summary.get("granularity"),
            "lookback_days": summary.get("lookback_days"),
            "dataset_start_utc": summary.get("dataset_start_utc"),
            "dataset_end_utc": summary.get("dataset_end_utc"),
            "replay_mode": summary.get("replay_mode"),
            "exact_strategy_replay": _safe_bool(summary.get("exact_strategy_replay"), False),
            "candidate_count": summary.get("candidate_count"),
            "clean_sample_count": _get_first(summary.get("clean_sample_count"), summary.get("candidate_count")),
            "win_rate": summary.get("win_rate"),
            "expectancy_r": summary.get("expectancy_r"),
            "profit_factor_r": summary.get("profit_factor_r"),
            "max_loss_streak": summary.get("max_loss_streak"),
            "drawdown_proxy_r": summary.get("drawdown_proxy_r"),
            "news_reconstruction_available": _safe_bool(summary.get("news_reconstruction_available")),
            "calendar_reconstruction_available": _safe_bool(summary.get("calendar_reconstruction_available")),
            "news_rows_count": summary.get("news_rows_count"),
            "calendar_rows_count": summary.get("calendar_rows_count"),
            "recommendation_label": _get_first(recommendation.get("recommendation_label"), summary.get("recommendation_label")),
            "result_pack_size_bytes": manifest.get("result_pack_size_bytes"),
            "alpha_import_path": str(path.parent.relative_to(repo_root)) if path.is_relative_to(repo_root) else str(path.parent),
            "latest_pointer_path": str(Path("ARTIFACTS/performance/latest_research_job_result.json")),
            "paper_review_only": _get_first(manifest.get("paper_review_only"), summary.get("paper_review_only")),
            "live_permission": _get_first(manifest.get("live_permission"), summary.get("live_permission")),
            "ny_live_enabled": _get_first(manifest.get("ny_live_enabled"), summary.get("ny_live_enabled")),
            "send_trade_unlock_changed": _get_first(manifest.get("send_trade_unlock_changed"), summary.get("send_trade_unlock_changed")),
            "execution_paths_changed": _get_first(manifest.get("execution_paths_changed"), summary.get("execution_paths_changed")),
            "classification": summary.get("classification"),
        }
        return _canonicalize_row(score_row(row))
    except Exception:
        return None


def row_from_phase8o_import(path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
    try:
        summary_path = path.parent / "phase8o_backtest_summary.json"
        recommendation_path = path.parent / "phase8o_recommendation.json"
        if not summary_path.is_file():
            return None
        manifest = read_json(path)
        summary = read_json(summary_path)
        recommendation = read_json(recommendation_path) if recommendation_path.is_file() else {}
        run_id = path.parent.name
        row = {
            "run_id": run_id,
            "job_id": _get_first(summary.get("job_id"), run_id),
            "generated_at_utc": _get_first(summary.get("generated_at_utc"), manifest.get("generated_at_utc")),
            "phase": summary.get("phase"),
            "strategy_name": _get_first(summary.get("strategy_name"), "phase8o_exact_replay"),
            "strategy_source_path": summary.get("strategy_source_path"),
            "instrument": summary.get("instrument"),
            "session_bucket": summary.get("session_bucket"),
            "session_window_utc": summary.get("session_window_utc"),
            "granularity": summary.get("granularity"),
            "lookback_days": summary.get("lookback_days"),
            "dataset_start_utc": summary.get("dataset_start_utc"),
            "dataset_end_utc": summary.get("dataset_end_utc"),
            "replay_mode": summary.get("replay_mode"),
            "exact_strategy_replay": _safe_bool(summary.get("exact_strategy_replay"), False),
            "candidate_count": summary.get("candidate_count"),
            "clean_sample_count": summary.get("clean_sample_count"),
            "win_rate": summary.get("win_rate"),
            "expectancy_r": summary.get("expectancy_r"),
            "profit_factor_r": summary.get("profit_factor_r"),
            "max_loss_streak": summary.get("max_loss_streak"),
            "drawdown_proxy_r": summary.get("drawdown_proxy_r"),
            "news_reconstruction_available": _safe_bool(summary.get("news_reconstruction_available")),
            "calendar_reconstruction_available": _safe_bool(summary.get("calendar_reconstruction_available")),
            "news_rows_count": summary.get("news_rows_count"),
            "calendar_rows_count": summary.get("calendar_rows_count"),
            "recommendation_label": _get_first(recommendation.get("recommendation_label"), summary.get("recommendation_label")),
            "result_pack_size_bytes": manifest.get("result_pack_size_bytes"),
            "alpha_import_path": str(path.parent.relative_to(repo_root)) if path.is_relative_to(repo_root) else str(path.parent),
            "latest_pointer_path": str(Path("ARTIFACTS/performance/latest_phase8o_backtest_summary.json")),
            "paper_review_only": _get_first(manifest.get("paper_review_only"), summary.get("paper_review_only")),
            "live_permission": _get_first(manifest.get("live_permission"), summary.get("live_permission")),
            "ny_live_enabled": _get_first(manifest.get("ny_live_enabled"), summary.get("ny_live_enabled")),
            "send_trade_unlock_changed": _get_first(manifest.get("send_trade_unlock_changed"), summary.get("send_trade_unlock_changed")),
            "execution_paths_changed": _get_first(manifest.get("execution_paths_changed"), summary.get("execution_paths_changed")),
            "classification": summary.get("classification"),
        }
        return _canonicalize_row(score_row(row))
    except Exception:
        return None


def iter_rows(repo_root: Path) -> Iterable[Dict[str, Any]]:
    performance = repo_root / PERFORMANCE_ROOT
    for path in sorted((performance / "imports" / "research_jobs").glob("*/phase8m_import_manifest.json")):
        row = row_from_phase8m_import(path, repo_root)
        if row:
            yield row
    for path in sorted((performance / "imports" / "phase8o").glob("*/phase8o_alpha_import_manifest.json")):
        row = row_from_phase8o_import(path, repo_root)
        if row:
            yield row


def build_index(repo_root: Path) -> Dict[str, Any]:
    rows = sorted(iter_rows(repo_root), key=lambda r: str(r.get("generated_at_utc") or ""), reverse=True)
    counts: Dict[str, int] = {}
    for row in rows:
        label = str(row.get("promotion_label") or "UNKNOWN")
        counts[label] = counts.get(label, 0) + 1
    return {
        "ok": True,
        "phase": PHASE,
        "classification": "PHASE8P_RESEARCH_RESULT_INDEX",
        "generated_at_utc": utc_now_iso_z(),
        "row_schema": ROW_FIELDS,
        "row_count": len(rows),
        "promotion_label_counts": counts,
        "rows": rows,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def write_index(index: Mapping[str, Any], index_json: Path, index_jsonl: Path) -> Dict[str, Any]:
    rows = list(index.get("rows") or [])
    index_json.parent.mkdir(parents=True, exist_ok=True)
    index_json.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    index_jsonl.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    return {
        "ok": True,
        "index_json": str(index_json),
        "index_jsonl": str(index_jsonl),
        "row_count": len(rows),
        "index_size_bytes": index_json.stat().st_size,
        "index_jsonl_size_bytes": index_jsonl.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 8P compact research result index.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--index-json", type=Path, default=DEFAULT_INDEX_JSON)
    parser.add_argument("--index-jsonl", type=Path, default=DEFAULT_INDEX_JSONL)
    args = parser.parse_args()

    try:
        repo_root = args.repo_root.expanduser().resolve()
        index_json = args.index_json if args.index_json.is_absolute() else repo_root / args.index_json
        index_jsonl = args.index_jsonl if args.index_jsonl.is_absolute() else repo_root / args.index_jsonl
        index = build_index(repo_root)
        result = write_index(index, index_json, index_jsonl)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
