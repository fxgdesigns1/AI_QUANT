#!/usr/bin/env python3
"""
Phase 8O: discover exact live strategy, candidate, gate, and indicator paths.

This script is intentionally read-only. It proves paths from source text and
fails closed when required live logic cannot be resolved.
"""

from __future__ import annotations

import argparse
import ast
import json
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PHASE = "Phase 8O"
PASS_CLASSIFICATION = "PASS_EXACT_LOGIC_DISCOVERY_COMPLETE"
FAIL_CLASSIFICATION = "FAIL_CLOSED_STRATEGY_LOGIC_NOT_FOUND"

DEFAULT_SEARCH_ROOTS = (
    "src",
    "scripts",
    "runtime",
    "ARTIFACTS",
    "docs",
    "tests",
)

REQUIRED_FIELDS = (
    "candidate_generation_path",
    "entry_logic_path",
    "stop_loss_logic_path",
    "take_profit_logic_path",
    "indicator_logic_path",
    "news_gate_logic_path",
    "calendar_gate_logic_path",
    "session_filter_logic_path",
    "pair_session_policy_path",
)


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def is_phase8o_tooling(path: Path, root: Path) -> bool:
    rel_path = rel(path, root)
    return (
        rel_path.startswith("scripts/phase8o_")
        or rel_path.startswith("tests/test_phase8o_")
        or rel_path == "docs/runbooks/PHASE8O_EXACT_STRATEGY_REPLAY.md"
    )


def iter_candidate_files(root: Path) -> Iterable[Path]:
    suffixes = {".py", ".yaml", ".yml", ".json", ".jsonl", ".md", ".ps1", ".sh"}
    for base_name in DEFAULT_SEARCH_ROOTS:
        base = root / base_name
        if not base.exists():
            continue
        if base.is_file() and base.suffix.lower() in suffixes:
            yield base
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                yield path
    wt = root / "working_trading_system.py"
    if wt.is_file():
        yield wt
    nm = root / "news_manager.py"
    if nm.is_file():
        yield nm


def first_file_with(root: Path, files: Sequence[Path], required: Sequence[str]) -> Optional[str]:
    for path in files:
        if is_phase8o_tooling(path, root):
            continue
        text = safe_read_text(path)
        if all(token in text for token in required):
            return rel(path, root)
    return None


def all_files_with(root: Path, files: Sequence[Path], required: Sequence[str]) -> List[str]:
    found: List[str] = []
    for path in files:
        if is_phase8o_tooling(path, root):
            continue
        text = safe_read_text(path)
        if all(token in text for token in required):
            found.append(rel(path, root))
    return sorted(set(found))


@dataclass(frozen=True)
class StrategyFunctionEvidence:
    path: str
    classes: List[str]
    has_analyze_market: bool
    emits_trade_signal: bool
    has_entry_stop_tp: bool


