#!/usr/bin/env python3
"""Assemble an ALPHA-compatible research export pack (read-only research artifacts)."""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "configs" / "local_research" / "export_contract.json"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _empty_stub(schema: str, reason: str) -> Dict[str, Any]:
    return {"schema": schema, "empty": True, "reason": reason}


def _summarize_tournament(report: Optional[Dict[str, Any]], champs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    winners = []
    if champs:
        for c in champs.get("champions") or []:
            winners.append(
                {
                    "variant_id": c.get("variant_id"),
                    "instrument": c.get("instrument"),
                    "expectancy_r": c.get("expectancy_r"),
                }
            )
    trade_counts: List[int] = []
    win_rates: List[float] = []
    instruments_set: set[str] = set()
    if report:
        for row in report.get("results") or []:
            trade_counts.append(int(row.get("total_trades") or 0))
            if row.get("win_rate") is not None:
                win_rates.append(float(row["win_rate"]))
            if row.get("instrument"):
                instruments_set.add(str(row["instrument"]))
    return {
        "winner_shapes": winners[:20],
        "trade_counts": trade_counts,
        "win_rates_clip": win_rates[:50],
        "instruments_tested": sorted(instruments_set),
    }


def build_manifest(
    pack_id: str,
    tournament_dir: Path,
    mc_summary_path: Optional[Path],
    import_intent: str,
) -> Dict[str, Any]:
    report = _load_json(tournament_dir / "report.json")
    champs = _load_json(tournament_dir / "champions.json")
    resolved = _load_json(tournament_dir / "tournament_config_resolved.json")
    mc_summary = _load_json(mc_summary_path) if mc_summary_path else None

    su = _summarize_tournament(report, champs)

    exp_r: List[float] = []
    max_dd: List[float] = []
    if report:
        for row in report.get("results") or []:
            if row.get("expectancy_r") is not None:
                exp_r.append(float(row["expectancy_r"]))
            if row.get("max_drawdown") is not None:
                max_dd.append(float(row["max_drawdown"]))

    rr_min = None
    if resolved:
        rr_min = resolved.get("risk_reward")

    variants_tested = report.get("variants_tested") if report else None
    if variants_tested is None and resolved:
        variants_tested = len(resolved.get("variants") or [])

    return {
        "pack_id": pack_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_machine": socket.gethostname(),
        "dataset_coverage_start": None,
        "dataset_coverage_end": None,
        "enrichment_coverage_start": None,
        "enrichment_coverage_end": None,
        "scoring_window": None,
        "mode": "research_pack",
        "instruments_tested": su["instruments_tested"],
        "variants_tested": variants_tested,
        "calendar_included": False,
        "news_included": False,
        "winner_shapes": su["winner_shapes"],
        "trade_counts": su["trade_counts"],
        "win_rates_if_available": su["win_rates_clip"],
        "expectancy_R": sum(exp_r) / len(exp_r) if exp_r else None,
        "max_drawdown_R": max(max_dd) if max_dd else None,
        "rr_min": rr_min,
        "import_intent": import_intent,
        "monte_carlo_run_id": (mc_summary or {}).get("run_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--tournament-dir", type=Path, required=True)
    parser.add_argument("--monte-carlo-summary", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--import-intent", default="review_only")
    args = parser.parse_args()

    if not CONTRACT_PATH.is_file():
        print(f"Missing export contract: {CONTRACT_PATH}", file=sys.stderr)
        return 1

    out = args.output_root / args.pack_id
    out.mkdir(parents=True, exist_ok=True)

    # Required tournament files
    for name in ("report.json", "tournament_config_resolved.json", "champions.json"):
        src = args.tournament_dir / name
        if not src.is_file():
            print(f"Missing required tournament artifact: {src}", file=sys.stderr)
            return 1
        shutil.copy2(src, out / name)

    # tournament_results.json optional but useful
    tr = args.tournament_dir / "tournament_results.json"
    if tr.is_file():
        shutil.copy2(tr, out / "tournament_results.json")

    mc_path = args.monte_carlo_summary
    if mc_path and mc_path.is_file():
        shutil.copy2(mc_path, out / "monte_carlo_summary.json")
        mc_dir = mc_path.parent
        for extra in ("drawdown_distribution.json", "equity_curve_samples.json", "risk_summary.json"):
            p = mc_dir / extra
            if p.is_file():
                shutil.copy2(p, out / extra)
    else:
        stub_mc = {
            "schema": "fxg.monte_carlo.summary.v1",
            "empty": True,
            "reason": "Monte Carlo not run for this pack",
            "run_id": None,
        }
        (out / "monte_carlo_summary.json").write_text(json.dumps(stub_mc, indent=2), encoding="utf-8")

    research_summary = {
        "schema": "fxg.research_summary.v1",
        "pack_id": args.pack_id,
        "tournament_dir": str(args.tournament_dir.resolve()),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "note": "Generated by local research estate; not an execution directive.",
    }
    (out / "research_summary.json").write_text(json.dumps(research_summary, indent=2), encoding="utf-8")

    (out / "regime_matrix.json").write_text(
        json.dumps(_empty_stub("fxg.regime_matrix.v1", "Regime matrix not produced in this run"), indent=2),
        encoding="utf-8",
    )
    (out / "classifier_output.json").write_text(
        json.dumps(_empty_stub("fxg.classifier_output.v1", "Classifier output not produced in this run"), indent=2),
        encoding="utf-8",
    )

    manifest = build_manifest(args.pack_id, args.tournament_dir, mc_path, args.import_intent)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with open(CONTRACT_PATH, encoding="utf-8") as f:
        contract = json.load(f)
    required = contract.get("required_files") or []
    missing = [fn for fn in required if not (out / fn).is_file()]
    if missing:
        print(f"Pack incomplete, missing: {missing}", file=sys.stderr)
        return 1

    latest = args.output_root / "latest_research_summary.json"
    shutil.copy2(out / "research_summary.json", latest)

    print(out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
