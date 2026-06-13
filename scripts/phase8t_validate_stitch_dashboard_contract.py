#!/usr/bin/env python3
"""
Phase 8T: validate latest_research_dashboard.json against the Stitch / external-dashboard contract.

Read-only with respect to trading runtime. Never prints secrets.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONTRACT_REL = Path("ARTIFACTS/performance/latest_stitch_dashboard_contract.json")
DEFAULT_DASHBOARD_REL = Path("ARTIFACTS/performance/latest_research_dashboard.json")

PHASE = "Phase 8T"

# Dashboard payload must expose these keys for Stitch (flat JSON).
REQUIRED_DASHBOARD_FIELDS: Tuple[str, ...] = (
    "generated_at_utc",
    "dashboard_freshness_seconds",
    "result_rows_indexed",
    "research_summary",
    "latest_research_runs",
    "promotion_candidates",
    "continue_forward_candidates",
    "watch_only_candidates",
    "demoted_blocked_candidates",
    "fail_closed_data_incomplete_runs",
    "proxy_rows",
    "fail_closed_rows",
    "providers_working",
    "providers_blocked",
    "calendar_calls_this_month",
    "calendar_budget_remaining",
    "calendar_cache_hit_rate",
    "last_calendar_api_call_utc",
    "latest_phase8o_classification",
    "exact_strategy_replay",
    "news_reconstruction_available",
    "calendar_reconstruction_available",
    "alpha_latest_pointers",
    "stitch_mcp_contract_health",
    "paper_review_only",
    "live_permission",
    "ny_live_enabled",
    "send_trade_unlock_changed",
    "execution_paths_changed",
)

PROXY_REPLAY_MODES = frozenset(
    {
        "best_available_proxy_reconstruction",
    }
)


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_generated_at(ts: Any) -> Optional[datetime]:
    if ts is None or not isinstance(ts, str):
        return None
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _replay_mode_bad(mode: Any) -> bool:
    m = str(mode or "").strip().lower()
    if not m:
        return False
    if "fail_closed" in m or m.startswith("fail"):
        return True
    if m in PROXY_REPLAY_MODES or "proxy" in m:
        return True
    return False


def compute_freshness_seconds(dashboard: Mapping[str, Any], *, now: Optional[datetime] = None) -> int:
    """Seconds between generated_at_utc and now (UTC)."""
    gen = _parse_generated_at(dashboard.get("generated_at_utc"))
    if gen is None:
        return -1
    n = now or datetime.now(timezone.utc)
    if gen.tzinfo is None:
        gen = gen.replace(tzinfo=timezone.utc)
    return max(0, int((n - gen).total_seconds()))


def validate_dashboard_payload(
    dashboard: Mapping[str, Any],
    *,
    freshness_warn_seconds: int = 86400,
    calendar_budget_warn_remaining: int = 50,
) -> Tuple[List[str], List[str]]:
    """
    Return (errors, warnings). Errors block PASS; warnings are non-fatal.
    """
    errors: List[str] = []
    warnings: List[str] = []

    for key in REQUIRED_DASHBOARD_FIELDS:
        if key not in dashboard:
            errors.append(f"missing_required_field:{key}")

    if not isinstance(dashboard.get("promotion_candidates"), list):
        if "promotion_candidates" in dashboard:
            errors.append("promotion_candidates_not_list")
    if not isinstance(dashboard.get("proxy_rows"), list):
        if "proxy_rows" in dashboard:
            errors.append("proxy_rows_not_list")
    if not isinstance(dashboard.get("fail_closed_rows"), list):
        if "fail_closed_rows" in dashboard:
            errors.append("fail_closed_rows_not_list")

    for row in dashboard.get("promotion_candidates") or []:
        if not isinstance(row, dict):
            errors.append("promotion_candidate_not_object")
            continue
        mode = row.get("replay_mode")
        if _replay_mode_bad(mode):
            errors.append(f"promotion_candidate_invalid_replay_mode:{mode}")
        if str(row.get("promotion_label") or "") == "FAIL_CLOSED_DATA_INCOMPLETE":
            errors.append("promotion_candidate_is_fail_closed")

    for flag in ("ny_live_enabled", "live_permission", "send_trade_unlock_changed", "execution_paths_changed"):
        if dashboard.get(flag) is True:
            errors.append(f"safety_flag_true:{flag}")

    fresh = compute_freshness_seconds(dashboard)
    if fresh < 0:
        warnings.append("dashboard_freshness_unparsed_generated_at_utc")
    elif fresh > freshness_warn_seconds:
        warnings.append(f"dashboard_stale_seconds:{fresh}")

    blocked = dashboard.get("providers_blocked")
    if isinstance(blocked, list) and len(blocked) > 0:
        warnings.append(f"providers_blocked_non_empty:{len(blocked)}")

    if dashboard.get("exact_strategy_replay") is False:
        warnings.append("exact_strategy_replay_false")

    cal_left = dashboard.get("calendar_budget_remaining")
    try:
        if cal_left is not None and int(cal_left) < calendar_budget_warn_remaining:
            warnings.append(f"calendar_budget_low_remaining:{cal_left}")
    except (TypeError, ValueError):
        pass

    return errors, warnings


def build_stitch_contract_document(repo_root: Path) -> Dict[str, Any]:
    """Static contract: schema, allowed values, and where Stitch / operators read payloads."""
    return {
        "ok": True,
        "phase": PHASE,
        "contract_version": "phase8t_v1",
        "generated_at_utc": _utc_now_iso_z(),
        "description": "Stitch and external front-ends must consume canonical JSON payload/contract artifacts. Static Phase 8P HTML is fallback-only.",
        "primary_payload": {
            "path": "ARTIFACTS/performance/latest_research_dashboard.json",
            "format": "json",
            "required_top_level_fields": list(REQUIRED_DASHBOARD_FIELDS),
        },
        "supporting_artifacts": {
            "latest_phase8r_provider_capability_report": "ARTIFACTS/performance/latest_phase8r_provider_capability_report.json",
            "latest_phase8o_backtest_summary": "ARTIFACTS/performance/latest_phase8o_backtest_summary.json",
            "latest_calendar_api_usage": "ARTIFACTS/performance/latest_calendar_api_usage_report.json",
        },
        "mcp_and_api_mapping": {
            "note": "This repo does not host a dedicated dashboard API service by default. Operators deploy compact JSON artifacts under ARTIFACTS/performance. "
            "The static HTML page is fallback-only and must not be treated as Stitch source of truth.",
            "non_secrets_endpoints": [
                "file://<repo>/ARTIFACTS/performance/latest_research_dashboard.json",
                "file://<repo>/ARTIFACTS/performance/latest_stitch_dashboard_contract.json",
                "file://<repo>/ARTIFACTS/performance/latest_stitch_dashboard_payload.json",
            ],
        },
        "row_separation_rules": {
            "promotion_candidates": "PROMOTE_REVIEW_CANDIDATE only; must not include proxy or fail-closed replay modes.",
            "continue_forward_candidates": "CONTINUE_FORWARD_PAPER_REVIEW (not promotable as first-class).",
            "watch_only_candidates": "WATCH_ONLY",
            "proxy_rows": "Rows whose replay_mode indicates proxy / best_available_proxy_reconstruction.",
            "fail_closed_rows": "Rows labeled FAIL_CLOSED_DATA_INCOMPLETE or fail-closed classification.",
        },
        "validation": {
            "command": "python scripts/phase8t_validate_stitch_dashboard_contract.py --repo-root . --validate",
        },
    }


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8T Stitch dashboard contract write/validate.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dashboard-json", type=Path, default=DEFAULT_DASHBOARD_REL)
    parser.add_argument("--contract-json", type=Path, default=DEFAULT_CONTRACT_REL)
    parser.add_argument("--write-contract", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--freshness-warn-seconds", type=int, default=86400)
    parser.add_argument("--calendar-budget-warn-remaining", type=int, default=50)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    dashboard_path = args.dashboard_json if args.dashboard_json.is_absolute() else repo_root / args.dashboard_json
    contract_path = args.contract_json if args.contract_json.is_absolute() else repo_root / args.contract_json

    if args.write_contract:
        doc = build_stitch_contract_document(repo_root)
        _write_json(contract_path, doc)
        print(json.dumps({"ok": True, "wrote": str(contract_path)}, indent=2))

    if not args.write_report and not args.validate:
        return 0

    if args.write_report or args.validate:
        if not dashboard_path.is_file():
            err = {
                "ok": False,
                "phase": PHASE,
                "error": "missing_dashboard_json",
                "path": str(dashboard_path),
            }
            print(json.dumps(err, indent=2))
            return 1
        try:
            dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "phase": PHASE, "error": f"invalid_json:{exc}"}, indent=2))
            return 1

        errors, warnings = validate_dashboard_payload(
            dashboard,
            freshness_warn_seconds=args.freshness_warn_seconds,
            calendar_budget_warn_remaining=args.calendar_budget_warn_remaining,
        )
        report = {
            "ok": len(errors) == 0,
            "phase": PHASE,
            "classification": "PHASE8T_STITCH_CONTRACT_VALIDATION",
            "generated_at_utc": _utc_now_iso_z(),
            "dashboard_json": str(dashboard_path),
            "contract_json": str(contract_path),
            "errors": errors,
            "warnings": warnings,
            "dashboard_freshness_seconds_computed": compute_freshness_seconds(dashboard),
        }

        if args.write_report:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            report_path = repo_root / "artifacts" / f"PHASE8T_STITCH_DASHBOARD_CONTRACT_REPORT_{stamp}.json"
            _write_json(report_path, report)
            report["report_written"] = str(report_path)

        print(json.dumps(report, indent=2))
        return 0 if len(errors) == 0 else 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
