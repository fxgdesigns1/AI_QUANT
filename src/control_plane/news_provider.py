from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

_blocked_provider_keys: Dict[str, Dict[str, float]] = {}
_block_ttl_seconds = 3600


def _rate_limit_meta(headers: Dict[str, Any]) -> Dict[str, Any]:
    def _get(name: str) -> Optional[str]:
        return headers.get(name) or headers.get(name.lower())
    meta = {}
    remaining = _get("X-RateLimit-Remaining")
    limit = _get("X-RateLimit-Limit")
    reset = _get("X-RateLimit-Reset")
    if remaining is not None:
        meta["remaining"] = remaining
    if limit is not None:
        meta["limit"] = limit
    if reset is not None:
        meta["reset"] = reset
    return meta


def _should_block_error(message: str) -> Optional[int]:
    msg = message.lower()
    if "401" in msg or "invalid api token" in msg or "invalid api key" in msg or "unauthorized" in msg:
        return _block_ttl_seconds
    if "403" in msg or "forbidden" in msg:
        return _block_ttl_seconds
    if "429" in msg or "rate limit" in msg:
        return 600
    return None


def _is_key_blocked(provider: str, key: str) -> bool:
    if not key:
        return True
    provider_keys = _blocked_provider_keys.get(provider, {})
    expiry = provider_keys.get(key)
    if not expiry:
        return False
    if time.time() > expiry:
        provider_keys.pop(key, None)
        return False
    return True


def _block_key(provider: str, key: str, ttl: int) -> None:
    if not key:
        return
    _blocked_provider_keys.setdefault(provider, {})[key] = time.time() + ttl

from src.core.settings import settings


class NewsError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewsItem:
    ts_utc: float
    source: str
    title: str
    url: str
    summary: str
    symbols: List[str]
    impact: str  # low|medium|high


def _env(name: str) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else None


def _impact_from_text(title: str, summary: str, threshold: str = "medium") -> str:
    # Simple deterministic heuristic. No ML deps.
    text = f"{title} {summary}".lower()
    high_kw = [
        "rate decision", "interest rate", "fed", "fomc", "boj", "ecb", "boe",
        "cpi", "inflation", "jobs report", "nonfarm", "gdp", "recession",
        "bank failure", "default", "war", "sanction", "crisis"
    ]
    med_kw = ["earnings", "guidance", "central bank", "oil", "gold", "yen", "dollar", "pmi", "retail sales"]

    score = 0
    score += 3 * sum(1 for k in high_kw if k in text)
    score += 1 * sum(1 for k in med_kw if k in text)

    # threshold tunes mapping
    if threshold == "low":
        return "high" if score >= 2 else ("medium" if score >= 1 else "low")
    if threshold == "high":
        return "high" if score >= 5 else ("medium" if score >= 2 else "low")
    return "high" if score >= 4 else ("medium" if score >= 1 else "low")


def _dedupe_key(url: str, title: str) -> str:
    h = hashlib.sha256((url.strip() + "|" + title.strip()).encode("utf-8", errors="ignore")).hexdigest()
    return h[:16]


def fetch_news_newsapi(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 10.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    api_key = _env("NEWSAPI_API_KEY")
    if not api_key:
        raise NewsError("Missing required env var: NEWSAPI_API_KEY")

    # NewsAPI: /v2/everything is more reliable than top-headlines for FX keywords
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": str(max_items),
        "sortBy": "publishedAt",
    }
    headers = {"X-Api-Key": api_key}
    r = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"NewsAPI error {r.status_code}: {r.text[:200]}")
    data = r.json()
    articles = data.get("articles") or []

    out: List[Dict[str, Any]] = []
    now = time.time()
    for a in articles:
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        url_ = (a.get("url") or "").strip()
        if not title or not url_:
            continue
        summary = (a.get("description") or "").strip()
        source = ((a.get("source") or {}).get("name") or "newsapi").strip()
        impact = _impact_from_text(title, summary, threshold)
        out.append(
            {
                "id": _dedupe_key(url_, title),
                "ts_utc": now,
                "source": source,
                "title": title,
                "url": url_,
                "summary": summary,
                "symbols": [],
                "impact": impact,
            }
        )
    return out, _rate_limit_meta(r.headers)


