#!/usr/bin/env python3
"""
Phase 8K: Local-only NY EUR_USD replay / best-available proxy (5950X research).

- Reads Phase 8J handoff pack (manifest + ARTIFACTS/*).
- Optional OANDA candle pulls (historical only; env credentials), or `--candles-jsonl-gz`
  from Phase 8K-DATA ALPHA export (no local OANDA key needed on 5950X).
- Writes Phase 8J-named compact outputs for import verifier compatibility.

Does not import broker order/execution modules.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.oanda_mid_historical_fetch import (  # noqa: E402
    fetch_oanda_mid_candles_range,
    parse_time_iso_utc,
)

from scripts.local_research.phase8k_replay_lib import (  # noqa: E402
    OrbProxyParams,
    aggregate_month_by_month,
    build_daily_orb_proxy_trades,
    classify_replay_from_handoff_pack,
    drawdown_proxy_r,
    expectancy_r,
    filter_candles_session_window,
    inventory_path_in_pack,
    load_json_if_exists,
    max_loss_streak,
    month_key_utc,
    parse_session_window_utc,
    profit_factor_r,
    replay_inventory_candidates_against_bars,
    _iter_inventory_candidates,
)

UTC = timezone.utc
PHASE = "Phase 8K"
SESSION_BUCKET = "NY_OPEN_SECONDARY_PROPOSED"
DEFAULT_WINDOW = "13:30-16:00"


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def load_candles_jsonl_gz(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with gzip.open(path.expanduser().resolve(), "rt", encoding="utf-8") as gz:
        for line in gz:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
    out.sort(
        key=lambda x: parse_time_iso_utc(str(x.get("time")))
        or datetime.min.replace(tzinfo=UTC)
    )
    return out


def clip_candles_to_lookback_from_last_bar(
    candles: List[Dict[str, Any]],
    *,
    lookback_days: int,
) -> List[Dict[str, Any]]:
    """Clip to [last_bar_time - lookback_days, last_bar_time] so stale exports still replay."""
    if not candles or lookback_days <= 0:
        return candles
    times = [parse_time_iso_utc(c.get("time")) for c in candles]
    times = [t for t in times if t is not None]
    if not times:
        return candles
    t_end = max(times)
    t_start = t_end - timedelta(days=lookback_days)
    clipped: List[Dict[str, Any]] = []
    for c in candles:
        t = parse_time_iso_utc(c.get("time"))
        if t is not None and t_start <= t <= t_end:
            clipped.append(c)
    return clipped


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_checksums(out_dir: Path, names: List[str]) -> None:
    lines = []
    for n in sorted(names):
        if n == "checksums.sha256":
            continue
        digest = _sha256_file(out_dir / n)
        lines.append(f"{digest}  {n}")
    (out_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pick_recommendation(
    *,
    expectancy: float,
    resolved: int,
    months: List[Dict[str, Any]],
) -> str:
    if resolved < 12:
        return "NEEDS_MORE_REPLAY_DATA"
    pos_months = sum(1 for m in months if m.get("expectancy_r", 0) > 0)
    if expectancy >= 0.2 and pos_months >= max(1, int(len(months) * 0.6)):
        return "PREPARE_PROMOTION_REVIEW_PACK"
    if expectancy > 0.05:
        return "CONTINUE_FORWARD_PAPER_REVIEW"
    if expectancy < -0.05:
        return "DOWNGRADE_RESEARCH_ONLY"
    return "NEEDS_MORE_REPLAY_DATA"


def _load_inventory_candidates_filtered(
    input_pack: Path, instrument: str, session_substr: str
) -> List[Dict[str, Any]]:
    inv = load_json_if_exists(inventory_path_in_pack(input_pack))
    if not inv:
        return []
    cands = _iter_inventory_candidates(inv)

    def matches(row: Dict[str, Any]) -> bool:
        sb = row.get("session_bucket") or row.get("session") or row.get("session_key") or ""
        ins = row.get("instrument") or row.get("pair") or row.get("symbol") or ""
        return str(ins).upper() == instrument.upper() and session_substr.lower() in str(sb).lower()

    return [c for c in cands if isinstance(c, dict) and matches(c)]


def run_pipeline(
    *,
    input_pack: Path,
    output_dir: Path,
    instrument: str,
    session_window_utc: str,
    lookback_days: int,
    granularity: str,
    dry_run_plan: bool,
    write_result_pack: bool,
    fixtures_candles_json: Optional[Path],
    candles_jsonl_gz: Optional[Path],
    spread_pips: float,
    slippage_pips: float,
) -> Dict[str, Any]:
    start_min, end_min = parse_session_window_utc(session_window_utc)
    exact_ok, replay_mode, notes, inv_count = classify_replay_from_handoff_pack(
        input_pack,
        instrument=instrument,
        session_bucket_substr="NY_OPEN_SECONDARY",
    )
    manifest = load_json_if_exists(input_pack / "manifest.json") or {}

    t_end = datetime.now(UTC)
    t_start = t_end - timedelta(days=lookback_days)

    pip = 0.0001 if "JPY" not in instrument.upper() else 0.01
    spread_half = (spread_pips * pip) / 2.0
    slip = slippage_pips * pip

    creds = bool(_env("OANDA_API_KEY"))

    est_session_minutes = max(0, end_min - start_min + 1)
    bars_per_day = max(1, int(est_session_minutes / (5 if granularity.upper() == "M5" else 15)))
    est_bars = int(lookback_days * bars_per_day * 1.05)

    plan: Dict[str, Any] = {
        "phase": PHASE,
        "input_pack": str(input_pack.resolve()),
        "exact_replay_possible": exact_ok,
        "replay_mode": replay_mode if not exact_ok else "exact_replay_possible",
        "inventory_candidate_total_session_match": inv_count,
        "classification_notes": notes,
        "instrument": instrument,
        "granularity": granularity.upper(),
        "lookback_days": lookback_days,
        "session_window_utc": session_window_utc,
        "dataset_start_utc": t_start.isoformat().replace("+00:00", "Z"),
        "dataset_end_utc": t_end.isoformat().replace("+00:00", "Z"),
        "estimated_in_window_bars": est_bars,
        "oanda_credentials_from_env": creds,
        "fixtures_mode": bool(fixtures_candles_json),
        "candles_jsonl_gz": str(candles_jsonl_gz.resolve()) if candles_jsonl_gz else None,
    }

    if dry_run_plan:
        return {"dry_run_plan": plan}

    if candles_jsonl_gz is not None and not candles_jsonl_gz.expanduser().resolve().is_file():
        raise RuntimeError("candles_jsonl_gz_not_found")

    candles: List[Dict[str, Any]]
    if candles_jsonl_gz is not None:
        candles = load_candles_jsonl_gz(candles_jsonl_gz)
        candles = clip_candles_to_lookback_from_last_bar(candles, lookback_days=lookback_days)
    elif fixtures_candles_json is not None:
        candles = json.loads(fixtures_candles_json.read_text(encoding="utf-8"))
        if not isinstance(candles, list):
            raise RuntimeError("fixtures_candles_json must be a JSON array")
    else:
        if not creds:
            raise RuntimeError(
                "OANDA_API_KEY required for candle fetch (or use --fixtures-candles-json / --candles-jsonl-gz)"
            )
        candles = fetch_oanda_mid_candles_range(
            instrument,
            granularity.upper(),
            t_start,
            t_end,
        )

    in_win = filter_candles_session_window(
        candles,
        start_minutes=start_min,
        end_minutes=end_min,
    )

    filtered_inv = _load_inventory_candidates_filtered(
        input_pack, instrument=instrument, session_substr="NY_OPEN_SECONDARY"
    )

    ran_exact = False
    if exact_ok and filtered_inv:
        trades = replay_inventory_candidates_against_bars(
            filtered_inv,
            candles,
            granularity=granularity,
            spread_half=spread_half,
            slippage=slip,
        )
        if len(trades) > 0:
            ran_exact = True
            candidate_source = "archived_inventory_exact"
            replay_mode = "exact_replay_possible"
            approx = (
                "exact_replay_using_inventory_fields_and_mid_candles; "
                "conservative_same_bar_sl_before_tp"
            )
        else:
            trades = []

    if not ran_exact:
        trades = build_daily_orb_proxy_trades(
            candles,
            session_start_minutes=start_min,
            session_end_minutes=end_min,
            params=OrbProxyParams(rr_multiple=2.0),
            spread_half=spread_half,
            slippage=slip,
        )
        candidate_source = "best_available_proxy_orb_first_m15_bar_breakout"
        replay_mode = "best_available_proxy_reconstruction"
        extra = "inventory_replay_yielded_zero_trades; " if exact_ok and filtered_inv else ""
        approx = (
            f"{extra}"
            "NY_OPEN_SECONDARY_PROPOSED lane rules are not embedded in this script; "
            "used first in-session M15 ORB breakout-close proxy with 2R TP. "
            "Not live permission; not lane policy."
        )

    rmuls = [float(t.get("r_multiple") or 0.0) for t in trades]
    outcomes = [str(t.get("outcome") or "") for t in trades]
    wins = sum(1 for o in outcomes if o == "win")
    losses = sum(1 for o in outcomes if o == "loss")
    be = sum(1 for o in outcomes if o == "breakeven")

    months = aggregate_month_by_month(trades, time_field="entry_time_utc")
    exp = expectancy_r(rmuls)
    pfr = profit_factor_r(rmuls)
    mls = max_loss_streak(outcomes)
    dd = drawdown_proxy_r(rmuls)
    wr = (wins / len(trades)) if trades else 0.0

    dataset_start = t_start.isoformat().replace("+00:00", "Z")
    dataset_end = t_end.isoformat().replace("+00:00", "Z")
    if candles:
        t0 = parse_time_iso_utc(str(candles[0].get("time")))
        t1 = parse_time_iso_utc(str(candles[-1].get("time")))
        if t0 and t1:
            dataset_start = t0.isoformat().replace("+00:00", "Z")
            dataset_end = t1.isoformat().replace("+00:00", "Z")

    summary: Dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": PHASE,
        "classification": str(manifest.get("classification") or "RESEARCH_ONLY"),
        "machine_role": "5950X",
        "instrument": instrument,
        "session_bucket": SESSION_BUCKET,
        "session_window_utc": session_window_utc,
        "data_source": (
            "alpha_export_jsonl_gz"
            if candles_jsonl_gz is not None
            else ("fixtures_json" if fixtures_candles_json is not None else "oanda_mid")
        ),
        "dataset_start_utc": dataset_start,
        "dataset_end_utc": dataset_end,
        "granularity": granularity.upper(),
        "lookback_days": lookback_days,
        "candidate_source": candidate_source,
        "replay_mode": replay_mode,
        "exact_replay_possible": bool(ran_exact),
        "candidate_count": inv_count if inv_count else len(filtered_inv),
        "resolved_count": len(trades),
        "win_count": wins,
        "loss_count": losses,
        "breakeven_count": be,
        "win_rate": round(wr, 6) if trades else 0.0,
        "expectancy_r": round(exp, 6) if trades else 0.0,
        "profit_factor_r": (
            (round(pfr, 6) if pfr != float("inf") else 999999.0) if trades else 0.0
        ),
        "max_loss_streak": mls,
        "drawdown_proxy_r": round(dd, 6),
        "month_by_month_stats": months,
        "spread_slippage_assumptions": {
            "spread_pips": spread_pips,
            "slippage_pips_per_side": slippage_pips,
            "pip_size": pip,
        },
        "news_reconstruction_available": False,
        "approximation_notes": approx,
        "recommendation_label": _pick_recommendation(expectancy=exp, resolved=len(trades), months=months),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }

    recommendation = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "classification": summary["classification"],
        "recommendation_label": summary["recommendation_label"],
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "notes": "Phase 8K local research only; scorecard win rate without R coverage is not predictive of R.",
    }

    run_manifest = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "machine_role": "5950X",
        "input_pack": str(input_pack.resolve()),
        "output_dir": str(output_dir.resolve()),
        "argv": sys.argv,
        "replay_mode": replay_mode,
        "exact_replay_possible": summary["exact_replay_possible"],
    }

    monthly_path = output_dir / "phase8j_monthly_persistence.json"
    summary_path = output_dir / "phase8j_replay_summary.json"
    rec_path = output_dir / "phase8j_recommendation.json"
    man_path = output_dir / "phase8j_run_manifest.json"
    samples_path = output_dir / "phase8j_replay_samples_compact.jsonl"

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    monthly_path.write_text(json.dumps({"months": months, "phase": PHASE}, indent=2), encoding="utf-8")
    rec_path.write_text(json.dumps(recommendation, indent=2), encoding="utf-8")
    man_path.write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    lines_out: List[str] = []
    for t in trades[:500]:
        lines_out.append(json.dumps(t, separators=(",", ":")))
    samples_path.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")

    names = [
        "phase8j_replay_summary.json",
        "phase8j_monthly_persistence.json",
        "phase8j_recommendation.json",
        "phase8j_run_manifest.json",
        "phase8j_replay_samples_compact.jsonl",
    ]
    _write_checksums(output_dir, names)

    if write_result_pack:
        arc = output_dir / "phase8j_5950x_result_pack.tar.gz"
        with tarfile.open(arc, mode="w:gz") as tf:
            for n in names + ["checksums.sha256"]:
                p = output_dir / n
                if p.is_file():
                    tf.add(p, arcname=n)

    return {"plan": plan, "summary": summary, "trades_count": len(trades), "in_window_candles": len(in_win)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8K local NY EUR_USD replay / proxy.")
    parser.add_argument("--input-pack", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--session-window-utc", type=str, default=DEFAULT_WINDOW)
    parser.add_argument("--lookback-days", type=int, default=180)
    parser.add_argument("--granularity", type=str, default="M15", choices=("M5", "M15", "H1"))
    parser.add_argument("--dry-run-plan", action="store_true")
    parser.add_argument("--write-result-pack", action="store_true")
    parser.add_argument(
        "--fixtures-candles-json",
        type=Path,
        default=None,
        help="Optional local JSON array of candles (skip OANDA); research/testing only.",
    )
    parser.add_argument(
        "--candles-jsonl-gz",
        type=Path,
        default=None,
        help="gzip JSONL candle export (e.g. from phase8k_export_oanda_candles_for_5950x.py on ALPHA).",
    )
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--slippage-pips", type=float, default=0.5)
    args = parser.parse_args()

    if not args.input_pack.is_dir():
        print(json.dumps({"ok": False, "error": "input_pack_not_dir"}, indent=2))
        return 1

    srcs = [args.fixtures_candles_json is not None, args.candles_jsonl_gz is not None]
    if sum(srcs) > 1:
        print(
            json.dumps(
                {"ok": False, "error": "use only one of --fixtures-candles-json or --candles-jsonl-gz"},
                indent=2,
            )
        )
        return 1

    try:
        out = run_pipeline(
            input_pack=args.input_pack,
            output_dir=args.output_dir,
            instrument=args.instrument,
            session_window_utc=args.session_window_utc,
            lookback_days=args.lookback_days,
            granularity=args.granularity,
            dry_run_plan=args.dry_run_plan,
            write_result_pack=args.write_result_pack,
            fixtures_candles_json=args.fixtures_candles_json,
            candles_jsonl_gz=args.candles_jsonl_gz,
            spread_pips=args.spread_pips,
            slippage_pips=args.slippage_pips,
        )
        print(json.dumps(out, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
