#!/usr/bin/env python3
"""
Phase 8N: normalize Phase 8M latest imported research-job result into a strict metrics summary.

This script is intentionally "read-only": it parses a JSON file produced on ALPHA
(`ARTIFACTS/performance/latest_research_job_result.json`) and emits a compact summary JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    RESULT_SUMMARY_REQUIRED_FIELDS,
    require_fields,
    validate_safety,
)


def _get(d: Mapping[str, Any], k: str) -> Any:
    return d.get(k)


def normalize_latest_import_manifest(obj: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Accepts Phase 8M import manifest (the latest result pointer JSON) and returns a strict summary.
    Fails closed if safety flags are wrong or required metrics are missing.
    """
    if not isinstance(obj, Mapping):
        raise ContractError("latest_result_not_a_mapping")

    # Import manifest required fields (phase8m_import_research_result.py)
    require_fields(
        obj,
        (
            "job_id",
            "phase",
            "classification",
            "result_pack_size_bytes",
            "paper_review_only",
            "live_permission",
            "ny_live_enabled",
            "send_trade_unlock_changed",
            "execution_paths_changed",
        ),
        "latest_import_manifest",
    )

    validate_safety(
        {
            "research_only": True,
            "paper_review_only": bool(_get(obj, "paper_review_only")),
            "live_permission": bool(_get(obj, "live_permission")),
            "ny_live_enabled": bool(_get(obj, "ny_live_enabled")),
            "send_trade_unlock_changed": bool(_get(obj, "send_trade_unlock_changed")),
            "execution_paths_changed": bool(_get(obj, "execution_paths_changed")),
        },
        label="latest_import_manifest",
    )

    summary = obj.get("summary") or {}
    if not isinstance(summary, Mapping):
        raise ContractError("latest_import_manifest_summary_missing_or_invalid")
    require_fields(summary, RESULT_SUMMARY_REQUIRED_FIELDS, "backtest_summary")

    # Safety re-check on the embedded summary (pack contract already enforces, but we fail closed here too).
    validate_safety(
        {
            "research_only": True,
            "paper_review_only": bool(summary.get("paper_review_only")),
            "live_permission": bool(summary.get("live_permission")),
            "ny_live_enabled": bool(summary.get("ny_live_enabled")),
            "send_trade_unlock_changed": bool(summary.get("send_trade_unlock_changed")),
            "execution_paths_changed": bool(summary.get("execution_paths_changed")),
        },
        label="backtest_summary",
    )

    def opt_bool(v: Any) -> Optional[bool]:
        if v is None:
            return None
        return bool(v)

    # These are phase8l/phase8k metadata fields; they may be absent depending on job implementation.
    news_avail = opt_bool(summary.get("news_reconstruction_available"))
    cal_avail = opt_bool(summary.get("calendar_reconstruction_available"))

    return {
        "ok": True,
        "job_id": str(summary.get("job_id")),
        "job_type": str(summary.get("job_type")),
        "replay_mode": summary.get("replay_mode"),
        "instrument": summary.get("instrument"),
        "granularity": summary.get("granularity"),
        "lookback_days": summary.get("lookback_days"),
        "session_bucket": summary.get("session_bucket"),
        "session_window_utc": summary.get("session_window_utc"),
        "candidate_count": summary.get("candidate_count"),
        "expectancy_r": summary.get("expectancy_r"),
        "profit_factor_r": summary.get("profit_factor_r"),
        "max_loss_streak": summary.get("max_loss_streak"),
        "drawdown_proxy_r": summary.get("drawdown_proxy_r"),
        "recommendation_label": summary.get("recommendation_label"),
        "news_reconstruction_available": news_avail,
        "calendar_reconstruction_available": cal_avail,
        "alpha_result_pointer": obj.get("latest_pointer") or obj.get("latest_result_pointer"),
        "result_pack_size_bytes": int(obj.get("result_pack_size_bytes")),
        "paper_review_only": bool(obj.get("paper_review_only")),
        "live_permission": bool(obj.get("live_permission")),
        "ny_live_enabled": bool(obj.get("ny_live_enabled")),
        "send_trade_unlock_changed": bool(obj.get("send_trade_unlock_changed")),
        "execution_paths_changed": bool(obj.get("execution_paths_changed")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize Phase 8M ALPHA latest research result pointer to a strict metrics summary.")
    ap.add_argument("--latest-json", required=True, type=Path, help="Path to latest_research_job_result.json (copied from ALPHA).")
    args = ap.parse_args()
    try:
        p = args.latest_json.expanduser().resolve()
        obj = json.loads(p.read_text(encoding="utf-8"))
        out = normalize_latest_import_manifest(obj)
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

