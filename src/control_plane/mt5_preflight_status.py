"""Read-only MT5 preflight aggregation for operators (telemetry / lock checks only).

Does not prove Windows vs Mac consumer exclusivity or EA execution; those require
operator-side evidence. Never returns PASS unless all strict gates including
consumer exclusivity are satisfied (normally unreachable from API-only probes).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _systemctl_is_active(unit: str) -> bool | None:
    if platform.system() != "Linux":
        return None
    try:
        r = subprocess.run(
            ["systemctl", "is-active", unit, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=6,
        )
        return r.stdout.strip() == "active"
    except Exception:
        return None


def _manual_010_lock_ok() -> tuple[bool, str]:
    """Delegate to manual_execution: same canonical constants as _emit_manual_010_bridge."""
    try:
        from src.core.manual_execution import manual_010_emit_lock_ok

        return manual_010_emit_lock_ok()
    except Exception as exc:
        return False, f"manual_010_emit_lock_ok_error:{exc}"[:200]


def _probe_sidecar_endpoint(base_url: str, headers: dict[str, str], path: str) -> dict[str, Any]:
    try:
        response = requests.get(f"{base_url}{path}", headers=headers, timeout=4)
        return {
            "attempted": True,
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "error": None,
        }
    except requests.RequestException as exc:
        return {
            "attempted": True,
            "ok": False,
            "status_code": None,
            "error": str(exc)[:200],
        }


def _parse_ts_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _read_json_artifact(file_name: str) -> tuple[dict[str, Any] | None, str | None]:
    """Read a JSON artifact from repo ARTIFACTS/ (or artifacts/). Returns (data, absolute_path_str)."""
    root = _repo_root()
    for d in (root / "ARTIFACTS", root / "artifacts"):
        p = d / file_name
        if not p.exists():
            continue
        try:
            return json.loads(p.read_text(encoding="utf-8", errors="replace")), str(p)
        except Exception:
            return None, str(p)
    return None, None


def _artifact_fresh_enough(path_str: str | None, *, max_age_seconds: int) -> bool:
    if not path_str:
        return False
    try:
        p = Path(path_str)
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime) <= timedelta(seconds=max_age_seconds)
    except Exception:
        return False


def _normalize_target_kind(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    return raw if raw in {"home_lan", "remote_overlay"} else None


def _read_windows_consumer_heartbeat(
    *,
    max_age_seconds: int,
) -> dict[str, Any]:
    """Best-effort read of synced Windows consumer heartbeat (fail-open, fail-visible)."""
    hb, hb_path = _read_json_artifact("windows_consumer_heartbeat.json")
    now = datetime.now(timezone.utc)
    out: dict[str, Any] = {
        "present": hb_path is not None,
        "path": hb_path,
        "ok": False,
        "fresh": False,
        "age_seconds": None,
        "ts_utc": None,
        "parse_error": None,
        "schema_version": None,
        "latest_signal_id_seen": None,
        "latest_signal_id_executed_ok": None,
        "latest_signal_id_failed": None,
        "validation_ok_count": None,
        "terminal_rejects_count": None,
        "lock_dedupe_hits_count": None,
        "execution_enabled": None,
        "kill_switch_enabled": None,
        "last_result_code": None,
        "bridge_account": None,
        "ea_name": None,
        "ea_version": None,
        "chart_symbol": None,
    }
    if hb_path is None:
        return out
    if not hb or not isinstance(hb, dict):
        out["parse_error"] = "missing_or_unreadable_json"
        return out

    out["schema_version"] = hb.get("heartbeat_schema_version")
    ts = _parse_ts_utc(hb.get("ts_utc"))
    if not ts:
        out["parse_error"] = "missing_or_invalid_ts_utc"
        return out
    age = int((now - ts).total_seconds())
    out["ts_utc"] = ts.isoformat().replace("+00:00", "Z")
    out["age_seconds"] = age
    out["fresh"] = age <= int(max_age_seconds)
    out["bridge_account"] = hb.get("bridge_account")
    out["ea_name"] = hb.get("ea_name")
    out["ea_version"] = hb.get("ea_version")
    out["chart_symbol"] = hb.get("chart_symbol")
    out["latest_signal_id_seen"] = hb.get("latest_signal_id_seen")
    out["latest_signal_id_executed_ok"] = hb.get("latest_signal_id_executed_ok")
    out["latest_signal_id_failed"] = hb.get("latest_signal_id_failed")
    out["validation_ok_count"] = hb.get("validation_ok_count")
    out["terminal_rejects_count"] = hb.get("terminal_rejects_count")
    out["lock_dedupe_hits_count"] = hb.get("lock_dedupe_hits_count")
    out["execution_enabled"] = hb.get("execution_enabled")
    out["kill_switch_enabled"] = hb.get("kill_switch_enabled")
    out["last_result_code"] = hb.get("last_result_code")

    # "ok" means parseable + schema version known + fresh enough.
    out["ok"] = bool(out["fresh"] and str(out["schema_version"]) in {"1", "1.0"})
    if not out["ok"] and out["fresh"]:
        out["parse_error"] = "unsupported_schema_version"
    return out


def _audit_consumer_path_files(
    *,
    proof_max_age_seconds: int,
    windows_heartbeat_fresh: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    """Return summary, failed_checks, degraded_checks, exact_stop_hint."""
    failed: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    exact_stop_hint = ""

    data, src = _read_json_artifact("active_consumer_paths.json")
    summary: dict[str, Any] = {
        "active_consumer_kind": None,
        "active_consumer_terminal_data_dir": None,
        "active_signal_file_path": None,
        "active_bridge_log_path": None,
        "signal_file_exists": False,
        "bridge_log_exists": False,
        "signal_file_fresh": False,
        "bridge_log_fresh": False,
        "last_signal_id_seen": None,
        "last_bridge_log_signal_id_seen": None,
        "last_update_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifact_path": src,
    }

    if not data or not isinstance(data, dict):
        if windows_heartbeat_fresh:
            degraded.append(
                {
                    "name": "active_consumer_paths_missing",
                    "layer": "consumer_path",
                    "reason": "active_consumer_paths.json missing/unreadable, but windows_consumer_heartbeat is fresh",
                }
            )
            exact_stop_hint = ""
        else:
            failed.append(
                {
                    "name": "active_consumer_paths_missing",
                    "layer": "consumer_path",
                    "reason": "active_consumer_paths.json missing or unreadable",
                }
            )
            exact_stop_hint = "active_terminal_data_dir_unproven"
        return summary, failed, degraded, exact_stop_hint

    summary["active_consumer_kind"] = data.get("active_consumer")
    paths = data.get("paths") if isinstance(data.get("paths"), dict) else {}
    sig_s = paths.get("signals_file") or paths.get("signal_file")
    br_s = paths.get("bridge_log")
    summary["active_signal_file_path"] = sig_s
    summary["active_bridge_log_path"] = br_s

    if not sig_s or not br_s:
        if windows_heartbeat_fresh:
            degraded.append(
                {
                    "name": "active_consumer_paths_incomplete",
                    "layer": "consumer_path",
                    "reason": "active_consumer_paths.json incomplete, but windows_consumer_heartbeat is fresh",
                }
            )
            exact_stop_hint = ""
        else:
            failed.append(
                {
                    "name": "active_consumer_paths_incomplete",
                    "layer": "consumer_path",
                    "reason": "signals_file or bridge_log path missing in active_consumer_paths.json",
                }
            )
            exact_stop_hint = "active_terminal_data_dir_unproven"
        return summary, failed, degraded, exact_stop_hint

    sig_p = Path(str(sig_s))
    br_p = Path(str(br_s))

    summary["signal_file_exists"] = sig_p.is_file()
    summary["bridge_log_exists"] = br_p.is_file()

    if not summary["signal_file_exists"]:
        if windows_heartbeat_fresh:
            degraded.append(
                {
                    "name": "active_consumer_signal_file_missing",
                    "layer": "consumer_path",
                    "reason": f"signal file not found at {sig_p} (windows_consumer_heartbeat is fresh)",
                }
            )
        else:
            failed.append(
                {
                    "name": "active_consumer_signal_file_missing",
                    "layer": "consumer_path",
                    "reason": f"signal file not found at {sig_p}",
                }
            )
            exact_stop_hint = "active_consumer_signal_file_missing"
    if not summary["bridge_log_exists"]:
        if windows_heartbeat_fresh:
            degraded.append(
                {
                    "name": "active_consumer_bridge_log_missing",
                    "layer": "consumer_path",
                    "reason": f"bridge log not found at {br_p} (windows_consumer_heartbeat is fresh)",
                }
            )
        else:
            failed.append(
                {
                    "name": "active_consumer_bridge_log_missing",
                    "layer": "consumer_path",
                    "reason": f"bridge log not found at {br_p}",
                }
            )
            if not exact_stop_hint:
                exact_stop_hint = "active_consumer_bridge_log_missing"

    now = datetime.now(timezone.utc)
    max_age = timedelta(seconds=proof_max_age_seconds)

    def _fresh(path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            return (now - mtime) <= max_age
        except Exception:
            return False

    summary["signal_file_fresh"] = _fresh(sig_p)
    summary["bridge_log_fresh"] = _fresh(br_p)

    if summary["signal_file_exists"] and not summary["signal_file_fresh"]:
        degraded.append(
            {
                "name": "active_consumer_signal_file_stale",
                "layer": "consumer_path",
                "reason": f"signal file mtime older than {proof_max_age_seconds}s",
            }
        )
        if not exact_stop_hint and not windows_heartbeat_fresh:
            exact_stop_hint = "active_consumer_signal_file_stale"
    if summary["bridge_log_exists"] and not summary["bridge_log_fresh"]:
        degraded.append(
            {
                "name": "active_bridge_log_stale",
                "layer": "consumer_path",
                "reason": f"bridge log mtime older than {proof_max_age_seconds}s",
            }
        )
        if not exact_stop_hint and not windows_heartbeat_fresh:
            exact_stop_hint = "active_bridge_log_stale"

    last_sig = None
    last_br = None
    if sig_p.is_file():
        try:
            lines = sig_p.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
            for ln in reversed(lines):
                try:
                    row = json.loads(ln)
                    last_sig = row.get("signal_id") or row.get("id")
                    if last_sig:
                        break
                except Exception:
                    continue
        except Exception:
            pass
    if br_p.is_file():
        try:
            lines = br_p.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
            for ln in reversed(lines):
                try:
                    row = json.loads(ln)
                    sid = row.get("signal_id") or row.get("sid")
                    if sid:
                        last_br = str(sid)
                        break
                except Exception:
                    continue
        except Exception:
            pass

    summary["last_signal_id_seen"] = str(last_sig) if last_sig else None
    summary["last_bridge_log_signal_id_seen"] = str(last_br) if last_br else None

    if summary["signal_file_exists"] and not last_sig:
        degraded.append(
            {
                "name": "consumer_signal_not_seen_recently",
                "layer": "consumer_path",
                "reason": "could not parse a recent signal_id from active signal file tail",
            }
        )

    return summary, failed, degraded, exact_stop_hint


def collect_mt5_preflight() -> dict[str, Any]:
    control_plane_raw = _systemctl_is_active("ai-quant-control-plane")
    runner_raw = _systemctl_is_active("ai-quant-runner")
    control_plane_ok = control_plane_raw is True
    runner_ok = runner_raw is True
    lock_ok, _lock_detail = _manual_010_lock_ok()

    failed_checks: list[dict[str, Any]] = []
    degraded_checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_reason = ""

    sidecar_enabled_configured = os.getenv("MT5_SIDECAR_ENABLED", "false").lower() == "true"
    sidecar_base_url = os.getenv("MT5_SIDECAR_BASE_URL", "").strip().rstrip("/")
    sidecar_base_url_present = bool(sidecar_base_url)
    sidecar_api_key_present = bool(os.getenv("MT5_SIDECAR_API_KEY", "").strip())
    sidecar_probe_attempted = sidecar_enabled_configured and sidecar_base_url_present
    sidecar_headers = {"x-api-key": os.getenv("MT5_SIDECAR_API_KEY", "").strip()} if sidecar_api_key_present else {}

    if sidecar_probe_attempted:
        health_probe = _probe_sidecar_endpoint(sidecar_base_url, sidecar_headers, "/health")
        account_probe = _probe_sidecar_endpoint(sidecar_base_url, sidecar_headers, "/account")
        tick_probe = _probe_sidecar_endpoint(sidecar_base_url, sidecar_headers, "/symbols/EURUSD/tick")
    else:
        health_probe = {"attempted": False, "ok": False, "status_code": None, "error": None}
        account_probe = {"attempted": False, "ok": False, "status_code": None, "error": None}
        tick_probe = {"attempted": False, "ok": False, "status_code": None, "error": None}

    sidecar_health_ok = bool(health_probe["ok"])
    sidecar_account_ok = bool(account_probe["ok"])
    sidecar_tick_ok = bool(tick_probe["ok"])
    sidecar_http_ok = any(
        probe.get("status_code") is not None for probe in (health_probe, account_probe, tick_probe)
    )

    sidecar_error = None
    if not sidecar_enabled_configured:
        sidecar_error = "sidecar_not_enabled"
    elif not sidecar_base_url_present:
        sidecar_error = "sidecar_base_url_missing"
    else:
        for probe in (health_probe, account_probe, tick_probe):
            if probe.get("error"):
                sidecar_error = probe["error"]
                break
        if sidecar_error is None and not all((sidecar_health_ok, sidecar_account_ok, sidecar_tick_ok)):
            sidecar_error = "sidecar_probe_non_200"

    # target_kind must come from authoritative operator-target artifacts only.
    target_kind = "unknown"
    target_kind_source = "unavailable"
    target_kind_resolution_error = ""
    authoritative_target_inputs_used: list[dict[str, Any]] = []
    non_authoritative_target_inputs_ignored: list[dict[str, Any]] = []

    consumer_intended = "unknown"
    consumer_exclusive = False

    # Optional operator-proof integration (fail-closed when stale/missing/contradictory).
    # Reuse existing artifacts already produced by operator workflows (and used by the dashboard).
    proof_max_age_seconds = int(os.getenv("FXG_PREFLIGHT_PROOF_MAX_AGE_S", "1800") or "1800")
    windows_heartbeat = _read_windows_consumer_heartbeat(max_age_seconds=proof_max_age_seconds)
    windows_heartbeat_fresh = bool(windows_heartbeat.get("fresh") is True and windows_heartbeat.get("ok") is True)
    exclusivity, exclusivity_path = _read_json_artifact("consumer_exclusivity_check.json")
    operator_target, operator_target_path = _read_json_artifact("operator_target_kind.json")
    sidecar_target, sidecar_target_path = _read_json_artifact("mac_sidecar_target.json")
    smoke_target, smoke_target_path = _read_json_artifact("mac_remote_access_smoke_latest.json")
    health, health_path = _read_json_artifact("fxg_check_health_result.json")

    excl_ts = _parse_ts_utc((exclusivity or {}).get("ts_utc"))
    excl_fresh = bool(excl_ts and (datetime.now(timezone.utc) - excl_ts) <= timedelta(seconds=proof_max_age_seconds))
    operator_target_fresh = _artifact_fresh_enough(operator_target_path, max_age_seconds=proof_max_age_seconds)
    sidecar_target_fresh = _artifact_fresh_enough(sidecar_target_path, max_age_seconds=proof_max_age_seconds)
    smoke_target_fresh = _artifact_fresh_enough(smoke_target_path, max_age_seconds=proof_max_age_seconds)
    health_fresh = _artifact_fresh_enough(health_path, max_age_seconds=proof_max_age_seconds)

    operator_target_raw = (
        (operator_target or {}).get("selected_target_kind")
        if isinstance(operator_target, dict)
        else None
    )
    sidecar_target_raw = (sidecar_target or {}).get("target_kind") if isinstance(sidecar_target, dict) else None
    smoke_target_raw = (smoke_target or {}).get("target_kind") if isinstance(smoke_target, dict) else None
    health_target_raw = (
        ((health or {}).get("bridge_truth") or {}).get("sidecar_mode")
        if isinstance(health, dict) and isinstance((health or {}).get("bridge_truth"), dict)
        else None
    )
    env_target_raw = os.getenv("FXG_DASHBOARD_TARGET_KIND", "").strip() or None

    authoritative_candidates = [{
        "artifact": "operator_target_kind.json",
        "path": operator_target_path,
        "fresh": operator_target_fresh,
        "raw_target_kind": operator_target_raw,
        "parsed_target_kind": _normalize_target_kind(operator_target_raw),
    }]
    candidate = authoritative_candidates[0]
    if candidate["fresh"] and candidate["parsed_target_kind"] in {"home_lan", "remote_overlay"}:
        target_kind = str(candidate["parsed_target_kind"])
        authoritative_target_inputs_used = [candidate]
        target_kind_source = f"artifact:{Path(str(candidate['path'])).name}"
    else:
        if not operator_target_path:
            target_kind_resolution_error = "missing operator_target_kind.json"
        elif not operator_target_fresh:
            target_kind_resolution_error = f"operator_target_kind.json stale (max_age_s={proof_max_age_seconds})"
        else:
            target_kind_resolution_error = "operator_target_kind.json invalid selected_target_kind"

    non_authoritative_target_inputs_ignored = [
        {
            "input": "fxg_check_health_result.json",
            "path": health_path,
            "fresh": health_fresh,
            "raw_target_kind": health_target_raw,
            "parsed_target_kind": _normalize_target_kind(health_target_raw),
            "reason": "connectivity_evidence_only_not_operator_target_truth",
        },
        {
            "input": "mac_sidecar_target.json",
            "path": sidecar_target_path,
            "fresh": sidecar_target_fresh,
            "raw_target_kind": sidecar_target_raw,
            "parsed_target_kind": _normalize_target_kind(sidecar_target_raw),
            "reason": "legacy_target_artifact_non_authoritative_replaced_by_operator_target_kind",
        },
        {
            "input": "mac_remote_access_smoke_latest.json",
            "path": smoke_target_path,
            "fresh": smoke_target_fresh,
            "raw_target_kind": smoke_target_raw,
            "parsed_target_kind": _normalize_target_kind(smoke_target_raw),
            "reason": "connectivity_probe_output_non_authoritative_for_target_truth",
        },
        {
            "input": "FXG_DASHBOARD_TARGET_KIND",
            "path": "env",
            "fresh": True,
            "raw_target_kind": env_target_raw,
            "parsed_target_kind": _normalize_target_kind(env_target_raw),
            "reason": "env_not_authoritative_for_control_plane_target_kind",
        },
    ]

    if target_kind_resolution_error:
        failed_checks.append(
            {
                "name": "target_kind",
                "layer": "truth",
                "reason": target_kind_resolution_error,
            }
        )

    if exclusivity and health and excl_fresh and health_fresh:
        active_consumer = str(exclusivity.get("active_consumer") or "").strip()
        exclusive = bool(exclusivity.get("exclusive") is True)
        bridge_truth = (health.get("bridge_truth") or {}) if isinstance(health, dict) else {}
        execution_consumer = str(bridge_truth.get("execution_consumer") or "").strip()

        if (
            exclusive
            and active_consumer
            and active_consumer == execution_consumer
        ):
            consumer_intended = active_consumer
            consumer_exclusive = True
        else:
            failed_checks.append(
                {
                    "name": "consumer_exclusive",
                    "layer": "consumer",
                    "reason": "consumer proof contradictory (exclusive/active_consumer vs bridge_truth mismatch)",
                }
            )
    else:
        if not exclusivity:
            failed_checks.append(
                {"name": "consumer_exclusive", "layer": "consumer", "reason": "missing consumer_exclusivity_check.json"}
            )
        elif not excl_fresh:
            failed_checks.append(
                {
                    "name": "consumer_exclusive",
                    "layer": "consumer",
                    "reason": f"consumer_exclusivity_check.json stale (max_age_s={proof_max_age_seconds})",
                }
            )
        if not health:
            failed_checks.append(
                {"name": "connectivity_evidence", "layer": "telemetry", "reason": "missing fxg_check_health_result.json"}
            )
        elif not health_fresh:
            failed_checks.append(
                {
                    "name": "connectivity_evidence",
                    "layer": "telemetry",
                    "reason": f"fxg_check_health_result.json stale (max_age_s={proof_max_age_seconds})",
                }
            )
    overlay_reachable = bool(
        sidecar_probe_attempted and sidecar_health_ok and sidecar_account_ok and sidecar_tick_ok
    )
    if not sidecar_enabled_configured:
        warnings.append("sidecar_not_enabled")
    elif not sidecar_base_url_present:
        warnings.append("sidecar_base_url_missing")
    elif not sidecar_probe_attempted:
        warnings.append("sidecar_probe_not_attempted")
    elif not sidecar_http_ok:
        warnings.append("sidecar_http_unreachable")
    elif not sidecar_health_ok:
        warnings.append("sidecar_health_probe_failed")
    elif not sidecar_account_ok:
        warnings.append("sidecar_account_probe_failed")
    elif not sidecar_tick_ok:
        warnings.append("sidecar_tick_probe_failed")

    consumer_path_summary, cp_failed, cp_degraded, cp_exact_stop = _audit_consumer_path_files(
        proof_max_age_seconds=proof_max_age_seconds,
        windows_heartbeat_fresh=windows_heartbeat_fresh,
    )
    failed_checks.extend(cp_failed)
    degraded_checks.extend(cp_degraded)

    if control_plane_raw is None or runner_raw is None or not control_plane_ok or not runner_ok:
        mode = "DEGRADED"
        stop_point = "unknown" if (control_plane_raw is None or runner_raw is None) else "producer_fail"
        status = "BLOCKED"
        blocking_reason = "producer_fail"
        failed_checks.append({"name": "services", "layer": "producer", "reason": "control-plane/runner not active"})
    elif not lock_ok:
        mode = "DEGRADED"
        stop_point = "producer_fail"
        status = "BLOCKED"
        blocking_reason = "manual_010_lock_failed"
        failed_checks.append({"name": "manual_010_lock_ok", "layer": "producer", "reason": "fanout/bridge lock missing"})
    elif not sidecar_enabled_configured or not sidecar_base_url_present:
        mode = "NO_REMOTE_CONTROL"
        stop_point = "sidecar_unreachable"
        status = "BLOCKED"
        blocking_reason = "sidecar_unreachable"
        failed_checks.append({"name": "sidecar_reachable", "layer": "telemetry", "reason": str(sidecar_error or "unreachable")})
    elif not overlay_reachable:
        mode = "DEGRADED"
        stop_point = "sidecar_unreachable"
        status = "BLOCKED"
        blocking_reason = "sidecar_unreachable"
        failed_checks.append({"name": "sidecar_reachable", "layer": "telemetry", "reason": str(sidecar_error or "probe_failed")})
    else:
        # Telemetry OK; require explicit consumer proof to pass strict preflight.
        if consumer_exclusive and consumer_intended != "unknown" and target_kind in {"home_lan", "remote_overlay"}:
            mode = "READY"
            stop_point = "none"
            status = "PASS"
            blocking_reason = ""
        else:
            mode = "PARTIAL_REMOTE"
            stop_point = "consumer_path_fail"
            status = "BLOCKED"
            blocking_reason = "mt5_consumer_not_proven"
            if not any(c.get("name") == "consumer_exclusive" for c in failed_checks):
                failed_checks.append(
                    {
                        "name": "consumer_exclusive",
                        "layer": "consumer",
                        "reason": "remote consumer proof missing or stale",
                    }
                )

    exact_stop_point = stop_point
    if cp_exact_stop:
        exact_stop_point = cp_exact_stop
    if cp_failed:
        status = "BLOCKED"
        blocking_reason = blocking_reason or "consumer_path_failure"
        stop_point = "consumer_path_fail"
        if cp_exact_stop:
            exact_stop_point = cp_exact_stop
        if mode == "READY":
            mode = "DEGRADED"

    next_action = (
        "Confirm active MT5 execution consumer (Windows EA vs Mac) on the operator host; "
        "this API cannot prove consumer exclusivity. "
        "If sidecar is disabled, set MT5_SIDECAR_ENABLED and MT5_SIDECAR_BASE_URL only for telemetry probes."
    )
    if control_plane_ok is False:
        next_action = "Restore ai-quant-control-plane (systemctl status / journalctl)."
    elif runner_ok is False:
        next_action = "Restore ai-quant-runner (systemctl status / journalctl)."
    elif not lock_ok:
        next_action = "Restore manual 010 emit lock in src/core/manual_execution.py (fanout=True, bridge_account ftmo_demo2)."

    return {
        "preflight_status": status,
        "status": status,
        "lane": "010",
        "target_kind": target_kind,
        "target_kind_source": target_kind_source,
        "authoritative_target_inputs_used": authoritative_target_inputs_used,
        "non_authoritative_target_inputs_ignored": non_authoritative_target_inputs_ignored,
        "consumer_intended": consumer_intended,
        "consumer_exclusive": consumer_exclusive,
        "blocking_reason": blocking_reason,
        "failed_checks": failed_checks,
        "degraded_checks": degraded_checks,
        "control_plane_ok": control_plane_ok,
        "runner_ok": runner_ok,
        "manual_010_lock_ok": lock_ok,
        "bridge_account": "ftmo_demo2",
        "fanout_ok": lock_ok,
        "sidecar_enabled_configured": sidecar_enabled_configured,
        "sidecar_base_url_present": sidecar_base_url_present,
        "sidecar_api_key_present": sidecar_api_key_present,
        "sidecar_probe_attempted": sidecar_probe_attempted,
        "sidecar_http_ok": sidecar_http_ok,
        "sidecar_health_ok": sidecar_health_ok,
        "sidecar_account_ok": sidecar_account_ok,
        "sidecar_tick_ok": sidecar_tick_ok,
        "sidecar_error": sidecar_error,
        "overlay_reachable": overlay_reachable,
        "mode": mode,
        "stop_point": stop_point,
        "exact_stop_point": exact_stop_point,
        "consumer_path_summary": consumer_path_summary,
        "consumer_runtime_status": {
            "windows_consumer_heartbeat": windows_heartbeat,
            "windows_consumer_fresh_evidence": windows_heartbeat_fresh,
        },
        "next_action": next_action,
        "warnings": warnings,
        "provenance": {
            "sidecar_configured": sidecar_enabled_configured and sidecar_base_url_present,
            "systemctl_available": platform.system() == "Linux",
            "target_kind_source": target_kind_source,
            "consumer_proof": {
                "proof_max_age_seconds": proof_max_age_seconds,
                "exclusivity_path": exclusivity_path,
                "operator_target_path": operator_target_path,
                "sidecar_target_path": sidecar_target_path,
                "smoke_target_path": smoke_target_path,
                "health_path": health_path,
                "windows_consumer_heartbeat_path": windows_heartbeat.get("path"),
                "windows_consumer_heartbeat_fresh": windows_heartbeat.get("fresh"),
                "windows_consumer_heartbeat_ok": windows_heartbeat.get("ok"),
                "exclusivity_ts_utc": (excl_ts.isoformat() if excl_ts else None),
                "exclusivity_fresh": excl_fresh,
                "operator_target_fresh": operator_target_fresh,
                "sidecar_target_fresh": sidecar_target_fresh,
                "smoke_target_fresh": smoke_target_fresh,
                "health_fresh": health_fresh,
            },
            "sidecar_probe_status_codes": {
                "health": health_probe.get("status_code"),
                "account": account_probe.get("status_code"),
                "tick": tick_probe.get("status_code"),
            },
        },
    }
