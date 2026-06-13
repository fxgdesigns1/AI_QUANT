#!/usr/bin/env python3
"""
Dashboard Endpoint Test Script
Tests all dashboard endpoints with focus on transparency features.
"""

import requests
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

BASE_URL = "http://127.0.0.1:8787"
TIMEOUT = 10.0

def test_endpoint(path: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        result = {
            "path": path,
            "status_code": response.status_code,
            "success": response.status_code == expected_status,
            "has_data": False,
            "has_truth": False,
            "error": None
        }
        
        if response.status_code == expected_status:
            try:
                data = response.json()
                result["has_data"] = True
                result["data"] = data
                
                # Check for truth envelope
                if "data" in data and "truth" in data:
                    result["has_truth"] = True
                    result["truth"] = data["truth"]
                    result["payload"] = data["data"]
                else:
                    result["payload"] = data
                    
            except json.JSONDecodeError as e:
                result["error"] = f"JSON decode error: {str(e)}"
        else:
            result["error"] = f"Unexpected status code: {response.status_code}"
            try:
                result["response"] = response.text[:200]
            except:
                pass
                
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "path": path,
            "status_code": None,
            "success": False,
            "has_data": False,
            "has_truth": False,
            "error": f"Request failed: {str(e)}"
        }

def test_session_regime_gate_snapshot() -> Dict[str, Any]:
    """Test the enhanced session-regime-gate snapshot endpoint"""
    result = test_endpoint("/api/session-regime-gate/snapshot")
    
    if result["success"] and result["has_data"]:
        payload = result.get("payload", {})
        
        # Check for new transparency fields
        checks = {
            "has_trade_block_reason": "trade_block_reason" in payload,
            "has_block_details": "block_details" in payload,
            "has_readiness": "readiness" in payload,
            "has_readiness_score": "readiness_score" in payload,
            "has_candles_remaining": "candles_remaining" in payload,
            "has_eta_seconds": "eta_seconds" in payload,
            "has_next_session": "next_session" in payload,
            "has_current_session": "current_session" in payload,
        }
        
        result["transparency_checks"] = checks
        result["all_transparency_fields"] = all(checks.values())
        
        # Extract key values for reporting
        if payload:
            result["readiness"] = payload.get("readiness", "UNKNOWN")
            result["trade_block_reason"] = payload.get("trade_block_reason")
            result["current_session"] = payload.get("current_session")
            next_session = payload.get("next_session", {})
            result["next_tradable_session"] = next_session.get("next_tradable_session")
            result["countdown_seconds"] = next_session.get("countdown_seconds")
    
    return result

