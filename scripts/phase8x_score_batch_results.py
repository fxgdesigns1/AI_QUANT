#!/usr/bin/env python3
"""
Phase 8X: re-score indexed research rows with Phase 8X tournament promotion thresholds.

Wraps Phase 8P scoring only (no broker, no execution). Updates research_results_index.jsonl
and research_results_index.json when present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8p_index_research_results import DEFAULT_INDEX_JSON, DEFAULT_INDEX_JSONL  # noqa: E402
from scripts.phase8p_score_and_label_results import CONTINUE, PROMOTE, _label_counts, score_rows  # noqa: E402

PHASE = "Phase 8X"

DEFAULT_PROMOTION_GATE: Dict[str, Any] = {
    "minimum_trades": 80,
    "minimum_profit_factor": 1.25,
    "minimum_expectancy_r": 0.10,
    "maximum_drawdown_r": -6.0,
    "maximum_loss_streak": 5,
    "exact_replay_required": True,
    "news_calendar_required": True,
    "sha256_verified_required": True,
    "paper_review_only": True,
    "live_permission": False,
}


def gate_to_score_thresholds(gate: Mapping[str, Any]) -> Dict[str, Any]:
    """Map Phase 8X promotion gate keys to phase8p_score_and_label_results threshold names."""
    return {
        "minimum_clean_samples_for_review": int(gate.get("minimum_trades") or 80),
        "preferred_clean_samples_for_review": max(int(gate.get("minimum_trades") or 80), 100),
        "minimum_expectancy_r_for_review": float(gate.get("minimum_expectancy_r") or 0.10),
        "minimum_profit_factor_for_review": float(gate.get("minimum_profit_factor") or 1.25),
        "maximum_loss_streak_for_review": int(gate.get("maximum_loss_streak") or 5),
        "maximum_drawdown_proxy_r_for_review": float(gate.get("maximum_drawdown_r") or -6.0),
        "news_calendar_required_for_clean_promotion": bool(gate.get("news_calendar_required", True)),
    }


def load_gate(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.is_file():
        return dict(DEFAULT_PROMOTION_GATE)
    data = json.loads(path.read_text(encoding="utf-8"))
    out = dict(DEFAULT_PROMOTION_GATE)
    out.update({k: data[k] for k in data if k in DEFAULT_PROMOTION_GATE})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Phase 8X batch research results.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--input-jsonl", type=Path, default=None)
    parser.add_argument("--index-json", type=Path, default=None)
    parser.add_argument("--promotion-gate-json", type=Path, default=None, help="Optional JSON override for promotion gate.")
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    jsonl = args.input_jsonl or (repo_root / DEFAULT_INDEX_JSONL)
    index_json = args.index_json or (repo_root / DEFAULT_INDEX_JSON)
    jsonl = jsonl if jsonl.is_absolute() else repo_root / jsonl
    index_json = index_json if index_json.is_absolute() else repo_root / index_json

    gate_path = args.promotion_gate_json
    if gate_path is not None and not gate_path.is_absolute():
        gate_path = repo_root / gate_path

    gate = load_gate(gate_path)
    thresholds = gate_to_score_thresholds(gate)

    try:
        if not jsonl.is_file():
            print(json.dumps({"ok": False, "phase": PHASE, "error": f"missing_input_jsonl:{jsonl}"}, indent=2))
            return 1
        rows = []
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        scored = score_rows(rows, thresholds=thresholds)

        # Post-gate: proxy replay rows cannot be promotion candidates (hard tournament rule).
        for r in scored:
            rm = str(r.get("replay_mode") or "").lower()
            is_proxy = "proxy" in rm or rm == "best_available_proxy_reconstruction"
            if is_proxy and r.get("promotion_label") == PROMOTE:
                r["promotion_label"] = CONTINUE
                r["decision_reason"] = "phase8x_proxy_rows_cannot_be_promotion_candidates"

        # Post-gate: phase8aa exact context verification required for PROMOTE_REVIEW_CANDIDATE.
        for r in scored:
            if r.get("promotion_label") != PROMOTE:
                continue
            if not r.get("phase8aa_context_injected"):
                r["promotion_label"] = CONTINUE
                r["decision_reason"] = "phase8x_promote_requires_phase8aa_context_injection"
            elif not r.get("context_manifest_sha256_verified"):
                r["promotion_label"] = CONTINUE
                r["decision_reason"] = "phase8x_promote_requires_context_manifest_sha256_verified"
            elif str(r.get("replay_mode") or "") != "exact_context_pack_phase8aa":
                r["promotion_label"] = CONTINUE
                r["decision_reason"] = "phase8x_promote_requires_replay_mode_exact_context_pack_phase8aa"

        label_counts = _label_counts(scored)
        jsonl.write_text("\n".join(json.dumps(r, sort_keys=True) for r in scored) + ("\n" if scored else ""), encoding="utf-8")
        if index_json.is_file():
            index = json.loads(index_json.read_text(encoding="utf-8"))
            index["rows"] = scored
            index["row_count"] = len(scored)
            index["promotion_label_counts"] = label_counts
            index["phase8x_promotion_gate"] = gate
            index_json.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

        out_path = repo_root / "ARTIFACTS" / "performance" / "phase8x_score_batch_report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "ok": True,
            "phase": PHASE,
            "rows_scored": len(scored),
            "input_jsonl": str(jsonl),
            "index_json": str(index_json),
            "thresholds_applied": thresholds,
            "promotion_gate": gate,
        }
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
