#!/usr/bin/env python3
"""
Scan for trading opportunities using the progressive scanner
"""

import os
import sys
import requests
from datetime import datetime

def scan_for_opportunities():
    """Trigger a progressive trading scan"""
    
    print("\n" + "="*80)
    print("🔍 SCANNING FOR TRADING OPPORTUNITIES")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80 + "\n")
    
    # Try to connect to local system first
    base_urls = [
        "http://localhost:8080",
        "http://localhost:8090",
        "http://127.0.0.1:8080"
    ]
    
    for base_url in base_urls:
        try:
            print(f"🔗 Attempting to connect to: {base_url}")
            
            # Check health endpoint first
            health_response = requests.get(f"{base_url}/api/health", timeout=5)
            
            if health_response.status_code == 200:
                print(f"✅ System is online at {base_url}")
                
                # Trigger full scan
                print(f"\n🚀 Triggering progressive trading scan...")
                scan_response = requests.post(f"{base_url}/tasks/full_scan", timeout=60)
                
                if scan_response.status_code == 200:
                    result = scan_response.json()
                    
                    if result.get('ok'):
                        print(f"\n✅ SCAN COMPLETED SUCCESSFULLY")
                        print(f"{'─'*80}")
                        
                        total_trades = result.get('total_trades', 0)
                        scan_type = result.get('scan_type', 'unknown')
                        
                        print(f"📊 Scan Type: {scan_type.upper()}")
                        print(f"🎯 New Trades Found: {total_trades}")
                        
                        if total_trades > 0:
                            print(f"\n🎉 OPPORTUNITIES FOUND AND EXECUTED!")
                            
                            results = result.get('results', {})
                            if isinstance(results, dict):
                                for account, details in results.items():
                                    if isinstance(details, dict):
                                        trades = details.get('executed_trades', [])
                                        if trades:
                                            print(f"\n📋 {account}:")
                                            for trade in trades[:5]:  # Show first 5
                                                print(f"   • {trade.get('instrument', 'Unknown')}: {trade.get('side', 'Unknown')}")
                        else:
                            print(f"\n⚪ No new opportunities found at this time")
                            print(f"   Reasons:")
                            print(f"   • Market conditions don't meet entry criteria")
                            print(f"   • All instruments already have positions")
                            print(f"   • Position limits reached")
                        
                        print(f"\n{'─'*80}")
                        return True
                    else:
                        print(f"❌ Scan failed: {result.get('error', 'Unknown error')}")
                else:
                    print(f"❌ Scan request failed: {scan_response.status_code}")
                    
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to {base_url}")
            continue
        except requests.exceptions.Timeout:
            print(f"⏱️ Request timed out for {base_url}")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    # If we got here, no local system was found
    print(f"\n{'─'*80}")
    print(f"⚠️ TRADING SYSTEM NOT RUNNING LOCALLY")
    print(f"{'─'*80}")
    print(f"\nYour trading system appears to be running on Google Cloud.")
    print(f"\nTo check for opportunities on the cloud deployment:")
    print(f"1. Visit: https://ai-quant-trading.uc.r.appspot.com/dashboard")
    print(f"2. Or trigger a scan via the web interface")
    print(f"\nYour current positions are already managed and monitored.")
    print(f"The scanner runs automatically every hour on the cloud.")
    
    return False

if __name__ == "__main__":
    scan_for_opportunities()






















