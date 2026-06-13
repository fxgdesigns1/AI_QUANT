#!/usr/bin/env python3
"""
Phase 8Y: extend existing context-pack coverage to today.

What it does (in order):
  1. Detects the gap (last cached candle day -> today).
  2. Fetches only the gap candles from OANDA for each granularity.
  3. Merges + deduplicates (by 'time' key) into the existing JSONL.gz.
  4. Updates the candle cache manifest (sha256, row_count, coverage_end_*).
  5. Fetches only the gap news from Polygon.
  6. Merges + deduplicates (by url+title) into a new dated JSONL.gz.
  7. Updates the news cache manifest (upsert entry keyed to today's 90-day window).
  8. Re-runs the coverage inventory -> latest_phase8y_data_coverage_manifest.json.
  9. Re-builds the shared context pack -> latest_phase8y_shared_context_pack_manifest.json.
 10. Re-verifies all pack SHA256s -> latest_phase8y_context_pack_verification.json.
 11. Fails closed (exit 2) if verification does not pass.

Hard rules:
  - Never prints secret values.
  - Only OANDA read-only candle API + Polygon read-only news API are called.
  - No order / execution APIs touched.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

UTC = timezone.utc

# ── canonical paths (relative to repo_root, resolved later) ──────────────────
PERF = Path("ARTIFACTS") / "performance"
CACHE_DIR = PERF / "phase8y_context_cache"
CANDLE_DIR = CACHE_DIR / "candles"
NEWS_DIR = CACHE_DIR / "news"
CANDLE_MANIFEST = CACHE_DIR / "latest_phase8y_candle_cache_manifest.json"
NEWS_MANIFEST = CACHE_DIR / "latest_phase8y_news_cache_manifest.json"
COVERAGE_MANIFEST = PERF / "latest_phase8y_data_coverage_manifest.json"
PACK_MANIFEST = PERF / "latest_phase8y_shared_context_pack_manifest.json"
VERIFY_OUTPUT = PERF / "latest_phase8y_context_pack_verification.json"
PACK_DIR = PERF / "phase8y_shared_context_pack"
COST_ESTIMATE = PERF / "latest_phase8y_api_cost_estimate.json"

DEFAULT_ENV_FILE = Path(".env")
DEFAULT_SECRETS_ENV = Path(".secrets") / "phase8r_providers.env"


# ─────────────────────────── tiny utilities ──────────────────────────────────

def _iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _day(dt: datetime) -> str:
    return dt.astimezone(UTC).date().isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _load_jsonl_gz(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.is_file():
        return rows
    with gzip.open(path, "rt", encoding="utf-8") as gz:
        for line in gz:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and not row.get("placeholder"):
                rows.append(row)
    return rows


def _write_jsonl_gz(path: Path, rows: Sequence[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".jsonl.gz", dir=str(path.parent))
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as gz:
            for row in rows:
                gz.write(json.dumps(row, separators=(",", ":")) + "\n")
        tmp.replace(path)
        return int(path.stat().st_size)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _load_env(repo_root: Path, env_path: Path) -> None:
    p = env_path if env_path.is_absolute() else (repo_root / env_path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


# ─────────────────────────── candle helpers ──────────────────────────────────

def _candle_cache_path(repo_root: Path, instrument: str, granularity: str, lookback_days: int) -> Path:
    return (repo_root / CANDLE_DIR / f"phase8y_candles_{instrument}_{granularity.upper()}_{lookback_days}d.jsonl.gz").resolve()


def _candle_entry_for(manifest: Dict[str, Any], instrument: str, granularity: str, lookback_days: int) -> Optional[Dict[str, Any]]:
    for e in manifest.get("entries") or []:
        if (
            str(e.get("instrument") or "").upper() == instrument.upper()
            and str(e.get("granularity") or "").upper() == granularity.upper()
            and int(e.get("lookback_days") or 0) == int(lookback_days)
        ):
            return e
    return None


def _detect_candle_gap_start(entry: Optional[Dict[str, Any]]) -> str:
    """Return the day after last cached coverage — the first day we still need."""
    if entry:
        end_day = str(entry.get("coverage_end_day") or "")
        if end_day:
            last_dt = datetime.fromisoformat(end_day + "T00:00:00+00:00").astimezone(UTC)
            return (last_dt + timedelta(days=1)).date().isoformat()
    # No prior cache — fall back to 90 days ago.
    return (datetime.now(UTC) - timedelta(days=90)).date().isoformat()


def refresh_candles(
    *,
    repo_root: Path,
    instrument: str,
    granularities: List[str],
    lookback_days: int,
    gap_start_day: Optional[str],
    today: str,
    dry_run: bool,
) -> List[Dict[str, Any]]:
    from scripts.local_research.oanda_mid_historical_fetch import (
        fetch_oanda_mid_candles_range,
        parse_time_iso_utc,
    )

    manifest_path = (repo_root / CANDLE_MANIFEST).resolve()
    manifest = _read_json(manifest_path)
    manifest.setdefault("entries", [])

    results: List[Dict[str, Any]] = []
    for gran in granularities:
        g = gran.upper()
        entry = _candle_entry_for(manifest, instrument, g, lookback_days)
        gap_start = gap_start_day or _detect_candle_gap_start(entry)

        if gap_start > today:
            results.append({"granularity": g, "status": "already_current", "gap_start": gap_start, "today": today})
            continue

        fetch_start = datetime.fromisoformat(gap_start + "T00:00:00+00:00").astimezone(UTC)
        fetch_end = datetime.now(UTC)

        print(f"  [candles] {instrument} {g}: fetching {gap_start} -> {today} ...", flush=True)
        if dry_run:
            results.append({"granularity": g, "status": "dry_run", "would_fetch_from": gap_start, "would_fetch_to": today})
            continue

        new_rows = fetch_oanda_mid_candles_range(instrument, g, fetch_start, fetch_end)
        if not new_rows:
            results.append({"granularity": g, "status": "no_new_candles", "gap_start": gap_start})
            continue

        cache_path = _candle_cache_path(repo_root, instrument, g, lookback_days)
        existing = _load_jsonl_gz(cache_path)

        # Merge: deduplicate by 'time', keep all, sort ascending.
        seen_times: set = {str(r.get("time") or "") for r in existing}
        appended = 0
        for r in new_rows:
            t = str(r.get("time") or "")
            if t not in seen_times:
                existing.append(r)
                seen_times.add(t)
                appended += 1
        existing.sort(key=lambda r: str(r.get("time") or ""))

        size = _write_jsonl_gz(cache_path, existing)
        sha = _sha256(cache_path)
        t0 = parse_time_iso_utc(existing[0].get("time")) if existing else None
        t1 = parse_time_iso_utc(existing[-1].get("time")) if existing else None

        # Update the manifest entry in-place.
        updated_entry = dict(entry or {})
        updated_entry.update({
            "kind": "candles",
            "instrument": instrument.upper(),
            "granularity": g,
            "lookback_days": int(lookback_days),
            "coverage_start_utc": _iso_z(t0) if t0 else updated_entry.get("coverage_start_utc"),
            "coverage_start_day": _day(t0) if t0 else updated_entry.get("coverage_start_day"),
            "coverage_end_utc": _iso_z(t1) if t1 else updated_entry.get("coverage_end_utc"),
            "coverage_end_day": _day(t1) if t1 else updated_entry.get("coverage_end_day"),
            "required_end_utc": _iso_z(fetch_end),
            "required_end_day": today,
            "complete_for_required_window": True,
            "row_count": len(existing),
            "compressed_size_bytes": int(size),
            "sha256": sha,
            "path": str(cache_path),
            "saved_at_utc": _iso_z(datetime.now(UTC)),
        })

        manifest["entries"] = [
            e for e in manifest["entries"]
            if not (
                str(e.get("instrument") or "").upper() == instrument.upper()
                and str(e.get("granularity") or "").upper() == g
                and int(e.get("lookback_days") or 0) == int(lookback_days)
            )
        ] + [updated_entry]

        results.append({
            "granularity": g,
            "status": "refreshed",
            "prior_rows": len(existing) - appended,
            "appended_rows": appended,
            "total_rows": len(existing),
            "coverage_end_day": updated_entry["coverage_end_day"],
            "sha256": sha,
        })

    if not dry_run:
        manifest["generated_at_utc"] = _iso_z(datetime.now(UTC))
        manifest["phase"] = "Phase 8Y"
        manifest["classification"] = "PHASE8Y_CANDLE_CACHE_MANIFEST"
        manifest["cache_dir"] = str((repo_root / CANDLE_DIR).resolve())
        manifest["secrets_exposed"] = False
        manifest["paper_review_only"] = True
        manifest["ny_live_enabled"] = False
        manifest["execution_paths_changed"] = False
        _write_json(manifest_path, manifest)

    return results


# ─────────────────────────── news helpers ────────────────────────────────────

def _news_entry_for_window(manifest: Dict[str, Any], start_day: str, end_day: str) -> Optional[Dict[str, Any]]:
    for e in manifest.get("entries") or []:
        if (
            str(e.get("required_start_day") or "") == start_day
            and str(e.get("required_end_day") or "") == end_day
        ):
            return e
    return None


def _latest_news_entry(manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the entry with the most recent required_end_day."""
    entries = [e for e in (manifest.get("entries") or []) if isinstance(e, dict)]
    if not entries:
        return None
    return max(entries, key=lambda e: str(e.get("required_end_day") or ""))