def fetch_news_alphavantage(
    *,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 12.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    api_key = _env("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise NewsError("Missing required env var: ALPHAVANTAGE_API_KEY")

    # AlphaVantage NEWS_SENTIMENT endpoint
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "limit": str(max_items),
        "sort": "LATEST",
    }
    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"AlphaVantage error {r.status_code}: {r.text[:200]}")
    data = r.json()
    feed = data.get("feed") or []

    out: List[Dict[str, Any]] = []
    now = time.time()
    for f in feed:
        title = (f.get("title") or "").strip()
        url_ = (f.get("url") or "").strip()
        if not title or not url_:
            continue
        summary = (f.get("summary") or "").strip()
        source = (f.get("source") or "alphavantage").strip()
        tickers = [t.get("ticker") for t in (f.get("ticker_sentiment") or []) if t.get("ticker")]
        impact = _impact_from_text(title, summary, threshold)
        out.append(
            {
                "id": _dedupe_key(url_, title),
                "ts_utc": now,
                "source": source,
                "title": title,
                "url": url_,
                "summary": summary,
                "symbols": tickers[:8],
                "impact": impact,
            }
        )
    return out, _rate_limit_meta(r.headers)


def fetch_news_marketaux(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 8.0,
    api_key: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch news from MarketAux"""
    if not settings.marketaux_keys:
        raise NewsError("No MarketAux keys configured")
    
    api_key = api_key or settings.marketaux_keys[0]
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": api_key,
        "search": query,
        "language": "en",
        "limit": str(max_items),
    }
    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"MarketAux error {r.status_code}: {r.text[:200]}")
    data = r.json()
    articles = data.get("data") or []
    
    out: List[Dict[str, Any]] = []
    now = time.time()
    for a in articles:
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        url_ = (a.get("url") or "").strip()
        if not title or not url_:
            continue
        summary = (a.get("description") or "").strip()
        source = (a.get("source") or "marketaux").strip()
        symbols = [s.get("symbol") for s in (a.get("entities") or []) if s.get("symbol")]
        impact = _impact_from_text(title, summary, threshold)
        out.append({
            "id": _dedupe_key(url_, title),
            "ts_utc": now,
            "source": source,
            "title": title,
            "url": url_,
            "summary": summary,
            "symbols": symbols[:8],
            "impact": impact,
        })
    return out, _rate_limit_meta(r.headers)


def fetch_news_finnhub(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 8.0,
    api_key: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch news from Finnhub"""
    if not settings.finnhub_keys:
        raise NewsError("No Finnhub keys configured")
    
    api_key = api_key or settings.finnhub_keys[0]
    # Finnhub general news endpoint
    url = "https://finnhub.io/api/v1/news"
    params = {
        "category": "general",
        "token": api_key,
    }
    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"Finnhub error {r.status_code}: {r.text[:200]}")
    articles = r.json() or []
    
    out: List[Dict[str, Any]] = []
    now = time.time()
    for a in articles[:max_items]:
        title = (a.get("headline") or "").strip()
        url_ = (a.get("url") or "").strip()
        if not title or not url_:
            continue
        summary = (a.get("summary") or "").strip()
        source = (a.get("source") or "finnhub").strip()
        symbols = [s for s in (a.get("related") or "").split(",") if s.strip()][:8]
        impact = _impact_from_text(title, summary, threshold)
        out.append({
            "id": _dedupe_key(url_, title),
            "ts_utc": now,
            "source": source,
            "title": title,
            "url": url_,
            "summary": summary,
            "symbols": symbols,
            "impact": impact,
        })
    return out, _rate_limit_meta(r.headers)


