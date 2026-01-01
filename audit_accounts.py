#!/usr/bin/env python3
"""
Deep audit of each account, combining strategy logs with on-chain OANDA data.
"""

import os
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import yaml
import requests


OANDA_API_KEY = os.getenv("OANDA_API_KEY")
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

ACCOUNTS_PATH_CANDIDATES = [
    Path(
        "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"
    ),
    Path(
        "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml"
    ),
]


def run_ssh_command(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            f"gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a --command='{command}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout or result.stderr or ""
    except Exception as exc:
        return f"SSH command failed: {exc}"


def load_accounts() -> List[Dict[str, Any]]:
    for path in ACCOUNTS_PATH_CANDIDATES:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    payload = yaml.safe_load(fh) or {}
                accounts_section = payload.get("accounts", {})
                accounts = []
                for logical, entry in accounts_section.items():
                    account = dict(entry)
                    account["logical_name"] = logical
                    accounts.append(account)
                return accounts
            except Exception as exc:
                print(f"Failed to read {path}: {exc}")
    raise FileNotFoundError("accounts.yaml not found in known locations")


def fetch_service_status() -> str:
    command = "sudo systemctl status ai_trading.service --no-pager | head -n 20"
    return run_ssh_command(command, timeout=30)

def oanda_request(
    account_id: str, path: str, params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}/{path}"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        print(f"  → OANDA {path} failed ({response.status_code}) for {account_id}")
    except Exception as exc:
        print(f"  → OANDA {path} error for {account_id}: {exc}")
    return None


def fetch_oanda_summary(account_id: str) -> Dict[str, Any]:
    summary = oanda_request(account_id, "")
    return summary.get("account", {}) if summary else {}


def fetch_open_positions(account_id: str) -> List[Dict[str, Any]]:
    data = oanda_request(account_id, "openPositions")
    return data.get("positions", []) if data else []


def fetch_open_trades(account_id: str) -> List[Dict[str, Any]]:
    data = oanda_request(account_id, "openTrades")
    return data.get("trades", []) if data else []


def fetch_recent_transactions(account_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    window_start = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=hours)
    data = oanda_request(account_id, "transactions", {"count": 40})
    transactions: List[Dict[str, Any]] = []
    if not data:
        return transactions
    for tx in data.get("transactions", []):
        time_str = tx.get("time")
        if not time_str:
            continue
        try:
            tx_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if tx_time >= window_start and tx.get("type") in ("ORDER_FILL", "ORDER_CANCEL", "ORDER_CREATE"):
            transactions.append(tx)
    return transactions


def audit():
    accounts = load_accounts()
    logs = fetch_recent_logs(hours=6)
    parsed_logs = parse_logs(logs)
    service_status = fetch_service_status()

    print("\n" + "=" * 60)
    print("SYSTEM STATUS")
    print("=" * 60)
    print(service_status.strip() or "No systemctl output")
    print("\n" + "=" * 60)

    for account in sorted(accounts, key=lambda a: a.get("logical_name")):
        account_id = account.get("account_id")
        name = account.get("name", "Unnamed")
        strategy = account.get("strategy", "unknown")
        logical = account.get("logical_name")
        print(f"\n{'-' * 60}")
        print(f"{logical} / {name} → {account_id}")
        print(f"Strategy: {strategy}")
        print("-" * 60)

        log_info = parsed_logs.get(account_id, {})
        if log_info:
            attempt = log_info.get("last_strategy_attempt")
            if attempt:
                print(f"Last strategy attempt: {attempt}")
            if log_info.get("loaded"):
                print("Loading check: ✅ strategy loaded")
                if log_info.get("has_analyze_market") is True:
                    print("  → analyze_market() is available")
                elif log_info.get("has_analyze_market") is False:
                    print("  → analyze_market() missing (falling back to generate_signals)")
                else:
                    print("  → analyze_market() unknown (no explicit log)")
            else:
                print("Loading check: ⚠️ not loaded in the sampled logs")
            recent_signal = log_info.get("recent_generated")
            if recent_signal:
                print(f"Last signal log: {recent_signal}")
            last_exec = log_info.get("last_executed")
            if last_exec:
                print(f"Last trade execution line: {last_exec}")
        else:
            print("No recent log entries captured for this account (try widening timeframe)")

        summary = fetch_oanda_summary(account_id)
        balance = summary.get("balance")
        print(f"\nOANDA account balance: ${float(balance):,.2f}" if balance else "OANDA balance: unavailable")
        positions = fetch_open_positions(account_id)
        trades = fetch_open_trades(account_id)
        txns = fetch_recent_transactions(account_id)

        print(f"Open positions: {len(positions)}")
        for pos in positions:
            instrument = pos.get("instrument")
            units = pos.get("long", {}).get("units") or pos.get("short", {}).get("units")
            print(f"  • {instrument}: {units}")
        print(f"Open trades: {len(trades)}")
        print(f"Trades in last 24h: {len(txns)}")
        for tx in txns[:3]:
            tx_type = tx.get("type")
            instrument = tx.get("instrument")
            units = tx.get("units")
            price = tx.get("price")
            side = "BUY" if float(units) > 0 else "SELL"
            time = tx.get("time")
            print(f"  - {tx_type} {instrument} {side} {units} @ {price} ({time})")
        if txns:
            print("  (more transactions available if needed)")

    print("\nAudit complete.")


if __name__ == "__main__":
    audit()

