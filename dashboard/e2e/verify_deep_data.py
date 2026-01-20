import os
import sys
import time
import json
import subprocess
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# Configuration
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "runtime"
DATA_DIR = REPO_ROOT / "data"
STATUS_FILE = RUNTIME_DIR / "status.json"
LEDGER_FILE = DATA_DIR / "trade_ledger.jsonl"
API_HOST = "127.0.0.1"
API_PORT = 8787
DASHBOARD_URL = f"http://{API_HOST}:{API_PORT}/"

def setup_data():
    print("Populating data files...")
    # 1. Status (News)
    if not RUNTIME_DIR.exists():
        RUNTIME_DIR.mkdir(parents=True)
    
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "timestamp_utc": time.time(),
            "mode": "live",
            "recent_news": [{"title": "Market Stable", "source": "Bloomberg", "published_at": datetime.now(timezone.utc).isoformat()}]
        }, f)

    # 2. Trade Ledger (Journal)
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        
    trades = [
        {
            "id": "TRD-2024-001",
            "instrument": "EUR_USD",
            "realizedPL": 1250.50,
            "units": 100000,
            "state": "CLOSED",
            "openTime": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            "closeTime": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "account_id": "001-001-MOCK",
            "strategy_key": "MOMENTUM_V2"
        },
        {
            "id": "TRD-2024-002",
            "instrument": "XAU_USD",
            "realizedPL": -450.00,
            "units": 50,
            "state": "CLOSED",
            "openTime": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
            "closeTime": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "account_id": "001-001-MOCK",
            "strategy_key": "GOLD_SCALPER"
        }
    ]
    
    with open(LEDGER_FILE, "w") as f:
        for t in trades:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(trades)} trades to {LEDGER_FILE}")

def stream_reader(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line.strip()}")

def run_verification():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print(f"Navigating to {DASHBOARD_URL}...")
        page.goto(DASHBOARD_URL, timeout=30000)
        page.wait_for_timeout(5000)
        
        # --- CHECK 1: SCANNER ---
        print("\n--- Verifying Structural Scanner ---")
        try:
            page.locator("#nav-scanner").click()
            page.wait_for_timeout(3000) # Give it time to fetch
            
            if page.locator("text=EUR_USD").is_visible():
                print("✅ PASS: EUR_USD visible in Scanner")
            else:
                print("❌ FAIL: EUR_USD not found in Scanner")
                
            if page.locator(".text-green-400").count() > 0 or page.locator(".text-red-400").count() > 0:
                 print("✅ PASS: Scanner scores detected")
            
            # Check for Regime Text (visible text only)
            # We expect to see a regime like "RANGE_BOUND", "UPTREND", etc.
            # We explicitly check that "INSUFFICIENT HISTORY" is NOT visible.
            
            if page.locator("text=INSUFFICIENT HISTORY").is_visible():
                print("❌ FAIL: Scanner shows 'INSUFFICIENT HISTORY' (Mock failed)")
                # Try to grab the rationale/warning text
                try:
                    print(f"Visible warnings: {page.locator('.text-yellow-400').all_inner_texts()}")
                except:
                    pass
            elif page.locator("text=INSUFFICIENT_DATA").is_visible():
                 print("❌ FAIL: Scanner shows 'INSUFFICIENT_DATA' raw text")
            else:
                # Check for positive confirmation
                # Regime is usually in a span with text-xs
                if page.locator("text=RANGE_BOUND").is_visible() or page.locator("text=UPTREND").is_visible() or page.locator("text=DOWNTREND").is_visible() or page.locator("text=WEAK_TREND").is_visible():
                    print("✅ PASS: Valid Regime detected in Scanner")
                else:
                    print("⚠️ WARNING: No specific regime text found, but no error either. Content might be dynamic.")

            page.screenshot(path="dashboard_scanner_verified_fixed.png", full_page=True)
            print("📸 captured dashboard_scanner_verified_fixed.png")

        except Exception as e:
            print(f"❌ FAIL Scanner: {e}")

        # --- CHECK 2: JOURNAL ---
        print("\n--- Verifying Forensic Journal ---")
        try:
            page.locator("#nav-journal").click()
            page.wait_for_timeout(2000)
            
            if page.locator("text=TRD-2024-001").is_visible():
                print("✅ PASS: Trade TRD-2024-001 found")
            else:
                print("❌ FAIL: Trade TRD-2024-001 NOT found")
                
            if page.locator("text=1250.50").is_visible():
                print("✅ PASS: PnL 1250.50 found")
            else:
                print("❌ FAIL: PnL 1250.50 NOT found")
                
            if page.locator("text=-450.00").is_visible():
                print("✅ PASS: Negative PnL -450.00 found")
                
            page.screenshot(path="dashboard_journal_verified.png", full_page=True)
            
        except Exception as e:
            print(f"❌ FAIL Journal: {e}")

def main():
    setup_data()
    
    print("Starting Mock API...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONUNBUFFERED"] = "1" # Force unbuffered output
    
    api_process = subprocess.Popen(
        [sys.executable, "run_mock_api.py"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Start threads to print API output
    t_out = threading.Thread(target=stream_reader, args=(api_process.stdout, "API_OUT"))
    t_err = threading.Thread(target=stream_reader, args=(api_process.stderr, "API_ERR"))
    t_out.daemon = True
    t_err.daemon = True
    t_out.start()
    t_err.start()
    
    print("Waiting for API...")
    time.sleep(8)
    
    try:
        run_verification()
    finally:
        print("Stopping API...")
        api_process.terminate()
        api_process.wait()

if __name__ == "__main__":
    main()