def fetch_news_polygon(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 8.0,
    api_key: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch news from Polygon"""
    if not settings.polygon_keys:
        raise NewsError("No Polygon keys configured")
    
    api_key = api_key or settings.polygon_keys[0]
    url = "https://api.polygon.io/v2/reference/news"
    params = {
        "apiKey": api_key,
        "limit": str(max_items),
        "order": "desc",
    }
    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"Polygon error {r.status_code}: {r.text[:200]}")
    data = r.json()
    if not isinstance(data, dict):
        raise NewsError(f"Polygon error {r.status_code}: {str(data)[:200]}")
    articles = data.get("results") or []
    if not isinstance(articles, list):
        raise NewsError(f"Polygon error {r.status_code}: {str(articles)[:200]}")
    
    out: List[Dict[str, Any]] = []
    now = time.time()
    for a in articles:
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        url_ = (a.get("article_url") or "").strip()
        if not title or not url_:
            continue
        summary = (a.get("description") or "").strip()
        source = (a.get("publisher", {}).get("name") or "polygon").strip()
        symbols = [t.get("ticker") for t in (a.get("tickers") or []) if isinstance(t, dict) and t.get("ticker")][:8]
        impact = _impact_from_text(title, summary, threshold)
        out.append({
            "id": _dedupe_key(url_, title),
            "ts_utc": now,
            "source": source,
            "title": title,
            "url": url_,
            "summary": summary,
            "symbols": symbols,
            "impact": impact,
        })
    return out, _rate_limit_meta(r.headers)


def fetch_news_fmp(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
    timeout_s: float = 8.0,
    api_key: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch news from Financial Modeling Prep"""
    if not settings.fmp_keys:
        raise NewsError("No FMP keys configured")
    
    api_key = api_key or settings.fmp_keys[0]
    url = "https://financialmodelingprep.com/api/v3/stock_news"
    params = {
        "apikey": api_key,
        "limit": str(max_items),
    }
    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise NewsError(f"FMP error {r.status_code}: {r.text[:200]}")
    articles = r.json() or []
    
    out: List[Dict[str, Any]] = []
    now = time.time()
    for a in articles:
        title = (a.get("title") or "").strip()
        url_ = (a.get("url") or "").strip()
        if not title or not url_:
            continue
        summary = (a.get("text") or "").strip()
        source = (a.get("site") or "fmp").strip()
        symbols = [a.get("symbol")] if a.get("symbol") else []
        impact = _impact_from_text(title, summary, threshold)
        out.append({
            "id": _dedupe_key(url_, title),
            "ts_utc": now,
            "source": source,
            "title": title,
            "url": url_,
            "summary": summary,
            "symbols": symbols,
            "impact": impact,
        })
    return out, _rate_limit_meta(r.headers)


def fetch_news_with_registry(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch news using multi-provider registry in priority order
    
    Returns:
        (items, status) where status includes providers_used, errors_by_provider, fetched_count
    """
    providers_used: List[str] = []
    errors_by_provider: Dict[str, str] = {}
    all_items: List[Dict[str, Any]] = []
    seen_ids: set = set()
    
    # Priority order: MarketAux -> Finnhub -> Polygon -> FMP -> NewsAPI -> AlphaVantage
    # Only add providers that have keys configured
    provider_fns = []
    
    if settings.marketaux_keys:
        provider_fns.append(("marketaux", settings.marketaux_keys, lambda k: fetch_news_marketaux(query=query, threshold=threshold, max_items=max_items, api_key=k)))
    if settings.finnhub_keys:
        provider_fns.append(("finnhub", settings.finnhub_keys, lambda k: fetch_news_finnhub(query=query, threshold=threshold, max_items=max_items, api_key=k)))
    if settings.polygon_keys:
        provider_fns.append(("polygon", settings.polygon_keys, lambda k: fetch_news_polygon(query=query, threshold=threshold, max_items=max_items, api_key=k)))
    if settings.fmp_keys:
        provider_fns.append(("fmp", settings.fmp_keys, lambda k: fetch_news_fmp(query=query, threshold=threshold, max_items=max_items, api_key=k)))
    if settings.newsapi_api_key:
        provider_fns.append(("newsapi", [settings.newsapi_api_key], lambda k: fetch_news_newsapi(query=query, threshold=threshold, max_items=max_items)))
    if settings.alphavantage_api_key:
        provider_fns.append(("alphavantage", [settings.alphavantage_api_key], lambda k: fetch_news_alphavantage(threshold=threshold, max_items=max_items)))
    
    rate_limits: Dict[str, Any] = {}

    for provider_name, keys, fetch_fn in provider_fns:
        last_error = None
        for key in keys:
            if _is_key_blocked(provider_name, key):
                continue
            try:
                items, meta = fetch_fn(key)
                if meta:
                    rate_limits[provider_name] = meta
                # Deduplicate by id
                for item in items:
                    item_id = item.get("id")
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        all_items.append(item)
                if items:
                    providers_used.append(provider_name)
                last_error = None
                break
            except NewsError as e:
                last_error = str(e)[:200]
                ttl = _should_block_error(last_error)
                if ttl:
                    _block_key(provider_name, key, ttl)
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
        if last_error:
            errors_by_provider[provider_name] = last_error
    
    # Limit to max_items
    all_items = all_items[:max_items]
    
    status = {
        "providers_used": providers_used,
        "errors_by_provider": errors_by_provider,
        "rate_limits": rate_limits,
        "fetched_count": len(all_items),
        "reason": "no_news_providers_configured" if not providers_used and not all_items else None,
    }
    
    return all_items, status


def fetch_news(
    *,
    query: str,
    threshold: str = "medium",
    max_items: int = 30,
) -> List[Dict[str, Any]]:
    """Legacy function: use registry and return items only"""
    items, _ = fetch_news_with_registry(query=query, threshold=threshold, max_items=max_items)
    return items