def inspect_strategy_file(path: Path, root: Path) -> Optional[StrategyFunctionEvidence]:
    if path.suffix.lower() != ".py":
        return None
    if is_phase8o_tooling(path, root):
        return None
    rel_path = rel(path, root)
    if not rel_path.startswith("src/strategies/"):
        return None
    text = safe_read_text(path)
    if "def analyze_market" not in text:
        return None
    classes: List[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_analyze = any(
                    isinstance(child, ast.FunctionDef) and child.name == "analyze_market"
                    for child in node.body
                )
                if has_analyze:
                    classes.append(node.name)
    return StrategyFunctionEvidence(
        path=rel_path,
        classes=classes,
        has_analyze_market=True,
        emits_trade_signal="TradeSignal(" in text,
        has_entry_stop_tp=all(k in text for k in ("entry_price", "stop_loss", "take_profit")),
    )


def discover(root: Path) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    files = list(dict.fromkeys(iter_candidate_files(root)))
    py_files = [p for p in files if p.suffix.lower() == ".py"]

    strategy_evidence = [
        e for p in py_files for e in [inspect_strategy_file(p, root)] if e is not None
    ]
    strategy_paths_found = [e.__dict__ for e in strategy_evidence]
    signal_strategy_paths = [
        e.path for e in strategy_evidence if e.emits_trade_signal and e.has_entry_stop_tp
    ]

    candidate_generation_path = first_file_with(
        root,
        files,
        ("strategy.analyze_market", "trade_selector.select_trades"),
    )
    if candidate_generation_path is None:
        candidate_generation_path = first_file_with(
            root,
            files,
            ("analyze_market", "TradeSelector", "select_trades"),
        )

    trade_selector_path = first_file_with(root, files, ("class TradeSelector", "calculate_score"))
    entry_logic_path = signal_strategy_paths or all_files_with(root, py_files, ("entry_price", "TradeSignal("))
    stop_loss_logic_path = signal_strategy_paths or all_files_with(root, py_files, ("stop_loss", "TradeSignal("))
    take_profit_logic_path = signal_strategy_paths or all_files_with(root, py_files, ("take_profit", "TradeSignal("))

    indicator_logic_path = first_file_with(root, files, ("def add_indicators", "atr_14", "rsi_14"))
    if indicator_logic_path is None:
        indicator_logic_path = first_file_with(root, files, ("calculate_rsi", "calculate_ema"))

    news_gate_logic_path = first_file_with(root, files, ("fetch_news_with_registry", "is_embargo"))
    if news_gate_logic_path is None:
        news_gate_logic_path = first_file_with(root, files, ("news_embargo", "should_allow_trade"))

    calendar_gate_logic_path = first_file_with(
        root,
        files,
        ("fetch_tradingeconomics_calendar_rows", "fetch_finnhub_calendar_rows"),
    )
    if calendar_gate_logic_path is None:
        calendar_gate_logic_path = first_file_with(root, files, ("class NewsManager", "refresh_calendar"))

    session_filter_logic_path = first_file_with(root, files, ("should_allow_trade", "_classify_session"))
    if session_filter_logic_path is None:
        session_filter_logic_path = first_file_with(root, files, ("SESSION_WINDOWS", "NY_OPEN_SECONDARY_PROPOSED"))

    pair_session_policy_path = first_file_with(root, files, ("session_preference", "instruments"))
    if pair_session_policy_path is None:
        pair_session_policy_path = first_file_with(root, files, ("pair_session_scorecard", "session_bucket"))

    archived_candidate_inventory = root / "ARTIFACTS" / "performance" / "latest_phase8h_archived_candidate_inventory.json"
    pair_session_scorecard = root / "ARTIFACTS" / "performance" / "pair_session_scorecard.json"
    pair_session_review = root / "ARTIFACTS" / "performance" / "pair_session_paper_review_log.jsonl"

    evidence_paths: Dict[str, Any] = {
        "candidate_generation_path": candidate_generation_path,
        "trade_selector_path": trade_selector_path,
        "entry_logic_path": entry_logic_path,
        "stop_loss_logic_path": stop_loss_logic_path,
        "take_profit_logic_path": take_profit_logic_path,
        "indicator_logic_path": indicator_logic_path,
        "news_gate_logic_path": news_gate_logic_path,
        "calendar_gate_logic_path": calendar_gate_logic_path,
        "session_filter_logic_path": session_filter_logic_path,
        "pair_session_policy_path": pair_session_policy_path,
    }

    missing_logic: List[str] = []
    for key in REQUIRED_FIELDS:
        value = evidence_paths.get(key)
        if not value:
            missing_logic.append(key)
    if not strategy_paths_found:
        missing_logic.append("strategy_paths_found")
    if not trade_selector_path:
        missing_logic.append("candidate_scoring_logic")

    a_plus_focus_paths = all_files_with(root, files, ("A+ FOCUS",))
    if not a_plus_focus_paths:
        missing_logic.append("a_plus_focus_classification")

    exact_replay_possible = not missing_logic
    classification = PASS_CLASSIFICATION if exact_replay_possible else FAIL_CLASSIFICATION

    return {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": classification,
        "repo_root": str(root),
        "hostname": socket.gethostname(),
        "strategy_paths_found": strategy_paths_found,
        **evidence_paths,
        "candidate_archive_path": rel(archived_candidate_inventory, root),
        "candidate_archive_exists": archived_candidate_inventory.is_file(),
        "pair_session_artifacts": {
            "pair_session_scorecard": {
                "path": rel(pair_session_scorecard, root),
                "exists": pair_session_scorecard.is_file(),
            },
            "pair_session_paper_review_log": {
                "path": rel(pair_session_review, root),
                "exists": pair_session_review.is_file(),
            },
        },
        "a_plus_focus_paths": a_plus_focus_paths,
        "exact_replay_possible": exact_replay_possible,
        "missing_logic": sorted(set(missing_logic)),
        "fail_closed_reason": None if exact_replay_possible else "missing_required_exact_logic",
        "no_assumptions": True,
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def write_report(report: Dict[str, Any], output: Optional[Path]) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8O exact strategy logic discovery.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()

    report = discover(args.repo_root)
    write_report(report, args.output)
    print(json.dumps(report, indent=2))
    if args.fail_on_missing and not report.get("exact_replay_possible"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