def main():
    print("=" * 80)
    print("DASHBOARD ENDPOINT TEST SUITE")
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)
    print()
    
    # Test core endpoints
    endpoints_to_test = [
        ("Health Check", "/health"),
        ("System Status", "/api/status"),
        ("Truth Status", "/api/truth/status"),
        ("Config", "/api/config"),
        ("Strategies", "/api/strategies"),
        ("Active Trades", "/api/trades/active"),
        ("Market Overview", "/api/market/overview"),
        ("News", "/api/news"),
        ("Performance Summary", "/api/performance/summary"),
    ]
    
    results = []
    
    # Test core endpoints
    print("--- CORE ENDPOINTS ---")
    for name, path in endpoints_to_test:
        print(f"\nTesting {name}...")
        result = test_endpoint(path)
        results.append((name, result))
        
        if result["success"]:
            print(f"  ✅ {path} - OK")
            if result["has_truth"]:
                truth = result["truth"]
                complete = truth.get("complete", False)
                source = truth.get("source", "unknown")
                print(f"     Truth: {'COMPLETE' if complete else 'INCOMPLETE'} from {source}")
        else:
            print(f"  ❌ {path} - FAILED")
            if result["error"]:
                print(f"     Error: {result['error']}")
            else:
                print(f"     Status: {result['status_code']}")
    
    # Test session-regime-gate endpoints (key for transparency)
    print("\n" + "=" * 80)
    print("--- SESSION REGIME GATE ENDPOINTS (TRANSPARENCY) ---")
    
    # Test snapshot (most important)
    print("\nTesting Session Regime Gate Snapshot...")
    snapshot_result = test_session_regime_gate_snapshot()
    results.append(("Session Regime Gate Snapshot", snapshot_result))
    
    if snapshot_result["success"]:
        print(f"  ✅ /api/session-regime-gate/snapshot - OK")
        
        if snapshot_result.get("all_transparency_fields"):
            print("  ✅ All transparency fields present")
        else:
            print("  ⚠️  Some transparency fields missing:")
            checks = snapshot_result.get("transparency_checks", {})
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"     {status} {check}")
        
        # Report key values
        if snapshot_result.get("readiness"):
            readiness = snapshot_result["readiness"]
            print(f"     Readiness: {readiness}")
        if snapshot_result.get("trade_block_reason"):
            print(f"     Block Reason: {snapshot_result['trade_block_reason']}")
        if snapshot_result.get("current_session"):
            print(f"     Current Session: {snapshot_result['current_session']}")
        if snapshot_result.get("next_tradable_session"):
            session = snapshot_result["next_tradable_session"]
            countdown = snapshot_result.get("countdown_seconds", 0)
            hours = countdown // 3600
            minutes = (countdown % 3600) // 60
            print(f"     Next Session: {session} (in {hours}h {minutes}m)")
    else:
        print(f"  ❌ /api/session-regime-gate/snapshot - FAILED")
        if snapshot_result["error"]:
            print(f"     Error: {snapshot_result['error']}")
        elif snapshot_result.get("status_code") == 404:
            print(f"     ⚠️  Endpoint not found - server may need restart")
    
    # Test decisions endpoint
    print("\nTesting Session Regime Gate Decisions...")
    decisions_result = test_endpoint("/api/session-regime-gate/decisions?limit=5")
    results.append(("Session Regime Gate Decisions", decisions_result))
    
    if decisions_result["success"]:
        print(f"  ✅ /api/session-regime-gate/decisions - OK")
        payload = decisions_result.get("payload", {})
        count = payload.get("count", 0)
        print(f"     Found {count} recent decisions")
    else:
        print(f"  ❌ /api/session-regime-gate/decisions - FAILED")
        if decisions_result.get("status_code") == 404:
            print(f"     ⚠️  Endpoint not found - server may need restart")
    
    # Test statistics endpoint
    print("\nTesting Session Regime Gate Statistics...")
    stats_result = test_endpoint("/api/session-regime-gate/statistics")
    results.append(("Session Regime Gate Statistics", stats_result))
    
    if stats_result["success"]:
        print(f"  ✅ /api/session-regime-gate/statistics - OK")
    else:
        print(f"  ❌ /api/session-regime-gate/statistics - FAILED")
        if stats_result.get("status_code") == 404:
            print(f"     ⚠️  Endpoint not found - server may need restart")
    
    # Summary
    print("\n" + "=" * 80)
    print("--- SUMMARY ---")
    
    total = len(results)
    passed = sum(1 for _, r in results if r["success"])
    failed = total - passed
    
    print(f"Total endpoints tested: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed endpoints:")
        for name, result in results:
            if not result["success"]:
                status_code = result.get("status_code", "N/A")
                error = result.get("error", "Unknown error")
                print(f"  ❌ {name}: {status_code} - {error}")
    
    # Critical transparency check
    print("\n--- TRANSPARENCY FEATURES CHECK ---")
    snapshot = snapshot_result
    if snapshot.get("all_transparency_fields"):
        print("✅ All transparency fields are present in snapshot endpoint")
        print("   - trade_block_reason")
        print("   - block_details")
        print("   - readiness")
        print("   - readiness_score")
        print("   - candles_remaining")
        print("   - eta_seconds")
        print("   - next_session (countdown)")
    else:
        print("❌ Some transparency fields are missing")
        if snapshot.get("status_code") == 404:
            print("   ⚠️  Endpoint not found - restart API server to load new code")
        elif not snapshot["success"]:
            print(f"   ⚠️  Endpoint failed: {snapshot.get('error', 'Unknown error')}")
        else:
            checks = snapshot.get("transparency_checks", {})
            for check, passed in checks.items():
                if not passed:
                    print(f"   ❌ Missing: {check}")
    
    print("\n" + "=" * 80)
    print("Test completed at:", datetime.now(timezone.utc).isoformat())
    print("=" * 80)
    
    # Return exit code based on critical checks
    if failed > 0 or not snapshot.get("all_transparency_fields", False):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
