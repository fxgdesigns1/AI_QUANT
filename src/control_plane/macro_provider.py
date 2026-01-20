from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class FredResult:
    ok: bool
    series: Dict[str, Any]
    status: Dict[str, Any]


def _hash_inputs(payload: Dict[str, Any]) -> str:
    raw = repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def fetch_fred_series(api_key: str, series_id: str, base_url: str = "https://api.stlouisfed.org/fred") -> Dict[str, Any]:
    url = f"{base_url}/series/observations"
    params = {
        "api_key": api_key,
        "file_type": "json",
        "series_id": series_id,
        "sort_order": "desc",
        "limit": 50,
    }
    r = requests.get(url, params=params, timeout=8)
    r.raise_for_status()
    return r.json()


def compute_macro_snapshot(fred_keys: List[str], series_ids: List[str]) -> FredResult:
    if not fred_keys:
        return FredResult(ok=False, series={}, status={"reason": "no_fred_keys_configured"})
    if not series_ids:
        return FredResult(ok=False, series={}, status={"reason": "no_fred_series_configured"})

    key = fred_keys[0]
    out: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for sid in series_ids:
        try:
            data = fetch_fred_series(key, sid)
            out[sid] = data
        except Exception as e:
            errors[sid] = f"{type(e).__name__}: {str(e)[:200]}"

    status = {
        "ok": len(out) > 0,
        "providers_used": ["fred"],
        "errors_by_series": errors,
        "series_count": len(out),
        "inputs_hash": _hash_inputs({"series_ids": series_ids}),
        "data_source": "fred",
    }
    return FredResult(ok=status["ok"], series=out, status=status)
