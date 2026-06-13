#!/usr/bin/env python3
"""
Phase 8Y: estimate API calls/cost from coverage manifest (no network calls).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
PERF_DIR = Path("ARTIFACTS") / "performance"
DEFAULT_MANIFEST = PERF_DIR / "latest_phase8y_data_coverage_manifest.json"
DEFAULT_OUTPUT = PERF_DIR / "latest_phase8y_api_cost_estimate.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def estimate_cost(manifest: Dict[str, Any], *, max_paid_calendar_calls: int) -> Dict[str, Any]:
    safe_by_coverage = bool(manifest.get("safe_to_run_batch"))
    paid_calendar_needed = int(manifest.get("estimated_paid_calendar_calls_needed") or 0)
    total_calls_needed = int(manifest.get("estimated_api_calls_needed") or 0)
    monthly_remaining = int(manifest.get("monthly_calendar_calls_remaining") or 0)

    provider_estimates = {
        "rapidapi_calendar": {
            "strategy": "Pull once per country-set/date-window and reuse cache for all jobs",
            "estimated_calls": paid_calendar_needed,
            "max_calls_per_preflight": 1,
            "countries": "US,GB,EU",
        },
        "newsapi": {
            "strategy": "pageSize=100; page only until target coverage met; cache by query/window",
            "estimated_calls": 0 if (manifest.get("news_by_provider_date_range") or {}) else 1,
        },
        "marketaux": {
            "strategy": "Use plan max limit; stop when returned rows < limit",
            "estimated_calls": 0,
        },
        "alphavantage": {
            "strategy": "NEWS_SENTIMENT limit=1000; broad FX buckets",
            "estimated_calls": 0,
        },
        "polygon": {
            "strategy": "limit=1000 + pagination where available",
            "estimated_calls": 0,
        },
        "fred": {
            "strategy": "Pull once per macro series/date-window and cache",
            "estimated_calls": 0 if (manifest.get("macro_by_provider_series_date_range") or {}) else 1,
        },
        "fmp": {
            "strategy": "Fallback calendar/economic source only when primary fails",
            "estimated_calls": 0 if paid_calendar_needed == 0 else 1,
        },
    }
    within_budget = paid_calendar_needed <= int(max_paid_calendar_calls) and paid_calendar_needed <= monthly_remaining
    safe = bool(safe_by_coverage and within_budget)

    return {
        "generated_at_utc": _iso_now(),
        "phase": "Phase 8Y",
        "classification": "PHASE8Y_API_COST_ESTIMATE",
        "estimated_api_calls_needed": total_calls_needed,
        "estimated_paid_calendar_calls_needed": paid_calendar_needed,
        "max_paid_calendar_calls_budget_for_preflight": int(max_paid_calendar_calls),
        "monthly_calendar_calls_used": int(manifest.get("monthly_calendar_calls_used") or 0),
        "monthly_calendar_calls_remaining": monthly_remaining,
        "estimated_paid_calls_within_budget": within_budget,
        "provider_estimates": provider_estimates,
        "recommended_batching": {
            "cache_first": True,
            "shared_context_pack_required": True,
            "do_not_call_news_or_calendar_per_job": True,
            "rapidapi_calendar_prefetch_max_calls": 1,
        },
        "safe_to_run_batch": safe,
        "fail_closed_reasons": [] if safe else ["estimated_calls_exceed_budget_or_preflight_manifest_blocked"],
        "paper_review_only": True,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8Y API call/cost estimator.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-paid-calendar-calls", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else (repo_root / args.manifest)
    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    manifest = _read_json(manifest_path)
    if not manifest:
        print(json.dumps({"ok": False, "error": "missing_or_invalid_manifest", "manifest": str(manifest_path)}, indent=2))
        return 1
    payload = estimate_cost(manifest, max_paid_calendar_calls=int(args.max_paid_calendar_calls))
    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": bool(args.dry_run),
                "output": str(output_path),
                "safe_to_run_batch": payload.get("safe_to_run_batch"),
                "estimated_paid_calendar_calls_needed": payload.get("estimated_paid_calendar_calls_needed"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
