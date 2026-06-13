#!/usr/bin/env python3
"""
Phase 8Y: fetch+cache OANDA mid candles once per (instrument, granularity, window).

Writes:
- ARTIFACTS/performance/phase8y_context_cache/candles/*.jsonl.gz
- ARTIFACTS/performance/phase8y_context_cache/latest_phase8y_candle_cache_manifest.json

No broker order APIs; read-only historical candles only.
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
from typing import Any, Dict, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
UTC = timezone.utc

PERF = Path("ARTIFACTS") / "performance"
CACHE_DIR = PERF / "phase8y_context_cache"
CANDLE_DIR = CACHE_DIR / "candles"
MANIFEST_PATH = CACHE_DIR / "latest_phase8y_candle_cache_manifest.json"
DEFAULT_ENV_FILE = Path(".env")


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _day(dt: datetime) -> str:
    return dt.astimezone(UTC).date().isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _required_window(lookback_days: int) -> Tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(days=max(1, int(lookback_days)))
    return start, end


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_env_file(repo_root: Path, env_path: Path) -> Dict[str, bool]:
    """Load KEY=VALUE lines into os.environ if missing. Returns presence map by key name (no values)."""
    p = env_path if env_path.is_absolute() else (repo_root / env_path)
    present: Dict[str, bool] = {}
    if not p.is_file():
        return present
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        present[k] = bool(v)
        if k not in os.environ and v:
            os.environ[k] = v
    return present


def _cache_path(instrument: str, granularity: str, lookback_days: int) -> Path:
    return CANDLE_DIR / f"phase8y_candles_{instrument}_{granularity.upper()}_{int(lookback_days)}d.jsonl.gz"


def _already_cached(meta: Dict[str, Any], instrument: str, granularity: str, lookback_days: int) -> bool:
    for e in meta.get("entries") or []:
        if (
            str(e.get("instrument") or "").upper() == instrument.upper()
            and str(e.get("granularity") or "").upper() == granularity.upper()
            and int(e.get("lookback_days") or 0) == int(lookback_days)
            and bool(e.get("complete_for_required_window"))
        ):
            p = Path(e.get("path") or "")
            if p.is_file() and str(e.get("sha256") or "") == _sha256_file(p):
                return True
    return False


def fetch_and_cache(
    *,
    repo_root: Path,
    instrument: str,
    granularity: str,
    lookback_days: int,
    force: bool,
    env_file: Path,
) -> Dict[str, Any]:
    from scripts.local_research.oanda_mid_historical_fetch import (  # noqa: E402
        fetch_oanda_mid_candles_range,
        parse_time_iso_utc,
    )

    repo_root = repo_root.expanduser().resolve()
    cache_root = (repo_root / CACHE_DIR).resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    _load_env_file(repo_root, env_file)

    manifest_path = (repo_root / MANIFEST_PATH).resolve()
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    manifest.setdefault("entries", [])

    if not force and _already_cached(manifest, instrument, granularity, lookback_days):
        return {"ok": True, "cache_hit": True, "instrument": instrument, "granularity": granularity.upper()}

    if not os.getenv("OANDA_API_KEY"):
        raise RuntimeError("Missing OANDA_API_KEY in environment")

    start, end = _required_window(lookback_days)
    rows = fetch_oanda_mid_candles_range(instrument, granularity.upper(), start, end)
    if not rows:
        raise RuntimeError(f"NO_CANDLES_FETCHED:{instrument}:{granularity}")

    out_path = (repo_root / _cache_path(instrument, granularity, lookback_days)).resolve()
    size = _write_jsonl_gz(out_path, rows)
    sha = _sha256_file(out_path)
    t0 = parse_time_iso_utc(rows[0].get("time"))
    t1 = parse_time_iso_utc(rows[-1].get("time"))
    # Phase 8Y coverage is day-window based (not "to-the-second now"). We still record UTC timestamps.
    complete = bool(t0 and t1 and (_day(t0) <= start.date().isoformat()) and (_day(t1) >= end.date().isoformat()))

    entry = {
        "kind": "candles",
        "instrument": instrument.upper(),
        "granularity": granularity.upper(),
        "lookback_days": int(lookback_days),
        "coverage_start_utc": _iso_z(t0) if t0 else None,
        "coverage_end_utc": _iso_z(t1) if t1 else None,
        "coverage_start_day": _day(t0) if t0 else None,
        "coverage_end_day": _day(t1) if t1 else None,
        "required_start_utc": _iso_z(start),
        "required_end_utc": _iso_z(end),
        "required_start_day": start.date().isoformat(),
        "required_end_day": end.date().isoformat(),
        "complete_for_required_window": complete,
        "row_count": len(rows),
        "compressed_size_bytes": int(size),
        "sha256": sha,
        "path": str(out_path),
        "saved_at_utc": _iso_z(datetime.now(UTC)),
    }
    manifest["generated_at_utc"] = _iso_z(datetime.now(UTC))
    manifest["phase"] = "Phase 8Y"
    manifest["classification"] = "PHASE8Y_CANDLE_CACHE_MANIFEST"
    manifest["cache_dir"] = str((repo_root / CANDLE_DIR).resolve())
    manifest["entries"] = [e for e in (manifest.get("entries") or []) if not (
        str(e.get("instrument") or "").upper() == entry["instrument"]
        and str(e.get("granularity") or "").upper() == entry["granularity"]
        and int(e.get("lookback_days") or 0) == entry["lookback_days"]
    )] + [entry]
    manifest["secrets_exposed"] = False
    manifest["paper_review_only"] = True
    manifest["ny_live_enabled"] = False
    manifest["execution_paths_changed"] = False

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"ok": True, "cache_hit": False, "entry": entry, "manifest": str(manifest_path)}


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 8Y candle cache fetcher (OANDA mid).")
    p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    p.add_argument("--instrument", type=str, default="EUR_USD")
    p.add_argument("--lookback-days", type=int, default=90)
    p.add_argument("--granularities", nargs="*", default=["M15", "M5"])
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    instrument = str(args.instrument).upper()
    lookback = int(args.lookback_days)
    granularities = [str(g).upper() for g in args.granularities]
    results: List[Dict[str, Any]] = []
    for g in granularities:
        results.append(
            fetch_and_cache(
                repo_root=repo_root,
                instrument=instrument,
                granularity=g,
                lookback_days=lookback,
                force=bool(args.force),
                env_file=args.env_file,
            )
        )
    print(json.dumps({"ok": True, "results": results, "manifest": str((repo_root / MANIFEST_PATH).resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

