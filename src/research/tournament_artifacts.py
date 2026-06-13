"""
ALPHA-compatible tournament artifact writers (research-only).
Emits report.json, champions.json, tournament_config_resolved.json alongside tournament_results.json.
"""

from __future__ import annotations

import json
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _score_row(row: Dict[str, Any]) -> float:
    exp = float(row.get("expectancy_r") or 0.0)
    n = int(row.get("total_trades") or 0)
    depth = min(1.0, n / 15.0)
    return exp * depth


def write_tournament_config_resolved(config: Dict[str, Any], path: Path) -> None:
    """Config with absolute paths, suitable for audit trail."""
    safe = copy.deepcopy(config)
    for key in ("_source_path",):
        safe.pop(key, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe, indent=2), encoding="utf-8")


def build_report(tournament_output: Dict[str, Any]) -> Dict[str, Any]:
    results = tournament_output.get("results") or []
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for r in results:
        scored.append((_score_row(r), r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {
        "schema": "fxg.tournament.report.v1",
        "run_id": tournament_output.get("run_id"),
        "started_at": tournament_output.get("started_at"),
        "config_source": tournament_output.get("config_source"),
        "variants_tested": tournament_output.get("variants_tested"),
        "instruments": tournament_output.get("instruments"),
        "results": results,
        "ranked": [r for _, r in scored],
    }


def write_report(tournament_output: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_report(tournament_output), indent=2), encoding="utf-8")


def build_champions(tournament_output: Dict[str, Any], top_n: int = 10) -> Dict[str, Any]:
    results = list(tournament_output.get("results") or [])
    results.sort(key=_score_row, reverse=True)
    champs = []
    for r in results[:top_n]:
        champs.append(
            {
                "variant_id": r.get("variant_id"),
                "strategy": r.get("strategy"),
                "instrument": r.get("instrument"),
                "score": _score_row(r),
                "total_trades": r.get("total_trades"),
                "win_rate": r.get("win_rate"),
                "expectancy_r": r.get("expectancy_r"),
                "max_drawdown": r.get("max_drawdown"),
                "total_pnl": r.get("total_pnl"),
            }
        )
    return {
        "schema": "fxg.tournament.champions.v1",
        "run_id": tournament_output.get("run_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": top_n,
        "champions": champs,
    }


def write_champions(tournament_output: Dict[str, Any], path: Path, top_n: int = 10) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_champions(tournament_output, top_n=top_n), indent=2), encoding="utf-8")
