#!/usr/bin/env python3
"""
Phase 8U: Build canonical Stitch-facing dashboard payload from Phase 8P JSON.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("ARTIFACTS/performance/latest_research_dashboard.json")
DEFAULT_CONTRACT = Path("ARTIFACTS/performance/latest_stitch_dashboard_contract.json")
DEFAULT_PAYLOAD = Path("ARTIFACTS/performance/latest_stitch_dashboard_payload.json")

PROMOTE = "PROMOTE_REVIEW_CANDIDATE"
FAIL_CLOSED = "FAIL_CLOSED_DATA_INCOMPLETE"
PROXY_TOKEN = "proxy"


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _freshness(generated_at_utc: Any) -> Dict[str, Any]:
    gen = _parse_iso(generated_at_utc)
    if gen is None:
        return {"seconds": -1, "stale": True, "status": "UNKNOWN_GENERATED_AT"}
    seconds = max(0, int((datetime.now(timezone.utc) - gen).total_seconds()))
    stale = seconds > 86400
    return {
        "seconds": seconds,
        "stale": stale,
        "status": "STALE" if stale else "FRESH",
    }


def _is_proxy_row(row: Mapping[str, Any]) -> bool:
    mode = str(row.get("replay_mode") or "").lower()
    return PROXY_TOKEN in mode or mode == "best_available_proxy_reconstruction"


def _is_exact_replay_row(row: Mapping[str, Any]) -> bool:
    return (
        bool(row.get("phase8aa_context_injected"))
        and bool(row.get("context_manifest_sha256_verified"))
        and str(row.get("replay_mode") or "") == "exact_context_pack_phase8aa"
    )


def _is_fail_closed_row(row: Mapping[str, Any]) -> bool:
    label = str(row.get("promotion_label") or "")
    if label == FAIL_CLOSED:
        return True
    mode = str(row.get("replay_mode") or "").lower()
    return "fail_closed" in mode or mode.startswith("fail")


def _ensure_decision_reason(row: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    existing = str(out.get("decision_reason") or "").strip()
    if existing:
        return out
    label = str(out.get("promotion_label") or "UNKNOWN")
    out["decision_reason"] = f"auto_filled_reason_missing_for_label:{label}"
    return out


def _normalize_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [_ensure_decision_reason(r) for r in rows if isinstance(r, Mapping)]


def build_payload(dashboard: Mapping[str, Any], contract: Mapping[str, Any]) -> Dict[str, Any]:
    latest_runs = _normalize_rows(dashboard.get("latest_research_runs") or [])
    promotion_candidates = _normalize_rows(dashboard.get("promotion_candidates") or [])
    continue_forward = _normalize_rows(dashboard.get("continue_forward_candidates") or [])
    watch_only = _normalize_rows(dashboard.get("watch_only_candidates") or [])
    demoted_blocked = _normalize_rows(dashboard.get("demoted_blocked_candidates") or [])
    fail_closed = _normalize_rows(dashboard.get("fail_closed_rows") or [])
    proxy_rows = _normalize_rows(dashboard.get("proxy_rows") or [])

    # Enforce separation in payload, even if source dashboard accidentally drifts.
    promotion_candidates = [
        r for r in promotion_candidates if str(r.get("promotion_label") or "") == PROMOTE and not _is_proxy_row(r) and not _is_fail_closed_row(r)
    ]
    fail_closed = [r for r in fail_closed if _is_fail_closed_row(r)]
    proxy_rows = [r for r in proxy_rows if _is_proxy_row(r)]

    # Separate exact replay rows from proxy leads
    exact_replay_rows = [r for r in latest_runs if _is_exact_replay_row(r)]
    proxy_lead_rows = [r for r in latest_runs if not _is_exact_replay_row(r) and _is_proxy_row(r)]
    n_exact = len(exact_replay_rows)
    n_total = len(latest_runs)
    n_proxy = len(proxy_lead_rows)
    exact_replay_banner = (
        f"{n_exact} of {n_total} results are exact replay (phase8aa). "
        f"{n_proxy} are proxy leads only."
    )

    freshness = _freshness(dashboard.get("generated_at_utc"))
    warnings: List[str] = []
    if freshness["stale"]:
        warnings.append(f"dashboard_stale_seconds:{freshness['seconds']}")
    if not dashboard.get("providers_working"):
        warnings.append("providers_working_empty")
    if dashboard.get("exact_strategy_replay") is False:
        warnings.append("exact_strategy_replay_false")

    payload = {
        "ok": True,
        "generated_at_utc": _utc_now_iso_z(),
        "source": {
            "dashboard_path": "ARTIFACTS/performance/latest_research_dashboard.json",
            "contract_path": "ARTIFACTS/performance/latest_stitch_dashboard_contract.json",
            "source_generated_at_utc": dashboard.get("generated_at_utc"),
        },
        "contract_version": str(contract.get("contract_version") or "phase8t_v1"),
        "freshness": freshness,
        "summary_cards": {
            "result_rows_indexed": int(dashboard.get("result_rows_indexed") or 0),
            "promotion_candidates_count": len(promotion_candidates),
            "exact_replay_results_count": n_exact,
            "proxy_research_leads_count": n_proxy,
            "exact_replay_status": bool(dashboard.get("exact_strategy_replay")),
            "calendar_budget_remaining": dashboard.get("calendar_budget_remaining"),
            "calendar_calls_this_month": dashboard.get("calendar_calls_this_month"),
            "estimated_calls_needed_next_batch": dashboard.get("phase8y_estimated_api_calls_needed"),
            "estimated_paid_calendar_calls_needed": dashboard.get("phase8y_estimated_paid_calendar_calls_needed"),
            "cache_hit_rate": dashboard.get("calendar_cache_hit_rate"),
            "exact_replay_readiness": dashboard.get("phase8y_exact_replay_possible"),
            "safe_to_run_batch": dashboard.get("phase8y_safe_to_run_batch"),
            "missing_data_windows_count": len(dashboard.get("phase8y_missing_windows") or []),
            "providers_working_count": len(dashboard.get("providers_working") or []),
            "providers_blocked_count": len(dashboard.get("providers_blocked") or []),
            "dashboard_freshness": freshness,
        },
        "tables": {
            "latest_runs": latest_runs,
            "exact_replay_results": exact_replay_rows,
            "proxy_research_leads": proxy_lead_rows,
            "promotion_candidates": promotion_candidates,
            "continue_forward": continue_forward,
            "watch_only": watch_only,
            "demoted_blocked": demoted_blocked,
            "fail_closed": fail_closed,
            "proxy_research": proxy_rows,
        },
        "exact_replay_banner": exact_replay_banner,
        "filters": {
            "replay_mode": sorted({str(r.get("replay_mode") or "") for r in latest_runs if r.get("replay_mode")}),
            "promotion_label": sorted({str(r.get("promotion_label") or "") for r in latest_runs if r.get("promotion_label")}),
            "instrument": sorted({str(r.get("instrument") or "") for r in latest_runs if r.get("instrument")}),
            "session_bucket": sorted({str(r.get("session_bucket") or "") for r in latest_runs if r.get("session_bucket")}),
            "timeframe": sorted({str(r.get("granularity") or "") for r in latest_runs if r.get("granularity")}),
            "provider_status": ["working", "blocked"],
        },
        "warnings": warnings,
        "phase8x_batch_progress": (
            dashboard.get("phase8x_batch_progress")
            if isinstance(dashboard.get("phase8x_batch_progress"), dict)
            else None
        ),
        "safety": {
            "paper_review_only": bool(dashboard.get("paper_review_only")),
            "live_permission": bool(dashboard.get("live_permission")),
            "ny_live_enabled": bool(dashboard.get("ny_live_enabled")),
            "send_trade_unlock_changed": bool(dashboard.get("send_trade_unlock_changed")),
            "execution_paths_changed": bool(dashboard.get("execution_paths_changed")),
        },
        "alpha_pointers": dict(dashboard.get("alpha_latest_pointers") or {}),
        "calendar_budget": {
            "calendar_calls_this_month": dashboard.get("calendar_calls_this_month"),
            "calendar_budget_remaining": dashboard.get("calendar_budget_remaining"),
            "calendar_cache_hit_rate": dashboard.get("calendar_cache_hit_rate"),
            "last_calendar_api_call_utc": dashboard.get("last_calendar_api_call_utc"),
        },
        "provider_capability": {
            "providers_working": list(dashboard.get("providers_working") or []),
            "providers_blocked": list(dashboard.get("providers_blocked") or []),
            "stitch_mcp_contract_health": dashboard.get("stitch_mcp_contract_health"),
        },
        "exact_replay_status": {
            "latest_phase8o_classification": dashboard.get("latest_phase8o_classification"),
            "exact_strategy_replay": bool(dashboard.get("exact_strategy_replay")),
            "news_reconstruction_available": dashboard.get("news_reconstruction_available"),
            "calendar_reconstruction_available": dashboard.get("calendar_reconstruction_available"),
        },
        "phase8y_coverage": {
            "phase8y_data_coverage_manifest_present": dashboard.get("phase8y_data_coverage_manifest_present"),
            "phase8y_api_cost_estimate_present": dashboard.get("phase8y_api_cost_estimate_present"),
            "phase8y_context_pack_verified": dashboard.get("phase8y_context_pack_verified"),
            "estimated_api_calls_needed": dashboard.get("phase8y_estimated_api_calls_needed"),
            "estimated_paid_calendar_calls_needed": dashboard.get("phase8y_estimated_paid_calendar_calls_needed"),
            "cache_hit_rate": dashboard.get("calendar_cache_hit_rate"),
            "exact_replay_readiness": dashboard.get("phase8y_exact_replay_possible"),
            "missing_data_windows": list(dashboard.get("phase8y_missing_windows") or []),
            "safe_to_run_batch": dashboard.get("phase8y_safe_to_run_batch"),
        },
    }
    p8x = payload.get("phase8x_batch_progress")
    sc = payload["summary_cards"]
    if isinstance(p8x, dict):
        sc["phase8x_batch_progress_present"] = True
        sc["phase8x_pending"] = p8x.get("pending")
        sc["phase8x_running"] = p8x.get("running")
        sc["phase8x_done"] = p8x.get("done")
        sc["phase8x_failed"] = p8x.get("failed")
        sc["phase8x_total"] = p8x.get("total")
        sc["phase8x_percent_complete"] = p8x.get("percent_complete")
        sc["phase8x_stop_reason"] = p8x.get("stop_reason")
        sc["phase8x_current_job_id"] = p8x.get("current_job_id")
    else:
        sc["phase8x_batch_progress_present"] = False
    return payload


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 8U Stitch dashboard payload.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--source-dashboard", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--contract-json", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()
    source = args.source_dashboard if args.source_dashboard.is_absolute() else repo / args.source_dashboard
    contract = args.contract_json if args.contract_json.is_absolute() else repo / args.contract_json
    output = args.output if args.output.is_absolute() else repo / args.output

    if not source.is_file():
        print(json.dumps({"ok": False, "error": "missing_source_dashboard", "path": str(source)}, indent=2))
        return 1
    if not contract.is_file():
        print(json.dumps({"ok": False, "error": "missing_contract_json", "path": str(contract)}, indent=2))
        return 1

    payload = build_payload(_read_json(source), _read_json(contract))
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "payload_path": str(output),
                "rows": len(payload["tables"]["latest_runs"]),
                "promotion_candidates": len(payload["tables"]["promotion_candidates"]),
                "proxy_rows": len(payload["tables"]["proxy_research"]),
                "fail_closed_rows": len(payload["tables"]["fail_closed"]),
                "freshness_status": payload["freshness"]["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
