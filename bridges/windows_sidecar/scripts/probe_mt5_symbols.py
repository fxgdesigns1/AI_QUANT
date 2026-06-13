#!/usr/bin/env python3
"""Probe MT5 terminal, account, and symbol state. Run from repo root with sidecar venv."""
import json
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
sidecar_root = script_dir.parent
repo = sidecar_root.parent.parent  # workspace root
sys.path.insert(0, str(repo))

# Load env
from dotenv import load_dotenv
load_dotenv(sidecar_root / ".env", override=True)

import MetaTrader5 as mt5
from bridges.windows_sidecar.service.config import MT5_TERMINAL_PATH, BRIDGE_ID

path = MT5_TERMINAL_PATH or None
ok = mt5.initialize(path=path)
if not ok:
    err = mt5.last_error()
    out = {"initialize_ok": False, "last_error": err, "terminal_path": path}
    print(json.dumps(out, indent=2))
    sys.exit(1)

terminal = mt5.terminal_info()
account = mt5.account_info()
symbols_total = mt5.symbols_total()

# Selected symbols
selected = mt5.symbols_get(selected=True)
symbols_total_selected = len(selected) if selected else 0
selected_names = [s.name for s in selected] if selected else []

# EURUSD probe
eurusd_info = mt5.symbol_info("EURUSD")
eurusd_tick = mt5.symbol_info_tick("EURUSD")

# Try symbol_select if tick is None
eurusd_selected_before = getattr(eurusd_info, "select", getattr(eurusd_info, "selected", None)) if eurusd_info else None
select_attempted = False
if eurusd_info and not getattr(eurusd_info, "select", getattr(eurusd_info, "selected", False)):
    mt5.symbol_select("EURUSD", True)
    select_attempted = True
eurusd_info_after = mt5.symbol_info("EURUSD")
eurusd_tick_after = mt5.symbol_info_tick("EURUSD")

# Check for suffixed variants
all_symbols = mt5.symbols_get()
eurusd_like = [s.name for s in (all_symbols or []) if "EURUSD" in s.name.upper()][:20]

last_err = mt5.last_error()
mt5.shutdown()

out = {
    "initialize_ok": True,
    "terminal_path": path,
    "terminal_info": {
        "connected": terminal.connected if terminal else None,
        "trade_allowed": terminal.trade_allowed if terminal else None,
    } if terminal else None,
    "account_info": {
        "login": account.login if account else None,
        "server": account.server if account else None,
    } if account else None,
    "symbols_total": symbols_total,
    "symbols_total_selected": symbols_total_selected,
    "selected_symbols_sample": selected_names[:30],
    "eurusd_probe": {
        "symbol_info_before": {
            "name": eurusd_info.name if eurusd_info else None,
            "select": getattr(eurusd_info, "select", getattr(eurusd_info, "selected", None)) if eurusd_info else None,
            "visible": getattr(eurusd_info, "visible", None) if eurusd_info else None,
        } if eurusd_info else None,
        "symbol_info_tick_before": {
            "bid": eurusd_tick.bid if eurusd_tick else None,
            "ask": eurusd_tick.ask if eurusd_tick else None,
        } if eurusd_tick else None,
        "select_attempted": select_attempted,
        "symbol_info_after": {
            "name": eurusd_info_after.name if eurusd_info_after else None,
            "select": getattr(eurusd_info_after, "select", getattr(eurusd_info_after, "selected", None)) if eurusd_info_after else None,
        } if eurusd_info_after else None,
        "symbol_info_tick_after": {
            "bid": eurusd_tick_after.bid if eurusd_tick_after else None,
            "ask": eurusd_tick_after.ask if eurusd_tick_after else None,
        } if eurusd_tick_after else None,
    },
    "eurusd_like_symbols": eurusd_like,
    "last_error": last_err,
}

print(json.dumps(out, indent=2))
