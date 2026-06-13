#!/usr/bin/env python3
"""
Phase 8P: build compact JSON and static HTML dashboard from the research index.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.calendar_budgeted_client import merge_usage_into_dashboard_patch  # noqa: E402
from scripts.phase8p_index_research_results import DEFAULT_INDEX_JSON, build_index, write_index  # noqa: E402
from scripts.phase8p_score_and_label_results import (  # noqa: E402
    BLOCK,
    CONTINUE,
    DEMOTE,
    FAIL_CLOSED,
    PROMOTE,
    WATCH,
)

PHASE = "Phase 8P"
PERFORMANCE_ROOT = Path("ARTIFACTS/performance")
DEFAULT_DASHBOARD_JSON = PERFORMANCE_ROOT / "latest_research_dashboard.json"
DEFAULT_DIARY_JSON = PERFORMANCE_ROOT / "latest_weekend_research_diary.json"
DEFAULT_DASHBOARD_DIR = PERFORMANCE_ROOT / "research_dashboard"

TABLE_COLUMNS = [
    "generated_at_utc",
    "strategy_name",
    "instrument",
    "session_bucket",
    "granularity",
    "lookback_days",
    "replay_mode",
    "clean_sample_count",
    "expectancy_r",
    "profit_factor_r",
    "max_loss_streak",
    "drawdown_proxy_r",
    "recommendation_label",
    "promotion_label",
    "decision_reason",
]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _label_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        label = str(row.get("promotion_label") or "UNKNOWN")
        counts[label] = counts.get(label, 0) + 1
    return counts


def _sort_key(row: Mapping[str, Any]) -> tuple[float, float, float]:
    return (_num(row.get("expectancy_r")), _num(row.get("profit_factor_r")), _num(row.get("clean_sample_count")))


def _top(rows: List[Mapping[str, Any]], *, labels: Iterable[str] | None = None, limit: int = 50) -> List[Dict[str, Any]]:
    allowed = set(labels or [])
    selected = [dict(r) for r in rows if not allowed or r.get("promotion_label") in allowed]
    return sorted(selected, key=_sort_key, reverse=True)[:limit]


def _strategy_group_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("strategy_name") or ""),
        str(row.get("instrument") or ""),
        str(row.get("granularity") or ""),
        str(row.get("session_bucket") or ""),
    )


def _dedupe_unique_strategies(rows: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """One row per (strategy, instrument, granularity, session); keep best by sort_key."""
    best: Dict[tuple[str, str, str, str], Dict[str, Any]] = {}
    for r in rows:
        k = _strategy_group_key(r)
        if k not in best or _sort_key(r) > _sort_key(best[k]):
            best[k] = dict(r)
    return sorted(best.values(), key=_sort_key, reverse=True)


def _group_leaderboard(rows: List[Mapping[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    groups: Dict[tuple[Any, ...], List[Mapping[str, Any]]] = {}
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        groups.setdefault(key, []).append(row)
    out = []
    for key, items in groups.items():
        scored = [_num(i.get("expectancy_r")) for i in items]
        pfs = [_num(i.get("profit_factor_r")) for i in items]
        entry = {k: v for k, v in zip(keys, key)}
        entry.update(
            {
                "run_count": len(items),
                "avg_expectancy_r": round(sum(scored) / len(scored), 4) if scored else None,
                "best_expectancy_r": max(scored) if scored else None,
                "avg_profit_factor_r": round(sum(pfs) / len(pfs), 4) if pfs else None,
                "promotion_label_counts": _label_counts(items),
            }
        )
        out.append(entry)
    return sorted(out, key=lambda r: _num(r.get("best_expectancy_r")), reverse=True)


def _phase8r_capability_patch(repo_root: Path) -> Dict[str, Any]:
    """Snapshot from latest Phase 8R capability run (if present)."""
    path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8r_provider_capability_report.json"
    if not path.is_file():
        return {"phase8r_capability_report_present": False}
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"phase8r_capability_report_present": False}

    def _blocked_from_probes(probes: Any) -> List[str]:
        out: List[str] = []
        if not isinstance(probes, list):
            return out
        for p in probes:
            if not isinstance(p, dict):
                continue
            lab = str(p.get("provider") or "")
            if lab and int(p.get("rows_returned") or 0) <= 0:
                out.append(lab)
        return out

    working: List[str] = []
    working.extend(str(x) for x in (r.get("working_news_providers") or []) if x)
    working.extend(str(x) for x in (r.get("working_calendar_providers") or []) if x)
    working.extend(str(x) for x in (r.get("working_macro_providers") or []) if x)
    blocked = _blocked_from_probes(r.get("probe_news")) + _blocked_from_probes(r.get("probe_calendar"))
    return {
        "phase8r_capability_report_present": True,
        "providers_working": working,
        "providers_blocked": blocked,
        "bypass_callers_detected": list(r.get("calendar_budget_bypass_paths_live") or []),
    }


def _phase8o_latest_pointer_patch(repo_root: Path) -> Dict[str, Any]:
    """Values from latest Phase 8O summary on disk (if present)."""
    path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8o_backtest_summary.json"
    absent = {
        "latest_phase8o_backtest_summary_present": False,
        "latest_phase8o_classification": None,
        "exact_strategy_replay": False,
        "news_reconstruction_available": None,
        "calendar_reconstruction_available": None,
    }
    if not path.is_file():
        return dict(absent)
    try:
        s = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {**absent, "latest_phase8o_classification": "JSON_INVALID"}
    return {
        "latest_phase8o_backtest_summary_present": True,
        "latest_phase8o_classification": s.get("classification"),
        "exact_strategy_replay": bool(s.get("exact_strategy_replay")),
        "news_reconstruction_available": s.get("news_reconstruction_available"),
        "calendar_reconstruction_available": s.get("calendar_reconstruction_available"),
    }


def _phase8x_tournament_patch(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "ARTIFACTS" / "performance" / "phase8x_tournament_leaderboard.json"
    if not path.is_file():
        return {"phase8x_tournament_leaderboard_present": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"phase8x_tournament_leaderboard_present": False, "phase8x_tournament_leaderboard_error": "JSON_INVALID"}
    return {"phase8x_tournament_leaderboard_present": True, "phase8x_tournament_leaderboard": payload}


def _phase8x_batch_progress_patch(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8x_batch_progress.json"
    absent: Dict[str, Any] = {"phase8x_batch_progress_present": False, "phase8x_batch_progress": None}
    if not path.is_file():
        return dict(absent)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {**absent, "phase8x_batch_progress_error": "JSON_INVALID"}
    if not isinstance(data, dict):
        return {**absent, "phase8x_batch_progress_error": "NOT_OBJECT"}
    return {"phase8x_batch_progress_present": True, "phase8x_batch_progress": data}


def _phase8y_patch(repo_root: Path) -> Dict[str, Any]:
    coverage_path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8y_data_coverage_manifest.json"
    cost_path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8y_api_cost_estimate.json"
    verify_path = repo_root / "ARTIFACTS" / "performance" / "latest_phase8y_context_pack_verification.json"
    if not coverage_path.is_file():
        return {"phase8y_data_coverage_manifest_present": False}
    try:
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"phase8y_data_coverage_manifest_present": False, "phase8y_manifest_error": "JSON_INVALID"}
    cost: Dict[str, Any] = {}
    verify: Dict[str, Any] = {}
    if cost_path.is_file():
        try:
            cost = json.loads(cost_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cost = {}
    if verify_path.is_file():
        try:
            verify = json.loads(verify_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verify = {}
    return {
        "phase8y_data_coverage_manifest_present": True,
        "phase8y_api_cost_estimate_present": bool(cost),
        "phase8y_context_pack_verified": bool(verify.get("all_files_verified")),
        "phase8y_estimated_api_calls_needed": coverage.get("estimated_api_calls_needed"),
        "phase8y_estimated_paid_calendar_calls_needed": coverage.get("estimated_paid_calendar_calls_needed"),
        "phase8y_exact_replay_possible": bool(coverage.get("exact_replay_possible")),
        "phase8y_missing_windows": list(coverage.get("missing_windows") or []),
        "phase8y_safe_to_run_batch": bool(coverage.get("safe_to_run_batch")) and bool(cost.get("safe_to_run_batch", True)),
    }


def _fallback_replay_flags_from_rows(rows: List[Mapping[str, Any]]) -> Dict[str, Any]:
    """When latest_phase8o_backtest_summary.json is missing, derive booleans from indexed rows."""
    ex = [bool(r.get("exact_strategy_replay")) for r in rows if r.get("exact_strategy_replay") is not None]
    news = [r.get("news_reconstruction_available") for r in rows]
    cal = [r.get("calendar_reconstruction_available") for r in rows]
    return {
        "exact_strategy_replay": any(ex) if ex else False,
        "news_reconstruction_available": any(n is True for n in news) if news else False,
        "calendar_reconstruction_available": any(c is True for c in cal) if cal else False,
    }


def build_dashboard(
    index: Mapping[str, Any],
    *,
    alpha_import_size_bytes: int = 0,
    retention_deleted_count: int = 0,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = [dict(r) for r in index.get("rows") or []]
    latest_runs = sorted(rows, key=lambda r: str(r.get("generated_at_utc") or ""), reverse=True)[:100]
    provider_status = {
        "news_available_runs": sum(1 for r in rows if r.get("news_reconstruction_available") is True),
        "calendar_available_runs": sum(1 for r in rows if r.get("calendar_reconstruction_available") is True),
        "news_unavailable_runs": sum(1 for r in rows if r.get("news_reconstruction_available") is not True),
        "calendar_unavailable_runs": sum(1 for r in rows if r.get("calendar_reconstruction_available") is not True),
    }
    diary = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "PHASE8P_WEEKEND_RESEARCH_DIARY",
        "runs_indexed": len(rows),
        "top_candidates": _top(rows, labels=[PROMOTE, CONTINUE], limit=10),
        "demotions": _top(rows, labels=[DEMOTE, BLOCK], limit=10),
        "fail_closed": [r for r in latest_runs if r.get("promotion_label") == FAIL_CLOSED][:10],
        "next_action_owner": "CURSOR",
        "next_action": "Review PROMOTE_REVIEW_CANDIDATE rows manually; research labels do not enable live or paper lane changes.",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    proxy_rows = [
        r
        for r in rows
        if "proxy" in str(r.get("replay_mode") or "").lower()
        or str(r.get("replay_mode") or "") == "best_available_proxy_reconstruction"
    ]
    fail_closed_rows = [r for r in latest_runs if r.get("promotion_label") == FAIL_CLOSED]
    promotion_candidates = _dedupe_unique_strategies(_top(rows, labels=[PROMOTE]))
    continue_forward_candidates = _top(rows, labels=[CONTINUE])
    watch_only_candidates = _top(rows, labels=[WATCH])
    label_hist = _label_counts(rows)
    out: Dict[str, Any] = {
        "ok": True,
        "phase": PHASE,
        "classification": "PHASE8P_RESEARCH_DASHBOARD",
        "generated_at_utc": utc_now_iso_z(),
        "dashboard_freshness_seconds": 0,
        "result_rows_indexed": len(rows),
        "research_summary": {
            "runs_indexed": len(rows),
            "promotion_label_counts": label_hist,
            "promotion_candidate_count": len(promotion_candidates),
            "continue_forward_count": len(continue_forward_candidates),
            "watch_only_count": len(watch_only_candidates),
            "proxy_row_count": len(proxy_rows),
            "fail_closed_row_count": len(fail_closed_rows),
        },
        "latest_research_runs": latest_runs,
        "strategy_leaderboard": _group_leaderboard(rows, ["strategy_name", "instrument", "granularity"]),
        "pair_session_leaderboard": _group_leaderboard(rows, ["instrument", "session_bucket", "granularity"]),
        "promotion_candidates": promotion_candidates,
        "continue_forward_candidates": continue_forward_candidates,
        "watch_only_candidates": watch_only_candidates,
        "demoted_blocked_candidates": _top(rows, labels=[DEMOTE, BLOCK]),
        "fail_closed_data_incomplete_runs": fail_closed_rows,
        "fail_closed_rows": fail_closed_rows,
        "proxy_rows": proxy_rows[:50],
        "news_calendar_provider_status": provider_status,
        "weekly_diary_summary": diary,
        "storage_safety": {
            "alpha_import_size_bytes": int(alpha_import_size_bytes),
            "dashboard_size_bytes": 0,
            "index_size_bytes": 0,
            "local_cache_size_bytes": 0,
            "retention_deleted_count": int(retention_deleted_count),
            "alpha_result_pack_cap_mb": 25,
            "alpha_dashboard_json_cap_mb": 5,
            "alpha_index_jsonl_cap_mb": 25,
            "retain_raw_candles_on_alpha": False,
        },
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "alpha_latest_pointers": {
            "latest_research_dashboard": "ARTIFACTS/performance/latest_research_dashboard.json",
            "latest_stitch_dashboard_contract": "ARTIFACTS/performance/latest_stitch_dashboard_contract.json",
            "latest_phase8o_backtest_summary": "ARTIFACTS/performance/latest_phase8o_backtest_summary.json",
            "latest_phase8r_provider_capability_report": "ARTIFACTS/performance/latest_phase8r_provider_capability_report.json",
            "research_dashboard_html_dir": "ARTIFACTS/performance/research_dashboard/",
        },
        "stitch_mcp_contract_health": {
            "contract_version": "phase8t_v1",
            "validation_script": "scripts/phase8t_validate_stitch_dashboard_contract.py",
            "notes": "Static research_dashboard/index.html is fallback-only. Stitch integration must read canonical JSON payload/contract artifacts. "
            "Run Phase 8T/8U validators after each dashboard rebuild.",
        },
        "providers_working": [],
        "providers_blocked": [],
        "calendar_calls_this_month": None,
        "calendar_budget_remaining": None,
        "calendar_cache_hit_rate": None,
    }
    if repo_root is not None:
        rr = repo_root.expanduser().resolve()
        out.update(merge_usage_into_dashboard_patch(rr))
        out.update(_phase8x_tournament_patch(rr))
        out.update(_phase8x_batch_progress_patch(rr))
        out.update(_phase8y_patch(rr))
        out.update(_phase8r_capability_patch(rr))
        p8o = _phase8o_latest_pointer_patch(rr)
        if not p8o.get("latest_phase8o_backtest_summary_present"):
            p8o.update(_fallback_replay_flags_from_rows(rows))
        out.update(
            {
                "latest_phase8o_classification": p8o.get("latest_phase8o_classification"),
                "exact_strategy_replay": bool(p8o.get("exact_strategy_replay")),
                "news_reconstruction_available": p8o.get("news_reconstruction_available"),
                "calendar_reconstruction_available": p8o.get("calendar_reconstruction_available"),
                "latest_phase8o_backtest_summary_present": p8o.get("latest_phase8o_backtest_summary_present"),
            }
        )
    else:
        fb = _fallback_replay_flags_from_rows(rows)
        out.update(
            {
                "latest_phase8o_classification": None,
                "exact_strategy_replay": fb["exact_strategy_replay"],
                "news_reconstruction_available": fb["news_reconstruction_available"],
                "calendar_reconstruction_available": fb["calendar_reconstruction_available"],
                "latest_phase8o_backtest_summary_present": False,
            }
        )
    return out


def _badge_class(label: Any) -> str:
    if label == PROMOTE:
        return "green"
    if label in {CONTINUE, WATCH}:
        return "amber"
    return "red"


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _table(title: str, rows: List[Mapping[str, Any]], columns: List[str] = TABLE_COLUMNS) -> str:
    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = []
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col)
            if col == "promotion_label":
                cells.append(f'<td><span class="badge {_badge_class(value)}">{_cell(value)}</span></td>')
            else:
                cells.append(f"<td>{_cell(value)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    empty = '<tr><td colspan="15" class="empty">No rows.</td></tr>' if not body else ""
    return f"<section><h2>{html.escape(title)}</h2><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}{empty}</tbody></table></section>"


def render_html(dashboard: Mapping[str, Any]) -> str:
    tables = [
        _table("Latest Research Runs", list(dashboard.get("latest_research_runs") or [])),
        _table("Promotion Candidates (PROMOTE only)", list(dashboard.get("promotion_candidates") or [])),
        _table("Continue Forward (not auto-promotable)", list(dashboard.get("continue_forward_candidates") or [])),
        _table("Watch Only", list(dashboard.get("watch_only_candidates") or [])),
        _table("Demoted / Blocked Candidates", list(dashboard.get("demoted_blocked_candidates") or [])),
        _table("Fail-Closed / Data-Incomplete Runs", list(dashboard.get("fail_closed_data_incomplete_runs") or [])),
        _table("Proxy Research Rows", list(dashboard.get("proxy_rows") or [])),
    ]
    rows = dashboard.get("latest_research_runs") or []
    counts = _label_counts(rows)
    count_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in sorted(counts.items()))
    provider = dashboard.get("news_calendar_provider_status") or {}
    provider_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in sorted(provider.items()))
    cal_calls = dashboard.get("calendar_calls_this_month")
    cal_left = dashboard.get("calendar_budget_remaining")
    cal_hit = dashboard.get("calendar_cache_hit_rate")
    cal_last = dashboard.get("last_calendar_api_call_utc")
    cal_blocked = dashboard.get("providers_blocked_by_budget")
    usage_lines = [
        f"calendar_calls_this_month={_cell(cal_calls)}",
        f"calendar_budget_remaining={_cell(cal_left)}",
        f"calendar_cache_hit_rate={_cell(cal_hit)}",
        f"last_calendar_api_call_utc={_cell(cal_last)}",
        f"providers_blocked_by_budget={_cell(cal_blocked)}",
    ]
    usage_html = "".join(f"<li>{html.escape(line)}</li>" for line in usage_lines)
    prov_ok = dashboard.get("providers_working")
    prov_bad = dashboard.get("providers_blocked")
    bypass = dashboard.get("bypass_callers_detected")
    cap_html = "".join(
        f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>"
        for k, v in (
            ("providers_working", prov_ok),
            ("providers_blocked", prov_bad),
            ("bypass_callers_detected", bypass),
        )
    )
    p8o_cls = dashboard.get("latest_phase8o_classification")
    ex_rep = dashboard.get("exact_strategy_replay")
    rs = dashboard.get("research_summary") or {}
    phase8o_html = "".join(
        f"<li><b>{html.escape(k)}</b>: {_cell(v)}</li>"
        for k, v in (
            ("latest_phase8o_classification", p8o_cls),
            ("exact_strategy_replay", ex_rep),
            ("result_rows_indexed", dashboard.get("result_rows_indexed")),
            ("dashboard_freshness_seconds", dashboard.get("dashboard_freshness_seconds")),
        )
    )
    stitch_health = dashboard.get("stitch_mcp_contract_health") or {}
    stitch_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in sorted(stitch_health.items()))
    alpha_ptr = dashboard.get("alpha_latest_pointers") or {}
    alpha_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in sorted(alpha_ptr.items()))
    summary_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in sorted(rs.items()))
    p8y_lines = [
        ("phase8y_data_coverage_manifest_present", dashboard.get("phase8y_data_coverage_manifest_present")),
        ("phase8y_api_cost_estimate_present", dashboard.get("phase8y_api_cost_estimate_present")),
        ("phase8y_context_pack_verified", dashboard.get("phase8y_context_pack_verified")),
        ("phase8y_estimated_api_calls_needed", dashboard.get("phase8y_estimated_api_calls_needed")),
        ("phase8y_estimated_paid_calendar_calls_needed", dashboard.get("phase8y_estimated_paid_calendar_calls_needed")),
        ("phase8y_exact_replay_possible", dashboard.get("phase8y_exact_replay_possible")),
        ("phase8y_safe_to_run_batch", dashboard.get("phase8y_safe_to_run_batch")),
        ("phase8y_missing_windows_count", len(dashboard.get("phase8y_missing_windows") or [])),
    ]
    p8y_html = "".join(f"<li><b>{_cell(k)}</b>: {_cell(v)}</li>" for k, v in p8y_lines)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Phase 8P Research Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #17202a; }}
    h1 {{ margin-bottom: 4px; }}
    .meta, .empty {{ color: #667085; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 18px 0; }}
    .card {{ border: 1px solid #d0d5dd; border-radius: 8px; padding: 12px; background: #fff; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-bottom: 28px; }}
    th, td {{ border: 1px solid #d0d5dd; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #f2f4f7; position: sticky; top: 0; }}
    .badge {{ border-radius: 10px; padding: 2px 8px; font-weight: bold; white-space: nowrap; }}
    .green {{ background: #dcfae6; color: #067647; }}
    .amber {{ background: #fef0c7; color: #b54708; }}
    .red {{ background: #fee4e2; color: #b42318; }}
  </style>
</head>
<body>
  <h1>Phase 8P Research Dashboard</h1>
  <p class="meta">Generated: {_cell(dashboard.get("generated_at_utc"))}. Research labels never grant live permission.</p>
  <div class="grid">
    <div class="card"><h2>Research Summary</h2><ul>{summary_html}</ul></div>
    <div class="card"><h2>Promotion Label Counts</h2><ul>{count_html}</ul></div>
    <div class="card"><h2>News / Calendar Status</h2><ul>{provider_html}</ul></div>
    <div class="card"><h2>Phase 8S Calendar API Usage</h2><ul>{usage_html}</ul></div>
    <div class="card"><h2>Provider capability (8R snapshot)</h2><ul>{cap_html}</ul></div>
    <div class="card"><h2>Exact Replay Status</h2><ul>{phase8o_html}</ul></div>
    <div class="card"><h2>Phase 8Y Coverage/API Preflight</h2><ul>{p8y_html}</ul></div>
    <div class="card"><h2>ALPHA Latest Pointers</h2><ul>{alpha_html}</ul></div>
    <div class="card"><h2>Stitch / MCP Contract Health</h2><ul>{stitch_html}</ul></div>
    <div class="card"><h2>Safety</h2><p>paper_review_only=true<br>live_permission=false<br>ny_live_enabled=false<br>send_trade_unlock_changed=false<br>execution_paths_changed=false</p></div>
  </div>
  {''.join(tables)}
  <script id="phase8p-dashboard-json" type="application/json">{html.escape(json.dumps(dashboard, sort_keys=True))}</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 8P research dashboard JSON and static HTML.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--index-json", type=Path, default=DEFAULT_INDEX_JSON)
    parser.add_argument("--dashboard-json", type=Path, default=DEFAULT_DASHBOARD_JSON)
    parser.add_argument("--diary-json", type=Path, default=DEFAULT_DIARY_JSON)
    parser.add_argument("--dashboard-dir", type=Path, default=DEFAULT_DASHBOARD_DIR)
    args = parser.parse_args()

    try:
        repo_root = args.repo_root.expanduser().resolve()
        index_json = args.index_json if args.index_json.is_absolute() else repo_root / args.index_json
        if index_json.is_file():
            index = json.loads(index_json.read_text(encoding="utf-8"))
        else:
            index = build_index(repo_root)
            write_index(index, index_json, repo_root / "ARTIFACTS/performance/research_results_index.jsonl")
        dashboard = build_dashboard(index, repo_root=repo_root)
        dashboard_json = args.dashboard_json if args.dashboard_json.is_absolute() else repo_root / args.dashboard_json
        diary_json = args.diary_json if args.diary_json.is_absolute() else repo_root / args.diary_json
        dashboard_dir = args.dashboard_dir if args.dashboard_dir.is_absolute() else repo_root / args.dashboard_dir
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        html_path = dashboard_dir / "index.html"
        dashboard_json.parent.mkdir(parents=True, exist_ok=True)
        dashboard_json.write_text(json.dumps(dashboard, indent=2, sort_keys=True), encoding="utf-8")
        diary_json.write_text(json.dumps(dashboard["weekly_diary_summary"], indent=2, sort_keys=True), encoding="utf-8")
        html_path.write_text(render_html(dashboard), encoding="utf-8")
        dashboard["storage_safety"]["dashboard_size_bytes"] = dashboard_json.stat().st_size + html_path.stat().st_size
        dashboard["storage_safety"]["index_size_bytes"] = index_json.stat().st_size if index_json.is_file() else 0
        dashboard_json.write_text(json.dumps(dashboard, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"ok": True, "dashboard_json": str(dashboard_json), "dashboard_html": str(html_path), "diary_json": str(diary_json), "rows": len(index.get("rows") or [])}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
