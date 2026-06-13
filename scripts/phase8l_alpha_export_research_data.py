#!/usr/bin/env python3
"""
FXG Phase 8L: ALPHA-side research data export (read-only).

- OANDA historical mid candles only (no orders, positions, or execution APIs).
- Optional economic calendar / news context via environment keys (read-only HTTP).
- Credentials only from environment (e.g. source /etc/ai-quant/.env before invoke).
- Writes compressed JSONL + unified manifest + checksums; never writes secrets.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import socket
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.oanda_mid_historical_fetch import (  # noqa: E402
    estimate_gzip_compressed_bytes_heuristic,
    estimate_jsonl_raw_bytes,
    expected_candle_count_full_clock,
    fetch_oanda_mid_candles_range,
    oanda_headers_from_env,
    parse_time_iso_utc,
)
from scripts.local_research.phase8l_news_calendar_fetch import (  # noqa: E402
    fetch_finnhub_calendar_rows,
    fetch_newsapi_forex_rows,
    fetch_tradingeconomics_calendar_rows,
    resolve_finnhub_key,
    resolve_newsapi_key,
    resolve_trading_economics_key,
)

UTC = timezone.utc
PHASE = "Phase 8L"
CLASSIFICATION = "ALPHA_RESEARCH_EXPORT_ONLY"


def _utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
        sz = int(tmp.stat().st_size)
        tmp.replace(path)
        return sz
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _export_candles_single(
    *,
    instrument: str,
    granularity: str,
    days: int,
    output: Path,
    max_export_size_bytes: int,
) -> Dict[str, Any]:
    t_end = datetime.now(UTC)
    t_start = t_end - timedelta(days=days)
    creds = bool(os.getenv("OANDA_API_KEY"))
    if not creds:
        raise RuntimeError("Missing OANDA_API_KEY in environment")
    _ = oanda_headers_from_env()
    candles = fetch_oanda_mid_candles_range(
        instrument,
        granularity.upper(),
        t_start,
        t_end,
    )
    if not candles:
        raise RuntimeError(f"NO_CANDLES_FETCHED:{instrument}:{granularity}")

    output = output.expanduser().resolve()
    fd, tmp_path = tempfile.mkstemp(suffix=".jsonl.gz", dir=str(output.parent))
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as gz:
            for c in candles:
                gz.write(json.dumps(c, separators=(",", ":")) + "\n")
        sz = int(tmp.stat().st_size)
        if sz > max_export_size_bytes:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"EXPORT_SIZE_REFUSED:{instrument}:{granularity}:bytes={sz}>{max_export_size_bytes}"
            )
        digest = hashlib.sha256()
        with open(tmp, "rb") as bf:
            for chunk in iter(lambda: bf.read(1024 * 1024), b""):
                digest.update(chunk)
        sha = digest.hexdigest()
        tmp.replace(output)
        t_first = parse_time_iso_utc(candles[0].get("time"))
        t_last = parse_time_iso_utc(candles[-1].get("time"))
        return {
            "file": output.name,
            "path": str(output),
            "instrument": instrument,
            "granularity": granularity.upper(),
            "candle_count": len(candles),
            "compressed_size_bytes": sz,
            "sha256": sha,
            "dataset_start_utc": t_first.isoformat().replace("+00:00", "Z") if t_first else None,
            "dataset_end_utc": t_last.isoformat().replace("+00:00", "Z") if t_last else None,
        }
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def build_dry_run_plan(
    *,
    instruments: Sequence[str],
    granularities: Sequence[str],
    days: int,
    output_dir: Path,
    max_export_size_bytes: int,
    credentials_present: bool,
) -> Dict[str, Any]:
    per_combo: List[Dict[str, Any]] = []
    total_est = 0
    for ins in instruments:
        for gran in granularities:
            n = expected_candle_count_full_clock(days, gran)
            raw_est = estimate_jsonl_raw_bytes(n)
            gz_est = estimate_gzip_compressed_bytes_heuristic(raw_est)
            total_est += gz_est
            out_name = f"phase8l_candles_{ins}_{gran.upper()}_{days}d.jsonl.gz"
            per_combo.append(
                {
                    "instrument": ins,
                    "granularity": gran.upper(),
                    "expected_candle_count_approx": n,
                    "estimated_compressed_bytes_heuristic": gz_est,
                    "output_file": out_name,
                }
            )
    news_rows_est = 200 * 400
    cal_rows_est = 500 * 350
    total_est += estimate_gzip_compressed_bytes_heuristic(news_rows_est)
    total_est += estimate_gzip_compressed_bytes_heuristic(cal_rows_est)
    total_est += 50_000

    return {
        "phase": PHASE,
        "mode": "dry_run_plan",
        "output_dir": str(output_dir),
        "days_requested": days,
        "instruments": list(instruments),
        "granularities": [g.upper() for g in granularities],
        "per_instrument_granularity": per_combo,
        "estimated_total_compressed_bytes_heuristic": total_est,
        "max_export_size_bytes": max_export_size_bytes,
        "preflight_compressed_estimate_fits": total_est <= max_export_size_bytes,
        "oanda_credentials_from_env": credentials_present,
        "would_refuse_preflight": total_est > max_export_size_bytes,
    }


def run_export(
    *,
    days: int,
    instruments: Sequence[str],
    granularities: Sequence[str],
    output_dir: Path,
    max_export_size_bytes: int,
    dry_run_plan: bool,
    write_export: bool,
    max_context_rows: int,
) -> Dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    creds_oanda = bool(os.getenv("OANDA_API_KEY"))
    te_key, _ = resolve_trading_economics_key()
    fin_key, _ = resolve_finnhub_key()
    newsapi_key, _ = resolve_newsapi_key()

    if dry_run_plan:
        plan = build_dry_run_plan(
            instruments=instruments,
            granularities=granularities,
            days=days,
            output_dir=output_dir,
            max_export_size_bytes=max_export_size_bytes,
            credentials_present=creds_oanda,
        )
        return {"dry_run_plan": plan}

    if not write_export:
        return {"ok": False, "error": "use --write-export or --dry-run-plan"}

    plan = build_dry_run_plan(
        instruments=instruments,
        granularities=granularities,
        days=days,
        output_dir=output_dir,
        max_export_size_bytes=max_export_size_bytes,
        credentials_present=creds_oanda,
    )
    if plan.get("would_refuse_preflight"):
        raise RuntimeError(
            "EXPORT_PREFLIGHT_REFUSED:"
            f"{plan.get('estimated_total_compressed_bytes_heuristic')}>"
            f"{max_export_size_bytes}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    t_end = datetime.now(UTC)
    t_start = t_end - timedelta(days=days)
    d1 = t_start.strftime("%Y-%m-%d")
    d2 = t_end.strftime("%Y-%m-%d")

    candle_exports: List[Dict[str, Any]] = []
    candle_counts: Dict[str, int] = {}
    sha_by_file: Dict[str, str] = {}
    total_compressed = 0
    ds_start: Optional[str] = None
    ds_end: Optional[str] = None

    for ins in instruments:
        for gran in granularities:
            fname = f"phase8l_candles_{ins}_{gran.upper()}_{days}d.jsonl.gz"
            out_p = output_dir / fname
            info = _export_candles_single(
                instrument=ins,
                granularity=gran,
                days=days,
                output=out_p,
                max_export_size_bytes=max_export_size_bytes,
            )
            candle_exports.append(info)
            key = f"{ins}_{gran.upper()}"
            candle_counts[key] = int(info["candle_count"])
            sha_by_file[fname] = str(info["sha256"])
            total_compressed += int(info["compressed_size_bytes"])
            if info.get("dataset_start_utc"):
                ds_start = ds_start or info["dataset_start_utc"]
            if info.get("dataset_end_utc"):
                ds_end = info["dataset_end_utc"]

    cal_rows: List[Dict[str, Any]] = []
    if te_key:
        te_cal, _ = fetch_tradingeconomics_calendar_rows(
            api_key=te_key, d1=d1, d2=d2, max_rows=max_context_rows
        )
        cal_rows.extend(te_cal)
    if fin_key:
        fh_cal, _ = fetch_finnhub_calendar_rows(
            api_key=fin_key, d1=d1, d2=d2, max_rows=max_context_rows
        )
        cal_rows.extend(fh_cal)
    calendar_available = bool(cal_rows)
    cal_path = output_dir / f"phase8l_calendar_context_{days}d.jsonl.gz"
    cal_sz = _write_jsonl_gz(cal_path, cal_rows[:max_context_rows] if cal_rows else [{"placeholder": True, "reason": "no_calendar_rows"}])
    total_compressed += cal_sz
    sha_by_file[cal_path.name] = _sha256_file(cal_path)

    news_rows: List[Dict[str, Any]] = []
    if newsapi_key:
        news_rows, _ = fetch_newsapi_forex_rows(
            api_key=newsapi_key,
            from_day=d1,
            to_day=d2,
            max_items=max_context_rows,
        )
    news_available = bool(news_rows)
    news_path = output_dir / f"phase8l_news_context_{days}d.jsonl.gz"
    news_sz = _write_jsonl_gz(
        news_path,
        news_rows[:max_context_rows] if news_rows else [{"placeholder": True, "reason": "no_news_rows"}],
    )
    total_compressed += news_sz
    sha_by_file[news_path.name] = _sha256_file(news_path)

    export_files = [c["file"] for c in candle_exports] + [news_path.name, cal_path.name]

    manifest: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso_z(),
        "source_host": socket.gethostname(),
        "phase": PHASE,
        "classification": CLASSIFICATION,
        "days_requested": days,
        "instruments": list(instruments),
        "granularities": [g.upper() for g in granularities],
        "export_files": export_files,
        "candle_counts": candle_counts,
        "dataset_start_utc": ds_start,
        "dataset_end_utc": ds_end,
        "news_reconstruction_available": news_available,
        "calendar_reconstruction_available": calendar_available,
        "secret_fields_written": False,
        "order_or_execution_apis_called": False,
        "compressed_size_bytes": total_compressed,
        "max_export_size_mb": round(max_export_size_bytes / (1024 * 1024), 4),
        "sha256_by_file": sha_by_file,
        "alpha_cleanup_required": True,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "candle_exports": candle_exports,
    }

    man_path = output_dir / "phase8l_alpha_export_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sha_by_file["phase8l_alpha_export_manifest.json"] = _sha256_file(man_path)
    total_compressed += int(man_path.stat().st_size)

    if total_compressed > max_export_size_bytes:
        raise RuntimeError(
            f"EXPORT_TOTAL_SIZE_REFUSED:bytes={total_compressed}>{max_export_size_bytes}"
        )

    lines = [f"{sha_by_file[n]}  {n}" for n in sorted(sha_by_file.keys())]
    chk = output_dir / "checksums.sha256"
    chk.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"ok": True, "manifest": str(man_path), "compressed_size_bytes": total_compressed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8L ALPHA research export (read-only).")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--instruments", type=str, default="EUR_USD", help="Comma-separated OANDA instruments.")
    parser.add_argument("--granularities", type=str, default="M15,M5", help="Comma-separated granularities.")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/fxg_phase8l_exports"))
    parser.add_argument("--dry-run-plan", action="store_true")
    parser.add_argument("--write-export", action="store_true")
    parser.add_argument("--max-export-size-mb", type=float, default=50.0)
    parser.add_argument("--max-context-rows", type=int, default=400, help="Cap for news/calendar JSONL rows.")
    args = parser.parse_args()

    instruments = [x.strip() for x in str(args.instruments).split(",") if x.strip()]
    granularities = [x.strip() for x in str(args.granularities).split(",") if x.strip()]
    max_bytes = int(float(args.max_export_size_mb) * 1024 * 1024)

    try:
        res = run_export(
            days=int(args.days),
            instruments=instruments,
            granularities=granularities,
            output_dir=args.output_dir,
            max_export_size_bytes=max_bytes,
            dry_run_plan=bool(args.dry_run_plan),
            write_export=bool(args.write_export),
            max_context_rows=int(args.max_context_rows),
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
