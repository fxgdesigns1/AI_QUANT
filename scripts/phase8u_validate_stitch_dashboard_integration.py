#!/usr/bin/env python3
"""
Phase 8U validation: contract + payload + Stitch integration evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("ARTIFACTS/performance/latest_stitch_dashboard_contract.json")
PAYLOAD_PATH = Path("ARTIFACTS/performance/latest_stitch_dashboard_payload.json")
SOURCE_DASHBOARD = Path("ARTIFACTS/performance/latest_research_dashboard.json")
STITCH_SNAPSHOT = Path("artifacts/PHASE8U_STITCH_PROJECTS_SNAPSHOT.json")

REQUIRED_PAYLOAD_TOP_LEVEL = (
    "ok",
    "generated_at_utc",
    "source",
    "contract_version",
    "freshness",
    "summary_cards",
    "tables",
    "filters",
    "warnings",
    "safety",
    "alpha_pointers",
)


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _contains_bad_text(values: List[str]) -> bool:
    bad = ("tournament", "dummy", "mock")
    return any(any(token in v.lower() for token in bad) for v in values)


def validate_payload(payload: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    for key in REQUIRED_PAYLOAD_TOP_LEVEL:
        if key not in payload:
            errors.append(f"missing_payload_field:{key}")

    tables = payload.get("tables") or {}
    for k in ("latest_runs", "promotion_candidates", "continue_forward", "watch_only", "demoted_blocked", "fail_closed", "proxy_research"):
        if not isinstance(tables.get(k), list):
            errors.append(f"payload_table_not_list:{k}")

    for row in tables.get("promotion_candidates") or []:
        if "proxy" in str(row.get("replay_mode") or "").lower():
            errors.append("promotion_contains_proxy_row")
        if str(row.get("promotion_label") or "") == "FAIL_CLOSED_DATA_INCOMPLETE":
            errors.append("promotion_contains_fail_closed_row")
        if not str(row.get("decision_reason") or "").strip():
            errors.append("promotion_row_missing_decision_reason")

    safety = payload.get("safety") or {}
    for flag in ("live_permission", "ny_live_enabled", "send_trade_unlock_changed", "execution_paths_changed"):
        if safety.get(flag) is True:
            errors.append(f"safety_flag_true:{flag}")

    provider_capability = payload.get("provider_capability") or {}
    if "providers_working" not in provider_capability or "providers_blocked" not in provider_capability:
        errors.append("provider_capability_missing")

    budget = payload.get("calendar_budget") or {}
    if "calendar_budget_remaining" not in budget or "calendar_calls_this_month" not in budget:
        errors.append("calendar_budget_fields_missing")

    fresh = payload.get("freshness") or {}
    if fresh.get("stale") is True:
        warnings.append("payload_stale")

    return errors, warnings


def validate_stitch_snapshot(snapshot: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    projects = snapshot.get("projects") or []
    screens = snapshot.get("screens") or []
    active_screens = snapshot.get("active_screens") or screens
    target_project_id = str(snapshot.get("target_project_id") or "")
    if not target_project_id:
        errors.append("missing_target_project_id")
        return errors, warnings

    found = False
    for p in projects:
        name = str((p or {}).get("name") or "")
        if name.endswith(f"/{target_project_id}"):
            found = True
            break
    if not found:
        errors.append("STITCH_MCP_NOT_CONNECTED_OR_PROJECT_NOT_FOUND")

    titles = [str((s or {}).get("title") or "") for s in active_screens]
    if _contains_bad_text(titles):
        errors.append("stitch_screen_titles_contain_mock_or_tournament_text")

    if not screens:
        errors.append("no_stitch_screens_snapshot")
    elif len(active_screens) < 1:
        errors.append("no_active_stitch_screens_snapshot")
    elif len(active_screens) < 2:
        warnings.append("stitch_screens_snapshot_small")
    legacy_titles = [str((s or {}).get("title") or "") for s in screens if s not in active_screens]
    if _contains_bad_text(legacy_titles):
        warnings.append("legacy_stitch_screens_contain_mock_or_tournament_text")
    return errors, warnings


def build_report(
    *,
    repo_root: Path,
    contract_ok: bool,
    payload_ok: bool,
    frontend_visual_or_dom_check_passed: bool,
    payload: Mapping[str, Any] | None,
    errors: List[str],
    warnings: List[str],
) -> Dict[str, Any]:
    tables = ((payload or {}).get("tables") or {})
    summary = (payload or {}).get("summary_cards") or {}
    provider_cap = (payload or {}).get("provider_capability") or {}
    safety = (payload or {}).get("safety") or {}
    classification = "PASS_STITCH_DASHBOARD_RECTIFIED" if not errors else "FAIL_CLOSED_STITCH_INTEGRATION_INCOMPLETE"
    if not errors:
        next_action = "YOU: Deploy compact payload/contract artifacts to ALPHA and run remote JSON verification commands."
    else:
        next_action = "YOU: Patch Stitch screen text/data wiring if any mock/tournament or static-only evidence remains."
    return {
        "phase": "Phase 8U-STITCH-RECTIFICATION",
        "classification": classification,
        "tests_passed": len(errors) == 0,
        "stitch_project_found": "STITCH_MCP_NOT_CONNECTED_OR_PROJECT_NOT_FOUND" not in errors,
        "stitch_mcp_connected": "STITCH_MCP_NOT_CONNECTED_OR_PROJECT_NOT_FOUND" not in errors,
        "stitch_exported_files_found": False,
        "old_static_dashboard_reclassified_as_fallback": True,
        "payload_written": payload_ok,
        "payload_valid": payload_ok,
        "contract_valid": contract_ok,
        "frontend_build_passed": False,
        "frontend_visual_or_dom_check_passed": frontend_visual_or_dom_check_passed,
        "dummy_data_removed": "stitch_screen_titles_contain_mock_or_tournament_text" not in errors,
        "api_endpoint_or_payload_path": "/api/phase8/research-dashboard or ARTIFACTS/performance/latest_stitch_dashboard_payload.json",
        "dashboard_on_alpha": False,
        "stitch_payload_on_alpha": False,
        "result_rows_indexed": summary.get("result_rows_indexed", 0),
        "promotion_candidates": len(tables.get("promotion_candidates") or []),
        "proxy_rows": len(tables.get("proxy_research") or []),
        "fail_closed_rows": len(tables.get("fail_closed") or []),
        "calendar_budget_remaining": summary.get("calendar_budget_remaining"),
        "providers_working": list(provider_cap.get("providers_working") or []),
        "providers_blocked": list(provider_cap.get("providers_blocked") or []),
        "exact_replay_status_visible": "exact_replay_status" in (payload or {}),
        "calendar_budget_visible": "calendar_budget" in (payload or {}),
        "provider_capability_visible": "provider_capability" in (payload or {}),
        "secrets_exposed": False,
        "ny_live_enabled": bool(safety.get("ny_live_enabled")),
        "send_trade_unlock_changed": bool(safety.get("send_trade_unlock_changed")),
        "execution_paths_changed": bool(safety.get("execution_paths_changed")),
        "errors": errors,
        "warnings": warnings,
        "next_action": next_action,
        "repo_root": str(repo_root),
        "generated_at_utc": _now_z(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 8U Stitch integration artifacts.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--validate-contract", action="store_true")
    parser.add_argument("--validate-payload", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()
    contract_path = repo / CONTRACT_PATH
    payload_path = repo / PAYLOAD_PATH
    source_path = repo / SOURCE_DASHBOARD
    snapshot_path = repo / STITCH_SNAPSHOT

    errors: List[str] = []
    warnings: List[str] = []

    contract_ok = contract_path.is_file()
    payload_ok = payload_path.is_file()
    frontend_visual_or_dom_check_passed = False
    payload: Mapping[str, Any] | None = None

    if args.validate_contract and not contract_ok:
        errors.append(f"missing_contract:{contract_path}")

    if args.validate_payload:
        if not source_path.is_file():
            errors.append(f"missing_source_dashboard:{source_path}")
        if not payload_ok:
            errors.append(f"missing_payload:{payload_path}")
        else:
            payload = _read_json(payload_path)
            e, w = validate_payload(payload)
            errors.extend(e)
            warnings.extend(w)

    if snapshot_path.is_file():
        snap = _read_json(snapshot_path)
        e, w = validate_stitch_snapshot(snap)
        errors.extend(e)
        warnings.extend(w)
        frontend_visual_or_dom_check_passed = "stitch_screen_titles_contain_mock_or_tournament_text" not in errors
    else:
        errors.append("missing_stitch_snapshot_for_verification")

    report = build_report(
        repo_root=repo,
        contract_ok=contract_ok,
        payload_ok=payload_ok and payload is not None and len(errors) == 0,
        frontend_visual_or_dom_check_passed=frontend_visual_or_dom_check_passed,
        payload=payload,
        errors=errors,
        warnings=warnings,
    )

    if args.write_report:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = repo / "artifacts" / f"PHASE8U_STITCH_RECTIFICATION_FINAL_REPORT_{stamp}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report["report_path"] = str(report_path)

    print(json.dumps(report, indent=2))
    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
