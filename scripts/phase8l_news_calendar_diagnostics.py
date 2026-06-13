#!/usr/bin/env python3
"""
Phase 8L: read-only news/calendar provider diagnostics (env presence + HTTP + row counts).

Runs on ALPHA with `source /etc/ai-quant/.env` — never prints secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.phase8l_news_calendar_fetch import (  # noqa: E402
    DOCUMENTED_PROVIDER_ENV_NAMES,
    TRADING_ECONOMICS_ENV_CANDIDATES,
    documented_env_presence_map,
    env_presence_map,
    fetch_finnhub_calendar_rows,
    fetch_newsapi_forex_rows,
    fetch_tradingeconomics_calendar_rows,
    resolve_finnhub_key,
    resolve_newsapi_key,
    resolve_trading_economics_key,
    NEWSAPI_ENV_CANDIDATES,
    FINNHUB_ENV_CANDIDATES,
)
from scripts.phase8o_alpha_export_exact_replay_data import control_plane_news_probe  # noqa: E402

UTC = timezone.utc
PHASE = "Phase 8L-NEWS-CALENDAR-DIAGNOSTICS"

# Extra env names to report presence only (exporter may not consume).
TE_EXTRA_ENV_NAMES = ("TRADING_ECONOMICS_CLIENT",)


def _utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso_day(s: str) -> str:
    """Accept YYYY-MM-DD or full ISO Z; return YYYY-MM-DD for provider query params."""
    s = (s or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    raise ValueError(f"invalid_day:{s}")


def _classify_provider(
    *,
    env_present: bool,
    selected_env_name: Optional[str],
    http_status: Optional[int],
    rows: int,
    parser_ok: bool,
    api_error: Any,
) -> str:
    if not env_present:
        return "PROVIDER_KEYS_MISSING"
    if http_status in (401, 403):
        return "PROVIDER_AUTH_FAILED"
    if http_status == 429:
        return "PROVIDER_RATE_LIMITED"
    if not parser_ok and http_status == 200:
        return "PARSER_BUG"
    if http_status == 200 and rows == 0:
        if isinstance(api_error, dict):
            code = str(api_error.get("code") or api_error.get("status") or "").lower()
            msg = str(api_error.get("message") or "").lower()
            if "daterange" in code or "too old" in msg or "upgrade" in msg or "paid" in msg:
                return "PROVIDER_DATE_RANGE_UNSUPPORTED"
        return "PROVIDER_RETURNED_EMPTY"
    if http_status is not None and http_status != 200:
        return "PROVIDER_AUTH_FAILED" if http_status in (401, 403) else "MIXED_PROVIDER_STATUS"
    if rows > 0:
        return "NEWS_CALENDAR_AVAILABLE"
    return "PROVIDER_KEYS_MISSING"


def _date_range_supported_flag(
    *,
    http_status: Optional[int],
    rows: int,
    api_error: Any,
) -> bool:
    if http_status != 200:
        return False
    if rows > 0:
        return True
    if isinstance(api_error, dict):
        msg = str(api_error.get("message") or "")
        if "only" in msg.lower() and "month" in msg.lower():
            return False
    return http_status == 200


def _rate_limited(http_status: Optional[int]) -> bool:
    return http_status == 429


def _auth_failed(http_status: Optional[int]) -> bool:
    return http_status in (401, 403)


def _failure_reason(
    *,
    env_present: bool,
    http_status: Optional[int],
    rows: int,
    parser_ok: bool,
    meta: Dict[str, Any],
) -> str:
    if not env_present:
        return "no_env_key_in_expected_names"
    if meta.get("failure_reason"):
        return str(meta["failure_reason"])
    if http_status not in (200, None) and http_status is not None:
        return f"http_status_{http_status}"
    if http_status == 200 and not parser_ok:
        return "parser_failed"
    if http_status == 200 and parser_ok and rows == 0:
        err = meta.get("api_error")
        if isinstance(err, dict) and err.get("message"):
            return f"provider_message:{err.get('message')}"
        return "zero_rows_valid_json"
    return "ok"


def run_diagnostics(
    *,
    instrument: str,
    days: int,
    start_utc: str,
    end_utc: str,
    max_rows: int,
    repo_path: str,
) -> Dict[str, Any]:
    d1 = _parse_iso_day(start_utc)
    d2 = _parse_iso_day(end_utc)

    news_key, news_name = resolve_newsapi_key()
    te_key, te_name = resolve_trading_economics_key()
    fin_key, fin_name = resolve_finnhub_key()

    news_rows, news_meta = fetch_newsapi_forex_rows(
        api_key=news_key,
        from_day=d1,
        to_day=d2,
        max_items=max_rows,
    )
    te_rows, te_meta = fetch_tradingeconomics_calendar_rows(
        api_key=te_key,
        d1=d1,
        d2=d2,
        max_rows=max_rows,
    )
    fin_rows, fin_meta = fetch_finnhub_calendar_rows(
        api_key=fin_key,
        d1=d1,
        d2=d2,
        max_rows=max_rows,
    )

    news_env = env_presence_map(NEWSAPI_ENV_CANDIDATES)
    te_env = env_presence_map(tuple(TRADING_ECONOMICS_ENV_CANDIDATES) + TE_EXTRA_ENV_NAMES)
    fin_env = env_presence_map(FINNHUB_ENV_CANDIDATES)

    def pack(
        label: str,
        *,
        env_map: Dict[str, bool],
        selected: Optional[str],
        key_present: bool,
        rows: List[Dict[str, Any]],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        st = meta.get("http_status")
        api_err = meta.get("api_error")
        return {
            "provider": label,
            "env_present": key_present,
            "env_presence_by_name": env_map,
            "selected_env_name": selected,
            "http_status": st,
            "rate_limited": _rate_limited(st if isinstance(st, int) else None),
            "auth_failed": _auth_failed(st if isinstance(st, int) else None),
            "rows_returned": len(rows),
            "date_range_supported": _date_range_supported_flag(
                http_status=st if isinstance(st, int) else None,
                rows=len(rows),
                api_error=api_err,
            ),
            "parser_ok": bool(meta.get("parser_ok")),
            "failure_reason": _failure_reason(
                env_present=key_present,
                http_status=st if isinstance(st, int) else None,
                rows=len(rows),
                parser_ok=bool(meta.get("parser_ok")),
                meta=meta,
            ),
            "api_error_redacted_shape": type(api_err).__name__
            if api_err is not None
            else None,
        }

    news_pr = pack(
        "NewsAPI",
        env_map=news_env,
        selected=news_name,
        key_present=bool(news_key),
        rows=news_rows,
        meta=news_meta,
    )
    te_pr = pack(
        "TradingEconomics",
        env_map=te_env,
        selected=te_name,
        key_present=bool(te_key),
        rows=te_rows,
        meta=te_meta,
    )
    fin_pr = pack(
        "Finnhub",
        env_map=fin_env,
        selected=fin_name,
        key_present=bool(fin_key),
        rows=fin_rows,
        meta=fin_meta,
    )
    control_probe = control_plane_news_probe()
    current_news_available = bool(
        control_probe.get("status_endpoint_ok")
        and control_probe.get("provider_status_endpoint_ok")
        and (
            int(control_probe.get("news_count") or 0) > 0
            or int(control_probe.get("assess_news_count") or 0) > 0
        )
    )

    calendar_rows_total = len(te_rows) + len(fin_rows)
    news_class = _classify_provider(
        env_present=news_pr["env_present"],
        selected_env_name=news_pr["selected_env_name"],
        http_status=news_pr["http_status"],
        rows=news_pr["rows_returned"],
        parser_ok=news_pr["parser_ok"],
        api_error=news_meta.get("api_error"),
    )
    cal_class_te = _classify_provider(
        env_present=te_pr["env_present"],
        selected_env_name=te_pr["selected_env_name"],
        http_status=te_pr["http_status"],
        rows=te_pr["rows_returned"],
        parser_ok=te_pr["parser_ok"],
        api_error=te_meta.get("api_error"),
    )
    cal_class_fin = _classify_provider(
        env_present=fin_pr["env_present"],
        selected_env_name=fin_pr["selected_env_name"],
        http_status=fin_pr["http_status"],
        rows=fin_pr["rows_returned"],
        parser_ok=fin_pr["parser_ok"],
        api_error=fin_meta.get("api_error"),
    )

    if calendar_rows_total > 0:
        calendar_aggregate = "NEWS_CALENDAR_AVAILABLE"
    elif cal_class_te == "PROVIDER_KEYS_MISSING" and cal_class_fin == "PROVIDER_KEYS_MISSING":
        calendar_aggregate = "PROVIDER_KEYS_MISSING"
    elif cal_class_te in ("PROVIDER_AUTH_FAILED", "PROVIDER_RATE_LIMITED") or cal_class_fin in (
        "PROVIDER_AUTH_FAILED",
        "PROVIDER_RATE_LIMITED",
    ):
        calendar_aggregate = (
            "PROVIDER_AUTH_FAILED"
            if "PROVIDER_AUTH_FAILED" in (cal_class_te, cal_class_fin)
            else "PROVIDER_RATE_LIMITED"
        )
    else:
        calendar_aggregate = "MIXED_PROVIDER_STATUS"

    manifest_logic = (
        "Phase 8L manifest sets news_reconstruction_available=true iff news row list non-empty "
        "after fetch; calendar_reconstruction_available=true iff TE or Finnhub yields at least one row."
    )

    news_rc = news_class
    if current_news_available and news_pr["rows_returned"] == 0:
        news_rc = "PROVIDER_CURRENT_NEWS_AVAILABLE_HISTORICAL_RECONSTRUCTION_UNAVAILABLE"
    cal_rc = calendar_aggregate

    fix_required = news_pr["rows_returned"] == 0 or calendar_rows_total == 0
    fix_type: Optional[str] = None
    recommended_patch: Optional[str] = None
    if news_rc == "PROVIDER_KEYS_MISSING" or cal_rc == "PROVIDER_KEYS_MISSING":
        fix_type = "env_mapping_or_provision_keys"
        recommended_patch = (
            "Ensure ALPHA /etc/ai-quant/.env defines at least one name per provider from the "
            "expected list; Phase 8L exporter resolves aliases via phase8l_news_calendar_fetch."
        )
    elif news_rc in ("PROVIDER_DATE_RANGE_UNSUPPORTED", "PROVIDER_RETURNED_EMPTY"):
        fix_type = "provider_plan_or_date_window"
        recommended_patch = "Adjust NewsAPI plan or shrink date window; do not fabricate rows."
    elif news_rc == "PARSER_BUG" or cal_class_te == "PARSER_BUG" or cal_class_fin == "PARSER_BUG":
        fix_type = "parser"
        recommended_patch = "Patch parser against provider payload; add regression fixture."

    root_cause = (
        f"news:{news_rc}; calendar:{cal_rc} "
        f"(TE rows={te_pr['rows_returned']}, Finnhub rows={fin_pr['rows_returned']})"
    )

    classification = (
        "NEWS_CALENDAR_AVAILABLE"
        if news_pr["rows_returned"] > 0 and calendar_rows_total > 0
        else "MIXED_PROVIDER_STATUS"
        if news_pr["rows_returned"] > 0 or calendar_rows_total > 0
        else news_rc
        if news_rc != "PROVIDER_KEYS_MISSING"
        else cal_rc
        if cal_rc != "PROVIDER_KEYS_MISSING"
        else "PROVIDER_KEYS_MISSING"
    )

    out: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso_z(),
        "phase": PHASE,
        "classification": classification,
        "host": socket.gethostname(),
        "repo_path": repo_path,
        "instrument": instrument,
        "days_requested": days,
        "date_window_start_utc": start_utc,
        "date_window_end_utc": end_utc,
        "provider_results": [news_pr, te_pr, fin_pr],
        "documented_provider_env_names": list(DOCUMENTED_PROVIDER_ENV_NAMES),
        "documented_provider_env_presence_without_values": documented_env_presence_map(),
        "env_presence_summary": {
            "NewsAPI": news_env,
            "TradingEconomics": te_env,
            "Finnhub": fin_env,
        },
        "control_plane_news_probe": control_probe,
        "news_current_available_via_control_plane": current_news_available,
        "historical_news_reconstruction_supported": bool(news_pr["rows_returned"]),
        "http_status_summary": {
            "NewsAPI": news_pr["http_status"],
            "TradingEconomics_te": te_pr["http_status"],
            "Finnhub_calendar": fin_pr["http_status"],
        },
        "rows_by_provider": {
            "NewsAPI": news_pr["rows_returned"],
            "TradingEconomics": te_pr["rows_returned"],
            "Finnhub_calendar": fin_pr["rows_returned"],
            "calendar_combined": calendar_rows_total,
        },
        "parser_failures": [
            x["provider"]
            for x in (news_pr, te_pr, fin_pr)
            if x["env_present"] and x["http_status"] == 200 and not x["parser_ok"]
        ],
        "filtering_failures": [],
        "manifest_logic_check": manifest_logic,
        "news_root_cause": f"{news_rc}:{news_pr['failure_reason']}",
        "calendar_root_cause": (
            f"{cal_rc}:TE={te_pr['rows_returned']}:{te_pr['failure_reason']};"
            f"FH={fin_pr['rows_returned']}:{fin_pr['failure_reason']}"
        ),
        "news_root_cause_classification": news_rc,
        "calendar_root_cause_classification": cal_rc,
        "root_cause": root_cause,
        "fix_required": fix_required,
        "fix_applied": None,
        "fix_type": fix_type,
        "recommended_patch": recommended_patch,
        "safe_to_rerun_phase8l": True,
        "secret_values_printed": False,
        "order_or_execution_apis_called": False,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    return out


def _write_artifact(payload: Dict[str, Any], perf_dir: Path) -> Path:
    perf_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    p = perf_dir / f"phase8l_news_calendar_diagnostics_{stamp}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = perf_dir / "latest_phase8l_news_calendar_diagnostics.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_phase8o = perf_dir / "latest_phase8o_news_provider_diagnostics.json"
    latest_phase8o.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8L news/calendar provider diagnostics.")
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--start-utc", type=str, required=True)
    parser.add_argument("--end-utc", type=str, required=True)
    parser.add_argument("--max-rows", type=int, default=100)
    parser.add_argument("--write-artifact", action="store_true")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("/opt/ai-quant/ARTIFACTS/performance"),
    )
    parser.add_argument("--repo-path", type=str, default="/opt/ai-quant")
    args = parser.parse_args()

    payload = run_diagnostics(
        instrument=str(args.instrument),
        days=int(args.days),
        start_utc=str(args.start_utc),
        end_utc=str(args.end_utc),
        max_rows=int(args.max_rows),
        repo_path=str(args.repo_path),
    )
    if args.write_artifact:
        p = _write_artifact(payload, args.artifacts_dir.expanduser().resolve())
        payload["artifact_path"] = str(p)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
