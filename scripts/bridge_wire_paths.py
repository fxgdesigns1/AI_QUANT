#!/usr/bin/env python3
"""
MT5 Bridge path discovery + wiring for multi-terminal (FTMO + CityTraders).

Creates symlinks for:
- signals_prop_02.jsonl, signals_citytraders.jsonl -> each MT5 instance's MQL5/Files
- ftmo_bridge_log.jsonl, citytraders_bridge_log.jsonl <- collected from MT5 into ~/gcloud-system/logs/

Config: configs/bridge_accounts.json (mt5_signal_file, bridge_log_file per account).
Optional: mt5_instances maps account_id -> mql5_files path for multiple Wine instances.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

LOGS_BASE = os.path.expanduser("~/gcloud-system/logs")
DEDUPE_BASE = os.path.join(LOGS_BASE, "dedupe")

MT5_WINE_BASE_DEFAULT = os.path.expanduser(
    "~/Library/Application Support/net.metaquotes.wine.metatrader5"
)


def _load_config() -> dict:
    cfg_path = Path(PROJECT_ROOT) / "configs" / "bridge_accounts.json"
    if not cfg_path.exists():
        return {"accounts": [], "mt5_instances": {}}
    with open(cfg_path, "r") as f:
        return json.load(f)


def _stat_safe(path: str) -> dict | None:
    try:
        st = os.stat(path)
        return {"exists": True, "mtime": st.st_mtime, "size": st.st_size}
    except OSError:
        return None


def discover_mql5_dirs(mt5_root: str) -> list[str]:
    """Return MQL5/Files dirs (EA reads/writes here). Fallback to Common/Files."""
    drive_c = os.path.join(mt5_root, "drive_c")
    program_files = os.path.join(drive_c, "Program Files", "MetaTrader 5")
    mql5_files = os.path.join(program_files, "MQL5", "Files")
    dirs = []
    if os.path.isdir(mql5_files):
        dirs.append(mql5_files)
    terminal_base = os.path.join(drive_c, "users", "user", "AppData", "Roaming", "MetaQuotes", "Terminal")
    if os.path.isdir(terminal_base):
        for name in os.listdir(terminal_base):
            p = os.path.join(terminal_base, name)
            if not os.path.isdir(p):
                continue
            common_files = os.path.join(p, "Common", "Files")
            if os.path.isdir(common_files) and common_files not in dirs:
                dirs.append(common_files)
    if not dirs:
        dirs = [mql5_files] if os.path.isdir(os.path.dirname(mql5_files)) else []
    return dirs


def run_ln_sf(target: str, link_path: str) -> tuple[bool, str]:
    target_abs = os.path.abspath(target)
    link_dir = os.path.dirname(link_path)
    if link_dir and not os.path.exists(link_dir):
        try:
            os.makedirs(link_dir, exist_ok=True)
        except OSError as e:
            return False, str(e)
    try:
        subprocess.run(["ln", "-sf", target_abs, link_path], check=True, capture_output=True, text=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, str(e.stderr or e)
    except FileNotFoundError:
        return False, "ln not found"


def wire(
    write_symlinks: bool = True,
    mt5_root: str | None = None,
) -> dict:
    cfg = _load_config()
    mt5_root = mt5_root or MT5_WINE_BASE_DEFAULT
    mt5_instances = cfg.get("mt5_instances") or {}

    report = {
        "mt5_root": mt5_root,
        "actions": [],
        "errors": [],
        "wired": [],
    }

    if not os.path.isdir(mt5_root):
        report["errors"].append(f"mt5_root missing: {mt5_root}")
        return report

    mql5_dirs = discover_mql5_dirs(mt5_root)
    if not mql5_dirs:
        report["errors"].append("No MQL5/Files or Common/Files found")
        return report

    os.makedirs(LOGS_BASE, exist_ok=True)
    os.makedirs(DEDUPE_BASE, exist_ok=True)

    for acc in cfg.get("accounts", []):
        if not acc.get("enabled", True):
            continue
        acc_id = acc.get("id") or acc.get("account_id")
        if not acc_id:
            continue
        signal_file = acc.get("mt5_signal_file") or "signals.jsonl"
        bridge_log = acc.get("bridge_log_file") or f"{acc_id}_bridge_log.jsonl"

        source_signal = os.path.join(LOGS_BASE, signal_file)
        source_bridge_log = os.path.join(LOGS_BASE, bridge_log)

        mql5_path = mt5_instances.get(acc_id, {}).get("mql5_files")
        if not mql5_path:
            mql5_path = mql5_dirs[0]

        mt5_signal_link = os.path.join(mql5_path, signal_file)
        mt5_bridge_log = os.path.join(mql5_path, bridge_log)

        if write_symlinks:
            ok, err = run_ln_sf(source_signal, mt5_signal_link)
            if ok:
                report["actions"].append(f"Symlink: {mt5_signal_link} -> {source_signal}")
                report["wired"].append({"account": acc_id, "signal_file": signal_file})
            else:
                report["errors"].append(f"Signal symlink {acc_id}: {err}")

            ok, err = run_ln_sf(mt5_bridge_log, source_bridge_log)
            if ok:
                report["actions"].append(f"Symlink: {source_bridge_log} -> {mt5_bridge_log}")
            else:
                report["errors"].append(f"Bridge log symlink {acc_id}: {err}")

        dedupe_dir = os.path.join(DEDUPE_BASE, acc_id)
        os.makedirs(dedupe_dir, exist_ok=True)
        dedupe_mt5 = os.path.join(mql5_path, f"dedupe_{acc_id}")
        if write_symlinks and not os.path.exists(dedupe_mt5):
            ok, _ = run_ln_sf(dedupe_dir, dedupe_mt5)
            if ok:
                report["actions"].append(f"Symlink: {dedupe_mt5} -> {dedupe_dir}")

    signals_default = os.path.join(LOGS_BASE, "signals.jsonl")
    if write_symlinks and os.path.exists(signals_default):
        for mql5_path in mql5_dirs[:1]:
            default_link = os.path.join(mql5_path, "signals.jsonl")
            if not os.path.exists(default_link):
                ok, _ = run_ln_sf(signals_default, default_link)
                if ok:
                    report["actions"].append(f"Symlink: {default_link} -> {signals_default}")

    return report


def print_report(report: dict) -> None:
    print("=== MT5 Bridge Multi-Terminal Wiring ===\n")
    print(f"mt5_root: {report.get('mt5_root')}")
    print(f"logs_base: {LOGS_BASE}\n")
    if report.get("actions"):
        print("Actions:")
        for a in report["actions"]:
            print(f"  - {a}")
        print()
    if report.get("errors"):
        print("Errors:")
        for e in report["errors"]:
            print(f"  - {e}")
        print()
    for w in report.get("wired", []):
        sig = os.path.join(LOGS_BASE, w["signal_file"])
        if os.path.exists(sig):
            st = _stat_safe(sig)
            print(f"{w['account']} signals: {sig} (size={st.get('size', 0)})")


def main() -> int:
    parser = argparse.ArgumentParser(description="MT5 Bridge multi-terminal path wiring")
    parser.add_argument("--report", action="store_true", help="Report only, no symlinks")
    parser.add_argument("--no-report", action="store_true", help="Wire only, no print")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--mt5-root", type=str, default=None)
    args = parser.parse_args()

    write = not args.report
    r = wire(write_symlinks=write, mt5_root=args.mt5_root)

    if args.json:
        print(json.dumps(r, indent=2))
    elif not args.no_report:
        print_report(r)

    return 1 if r.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
