#!/usr/bin/env python3
"""
Probe Step 4: News Embargo Probe
Check if news embargo incorrectly blocked trading.

Supports two modes:
  --static-w23   Use hardcoded W23 calendar (2-6 Jun 2026) — no API call needed.
                 Pass a signal timestamp to check embargo status for that moment.
  (default)      Live mode: query the registered news providers.
"""
import sys
import os
import argparse
import logging
import time
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_news_embargo")


def probe_embargo_live():
    from src.control_plane.news_provider import fetch_news_with_registry

    logger.info("Probing news embargo status (live providers)...")
    try:
        query = "gold OR inflation OR cpi OR fed OR rate"
        logger.info(f"Querying news: {query}")
        items, status = fetch_news_with_registry(query=query, threshold="high", max_items=20)
        logger.info(f"Fetched {len(items)} high-impact items. Providers: {status.get('providers_used')}")

        now = time.time()
        embargo_window_seconds = 7200

        active = []
        for item in items:
            age = now - item['ts_utc']
            if abs(age) < embargo_window_seconds:
                active.append(item)

        if active:
            logger.info("EMBARGO SHOULD BE ACTIVE: High impact news found within window.")
            for item in active:
                logger.info(f" - {item['title']} ({item['impact']}) Age: {int(now - item['ts_utc'])}s")
        else:
            logger.info("NO EMBARGO: No high impact news in window.")
    except Exception as e:
        logger.error(f"Probe failed: {e}")


def probe_embargo_static_w23(signal_ts_str: str, instrument: str, side: str):
    """Check a single signal against the hardcoded W23 calendar."""
    from w23_signal_forensics import cross_reference_signal, W23_CALENDAR

    try:
        ts = datetime.strptime(signal_ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error(f"Bad timestamp format (expected YYYY-MM-DD HH:MM:SS): {signal_ts_str}")
        return

    logger.info(f"W23 static probe: {instrument} {side} @ {signal_ts_str}")
    logger.info(f"Calendar has {len(W23_CALENDAR)} events")

    result = cross_reference_signal(ts, instrument, side)
    status = result["status"]

    if status == "EMBARGO_HIT":
        logger.warning(f"EMBARGO_HIT  Direction alignment: {result['direction']}")
        for h in result["hits"]:
            logger.warning(
                f"  Event : {h['event']}  ({h['impact']})  "
                f"window=+/-{h['embargo_minutes']}m  "
                f"delta={h['seconds_from_event']:+.0f}s"
            )
    else:
        logger.info("CLEAR — signal is outside all W23 embargo windows.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--static-w23", action="store_true",
                    help="Use hardcoded W23 calendar instead of live API")
    ap.add_argument("--ts", default=None,
                    help="Signal timestamp UTC (YYYY-MM-DD HH:MM:SS) for --static-w23 mode")
    ap.add_argument("--instrument", default="EUR_USD")
    ap.add_argument("--side", default="BUY")
    args = ap.parse_args()

    if args.static_w23:
        ts = args.ts or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        probe_embargo_static_w23(ts, args.instrument, args.side)
    else:
        probe_embargo_live()
