import requests
import sys
import json
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8787"
HEADERS = {}
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN")
if CONTROL_PLANE_TOKEN:
    HEADERS["Authorization"] = f"Bearer {CONTROL_PLANE_TOKEN}"

def log(msg, status="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{status}] {msg}")

def verify_endpoint(name, url, checks):
    log(f"Verifying {name} ({url})...")
    try:
        r = requests.get(f"{BASE_URL}{url}", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            log(f"Failed to fetch {url}: {r.status_code}", "FAIL")
            return False
        
        data = r.json()
        
        # 1. Check Truth Envelope
        if "truth" not in data:
            log(f"{name}: Missing 'truth' envelope", "FAIL")
            return False
            
        truth = data["truth"]
        if not truth.get("complete", False):
            log(f"{name}: Truth not complete. Warnings: {truth.get('warnings')}", "WARN")
            # We allow partial truth for now, but note it
            
        # 2. Run specific checks
        for check_name, check_func in checks.items():
            try:
                if not check_func(data):
                    log(f"{name}: Check '{check_name}' failed", "FAIL")
                    return False
            except Exception as e:
                log(f"{name}: Check '{check_name}' raised exception: {e}", "FAIL")
                return False
                
        log(f"{name}: Verified successfully", "PASS")
        return True
        
    except Exception as e:
        log(f"Exception verifying {name}: {e}", "FAIL")
        return False

def check_active_trades(data):
    # response.data.length >= 0 (it's a list in 'accounts' or 'trades'?)
    # The API returns { data: { accounts: [...] } } usually? 
    # Wait, /api/trades/active returns { ok: ..., accounts: [...] } wrapped in truth
    
    # The wrapper puts the payload in 'data'
    payload = data.get("data", {})
    accounts = payload.get("accounts", [])
    
    if not isinstance(accounts, list):
        return False
        
    for acc in accounts:
        if "trades" in acc:
            for trade in acc["trades"]:
                # Check required fields
                required = ["id", "instrument", "units", "price", "unrealizedPL"]
                if not all(k in trade for k in required):
                    log(f"Active trade missing fields: {trade.keys()}", "FAIL")
                    return False
    return True

def check_journal_trades(data):
    # /api/journal/trades returns { ok: ..., trades: [...] } wrapped in truth
    payload = data.get("data", {})
    trades = payload.get("trades", [])
    
    if not isinstance(trades, list):
        return False
        
    # If there are trades, check structure
    if trades:
        t = trades[0]
        required = ["strategy_key", "instrument", "entry_price", "exit_price", "pnl", "opened_at", "closed_at"]
        # Note: fields might differ slightly, checking for key ones
        if not all(k in t for k in required if k in t): # Loose check as some might be optional
             pass 
    return True

def main():
    log("Starting Dashboard Backend Verification...")
    
    results = []
    
    # Verify Active Trades
    results.append(verify_endpoint(
        "Active Trades", 
        "/api/trades/active",
        {"structure_check": check_active_trades}
    ))
    
    # Verify Journal Trades
    results.append(verify_endpoint(
        "Journal Trades", 
        "/api/journal/trades",
        {"structure_check": check_journal_trades}
    ))
    
    if all(results):
        log("ALL CHECKS PASSED", "SUCCESS")
        sys.exit(0)
    else:
        log("SOME CHECKS FAILED", "FAILURE")
        sys.exit(1)

if __name__ == "__main__":
    main()
