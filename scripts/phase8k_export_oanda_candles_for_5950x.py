#!/usr/bin/env python3
"""
Phase 8K-DATA: ALPHA-side (or any host with OANDA env) candle export for 5950X replay.

- Historical mid candles only via OANDA REST (same pattern as scripts/research_fetch_oanda_m5_cache.py).
- Credentials from environment only (e.g. `source /etc/ai-quant/.env` before invoking).
- No order/execution imports.

Outputs:
- gzip JSONL (.jsonl.gz): one normalized candle object per line
- manifest JSON beside it (no secrets; secret_fields_written=false)
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
from typing import Any, Dict, List, Optional, Tuple

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

UTC = timezone.utc


def manifest_path_for_jsonl_gz(output: Path) -> Path:
    name = output.name
    if name.endswith(".jsonl.gz"):
        return output.with_name(name[: -len(".jsonl.gz")] + ".manifest.json")
    raise ValueError("output must end with .jsonl.gz")


def build_dry_run_plan(
    *,
    instrument: str,
    granularity: str,
    lookback_days: int,
    output: Path,
    max_export_size_bytes: int,
    credentials_present: bool,
) -> Dict[str, Any]:
    n = expected_candle_count_full_clock(lookback_days, granularity)
    raw_est = estimate_jsonl_raw_bytes(n)
    gz_est = estimate_gzip_compressed_bytes_heuristic(raw_est)
    try:
        manifest_path = manifest_path_for_jsonl_gz(output)
    except ValueError:
        manifest_path = output.parent / (output.name + ".manifest.json")

    return {
        "phase": "Phase 8K-DATA",
        "mode": "alpha_data_export_only",
        "instrument": instrument,
        "granularity": granularity.upper(),
        "lookback_days": lookback_days,
        "expected_candle_count_approx": n,
        "estimated_uncompressed_bytes_upper_bound": raw_est,
        "estimated_compressed_bytes_heuristic": gz_est,
        "max_export_size_bytes": max_export_size_bytes,
        "preflight_compressed_estimate_fits": gz_est <= max_export_size_bytes,
        "output_jsonl_gz": str(output),
        "output_manifest": str(manifest_path),
        "oanda_credentials_from_env": credentials_present,
        "would_refuse_preflight": gz_est > max_export_size_bytes,
    }


def preflight_refuses(
    *,
    lookback_days: int,
    granularity: str,
    max_export_size_bytes: int,
) -> Tuple[bool, Dict[str, Any]]:
    plan = build_dry_run_plan(
        instrument="",
        granularity=granularity,
        lookback_days=lookback_days,
        output=Path("placeholder.jsonl.gz"),
        max_export_size_bytes=max_export_size_bytes,
        credentials_present=False,
    )
    return bool(plan.get("would_refuse_preflight")), plan


def export_candles_jsonl_gz(
    *,
    instrument: str,
    granularity: str,
    lookback_days: int,
    output: Path,
    max_export_size_bytes: int,
    dry_run_plan: bool,
) -> Dict[str, Any]:
    t_end = datetime.now(UTC)
    t_start = t_end - timedelta(days=lookback_days)
    creds = bool(os.getenv("OANDA_API_KEY"))
    plan = build_dry_run_plan(
        instrument=instrument,
        granularity=granularity,
        lookback_days=lookback_days,
        output=output,
        max_export_size_bytes=max_export_size_bytes,
        credentials_present=creds,
    )

    if dry_run_plan:
        return {"dry_run_plan": plan}

    if plan.get("would_refuse_preflight"):
        raise RuntimeError(
            "EXPORT_PREFLIGHT_REFUSED:estimated_compressed_exceeds_cap:"
            f"{plan.get('estimated_compressed_bytes_heuristic')}>{max_export_size_bytes}"
        )

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
        raise RuntimeError("NO_CANDLES_FETCHED")

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_path_for_jsonl_gz(output)

    fd, tmp_path = tempfile.mkstemp(suffix=".jsonl.gz", dir=str(output.parent))
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as gz:
            for c in candles:
                line = json.dumps(c, separators=(",", ":"))
                gz.write(line + "\n")

        sz = int(tmp.stat().st_size)
        if sz > max_export_size_bytes:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"EXPORT_SIZE_REFUSED:actual_compressed_bytes={sz}>{max_export_size_bytes}"
            )

        digest = hashlib.sha256()
        with open(tmp, "rb") as bf:
            for chunk in iter(lambda: bf.read(1024 * 1024), b""):
                digest.update(chunk)
        sha = digest.hexdigest()

        tmp.replace(output)

        t_first = parse_time_iso_utc(candles[0].get("time"))
        t_last = parse_time_iso_utc(candles[-1].get("time"))
        manifest: Dict[str, Any] = {
            "schema": "fxg.phase8k.candle_export_manifest.v1",
            "source_host": socket.gethostname(),
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "instrument": instrument,
            "granularity": granularity.upper(),
            "start_utc": t_first.isoformat().replace("+00:00", "Z") if t_first else None,
            "end_utc": t_last.isoformat().replace("+00:00", "Z") if t_last else None,
            "candle_count": len(candles),
            "compressed_size_bytes": sz,
            "sha256": sha,
            "export_path": str(output),
            "secret_fields_written": False,
            "lookback_days_requested": lookback_days,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "candle_count": len(candles),
            "compressed_size_bytes": sz,
            "output": str(output),
            "manifest": str(manifest_path),
            "sha256": sha,
        }
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8K-DATA OANDA candle export (read-only).")
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--granularity", type=str, default="M15")
    parser.add_argument("--lookback-days", type=int, default=180)
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Path ending in .jsonl.gz",
    )
    parser.add_argument("--dry-run-plan", action="store_true")
    parser.add_argument(
        "--max-export-size-mb",
        type=float,
        default=25.0,
        help="Refuse if preflight heuristic or actual gzip exceeds this (default 25 MB).",
    )
    args = parser.parse_args()

    max_bytes = int(float(args.max_export_size_mb) * 1024 * 1024)

    if args.dry_run_plan:
        creds = bool(os.getenv("OANDA_API_KEY"))
        out = args.output or Path("/tmp/phase8k_export_placeholder.jsonl.gz")
        plan = build_dry_run_plan(
            instrument=args.instrument,
            granularity=args.granularity,
            lookback_days=args.lookback_days,
            output=out,
            max_export_size_bytes=max_bytes,
            credentials_present=creds,
        )
        print(json.dumps({"dry_run_plan": plan}, indent=2))
        return 0

    if not args.output:
        print(json.dumps({"ok": False, "error": "--output required unless --dry-run-plan"}, indent=2))
        return 1

    if not str(args.output).endswith(".jsonl.gz"):
        print(json.dumps({"ok": False, "error": "output must end with .jsonl.gz"}, indent=2))
        return 1

    try:
        res = export_candles_jsonl_gz(
            instrument=args.instrument,
            granularity=args.granularity,
            lookback_days=args.lookback_days,
            output=args.output,
            max_export_size_bytes=max_bytes,
            dry_run_plan=False,
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
