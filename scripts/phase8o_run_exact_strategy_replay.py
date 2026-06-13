#!/usr/bin/env python3
"""
Phase 8O: exact strategy replay or fail closed.

Allowed replay modes:
- Archived candidate replay when candidate rows contain the required live fields.
- Fail-closed result pack when exact candidate or exact live-rule reconstruction is not proven.

There is deliberately no ORB/proxy fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.phase8k_replay_lib import (  # noqa: E402
    _iter_inventory_candidates,
    _parse_iso_utc,
    aggregate_month_by_month,
    drawdown_proxy_r,
    expectancy_r,
    max_loss_streak,
    profit_factor_r,
    replay_inventory_candidates_against_bars,
)
from scripts.local_research.phase8l_metrics import daily_stats_from_trades, pick_recommendation  # noqa: E402

PHASE = "Phase 8O"
UTC = timezone.utc

REQUIRED_CANDIDATE_FIELDS = (
    "generated_at_utc",
    "instrument",
    "session_bucket",
    "side",
    "entry",
    "stop_loss",
    "take_profit",
    "score",
    "grade",
    "pair_session_policy_class",
    "news_gate_status",
    "preflight_state",
    "candidate_source",
)


def utc_now_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_dataset(path: Path) -> pd.DataFrame:
    path = path.expanduser().resolve()
    if path.suffix.lower() == ".pkl":
        return pd.read_pickle(path)
    try:
        return pd.read_parquet(path)
    except Exception:
        fallback = path.with_suffix(".pkl")
        if fallback.is_file():
            return pd.read_pickle(fallback)
        raise


def candles_df_to_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, r in df.sort_values("time_utc").iterrows():
        ts = r["time_utc"]
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        rows.append(
            {
                "time": ts.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "o": float(r["o"]),
                "h": float(r["h"]),
                "l": float(r["l"]),
                "c": float(r["c"]),
                "volume": int(r.get("volume") or 0),
            }
        )
    return rows


def field_present(row: Mapping[str, Any], field: str) -> bool:
    aliases = {
        "generated_at_utc": ("generated_at_utc", "entry_time_utc", "signal_time_utc", "timestamp_utc", "ts_utc"),
        "entry": ("entry", "entry_price", "open_price", "price"),
        "side": ("side", "direction", "signal_side"),
        "session_bucket": ("session_bucket", "session", "session_key"),
    }
    names = aliases.get(field, (field,))
    return any(row.get(name) is not None and str(row.get(name)) != "" for name in names)


def missing_candidate_fields(row: Mapping[str, Any]) -> List[str]:
    return [field for field in REQUIRED_CANDIDATE_FIELDS if not field_present(row, field)]


def normalize_candidate_for_replay(row: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    if out.get("entry_price") is None and out.get("entry") is not None:
        out["entry_price"] = out.get("entry")
    if out.get("direction") is None and out.get("side") is not None:
        out["direction"] = out.get("side")
    if out.get("entry_time_utc") is None:
        out["entry_time_utc"] = (
            out.get("generated_at_utc")
            or out.get("signal_time_utc")
            or out.get("timestamp_utc")
            or out.get("ts_utc")
        )
    return out


def load_candidates(candidate_archive: Path) -> List[Dict[str, Any]]:
    if not candidate_archive.is_file():
        return []
    obj = load_json(candidate_archive)
    return [dict(r) for r in _iter_inventory_candidates(obj) if isinstance(r, Mapping)]


def filter_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    instrument: str,
    session_bucket: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in candidates:
        ins = row.get("instrument") or row.get("pair") or row.get("symbol")
        sb = row.get("session_bucket") or row.get("session") or row.get("session_key")
        if str(ins or "").upper() != instrument.upper():
            continue
        if session_bucket and session_bucket.lower() not in str(sb or "").lower():
            continue
        out.append(dict(row))
    return out


def embargo_map(dataset: pd.DataFrame) -> Dict[str, Tuple[bool, bool]]:
    out: Dict[str, Tuple[bool, bool]] = {}
    for _, r in dataset.iterrows():
        ts = r["time_utc"]
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        key = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
        out[key] = (bool(r.get("news_embargo_adjacent")), bool(r.get("calendar_high_impact_adjacent")))
    return out


def enrich_trades(trades: Sequence[Mapping[str, Any]], dataset: pd.DataFrame, session_bucket: str) -> List[Dict[str, Any]]:
    emb = embargo_map(dataset)
    out: List[Dict[str, Any]] = []
    for t in trades:
        row = dict(t)
        news, cal = emb.get(str(row.get("entry_time_utc") or ""), (False, False))
        row["session_bucket"] = session_bucket
        row["news_embargo_adjacent"] = news
        row["calendar_high_impact_adjacent"] = cal
        row["clean_sample"] = not (news or cal)
        row["execution_instruction_emulated"] = "WAIT" if news or cal else "RESEARCH_ONLY"
        out.append(row)
    return out


def metric_bundle(trades: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rmuls = [float(t.get("r_multiple") or 0.0) for t in trades]
    outcomes = [str(t.get("outcome") or "") for t in trades]
    wins = sum(1 for x in outcomes if x == "win")
    losses = sum(1 for x in outcomes if x == "loss")
    breakeven = sum(1 for x in outcomes if x == "breakeven")
    months = aggregate_month_by_month(list(trades), time_field="entry_time_utc")
    return {
        "candidate_count": len(trades),
        "resolved_count": len(trades),
        "clean_sample_count": sum(1 for t in trades if t.get("clean_sample")),
        "excluded_news_gated": sum(1 for t in trades if t.get("news_embargo_adjacent")),
        "excluded_calendar_gated": sum(1 for t in trades if t.get("calendar_high_impact_adjacent")),
        "win_count": wins,
        "loss_count": losses,
        "breakeven_count": breakeven,
        "win_rate": round((wins / len(trades)) if trades else 0.0, 6),
        "expectancy_r": round(expectancy_r(rmuls), 6) if trades else 0.0,
        "profit_factor_r": (
            round(profit_factor_r(rmuls), 6)
            if trades and profit_factor_r(rmuls) != float("inf")
            else (999999.0 if trades else 0.0)
        ),
        "max_loss_streak": max_loss_streak(outcomes),
        "drawdown_proxy_r": round(drawdown_proxy_r(rmuls), 6) if trades else 0.0,
        "month_by_month_stats": months,
        "daily_stats": daily_stats_from_trades(trades),
    }


def write_checksums(out_dir: Path, names: Sequence[str]) -> None:
    lines = []
    for name in sorted(names):
        if name == "checksums.sha256":
            continue
        path = out_dir / name
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {name}")
    (out_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_result_pack(out_dir: Path, names: Sequence[str]) -> Path:
    pack = out_dir / "phase8o_result_pack.tar.gz"
    with tarfile.open(pack, mode="w:gz") as tf:
        for name in list(names) + ["checksums.sha256"]:
            path = out_dir / name
            if path.is_file():
                tf.add(path, arcname=name)
    return pack


def fail_summary(
    *,
    classification: str,
    reason: str,
    instrument: str,
    granularity: str,
    lookback_days: int,
    discovery: Optional[Dict[str, Any]],
    dataset_meta: Optional[Dict[str, Any]],
    session_bucket: str,
) -> Dict[str, Any]:
    now = utc_now_iso_z()
    return {
        "generated_at_utc": now,
        "phase": PHASE,
        "classification": classification,
        "replay_mode": "fail_closed",
        "exact_strategy_replay": False,
        "instrument": instrument,
        "granularity": granularity.upper(),
        "lookback_days": lookback_days,
        "dataset_start_utc": (dataset_meta or {}).get("dataset_start_utc"),
        "dataset_end_utc": (dataset_meta or {}).get("dataset_end_utc"),
        "session_bucket": session_bucket,
        "session_window_utc": None,
        "candidate_count": 0,
        "resolved_count": 0,
        "clean_sample_count": 0,
        "excluded_news_gated": 0,
        "excluded_calendar_gated": 0,
        "expectancy_r": 0.0,
        "profit_factor_r": 0.0,
        "win_rate": 0.0,
        "max_loss_streak": 0,
        "drawdown_proxy_r": 0.0,
        "month_by_month_stats": [],
        "daily_stats": [],
        "recommendation_label": "NEEDS_MORE_REPLAY_DATA",
        "news_reconstruction_available": bool((dataset_meta or {}).get("news_reconstruction_available")),
        "calendar_reconstruction_available": bool((dataset_meta or {}).get("calendar_reconstruction_available")),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "fail_closed_reason": reason,
        "strategy_paths_found": (discovery or {}).get("strategy_paths_found", []),
        "missing_logic": (discovery or {}).get("missing_logic", []),
        "no_assumptions": True,
    }


def run_candidate_replay(
    *,
    dataset: pd.DataFrame,
    candidates: Sequence[Mapping[str, Any]],
    instrument: str,
    granularity: str,
    session_bucket: str,
    spread_pips: float,
    slippage_pips: float,
) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
    filtered = filter_candidates(candidates, instrument=instrument, session_bucket=session_bucket)
    if not filtered:
        return [], "candidate_archive_missing_or_no_matching_rows", 0

    bad = [(i, missing_candidate_fields(row)) for i, row in enumerate(filtered) if missing_candidate_fields(row)]
    if bad:
        return [], f"candidate_rows_missing_required_fields:{bad[:5]}", len(filtered)

    df_i = dataset[dataset["instrument"].str.upper() == instrument.upper()].copy()
    if df_i.empty:
        return [], f"dataset_missing_instrument:{instrument}", len(filtered)
    candles = candles_df_to_rows(df_i)
    pip = float(df_i["pip_size"].iloc[0]) if "pip_size" in df_i.columns else 0.0001
    raw_trades = replay_inventory_candidates_against_bars(
        [normalize_candidate_for_replay(row) for row in filtered],
        candles,
        granularity=granularity,
        spread_half=(spread_pips * pip) / 2.0,
        slippage=slippage_pips * pip,
    )
    return enrich_trades(raw_trades, df_i, session_bucket), None, len(filtered)


def write_outputs(
    *,
    out_dir: Path,
    summary: Dict[str, Any],
    trades: Sequence[Mapping[str, Any]],
    recommendation_label: str,
    run_manifest: Dict[str, Any],
    write_pack: bool,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary["recommendation_label"] = recommendation_label
    run_manifest.setdefault("paper_review_only", True)
    run_manifest.setdefault("live_permission", False)
    run_manifest.setdefault("ny_live_enabled", False)
    run_manifest.setdefault("send_trade_unlock_changed", False)
    run_manifest.setdefault("execution_paths_changed", False)
    recommendation = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "classification": summary["classification"],
        "recommendation_label": recommendation_label,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "notes": "Research-only exact replay output. Does not grant live permission.",
    }
    monthly = {"phase": PHASE, "months": summary.get("month_by_month_stats", []), "session": summary.get("session_bucket")}
    daily = {"phase": PHASE, "daily": summary.get("daily_stats", [])}

    (out_dir / "phase8o_backtest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "phase8o_recommendation.json").write_text(json.dumps(recommendation, indent=2), encoding="utf-8")
    (out_dir / "phase8o_monthly_persistence.json").write_text(json.dumps(monthly, indent=2), encoding="utf-8")
    (out_dir / "phase8o_daily_persistence.json").write_text(json.dumps(daily, indent=2), encoding="utf-8")
    (out_dir / "phase8o_run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    lines = [json.dumps(t, separators=(",", ":")) for t in list(trades)[:2000]]
    (out_dir / "phase8o_replay_samples_compact.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    names = [
        "phase8o_backtest_summary.json",
        "phase8o_recommendation.json",
        "phase8o_monthly_persistence.json",
        "phase8o_daily_persistence.json",
        "phase8o_run_manifest.json",
        "phase8o_replay_samples_compact.jsonl",
    ]
    write_checksums(out_dir, names)
    pack = write_result_pack(out_dir, names) if write_pack else None
    return {"ok": True, "summary_path": str(out_dir / "phase8o_backtest_summary.json"), "result_pack": str(pack) if pack else None, "summary": summary}


def run_replay(
    *,
    dataset_path: Optional[Path],
    dataset_manifest: Optional[Path],
    discovery_report: Optional[Path],
    candidate_archive: Optional[Path],
    out_dir: Path,
    instrument: str,
    granularity: str,
    lookback_days: int,
    session_bucket: str,
    spread_pips: float,
    slippage_pips: float,
    write_result_pack: bool,
) -> Dict[str, Any]:
    discovery = load_json(discovery_report) if discovery_report and discovery_report.is_file() else None
    dataset_meta = load_json(dataset_manifest) if dataset_manifest and dataset_manifest.is_file() else None

    if discovery and not discovery.get("exact_replay_possible"):
        summary = fail_summary(
            classification="FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND",
            reason="strategy_discovery_exact_replay_possible_false",
            instrument=instrument,
            granularity=granularity,
            lookback_days=lookback_days,
            discovery=discovery,
            dataset_meta=dataset_meta,
            session_bucket=session_bucket,
        )
        return write_outputs(
            out_dir=out_dir,
            summary=summary,
            trades=[],
            recommendation_label="NEEDS_MORE_REPLAY_DATA",
            run_manifest={"generated_at_utc": utc_now_iso_z(), "phase": PHASE, "replay_mode": "fail_closed", "discovery_report": str(discovery_report) if discovery_report else None},
            write_pack=write_result_pack,
        )

    if dataset_path is None or not dataset_path.exists():
        summary = fail_summary(
            classification="FAIL_CLOSED_NEWS_CALENDAR_UNRESOLVED",
            reason="dataset_missing_or_not_built",
            instrument=instrument,
            granularity=granularity,
            lookback_days=lookback_days,
            discovery=discovery,
            dataset_meta=dataset_meta,
            session_bucket=session_bucket,
        )
        return write_outputs(
            out_dir=out_dir,
            summary=summary,
            trades=[],
            recommendation_label="NEEDS_MORE_REPLAY_DATA",
            run_manifest={"generated_at_utc": utc_now_iso_z(), "phase": PHASE, "replay_mode": "fail_closed"},
            write_pack=write_result_pack,
        )

    dataset = read_dataset(dataset_path)
    candidates = load_candidates(candidate_archive) if candidate_archive else []
    trades, fail_reason, candidate_count = run_candidate_replay(
        dataset=dataset,
        candidates=candidates,
        instrument=instrument,
        granularity=granularity,
        session_bucket=session_bucket,
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
    )
    if fail_reason:
        summary = fail_summary(
            classification="FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND",
            reason=f"exact_candidate_replay_unavailable:{fail_reason}; exact_live_rule_replay_not_proven_without_clock_and_news_injection",
            instrument=instrument,
            granularity=granularity,
            lookback_days=lookback_days,
            discovery=discovery,
            dataset_meta=dataset_meta,
            session_bucket=session_bucket,
        )
        summary["candidate_count"] = candidate_count
        return write_outputs(
            out_dir=out_dir,
            summary=summary,
            trades=[],
            recommendation_label="NEEDS_MORE_REPLAY_DATA",
            run_manifest={"generated_at_utc": utc_now_iso_z(), "phase": PHASE, "replay_mode": "fail_closed", "fail_closed_reason": fail_reason},
            write_pack=write_result_pack,
        )

    metrics = metric_bundle(trades)
    rec = pick_recommendation(
        expectancy=float(metrics["expectancy_r"]),
        resolved=int(metrics["resolved_count"]),
        months=metrics["month_by_month_stats"],
    )
    summary: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "PASS_EXACT_CANDIDATE_REPLAY_COMPLETE",
        "replay_mode": "archived_candidate_exact_replay",
        "exact_strategy_replay": True,
        "instrument": instrument,
        "granularity": granularity.upper(),
        "lookback_days": lookback_days,
        "dataset_start_utc": (dataset_meta or {}).get("dataset_start_utc"),
        "dataset_end_utc": (dataset_meta or {}).get("dataset_end_utc"),
        "session_bucket": session_bucket,
        "session_window_utc": "13:30-16:00" if "NY" in session_bucket else None,
        **metrics,
        "news_reconstruction_available": bool((dataset_meta or {}).get("news_reconstruction_available")),
        "calendar_reconstruction_available": bool((dataset_meta or {}).get("calendar_reconstruction_available")),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "strategy_paths_found": (discovery or {}).get("strategy_paths_found", []),
        "no_assumptions": True,
    }
    run_manifest = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "machine_role": "5950X",
        "replay_mode": summary["replay_mode"],
        "dataset_path": str(dataset_path),
        "dataset_manifest": str(dataset_manifest) if dataset_manifest else None,
        "candidate_archive": str(candidate_archive) if candidate_archive else None,
        "candidate_count_before_resolution": candidate_count,
        "paper_review_only": True,
        "live_permission": False,
    }
    return write_outputs(
        out_dir=out_dir,
        summary=summary,
        trades=trades,
        recommendation_label=rec,
        run_manifest=run_manifest,
        write_pack=write_result_pack,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8O exact strategy replay or fail closed.")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--dataset-manifest", type=Path, default=None)
    parser.add_argument("--strategy-discovery", type=Path, default=None)
    parser.add_argument("--candidate-archive", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path(r"C:\Users\gavin\fxg-research\phase8o_exact_replay\outputs"))
    parser.add_argument("--instrument", default="EUR_USD")
    parser.add_argument("--granularity", default="M15")
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--session-bucket", default="NY_OPEN_SECONDARY_PROPOSED")
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--slippage-pips", type=float, default=0.5)
    parser.add_argument("--write-result-pack", action="store_true")
    args = parser.parse_args()

    try:
        result = run_replay(
            dataset_path=args.dataset,
            dataset_manifest=args.dataset_manifest,
            discovery_report=args.strategy_discovery,
            candidate_archive=args.candidate_archive,
            out_dir=args.output_dir.expanduser().resolve(),
            instrument=args.instrument,
            granularity=args.granularity,
            lookback_days=int(args.lookback_days),
            session_bucket=args.session_bucket,
            spread_pips=float(args.spread_pips),
            slippage_pips=float(args.slippage_pips),
            write_result_pack=bool(args.write_result_pack),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
