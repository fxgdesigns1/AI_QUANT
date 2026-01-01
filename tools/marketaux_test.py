#!/usr/bin/env python3
"""
Test Marketaux API with the first available key found in /opt or /home runtime usage files.
Run this on the VM to verify API responses as the service would request them.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests

def load_keys():
    # Try common runtime locations
    candidates = [Path("/opt/quant_system_clean/runtime/marketaux_usage.json"), Path("/home/mac/runtime/marketaux_usage.json")]
    for p in candidates:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            keys = [k.get("key") for k in data.get("keys", []) if k.get("key")]
            if keys:
                return keys
    return []

def main():
    keys = load_keys()
    print("Found keys:", len(keys))
    if not keys:
        return
    key = keys[0]
    pa = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    url = (
        "https://api.marketaux.com/v1/news/all?"
        f"filter_entities=true&limit=20&sort=published_desc&published_after={pa}&language=en&countries=us,gb,eu&query=forex%20OR%20currency%20OR%20gold"
    )
    print("Requesting:", url)
    r = requests.get(url, params={"api_token": key}, timeout=15)
    print("Status:", r.status_code)
    try:
        data = r.json()
        print("Returned:", len(data.get("data", [])))
    except Exception as exc:
        print("JSON parse failed:", exc)
        print("Text:", r.text[:500])

if __name__ == "__main__":
    main()




