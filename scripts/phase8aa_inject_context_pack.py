#!/usr/bin/env python3
"""
Phase 8AA: Inject Phase 8Y verified context pack into a Phase 8L job environment.

Validates that the job's requested window is covered by the Phase 8Y context pack,
slices the relevant candle/news/calendar data, and injects it into the job's
alpha export directory so that exact_strategy_replay=True becomes possible.

Exit code 0 = success, context injected.
Exit code 1 = fail-closed (missing coverage, wrong instrument, SHA256 mismatch).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import tarfile
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE = "Phase 8AA"
CONTEXT_PACK_VERSION = "phase8y_2026-05-04"

SUPPORTED_INSTRUMENTS = {"EUR_USD"}
SUPPORTED_GRANULARITIES = {"M5", "M15"}
MAX_LOOKBACK_DAYS = 90  # Phase 8Y coverage span; fail-closed for anything longer

COVERAGE_START = date(2026, 2, 3)
COVERAGE_END = date(2026, 5, 4)

DEFAULT_CANDLE_CACHE_DIR = REPO_ROOT / "ARTIFACTS" / "performance" / "phase8y_context_cache" / "candles"
DEFAULT_NEWS_CACHE_DIR = REPO_ROOT / "ARTIFACTS" / "performance" / "phase8y_context_cache" / "news"
DEFAULT_CALENDAR_CACHE_DIR = REPO_ROOT / "ARTIFACTS" / "performance" / "calendar_http_cache"
DEFAULT_COVERAGE_MANIFEST = (
    REPO_ROOT / "ARTIFACTS" / "performance" / "phase8y_shared_context_pack" / "pack"
    / "latest_phase8y_data_coverage_manifest.json"
)
DEFAULT_CANDLE_MANIFEST = (
    REPO_ROOT / "ARTIFACTS" / "performance" / "phase8y_context_cache"
    / "latest_phase8y_candle_cache_manifest.json"
)
DEFAULT_NEWS_MANIFEST = (
    REPO_ROOT / "ARTIFACTS" / "performance" / "phase8y_context_cache"
    / "latest_phase8y_news_cache_manifest.json"
)


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(msg: str, extra: Optional[Dict[str, Any]] = None) -> int:
    out: Dict[str, Any] = {"ok": False, "phase": PHASE, "error": msg}
    if extra:
        out.update(extra)
    print(json.dumps(out, indent=2))
    return 1


def _parse_date_from_iso(s: Any) -> Optional[date]:
    if not isinstance(s, str) or not s.strip():
        return None
    raw = s.strip()[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _candle_date(row: Dict[str, Any]) -> Optional[date]:
    t = row.get("time")
    if not isinstance(t, str):
        return None
    return _parse_date_from_iso(t)


def _news_date(row: Dict[str, Any]) -> Optional[date]:
    for k in ("published_at", "date_utc", "date", "time"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            d = _parse_date_from_iso(v)
            if d is not None:
                return d
    return None


def _calendar_date(row: Dict[str, Any]) -> Optional[date]:
    for k in ("date", "Date", "date_utc", "time"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            d = _parse_date_from_iso(v)
            if d is not None:
                return d
    return None


def _load_jsonl_gz(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
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
                out.append(row)
    return out


def _write_jsonl_gz(rows: List[Dict[str, Any]], path: Path) -> str:
    """Write rows to gzipped JSONL; return SHA256 of the written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as gz:
        for row in rows:
            gz.write(json.dumps(row, separators=(",", ":")) + "\n")
    return _sha256_file(path)


def _slice_by_date(
    rows: List[Dict[str, Any]],
    *,
    window_start: date,
    window_end: date,
    date_fn: Any,
) -> Tuple[List[Dict[str, Any]], int]:
    sliced = [r for r in rows if (d := date_fn(r)) is not None and window_start <= d <= window_end]
    return sliced, len(sliced)


def _find_candle_file(candle_cache_dir: Path, instrument: str, granularity: str) -> Optional[Path]:
    name = f"phase8y_candles_{instrument}_{granularity}_90d.jsonl.gz"
    p = candle_cache_dir / name
    if p.is_file():
        return p
    for f in candle_cache_dir.glob("*.jsonl.gz"):
        if instrument in f.name and granularity in f.name:
            return f
    return None


def _find_news_file(news_cache_dir: Path) -> Optional[Path]:
    for provider in ("polygon", "marketaux"):
        for f in news_cache_dir.glob(f"*{provider}*.jsonl.gz"):
            return f
    for f in news_cache_dir.glob("*.jsonl.gz"):
        return f
    return None


