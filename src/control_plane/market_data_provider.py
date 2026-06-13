#!/usr/bin/env python3
"""Market data provider (single source of truth).
SAFE defaults:
- Uses OANDA Practice by default.
- Fails fast if creds missing when live data required.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Price:
    instrument: str
    bid: float
    ask: float
    mid: float
    ts_utc: float


@dataclass(frozen=True)
class PriceIntegrityResult:
    """Price integrity validation result"""
    ok: bool
    violation_code: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class Candle:
    time: str
    complete: bool
    volume: int
    o: float
    h: float
    l: float
    c: float


class MarketDataError(RuntimeError):
    pass


class PriceIntegrityError(MarketDataError):
    """Raised when price fails integrity validation"""
    pass


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _require(name: str) -> str:
    v = _env(name)
    if not v:
        raise MarketDataError(f"Missing required env var: {name}")
    return v


def _base_url() -> str:
    # Practice by default
    env = _env("OANDA_ENV", "practice").lower()
    if env == "live":
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_require('OANDA_API_KEY')}",
        "Content-Type": "application/json",
    }


# Price integrity guardrails
MAX_STALENESS_SEC = float(_env("PRICE_MAX_STALENESS_SEC", "10"))
MAX_SPREAD_PCT_FX = float(_env("PRICE_MAX_SPREAD_PCT_FX", "0.002"))  # 0.20%
MAX_SPREAD_PCT_METALS = float(_env("PRICE_MAX_SPREAD_PCT_METALS", "0.005"))  # 0.50%
MAX_SPREAD_PCT_INDICES = float(_env("PRICE_MAX_SPREAD_PCT_INDICES", "0.008"))  # 0.80%
PRICE_MIN_VALUE = 1e-6  # Reject prices smaller than this
MID_EPSILON = 1e-6  # Maximum difference between mid and (bid+ask)/2


def _get_instrument_type(instrument: str) -> str:
    """Determine instrument type from symbol pattern"""
    instrument_upper = instrument.upper()
    if "XAU" in instrument_upper or "XAG" in instrument_upper:
        return "metal"
    elif "USD" in instrument_upper and (len(instrument_upper.replace("_", "")) <= 8):
        return "fx"
    else:
        # Default to indices for others (US30, NAS100, SPX, GER30, etc.)
        return "index"


def _get_max_spread_pct(instrument: str) -> float:
    """Get max spread percentage for instrument type"""
    inst_type = _get_instrument_type(instrument)
    if inst_type == "metal":
        return MAX_SPREAD_PCT_METALS
    elif inst_type == "fx":
        return MAX_SPREAD_PCT_FX
    else:  # index
        return MAX_SPREAD_PCT_INDICES


def validate_price_integrity(price: Price, source_path: str = "unknown") -> PriceIntegrityResult:
    """Validate price integrity contract - single source of truth for all price validation.
    
    Enforces:
    - Required fields: instrument, bid, ask, mid, ts_utc
    - Invariants:
      * bid > 0, ask > 0
      * ask >= bid
      * spread_pct = (ask-bid)/mid within instrument-specific bounds
      * timestamp is fresh (<= MAX_STALENESS_SEC)
      * mid must be approx (bid+ask)/2 within epsilon
    - Rejects NaN/inf
    - Rejects unit/scale errors (prices < PRICE_MIN_VALUE)
    
    Returns PriceIntegrityResult with ok=True if valid, ok=False with violation_code if invalid.
    Logs structured PRICE_INTEGRITY_OK or PRICE_INTEGRITY_BLOCK marker.
    """
    now_utc = time.time()
    
    # Check for NaN/inf
    if not (math.isfinite(price.bid) and math.isfinite(price.ask) and math.isfinite(price.mid)):
        violation_code = "nan_or_inf"
        reason = f"Non-finite values: bid={price.bid}, ask={price.ask}, mid={price.mid}"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check bid > 0, ask > 0
    if price.bid <= 0 or price.ask <= 0:
        violation_code = "non_positive"
        reason = f"Non-positive price: bid={price.bid}, ask={price.ask}"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check price scale (reject extremely small prices)
    if price.mid < PRICE_MIN_VALUE:
        violation_code = "scale_error"
        reason = f"Price too small: mid={price.mid} < {PRICE_MIN_VALUE}"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check ask >= bid
    if price.ask < price.bid:
        violation_code = "ask_below_bid"
        reason = f"Ask below bid: bid={price.bid}, ask={price.ask}"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check mid = (bid+ask)/2 within epsilon
    expected_mid = (price.bid + price.ask) / 2.0
    mid_diff = abs(price.mid - expected_mid)
    if mid_diff > MID_EPSILON:
        violation_code = "mid_mismatch"
        reason = f"Mid mismatch: expected={expected_mid}, got={price.mid}, diff={mid_diff}"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'expected_mid': expected_mid, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check timestamp freshness
    age_sec = now_utc - price.ts_utc
    if age_sec > MAX_STALENESS_SEC:
        violation_code = "stale"
        reason = f"Stale price: age={age_sec:.2f}s > {MAX_STALENESS_SEC}s"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'age_sec': age_sec, 'max_age_sec': MAX_STALENESS_SEC, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # Check spread within limits
    spread_pct = (price.ask - price.bid) / price.mid if price.mid > 0 else float('inf')
    max_spread_pct = _get_max_spread_pct(price.instrument)
    if spread_pct > max_spread_pct:
        violation_code = "spread_too_wide"
        reason = f"Spread too wide: {spread_pct*100:.3f}% > {max_spread_pct*100:.3f}%"
        logger.warning(f"PRICE_INTEGRITY_BLOCK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'spread_pct': spread_pct, 'max_spread_pct': max_spread_pct, 'timestamp': price.ts_utc, 'violation_code': violation_code, 'source_path': source_path, 'reason': reason})}")
        return PriceIntegrityResult(ok=False, violation_code=violation_code, reason=reason)
    
    # All checks passed
    logger.debug(f"PRICE_INTEGRITY_OK {json.dumps({'instrument': price.instrument, 'bid': price.bid, 'ask': price.ask, 'mid': price.mid, 'timestamp': price.ts_utc, 'source_path': source_path})}")
    return PriceIntegrityResult(ok=True)


def get_latest_price(instrument: str, timeout_s: float = 7.0, validate: bool = True) -> Price:
    """Get latest price from OANDA and validate integrity.
    
    Args:
        instrument: Instrument symbol (e.g., "XAU_USD")
        timeout_s: Request timeout in seconds
        validate: If True, validate price integrity and raise PriceIntegrityError on failure
    
    Returns:
        Price object with validated data
    
    Raises:
        MarketDataError: On API errors
        PriceIntegrityError: On integrity validation failure (if validate=True)
    """
    account_id = _require("OANDA_ACCOUNT_ID")
    url = f"{_base_url()}/v3/accounts/{account_id}/pricing"
    params = {"instruments": instrument}
    r = requests.get(url, headers=_headers(), params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise MarketDataError(f"OANDA pricing error {r.status_code}: {r.text[:200]}")
    data = r.json()
    prices = data.get("prices") or []
    if not prices:
        raise MarketDataError(f"No price returned for {instrument}")
    p = prices[0]
    bids = p.get("bids") or []
    asks = p.get("asks") or []
    if not bids or not asks:
        raise MarketDataError(f"Malformed price payload for {instrument}")
    bid = float(bids[0]["price"])
    ask = float(asks[0]["price"])
    mid = (bid + ask) / 2.0
    price = Price(instrument=instrument, bid=bid, ask=ask, mid=mid, ts_utc=time.time())
    
    # Validate integrity (raises PriceIntegrityError on failure)
    if validate:
        integrity = validate_price_integrity(price, source_path="market_data_provider.get_latest_price")
        if not integrity.ok:
            raise PriceIntegrityError(f"Price integrity violation for {instrument}: {integrity.reason}")
    
    return price


def get_candles(
    instrument: str,
    granularity: str = "M5",
    count: int = 500,
    price: str = "M",
    timeout_s: float = 12.0,
) -> List[Candle]:
    url = f"{_base_url()}/v3/instruments/{instrument}/candles"
    params = {
        "granularity": granularity,
        "count": str(count),
        "price": price,
    }
    r = requests.get(url, headers=_headers(), params=params, timeout=timeout_s)
    if r.status_code != 200:
        raise MarketDataError(f"OANDA candles error {r.status_code}: {r.text[:200]}")
    data = r.json()
    out: List[Candle] = []
    for c in data.get("candles") or []:
        mid = c.get("mid") or {}
        out.append(
            Candle(
                time=str(c.get("time")),
                complete=bool(c.get("complete")),
                volume=int(c.get("volume") or 0),
                o=float(mid.get("o") or 0),
                h=float(mid.get("h") or 0),
                l=float(mid.get("l") or 0),
                c=float(mid.get("c") or 0),
            )
        )
    # Relaxed history requirement: allow if at least 10% of requested or 10 candles (whichever more)
    # but at most require 20 for basic analysis.
    min_required = min(20, max(10, count // 10))
    if len(out) < min_required:
        raise MarketDataError(f"Insufficient candle history for {instrument}: got {len(out)}, need {min_required}")
    return out
