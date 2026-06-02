"""
Bridge dashboard state emitter (multi-account).
Emits dashboard/bridge_state.json with:
- accounts (with last signals, last log events, connected status per account)
- master_feed oanda_account_id
- routing_rules
"""
import json
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "bridge_accounts.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "bridge_state.json")
LOGS_BASE = os.path.expanduser("~/gcloud-system/logs")
HEALTH_SIGNAL_WITHIN_SECONDS = 120


def _load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _read_last_n(path: str, n: int) -> list:
    if not os.path.exists(path):
        return []
    try:
        sys_path = PROJECT_ROOT
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        from utils.tail_jsonl import read_last_n_jsonl
        return read_last_n_jsonl(path, n)
    except ImportError:
        out = []
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return out[-n:]
        except Exception:
            return []


def emit_bridge_state():
    cfg = _load_config()
    master_feed = cfg.get("master_feed") or {}
    oanda_account_id = master_feed.get("oanda_account_id", "010")
    routing = cfg.get("routing_rules") or cfg.get("fanout") or {}
    fanout_enabled = routing.get("fanout_enabled", routing.get("enabled", False))
    fanout_targets = routing.get("fanout_targets") or routing.get("targets") or []

    state = {
        "schema": "bridge_state_v2",
        "master_feed": {"oanda_account_id": oanda_account_id},
        "routing_rules": {
            "fanout_enabled": fanout_enabled,
            "fanout_targets": fanout_targets,
        },
        "accounts": [],
        "health": "disconnected",
    }

    now = time.time()
    any_connected = False

    for acc in cfg.get("accounts", []):
        acc_id = acc.get("id") or acc.get("account_id")
        if not acc_id:
            continue

        signal_file = acc.get("mt5_signal_file") or "signals.jsonl"
        bridge_log = acc.get("bridge_log_file") or f"{acc_id}_bridge_log.jsonl"
        sig_path = os.path.join(LOGS_BASE, signal_file)
        log_path = os.path.join(LOGS_BASE, bridge_log)

        last_signals = _read_last_n(sig_path, 10)
        log_entries = _read_last_n(log_path, 100)
        signal_events = [e for e in log_entries if e.get("type") == "SIGNAL"]
        last_log_events = signal_events[-20:]

        connected = False
        for ev in signal_events[:5]:
            ts_str = ev.get("ts") or ev.get("timestamp_utc", "")
            if ts_str:
                try:
                    from datetime import datetime
                    s = ts_str[:19]
                    if "." in s.split()[0]:
                        dt = datetime.strptime(s, "%Y.%m.%d %H:%M:%S")
                    else:
                        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                    if (now - dt.timestamp()) < HEALTH_SIGNAL_WITHIN_SECONDS:
                        connected = True
                        any_connected = True
                        break
                except Exception:
                    pass

        acc_state = {
            "id": acc_id,
            "label": acc.get("label"),
            "enabled": acc.get("enabled", False),
            "environment": acc.get("environment"),
            "mt5_signal_file": signal_file,
            "bridge_account_value": acc.get("bridge_account_value", acc_id),
            "connected": connected,
            "last_signals": last_signals[-5:],
            "last_log_events": last_log_events,
            "signals_path": sig_path,
            "log_path": log_path,
            "signals_exists": os.path.exists(sig_path),
            "log_exists": os.path.exists(log_path),
        }
        state["accounts"].append(acc_state)

    if any_connected:
        state["health"] = "connected"

    state["last_50_signals"] = []
    state["last_100_emitted_signals"] = []
    state["ftmo_rules_counts"] = {"accepted": 0, "accepted_dry_run": 0, "rejected": 0, "ftmo_rules": 0}
    state["signals_file"] = {"path": os.path.join(LOGS_BASE, "signals.jsonl"), "exists": os.path.exists(os.path.join(LOGS_BASE, "signals.jsonl"))}
    state["log_file"] = {"path": os.path.join(LOGS_BASE, "ftmo_bridge_log.jsonl"), "exists": os.path.exists(os.path.join(LOGS_BASE, "ftmo_bridge_log.jsonl"))}

    for acc_state in state["accounts"]:
        for ev in acc_state.get("last_log_events", []):
            msg = ev.get("msg") or ev.get("message", "")
            if "ACCEPTED_DRY_RUN" in msg or "Dec:ACCEPTED_DRY_RUN" in msg:
                state["ftmo_rules_counts"]["accepted_dry_run"] += 1
            elif "ACCEPTED" in msg and "DRY_RUN" not in msg and "REJECTED" not in msg:
                state["ftmo_rules_counts"]["accepted"] += 1
            elif "FTMO_RULES" in msg or "FTMO Rules" in msg:
                state["ftmo_rules_counts"]["ftmo_rules"] += 1
            else:
                state["ftmo_rules_counts"]["rejected"] += 1

    all_signals = []
    for acc_state in state["accounts"]:
        all_signals.extend(acc_state.get("last_signals", []))
    all_signals.sort(key=lambda x: x.get("timestamp_utc", ""), reverse=True)
    state["last_100_emitted_signals"] = all_signals[:100]

    all_events = []
    for acc_state in state["accounts"]:
        all_events.extend(acc_state.get("last_log_events", []))
    all_events.sort(key=lambda x: x.get("ts", x.get("timestamp_utc", "")), reverse=True)
    state["last_50_signals"] = all_events[:50]
    state["last_seen_ids"] = list(dict.fromkeys(e.get("id", "") for e in all_events if e.get("id")))[:20]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

    return state