def refresh_news(
    *,
    repo_root: Path,
    gap_start_day: str,
    today: str,
    window_start_day: str,  # start of the full 90-day window (for manifest keying)
    max_calls: int,
    limit: int,
    dry_run: bool,
) -> Dict[str, Any]:
    from scripts.phase8y_fetch_cache_news import fetch_polygon_window, coverage_bounds

    manifest_path = (repo_root / NEWS_MANIFEST).resolve()
    manifest = _read_json(manifest_path)
    manifest.setdefault("entries", [])

    latest_entry = _latest_news_entry(manifest)
    existing_path = Path(latest_entry.get("path") or "") if latest_entry else None

    if gap_start_day > today:
        return {"status": "already_current", "gap_start": gap_start_day, "today": today}

    print(f"  [news] Polygon: fetching {gap_start_day} -> {today} ...", flush=True)
    if dry_run:
        return {"status": "dry_run", "would_fetch_from": gap_start_day, "would_fetch_to": today}

    polygon_csv = (os.getenv("POLYGON_API_KEYS") or "").strip()
    polygon_keys = [k.strip() for k in polygon_csv.split(",") if k.strip()]
    if not polygon_keys:
        return {"status": "skipped_no_polygon_key", "gap_start": gap_start_day}

    new_rows, fetch_meta = fetch_polygon_window(
        api_keys=polygon_keys,
        start_day=gap_start_day,
        end_day=today,
        limit=min(1000, int(limit) if int(limit) > 0 else 500),
        max_calls=max(6, int(max_calls) * max(1, min(3, len(polygon_keys)))),
        timeout_s=20.0,
    )

    # Load existing rows from the most recent news file.
    existing: List[Dict[str, Any]] = []
    if existing_path and existing_path.is_file():
        existing = _load_jsonl_gz(existing_path)

    # Merge: deduplicate by url+title.
    seen: set = {f"{r.get('url','')}|{r.get('title','')}" for r in existing}
    appended = 0
    for r in new_rows:
        key = f"{r.get('url','')}|{r.get('title','')}"
        if key not in seen:
            existing.append(r)
            seen.add(key)
            appended += 1

    cov_start, cov_end = coverage_bounds(existing)
    complete = bool(
        cov_start is not None
        and cov_end is not None
        and cov_start <= window_start_day
        and cov_end >= today
    )

    out_name = f"phase8y_news_polygon_{window_start_day.replace('-','')}_{today.replace('-','')}.jsonl.gz"
    out_path = (repo_root / NEWS_DIR / out_name).resolve()
    size = _write_jsonl_gz(out_path, existing)
    sha = _sha256(out_path)

    new_entry = {
        "kind": "news",
        "provider": "polygon",
        "required_start_day": window_start_day,
        "required_end_day": today,
        "coverage_start_day": cov_start,
        "coverage_end_day": cov_end,
        "complete_for_required_window": complete,
        "row_count": len(existing),
        "compressed_size_bytes": int(size),
        "sha256": sha,
        "path": str(out_path),
        "fetch_meta": {"gap_fetch_start_day": gap_start_day, "gap_fetch_end_day": today, "provider_meta": fetch_meta},
        "saved_at_utc": _iso_z(datetime.now(UTC)),
    }

    # Replace any entry with the same window key; keep others.
    manifest["entries"] = [
        e for e in manifest["entries"]
        if not (
            str(e.get("required_start_day") or "") == window_start_day
            and str(e.get("required_end_day") or "") == today
        )
    ] + [new_entry]
    manifest["generated_at_utc"] = _iso_z(datetime.now(UTC))
    manifest["phase"] = "Phase 8Y"
    manifest["classification"] = "PHASE8Y_NEWS_CACHE_MANIFEST"
    manifest["cache_dir"] = str((repo_root / NEWS_DIR).resolve())
    manifest["secrets_exposed"] = False
    manifest["paper_review_only"] = True
    manifest["ny_live_enabled"] = False
    manifest["execution_paths_changed"] = False
    _write_json(manifest_path, manifest)

    return {
        "status": "refreshed",
        "prior_rows": len(existing) - appended,
        "appended_rows": appended,
        "total_rows": len(existing),
        "coverage_end_day": cov_end,
        "complete": complete,
        "out_file": out_name,
        "sha256": sha,
    }


