#!/usr/bin/env python3
"""
Phase 8X: build ranked tournament tables from the research index (compact JSON only).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8p_build_research_dashboard import _dedupe_unique_strategies, _group_leaderboard  # noqa: E402
from scripts.phase8p_index_research_results import DEFAULT_INDEX_JSON, build_index  # noqa: E402
from scripts.phase8p_score_and_label_results import PROMOTE  # noqa: E402

PHASE = "Phase 8X"
DEFAULT_OUT = Path("ARTIFACTS/performance/phase8x_tournament_leaderboard.json")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sort_key(row: Mapping[str, Any]) -> tuple[float, float, float]:
    return (_num(row.get("expectancy_r")), _num(row.get("profit_factor_r")), _num(row.get("clean_sample_count")))


def _exact_promotion_pool(rows: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        rm = str(r.get("replay_mode") or "").lower()
        if "proxy" in rm or rm == "best_available_proxy_reconstruction":
            continue
        if r.get("exact_strategy_replay") is not True:
            continue
        if r.get("promotion_label") != PROMOTE:
            continue
        out.append(dict(r))
    return sorted(out, key=_sort_key, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 8X tournament leaderboard JSON.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--index-json", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    index_path = args.index_json or (repo_root / DEFAULT_INDEX_JSON)
    index_path = index_path if index_path.is_absolute() else repo_root / index_path
    out_path = args.output_json if args.output_json.is_absolute() else repo_root / args.output_json

    try:
        if index_path.is_file():
            index = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            index = build_index(repo_root)

        rows = [dict(r) for r in index.get("rows") or []]
        payload: Dict[str, Any] = {
            "ok": True,
            "phase": PHASE,
            "classification": "PHASE8X_TOURNAMENT_LEADERBOARD",
            "row_count": len(rows),
            "top_by_expectancy": sorted(rows, key=_sort_key, reverse=True)[:100],
            "strategy_instrument_session": _group_leaderboard(
                rows, ["strategy_name", "instrument", "session_bucket", "granularity"]
            )[:80],
            "best_combos_deduped": _dedupe_unique_strategies(rows)[:80],
            "exact_replay_promotion_only": _exact_promotion_pool(rows)[:50],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"ok": True, "phase": PHASE, "output_json": str(out_path), "tables": list(payload.keys())}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
