#!/usr/bin/env python3
"""
Phase 8P: apply research-only promote/watch/demote labels to compact result rows.

Pure scoring logic only. This module does not import runtime config, broker APIs, or
execution paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

PHASE = "Phase 8P"

PROMOTE = "PROMOTE_REVIEW_CANDIDATE"
CONTINUE = "CONTINUE_FORWARD_PAPER_REVIEW"
WATCH = "WATCH_ONLY"
DEMOTE = "DEMOTE_RESEARCH_ONLY"
BLOCK = "BLOCK_OR_DOWNGRADE"
FAIL_CLOSED = "FAIL_CLOSED_DATA_INCOMPLETE"

DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "minimum_clean_samples_for_review": 50,
    "preferred_clean_samples_for_review": 100,
    "minimum_expectancy_r_for_review": 0.15,
    "minimum_profit_factor_for_review": 1.2,
    "maximum_loss_streak_for_review": 4,
    "maximum_drawdown_proxy_r_for_review": -6.0,
    "news_calendar_required_for_clean_promotion": True,
}

DEFAULT_INDEX_JSON = Path("ARTIFACTS/performance/research_results_index.json")
DEFAULT_INDEX_JSONL = Path("ARTIFACTS/performance/research_results_index.jsonl")

SAFETY_EXPECTED: Dict[str, Any] = {
    "paper_review_only": True,
    "live_permission": False,
    "ny_live_enabled": False,
    "send_trade_unlock_changed": False,
    "execution_paths_changed": False,
}


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def missing_required_safety(row: Mapping[str, Any]) -> Iterable[str]:
    for key, expected in SAFETY_EXPECTED.items():
        if row.get(key) is not expected:
            yield key


def score_row(row: Mapping[str, Any], thresholds: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        t.update(dict(thresholds))

    out = dict(row)
    safety_bad = list(missing_required_safety(out))
    if safety_bad:
        out["promotion_label"] = FAIL_CLOSED
        out["decision_reason"] = "safety_flags_invalid:" + ",".join(safety_bad)
        return out

    replay_mode = str(out.get("replay_mode") or "").lower()
    classification = str(out.get("classification") or "").lower()
    exact_replay = _bool_or_none(out.get("exact_strategy_replay"))
    if "fail" in replay_mode or classification.startswith("fail"):
        out["promotion_label"] = FAIL_CLOSED
        out["decision_reason"] = "result_failed_closed_or_incomplete"
        return out

    clean_samples = _int_or_none(out.get("clean_sample_count"))
    if clean_samples is None:
        clean_samples = _int_or_none(out.get("candidate_count"))
    expectancy = _float_or_none(out.get("expectancy_r"))
    profit_factor = _float_or_none(out.get("profit_factor_r"))
    loss_streak = _int_or_none(out.get("max_loss_streak"))
    drawdown = _float_or_none(out.get("drawdown_proxy_r"))

    if None in (clean_samples, expectancy, profit_factor, loss_streak, drawdown):
        out["promotion_label"] = FAIL_CLOSED
        out["decision_reason"] = "missing_required_scoring_metrics"
        return out

    if loss_streak > int(t["maximum_loss_streak_for_review"]) or drawdown < float(t["maximum_drawdown_proxy_r_for_review"]):
        out["promotion_label"] = BLOCK
        out["decision_reason"] = "risk_limit_failed"
        return out

    if expectancy < 0 or profit_factor < 1.0:
        out["promotion_label"] = DEMOTE
        out["decision_reason"] = "negative_or_sub_break_even_result"
        return out

    min_samples = int(t["minimum_clean_samples_for_review"])
    preferred_samples = int(t["preferred_clean_samples_for_review"])
    exp_min = float(t["minimum_expectancy_r_for_review"])
    pf_min = float(t["minimum_profit_factor_for_review"])
    strong_metrics = clean_samples >= min_samples and expectancy >= exp_min and profit_factor >= pf_min

    news_ok = _bool_or_none(out.get("news_reconstruction_available"))
    calendar_ok = _bool_or_none(out.get("calendar_reconstruction_available"))
    requires_news_calendar = bool(t["news_calendar_required_for_clean_promotion"])
    news_calendar_ok = (news_ok is True and calendar_ok is True) if requires_news_calendar else True

    if strong_metrics and clean_samples >= preferred_samples and news_calendar_ok and exact_replay is True:
        out["promotion_label"] = PROMOTE
        out["decision_reason"] = "thresholds_passed_exact_replay_with_news_calendar"
    elif strong_metrics:
        out["promotion_label"] = CONTINUE
        reasons = []
        if clean_samples < preferred_samples:
            reasons.append("needs_preferred_sample_depth")
        if exact_replay is not True:
            reasons.append("not_exact_replay")
        if not news_calendar_ok:
            reasons.append("news_calendar_unavailable")
        out["decision_reason"] = ",".join(reasons) or "thresholds_passed_continue_review"
    elif expectancy >= 0.05 and profit_factor >= 1.05:
        out["promotion_label"] = WATCH
        out["decision_reason"] = "positive_but_below_review_thresholds"
    else:
        out["promotion_label"] = DEMOTE
        out["decision_reason"] = "weak_expectancy_or_profit_factor"

    return out


def score_rows(rows: Iterable[Mapping[str, Any]], thresholds: Optional[Mapping[str, Any]] = None) -> list[Dict[str, Any]]:
    return [score_row(row, thresholds=thresholds) for row in rows]


def _label_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        label = str(row.get("promotion_label") or "UNKNOWN")
        counts[label] = counts.get(label, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Phase 8P research result rows.")
    parser.add_argument("--input-jsonl", type=Path, default=DEFAULT_INDEX_JSONL)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_INDEX_JSONL)
    parser.add_argument("--index-json", type=Path, default=DEFAULT_INDEX_JSON)
    args = parser.parse_args()

    try:
        rows = []
        input_jsonl = args.input_jsonl.expanduser()
        output_jsonl = args.output_jsonl.expanduser()
        index_json = args.index_json.expanduser()
        for line in input_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        scored = score_rows(rows)
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        output_jsonl.write_text("\n".join(json.dumps(r, sort_keys=True) for r in scored) + ("\n" if scored else ""), encoding="utf-8")
        if index_json.is_file():
            index = json.loads(index_json.read_text(encoding="utf-8"))
            index["rows"] = scored
            index["row_count"] = len(scored)
            index["promotion_label_counts"] = _label_counts(scored)
            index_json.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"ok": True, "phase": PHASE, "rows_scored": len(scored), "output_jsonl": str(output_jsonl), "index_json": str(index_json)}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