# ─────────────────────────── rebuild + verify ────────────────────────────────

def rebuild_coverage(
    *,
    repo_root: Path,
    instrument: str,
    lookback_days: int,
    granularities: List[str],
) -> Dict[str, Any]:
    from scripts.phase8y_inventory_data_coverage import build_manifest as _build

    manifest = _build(
        repo_root=repo_root,
        instrument=instrument,
        lookback_days=lookback_days,
        granularities=granularities,
        max_paid_calendar_calls=0,
        require_news=False,
        require_calendar=False,
        require_macro=False,
    )
    out = (repo_root / COVERAGE_MANIFEST).resolve()
    _write_json(out, manifest)
    return manifest


def rebuild_pack(*, repo_root: Path) -> Dict[str, Any]:
    from scripts.phase8y_build_shared_context_pack import build_pack as _build

    coverage_path = (repo_root / COVERAGE_MANIFEST).resolve()
    cost_path = (repo_root / COST_ESTIMATE).resolve()
    output_dir = (repo_root / PACK_DIR).resolve()
    pack_manifest = _build(repo_root, output_dir=output_dir, coverage_path=coverage_path, cost_path=cost_path)
    manifest_out = (repo_root / PACK_MANIFEST).resolve()
    _write_json(manifest_out, pack_manifest)
    return pack_manifest


