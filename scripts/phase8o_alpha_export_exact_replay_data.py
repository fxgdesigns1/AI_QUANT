#!/usr/bin/env python3
"""
Phase 8O: ALPHA-side read-only exact replay data export.

Exports OANDA historical mid candles, provider diagnostics, news/calendar rows,
and compact candidate/context artifacts when present. It does not call broker
order or position mutation APIs.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import gzip
import hashlib
import json
import os
import shutil
import socket
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from scripts.local_research.oanda_mid_historical_fetch import (  # noqa: E402
    estimate_gzip_compressed_bytes_heuristic,
    estimate_jsonl_raw_bytes,
    expected_candle_count_full_clock,
    fetch_oanda_mid_candles_range,
    oanda_headers_from_env,
    parse_time_iso_utc,
)
from scripts.local_research.phase8l_news_calendar_fetch import (  # noqa: E402
    DOCUMENTED_PROVIDER_ENV_NAMES,
    FINNHUB_ENV_CANDIDATES,
    NEWSAPI_ENV_CANDIDATES,
    TRADING_ECONOMICS_ENV_CANDIDATES,
    documented_env_presence_map,
    env_presence_map,
    fetch_finnhub_calendar_rows,
    fetch_newsapi_forex_rows,
    fetch_tradingeconomics_calendar_rows,
    resolve_finnhub_key,
    resolve_newsapi_key,
    resolve_trading_economics_key,
)
from scripts.local_research.calendar_budgeted_client import fetch_calendar_with_budget  # noqa: E402
from scripts.local_research.phase8p_replay_snapshot_schema import redact_secrets  # noqa: E402
from scripts.local_research.rapidapi_economic_calendar_client import (  # noqa: E402
    fetch_tradingview_events,
    normalize_rows_for_export,
    resolve_rapidapi_key,
)
from scripts.phase8s_calendar_budget_guard import write_usage_report  # noqa: E402

PHASE = "Phase 8O"
UTC = timezone.utc
CONTROL_PLANE_BASE_URL = "http://127.0.0.1:8787"

CANDIDATE_CONTEXT_FILES = (
    "ARTIFACTS/performance/latest_phase8h_archived_candidate_inventory.json",
    "ARTIFACTS/performance/pair_session_scorecard.json",
    "ARTIFACTS/performance/pair_session_paper_review_log.jsonl",
    "ARTIFACTS/performance/pair_session_candidate_archive_index.json",
)


def utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl_gz(path: Path, rows: Sequence[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".jsonl.gz", dir=str(path.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as gz:
            for row in rows:
                gz.write(json.dumps(row, separators=(",", ":")) + "\n")
        size = int(tmp.stat().st_size)
        tmp.replace(path)
        return size
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def export_candles_single(
    *,
    instrument: str,
    granularity: str,
    days: int,
    output: Path,
    max_export_size_bytes: int,
) -> Dict[str, Any]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    if not os.getenv("OANDA_API_KEY"):
        raise RuntimeError("Missing OANDA_API_KEY in environment")
    _ = oanda_headers_from_env()
    candles = fetch_oanda_mid_candles_range(instrument, granularity.upper(), start, end)
    if not candles:
        raise RuntimeError(f"NO_CANDLES_FETCHED:{instrument}:{granularity}")

    output.parent.mkdir(parents=True, exist_ok=True)
    size = write_jsonl_gz(output, candles)
    if size > max_export_size_bytes:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"EXPORT_SIZE_REFUSED:{instrument}:{granularity}:bytes={size}>{max_export_size_bytes}")

    first = parse_time_iso_utc(candles[0].get("time"))
    last = parse_time_iso_utc(candles[-1].get("time"))
    return {
        "file": output.name,
        "path": str(output),
        "instrument": instrument,
        "granularity": granularity.upper(),
        "candle_count": len(candles),
        "compressed_size_bytes": size,
        "sha256": sha256_file(output),
        "dataset_start_utc": first.isoformat().replace("+00:00", "Z") if first else None,
        "dataset_end_utc": last.isoformat().replace("+00:00", "Z") if last else None,
    }


def dry_run_plan(
    *,
    instruments: Sequence[str],
    granularities: Sequence[str],
    days: int,
    output_dir: Path,
    max_export_size_bytes: int,
) -> Dict[str, Any]:
    combos: List[Dict[str, Any]] = []
    total_est = 0
    for instrument in instruments:
        for granularity in granularities:
            n = expected_candle_count_full_clock(days, granularity)
            raw = estimate_jsonl_raw_bytes(n)
            gz = estimate_gzip_compressed_bytes_heuristic(raw)
            total_est += gz
            combos.append(
                {
                    "instrument": instrument,
                    "granularity": granularity.upper(),
                    "expected_candle_count_approx": n,
                    "estimated_compressed_bytes_heuristic": gz,
                    "output_file": f"phase8o_candles_{instrument}_{granularity.upper()}_{days}d.jsonl.gz",
                }
            )
    total_est += estimate_gzip_compressed_bytes_heuristic(400 * 800)
    return {
        "phase": PHASE,
        "mode": "dry_run_plan",
        "output_dir": str(output_dir),
        "days_requested": days,
        "instruments": list(instruments),
        "granularities": [g.upper() for g in granularities],
        "per_instrument_granularity": combos,
        "estimated_total_compressed_bytes_heuristic": total_est,
        "max_export_size_bytes": max_export_size_bytes,
        "preflight_compressed_estimate_fits": total_est <= max_export_size_bytes,
        "oanda_credentials_from_env": bool(os.getenv("OANDA_API_KEY")),
        "would_refuse_preflight": total_est > max_export_size_bytes,
        "paper_review_only": True,
        "live_permission": False,
    }


def _request_json(url: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    captured_at = utc_now_iso_z()
    try:
        response = requests.get(url, timeout=timeout_s)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "http_status": None,
            "error": f"request_error:{type(exc).__name__}",
            "error_class": type(exc).__name__,
            "captured_at_utc": captured_at,
        }
    out: Dict[str, Any] = {
        "ok": response.status_code == 200,
        "http_status": int(response.status_code),
        "captured_at_utc": captured_at,
    }
    try:
        out["json"] = redact_secrets(response.json())
    except ValueError:
        out["ok"] = False
        out["error"] = "json_decode_error"
        out["error_class"] = "JSONDecodeError"
    return out


def _sanitize_control_plane_probe(
    *,
    status_result: Dict[str, Any],
    provider_result: Dict[str, Any],
    assess_result: Dict[str, Any],
    query_result: Dict[str, Any],
    calendar_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    status_json = status_result.get("json") if isinstance(status_result.get("json"), dict) else {}
    provider_json = provider_result.get("json") if isinstance(provider_result.get("json"), dict) else {}
    assess_json = assess_result.get("json") if isinstance(assess_result.get("json"), dict) else {}
    query_json = query_result.get("json") if isinstance(query_result.get("json"), dict) else {}
    calendar_result = calendar_result or {}
    calendar_json = calendar_result.get("json") if isinstance(calendar_result.get("json"), dict) else {}

    status_data = status_json.get("data") if isinstance(status_json.get("data"), dict) else {}
    provider_map = provider_json.get("providers") if isinstance(provider_json.get("providers"), dict) else {}
    assess_data = assess_json.get("data") if isinstance(assess_json.get("data"), dict) else {}
    query_data = query_json.get("data") if isinstance(query_json.get("data"), dict) else {}
    news_rows = query_data.get("news") if isinstance(query_data.get("news"), list) else []

    providers_used = []
    configured = provider_json.get("providers_configured")
    if isinstance(configured, list):
        providers_used = [str(x) for x in configured]

    return {
        "base_url": CONTROL_PLANE_BASE_URL,
        "status_endpoint_ok": bool(status_result.get("ok") and status_data.get("ok")),
        "status_http_status": status_result.get("http_status"),
        "status_providers": status_data.get("providers") if isinstance(status_data.get("providers"), dict) else {},
        "provider_status_endpoint_ok": bool(provider_result.get("ok") and provider_json.get("ok")),
        "provider_status_http_status": provider_result.get("http_status"),
        "provider_status": provider_map,
        "providers_used": providers_used,
        "configured_count": provider_json.get("configured_count"),
        "provider_status_source_mode": provider_json.get("source_mode"),
        "assess_endpoint_ok": bool(assess_result.get("ok") and assess_data.get("ok")),
        "assess_http_status": assess_result.get("http_status"),
        "assess_news_count": int(assess_data.get("news_count") or 0),
        "query_endpoint_ok": bool(query_result.get("ok") and query_data.get("ok")),
        "query_http_status": query_result.get("http_status"),
        "source_mode": query_data.get("source_mode"),
        "news_count": len(news_rows),
        "calendar_endpoint_ok": bool(calendar_result.get("ok")),
        "calendar_http_status": calendar_result.get("http_status"),
        "phase8p_forward_replay_context_snapshots": {
            "news_status_snapshot": redact_secrets(status_result),
            "provider_status_snapshot": redact_secrets(provider_result),
            "news_assess_snapshot": redact_secrets(assess_result),
            "news_snapshot": redact_secrets(query_result),
            "calendar_snapshot": redact_secrets(calendar_result),
        },
    }


def control_plane_news_probe() -> Dict[str, Any]:
    encoded_query = "forex%20OR%20USD%20OR%20GBP%20OR%20EUR%20OR%20gold"
    return _sanitize_control_plane_probe(
        status_result=_request_json(f"{CONTROL_PLANE_BASE_URL}/api/news/status"),
        provider_result=_request_json(f"{CONTROL_PLANE_BASE_URL}/api/news/provider_status"),
        assess_result=_request_json(f"{CONTROL_PLANE_BASE_URL}/api/news/assess?query={encoded_query}"),
        query_result=_request_json(
            f"{CONTROL_PLANE_BASE_URL}/api/news?query={encoded_query}&threshold=medium&max_items=10"
        ),
        calendar_result=_request_json(f"{CONTROL_PLANE_BASE_URL}/api/economic_calendar"),
    )


def provider_diagnostics(
    *,
    start_day: str,
    end_day: str,
    max_rows: int,
    repo_root: Path,
    probe_control_plane: bool = True,
    rapidapi_countries: str = "US,GB,EU",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    news_key, news_env = resolve_newsapi_key()
    te_key, te_env = resolve_trading_economics_key()
    fin_key, fin_env = resolve_finnhub_key()
    rap_key, rap_env = resolve_rapidapi_key()

    news_rows, news_meta = fetch_newsapi_forex_rows(
        api_key=news_key,
        from_day=start_day,
        to_day=end_day,
        max_items=max_rows,
    )

    session_remaining = [8]

    def inner_te() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return fetch_tradingeconomics_calendar_rows(
            api_key=te_key,
            d1=start_day,
            d2=end_day,
            max_rows=max_rows,
        )

    te_rows, te_bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="tradingeconomics_calendar",
        date_from=start_day,
        date_to=end_day,
        countries="",
        session_remaining_paid_calls=session_remaining,
        inner=inner_te,
    )
    te_meta = te_bmeta.get("inner") or {}

    def inner_fin() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return fetch_finnhub_calendar_rows(
            api_key=fin_key,
            d1=start_day,
            d2=end_day,
            max_rows=max_rows,
        )

    fin_rows, fin_bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="finnhub_economic_calendar",
        date_from=start_day,
        date_to=end_day,
        countries="",
        session_remaining_paid_calls=session_remaining,
        inner=inner_fin,
    )
    fin_meta = fin_bmeta.get("inner") or {}

    def inner_rap() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        raw, meta = fetch_tradingview_events(
            countries=rapidapi_countries,
            date_from=start_day,
            date_to=end_day,
        )
        norm = normalize_rows_for_export(raw, max_rows=max_rows)
        return norm, meta

    rap_rows, rap_bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="rapidapi_economic_calendar",
        date_from=start_day,
        date_to=end_day,
        countries=rapidapi_countries,
        session_remaining_paid_calls=session_remaining,
        inner=inner_rap,
    )
    rap_meta = rap_bmeta.get("inner") or {}

    calendar_rows = te_rows + fin_rows + rap_rows
    statuses = {
        "NewsAPI": {
            "selected_env_name": news_env,
            "env_present": bool(news_key),
            "http_status": news_meta.get("http_status"),
            "rows_returned": len(news_rows),
            "failure_reason": news_meta.get("failure_reason"),
        },
        "TradingEconomics": {
            "selected_env_name": te_env,
            "env_present": bool(te_key),
            "http_status": te_meta.get("http_status"),
            "rows_returned": len(te_rows),
            "failure_reason": te_meta.get("failure_reason"),
            "calendar_budget_cache_hit": bool(te_bmeta.get("cache_hit")),
            "calendar_budget_blocked": bool(te_bmeta.get("budget_blocked")),
        },
        "Finnhub": {
            "selected_env_name": fin_env,
            "env_present": bool(fin_key),
            "http_status": fin_meta.get("http_status"),
            "rows_returned": len(fin_rows),
            "failure_reason": fin_meta.get("failure_reason"),
            "calendar_budget_cache_hit": bool(fin_bmeta.get("cache_hit")),
            "calendar_budget_blocked": bool(fin_bmeta.get("budget_blocked")),
        },
        "RapidAPI_Economic_Calendar": {
            "selected_env_name": rap_env,
            "env_present": bool(rap_key),
            "http_status": rap_meta.get("http_status"),
            "rows_returned": len(rap_rows),
            "failure_reason": rap_meta.get("failure_reason"),
            "calendar_budget_cache_hit": bool(rap_bmeta.get("cache_hit")),
            "calendar_budget_blocked": bool(rap_bmeta.get("budget_blocked")),
        },
    }
    write_usage_report(repo_root)
    control_probe = control_plane_news_probe() if probe_control_plane else {}
    current_news_available = bool(
        control_probe.get("status_endpoint_ok")
        and control_probe.get("provider_status_endpoint_ok")
        and (
            int(control_probe.get("news_count") or 0) > 0
            or int(control_probe.get("assess_news_count") or 0) > 0
        )
    )

    unavailable = []
    if not news_rows:
        if current_news_available:
            unavailable.append("news_historical_reconstruction_unavailable_current_control_plane_available")
        else:
            unavailable.append(statuses["NewsAPI"].get("failure_reason") or "news_rows_empty")
    if not calendar_rows:
        unavailable.append("calendar_rows_empty")

    historical_supported = bool(news_rows)
    news_unavailable_classification = None
    if current_news_available and not historical_supported:
        news_unavailable_classification = "PROVIDER_CURRENT_NEWS_AVAILABLE_HISTORICAL_RECONSTRUCTION_UNAVAILABLE"

    diagnostics = {
        "providers_checked": ["NewsAPI", "TradingEconomics", "Finnhub", "RapidAPI_Economic_Calendar"],
        "documented_provider_env_names": list(DOCUMENTED_PROVIDER_ENV_NAMES),
        "documented_provider_env_presence_without_values": documented_env_presence_map(),
        "provider_env_presence_without_values": {
            "NewsAPI": env_presence_map(NEWSAPI_ENV_CANDIDATES),
            "TradingEconomics": env_presence_map(TRADING_ECONOMICS_ENV_CANDIDATES),
            "Finnhub": env_presence_map(FINNHUB_ENV_CANDIDATES),
        },
        "provider_statuses": statuses,
        "control_plane_news_probe": control_probe,
        "news_current_available_via_control_plane": current_news_available,
        "historical_news_reconstruction_supported": historical_supported,
        "news_unavailable_classification": news_unavailable_classification,
        "news_rows_count": len(news_rows),
        "calendar_rows_count": len(calendar_rows),
        "news_reconstruction_available": bool(news_rows),
        "calendar_reconstruction_available": bool(calendar_rows),
        "unavailable_reasons": unavailable,
    }
    return news_rows, calendar_rows, diagnostics


def copy_candidate_context(repo_root: Path, output_dir: Path, max_bytes_each: int) -> List[Dict[str, Any]]:
    copied: List[Dict[str, Any]] = []
    context_dir = output_dir / "candidate_context"
    context_dir.mkdir(parents=True, exist_ok=True)
    for rel_path in CANDIDATE_CONTEXT_FILES:
        src = repo_root / rel_path
        rec: Dict[str, Any] = {"source_path": rel_path, "exists": src.is_file(), "copied": False}
        if src.is_file():
            size = int(src.stat().st_size)
            rec["source_size_bytes"] = size
            if size <= max_bytes_each:
                dst = context_dir / src.name
                shutil.copy2(src, dst)
                rec.update({"copied": True, "file": str(dst), "sha256": sha256_file(dst)})
            else:
                rec["skip_reason"] = f"source_too_large:{size}>{max_bytes_each}"
        copied.append(rec)
    return copied


def run_export(
    *,
    repo_root: Path,
    days: int,
    instruments: Sequence[str],
    granularities: Sequence[str],
    output_dir: Path,
    max_export_size_bytes: int,
    max_context_rows: int,
    dry_run: bool,
    write_export: bool,
) -> Dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    if dry_run:
        return {"dry_run_plan": dry_run_plan(
            instruments=instruments,
            granularities=granularities,
            days=days,
            output_dir=output_dir,
            max_export_size_bytes=max_export_size_bytes,
        )}
    if not write_export:
        return {"ok": False, "error": "use --write-export or --dry-run-plan"}

    output_dir.mkdir(parents=True, exist_ok=True)
    candle_exports: List[Dict[str, Any]] = []
    for instrument in instruments:
        for granularity in granularities:
            candle_exports.append(
                export_candles_single(
                    instrument=instrument,
                    granularity=granularity,
                    days=days,
                    output=output_dir / f"phase8o_candles_{instrument}_{granularity.upper()}_{days}d.jsonl.gz",
                    max_export_size_bytes=max_export_size_bytes,
                )
            )

    starts = [e.get("dataset_start_utc") for e in candle_exports if e.get("dataset_start_utc")]
    ends = [e.get("dataset_end_utc") for e in candle_exports if e.get("dataset_end_utc")]
    start_day = min(starts)[:10] if starts else (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    end_day = max(ends)[:10] if ends else datetime.now(UTC).date().isoformat()
    news_rows, calendar_rows, diagnostics = provider_diagnostics(
        start_day=start_day,
        end_day=end_day,
        max_rows=max_context_rows,
        repo_root=repo_root,
    )

    news_file = output_dir / f"phase8o_news_context_{days}d.jsonl.gz"
    calendar_file = output_dir / f"phase8o_calendar_context_{days}d.jsonl.gz"
    news_size = write_jsonl_gz(news_file, news_rows)
    cal_size = write_jsonl_gz(calendar_file, calendar_rows)
    candidate_context = copy_candidate_context(repo_root, output_dir, max_bytes_each=5 * 1024 * 1024)

    manifest: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "ALPHA_EXACT_REPLAY_EXPORT_READ_ONLY",
        "hostname": socket.gethostname(),
        "repo_root": str(repo_root),
        "days_requested": days,
        "instruments": list(instruments),
        "granularities": [g.upper() for g in granularities],
        "dataset_start_utc": min(starts) if starts else None,
        "dataset_end_utc": max(ends) if ends else None,
        "candle_exports": candle_exports,
        "news_file": news_file.name,
        "calendar_file": calendar_file.name,
        "news_file_size_bytes": news_size,
        "calendar_file_size_bytes": cal_size,
        "candidate_context": candidate_context,
        **diagnostics,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    write_json(output_dir / "phase8o_alpha_export_manifest.json", manifest)

    checksum_names = [Path(e["path"]).name for e in candle_exports] + [
        news_file.name,
        calendar_file.name,
        "phase8o_alpha_export_manifest.json",
    ]
    lines = []
    for name in sorted(checksum_names):
        path = output_dir / name
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {name}")
    (output_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "manifest": str(output_dir / "phase8o_alpha_export_manifest.json"), "summary": manifest}


def split_csv(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8O ALPHA read-only exact replay export.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--instruments", default="EUR_USD")
    parser.add_argument("--granularities", default="M15,M5")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-export-size-bytes", type=int, default=250 * 1024 * 1024)
    parser.add_argument("--max-context-rows", type=int, default=1000)
    parser.add_argument("--dry-run-plan", action="store_true")
    parser.add_argument("--write-export", action="store_true")
    args = parser.parse_args()

    try:
        result = run_export(
            repo_root=args.repo_root.expanduser().resolve(),
            days=int(args.days),
            instruments=split_csv(args.instruments),
            granularities=split_csv(args.granularities),
            output_dir=args.output_dir,
            max_export_size_bytes=int(args.max_export_size_bytes),
            max_context_rows=int(args.max_context_rows),
            dry_run=bool(args.dry_run_plan),
            write_export=bool(args.write_export),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", True) else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
