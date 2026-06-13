"""
Phase 8L: shared read-only news/calendar HTTP helpers for ALPHA export and diagnostics.

No broker or order APIs. Credentials only from os.environ; never log key values.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

import requests

# Documented ALPHA provider env names from /etc/ai-quant/.env. Presence is reported
# only as booleans; values must never be emitted in diagnostics or manifests.
DOCUMENTED_PROVIDER_ENV_NAMES: Sequence[str] = (
    "FINNHUB_API_KEYS",
    "FINNHUB_API_KEY",
    "POLYGON_API_KEYS",
    "MARKETAUX_API_KEYS",
    "NEWSAPI_API_KEYS",
    "NEWSAPI_API_KEY",
    "ALPHAVANTAGE_API_KEYS",
    "FRED_API_KEYS",
    "FMP_API_KEYS",
    "TRADINGECONOMICS_API_KEYS",
)

# Priority order: first non-empty wins (must stay aligned with diagnostics expected names).
NEWSAPI_ENV_CANDIDATES: Sequence[str] = (
    "NEWSAPI_API_KEYS",
    "NEWSAPI_API_KEY",
    "NEWSAPI_KEY",
    "NEWS_API_KEY",
)

TRADING_ECONOMICS_ENV_CANDIDATES: Sequence[str] = (
    "TRADINGECONOMICS_API_KEYS",
    "TRADINGECONOMICS_API_KEY",
    "TRADINGECONOMICS_KEY",
    "TRADING_ECONOMICS_KEY",
    "TE_API_KEY",
)

FINNHUB_ENV_CANDIDATES: Sequence[str] = (
    "FINNHUB_API_KEYS",
    "FINNHUB_API_KEY",
    "FINNHUB_KEY",
)


def _dedupe_preserve(seq: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


NEWSAPI_ENV_CANDIDATES = _dedupe_preserve(NEWSAPI_ENV_CANDIDATES)
TRADING_ECONOMICS_ENV_CANDIDATES = _dedupe_preserve(TRADING_ECONOMICS_ENV_CANDIDATES)
FINNHUB_ENV_CANDIDATES = _dedupe_preserve(FINNHUB_ENV_CANDIDATES)


def env_presence_map(names: Sequence[str]) -> Dict[str, bool]:
    return {n: bool((os.getenv(n) or "").strip()) for n in names}


def documented_env_presence_map() -> Dict[str, bool]:
    return env_presence_map(DOCUMENTED_PROVIDER_ENV_NAMES)


def _first_env_value(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        return ""
    if name.endswith("_API_KEYS"):
        return value.split(",", 1)[0].strip()
    return value


def _resolve_first_env_key(names: Sequence[str]) -> Tuple[str, Optional[str]]:
    for name in names:
        value = _first_env_value(name)
        if value:
            return value, name
    return "", None


def resolve_newsapi_key() -> Tuple[str, Optional[str]]:
    return _resolve_first_env_key(NEWSAPI_ENV_CANDIDATES)


def resolve_trading_economics_key() -> Tuple[str, Optional[str]]:
    return _resolve_first_env_key(TRADING_ECONOMICS_ENV_CANDIDATES)


def resolve_finnhub_key() -> Tuple[str, Optional[str]]:
    return _resolve_first_env_key(FINNHUB_ENV_CANDIDATES)


def fetch_tradingeconomics_calendar_rows(
    *,
    api_key: str,
    d1: str,
    d2: str,
    max_rows: int,
    timeout_s: float = 15.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta: Dict[str, Any] = {
        "http_status": None,
        "parser_ok": False,
        "api_error": None,
    }
    rows: List[Dict[str, Any]] = []
    if not api_key:
        meta["failure_reason"] = "missing_api_key"
        return rows, meta
    url = f"https://api.tradingeconomics.com/calendar?d1={d1}&d2={d2}&format=json&c={api_key}"
    try:
        r = requests.get(url, timeout=timeout_s)
    except requests.RequestException as e:
        meta["failure_reason"] = f"request_error:{type(e).__name__}"
        return rows, meta
    meta["http_status"] = int(r.status_code)
    if r.status_code != 200:
        meta["failure_reason"] = f"http_{r.status_code}"
        try:
            meta["api_error"] = r.json()
        except Exception:
            meta["api_error"] = (r.text or "")[:240]
        return rows, meta
    try:
        data = r.json()
    except ValueError:
        meta["failure_reason"] = "json_decode_error"
        return rows, meta
    if not isinstance(data, list):
        meta["failure_reason"] = "unexpected_json_shape"
        return rows, meta
    meta["parser_ok"] = True
    for e in data[: max_rows * 2]:
        if not isinstance(e, dict):
            continue
        rows.append(
            {
                "source": "tradingeconomics",
                "date_utc": e.get("Date"),
                "country": e.get("Country"),
                "event": e.get("Event"),
                "currency": e.get("Currency"),
                "importance": (e.get("Importance") or "").lower(),
                "forecast": e.get("Forecast"),
                "actual": e.get("Actual"),
            }
        )
        if len(rows) >= max_rows:
            break
    return rows, meta


def fetch_finnhub_calendar_rows(
    *,
    api_key: str,
    d1: str,
    d2: str,
    max_rows: int,
    timeout_s: float = 15.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta: Dict[str, Any] = {"http_status": None, "parser_ok": False, "api_error": None}
    rows: List[Dict[str, Any]] = []
    if not api_key:
        meta["failure_reason"] = "missing_api_key"
        return rows, meta
    url = f"https://finnhub.io/api/v1/calendar/economic?from={d1}&to={d2}&token={api_key}"
    try:
        r = requests.get(url, timeout=timeout_s)
    except requests.RequestException as e:
        meta["failure_reason"] = f"request_error:{type(e).__name__}"
        return rows, meta
    meta["http_status"] = int(r.status_code)
    if r.status_code != 200:
        meta["failure_reason"] = f"http_{r.status_code}"
        try:
            meta["api_error"] = r.json()
        except Exception:
            meta["api_error"] = (r.text or "")[:240]
        return rows, meta
    try:
        data = r.json() or {}
    except ValueError:
        meta["failure_reason"] = "json_decode_error"
        return rows, meta
    cal = data.get("economicCalendar") or []
    if not isinstance(cal, list):
        meta["failure_reason"] = "unexpected_json_shape"
        return rows, meta
    meta["parser_ok"] = True
    for e in cal:
        if not isinstance(e, dict):
            continue
        rows.append(
            {
                "source": "finnhub",
                "time": e.get("time") or e.get("date"),
                "country": e.get("country"),
                "event": e.get("event"),
                "currency": e.get("currency"),
                "impact": (e.get("impact") or "").lower(),
                "estimate": e.get("estimate"),
                "actual": e.get("actual"),
            }
        )
        if len(rows) >= max_rows:
            break
    return rows, meta


def fetch_newsapi_forex_rows(
    *,
    api_key: str,
    from_day: str,
    to_day: str,
    max_items: int,
    timeout_s: float = 15.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta: Dict[str, Any] = {"http_status": None, "parser_ok": False, "api_error": None}
    rows: List[Dict[str, Any]] = []
    if not api_key:
        meta["failure_reason"] = "missing_api_key"
        return rows, meta
    q = "forex OR EUR OR USD OR GBP OR FED OR ECB OR CPI OR NFP"
    url = (
        "https://newsapi.org/v2/everything"
        f"?q={quote(q)}&from={from_day}&to={to_day}"
        f"&language=en&sortBy=publishedAt&pageSize={min(100, max_items)}&apiKey={api_key}"
    )
    try:
        r = requests.get(url, timeout=timeout_s)
    except requests.RequestException as e:
        meta["failure_reason"] = f"request_error:{type(e).__name__}"
        return rows, meta
    meta["http_status"] = int(r.status_code)
    if r.status_code != 200:
        meta["failure_reason"] = f"http_{r.status_code}"
        try:
            meta["api_error"] = r.json()
        except Exception:
            meta["api_error"] = (r.text or "")[:240]
        return rows, meta
    try:
        js = r.json()
    except ValueError:
        meta["failure_reason"] = "json_decode_error"
        return rows, meta
    arts = js.get("articles")
    if arts is None:
        meta["failure_reason"] = "missing_articles_key"
        return rows, meta
    if not isinstance(arts, list):
        meta["failure_reason"] = "unexpected_articles_shape"
        return rows, meta
    meta["parser_ok"] = True
    for a in arts:
        if not isinstance(a, dict):
            continue
        rows.append(
            {
                "source": "newsapi",
                "published_at": a.get("publishedAt"),
                "title": (a.get("title") or "")[:500],
                "description": (a.get("description") or "")[:500],
                "url": (a.get("url") or "")[:300],
            }
        )
        if len(rows) >= max_items:
            break
    return rows, meta
