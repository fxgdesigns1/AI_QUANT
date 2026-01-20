#!/usr/bin/env python3
"""
Local Strategy Assignment Tool
Assigns strategies to accounts 001-005 via local Control Plane API.
"""

import sys
import os
import requests
import json

# Ensure we have the token
TOKEN_FILE = "/tmp/control_plane_token_current.txt"
if not os.path.exists(TOKEN_FILE):
    # Try creating one via token_manager if possible, or fail
    print(f"❌ Token file not found: {TOKEN_FILE}")
    print("Ensure Control Plane is running: bash scripts/start_control_plane_clean.sh")
    sys.exit(1)

with open(TOKEN_FILE, "r") as f:
    token = f.read().strip()

# Configuration
ACCOUNT_PREFIX = "101-004-30719775-"
ACCOUNTS = {
    "001": "momentum",
    "002": "momentum_v2",
    "003": "range",
    "004": "gold",
    "005": "eur_usd_5m_safe"
}

print("=== ASSIGNING STRATEGIES (LOCAL) ===")
print(f"Target: http://127.0.0.1:8787/api/config")

# Build Payload
assignments = []
for suffix, strategy in ACCOUNTS.items():
    account_id = f"{ACCOUNT_PREFIX}{suffix}"
    assignments.append({
        "account_id": account_id,
        "strategy_key": strategy,
        "enabled": True
    })
    print(f"   - {suffix}: {strategy}")

payload = {
    "strategy_assignments": assignments
}

try:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    r = requests.post("http://127.0.0.1:8787/api/config", json=payload, headers=headers)
    
    print(f"\nResponse Status: {r.status_code}")
    if r.status_code == 200:
        print("✅ SUCCESS: Strategy assignments updated.")
        print(json.dumps(r.json(), indent=2))
    else:
        print("❌ FAILED: API Error")
        print(r.text)
        sys.exit(1)

except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
