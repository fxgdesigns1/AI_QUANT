#!/usr/bin/env python3
"""
Phase 8L: Local (5950X) orchestrator — dataset, replay, metrics, compact result pack.

Consumes ALPHA Phase 8L export directory + optional Phase 8J handoff pack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.local_research.phase8l_dataset_builder import build_dataset_from_alpha_export  # noqa: E402
from scripts.local_research.phase8l_replay_engine import run_full_replay  # noqa: E402
from scripts.local_research.phase8l_metrics import compute_metrics_bundle, pick_recommendation  # noqa: E402

UTC = timezone.utc
PHASE = "Phase 8L"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_phase8aa_context_manifest() -> Tuple[Optional[Dict[str, Any]], bool, Optional[str]]:
    """Read PHASE8AA_CONTEXT_MANIFEST env var and return (manifest, sha256_verified, version)."""
    manifest_path_str = os.environ.get("PHASE8AA_CONTEXT_MANIFEST")
    if not manifest_path_str:
        return None, False, None
    manifest_path = Path(manifest_path_str)
    if not manifest_path.is_file():
        return None, False, None
    try:
        ctx = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, False, None
    if not ctx.get("context_injected"):
        return None, False, None
    return ctx, False, ctx.get("context_pack_version")


def _verify_context_sha256s(ctx: Dict[str, Any], alpha_export_dir: Path) -> bool:
    """Verify SHA256 of injected files in alpha_export_dir against the context manifest."""
    for field, file_field in (
        ("alpha_candle_sha256", "alpha_candle_file"),
        ("alpha_news_sha256", "alpha_news_file"),
        ("alpha_calendar_sha256", "alpha_calendar_file"),
    ):
        expected = ctx.get(field)
        fname = ctx.get(file_field)
        if not expected or not fname:
            # Try non-alpha prefixed fields as fallback
            base = field.replace("alpha_", "")
            expected = ctx.get(base)
            fname = ctx.get(file_field.replace("alpha_", ""))
        if not expected or not fname:
            return False
        fpath = alpha_export_dir / fname
        if not fpath.is_file():
            return False
        h = hashlib.sha256()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            return False
    return True


def _write_checksums(out_dir: Path, names: List[str]) -> None:
    lines = []
    for n in sorted(names):
        if n == "checksums.sha256":
            continue
        digest = _sha256_file(out_dir / n)
        lines.append(f"{digest}  {n}")
    (out_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_build(
    *,
    alpha_export_dir: Path,
    input_pack: Optional[Path],
    local_root: Path,
    instrument: str,
    primary_granularity: str,
    spread_pips: float,
    slippage_pips: float,
    rr_multiple: float,
    write_result_pack: bool,
    metrics_session: str = "NY",
    session_bucket: str = "NY_OPEN_SECONDARY_PROPOSED",
    strategy_name: Optional[str] = None,
) -> Dict[str, Any]:
    alpha_export_dir = alpha_export_dir.expanduser().resolve()
    local_root = local_root.expanduser().resolve()
    data_dir = local_root / "data"
    out_dir = local_root / "outputs"
    rep_dir = local_root / "reports"
    for d in (data_dir, out_dir, rep_dir):
        d.mkdir(parents=True, exist_ok=True)

    manifest_alpha = json.loads((alpha_export_dir / "phase8l_alpha_export_manifest.json").read_text(encoding="utf-8"))

    # Phase 8AA: load context manifest if injected
    ctx_manifest, _, ctx_pack_version = _load_phase8aa_context_manifest()
    phase8aa_injected = bool(ctx_manifest and ctx_manifest.get("context_injected"))
    ctx_sha256_verified = False
    if phase8aa_injected and ctx_manifest is not None:
        ctx_sha256_verified = _verify_context_sha256s(ctx_manifest, alpha_export_dir)
        if not ctx_sha256_verified:
            raise RuntimeError("CONTEXT_VERIFICATION_FAILED:phase8aa_sha256_mismatch")

    df, ds_meta = build_dataset_from_alpha_export(
        export_dir=alpha_export_dir,
        primary_granularity=primary_granularity,
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
    )
    parquet_path = data_dir / "phase8l_research_dataset.parquet"
    df.to_parquet(parquet_path, index=False)
    sample_csv = data_dir / "phase8l_research_dataset_sample.csv"
    df.head(5000).to_csv(sample_csv, index=False)

    input_pack_resolved = None
    if input_pack is not None:
        p = input_pack.expanduser().resolve()
        if p.is_dir():
            input_pack_resolved = p

    ds_meta["input_pack"] = str(input_pack_resolved) if input_pack_resolved else None
    ds_meta["granularities"] = [primary_granularity.upper()]
    (data_dir / "phase8l_dataset_manifest.json").write_text(json.dumps(ds_meta, indent=2), encoding="utf-8")

    replay = run_full_replay(
        dataset=df,
        input_pack=input_pack_resolved,
        instrument=instrument,
        granularity=primary_granularity,
        spread_pips=spread_pips,
        slippage_pips=slippage_pips,
        rr_multiple=rr_multiple,
    )
    ny_trades = replay["ny_session"]["trades"]
    ld_trades = replay["london_session"]["trades"]
    ny_meta = replay["ny_session"]["meta"]
    ld_meta = replay["london_session"]["meta"]

    metrics = compute_metrics_bundle(
        ny_trades=ny_trades,
        london_trades=ld_trades,
        news_available=bool(ds_meta.get("news_reconstruction_available")),
        calendar_available=bool(ds_meta.get("calendar_reconstruction_available")),
    )
    ms = (metrics_session or "NY").strip().upper()
    if ms == "LONDON":
        primary_bucket = metrics["london"]
        primary_meta = ld_meta
        primary_trades = ld_trades
        session_label = "LONDON_PRIMARY"
    else:
        primary_bucket = metrics["ny"]
        primary_meta = ny_meta
        primary_trades = ny_trades
        session_label = "NY_OPEN_SECONDARY_PROPOSED"

    months = primary_bucket["month_by_month_stats"]
    rec_label = pick_recommendation(
        expectancy=float(primary_bucket["expectancy_r"]),
        resolved=int(primary_bucket["resolved_count"]),
        months=months,
    )

    agg = {
        "candidate_count": primary_bucket["candidate_count"],
        "resolved_count": primary_bucket["resolved_count"],
        "win_count": primary_bucket["win_count"],
        "loss_count": primary_bucket["loss_count"],
        "breakeven_count": primary_bucket["breakeven_count"],
        "win_rate": primary_bucket["win_rate"],
        "expectancy_r": primary_bucket["expectancy_r"],
        "profit_factor_r": primary_bucket["profit_factor_r"],
        "max_loss_streak": primary_bucket["max_loss_streak"],
        "drawdown_proxy_r": primary_bucket["drawdown_proxy_r"],
    }
    summary: Dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase": PHASE,
        "classification": "PASS_ONE_CLICK_RESEARCH_ENVIRONMENT_BUILT",
        "machine_role": "5950X",
        "dataset_start_utc": ds_meta["dataset_start_utc"],
        "dataset_end_utc": ds_meta["dataset_end_utc"],
        "instruments": [instrument],
        "granularities": [primary_granularity.upper()],
        "session_bucket": session_bucket,
        "strategy_name": strategy_name or "phase8l_default_session_replay",
        "session_window_utc": primary_meta["session_window_utc"],
        "replay_mode": "exact_context_pack_phase8aa" if (phase8aa_injected and ctx_sha256_verified) else primary_meta["replay_mode"],
        "exact_strategy_replay": bool(primary_meta.get("exact_replay_possible")) or (phase8aa_injected and ctx_sha256_verified),
        "phase8aa_context_injected": phase8aa_injected,
        "context_pack_version": ctx_pack_version if phase8aa_injected else None,
        "context_manifest_sha256_verified": ctx_sha256_verified,
        "candidate_count": agg["candidate_count"],
        "resolved_count": agg["resolved_count"],
        "win_count": agg["win_count"],
        "loss_count": agg["loss_count"],
        "breakeven_count": agg["breakeven_count"],
        "win_rate": agg["win_rate"],
        "expectancy_r": agg["expectancy_r"],
        "profit_factor_r": agg["profit_factor_r"],
        "max_loss_streak": agg["max_loss_streak"],
        "drawdown_proxy_r": agg["drawdown_proxy_r"],
        "clean_sample_count": primary_bucket.get("clean_sample_count"),
        "news_reconstruction_available": bool(ds_meta.get("news_reconstruction_available")),
        "calendar_reconstruction_available": bool(ds_meta.get("calendar_reconstruction_available")),
        "recommendation_label": rec_label,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "london_reference": metrics["london"],
        "ny_session_detail": metrics["ny"],
        "metrics_session": ms,
        "primary_session_label": session_label,
    }

    recommendation = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "classification": summary["classification"],
        "recommendation_label": rec_label,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "notes": "Research-only; Daily Overview permission not emulated as live unlock.",
    }

    run_manifest = {
        "generated_at_utc": summary["generated_at_utc"],
        "phase": PHASE,
        "machine_role": "5950X",
        "alpha_export_dir": str(alpha_export_dir),
        "input_pack": ds_meta.get("input_pack"),
        "local_root": str(local_root),
        "argv": sys.argv,
        "replay_mode_ny": ny_meta["replay_mode"],
        "replay_mode_london": ld_meta["replay_mode"],
        "metrics_session": ms,
        "requested_session_bucket": session_bucket,
        "dataset_manifest": str(data_dir / "phase8l_dataset_manifest.json"),
    }

    (out_dir / "phase8l_backtest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "phase8l_recommendation.json").write_text(json.dumps(recommendation, indent=2), encoding="utf-8")
    (out_dir / "phase8l_monthly_persistence.json").write_text(
        json.dumps({"months": months, "phase": PHASE, "session": session_label}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "phase8l_daily_persistence.json").write_text(
        json.dumps({"daily": primary_bucket["daily_stats"], "phase": PHASE}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "phase8l_run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    lines = [json.dumps(t, separators=(",", ":")) for t in primary_trades[:2000]]
    (out_dir / "phase8l_replay_samples_compact.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    names = [
        "phase8l_backtest_summary.json",
        "phase8l_recommendation.json",
        "phase8l_monthly_persistence.json",
        "phase8l_daily_persistence.json",
        "phase8l_run_manifest.json",
        "phase8l_replay_samples_compact.jsonl",
    ]
    _write_checksums(out_dir, names)

    pack_path = out_dir / "phase8l_result_pack.tar.gz"
    if write_result_pack:
        with tarfile.open(pack_path, mode="w:gz") as tf:
            for n in names + ["checksums.sha256"]:
                p = out_dir / n
                if p.is_file():
                    tf.add(p, arcname=n)

    return {
        "ok": True,
        "summary_path": str(out_dir / "phase8l_backtest_summary.json"),
        "result_pack": str(pack_path) if write_result_pack else None,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8L local research environment build.")
    parser.add_argument("--alpha-export-dir", type=Path, required=True)
    parser.add_argument("--input-pack", type=Path, default=None, help="Optional Phase 8J handoff pack directory.")
    parser.add_argument(
        "--local-root",
        type=Path,
        default=Path(r"C:\Users\gavin\fxg-research\phase8l_environment"),
    )
    parser.add_argument("--instrument", type=str, default="EUR_USD")
    parser.add_argument("--primary-granularity", type=str, default="M15")
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--slippage-pips", type=float, default=0.5)
    parser.add_argument("--rr-multiple", type=float, default=2.0)
    parser.add_argument("--write-result-pack", action="store_true")
    parser.add_argument(
        "--metrics-session",
        choices=("NY", "LONDON"),
        default="NY",
        help="Which session bucket supplies headline metrics, persistence, and compact samples.",
    )
    parser.add_argument(
        "--session-bucket",
        type=str,
        default="NY_OPEN_SECONDARY_PROPOSED",
        help="Recorded session label for the job (e.g. LONDON_OPEN, NY_OPEN_SECONDARY_PROPOSED).",
    )
    parser.add_argument("--strategy-name", type=str, default=None, help="Research strategy id for dashboard indexing.")
    args = parser.parse_args()

    try:
        res = run_build(
            alpha_export_dir=args.alpha_export_dir,
            input_pack=args.input_pack,
            local_root=args.local_root,
            instrument=args.instrument,
            primary_granularity=args.primary_granularity,
            spread_pips=float(args.spread_pips),
            slippage_pips=float(args.slippage_pips),
            rr_multiple=float(args.rr_multiple),
            write_result_pack=bool(args.write_result_pack),
            metrics_session=args.metrics_session,
            session_bucket=args.session_bucket,
            strategy_name=args.strategy_name,
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