def verify_pack(*, repo_root: Path) -> Dict[str, Any]:
    from scripts.phase8y_verify_context_pack import verify as _verify

    manifest_path = (repo_root / PACK_MANIFEST).resolve()
    result = _verify(manifest_path)
    out = (repo_root / VERIFY_OUTPUT).resolve()
    _write_json(out, result)
    return result


# ─────────────────────────── orchestrator ────────────────────────────────────

def run_refresh(
    *,
    repo_root: Path,
    instrument: str,
    lookback_days: int,
    granularities: List[str],
    env_file: Path,
    secrets_env: Path,
    gap_start_day: Optional[str],
    news_max_calls: int,
    news_limit: int,
    dry_run: bool,
) -> Dict[str, Any]:
    today = datetime.now(UTC).date().isoformat()

    _load_env(repo_root, env_file)
    _load_env(repo_root, secrets_env)

    if not os.getenv("OANDA_API_KEY"):
        raise RuntimeError("OANDA_API_KEY not found in environment — cannot fetch candles")

    # ── 1-4: candles ─────────────────────────────────────────────────────────
    print(f"\n[Phase 8Y Refresh] Candles: {instrument} {granularities}, gap -> {today}", flush=True)
    candle_results = refresh_candles(
        repo_root=repo_root,
        instrument=instrument,
        granularities=granularities,
        lookback_days=lookback_days,
        gap_start_day=gap_start_day,
        today=today,
        dry_run=dry_run,
    )

    # ── 5-7: news ─────────────────────────────────────────────────────────────
    # Determine gap start from the candle manifest (now updated) or from param.
    candle_manifest = _read_json((repo_root / CANDLE_MANIFEST).resolve())
    m15_entry = _candle_entry_for(candle_manifest, instrument, "M15", lookback_days)
    # Use the day AFTER the previous coverage end as the news gap start.
    news_manifest = _read_json((repo_root / NEWS_MANIFEST).resolve())
    latest_news = _latest_news_entry(news_manifest)
    news_gap_start = gap_start_day
    if news_gap_start is None:
        if latest_news:
            last_covered = str(latest_news.get("coverage_end_day") or latest_news.get("required_end_day") or "")
            if last_covered:
                news_gap_start = (
                    datetime.fromisoformat(last_covered + "T00:00:00+00:00").astimezone(UTC)
                    + timedelta(days=1)
                ).date().isoformat()
        if not news_gap_start:
            news_gap_start = _detect_candle_gap_start(m15_entry)

    # The full window start (for manifest keying) = start of existing coverage or 90 days ago.
    existing_news_start = str((latest_news or {}).get("coverage_start_day") or "")
    if not existing_news_start:
        existing_news_start = (datetime.now(UTC) - timedelta(days=lookback_days)).date().isoformat()
    # Clamp: window start should cover at least `lookback_days` before today.
    ninety_ago = (datetime.now(UTC) - timedelta(days=lookback_days)).date().isoformat()
    window_start_day = min(existing_news_start, ninety_ago)

    print(f"\n[Phase 8Y Refresh] News: gap {news_gap_start} -> {today}, window {window_start_day} -> {today}", flush=True)
    news_result = refresh_news(
        repo_root=repo_root,
        gap_start_day=news_gap_start,
        today=today,
        window_start_day=window_start_day,
        max_calls=news_max_calls,
        limit=news_limit,
        dry_run=dry_run,
    )

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "today": today,
            "candle_results": candle_results,
            "news_result": news_result,
        }

    # ── 8: coverage inventory ─────────────────────────────────────────────────
    print("\n[Phase 8Y Refresh] Rebuilding coverage manifest ...", flush=True)
    coverage = rebuild_coverage(
        repo_root=repo_root,
        instrument=instrument,
        lookback_days=lookback_days,
        granularities=granularities,
    )

    # ── 9: context pack ───────────────────────────────────────────────────────
    print("[Phase 8Y Refresh] Rebuilding shared context pack ...", flush=True)
    rebuild_pack(repo_root=repo_root)

    # ── 10-11: verify (fail closed) ───────────────────────────────────────────
    print("[Phase 8Y Refresh] Verifying pack SHA256s ...", flush=True)
    verification = verify_pack(repo_root=repo_root)
    if not verification.get("all_files_verified"):
        failed = [c["file"] for c in (verification.get("checked_files") or []) if not c.get("ok")]
        raise RuntimeError(f"PACK_VERIFICATION_FAILED: {failed}")

    print("[Phase 8Y Refresh] All files verified. Done.\n", flush=True)
    return {
        "ok": True,
        "today": today,
        "candle_results": candle_results,
        "news_result": news_result,
        "coverage_exact_replay_possible": coverage.get("exact_replay_possible"),
        "coverage_safe_to_run_batch": coverage.get("safe_to_run_batch"),
        "verification_passed": True,
        "paper_review_only": True,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }


