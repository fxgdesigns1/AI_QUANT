#!/usr/bin/env python3
"""
Background monitor: run verify_strategies_running.py every 5 minutes until stop time,
send Telegram summary if signals or errors appear, and save logs.
"""
import os
import time
import subprocess
import json
import fcntl
import logging
# Simple logger for monitor script
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6100678501")
VERIFY_SCRIPT = "/opt/quant_system_clean/google-cloud-trading-system/verify_strategies_running.py"
REPORT_PATH = "/tmp/incremental_relax_report.json"
LOG_PATH = "/tmp/monitoring.log"
SLEEP_SECS = 300

def send_telegram(text: str):
    import requests
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        with open(LOG_PATH, "a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} Telegram send failed: {e}\n")

def get_stop_time():
    # Prefer TEMP_RELAX_GLOBAL expiry if present and valid
    marker = "/opt/quant_system_clean/google-cloud-trading-system/TEMP_RELAX_GLOBAL"
    if os.path.exists(marker):
        try:
            raw = open(marker).read().strip().splitlines()[0].strip()
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > datetime.now(timezone.utc):
                return dt
        except Exception:
            pass
    # Fallback: next London 14:20 (adjust if already past)
    loc = ZoneInfo("Europe/London")
    now = datetime.now(timezone.utc)
    today_local = now.astimezone(loc).date()
    target_local = datetime(year=today_local.year, month=today_local.month, day=today_local.day, hour=14, minute=20, tzinfo=loc)
    if target_local.astimezone(timezone.utc) <= now:
        target_local = target_local + timedelta(days=1)
    return target_local.astimezone(timezone.utc)

def run_verify():
    try:
        proc = subprocess.run(["python3", VERIFY_SCRIPT], capture_output=True, text=True, timeout=120)
        return proc.returncode, proc.stdout + "\n" + proc.stderr
    except Exception as e:
        return 1, str(e)

def summarize_output(output: str):
    # simple summary: look for summary lines produced by verify_strategies_running.py
    lines = [l for l in output.splitlines() if l.strip()]
    summary_lines = []
    for l in lines[-60:]:
        if any(k in l for k in ("Total Strategies:", "✅ Running Correctly", "⚠️ Loaded but Inactive", "❌ Not Working")):
            summary_lines.append(l)
    return "\n".join(summary_lines) or (lines[-1] if lines else "No output")

def main():
    # Acquire a exclusive non-blocking lock to ensure only a single instance runs
    lock_path = "/tmp/monitor_until.lock"
    lock_file = None
    try:
        lock_file = open(lock_path, "w")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info("Monitor already running (lock is held). Exiting this instance.")
            return
        # Keep the lock for the duration of this process
        stop_time = get_stop_time()
        with open(LOG_PATH, "a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} Monitor started with lock\n")
        while datetime.now(timezone.utc) < stop_time:
            code, out = run_verify()
            summary = summarize_output(out)
            timestamp = datetime.now(timezone.utc).isoformat()
            with open(LOG_PATH, "a") as fh:
                fh.write(f"\n--- VERIFY {timestamp} ---\n")
                fh.write(out + "\n")
            try:
                with open(REPORT_PATH, "w") as fh:
                    fh.write(json.dumps({"timestamp": timestamp, "summary": summary}, indent=2))
            except Exception:
                pass
            if "✅ Running Correctly" in out or "❌ Not Working" in out or "Errors found" in out:
                if summary:
                    send_telegram(f"Monitor alert at {timestamp} UTC:\n{summary}")
            time.sleep(SLEEP_SECS)
        # Final run
        code, out = run_verify()
        summary = summarize_output(out)
        with open(LOG_PATH, "a") as fh:
            fh.write(f"\n--- FINAL VERIFY {datetime.now(timezone.utc).isoformat()} ---\n")
            fh.write(out + "\n")
        send_telegram(f"Final pre-NY check at {datetime.now(timezone.utc).isoformat()} UTC:\n{summary}")
        with open(REPORT_PATH, "w") as fh:
            fh.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary}, indent=2))
    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except Exception:
                pass
            lock_file.close()
    stop_time = get_stop_time()
    with open(LOG_PATH, "a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} Monitor started, stopping at {stop_time.isoformat()}\n")
    last_report = None
    while datetime.now(timezone.utc) < stop_time:
        code, out = run_verify()
        summary = summarize_output(out)
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(LOG_PATH, "a") as fh:
            fh.write(f"\n--- VERIFY {timestamp} ---\n")
            fh.write(out + "\n")
        # Save last verify output to report path
        try:
            with open(REPORT_PATH, "w") as fh:
                fh.write(json.dumps({"timestamp": timestamp, "summary": summary}, indent=2))
        except Exception:
            pass
        # If any strategies running or errors => alert
        if "✅ Running Correctly" in out or "❌ Not Working" in out or "Errors found" in out:
            if last_report != summary:
                send_telegram(f"Monitor alert at {timestamp} UTC:\n{summary}")
                last_report = summary
        time.sleep(SLEEP_SECS)
    # Final run at stop_time
    code, out = run_verify()
    summary = summarize_output(out)
    with open(LOG_PATH, "a") as fh:
        fh.write(f"\n--- FINAL VERIFY {datetime.now(timezone.utc).isoformat()} ---\n")
        fh.write(out + "\n")
    send_telegram(f"Final pre-NY check at {datetime.now(timezone.utc).isoformat()} UTC:\n{summary}")
    with open(REPORT_PATH, "w") as fh:
        fh.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary}, indent=2))

if __name__ == "__main__":
    main()


