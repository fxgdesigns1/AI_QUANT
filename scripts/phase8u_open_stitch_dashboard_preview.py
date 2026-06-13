#!/usr/bin/env python3
"""
Write a local HTML preview from ARTIFACTS Phase 8U Stitch payload (real JSON only).
Opens default browser on Windows when --open-browser is set.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BANNER_MAIN = "REAL PHASE 8U STITCH PAYLOAD PREVIEW"
BANNER_NOT_FALLBACK = "NOT FALLBACK STATIC HTML"


def _h(s: Any) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def _read_payload(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_error_page(message: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Phase 8U Preview — Error</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; background: #1a0a0a; color: #fecaca; }}
    h1 {{ color: #fee2e2; }}
  </style>
</head>
<body>
  <h1>{_h(BANNER_MAIN)} — BLOCKED</h1>
  <p><strong>{_h(BANNER_NOT_FALLBACK)}</strong> (this page is an explicit error state, not the old static HTML.)</p>
  <pre>{_h(message)}</pre>
</body>
</html>
"""


def _table_section(title: str, rows: List[Mapping[str, Any]], columns: Optional[List[str]] = None) -> str:
    if not rows:
        return f'<section class="section"><h2>{_h(title)}</h2><p class="empty">No rows.</p></section>'
    if columns is None:
        keys: List[str] = []
        for r in rows:
            if isinstance(r, dict):
                keys.extend(r.keys())
        columns = sorted(set(keys))
    if not columns:
        return f'<section class="section"><h2>{_h(title)}</h2><p class="empty">No columns.</p></section>'
    head = "".join(f"<th>{_h(c)}</th>" for c in columns)
    body_rows = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        cells = "".join(f"<td><code>{_h(r.get(c))}</code></td>" for c in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"""
<section class="section">
  <h2>{_h(title)}</h2>
  <div class="table-wrap">
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>{"".join(body_rows)}</tbody>
    </table>
  </div>
</section>
"""


def _summary_grid(payload: Mapping[str, Any]) -> str:
    sc = payload.get("summary_cards") or {}
    cal = payload.get("calendar_budget") or {}
    prov = payload.get("provider_capability") or {}
    fr = payload.get("freshness") or {}
    items: List[tuple[str, str]] = [
        ("contract_version", str(payload.get("contract_version") or "")),
        ("generated_at_utc", str(payload.get("generated_at_utc") or "")),
        ("dashboard freshness (seconds)", str(fr.get("seconds", ""))),
        ("dashboard freshness status", str(fr.get("status", ""))),
        ("result_rows_indexed", str((sc or {}).get("result_rows_indexed", ""))),
        ("promotion_candidates_count", str((sc or {}).get("promotion_candidates_count", ""))),
        ("calendar_calls_this_month", str(cal.get("calendar_calls_this_month", ""))),
        ("calendar_budget_remaining", str(cal.get("calendar_budget_remaining", ""))),
        ("calendar_cache_hit_rate", str(cal.get("calendar_cache_hit_rate", ""))),
        ("last_calendar_api_call_utc", str(cal.get("last_calendar_api_call_utc", ""))),
        ("estimated_calls_needed_next_batch", str((sc or {}).get("estimated_calls_needed_next_batch", ""))),
        ("estimated_paid_calendar_calls_needed", str((sc or {}).get("estimated_paid_calendar_calls_needed", ""))),
        ("exact_replay_readiness", str((sc or {}).get("exact_replay_readiness", ""))),
        ("missing_data_windows_count", str((sc or {}).get("missing_data_windows_count", ""))),
        ("safe_to_run_batch", str((sc or {}).get("safe_to_run_batch", ""))),
        ("providers_working (count)", str((sc or {}).get("providers_working_count", ""))),
        ("providers_blocked (count)", str((sc or {}).get("providers_blocked_count", ""))),
    ]
    prov_w = prov.get("providers_working")
    prov_b = prov.get("providers_blocked")
    if isinstance(prov_w, list):
        items.append(("providers_working", ", ".join(str(x) for x in prov_w)))
    if isinstance(prov_b, list):
        items.append(("providers_blocked", ", ".join(str(x) for x in prov_b)))
    ex = payload.get("exact_replay_status") or {}
    items.extend(
        [
            ("latest_phase8o_classification", str(ex.get("latest_phase8o_classification", ""))),
            ("exact_strategy_replay", str(ex.get("exact_strategy_replay", ""))),
        ]
    )
    cards = "".join(
        f'<div class="card"><div class="k">{_h(k)}</div><div class="v">{_h(v)}</div></div>' for k, v in items
    )
    return f'<div class="summary-grid">{cards}</div>'


def _safety_block(safety: Mapping[str, Any]) -> str:
    if not safety:
        return "<p class=\"warn\">Missing safety block in payload.</p>"
    lines = []
    for k in ("paper_review_only", "live_permission", "ny_live_enabled", "send_trade_unlock_changed", "execution_paths_changed"):
        if k in safety:
            lines.append(f"<tr><td>{_h(k)}</td><td><code>{_h(safety.get(k))}</code></td></tr>")
    return f"""
<section class="section">
  <h2>Safety flags</h2>
  <table class="safety"><tbody>{"".join(lines)}</tbody></table>
</section>
"""


def build_preview_html(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload.get("summary_cards"), dict) or not isinstance(payload.get("tables"), dict):
        return _render_error_page("Payload must include non-empty structure: summary_cards and tables (object).")
    tables = payload.get("tables") or {}
    required_table_keys = (
        "latest_runs",
        "promotion_candidates",
        "continue_forward",
        "watch_only",
        "demoted_blocked",
        "fail_closed",
        "proxy_research",
    )
    for k in required_table_keys:
        if k not in tables or not isinstance(tables.get(k), list):
            return _render_error_page(f"Missing or invalid tables.{k} (must be a list).")
    safety = payload.get("safety") or {}
    warnings = payload.get("warnings") or []
    style = """
    :root { --bg:#0f1115; --card:#1a1d23; --text:#e8eaed; --muted:#9aa0a6; --accent:#5b8def; --border:#2d3339; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: var(--bg); color: var(--text); }
    .banner { background: linear-gradient(90deg, #1e3a5f, #0f1115); border-bottom: 2px solid var(--accent); padding: 16px 24px; }
    .banner h1 { margin: 0 0 8px 0; font-size: 1.35rem; }
    .banner .sub { color: var(--muted); font-size: 0.9rem; }
    .wrap { max-width: 1400px; margin: 0 auto; padding: 24px; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
    .card .k { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
    .card .v { font-size: 14px; margin-top: 6px; word-break: break-word; }
    .section { margin-bottom: 28px; }
    .section h2 { font-size: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid var(--border); padding: 8px; text-align: left; vertical-align: top; }
    th { background: #141820; position: sticky; top: 0; }
    .empty { color: var(--muted); }
    .warnings { background: #2a2110; border: 1px solid #6b5a2a; padding: 12px; border-radius: 8px; }
    .safety td { padding: 6px 10px; }
    code { font-family: ui-monospace, Consolas, monospace; font-size: 11px; }
    """
    tables_html = "".join(
        [
            _table_section("Latest Runs", list(tables.get("latest_runs") or [])),
            _table_section("Promotion Candidates", list(tables.get("promotion_candidates") or [])),
            _table_section("Continue Forward", list(tables.get("continue_forward") or [])),
            _table_section("Watch Only", list(tables.get("watch_only") or [])),
            _table_section("Demoted / Blocked", list(tables.get("demoted_blocked") or [])),
            _table_section("Fail-Closed / Data-Incomplete", list(tables.get("fail_closed") or [])),
            _table_section("Proxy Research Rows", list(tables.get("proxy_research") or [])),
        ]
    )
    warn_html = ""
    if warnings:
        warn_html = (
            '<section class="section warnings"><h2>Warnings</h2><ul>'
            + "".join(f"<li>{_h(w)}</li>" for w in warnings)
            + "</ul></section>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Phase 8U Stitch Payload Preview</title>
  <style>{style}</style>
</head>
<body>
  <div class="banner">
    <h1>{_h(BANNER_MAIN)}</h1>
    <div class="sub"><strong>{_h(BANNER_NOT_FALLBACK)}</strong> — Data source: <code>latest_stitch_dashboard_payload.json</code> (Phase 8U canonical payload). Not <code>research_dashboard/index.html</code>.</div>
    <div class="sub">generated_at_utc: <code>{_h(payload.get("generated_at_utc"))}</code> · contract_version: <code>{_h(payload.get("contract_version"))}</code></div>
  </div>
  <div class="wrap">
    {_summary_grid(payload)}
    {_safety_block(safety)}
    {warn_html}
    <section class="section"><h2>Calendar budget</h2><pre class="card"><code>{_h(json.dumps(payload.get("calendar_budget") or {}, indent=2))}</code></pre></section>
    <section class="section"><h2>Provider capability</h2><pre class="card"><code>{_h(json.dumps(payload.get("provider_capability") or {}, indent=2))}</code></pre></section>
    {tables_html}
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Phase 8U Stitch dashboard preview from payload JSON.")
    parser.add_argument("--payload", type=Path, default=None, help="Path to latest_stitch_dashboard_payload.json")
    parser.add_argument("--output", type=Path, default=None, help="Output HTML path")
    parser.add_argument("--open-browser", action="store_true", help="Open default browser to file:// output")
    args = parser.parse_args()

    home = Path.home()
    payload_path = args.payload or (home / "fxg-phase8-dashboard" / "latest_stitch_dashboard_payload.json")
    output_path = args.output or (home / "fxg-phase8-dashboard" / "phase8u_stitch_dashboard_preview.html")

    payload_path = payload_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()

    if not payload_path.is_file():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render_error_page(f"Missing payload file: {payload_path}"), encoding="utf-8")
        print(json.dumps({"ok": False, "error": "missing_payload", "path": str(payload_path)}, indent=2))
        if args.open_browser:
            webbrowser.open(output_path.resolve().as_uri())
        return 1

    try:
        payload = _read_payload(payload_path)
    except json.JSONDecodeError as exc:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render_error_page(f"Invalid JSON: {exc}"), encoding="utf-8")
        print(json.dumps({"ok": False, "error": "invalid_json", "path": str(payload_path)}, indent=2))
        if args.open_browser:
            webbrowser.open(output_path.resolve().as_uri())
        return 1

    html_out = build_preview_html(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_out, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "payload_path": str(payload_path),
                "output_path": str(output_path),
                "banner": BANNER_MAIN,
            },
            indent=2,
        )
    )

    if args.open_browser:
        webbrowser.open(output_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
