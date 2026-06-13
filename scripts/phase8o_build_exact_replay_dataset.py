#!/usr/bin/env python3
"""
Phase 8O: build a deterministic exact replay dataset on the 5950X.

Pure local transform: candles + live/repo indicator calculations + session labels
+ UTC news/calendar labels. Missing news/calendar context fails closed by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.phase8l_dataset_builder import (  # noqa: E402
    SESSION_WINDOWS,
    add_indicators,
    add_session_features,
    build_event_blackouts,
    candles_jsonl_gz_to_dataframe,
    label_embargo,
    load_jsonl_gz,
)

PHASE = "Phase 8O"
UTC = timezone.utc

REQUIRED_INDICATOR_COLUMNS = (
    "atr_14",
    "ema_20",
    "ema_50",
    "sma_20",
    "sma_50",
    "rsi_14",
    "bar_return",
    "rolling_volatility",
    "session_open",
    "session_close",
    "range_high_session",
    "range_low_session",
)


def utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_manifest(export_dir: Path) -> Dict[str, Any]:
    path = export_dir / "phase8o_alpha_export_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing_phase8o_alpha_export_manifest:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def pip_size_for(instrument: str) -> float:
    up = instrument.upper()
    if "JPY" in up or "XAU" in up or "XAG" in up:
        return 0.01
    return 0.0001


def fail_closed_report(
    *,
    reason: str,
    manifest: Optional[Dict[str, Any]] = None,
    output: Optional[Path] = None,
) -> Dict[str, Any]:
    report = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "FAIL_CLOSED_NEWS_CALENDAR_UNRESOLVED"
        if "calendar" in reason or "news" in reason
        else "FAIL_CLOSED_DATASET_UNRESOLVED",
        "exact_strategy_replay": False,
        "fail_closed_reason": reason,
        "manifest_context": {
            "news_reconstruction_available": bool((manifest or {}).get("news_reconstruction_available")),
            "calendar_reconstruction_available": bool((manifest or {}).get("calendar_reconstruction_available")),
            "news_rows_count": int((manifest or {}).get("news_rows_count") or 0),
            "calendar_rows_count": int((manifest or {}).get("calendar_rows_count") or 0),
            "provider_statuses": (manifest or {}).get("provider_statuses") or {},
            "unavailable_reasons": (manifest or {}).get("unavailable_reasons") or [],
        },
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "no_assumptions": True,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_dataset_from_phase8o_export(
    *,
    export_dir: Path,
    primary_granularity: str = "M15",
    spread_pips: float = 1.0,
    slippage_pips: float = 0.5,
    require_news_calendar: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    export_dir = export_dir.expanduser().resolve()
    manifest = load_manifest(export_dir)

    if require_news_calendar:
        if not manifest.get("news_reconstruction_available"):
            raise RuntimeError("FAIL_CLOSED_NEWS_CALENDAR_UNRESOLVED:news_reconstruction_unavailable")
        if not manifest.get("calendar_reconstruction_available"):
            raise RuntimeError("FAIL_CLOSED_NEWS_CALENDAR_UNRESOLVED:calendar_reconstruction_unavailable")

    instruments = list(manifest.get("instruments") or [])
    days = int(manifest.get("days_requested") or 90)
    gran = primary_granularity.upper()
    news_rows = load_jsonl_gz(export_dir / f"phase8o_news_context_{days}d.jsonl.gz")
    calendar_rows = load_jsonl_gz(export_dir / f"phase8o_calendar_context_{days}d.jsonl.gz")
    news_blocks, calendar_blocks = build_event_blackouts(news_rows, calendar_rows)

    frames: List[pd.DataFrame] = []
    missing_gaps: List[str] = []
    for instrument in instruments:
        candle_path = export_dir / f"phase8o_candles_{instrument}_{gran}_{days}d.jsonl.gz"
        if not candle_path.is_file():
            missing_gaps.append(f"missing_file:{candle_path.name}")
            continue
        rows = load_jsonl_gz(candle_path)
        if not rows:
            missing_gaps.append(f"empty_candles:{candle_path.name}")
            continue
        df = candles_jsonl_gz_to_dataframe(rows, instrument=instrument, granularity=gran)
        df = add_session_features(df)
        df = label_embargo(df, news_blocks, calendar_blocks)
        df = add_indicators(df)
        df["spread_assumption_pips"] = float(spread_pips)
        df["slippage_assumption_pips"] = float(slippage_pips)
        df["pip_size"] = float(pip_size_for(instrument))
        frames.append(df)

    if not frames:
        raise RuntimeError("NO_DATASET_BUILT:missing_candles")

    dataset = pd.concat(frames, ignore_index=True).sort_values(["instrument", "time_utc"]).reset_index(drop=True)
    missing_cols = [c for c in REQUIRED_INDICATOR_COLUMNS if c not in dataset.columns]
    if missing_cols:
        raise RuntimeError(f"FAIL_CLOSED_INDICATOR_COLUMNS_MISSING:{','.join(missing_cols)}")

    meta: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "EXACT_REPLAY_DATASET_BUILT",
        "machine_role": "5950X",
        "source_alpha_export_manifest": str(export_dir / "phase8o_alpha_export_manifest.json"),
        "dataset_start_utc": dataset["time_utc"].min().isoformat().replace("+00:00", "Z"),
        "dataset_end_utc": dataset["time_utc"].max().isoformat().replace("+00:00", "Z"),
        "instruments": instruments,
        "granularities": [gran],
        "row_counts": {str(k): int(len(g)) for k, g in dataset.groupby("instrument")},
        "indicator_columns": [c for c in dataset.columns if c in REQUIRED_INDICATOR_COLUMNS],
        "required_indicator_columns": list(REQUIRED_INDICATOR_COLUMNS),
        "session_windows": SESSION_WINDOWS,
        "news_reconstruction_available": bool(manifest.get("news_reconstruction_available")),
        "calendar_reconstruction_available": bool(manifest.get("calendar_reconstruction_available")),
        "news_rows_count": int(manifest.get("news_rows_count") or len(news_rows)),
        "calendar_rows_count": int(manifest.get("calendar_rows_count") or len(calendar_rows)),
        "provider_statuses": manifest.get("provider_statuses") or {},
        "unavailable_reasons": manifest.get("unavailable_reasons") or [],
        "events_aligned_to_candles": int(dataset["news_embargo_adjacent"].sum() + dataset["calendar_high_impact_adjacent"].sum()),
        "embargo_windows_applied": {
            "news_windows": len(news_blocks),
            "calendar_windows": len(calendar_blocks),
            "window_minutes_each_side": 30,
        },
        "missing_data_gaps": missing_gaps,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "no_assumptions": True,
    }
    return dataset, meta


def write_dataset(dataset: pd.DataFrame, path: Path) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        dataset.to_parquet(path, index=False)
        return {"dataset_path": str(path), "dataset_format": "parquet"}
    except Exception as exc:
        fallback = path.with_suffix(".pkl")
        dataset.to_pickle(fallback)
        return {
            "dataset_path": str(fallback),
            "dataset_format": "pickle_fallback",
            "parquet_error": f"{type(exc).__name__}:{str(exc)[:200]}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8O exact replay dataset builder.")
    parser.add_argument("--alpha-export-dir", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, default=Path(r"C:\Users\gavin\fxg-research\phase8o_exact_replay"))
    parser.add_argument("--primary-granularity", default="M15")
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--slippage-pips", type=float, default=0.5)
    parser.add_argument("--allow-missing-news-calendar", action="store_true")
    args = parser.parse_args()

    local_root = args.local_root.expanduser().resolve()
    data_dir = local_root / "data"
    report_dir = local_root / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        dataset, meta = build_dataset_from_phase8o_export(
            export_dir=args.alpha_export_dir,
            primary_granularity=args.primary_granularity,
            spread_pips=float(args.spread_pips),
            slippage_pips=float(args.slippage_pips),
            require_news_calendar=not bool(args.allow_missing_news_calendar),
        )
        dataset_info = write_dataset(dataset, data_dir / "phase8o_exact_replay_dataset.parquet")
        sample_path = data_dir / "phase8o_exact_replay_dataset_sample.csv"
        dataset.head(5000).to_csv(sample_path, index=False)
        meta.update(dataset_info)
        meta["sample_csv"] = str(sample_path)
        manifest_path = data_dir / "phase8o_dataset_manifest.json"
        manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        result = {"ok": True, "dataset_manifest": str(manifest_path), "summary": meta}
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        manifest = None
        try:
            manifest = load_manifest(args.alpha_export_dir.expanduser().resolve())
        except Exception:
            manifest = None
        report = fail_closed_report(
            reason=str(exc),
            manifest=manifest,
            output=report_dir / "phase8o_dataset_fail_closed.json",
        )
        print(json.dumps({"ok": False, "error": str(exc), "fail_closed_report": report}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
