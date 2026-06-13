import requests
import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# Config
PORT = 5002  # Use a different port to avoid conflict
API_URL = f"http://localhost:{PORT}"
PROJECT_ROOT = Path(__file__).parent.parent
ENV = os.environ.copy()
ENV["PORT"] = str(PORT)
ENV["PYTHONPATH"] = str(PROJECT_ROOT)

def verify_api():
    print(f"🚀 Starting API Verification on port {PORT}...")
    
    # Start Server
    process = subprocess.Popen(
        [sys.executable, "dashboard/api_vm.py"],
        cwd=PROJECT_ROOT,
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for health
        print("⏳ Waiting for health check...")
        for i in range(10):
            try:
                resp = requests.get(f"{API_URL}/api/health")
                if resp.status_code == 200:
                    print("✅ API is UP")
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        else:
            print("❌ API failed to start")
            print(process.stdout.read())
            print(process.stderr.read())
            sys.exit(1)

        # Test 1: Get Journal Trades (Wide Range)
        print("\n🧪 Test 1: Fetch Journal Trades (Wide Range)")
        params = {
            "start_date": "2025-01-01",
            "end_date": "2026-12-31"
        }
        resp = requests.get(f"{API_URL}/api/vm/journal/trades", params=params)
        if resp.status_code != 200:
            print(f"❌ Failed: {resp.text}")
            sys.exit(1)
            
        data = resp.json()
        if not data.get("success"):
            print("❌ Success flag missing or false")
            sys.exit(1)
            
        trades = data.get("trades", [])
        stats = data.get("stats", {})
        meta = data.get("meta", {})
        
        print(f"   Trades Count: {len(trades)}")
        print(f"   Source: {meta.get('source')}")
        print(f"   Stats PL: {stats.get('total_pl')}")
        
        if len(trades) == 0:
            print("⚠️  Warning: No trades found. Check trades_flat.json content.")
            # Check file
            fpath = PROJECT_ROOT / 'data/processed/trades_flat.json'
            if fpath.exists():
                print(f"   File exists: {fpath} ({fpath.stat().st_size} bytes)")
            else:
                print(f"   File MISSING: {fpath}")
        else:
            print("✅ Trades fetched successfully")

        # Test 2: Filter by Account (if trades exist)
        if len(trades) > 0:
            acc_id = trades[0]['account_id']
            print(f"\n🧪 Test 2: Filter by Account ({acc_id})")
            params['account_id'] = acc_id
            resp = requests.get(f"{API_URL}/api/vm/journal/trades", params=params)
            data = resp.json()
            filtered = data.get("trades", [])
            print(f"   Filtered Count: {len(filtered)}")
            if len(filtered) == 0:
                 print("❌ Filter returned 0 trades (expected > 0)")
            elif any(t['account_id'] != acc_id for t in filtered):
                 print("❌ Filter failed (found wrong account)")
            else:
                 print("✅ Filter works")

    finally:
        print("\n🛑 Stopping Server...")
        os.kill(process.pid, signal.SIGTERM)
        process.wait()

if __name__ == "__main__":
    verify_api()
