#!/usr/bin/env python3
"""
30-60 minute live health monitor for the AI Trading system.
Sends a concise health summary to Telegram (if configured) every minute.
This script is read-only with respect to the running service; no configuration changes are made.
"""
import os
import time
import re
import datetime
import subprocess
import requests

# Telemetry/env loading (systemd may provide these; fallback to env file if present)
ENV_FILE = "/opt/quant_system_clean/google-cloud-trading-system/oanda_config.env"

def load_env_from_file(path: str):
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k] = v
    except FileNotFoundError:
        pass
    return data

def telegram_send(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        # Non-fatal if Telegram is unavailable
        pass

def collect_health() -> dict:
    # Service status
    svc = subprocess.run(["systemctl", "is-active", "ai_trading.service"], capture_output=True, text=True)
    service_status = svc.stdout.strip()

    # Recent logs for last 60 minutes
    logs = subprocess.run(
        ["journalctl", "-u", "ai_trading.service", "--since", "60 minutes", "--no-pager"],
        capture_output=True,
        text=True,
    ).stdout

    # Parse numbers from logs
    errors = len(re.findall(r"ERROR|Error|Error:", logs))
    traded_matches = re.findall(r"Executed\s+(\d+)\s+trades", logs, flags=re.IGNORECASE)
    last_trades = int(traded_matches[-1]) if traded_matches else None
    signals_matches = re.findall(r"Generated\s+(\d+)\s+trading\s+signals", logs, flags=re.IGNORECASE)
    signals = int(signals_matches[-1]) if signals_matches else None
    next_cycle_matches = re.findall(r"Next cycle in\s+(\d+)\s+seconds", logs, flags=re.IGNORECASE)
    next_cycle = int(next_cycle_matches[-1]) if next_cycle_matches else None

    # Health score (0-100)
    score = 0
    if service_status == "active":
        score += 60
    if last_trades is not None and last_trades > 0:
        score += 20
    if errors > 0:
        score = max(0, score - min(50, errors * 3))
    score = max(0, min(100, score))

    return {
        "service_status": service_status,
        "last_trades": last_trades,
        "signals": signals,
        "errors": errors,
        "next_cycle": next_cycle,
        "health_score": score,
        "logs_preview": logs[-1000:],
    }

def main():
    env = load_env_from_file(ENV_FILE)
    telegram_token = env.get("TELEGRAM_TOKEN")
    telegram_chat = env.get("TELEGRAM_CHAT_ID")

    duration = 60 * 60  # 60 minutes
    interval = 60       # 1 minute cadence
    end_ts = time.time() + duration

    while time.time() < end_ts:
        data = collect_health()
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        text = (
            f"AI Trading Health Report {now}\n"
            f"Service: {data['service_status']}\n"
            f"Last trades (24h snapshot): {data['last_trades'] if data['last_trades'] is not None else 'n/a'}\n"
            f"Signals (last cycle): {data['signals'] if data['signals'] is not None else 'n/a'}\n"
            f"Errors (60m): {data['errors']}\n"
            f"Next cycle in: {data['next_cycle'] if data['next_cycle'] is not None else 'n/a'} seconds\n"
            f"Health score: {data['health_score']}%\n"
        )
        if telegram_token and telegram_chat:
            telegram_send(telegram_token, telegram_chat, text)
        time.sleep(interval)

if __name__ == "__main__":
    main()


