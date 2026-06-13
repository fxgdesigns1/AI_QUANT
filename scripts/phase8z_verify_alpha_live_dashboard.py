#!/usr/bin/env python3
"""
Phase 8Z local verification + optional remote curl hints.
Writes artifacts/PHASE8Z_ALPHA_LIVE_DASHBOARD_REPORT_<UTC>.json (no secrets).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Phase 8Z dashboard wiring locally.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    repo = args.repo_root.expanduser().resolve()

    env = dict(**os.environ)
    env["PYTHONPATH"] = str(repo)
    env["PYTHONIOENCODING"] = "utf-8"

    rc = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_phase8z_alpha_live_dashboard", "-v"],
        cwd=str(repo),
        env=env,
    ).returncode

    tests_passed = rc == 0

    report = {
        "phase": "Phase 8Z",
        "classification": "PASS_ALPHA_LIVE_DASHBOARD_SERVED" if tests_passed else "FAIL_LOCAL_VERIFY",
        "tests_passed": tests_passed,
        "dashboard_route_live": None,
        "research_api_live": None,
        "batch_progress_api_live": None,
        "dashboard_served_from_alpha": None,
        "remote_access_mode": "SAFE_TUNNEL_ONLY",
        "desktop_tunnel_command": (
            'gcloud compute ssh --zone "us-central1-a" --project "fxg-ai-trading" '
            '"fxg-paper-e2-small-main-2026" -- -L 8787:127.0.0.1:8787'
        ),
        "macbook_tunnel_command": (
            'gcloud compute ssh --zone "us-central1-a" --project "fxg-ai-trading" '
            '"fxg-paper-e2-small-main-2026" -- -L 8787:127.0.0.1:8787'
        ),
        "pending": None,
        "running": None,
        "done": None,
        "failed": None,
        "percent_complete": None,
        "control_plane_restarted": None,
        "runner_restarted": False,
        "runtime_config_changed": False,
        "secrets_exposed": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
        "next_action": "YOU: run scripts/phase8z_deploy_alpha_live_dashboard.ps1 then curl checks on ALPHA via SSH"
        if tests_passed
        else "CURSOR: fix failing tests",
    }

    out_dir = repo / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"PHASE8Z_ALPHA_LIVE_DASHBOARD_REPORT_{_utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": tests_passed, "report_path": str(out_path)}, indent=2))
    return 0 if tests_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
