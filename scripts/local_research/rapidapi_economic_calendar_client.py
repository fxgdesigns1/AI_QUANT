"""
RapidAPI Economic Events Calendar (TradingView-shaped payload).

Read-only HTTP. Keys only from os.environ — never log values.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

DEFAULT_HOST = "economic-events-calendar.p.rapidapi.com"
DEFAULT_PATH = "/economic-events/tradingview"

RAPIDAPI_KEY_ENV: Sequence[str] = (
    "RAPIDAPI_KEY",
    "RAPIDAPI_API_KEY",
    "RAPIDAPI_ECONOMIC_CALENDAR_KEY",
    "ECONOMIC_EVENTS_CALENDAR_RAPIDAPI_KEY",
)


def resolve_rapidapi_key() -> Tuple[str, Optional[str]]:
    for name in RAPIDAPI_KEY_ENV:
        v = (os.getenv(name) or "").strip()
        if v:
            return v, name
    return "", None


def resolve_rapidapi_host() -> str:
    return (os.getenv("RAPIDAPI_ECONOMIC_CALENDAR_HOST") or DEFAULT_HOST).strip()


def parse_tradingview_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("result", "data", "events", "economicEvents"):
        inner = data.get(key)
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    return []


def fetch_tradingview_events(
    *,
    countries: str,
    date_from: str,
    date_to: str,
    timeout_s: float = 20.0,
    api_key: Optional[str] = None,
    host: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta: Dict[str, Any] = {
        "http_status": None,
        "parser_ok": False,
        "provider": "rapidapi_economic_calendar",
        "failure_reason": None,
        "selected_env_name": None,
    }
    key = (api_key or "").strip() or resolve_rapidapi_key()[0]
    meta["selected_env_name"] = resolve_rapidapi_key()[1] if not api_key else None
    if not key:
        meta["failure_reason"] = "missing_api_key"
        return [], meta
    h = (host or resolve_rapidapi_host()).strip()
    url = f"https://{h.rstrip('/')}{DEFAULT_PATH}"
    try:
        r = requests.get(
            url,
            headers={
                "X-RapidAPI-Key": key,
                "X-RapidAPI-Host": h,
            },
            params={
                "countries": countries,
                "from": date_from,
                "to": date_to,
            },
            timeout=timeout_s,
        )
    except requests.RequestException as e:
        meta["failure_reason"] = f"request_error:{type(e).__name__}"
        return [], meta
    meta["http_status"] = int(r.status_code)
    if r.status_code != 200:
        meta["failure_reason"] = f"http_{r.status_code}"
        try:
            meta["api_error_shape"] = type(r.json()).__name__
        except Exception:
            meta["api_error_shape"] = "non_json_body"
        return [], meta
    try:
        body = r.json()
    except ValueError:
        meta["failure_reason"] = "json_decode_error"
        return [], meta
    rows = parse_tradingview_payload(body)
    meta["parser_ok"] = True
    meta["failure_reason"] = "ok" if rows else "empty_results"
    norm: List[Dict[str, Any]] = []
    for e in rows[:500]:
        norm.append(
            {
                "source": "rapidapi_economic_calendar",
                "raw": {k: e.get(k) for k in list(e.keys())[:24]},
            }
        )
    return norm, meta


def normalize_rows_for_export(rows: List[Dict[str, Any]], *, max_rows: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows[:max_rows]:
        raw = r.get("raw") if isinstance(r.get("raw"), dict) else r
        if not isinstance(raw, dict):
            continue
        out.append(
            {
                "source": "rapidapi_economic_calendar",
                "country": raw.get("country") or raw.get("Country"),
                "event": raw.get("event") or raw.get("Event") or raw.get("title"),
                "date": raw.get("date") or raw.get("Date"),
            }
        )
    return out
