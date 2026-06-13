#!/usr/bin/env python3
"""
Phase 8X: queue a Cartesian batch of Phase 8M research jobs (ALPHA queue, 5950X execution).

Creates only validated phase8l_backtest jobs under ARTIFACTS/research_jobs/queue/pending.
No broker orders, no runtime/config edits, no live paths.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    DEFAULT_ALPHA_JOB_ROOT,
    build_job,
    ensure_job_dirs,
    job_file_for,
    utc_now_iso_z,
    write_json,
)
from scripts.phase8s_calendar_budget_guard import evaluate_budget  # noqa: E402

PHASE8X_PHASE = "Phase 8X"
PHASE8Y_MANIFEST_REL = Path("ARTIFACTS") / "performance" / "latest_phase8y_data_coverage_manifest.json"
PHASE8Y_VERIFY_REL = Path("ARTIFACTS") / "performance" / "latest_phase8y_context_pack_verification.json"

DEFAULT_INSTRUMENTS = ("EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD")
DEFAULT_GRANULARITIES = ("M5", "M15", "H1")
DEFAULT_LOOKBACKS = (90, 180, 365)
DEFAULT_SESSIONS = ("LONDON_OPEN", "NY_OPEN", "NY_OPEN_SECONDARY_PROPOSED")
DEFAULT_STRATEGIES = (
    "exact_current_alpha_strategy",
    "session_breakout_with_news_embargo",
    "trend_pullback_with_session_filter",
)

SESSION_WINDOW_UTC: Dict[str, str] = {
    "LONDON_OPEN": "07:00-10:30",
    "NY_OPEN": "13:30-16:00",
    "NY_OPEN_SECONDARY_PROPOSED": "13:30-16:00",
}

STRATEGY_RR_MULTIPLE: Dict[str, float] = {
    "exact_current_alpha_strategy": 2.0,
    "session_breakout_with_news_embargo": 2.0,
    "trend_pullback_with_session_filter": 1.5,
}


def iter_job_specs(
    *,
    instruments: Sequence[str],
    granularities: Sequence[str],
    lookbacks: Sequence[int],
    sessions: Sequence[str],
    strategies: Sequence[str],
) -> Iterable[Dict[str, Any]]:
    for ins in instruments:
        for gran in granularities:
            for lb in lookbacks:
                for sess in sessions:
                    for strat in strategies:
                        yield {
                            "instrument": ins,
                            "granularity": gran,
                            "lookback_days": int(lb),
                            "session_bucket": sess,
                            "session_window_utc": SESSION_WINDOW_UTC[sess],
                            "strategy_name": strat,
                            "research_strategy_key": strat,
                            "rr_multiple": STRATEGY_RR_MULTIPLE.get(strat, 2.0),
                            "phase8x_batch": True,
                        }


def count_jobs(**kwargs: Any) -> int:
    return sum(1 for _ in iter_job_specs(**kwargs))


def _requested_by() -> str:
    return f"{os.getenv('USERNAME') or os.getenv('USER') or 'unknown'}@{socket.gethostname()}"


def assert_calendar_headroom(
    repo_root: Path,
    *,
    max_additional_paid_calls: int,
) -> Dict[str, Any]:
    """Fail-closed if monthly ledger cannot admit ``max_additional_paid_calls`` (Phase 8S)."""
    from scripts.phase8s_calendar_budget_guard import ABSOLUTE_STOP_CALLS  # noqa: E402

    dec = evaluate_budget(repo_root)
    if not dec.allowed:
        raise ContractError(f"calendar_budget_blocked:{dec.reason}")
    paid = int(dec.paid_calls_this_month)
    headroom = ABSOLUTE_STOP_CALLS - paid
    if headroom < int(max_additional_paid_calls):
        raise ContractError(
            f"calendar_headroom_fail_closed:need_at_least_{max_additional_paid_calls}_slots_have_{headroom}"
        )
    return {"ok": True, "paid_calls_this_month": paid, "headroom_to_absolute_stop": headroom}


def assert_phase8y_preflight(
    repo_root: Path,
    *,
    manifest_path: Path,
    max_additional_paid_calls: int,
) -> Dict[str, Any]:
    """Fail-closed unless Phase 8Y manifest marks batch as safe."""
    if not manifest_path.is_absolute():
        manifest_path = (repo_root / manifest_path).resolve()
    if not manifest_path.is_file():
        raise ContractError(f"phase8y_manifest_missing:{manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"phase8y_manifest_invalid_json:{exc}") from exc

    if not bool(manifest.get("safe_to_run_batch")):
        reasons = ",".join(str(x) for x in (manifest.get("fail_closed_reasons") or []))
        raise ContractError(f"phase8y_fail_closed:{reasons or 'safe_to_run_batch_false'}")
    needed = int(manifest.get("estimated_paid_calendar_calls_needed") or 0)
    if needed > int(max_additional_paid_calls):
        raise ContractError(f"phase8y_estimated_paid_calls_exceed_requested_cap:{needed}>{max_additional_paid_calls}")

    verify_path = (repo_root / PHASE8Y_VERIFY_REL).resolve()
    verify_ok = False
    if verify_path.is_file():
        try:
            verify = json.loads(verify_path.read_text(encoding="utf-8"))
            verify_ok = bool(verify.get("all_files_verified"))
        except json.JSONDecodeError:
            verify_ok = False
    if not verify_ok:
        raise ContractError("phase8y_context_pack_not_verified")
    return {
        "ok": True,
        "safe_to_run_batch": True,
        "manifest_path": str(manifest_path),
        "estimated_paid_calendar_calls_needed": needed,
        "context_pack_verified": True,
    }


def create_jobs(
    *,
    repo_root: Path,
    job_root: Path,
    specs: Sequence[Mapping[str, Any]],
    requested_by: str,
    dry_run: bool,
) -> Dict[str, Any]:
    if dry_run:
        return {"ok": True, "dry_run": True, "would_create": len(specs), "phase": PHASE8X_PHASE}
    ensure_job_dirs(job_root)
    created: List[str] = []
    for spec in specs:
        job = build_job(
            job_type="phase8l_backtest",
            requested_by=requested_by,
            params=dict(spec),
        )
        path = job_file_for(job_root, "PENDING", job["job_id"])
        if path.exists():
            raise ContractError(f"job_already_exists:{path}")
        write_json(path, job)
        created.append(job["job_id"])
    return {"ok": True, "created": len(created), "job_ids": created, "phase": PHASE8X_PHASE}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Phase 8X batch research jobs.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--job-root", type=Path, default=None, help="Defaults to <repo>/ARTIFACTS/research_jobs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=0, help="If >0, cap total jobs after Cartesian expansion (stable sort).")
    parser.add_argument("--calendar-api-max-calls", type=int, default=3, help="Required headroom vs Phase 8S absolute stop.")
    parser.add_argument("--skip-calendar-preflight", action="store_true", help="Skip Phase 8S headroom check (tests only).")
    parser.add_argument("--skip-phase8y-preflight", action="store_true", help="Skip Phase 8Y safety gate (tests only).")
    parser.add_argument("--phase8y-manifest", type=Path, default=PHASE8Y_MANIFEST_REL)
    parser.add_argument(
        "--target-manifest-out",
        type=Path,
        default=None,
        help="After successful job creation, write phase8x_active_batch_target.json (job_ids, target_total).",
    )
    parser.add_argument("--instruments", nargs="*", default=list(DEFAULT_INSTRUMENTS))
    parser.add_argument("--granularities", nargs="*", default=list(DEFAULT_GRANULARITIES))
    parser.add_argument("--lookbacks-days", nargs="*", type=int, default=list(DEFAULT_LOOKBACKS))
    parser.add_argument("--sessions", nargs="*", default=list(DEFAULT_SESSIONS))
    parser.add_argument("--strategies", nargs="*", default=list(DEFAULT_STRATEGIES))
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    job_root = (args.job_root or (repo_root / DEFAULT_ALPHA_JOB_ROOT)).expanduser().resolve()

    instruments = tuple(str(x).upper() for x in args.instruments)
    granularities = tuple(str(x).upper() for x in args.granularities)
    lookbacks = tuple(int(x) for x in args.lookbacks_days)
    sessions = tuple(str(x) for x in args.sessions)
    strategies = tuple(str(x) for x in args.strategies)

    for s in sessions:
        if s not in SESSION_WINDOW_UTC:
            print(json.dumps({"ok": False, "error": f"unknown_session_bucket:{s}"}, indent=2))
            return 1

    kwargs = {
        "instruments": instruments,
        "granularities": granularities,
        "lookbacks": lookbacks,
        "sessions": sessions,
        "strategies": strategies,
    }
    total = count_jobs(**kwargs)
    specs = list(iter_job_specs(**kwargs))
    if int(args.max_jobs) > 0:
        specs = specs[: int(args.max_jobs)]
        total = len(specs)

    out: Dict[str, Any] = {
        "ok": True,
        "phase": PHASE8X_PHASE,
        "exact_job_count": total,
        "job_root": str(job_root),
        "matrix": {
            "instruments": list(instruments),
            "granularities": list(granularities),
            "lookbacks_days": list(lookbacks),
            "sessions": list(sessions),
            "strategies": list(strategies),
        },
        "dry_run": bool(args.dry_run),
    }

    try:
        if not args.skip_calendar_preflight:
            out["calendar_preflight"] = assert_calendar_headroom(
                repo_root, max_additional_paid_calls=int(args.calendar_api_max_calls)
            )
        if not args.skip_phase8y_preflight:
            out["phase8y_preflight"] = assert_phase8y_preflight(
                repo_root,
                manifest_path=args.phase8y_manifest,
                max_additional_paid_calls=int(args.calendar_api_max_calls),
            )
        if args.dry_run:
            print(json.dumps(out, indent=2))
            return 0
        res = create_jobs(
            repo_root=repo_root,
            job_root=job_root,
            specs=specs,
            requested_by=_requested_by(),
            dry_run=False,
        )
        out.update(res)
        if args.target_manifest_out and res.get("job_ids"):
            tm_path = args.target_manifest_out if args.target_manifest_out.is_absolute() else (repo_root / args.target_manifest_out)
            tm_path.parent.mkdir(parents=True, exist_ok=True)
            job_ids = list(res["job_ids"])
            tm_payload = {
                "phase": PHASE8X_PHASE,
                "emitted_at_utc": utc_now_iso_z(),
                "target_total": len(job_ids),
                "job_ids": job_ids,
            }
            write_json(tm_path, tm_payload)
            out["target_manifest_path"] = str(tm_path)
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "phase": PHASE8X_PHASE, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
