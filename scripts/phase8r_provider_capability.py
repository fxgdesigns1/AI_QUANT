#!/usr/bin/env python3
"""
Phase 8R: read-only provider capability for news, calendar, and macro (FRED) sources.

Loads optional --env-file into the process environment (no override of already-set vars).
Never prints API key values. Writes JSON reports only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.calendar_budgeted_client import fetch_calendar_with_budget  # noqa: E402
from scripts.local_research.phase8l_news_calendar_fetch import (  # noqa: E402
    fetch_finnhub_calendar_rows,
    fetch_newsapi_forex_rows,
    fetch_tradingeconomics_calendar_rows,
)
from scripts.local_research.rapidapi_economic_calendar_client import (  # noqa: E402
    fetch_tradingview_events,
    normalize_rows_for_export,
)

UTC = timezone.utc
PHASE = "Phase 8R"

# Exact list from Phase 8R-VERIFY-AND-RUNBOOK (order preserved).
PHASE8R_PROVIDER_ENV_NAMES: Sequence[str] = (
    "NEWSAPI_API_KEYS",
    "NEWSAPI_API_KEY",
    "FINNHUB_API_KEYS",
    "FINNHUB_API_KEY",
    "TRADINGECONOMICS_API_KEYS",
    "TRADINGECONOMICS_API_KEY",
    "MARKETAUX_API_KEYS",
    "MARKETAUX_API_KEY",
    "POLYGON_API_KEYS",
    "ALPHAVANTAGE_API_KEYS",
    "FRED_API_KEYS",
    "FMP_API_KEYS",
)


def _utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_env_file(path: Path, *, override: bool = False) -> int:
    """Return number of lines applied. KEY=VAL; no value echo."""
    if not path.is_file():
        return 0
    n = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = re.sub(r"^['\"]", "", re.sub(r"['\"]$", "", v.strip()))
        if not k:
            continue
        if override or k not in os.environ or not (os.environ.get(k) or "").strip():
            os.environ[k] = v
        n += 1
    return n


def env_presence_and_key_counts() -> Tuple[Dict[str, bool], Dict[str, int]]:
    presence: Dict[str, bool] = {}
    key_counts: Dict[str, int] = {}
    for name in PHASE8R_PROVIDER_ENV_NAMES:
        val = (os.getenv(name) or "").strip()
        presence[name] = bool(val)
        if not val:
            key_counts[name] = 0
        elif name.endswith("API_KEYS"):
            parts = [p.strip() for p in val.split(",") if p.strip()]
            key_counts[name] = len(parts)
        else:
            key_counts[name] = 1
    return presence, key_counts


def _split_keys_for_var(name: str) -> List[str]:
    v = (os.getenv(name) or "").strip()
    if not v:
        return []
    if "KEYS" in name and name.endswith("S"):
        return [p.strip() for p in v.split(",") if p.strip()]
    return [v]


def _keys_for_group(
    csv_names: Sequence[str], single_names: Sequence[str]
) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for n in csv_names:
        for k in _split_keys_for_var(n):
            out.append((k, n))
    for n in single_names:
        for k in _split_keys_for_var(n):
            out.append((k, n))
    return out


def _try_marketaux(keys: List[Tuple[str, str]], query: str, max_items: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "marketaux",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
    }
    if not keys:
        return out
    url = "https://api.marketaux.com/v1/news/all"
    for i, (key, src) in enumerate(keys):
        out["selected_env_name"] = src
        out["key_index_tried"] = i
        try:
            r = requests.get(
                url,
                params={"api_token": key, "search": query, "language": "en", "limit": str(max_items)},
                timeout=15.0,
            )
        except requests.RequestException as e:
            out["failure_reason"] = f"request_error:{type(e).__name__}"
            continue
        out["http_status"] = r.status_code
        if r.status_code == 429:
            out["failure_reason"] = "rate_limited"
            continue
        if r.status_code != 200:
            out["failure_reason"] = f"http_{r.status_code}"
            continue
        try:
            data = r.json()
        except ValueError:
            out["failure_reason"] = "json_decode_error"
            continue
        data_list = data.get("data")
        if not isinstance(data_list, list):
            out["failure_reason"] = "unexpected_shape"
            continue
        out["parser_ok"] = True
        out["rows_returned"] = min(len(data_list), max_items)
        out["failure_reason"] = "ok" if out["rows_returned"] else "empty_results"
        break
    return out


def _try_polygon(keys: List[Tuple[str, str]], max_items: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "polygon",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
    }
    if not keys:
        return out
    url = "https://api.polygon.io/v2/reference/news"
    for i, (key, src) in enumerate(keys):
        out["selected_env_name"] = src
        out["key_index_tried"] = i
        try:
            r = requests.get(
                url,
                params={"apiKey": key, "limit": str(max_items), "order": "desc"},
                timeout=15.0,
            )
        except requests.RequestException as e:
            out["failure_reason"] = f"request_error:{type(e).__name__}"
            continue
        out["http_status"] = r.status_code
        if r.status_code == 429:
            out["failure_reason"] = "rate_limited"
            continue
        if r.status_code != 200:
            out["failure_reason"] = f"http_{r.status_code}"
            continue
        try:
            data = r.json()
        except ValueError:
            out["failure_reason"] = "json_decode_error"
            continue
        results = data.get("results")
        if not isinstance(results, list):
            out["failure_reason"] = "unexpected_shape"
            continue
        out["parser_ok"] = True
        out["rows_returned"] = min(len(results), max_items)
        out["failure_reason"] = "ok" if out["rows_returned"] else "empty_results"
        break
    return out


def _try_alphavantage(keys: List[Tuple[str, str]], max_items: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "alphavantage",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
    }
    if not keys:
        return out
    url = "https://www.alphavantage.co/query"
    for i, (key, src) in enumerate(keys):
        out["selected_env_name"] = src
        out["key_index_tried"] = i
        try:
            r = requests.get(
                url,
                params={
                    "function": "NEWS_SENTIMENT",
                    "apikey": key,
                    "limit": str(max_items),
                    "sort": "LATEST",
                },
                timeout=20.0,
            )
        except requests.RequestException as e:
            out["failure_reason"] = f"request_error:{type(e).__name__}"
            continue
        out["http_status"] = r.status_code
        if r.status_code == 429:
            out["failure_reason"] = "rate_limited"
            continue
        if r.status_code != 200:
            out["failure_reason"] = f"http_{r.status_code}"
            continue
        try:
            data = r.json()
        except ValueError:
            out["failure_reason"] = "json_decode_error"
            continue
        feed = data.get("feed")
        if feed is None:
            if "Note" in data or "Information" in data:
                out["failure_reason"] = "plan_limit_or_throttled"
            else:
                out["failure_reason"] = "missing_feed"
            continue
        if not isinstance(feed, list):
            out["failure_reason"] = "unexpected_shape"
            continue
        out["parser_ok"] = True
        out["rows_returned"] = min(len(feed), max_items)
        out["failure_reason"] = "ok" if out["rows_returned"] else "empty_results"
        break
    return out


def _try_fmp_news(keys: List[Tuple[str, str]], max_items: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "fmp_stock_news",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
    }
    if not keys:
        return out
    url = "https://financialmodelingprep.com/api/v3/stock_news"
    for i, (key, src) in enumerate(keys):
        out["selected_env_name"] = src
        out["key_index_tried"] = i
        try:
            r = requests.get(url, params={"apikey": key, "limit": str(max_items)}, timeout=15.0)
        except requests.RequestException as e:
            out["failure_reason"] = f"request_error:{type(e).__name__}"
            continue
        out["http_status"] = r.status_code
        if r.status_code == 429:
            out["failure_reason"] = "rate_limited"
            continue
        if r.status_code != 200:
            out["failure_reason"] = f"http_{r.status_code}"
            continue
        try:
            data = r.json()
        except ValueError:
            out["failure_reason"] = "json_decode_error"
            continue
        if not isinstance(data, list):
            out["failure_reason"] = "unexpected_shape"
            continue
        out["parser_ok"] = True
        out["rows_returned"] = min(len(data), max_items)
        out["failure_reason"] = "ok" if out["rows_returned"] else "empty_results"
        break
    return out


def _try_fmp_economic_calendar(
    keys: List[Tuple[str, str]],
    d1: str,
    d2: str,
    repo_root: Path,
    session_remaining: List[int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "fmp_economic_calendar",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
        "budget_cache_hit": False,
        "budget_blocked": False,
    }
    if not keys:
        return out
    key, src = keys[0]
    out["selected_env_name"] = src
    out["key_index_tried"] = 0
    url = "https://financialmodelingprep.com/api/v3/economic_calendar"

    def inner() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        meta: Dict[str, Any] = {}
        try:
            r = requests.get(url, params={"from": d1, "to": d2, "apikey": key}, timeout=15.0)
        except requests.RequestException as e:
            meta["failure_reason"] = f"request_error:{type(e).__name__}"
            meta["http_status"] = None
            return [], meta
        meta["http_status"] = int(r.status_code)
        if r.status_code != 200:
            meta["failure_reason"] = f"http_{r.status_code}"
            return [], meta
        try:
            data = r.json()
        except ValueError:
            meta["failure_reason"] = "json_decode_error"
            return [], meta
        if not isinstance(data, list):
            meta["failure_reason"] = "unexpected_shape"
            return [], meta
        meta["parser_ok"] = True
        meta["failure_reason"] = "ok" if data else "empty_results"
        rows = [dict(x) for x in data if isinstance(x, dict)]
        return rows, meta

    rows, bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="fmp_economic_calendar",
        date_from=d1,
        date_to=d2,
        countries="",
        session_remaining_paid_calls=session_remaining,
        inner=inner,
    )
    inner_meta = bmeta.get("inner") or {}
    out["http_status"] = inner_meta.get("http_status")
    out["parser_ok"] = bool(inner_meta.get("parser_ok"))
    out["rows_returned"] = len(rows)
    out["failure_reason"] = inner_meta.get("failure_reason") or ("ok" if rows else "empty_or_blocked")
    out["budget_cache_hit"] = bool(bmeta.get("cache_hit"))
    out["budget_blocked"] = bool(bmeta.get("budget_blocked"))
    return out


def _try_fred(keys: List[Tuple[str, str]], observation_start: date) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "fred_observations",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
        "series_id": "GDP",
    }
    if not keys:
        return out
    url = "https://api.stlouisfed.org/fred/series/observations"
    for i, (key, src) in enumerate(keys):
        out["selected_env_name"] = src
        out["key_index_tried"] = i
        try:
            r = requests.get(
                url,
                params={
                    "series_id": "GDP",
                    "api_key": key,
                    "file_type": "json",
                    "observation_start": observation_start.isoformat(),
                    "limit": 10,
                    "sort_order": "desc",
                },
                timeout=15.0,
            )
        except requests.RequestException as e:
            out["failure_reason"] = f"request_error:{type(e).__name__}"
            continue
        out["http_status"] = r.status_code
        if r.status_code == 429:
            out["failure_reason"] = "rate_limited"
            continue
        if r.status_code != 200:
            out["failure_reason"] = f"http_{r.status_code}"
            continue
        try:
            data = r.json()
        except ValueError:
            out["failure_reason"] = "json_decode_error"
            continue
        obs = data.get("observations")
        if not isinstance(obs, list):
            out["failure_reason"] = "unexpected_shape"
            continue
        out["parser_ok"] = True
        out["rows_returned"] = len(obs)
        out["failure_reason"] = "ok" if out["rows_returned"] else "empty_results"
        break
    return out


def _newsapi_probe(keys: List[Tuple[str, str]], d1: str, d2: str, max_items: int) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "provider": "newsapi",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
    }
    if not keys:
        return base
    for i, (key, src) in enumerate(keys):
        rows, meta = fetch_newsapi_forex_rows(
            api_key=key, from_day=d1, to_day=d2, max_items=max_items
        )
        base["selected_env_name"] = src
        base["key_index_tried"] = i
        base["http_status"] = meta.get("http_status")
        base["parser_ok"] = bool(meta.get("parser_ok"))
        base["rows_returned"] = len(rows)
        base["failure_reason"] = meta.get("failure_reason") or (
            "ok" if rows else "empty_or_blocked"
        )
        if rows:
            break
        if meta.get("http_status") == 429:
            continue
        break
    return base


def _te_calendar(
    keys: List[Tuple[str, str]],
    d1: str,
    d2: str,
    max_rows: int,
    repo_root: Path,
    session_remaining: List[int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "tradingeconomics_calendar",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
        "budget_cache_hit": False,
        "budget_blocked": False,
    }
    if not keys:
        return out
    key, src = keys[0]
    out["selected_env_name"] = src
    out["key_index_tried"] = 0

    def inner() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return fetch_tradingeconomics_calendar_rows(
            api_key=key, d1=d1, d2=d2, max_rows=max_rows
        )

    rows, bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="tradingeconomics_calendar",
        date_from=d1,
        date_to=d2,
        countries="",
        session_remaining_paid_calls=session_remaining,
        inner=inner,
    )
    inner_meta = bmeta.get("inner") or {}
    out["http_status"] = inner_meta.get("http_status")
    out["parser_ok"] = bool(inner_meta.get("parser_ok"))
    out["rows_returned"] = len(rows)
    out["failure_reason"] = inner_meta.get("failure_reason") or ("ok" if rows else "empty_or_blocked")
    out["budget_cache_hit"] = bool(bmeta.get("cache_hit"))
    out["budget_blocked"] = bool(bmeta.get("budget_blocked"))
    return out


def _fh_calendar(
    keys: List[Tuple[str, str]],
    d1: str,
    d2: str,
    max_rows: int,
    repo_root: Path,
    session_remaining: List[int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "finnhub_economic_calendar",
        "rows_returned": 0,
        "http_status": None,
        "selected_env_name": None,
        "key_index_tried": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
        "budget_cache_hit": False,
        "budget_blocked": False,
    }
    if not keys:
        return out
    key, src = keys[0]
    out["selected_env_name"] = src
    out["key_index_tried"] = 0

    def inner() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return fetch_finnhub_calendar_rows(api_key=key, d1=d1, d2=d2, max_rows=max_rows)

    rows, bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="finnhub_economic_calendar",
        date_from=d1,
        date_to=d2,
        countries="",
        session_remaining_paid_calls=session_remaining,
        inner=inner,
    )
    inner_meta = bmeta.get("inner") or {}
    out["http_status"] = inner_meta.get("http_status")
    out["parser_ok"] = bool(inner_meta.get("parser_ok"))
    out["rows_returned"] = len(rows)
    out["failure_reason"] = inner_meta.get("failure_reason") or ("ok" if rows else "empty_or_blocked")
    out["budget_cache_hit"] = bool(bmeta.get("cache_hit"))
    out["budget_blocked"] = bool(bmeta.get("budget_blocked"))
    return out


def _rapidapi_calendar(
    *,
    countries: str,
    d1: str,
    d2: str,
    max_rows: int,
    repo_root: Path,
    session_remaining: List[int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": "rapidapi_economic_calendar",
        "rows_returned": 0,
        "http_status": None,
        "parser_ok": False,
        "failure_reason": "no_keys",
        "budget_cache_hit": False,
        "budget_blocked": False,
    }

    def inner() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        raw, meta = fetch_tradingview_events(countries=countries, date_from=d1, date_to=d2)
        norm = normalize_rows_for_export(raw, max_rows=max_rows)
        return norm, meta

    rows, bmeta = fetch_calendar_with_budget(
        repo_root=repo_root,
        provider="rapidapi_economic_calendar",
        date_from=d1,
        date_to=d2,
        countries=countries,
        session_remaining_paid_calls=session_remaining,
        inner=inner,
    )
    inner_meta = bmeta.get("inner") or {}
    out["http_status"] = inner_meta.get("http_status")
    out["parser_ok"] = bool(inner_meta.get("parser_ok"))
    out["rows_returned"] = len(rows)
    out["failure_reason"] = inner_meta.get("failure_reason") or ("ok" if rows else "empty_or_blocked")
    out["budget_cache_hit"] = bool(bmeta.get("cache_hit"))
    out["budget_blocked"] = bool(bmeta.get("budget_blocked"))
    return out


def run_capability(
    *,
    instrument: str,
    lookback_days: int,
    max_probe_rows: int,
    env_file_lines_applied: int,
    repo_root: Path,
    max_calendar_paid_calls: int,
    provider_filter: str,
    rapidapi_countries: str,
) -> Tuple[Dict[str, Any], int]:
    end_d = date.today()
    start_d = end_d - timedelta(days=max(1, lookback_days))
    d1 = start_d.isoformat()
    d2 = end_d.isoformat()

    presence, key_counts = env_presence_and_key_counts()

    newsapi_keys = _keys_for_group(("NEWSAPI_API_KEYS",), ("NEWSAPI_API_KEY",))
    marketaux_keys = _keys_for_group(("MARKETAUX_API_KEYS",), ("MARKETAUX_API_KEY",))
    polygon_keys = _keys_for_group(("POLYGON_API_KEYS",), ("POLYGON_API_KEY",))
    av_keys = _keys_for_group(("ALPHAVANTAGE_API_KEYS",), ("ALPHAVANTAGE_API_KEY",))
    fmp_keys = _keys_for_group(("FMP_API_KEYS",), ())
    fred_keys = _keys_for_group(("FRED_API_KEYS",), ())
    te_keys = _keys_for_group(("TRADINGECONOMICS_API_KEYS",), ("TRADINGECONOMICS_API_KEY",))
    finnhub_keys = _keys_for_group(("FINNHUB_API_KEYS",), ("FINNHUB_API_KEY",))

    query = "EUR USD ECB Fed CPI NFP forex"

    session_remaining = [max(0, int(max_calendar_paid_calls))]

    probes_news = []
    if provider_filter != "rapidapi_calendar":
        probes_news = [
            _newsapi_probe(newsapi_keys, d1, d2, max_probe_rows),
            _try_marketaux(marketaux_keys, query, max_probe_rows),
            _try_polygon(polygon_keys, max_probe_rows),
            _try_alphavantage(av_keys, max_probe_rows),
            _try_fmp_news(fmp_keys, max_probe_rows),
        ]
    probes_macro = []
    if provider_filter != "rapidapi_calendar":
        probes_macro = [_try_fred(fred_keys, start_d)]

    if provider_filter == "rapidapi_calendar":
        probes_calendar = [
            _rapidapi_calendar(
                countries=rapidapi_countries,
                d1=d1,
                d2=d2,
                max_rows=max_probe_rows,
                repo_root=repo_root,
                session_remaining=session_remaining,
            )
        ]
    elif provider_filter == "legacy_calendar":
        probes_calendar = [
            _te_calendar(te_keys, d1, d2, max_probe_rows, repo_root, session_remaining),
            _fh_calendar(finnhub_keys, d1, d2, max_probe_rows, repo_root, session_remaining),
            _try_fmp_economic_calendar(fmp_keys, d1, d2, repo_root, session_remaining),
        ]
    else:
        probes_calendar = [
            _te_calendar(te_keys, d1, d2, max_probe_rows, repo_root, session_remaining),
            _fh_calendar(finnhub_keys, d1, d2, max_probe_rows, repo_root, session_remaining),
            _try_fmp_economic_calendar(fmp_keys, d1, d2, repo_root, session_remaining),
            _rapidapi_calendar(
                countries=rapidapi_countries,
                d1=d1,
                d2=d2,
                max_rows=max_probe_rows,
                repo_root=repo_root,
                session_remaining=session_remaining,
            ),
        ]

    news_labels = ("newsapi", "marketaux", "polygon", "alphavantage", "fmp_stock_news")
    working_news = [
        news_labels[i]
        for i, p in enumerate(probes_news)
        if isinstance(p.get("rows_returned"), int) and p["rows_returned"] > 0
    ]

    cal_work_labels = []
    for p in probes_calendar:
        label = str(p.get("provider") or "")
        if int(p.get("rows_returned") or 0) > 0 and label:
            cal_work_labels.append(label)

    historical_news_supported = any(
        p.get("parser_ok") and p.get("rows_returned", 0) > 0 for p in probes_news
    )
    historical_calendar_supported = len(cal_work_labels) > 0
    historical_macro_supported = bool(
        probes_macro and int(probes_macro[0].get("rows_returned") or 0) > 0
    )

    news_rows_count = sum(int(p.get("rows_returned") or 0) for p in probes_news)
    calendar_rows_count = sum(int(p.get("rows_returned") or 0) for p in probes_calendar)

    if provider_filter == "rapidapi_calendar":
        strict_pass = bool(historical_calendar_supported)
    else:
        strict_pass = (
            len(working_news) > 0
            and len(cal_work_labels) > 0
            and historical_news_supported
            and historical_calendar_supported
        )

    classification = "PASS_PROVIDER_CAPABILITY" if strict_pass else "FAIL_CLOSED_PROVIDER_CAPABILITY"

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso_z(),
        "phase": PHASE,
        "classification": classification,
        "instrument": instrument,
        "lookback_days": lookback_days,
        "date_window_start_day": d1,
        "date_window_end_day": d2,
        "provider_filter": provider_filter,
        "max_calendar_paid_calls_budget": max_calendar_paid_calls,
        "calendar_paid_calls_remaining_after_run": session_remaining[0],
        "rapidapi_default_countries": rapidapi_countries,
        "calendar_budget_bypass_paths_live": [
            "news_manager.py:NewsManager.refresh_calendar (direct TE/FH URLs — not wrapped this phase)",
            "src/control_plane/api.py:get_economic_calendar (uses NewsManager)",
        ],
        "env_file_lines_applied": env_file_lines_applied,
        "provider_env_presence": presence,
        "provider_key_counts": key_counts,
        "probe_news": probes_news,
        "probe_calendar": probes_calendar,
        "probe_macro": probes_macro,
        "working_news_providers": working_news,
        "working_calendar_providers": cal_work_labels,
        "working_macro_providers": ["fred_observations"] if historical_macro_supported else [],
        "historical_news_supported": historical_news_supported,
        "historical_calendar_supported": historical_calendar_supported,
        "historical_macro_supported": historical_macro_supported,
        "news_rows_count": news_rows_count,
        "calendar_rows_count": calendar_rows_count,
        "fred_rows_count": int(probes_macro[0].get("rows_returned") or 0) if probes_macro else 0,
        "secrets_exposed": False,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "order_or_execution_apis_called": False,
    }

    exit_code = 0 if strict_pass else 1
    return report, exit_code


def write_aligned_manifest(report: Dict[str, Any], path: Path) -> None:
    if report.get("classification") != "PASS_PROVIDER_CAPABILITY":
        return
    start_day = report.get("date_window_start_day")
    end_day = report.get("date_window_end_day")
    manifest = {
        "generated_at_utc": _utc_now_iso_z(),
        "phase": PHASE,
        "classification": "PHASE8R_ALIGNED_CONTEXT_MANIFEST",
        "instrument": report.get("instrument"),
        "lookback_days": report.get("lookback_days"),
        "aligned_window_start_day": start_day,
        "aligned_window_end_day": end_day,
        "news_providers_verified": report.get("working_news_providers"),
        "calendar_providers_verified": report.get("working_calendar_providers"),
        "historical_news_supported": report.get("historical_news_supported"),
        "historical_calendar_supported": report.get("historical_calendar_supported"),
        "news_rows_count": report.get("news_rows_count"),
        "calendar_rows_count": report.get("calendar_rows_count"),
        "notes": "Aligned to Phase 8R probe window; used for replay context gates.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8R provider capability (read-only).")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--max-probe-rows", type=int, default=50)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--max-calendar-paid-calls", type=int, default=50)
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=None,
        help="Alias for --max-calendar-paid-calls (calendar HTTP budget per run).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="all",
        choices=["all", "rapidapi_calendar", "legacy_calendar"],
    )
    parser.add_argument("--rapidapi-countries", type=str, default="US,GB,EU")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "ARTIFACTS" / "performance",
    )
    args = parser.parse_args()

    applied = 0
    if args.env_file:
        applied = load_env_file(args.env_file.expanduser().resolve(), override=False)

    cap = args.max_api_calls if args.max_api_calls is not None else int(args.max_calendar_paid_calls)

    report, exit_code = run_capability(
        instrument=str(args.instrument),
        lookback_days=int(args.lookback_days),
        max_probe_rows=int(args.max_probe_rows),
        env_file_lines_applied=applied,
        repo_root=args.repo_root.expanduser().resolve(),
        max_calendar_paid_calls=int(cap),
        provider_filter=str(args.provider),
        rapidapi_countries=str(args.rapidapi_countries),
    )

    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"phase8r_provider_capability_report_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest = out_dir / "latest_phase8r_provider_capability_report.json"
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    aligned = out_dir / "latest_phase8r_aligned_context_manifest.json"
    if report.get("classification") == "PASS_PROVIDER_CAPABILITY":
        write_aligned_manifest(report, aligned)
    elif aligned.is_file():
        aligned.unlink()

    print(json.dumps({"ok": exit_code == 0, "classification": report["classification"], "report": str(latest)}, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