# ─────────────────────────── CLI ─────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Phase 8Y context-pack refresh: extend coverage to today.")
    p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    p.add_argument("--instrument", type=str, default="EUR_USD")
    p.add_argument("--lookback-days", type=int, default=90)
    p.add_argument("--granularities", nargs="*", default=["M15", "M5"])
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE,
                   help="Path to .env with OANDA_API_KEY.")
    p.add_argument("--secrets-env", type=Path, default=DEFAULT_SECRETS_ENV,
                   help="Path to secrets env with POLYGON_API_KEYS.")
    p.add_argument("--gap-start-day", type=str, default=None,
                   help="Override gap start (YYYY-MM-DD). Default: day after last cached candle.")
    p.add_argument("--news-max-calls", type=int, default=6)
    p.add_argument("--news-limit", type=int, default=500,
                   help="Max articles per Polygon pagination page.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print plan; do not fetch, write, or verify.")
    args = p.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    try:
        result = run_refresh(
            repo_root=repo_root,
            instrument=str(args.instrument).upper(),
            lookback_days=int(args.lookback_days),
            granularities=[str(g).upper() for g in args.granularities],
            env_file=args.env_file,
            secrets_env=args.secrets_env,
            gap_start_day=args.gap_start_day or None,
            news_max_calls=int(args.news_max_calls),
            news_limit=int(args.news_limit),
            dry_run=bool(args.dry_run),
        )
        print(json.dumps(result, indent=2))
        return 0
    except RuntimeError as exc:
        # RuntimeError includes our PACK_VERIFICATION_FAILED sentinel.
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
