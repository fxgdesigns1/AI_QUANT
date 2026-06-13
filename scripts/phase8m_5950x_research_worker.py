#!/usr/bin/env python3
"""
Phase 8M: 5950X pull-based research worker.

Polls ALPHA with gcloud compute ssh/scp, runs heavy work locally, and uploads only
compact verified result packs back to ALPHA.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.phase8l_verify_result_pack import verify_result_pack as verify_phase8l_pack  # noqa: E402
from scripts.phase8m_contract import (  # noqa: E402
    ContractError,
    PHASE,
    RESULT_REQUIRED_FILES,
    read_json,
    utc_now_iso_z,
    verify_research_result_pack,
    write_checksums,
    write_json,
)


DEFAULT_LOCAL_ROOT = Path(r"C:\Users\gavin\fxg-research\research_worker")


def _gcloud_executable() -> str:
    """Windows CreateProcess often fails on bare ``gcloud``; use a resolved path."""
    for key in ("GCLOUD_PATH", "CLOUDSDK_GCLOUD_PATH"):
        raw = os.environ.get(key)
        if raw:
            p = Path(raw)
            if p.is_file():
                return str(p.resolve())
    found = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not found:
        raise ContractError(
            "gcloud_not_found: set GCLOUD_PATH to gcloud.cmd or add Google Cloud SDK bin to PATH"
        )
    return str(Path(found).resolve())


def _json_from_output(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ContractError(f"no_json_in_command_output:{text[:200]}")
    return json.loads(text[start : end + 1])


def run_cmd(
    args: Sequence[str],
    *,
    dry_run: bool = False,
    cwd: Optional[Path] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> str:
    printable = " ".join(str(a) for a in args)
    if dry_run:
        return json.dumps({"dry_run": True, "command": printable})
    argv = [str(a) for a in args]
    env = None
    if extra_env:
        env = {**os.environ, **extra_env}
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        exe = argv[0] if argv else ""
        raise ContractError(
            f"executable_not_found_or_bad_path:{exe!s} (WinError 2 / ENOENT). "
            f"cwd={cwd!s}. full_command={printable!s}. detail={exc!s}"
        ) from exc
    if proc.returncode != 0:
        raise ContractError(f"command_failed:{proc.returncode}:{printable}\n{proc.stdout}")
    return proc.stdout


def _run_injector_no_raise(cmd: List[str]) -> Dict[str, Any]:
    """Run phase8aa injector without raising on failure; return result dict."""
    argv = [str(a) for a in cmd]
    try:
        proc = subprocess.run(
            argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        out = proc.stdout or ""
        start = out.find("{")
        end = out.rfind("}")
        result: Dict[str, Any] = {}
        if start >= 0 and end >= start:
            try:
                result = json.loads(out[start : end + 1])
            except json.JSONDecodeError:
                pass
        if proc.returncode != 0:
            result.setdefault("ok", False)
            result["blocked"] = True
            result["exit_code"] = proc.returncode
            result.setdefault("error", out[:500])
        return result
    except FileNotFoundError as exc:
        return {"ok": False, "blocked": True, "error": str(exc)}


def gcloud_ssh(
    *,
    project: str,
    zone: str,
    vm: str,
    command: str,
    dry_run: bool = False,
) -> str:
    return run_cmd(
        [_gcloud_executable(), "compute", "ssh", "--zone", zone, "--project", project, vm, "--command", command],
        dry_run=dry_run,
    )


def gcloud_scp(
    *,
    project: str,
    zone: str,
    source: str,
    dest: str,
    dry_run: bool = False,
) -> str:
    return run_cmd(
        [_gcloud_executable(), "compute", "scp", "--zone", zone, "--project", project, source, dest],
        dry_run=dry_run,
    )


def alpha_python(alpha_repo: str, script: str, args: Sequence[str]) -> str:
    quoted_args = " ".join(args)
    return f"cd {alpha_repo} && sudo -u aiquant {alpha_repo}/.venv/bin/python3 {script} {quoted_args}"


def list_remote_jobs(*, project: str, zone: str, vm: str, alpha_repo: str, dry_run: bool = False) -> Dict[str, Any]:
    out = gcloud_ssh(
        project=project,
        zone=zone,
        vm=vm,
        command=alpha_python(alpha_repo, "scripts/phase8m_list_research_jobs.py", []),
        dry_run=dry_run,
    )
    return _json_from_output(out)


def pick_pending_job(list_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pending = ((list_payload.get("jobs") or {}).get("pending") or [])
    if not pending:
        return None
    pending_sorted = sorted(pending, key=lambda j: str(j.get("created_at_utc") or ""))
    return pending_sorted[0]


def find_pending_job_by_id(list_payload: Dict[str, Any], job_id: str) -> Optional[Dict[str, Any]]:
    pending = ((list_payload.get("jobs") or {}).get("pending") or [])
    for j in pending:
        if str(j.get("job_id") or "") == str(job_id):
            return j
    return None

def remote_claim_job_command(alpha_repo: str, job_id: str) -> str:
    py = (
        "from pathlib import Path;"
        "from scripts.phase8m_contract import DEFAULT_ALPHA_JOB_ROOT,job_file_for,read_json,move_job,utc_now_iso_z;"
        f"job=read_json(job_file_for(DEFAULT_ALPHA_JOB_ROOT,'PENDING','{job_id}'));"
        "move_job(DEFAULT_ALPHA_JOB_ROOT,job,'PENDING','RUNNING',{'updated_at_utc':utc_now_iso_z()});"
        "print('OK')"
    )
    return f"cd {alpha_repo} && sudo -u aiquant {alpha_repo}/.venv/bin/python3 -c \"{py}\""


def remote_fail_job_command(alpha_repo: str, job_id: str, reason: str) -> str:
    safe_reason = reason.replace("\\", "/").replace("'", "").replace('"', "")[:500]
    py = (
        "from scripts.phase8m_contract import DEFAULT_ALPHA_JOB_ROOT,job_file_for,read_json,move_job,utc_now_iso_z;"
        f"job=read_json(job_file_for(DEFAULT_ALPHA_JOB_ROOT,'RUNNING','{job_id}'));"
        f"move_job(DEFAULT_ALPHA_JOB_ROOT,job,'RUNNING','FAILED',{{'updated_at_utc':utc_now_iso_z(),'failure_reason':'{safe_reason}'}});"
        "print('OK')"
    )
    return f"cd {alpha_repo} && sudo -u aiquant {alpha_repo}/.venv/bin/python3 -c \"{py}\""


def _extract_pack(archive: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:gz") as tf:
        try:
            tf.extractall(path=dst, filter="data")
        except TypeError:
            tf.extractall(path=dst)


def _tar_dir_files(root: Path, archive: Path, names: Sequence[str]) -> None:
    with tarfile.open(archive, mode="w:gz") as tf:
        for n in names:
            p = root / n
            if p.is_file():
                tf.add(p, arcname=n)


def _safe_summary_common(job: Dict[str, Any], source_summary: Dict[str, Any]) -> Dict[str, Any]:
    params = job.get("params") or {}
    strat = params.get("strategy_name") or params.get("research_strategy_key") or source_summary.get("strategy_name")
    return {
        "generated_at_utc": utc_now_iso_z(),
        "job_id": job["job_id"],
        "phase": PHASE,
        "job_type": job["job_type"],
        "classification": "RESEARCH_JOB_RESULT",
        "machine_role": "5950X",
        "instrument": params.get("instrument"),
        "granularity": params.get("granularity"),
        "lookback_days": params.get("lookback_days"),
        "session_bucket": source_summary.get("session_bucket") or params.get("session_bucket"),
        "session_window_utc": source_summary.get("session_window_utc") or params.get("session_window_utc"),
        "strategy_name": strat,
        "replay_mode": source_summary.get("replay_mode"),
        "exact_strategy_replay": source_summary.get("exact_strategy_replay"),
        "candidate_count": source_summary.get("candidate_count", 0),
        "clean_sample_count": source_summary.get("clean_sample_count"),
        "expectancy_r": source_summary.get("expectancy_r", 0.0),
        "profit_factor_r": source_summary.get("profit_factor_r", 0.0),
        "max_loss_streak": source_summary.get("max_loss_streak", 0),
        "drawdown_proxy_r": source_summary.get("drawdown_proxy_r", 0.0),
        "recommendation_label": source_summary.get("recommendation_label", "NEEDS_MORE_REPLAY_DATA"),
        "news_reconstruction_available": source_summary.get("news_reconstruction_available"),
        "calendar_reconstruction_available": source_summary.get("calendar_reconstruction_available"),
        "phase8aa_context_injected": bool(source_summary.get("phase8aa_context_injected")),
        "context_pack_version": source_summary.get("context_pack_version"),
        "context_manifest_sha256_verified": bool(source_summary.get("context_manifest_sha256_verified")),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def build_generic_result_pack_from_phase8l(*, job: Dict[str, Any], phase8l_root: Path, out_dir: Path) -> Path:
    phase8l_out = phase8l_root / "outputs"
    verify_phase8l_pack(phase8l_out / "phase8l_result_pack.tar.gz")
    out_dir.mkdir(parents=True, exist_ok=True)
    source_summary = read_json(phase8l_out / "phase8l_backtest_summary.json")
    summary = _safe_summary_common(job, source_summary)
    rec = read_json(phase8l_out / "phase8l_recommendation.json")
    rec.update(
        {
            "phase": PHASE,
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        }
    )
    manifest = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "RESEARCH_JOB_RESULT_PACK",
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "source": "phase8l_backtest",
        "source_result_pack": str(phase8l_out / "phase8l_result_pack.tar.gz"),
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    write_json(out_dir / "backtest_summary.json", summary)
    write_json(out_dir / "recommendation.json", rec)
    write_json(out_dir / "research_job_result_manifest.json", manifest)
    shutil.copy2(phase8l_out / "phase8l_monthly_persistence.json", out_dir / "monthly_persistence.json")
    shutil.copy2(phase8l_out / "phase8l_daily_persistence.json", out_dir / "daily_persistence.json")
    shutil.copy2(phase8l_out / "phase8l_replay_samples_compact.jsonl", out_dir / "replay_samples_compact.jsonl")
    names = sorted(RESULT_REQUIRED_FILES - {"checksums.sha256"})
    write_checksums(out_dir, names)
    archive = out_dir / "research_job_result_pack.tar.gz"
    _tar_dir_files(out_dir, archive, names + ["checksums.sha256"])
    verify_research_result_pack(archive)
    return archive


def build_generic_result_pack_from_phase8k(*, job: Dict[str, Any], phase8k_out: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    source_summary = read_json(phase8k_out / "phase8j_replay_summary.json")
    summary = _safe_summary_common(job, source_summary)
    rec = read_json(phase8k_out / "phase8j_recommendation.json")
    rec.update(
        {
            "phase": PHASE,
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        }
    )
    manifest = {
        "generated_at_utc": utc_now_iso_z(),
        "phase": PHASE,
        "classification": "RESEARCH_JOB_RESULT_PACK",
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "source": "phase8k_replay",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    write_json(out_dir / "backtest_summary.json", summary)
    write_json(out_dir / "recommendation.json", rec)
    write_json(out_dir / "research_job_result_manifest.json", manifest)
    shutil.copy2(phase8k_out / "phase8j_monthly_persistence.json", out_dir / "monthly_persistence.json")
    write_json(out_dir / "daily_persistence.json", {"phase": PHASE, "job_id": job["job_id"], "daily": []})
    shutil.copy2(phase8k_out / "phase8j_replay_samples_compact.jsonl", out_dir / "replay_samples_compact.jsonl")
    names = sorted(RESULT_REQUIRED_FILES - {"checksums.sha256"})
    write_checksums(out_dir, names)
    archive = out_dir / "research_job_result_pack.tar.gz"
    _tar_dir_files(out_dir, archive, names + ["checksums.sha256"])
    verify_research_result_pack(archive)
    return archive


def _inject_context_for_job(
    *,
    job: Dict[str, Any],
    alpha_export: Path,
    workspace: Path,
    instrument: str,
    granularity: str,
) -> Optional[Path]:
    """Run phase8aa_inject_context_pack.py; return path to job_context_manifest.json or None."""
    job_id = str(job["job_id"])
    ctx_out = workspace / "phase8aa_context"
    ctx_out.mkdir(parents=True, exist_ok=True)

    # Derive window from alpha export manifest
    window_start_arg: List[str] = []
    window_end_arg: List[str] = []
    alpha_man = alpha_export / "phase8l_alpha_export_manifest.json"
    if alpha_man.is_file():
        try:
            m = json.loads(alpha_man.read_text(encoding="utf-8"))
            ds = str(m.get("dataset_start_utc") or "")[:10]
            de = str(m.get("dataset_end_utc") or "")[:10]
            if ds:
                window_start_arg = ["--job-window-start", ds]
            if de:
                window_end_arg = ["--job-window-end", de]
        except (json.JSONDecodeError, OSError):
            pass

    injector_cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "phase8aa_inject_context_pack.py"),
        "--job-id", job_id,
        "--instrument", instrument,
        "--granularity", granularity,
        "--alpha-export-dir", str(alpha_export),
        "--output-dir", str(ctx_out),
        *window_start_arg,
        *window_end_arg,
    ]
    result = _run_injector_no_raise(injector_cmd)
    if result.get("blocked") or not result.get("ok"):
        reason = result.get("error") or result.get("reason") or "unknown_injector_failure"
        raise ContractError(f"BLOCKED_NEEDS_CONTEXT:{reason}")

    manifest_path = ctx_out / "job_context_manifest.json"
    if manifest_path.is_file():
        return manifest_path
    # Injector may have returned manifest_path in result
    mp = result.get("manifest_path")
    if mp and Path(mp).is_file():
        return Path(mp)
    return None


def run_local_job(*, job: Dict[str, Any], input_pack: Path, local_root: Path) -> Path:
    job_id = str(job["job_id"])
    workspace = local_root / "jobs" / job_id
    input_dir = workspace / "input"
    output_dir = local_root / "outputs" / job_id
    _extract_pack(input_pack, input_dir)
    alpha_export = input_dir / "alpha_export"
    if not (alpha_export / "phase8l_alpha_export_manifest.json").is_file():
        raise ContractError("input_pack_missing_alpha_export_manifest")

    params = job.get("params") or {}
    if job["job_type"] == "phase8l_backtest":
        phase8l_root = workspace / "phase8l_environment"
        sb = str(params.get("session_bucket") or "NY_OPEN_SECONDARY_PROPOSED")
        metrics_session = "LONDON" if "LONDON" in sb.upper() else "NY"
        strat = params.get("strategy_name") or params.get("research_strategy_key") or "phase8l_default_session_replay"
        rr = float(params.get("rr_multiple") or 2.0)
        instrument = str(params.get("instrument") or "EUR_USD")
        granularity = str(params.get("granularity") or "M15")

        # Phase 8AA: inject context pack before running Phase 8L
        ctx_manifest_path = _inject_context_for_job(
            job=job,
            alpha_export=alpha_export,
            workspace=workspace,
            instrument=instrument,
            granularity=granularity,
        )

        phase8l_env: Dict[str, str] = {}
        if ctx_manifest_path:
            phase8l_env["PHASE8AA_CONTEXT_MANIFEST"] = str(ctx_manifest_path)

        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "phase8l_build_local_research_environment.py"),
            "--alpha-export-dir",
            str(alpha_export),
            "--local-root",
            str(phase8l_root),
            "--instrument",
            instrument,
            "--primary-granularity",
            granularity,
            "--metrics-session",
            metrics_session,
            "--session-bucket",
            sb,
            "--strategy-name",
            str(strat),
            "--rr-multiple",
            str(rr),
            "--write-result-pack",
        ]
        run_cmd(cmd, extra_env=phase8l_env if phase8l_env else None)
        return build_generic_result_pack_from_phase8l(job=job, phase8l_root=phase8l_root, out_dir=output_dir)

    if job["job_type"] == "phase8k_replay":
        handoff = workspace / "empty_handoff_pack"
        handoff.mkdir(parents=True, exist_ok=True)
        write_json(handoff / "manifest.json", {"phase": PHASE, "job_id": job_id, "classification": "EMPTY_HANDOFF_PROXY_ONLY"})
        days = int(params.get("lookback_days") or 180)
        instrument = str(params.get("instrument") or "EUR_USD").upper()
        gran = str(params.get("granularity") or "M15").upper()
        candle_file = alpha_export / f"phase8l_candles_{instrument}_{gran}_{days}d.jsonl.gz"
        if not candle_file.is_file():
            raise ContractError(f"missing_candle_export:{candle_file}")
        phase8k_out = workspace / "phase8k_outputs"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "phase8k_local_ny_eurusd_replay.py"),
            "--input-pack",
            str(handoff),
            "--output-dir",
            str(phase8k_out),
            "--instrument",
            instrument,
            "--granularity",
            gran,
            "--lookback-days",
            str(days),
            "--candles-jsonl-gz",
            str(candle_file),
            "--write-result-pack",
        ]
        run_cmd(cmd)
        return build_generic_result_pack_from_phase8k(job=job, phase8k_out=phase8k_out, out_dir=output_dir)

    raise ContractError(f"unsupported_job_type:{job['job_type']}")


def run_once(
    *,
    project: str,
    zone: str,
    vm: str,
    alpha_repo: str,
    local_root: Path,
    dry_run: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    local_root.mkdir(parents=True, exist_ok=True)
    listing = list_remote_jobs(project=project, zone=zone, vm=vm, alpha_repo=alpha_repo, dry_run=dry_run)
    if dry_run:
        return {"ok": True, "dry_run": True, "would_list_jobs": listing, "would_target_job_id": job_id}
    job_brief = find_pending_job_by_id(listing, job_id) if job_id else pick_pending_job(listing)
    if not job_brief:
        if job_id:
            raise ContractError(f"requested_job_id_not_pending:{job_id}")
        return {"ok": True, "status": "NO_PENDING_JOBS"}
    job_id = str(job_brief["job_id"])
    try:
        gcloud_ssh(project=project, zone=zone, vm=vm, command=remote_claim_job_command(alpha_repo, job_id))
        prep = _json_from_output(
            gcloud_ssh(
                project=project,
                zone=zone,
                vm=vm,
                command=alpha_python(alpha_repo, "scripts/phase8m_prepare_job_data_export.py", ["--job-id", job_id, "--overwrite"]),
            )
        )
        local_pack = local_root / "jobs" / job_id / "phase8m_job_input_pack.tar.gz"
        local_pack.parent.mkdir(parents=True, exist_ok=True)
        remote_pack = str(prep["input_pack"])
        if remote_pack and not remote_pack.startswith("/"):
            remote_pack = f"{alpha_repo.rstrip('/')}/{remote_pack}"
        gcloud_scp(project=project, zone=zone, source=f"{vm}:{remote_pack}", dest=str(local_pack))
        input_extract = local_root / "jobs" / job_id / "peek"
        _extract_pack(local_pack, input_extract)
        job = read_json(input_extract / "phase8m_job.json")
        result_pack = run_local_job(job=job, input_pack=local_pack, local_root=local_root)
        verify_research_result_pack(result_pack)
        remote_result = f"/tmp/phase8m_{job_id}_result_pack.tar.gz"
        gcloud_scp(project=project, zone=zone, source=str(result_pack), dest=f"{vm}:{remote_result}")
        imported = _json_from_output(
            gcloud_ssh(
                project=project,
                zone=zone,
                vm=vm,
                command=alpha_python(alpha_repo, "scripts/phase8m_import_research_result.py", [remote_result]),
            )
        )
        summary = read_json(result_pack.parent / "backtest_summary.json")
        return {"ok": True, "job_id": job_id, "result_pack": str(result_pack), "imported": imported, "summary": summary}
    except Exception as exc:
        try:
            gcloud_ssh(project=project, zone=zone, vm=vm, command=remote_fail_job_command(alpha_repo, job_id, str(exc)))
        except Exception:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Phase 8M 5950X research worker poll cycle.")
    parser.add_argument("--project", default="fxg-ai-trading")
    parser.add_argument("--zone", default="us-central1-a")
    parser.add_argument("--vm", default="fxg-paper-e2-small-main-2026")
    parser.add_argument("--alpha-repo", default="/opt/ai-quant")
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument("--job-id", default=None, help="If set, process only this exact pending job_id (fail if not pending).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        res = run_once(
            project=args.project,
            zone=args.zone,
            vm=args.vm,
            alpha_repo=args.alpha_repo,
            local_root=args.local_root,
            dry_run=bool(args.dry_run),
            job_id=str(args.job_id) if args.job_id else None,
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

