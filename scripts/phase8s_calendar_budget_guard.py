#!/usr/bin/env python3
"""
Phase 8S: global monthly ledger + hard budget for paid calendar HTTP calls.

No secrets are written to the ledger or reports (only provider ids + fingerprints).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

UTC = timezone.utc

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]

LEDGER_REL = Path("ARTIFACTS") / "performance" / "calendar_api_usage_ledger.jsonl"
USAGE_REPORT_REL = Path("ARTIFACTS") / "performance" / "latest_calendar_api_usage_report.json"
CACHE_MANIFEST_REL = Path("ARTIFACTS") / "performance" / "latest_calendar_cache_manifest.json"

MONTHLY_PLAN_CALLS = 1000
SOFT_WARNING_CALLS = 650
SAFE_TARGET_CALLS = 750
HARD_STOP_CALLS = 850
ABSOLUTE_STOP_CALLS = 900


def _month_key(ts: Optional[datetime] = None) -> str:
    d = ts or datetime.now(UTC)
    return d.strftime("%Y-%m")


def ledger_path(repo_root: Path) -> Path:
    return (repo_root / LEDGER_REL).resolve()


def usage_report_path(repo_root: Path) -> Path:
    return (repo_root / USAGE_REPORT_REL).resolve()


def cache_manifest_path(repo_root: Path) -> Path:
    return (repo_root / CACHE_MANIFEST_REL).resolve()


def request_fingerprint(provider: str, d1: str, d2: str, countries: str = "") -> str:
    raw = f"{provider}|{d1}|{d2}|{countries}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def iter_ledger_events(repo_root: Path) -> Iterator[Dict[str, Any]]:
    p = ledger_path(repo_root)
    if not p.is_file():
        return
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def count_month_stats(repo_root: Path, month: Optional[str] = None) -> Dict[str, Any]:
    mk = month or _month_key()
    paid_calls = 0
    blocked = 0
    cache_hits = 0
    by_provider: Dict[str, int] = {}
    last_call_ts: Optional[str] = None
    for ev in iter_ledger_events(repo_root):
        if ev.get("month_key") != mk:
            continue
        kind = ev.get("event") or ""
        prov = str(ev.get("provider") or "unknown")
        if kind == "paid_calendar_call":
            paid_calls += 1
            by_provider[prov] = by_provider.get(prov, 0) + 1
            ts = ev.get("ts_utc")
            if isinstance(ts, str):
                last_call_ts = ts
        elif kind == "budget_blocked":
            blocked += 1
        elif kind == "calendar_cache_hit":
            cache_hits += 1
    total_events = paid_calls + blocked + cache_hits
    hit_rate = (cache_hits / total_events) if total_events else 0.0
    return {
        "month_key": mk,
        "paid_calendar_calls": paid_calls,
        "budget_blocked_events": blocked,
        "calendar_cache_hits": cache_hits,
        "cache_hit_rate": round(hit_rate, 4),
        "by_provider": by_provider,
        "last_paid_call_ts_utc": last_call_ts,
    }


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    paid_calls_this_month: int


def evaluate_budget(repo_root: Path, *, month: Optional[str] = None) -> BudgetDecision:
    stats = count_month_stats(repo_root, month)
    n = int(stats["paid_calendar_calls"])
    if n >= ABSOLUTE_STOP_CALLS:
        return BudgetDecision(False, "absolute_stop_exceeded", n)
    if n >= HARD_STOP_CALLS:
        return BudgetDecision(False, "hard_stop_exceeded", n)
    return BudgetDecision(True, "within_budget", n)


def append_ledger(repo_root: Path, event: Dict[str, Any]) -> None:
    p = ledger_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts_utc", datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    event.setdefault("month_key", _month_key())
    line = json.dumps(event, separators=(",", ":")) + "\n"
    with open(p, "a", encoding="utf-8") as f:
        f.write(line)


def write_usage_report(repo_root: Path) -> Path:
    stats = count_month_stats(repo_root)
    dec = evaluate_budget(repo_root)
    remaining = max(0, MONTHLY_PLAN_CALLS - stats["paid_calendar_calls"])
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": "Phase 8S",
        "classification": "CALENDAR_API_USAGE_REPORT",
        "month_key": stats["month_key"],
        "calendar_calls_this_month": stats["paid_calendar_calls"],
        "calendar_budget_remaining": remaining,
        "calendar_budget_monthly_cap": MONTHLY_PLAN_CALLS,
        "calendar_cache_hit_rate": stats["cache_hit_rate"],
        "calendar_cache_hits_month": stats["calendar_cache_hits"],
        "budget_blocked_events_month": stats["budget_blocked_events"],
        "last_calendar_api_call_utc": stats["last_paid_call_ts_utc"],
        "budget_soft_warning_at": SOFT_WARNING_CALLS,
        "budget_hard_stop_at": HARD_STOP_CALLS,
        "budget_absolute_stop_at": ABSOLUTE_STOP_CALLS,
        "next_paid_call_allowed": dec.allowed,
        "budget_decision_reason": dec.reason,
        "providers_usage_counts": stats["by_provider"],
        "secrets_exposed": False,
        "paper_review_only": True,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    out = usage_report_path(repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def write_cache_manifest(repo_root: Path, cache_dir: Path, entries: List[Dict[str, Any]]) -> Path:
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": "Phase 8S",
        "classification": "CALENDAR_CACHE_MANIFEST",
        "cache_dir": str(cache_dir.resolve()),
        "entries": entries,
        "cache_ttl_days_policy": 365,
        "secrets_exposed": False,
    }
    out = cache_manifest_path(repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def dry_run_plan(
    *,
    repo_root: Path,
    provider: str,
    countries: str,
    date_from: str,
    date_to: str,
    max_api_calls: int,
) -> Dict[str, Any]:
    fp = request_fingerprint(provider, date_from, date_to, countries)
    stats = count_month_stats(repo_root)
    dec = evaluate_budget(repo_root)
    would_allow = dec.allowed and max_api_calls > 0
    return {
        "phase": "Phase 8S",
        "classification": "DRY_RUN_PLAN",
        "provider": provider,
        "request_fingerprint": fp,
        "countries": countries,
        "from": date_from,
        "to": date_to,
        "max_api_calls_requested": max_api_calls,
        "paid_calls_this_month": stats["paid_calendar_calls"],
        "would_allow_next_call": would_allow,
        "budget_reason": dec.reason,
        "month_key": stats["month_key"],
    }


def write_master_final_report(repo_root: Path) -> Path:
    """Write artifacts/PHASE8S_MASTER_FINAL_REPORT_<UTC stamp>.json (no secrets)."""
    repo_root = repo_root.expanduser().resolve()
    rep_path = usage_report_path(repo_root)
    usage: Dict[str, Any] = {}
    if rep_path.is_file():
        try:
            usage = json.loads(rep_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            usage = {}
    led = ledger_path(repo_root)
    man = cache_manifest_path(repo_root)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = repo_root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"PHASE8S_MASTER_FINAL_REPORT_{stamp}.json"
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": "Phase 8S-MASTER",
        "classification": "PHASE8S_MASTER_FINAL",
        "calendar_usage_report_path": str(rep_path) if rep_path.is_file() else None,
        "ledger_present": led.is_file(),
        "cache_manifest_present": man.is_file(),
        "usage_snapshot": usage,
        "expected_outcomes": {
            "global_calendar_cost_control": True,
            "monthly_budget_guard_enabled": True,
            "cache_layer_present": True,
        },
        "secrets_exposed": False,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8S calendar budget guard / usage report.")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--write-report-only", action="store_true")
    parser.add_argument("--write-master-final-report", action="store_true", help="Write artifacts/PHASE8S_MASTER_FINAL_REPORT_*.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--provider", type=str, default="rapidapi_economic_calendar")
    parser.add_argument("--countries", type=str, default="US,GB,EU")
    parser.add_argument("--from", dest="date_from", type=str, default="2026-04-01")
    parser.add_argument("--to", dest="date_to", type=str, default="2026-05-01")
    parser.add_argument("--max-api-calls", type=int, default=1)
    args = parser.parse_args()
    root = args.repo_root.expanduser().resolve()

    if args.write_report_only:
        p = write_usage_report(root)
        print(json.dumps({"ok": True, "report": str(p)}, indent=2))
        return 0

    if args.write_master_final_report:
        write_usage_report(root)
        p = write_master_final_report(root)
        print(json.dumps({"ok": True, "master_report": str(p)}, indent=2))
        return 0

    if args.dry_run:
        plan = dry_run_plan(
            repo_root=root,
            provider=args.provider,
            countries=args.countries,
            date_from=args.date_from,
            date_to=args.date_to,
            max_api_calls=int(args.max_api_calls),
        )
        print(json.dumps(plan, indent=2))
        return 0

    write_usage_report(root)
    print(json.dumps({"ok": True, "report": str(usage_report_path(root))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
