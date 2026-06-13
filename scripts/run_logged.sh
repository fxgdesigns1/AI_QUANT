#!/usr/bin/env python3
"""
Single canonical command runner that appends ALL stdout/stderr to one log file.

Why Python (despite .sh extension)?
- This workspace is on Windows where `bash` may not be available (WSL not installed).
- We must still enforce the "one canonical log file" rule without introducing a second helper script.

Usage (PowerShell):
  python scripts/run_logged.sh run -- node -v
  python scripts/run_logged.sh run_shell "gcloud --version"

Environment:
  LOG_FILE: override log path (default ARTIFACTS/wiring/DASHBOARD_WIRING.log)
"""

from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
from typing import List


def _utc_ts() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_path() -> str:
    return os.environ.get("LOG_FILE", os.path.join("ARTIFACTS", "wiring", "DASHBOARD_WIRING.log"))


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _append_header(log_file: str, header: str) -> None:
    _ensure_parent(log_file)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n===== " + _utc_ts() + " :: " + header + "\n")


def _tee_process(proc: subprocess.Popen, log_file: str) -> int:
    assert proc.stdout is not None
    _ensure_parent(log_file)
    with open(log_file, "a", encoding="utf-8", errors="replace") as f:
        for line in proc.stdout:
            try:
                sys.stdout.write(line)
            except UnicodeEncodeError:
                # Windows consoles can be cp1252; replace unprintable chars but keep log lossless.
                sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))
            f.write(line)
    return proc.wait()


def run(argv: List[str]) -> int:
    log_file = _log_path()
    # Safe: logs the exact argv list. Caller must not pass secrets as args.
    _append_header(log_file, " ".join(argv))
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return _tee_process(proc, log_file)


def run_shell(cmd: str) -> int:
    log_file = _log_path()
    # Intentionally redact shell payload in header to avoid accidental secret leakage.
    _append_header(log_file, "shell (command redacted in log-safe mode)")
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return _tee_process(proc, log_file)


def main() -> int:
    if len(sys.argv) < 2:
        print("ERROR: missing subcommand: run | run_shell", file=sys.stderr)
        return 2
    sub = sys.argv[1]
    if sub == "run":
        if len(sys.argv) < 3:
            print("ERROR: run requires a command argv", file=sys.stderr)
            return 2
        argv = sys.argv[2:]
        # Allow common separator style: `run -- <cmd> <args...>`
        if argv and argv[0] == "--":
            argv = argv[1:]
        if not argv:
            print("ERROR: run requires a command argv", file=sys.stderr)
            return 2
        return run(argv)
    if sub == "run_shell":
        if len(sys.argv) != 3:
            print("ERROR: run_shell requires exactly one string argument", file=sys.stderr)
            return 2
        return run_shell(sys.argv[2])
    print(f"ERROR: unknown subcommand: {sub}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

