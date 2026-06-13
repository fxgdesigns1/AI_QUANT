#!/usr/bin/env python3
"""
Phase 8Y: data coverage inventory + fail-closed batch safety decision.

Dry-run mode is read-only: this script never executes paid HTTP calls.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

UTC = timezone.utc
REPO_ROOT = Path(__file__).resolve().parents[1]
PERF_DIR = Path("ARTIFACTS") / "performance"
DEFAULT_OUTPUT = PERF_DIR / "latest_phase8y_data_coverage_manifest.json"
PHASE8Y_CACHE_DIR = PERF_DIR / "phase8y_context_cache"
PHASE8Y_CANDLE_MANIFEST = PHASE8Y_CACHE_DIR / "latest_phase8y_candle_cache_manifest.json"
PHASE8Y_NEWS_MANIFEST = PHASE8Y_CACHE_DIR / "latest_phase8y_news_cache_manifest.json"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _required_window(lookback_days: int) -> Tuple[datetime, datetime]:
    end = _utc_now()
    start = end - timedelta(days=max(1, int(lookback_days)))
    return start, end


def _window_complete(
    start: Optional[datetime],
    end: Optional[datetime],
    required_start: datetime,
    required_end: datetime,
) -> bool:
    if start is None or end is None:
        return False
    # permit a tiny tolerance around boundary timestamps
    return start <= (required_start + timedelta(minutes=5)) and end >= (required_end - timedelta(minutes=5))


def _extract_days_from_candle_name(name: str) -> Optional[int]:
    m = re.search(r"_(\d+)d(?:\.jsonl\.gz|\.json|\.jsonl)$", name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _phase8y_candle_cache_entry(
    repo_root: Path,
    *,
    instrument: str,
    granularity: str,
    lookback_days: int,
) -> Optional[Dict[str, Any]]:
    m = _read_json(repo_root / PHASE8Y_CANDLE_MANIFEST)
    for e in m.get("entries") or []:
        if not isinstance(e, dict):
            continue
        if str(e.get("kind") or "") != "candles":
            continue
        if str(e.get("instrument") or "").upper() != instrument.upper():
            continue
        if str(e.get("granularity") or "").upper() != granularity.upper():
            continue
        if int(e.get("lookback_days") or 0) != int(lookback_days):
            continue
        return e
    return None


def _phase8y_news_cache_entry(
    repo_root: Path,
    *,
    required_start_day: str,
    required_end_day: str,
) -> Optional[Dict[str, Any]]:
    m = _read_json(repo_root / PHASE8Y_NEWS_MANIFEST)
    for e in m.get("entries") or []:
        if not isinstance(e, dict):
            continue
        if str(e.get("kind") or "") != "news":
            continue
        if str(e.get("required_start_day") or "") != required_start_day:
            continue
        if str(e.get("required_end_day") or "") != required_end_day:
            continue
        return e
    return None


def _collect_candle_ranges(
    repo_root: Path,
    *,
    instrument: str,
    granularities: Sequence[str],
    required_start: datetime,
    required_end: datetime,
) -> Tuple[Dict[str, Any], bool, List[Dict[str, Any]]]:
    out: Dict[str, Any] = {}
    missing: List[Dict[str, Any]] = []
    all_complete = True
    perf_index = _read_json(repo_root / PERF_DIR / "research_results_index.json")
    rows = perf_index.get("rows") if isinstance(perf_index.get("rows"), list) else []

    # Optional explicit candle exports, if present.
    explicit_files = list(repo_root.glob(f"**/phase8o_candles_{instrument}_*.jsonl.gz"))
    explicit_files += list(repo_root.glob(f"**/phase8l_candles_{instrument}_*.jsonl.gz"))

    lookback_days = max(1, int((required_end - required_start).total_seconds() // 86400))
    for gran in granularities:
        g = gran.upper()
        start_candidates: List[datetime] = []
        end_candidates: List[datetime] = []
        sources: List[str] = []

        p8y_entry = _phase8y_candle_cache_entry(
            repo_root,
            instrument=instrument,
            granularity=g,
            lookback_days=lookback_days,
        )
        if isinstance(p8y_entry, dict):
            cs = _parse_iso(p8y_entry.get("coverage_start_utc"))
            ce = _parse_iso(p8y_entry.get("coverage_end_utc"))
            if cs is not None:
                start_candidates.append(cs)
            if ce is not None:
                end_candidates.append(ce)
            sources.append("phase8y_context_cache.candle_manifest")

        for r in rows:
            if not isinstance(r, Mapping):
                continue
            if str(r.get("instrument") or "").upper() != instrument.upper():
                continue
            if str(r.get("granularity") or "").upper() != g:
                continue
            dt = _parse_iso(r.get("generated_at_utc"))
            if dt is None:
                continue
            start_candidates.append(dt)
            end_candidates.append(dt)
            sources.append("research_results_index.generated_at_utc")

        for p in explicit_files:
            if f"_{g}_" not in p.name.upper():
                continue
            days = _extract_days_from_candle_name(p.name) or 0
            if days <= 0:
                continue
            end = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
            start = end - timedelta(days=days)
            start_candidates.append(start)
            end_candidates.append(end)
            sources.append(str(p.relative_to(repo_root)))

        have_start = min(start_candidates) if start_candidates else None
        have_end = max(end_candidates) if end_candidates else None
        # Day-window based completeness (phase8y cache manifests are day-based).
        req_start_day = required_start.date().isoformat()
        req_end_day = required_end.date().isoformat()
        have_start_day = have_start.date().isoformat() if have_start else None
        have_end_day = have_end.date().isoformat() if have_end else None
        complete = bool(have_start_day and have_end_day and have_start_day <= req_start_day and have_end_day >= req_end_day)
        all_complete = all_complete and complete

        if not complete:
            missing.append(
                {
                    "kind": "candles",
                    "instrument": instrument,
                    "granularity": g,
                    "required_start_day": required_start.date().isoformat(),
                    "required_end_day": required_end.date().isoformat(),
                    "coverage_start_day": have_start.date().isoformat() if have_start else None,
                    "coverage_end_day": have_end.date().isoformat() if have_end else None,
                    "reason": "missing_or_incomplete_candle_window",
                }
            )

        out[g] = {
            "coverage_start_utc": _iso_z(have_start) if have_start else None,
            "coverage_end_utc": _iso_z(have_end) if have_end else None,
            "required_start_utc": _iso_z(required_start),
            "required_end_utc": _iso_z(required_end),
            "complete_for_required_window": complete,
            "evidence_sources": sorted(set(sources)),
        }

    return {instrument: out}, all_complete, missing


def _provider_map_with_window(
    providers: Sequence[str],
    *,
    start_day: Optional[str],
    end_day: Optional[str],
    rows_count: int,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for p in providers:
        out[str(p)] = {
            "date_window_start_day": start_day,
            "date_window_end_day": end_day,
            "rows_count": int(rows_count),
            "covered": bool(rows_count > 0 and start_day and end_day),
        }
    return out


def _month_stats(repo_root: Path) -> Tuple[int, int, int]:
    usage = _read_json(repo_root / PERF_DIR / "latest_calendar_api_usage_report.json")
    used = int(usage.get("calendar_calls_this_month") or 0)
    remaining = int(usage.get("calendar_budget_remaining") or 0)
    hits = int(usage.get("calendar_cache_hits_month") or 0)
    return used, remaining, hits


@dataclass
class CoverageDecision:
    safe_to_run_batch: bool
    fail_reasons: List[str]
    exact_replay_possible: bool


def _decide(
    *,
    candles_complete: bool,
    news_complete: bool,
    calendar_complete: bool,
    macro_complete: bool,
    require_news: bool,
    require_calendar: bool,
    require_macro: bool,
    estimated_paid_calendar_calls_needed: int,
    max_paid_calendar_calls: int,
    monthly_calendar_calls_remaining: int,
    provider_credentials_missing: Sequence[str],
) -> CoverageDecision:
    fail_reasons: List[str] = []
    if not candles_complete:
        fail_reasons.append("missing_candles")
    if require_calendar and not calendar_complete:
        fail_reasons.append("missing_calendar_for_exact_replay")
    if require_news and not news_complete:
        fail_reasons.append("missing_news_for_exact_replay")
    if require_macro and not macro_complete:
        fail_reasons.append("missing_macro_for_exact_replay")
    if provider_credentials_missing:
        fail_reasons.append("provider_credentials_missing")
    if estimated_paid_calendar_calls_needed > max_paid_calendar_calls:
        fail_reasons.append("estimated_calls_exceed_budget")
    if estimated_paid_calendar_calls_needed > monthly_calendar_calls_remaining:
        fail_reasons.append("monthly_calendar_budget_exhausted")
    exact_replay_possible = (
        candles_complete
        and (calendar_complete or not require_calendar)
        and (news_complete or not require_news)
        and (macro_complete or not require_macro)
        and not provider_credentials_missing
    )
    return CoverageDecision(
        safe_to_run_batch=len(fail_reasons) == 0,
        fail_reasons=fail_reasons,
        exact_replay_possible=exact_replay_possible,
    )


def build_manifest(
    *,
    repo_root: Path,
    instrument: str,
    lookback_days: int,
    granularities: Sequence[str],
    max_paid_calendar_calls: int,
    require_news: bool,
    require_calendar: bool,
    require_macro: bool,
) -> Dict[str, Any]:
    required_start, required_end = _required_window(lookback_days)
    required_start_day = required_start.date().isoformat()
    required_end_day = required_end.date().isoformat()
    aligned = _read_json(repo_root / PERF_DIR / "latest_phase8r_aligned_context_manifest.json")
    provider = _read_json(repo_root / PERF_DIR / "latest_phase8r_provider_capability_report.json")
    news_diag = _read_json(repo_root / PERF_DIR / "latest_phase8o_news_provider_diagnostics.json")
    verify = _read_json(repo_root / PERF_DIR / "latest_phase8y_context_pack_verification.json")

    candle_ranges, candles_complete, missing = _collect_candle_ranges(
        repo_root,
        instrument=instrument,
        granularities=granularities,
        required_start=required_start,
        required_end=required_end,
    )

    aligned_start = aligned.get("aligned_window_start_day") or provider.get("date_window_start_day")
    aligned_end = aligned.get("aligned_window_end_day") or provider.get("date_window_end_day")
    p8y_news = _phase8y_news_cache_entry(repo_root, required_start_day=required_start_day, required_end_day=required_end_day)
    news_rows = int((p8y_news or {}).get("row_count") or aligned.get("news_rows_count") or news_diag.get("news_rows_count") or 0)
    cal_rows = int(aligned.get("calendar_rows_count") or news_diag.get("calendar_rows_count") or 0)
    macro_rows = int(provider.get("fred_rows_count") or 0)

    working_news = list(provider.get("working_news_providers") or [])
    if not working_news and news_rows > 0:
        working_news = ["news_context_cache"]
    working_cal = list(provider.get("working_calendar_providers") or [])
    if not working_cal and cal_rows > 0:
        working_cal = ["calendar_context_cache"]
    working_macro = list(provider.get("working_macro_providers") or [])
    if not working_macro and macro_rows > 0:
        working_macro = ["fred"]

    news_start_day = (p8y_news or {}).get("coverage_start_day") or aligned_start
    news_end_day = (p8y_news or {}).get("coverage_end_day") or aligned_end
    news_provider_label = (p8y_news or {}).get("provider") or None
    if news_provider_label and news_provider_label not in working_news:
        working_news = [str(news_provider_label)]
    news_map = _provider_map_with_window(working_news, start_day=news_start_day, end_day=news_end_day, rows_count=news_rows)
    cal_map = _provider_map_with_window(
        working_cal,
        start_day=aligned_start,
        end_day=aligned_end,
        rows_count=cal_rows,
    )
    macro_map = _provider_map_with_window(
        working_macro,
        start_day=aligned_start,
        end_day=aligned_end,
        rows_count=macro_rows,
    )

    news_complete = bool(
        news_rows > 0
        and news_map
        and isinstance(news_start_day, str)
        and isinstance(news_end_day, str)
        and news_start_day <= required_start_day
        and news_end_day >= required_end_day
    )
    calendar_complete = bool(cal_rows > 0 and cal_map)
    macro_complete = bool(macro_rows > 0 and macro_map)
    if require_news and not news_complete:
        missing.append(
            {
                "kind": "news",
                "required_start_day": required_start.date().isoformat(),
                "required_end_day": required_end.date().isoformat(),
                "coverage_start_day": aligned_start,
                "coverage_end_day": aligned_end,
                "reason": "news_context_missing_or_empty",
            }
        )
    if require_calendar and not calendar_complete:
        missing.append(
            {
                "kind": "calendar",
                "required_start_day": required_start.date().isoformat(),
                "required_end_day": required_end.date().isoformat(),
                "coverage_start_day": aligned_start,
                "coverage_end_day": aligned_end,
                "reason": "calendar_context_missing_or_empty",
            }
        )
    if require_macro and not macro_complete:
        missing.append(
            {
                "kind": "macro",
                "required_start_day": required_start.date().isoformat(),
                "required_end_day": required_end.date().isoformat(),
                "coverage_start_day": aligned_start,
                "coverage_end_day": aligned_end,
                "reason": "macro_context_missing_or_empty",
            }
        )

    env_presence = provider.get("provider_env_presence") if isinstance(provider.get("provider_env_presence"), dict) else {}
    provider_credentials_missing: List[str] = []
    if require_news and not bool(
        env_presence.get("MARKETAUX_API_KEYS")
        or env_presence.get("POLYGON_API_KEYS")
        or env_presence.get("ALPHAVANTAGE_API_KEYS")
        or env_presence.get("NEWSAPI_API_KEYS")
        or env_presence.get("NEWSAPI_API_KEY")
    ):
        provider_credentials_missing.append("news_provider_missing")
    if require_calendar and not bool(env_presence.get("FMP_API_KEYS") or env_presence.get("TRADINGECONOMICS_API_KEYS")):
        provider_credentials_missing.append("calendar_fallback")
    if require_macro and not bool(env_presence.get("FRED_API_KEYS")):
        provider_credentials_missing.append("fred")

    used, remaining, cache_hits = _month_stats(repo_root)
    estimated_paid_calendar_calls_needed = 0 if calendar_complete else 1
    estimated_api_calls_needed = estimated_paid_calendar_calls_needed + (0 if news_complete else 1) + (0 if macro_complete or not require_macro else 1)
    context_pack_verified = bool(verify.get("ok") is True and verify.get("all_files_verified") is True)

    decision = _decide(
        candles_complete=candles_complete,
        news_complete=news_complete,
        calendar_complete=calendar_complete,
        macro_complete=macro_complete,
        require_news=require_news,
        require_calendar=require_calendar,
        require_macro=require_macro,
        estimated_paid_calendar_calls_needed=estimated_paid_calendar_calls_needed,
        max_paid_calendar_calls=max_paid_calendar_calls,
        monthly_calendar_calls_remaining=remaining,
        provider_credentials_missing=provider_credentials_missing,
    )

    return {
        "generated_at_utc": _iso_z(_utc_now()),
        "phase": "Phase 8Y",
        "classification": "PHASE8Y_DATA_COVERAGE_MANIFEST",
        "instrument": instrument,
        "lookback_days": int(lookback_days),
        "required_window_start_day": required_start_day,
        "required_window_end_day": required_end_day,
        "candles_by_instrument_granularity_date_range": candle_ranges,
        "news_by_provider_date_range": news_map,
        "calendar_by_provider_date_range": cal_map,
        "macro_by_provider_series_date_range": macro_map,
        "cache_hits": {
            "monthly_calendar_cache_hits": int(cache_hits),
            "calendar_cache_manifest_entries": len((_read_json(repo_root / PERF_DIR / "latest_calendar_cache_manifest.json").get("entries") or [])),
        },
        "missing_windows": missing,
        "exact_replay_possible": decision.exact_replay_possible,
        "estimated_api_calls_needed": int(estimated_api_calls_needed),
        "estimated_paid_calendar_calls_needed": int(estimated_paid_calendar_calls_needed),
        "monthly_calendar_calls_used": int(used),
        "monthly_calendar_calls_remaining": int(remaining),
        "max_paid_calendar_calls_budget_for_preflight": int(max_paid_calendar_calls),
        "provider_credentials_missing": provider_credentials_missing,
        "shared_context_pack_verified": context_pack_verified,
        "safe_to_run_batch": decision.safe_to_run_batch,
        "fail_closed_reasons": decision.fail_reasons,
        "paper_review_only": True,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8Y data coverage inventory (no paid calls).")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--granularities", nargs="*", default=["M15", "M5"])
    parser.add_argument("--max-paid-calendar-calls", type=int, default=1)
    parser.add_argument("--require-news", action="store_true", default=False)
    parser.add_argument("--require-calendar", action="store_true", default=False)
    parser.add_argument("--require-macro", action="store_true", default=False)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    output = args.output if args.output.is_absolute() else (repo_root / args.output)
    manifest = build_manifest(
        repo_root=repo_root,
        instrument=str(args.instrument).upper(),
        lookback_days=int(args.lookback_days),
        granularities=[str(g).upper() for g in args.granularities],
        max_paid_calendar_calls=int(args.max_paid_calendar_calls),
        require_news=bool(args.require_news),
        require_calendar=bool(args.require_calendar),
        require_macro=bool(args.require_macro),
    )
    if not args.dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": bool(args.dry_run),
                "output": str(output),
                "safe_to_run_batch": manifest.get("safe_to_run_batch"),
                "exact_replay_possible": manifest.get("exact_replay_possible"),
                "estimated_paid_calendar_calls_needed": manifest.get("estimated_paid_calendar_calls_needed"),
                "missing_windows": len(manifest.get("missing_windows") or []),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