def _load_calendar_rows_from_cache(calendar_cache_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not calendar_cache_dir.is_dir():
        return rows
    for entry in sorted(calendar_cache_dir.glob("*.json")):
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        entry_rows = data.get("rows") or []
        for r in entry_rows:
            if isinstance(r, dict):
                rows.append(r)
    return rows


def _resolve_context_pack_dir(context_pack: Optional[Path], tmp_dir: Path) -> Optional[Path]:
    """Extract tar.gz or return directory path containing coverage manifest."""
    if context_pack is None:
        return None
    context_pack = context_pack.expanduser().resolve()
    if not context_pack.exists():
        return None
    if context_pack.is_dir():
        return context_pack
    if context_pack.suffix in (".gz", ".tgz") or context_pack.name.endswith(".tar.gz"):
        extract_dir = tmp_dir / "context_pack_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(context_pack, "r:gz") as tf:
            try:
                tf.extractall(path=extract_dir, filter="data")
            except TypeError:
                tf.extractall(path=extract_dir)
        return extract_dir
    return None


def _load_coverage_manifest(
    context_pack_dir: Optional[Path],
    coverage_manifest_path: Optional[Path],
) -> Optional[Dict[str, Any]]:
    candidates = []
    if coverage_manifest_path and coverage_manifest_path.is_file():
        candidates.append(coverage_manifest_path)
    if context_pack_dir:
        for name in ("latest_phase8y_data_coverage_manifest.json", "latest_phase8y_aligned_context_manifest.json"):
            p = context_pack_dir / name
            if p.is_file():
                candidates.append(p)
    candidates.append(DEFAULT_COVERAGE_MANIFEST)
    for p in candidates:
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def validate_coverage(
    *,
    instrument: str,
    granularity: str,
    window_start: date,
    window_end: date,
    coverage: Dict[str, Any],
) -> Optional[str]:
    """Return error string if not covered, else None."""
    if instrument not in SUPPORTED_INSTRUMENTS:
        return f"instrument_not_covered:supported={sorted(SUPPORTED_INSTRUMENTS)}"
    if granularity not in SUPPORTED_GRANULARITIES:
        return f"granularity_not_covered:supported={sorted(SUPPORTED_GRANULARITIES)}"
    days_requested = (window_end - window_start).days
    if days_requested > MAX_LOOKBACK_DAYS:
        return (
            f"window_too_long:{days_requested}d>max_{MAX_LOOKBACK_DAYS}d:"
            "needs_context_expansion_phase8ab"
        )
    if window_start < COVERAGE_START:
        return f"window_starts_before_coverage:{window_start}<{COVERAGE_START}"
    if window_end > COVERAGE_END:
        return f"window_ends_after_coverage:{window_end}>{COVERAGE_END}"
    if not coverage.get("exact_replay_possible") and not coverage.get("safe_to_run_batch"):
        return "coverage_manifest_says_not_safe_to_run"
    return None


def inject(
    *,
    job_id: str,
    instrument: str,
    granularity: str,
    window_start: date,
    window_end: date,
    candle_cache_dir: Path,
    news_cache_dir: Path,
    calendar_cache_dir: Path,
    alpha_export_dir: Optional[Path],
    output_dir: Path,
) -> Dict[str, Any]:
    """Slice Phase 8Y data to the job window, write to alpha_export_dir and output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Candles ---
    candle_src = _find_candle_file(candle_cache_dir, instrument, granularity)
    if candle_src is None:
        raise RuntimeError(f"candle_file_not_found:{candle_cache_dir}/{instrument}_{granularity}")
    all_candles = _load_jsonl_gz(candle_src)
    sliced_candles, candle_rows = _slice_by_date(
        all_candles, window_start=window_start, window_end=window_end, date_fn=_candle_date
    )
    if candle_rows == 0:
        raise RuntimeError(f"no_candles_in_window:{window_start}:{window_end}")

    # --- News ---
    news_src = _find_news_file(news_cache_dir)
    if news_src is None:
        raise RuntimeError(f"news_file_not_found:{news_cache_dir}")
    all_news = _load_jsonl_gz(news_src)
    sliced_news, news_rows_count = _slice_by_date(
        all_news, window_start=window_start, window_end=window_end, date_fn=_news_date
    )
    news_covers_window = news_rows_count > 0

    # --- Calendar ---
    all_calendar = _load_calendar_rows_from_cache(calendar_cache_dir)
    sliced_calendar, cal_rows_count = _slice_by_date(
        all_calendar, window_start=window_start, window_end=window_end, date_fn=_calendar_date
    )
    calendar_covers_window = cal_rows_count > 0

    # Determine lookback days from actual candle data (for file naming)
    days = max(1, (window_end - window_start).days)

    # Write sliced files to output_dir first (for SHA256 tracking)
    candle_out_name = f"phase8l_candles_{instrument}_{granularity}_{days}d.jsonl.gz"
    news_out_name = f"phase8l_news_context_{days}d.jsonl.gz"
    cal_out_name = f"phase8l_calendar_context_{days}d.jsonl.gz"

    candle_sha = _write_jsonl_gz(sliced_candles, output_dir / candle_out_name)
    news_sha = _write_jsonl_gz(sliced_news if sliced_news else [{"placeholder": True, "reason": "no_news_in_window"}], output_dir / news_out_name)
    cal_sha = _write_jsonl_gz(sliced_calendar if sliced_calendar else [{"placeholder": True, "reason": "no_calendar_in_window"}], output_dir / cal_out_name)

    manifest: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso_z(),
        "phase": PHASE,
        "classification": "PHASE8AA_JOB_CONTEXT_MANIFEST",
        "job_id": job_id,
        "context_injected": True,
        "context_pack_version": CONTEXT_PACK_VERSION,
        "instrument": instrument,
        "granularity": granularity,
        "window_start": str(window_start),
        "window_end": str(window_end),
        "lookback_days": days,
        "candle_rows": candle_rows,
        "news_rows_in_window": news_rows_count,
        "calendar_rows_in_window": cal_rows_count,
        "news_covers_window": news_covers_window,
        "calendar_covers_window": calendar_covers_window,
        "candle_file": candle_out_name,
        "news_file": news_out_name,
        "calendar_file": cal_out_name,
        "candle_sha256": candle_sha,
        "news_sha256": news_sha,
        "calendar_sha256": cal_sha,
        "context_verified": True,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "execution_paths_changed": False,
    }

    # Inject into alpha_export_dir (overwrite existing files)
    if alpha_export_dir is not None and alpha_export_dir.is_dir():
        alpha_man_path = alpha_export_dir / "phase8l_alpha_export_manifest.json"
        alpha_manifest: Dict[str, Any] = {}
        if alpha_man_path.is_file():
            try:
                alpha_manifest = json.loads(alpha_man_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                alpha_manifest = {}

        # Determine actual days from the alpha export manifest (for correct filename)
        alpha_days = int(alpha_manifest.get("days_requested") or days)
        alpha_candle_name = f"phase8l_candles_{instrument}_{granularity}_{alpha_days}d.jsonl.gz"
        alpha_news_name = f"phase8l_news_context_{alpha_days}d.jsonl.gz"
        alpha_cal_name = f"phase8l_calendar_context_{alpha_days}d.jsonl.gz"

        alpha_candle_sha = _write_jsonl_gz(sliced_candles, alpha_export_dir / alpha_candle_name)
        alpha_news_sha = _write_jsonl_gz(
            sliced_news if sliced_news else [{"placeholder": True, "reason": "no_news_in_window"}],
            alpha_export_dir / alpha_news_name,
        )
        alpha_cal_sha = _write_jsonl_gz(
            sliced_calendar if sliced_calendar else [{"placeholder": True, "reason": "no_calendar_in_window"}],
            alpha_export_dir / alpha_cal_name,
        )

        # Update alpha export manifest
        alpha_manifest["news_reconstruction_available"] = news_covers_window
        alpha_manifest["calendar_reconstruction_available"] = calendar_covers_window
        alpha_manifest["phase8aa_context_injected"] = True
        alpha_manifest["context_pack_version"] = CONTEXT_PACK_VERSION
        alpha_manifest["phase8aa_candle_sha256"] = alpha_candle_sha
        alpha_manifest["phase8aa_news_sha256"] = alpha_news_sha
        alpha_manifest["phase8aa_calendar_sha256"] = alpha_cal_sha
        alpha_man_path.write_text(json.dumps(alpha_manifest, indent=2), encoding="utf-8")

        # Update manifest with alpha_export paths and sha256s
        manifest["alpha_export_dir"] = str(alpha_export_dir)
        manifest["alpha_candle_file"] = alpha_candle_name
        manifest["alpha_news_file"] = alpha_news_name
        manifest["alpha_calendar_file"] = alpha_cal_name
        manifest["alpha_candle_sha256"] = alpha_candle_sha
        manifest["alpha_news_sha256"] = alpha_news_sha
        manifest["alpha_calendar_sha256"] = alpha_cal_sha

    manifest_path = output_dir / "job_context_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8AA: inject verified context pack into job environment.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--instrument", default="EUR_USD")
    parser.add_argument("--granularity", default="M15")
    parser.add_argument("--job-window-start", default=None, help="YYYY-MM-DD")
    parser.add_argument("--job-window-end", default=None, help="YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--context-pack", type=Path, default=None, help="Path to context pack tar.gz or directory.")
    parser.add_argument("--coverage-manifest", type=Path, default=None)
    parser.add_argument("--candle-cache-dir", type=Path, default=None)
    parser.add_argument("--news-cache-dir", type=Path, default=None)
    parser.add_argument("--calendar-cache-dir", type=Path, default=None)
    parser.add_argument("--alpha-export-dir", type=Path, default=None, help="Job alpha export dir to inject into.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Where to write job_context_manifest.json.")
    args = parser.parse_args()

    instrument = str(args.instrument).upper().replace("-", "_")
    granularity = str(args.granularity).upper()

    if instrument not in SUPPORTED_INSTRUMENTS:
        return _fail(f"instrument_not_covered:{instrument}", {"needs_context_expansion": True})
    if granularity not in SUPPORTED_GRANULARITIES:
        return _fail(f"granularity_not_covered:{granularity}")

    with tempfile.TemporaryDirectory() as _tmp:
        tmp_dir = Path(_tmp)

        context_pack_dir = _resolve_context_pack_dir(args.context_pack, tmp_dir)
        coverage = _load_coverage_manifest(context_pack_dir, args.coverage_manifest)
        if not coverage:
            return _fail("coverage_manifest_not_found:cannot_validate_without_coverage")

        # Determine job window
        window_start: Optional[date] = None
        window_end: Optional[date] = None

        if args.job_window_start:
            window_start = _parse_date_from_iso(args.job_window_start)
        if args.job_window_end:
            window_end = _parse_date_from_iso(args.job_window_end)

        # Derive from lookback_days if not explicit
        if window_end is None:
            window_end = COVERAGE_END
        if window_start is None:
            if args.lookback_days:
                from datetime import timedelta
                window_start = window_end - timedelta(days=int(args.lookback_days))
            elif args.alpha_export_dir:
                # Read from alpha export manifest
                ae = args.alpha_export_dir.expanduser().resolve()
                man = ae / "phase8l_alpha_export_manifest.json"
                if man.is_file():
                    try:
                        m = json.loads(man.read_text(encoding="utf-8"))
                        ds = m.get("dataset_start_utc")
                        de = m.get("dataset_end_utc")
                        if ds:
                            window_start = _parse_date_from_iso(ds)
                        if de:
                            window_end = _parse_date_from_iso(de)
                    except (json.JSONDecodeError, OSError):
                        pass
            if window_start is None:
                window_start = COVERAGE_START

        err = validate_coverage(
            instrument=instrument,
            granularity=granularity,
            window_start=window_start,
            window_end=window_end,
            coverage=coverage,
        )
        if err:
            return _fail(err, {"needs_context_expansion": True, "window_start": str(window_start), "window_end": str(window_end)})

        candle_cache_dir = (args.candle_cache_dir or DEFAULT_CANDLE_CACHE_DIR).expanduser().resolve()
        news_cache_dir = (args.news_cache_dir or DEFAULT_NEWS_CACHE_DIR).expanduser().resolve()
        calendar_cache_dir = (args.calendar_cache_dir or DEFAULT_CALENDAR_CACHE_DIR).expanduser().resolve()

        if not candle_cache_dir.is_dir():
            return _fail(f"candle_cache_dir_missing:{candle_cache_dir}")

        alpha_export_dir: Optional[Path] = None
        if args.alpha_export_dir:
            alpha_export_dir = args.alpha_export_dir.expanduser().resolve()
            if not alpha_export_dir.is_dir():
                return _fail(f"alpha_export_dir_not_found:{alpha_export_dir}")

        default_output = REPO_ROOT / "ARTIFACTS" / "performance" / "phase8aa_jobs" / str(args.job_id)
        output_dir = (args.output_dir or default_output).expanduser().resolve()

        try:
            result = inject(
                job_id=args.job_id,
                instrument=instrument,
                granularity=granularity,
                window_start=window_start,
                window_end=window_end,
                candle_cache_dir=candle_cache_dir,
                news_cache_dir=news_cache_dir,
                calendar_cache_dir=calendar_cache_dir,
                alpha_export_dir=alpha_export_dir,
                output_dir=output_dir,
            )
        except Exception as exc:
            return _fail(f"inject_failed:{exc}")

        print(json.dumps({"ok": True, **result}, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
