#!/usr/bin/env python3
"""
End-to-end bridge verification with per-target support.
- Runs path wiring, generates test signal (with optional fanout)
- Verifies signal_id appears in the correct bridge log for each target
- Clear diagnostics if not found
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from utils.tail_jsonl import tail_jsonl, read_last_n_jsonl

LOGS_BASE = os.path.expanduser("~/gcloud-system/logs")
STALE_MTIME_THRESHOLD = 30


def _load_config():
    cfg_path = os.path.join(PROJECT_ROOT, "configs", "bridge_accounts.json")
    if not os.path.exists(cfg_path):
        return {}
    with open(cfg_path, "r") as f:
        return json.load(f)


def _bridge_log_for_account(account_id: str) -> str:
    cfg = _load_config()
    for a in cfg.get("accounts", []):
        if (a.get("id") or a.get("account_id")) == account_id:
            log_file = a.get("bridge_log_file") or f"{account_id}_bridge_log.jsonl"
            return os.path.join(LOGS_BASE, log_file)
    return os.path.join(LOGS_BASE, f"{account_id}_bridge_log.jsonl")


def _signal_file_for_account(account_id: str) -> str:
    cfg = _load_config()
    for a in cfg.get("accounts", []):
        if (a.get("id") or a.get("account_id")) == account_id:
            fname = a.get("mt5_signal_file") or "signals.jsonl"
            return os.path.join(LOGS_BASE, fname)
    return os.path.join(LOGS_BASE, "signals.jsonl")


def run(cmd: str, cwd: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout or "", r.stderr or ""


def _signal_in_file(signal_id: str, path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        entries = read_last_n_jsonl(path, 500)
        return any(e.get("signal_id") == signal_id for e in entries)
    except Exception:
        return False


def _print_diagnostics(signal_id: str, account_id: str, last_events: list, bridge_log_path: str):
    print(f"\n=== DIAGNOSTICS for {account_id} ===\n")
    if os.path.exists(bridge_log_path):
        realpath = os.path.realpath(bridge_log_path)
        mtime = os.path.getmtime(bridge_log_path)
        print(f"Bridge log: {bridge_log_path}")
        print(f"Realpath:   {realpath}")
        print(f"Mtime:      {datetime.fromtimestamp(mtime).isoformat()}")
    else:
        print(f"Bridge log NOT FOUND: {bridge_log_path}")
    print("\nLast 20 SIGNAL events (id, msg):")
    for ev in last_events[-20:]:
        print(f"  id={ev.get('id','')} msg={(ev.get('msg') or ev.get('message',''))[:60]}")
    sig_file = _signal_file_for_account(account_id)
    in_sig = _signal_in_file(signal_id, sig_file)
    print(f"\nSignal {signal_id[:12]}... in {sig_file}: {'YES' if in_sig else 'NO'}")
    print("\nLIKELY CAUSES:")
    print("  - EA not running or InpBridgeAccount mismatch")
    print("  - Wrong signal file path in EA")
    print("  - Bridge log symlink broken")


def watch_for_signal_in_log(
    signal_id: str,
    bridge_log_path: str,
    timeout: int = 90,
    poll_interval: float = 1.0,
) -> bool:
    last_pos = 0
    last_events = []
    last_mtime = 0.0
    last_mtime_change = time.time()

    if not os.path.exists(bridge_log_path):
        print(f"Bridge log not found: {bridge_log_path}")
        return False

    start = time.time()
    while time.time() - start < timeout:
        if not os.path.exists(bridge_log_path):
            time.sleep(poll_interval)
            continue

        current_mtime = os.path.getmtime(bridge_log_path)
        if current_mtime != last_mtime:
            last_mtime = current_mtime
            last_mtime_change = time.time()

        if (time.time() - last_mtime_change) > STALE_MTIME_THRESHOLD:
            print(f"FAIL-FAST: Bridge log unchanged for {STALE_MTIME_THRESHOLD}s")
            _print_diagnostics(signal_id, "?", last_events, bridge_log_path)
            return False

        entries, last_pos = tail_jsonl(bridge_log_path, last_pos, max_lines=500)
        for entry in entries:
            if entry.get("type") == "SIGNAL" and entry.get("id") == signal_id:
                return True
            if entry.get("type") == "SIGNAL":
                last_events.append(entry)
                last_events = last_events[-50:]

        time.sleep(poll_interval)

    _print_diagnostics(signal_id, "?", last_events, bridge_log_path)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end bridge verification (multi-target)")
    parser.add_argument("--bridge-account", type=str, default="prop_02", help="Account for single-target test")
    parser.add_argument("--fanout", action="store_true", help="Test fanout to all enabled targets")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--no-wire", action="store_true", help="Skip path wiring")
    args = parser.parse_args()

    if args.fanout:
        cfg = _load_config()
        rules = cfg.get("routing_rules") or cfg.get("fanout") or {}
        targets = rules.get("fanout_targets") or rules.get("targets") or ["prop_02", "citytraders"]
        accounts = {a.get("id") or a.get("account_id"): a for a in cfg.get("accounts", [])}
        targets = [t for t in targets if accounts.get(t, {}).get("enabled", False)]
        if not targets:
            targets = ["prop_02", "citytraders"]
    else:
        targets = [args.bridge_account]

    print("Step 1: Path wiring...")
    if not args.no_wire:
        code, out, err = run("python3 scripts/bridge_wire_paths.py")
        if code != 0:
            print(out, err)
            return 1
        print(out)
    else:
        code, out, _ = run("python3 scripts/bridge_wire_paths.py --report")
        if code != 0:
            print(out)
            return 1

    print("Step 2: Generate test signal...")
    cmd = "python3 scripts/generate_test_signal.py --bridge-account prop_02 --machine"
    if args.fanout:
        cmd = "python3 scripts/generate_test_signal.py --fanout --machine"
    code, out, err = run(cmd)
    if code != 0:
        print(out, err)
        return 1
    signal_id = out.strip()
    if not signal_id or len(signal_id) < 20:
        print("Could not get signal_id. Output:", repr(out))
        return 1
    print(f"Emitted signal_id: {signal_id[:20]}...")

    print(f"Step 3: Verify each target (timeout={args.timeout}s)...")
    all_ok = True
    for acc_id in targets:
        bridge_log = _bridge_log_for_account(acc_id)
        print(f"  Checking {acc_id} -> {bridge_log}")
        if watch_for_signal_in_log(signal_id, bridge_log, timeout=args.timeout):
            print(f"  OK: {acc_id}")
        else:
            print(f"  FAIL: {acc_id}")
            all_ok = False

    if all_ok:
        print(f"\nBRIDGE_OK signal_id={signal_id} accounts={','.join(targets)}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
