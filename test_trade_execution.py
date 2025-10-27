#!/usr/bin/env python3
"""
Test Trade Execution
Test the trade execution functionality directly
"""

import requests
import json
import time

def test_trade_execution():
    """Test trade execution functionality"""
    base_url = "http://localhost:8080"
    
    print("🔍 Testing Trade Execution System")
    print("=" * 50)
    
    # 1. Test system status
    print("\n1. Testing System Status...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=10)
        if response.status_code == 200:
            print("✅ System is running")
        else:
            print(f"❌ System status error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ System not responding: {e}")
        return
    
    # 2. Test scan to generate signals
    print("\n2. Testing Signal Generation...")
    try:
        response = requests.post(f"{base_url}/tasks/full_scan", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Scan completed: {data.get('ok', False)}")
            if data.get('ok'):
                results = data.get('results', {})
                total_signals = sum(r.get('signals_generated', 0) for r in results.values())
                total_trades = sum(r.get('trades_executed', 0) for r in results.values())
                print(f"📊 Generated {total_signals} signals, executed {total_trades} trades")
                
                # Show details for accounts with signals
                for account_id, result in results.items():
                    if result.get('signals_generated', 0) > 0:
                        print(f"   • {account_id}: {result.get('signals_generated', 0)} signals")
                        if result.get('trade_results', {}).get('failed_trades'):
                            failed = result['trade_results']['failed_trades']
                            print(f"     - {len(failed)} failed trades")
                            for trade in failed[:1]:  # Show first failure reason
                                if 'error_message' in trade:
                                    print(f"     - Reason: {trade['error_message']}")
            else:
                print(f"❌ Scan failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Scan request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Scan error: {e}")
    
    # 3. Test opportunities API
    print("\n3. Testing Opportunities API...")
    try:
        response = requests.get(f"{base_url}/api/opportunities", timeout=10)
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('opportunities', [])
            print(f"📊 Found {len(opportunities)} opportunities")
            if opportunities:
                for opp in opportunities[:3]:  # Show first 3
                    print(f"   • {opp.get('instrument', 'N/A')} {opp.get('direction', 'N/A')} - Quality: {opp.get('quality_score', 'N/A')}%")
            else:
                print("ℹ️ No opportunities available")
                if 'error' in data:
                    print(f"   Error: {data['error']}")
        else:
            print(f"❌ Opportunities API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Opportunities API error: {e}")
    
    # 4. Test trade approval (if we had an opportunity)
    print("\n4. Testing Trade Approval...")
    try:
        # Create a test approval request
        test_data = {
            "opportunity_id": "test_signal_001",
            "position_size": 1000,
            "current_price": 4115.0,
            "dollar_value": 4115.0
        }
        
        response = requests.post(
            f"{base_url}/api/opportunities/approve",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Approval response: {data.get('success', False)}")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Approval request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Approval test error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Trade Execution Test Complete")
    print("=" * 50)

if __name__ == "__main__":
    test_trade_execution()
