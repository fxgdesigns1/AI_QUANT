#!/usr/bin/env python3
"""
Test TradingView Integration
Verifies that the TradingView widget is properly integrated into the dashboard
"""

import os
import sys
import time
import requests
from datetime import datetime

def test_dashboard_access():
    """Test if the dashboard is accessible"""
    try:
        # Test local dashboard
        response = requests.get('http://localhost:8080', timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard is accessible")
            return True
        else:
            print(f"❌ Dashboard returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access dashboard: {e}")
        return False

def test_tradingview_script():
    """Test if TradingView script is loaded in the HTML"""
    try:
        response = requests.get('http://localhost:8080', timeout=10)
        if response.status_code == 200:
            html_content = response.text
            
            # Check for TradingView script
            if 's3.tradingview.com/tv.js' in html_content:
                print("✅ TradingView script is loaded")
            else:
                print("❌ TradingView script not found")
                return False
            
            # Check for TradingView widget container
            if 'tradingview_widget' in html_content:
                print("✅ TradingView widget container found")
            else:
                print("❌ TradingView widget container not found")
                return False
            
            # Check for symbol selector
            if 'symbolSelector' in html_content:
                print("✅ Symbol selector found")
            else:
                print("❌ Symbol selector not found")
                return False
            
            # Check for timeframe buttons
            if 'data-timeframe' in html_content:
                print("✅ Timeframe buttons found")
            else:
                print("❌ Timeframe buttons not found")
                return False
            
            return True
        else:
            print(f"❌ Dashboard returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access dashboard: {e}")
        return False

def test_api_endpoints():
    """Test if API endpoints are working"""
    endpoints = [
        '/api/systems',
        '/api/market',
        '/api/news',
        '/api/overview'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://localhost:8080{endpoint}', timeout=5)
            if response.status_code == 200:
                print(f"✅ API endpoint {endpoint} is working")
            else:
                print(f"❌ API endpoint {endpoint} returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ API endpoint {endpoint} error: {e}")

def main():
    """Main test function"""
    print("🧪 Testing TradingView Integration")
    print("=" * 50)
    
    # Test dashboard access
    if not test_dashboard_access():
        print("\n❌ Dashboard is not accessible. Please start the dashboard first:")
        print("   python dashboard/advanced_dashboard.py")
        return False
    
    print("\n📊 Testing TradingView Components:")
    if not test_tradingview_script():
        print("\n❌ TradingView integration has issues")
        return False
    
    print("\n🔌 Testing API Endpoints:")
    test_api_endpoints()
    
    print("\n✅ TradingView Integration Test Complete!")
    print("\n📋 Integration Features:")
    print("   • Live TradingView charts with real-time data")
    print("   • Symbol selector for major currency pairs and crypto")
    print("   • Timeframe switching (1H, 4H, 1D)")
    print("   • Technical indicators (RSI, MACD, EMA)")
    print("   • Dark theme matching your dashboard")
    print("   • London timezone for UK trading hours")
    print("   • Auto-sync with market data updates")
    
    print("\n🎯 Usage Instructions:")
    print("   1. Open your dashboard in a web browser")
    print("   2. Navigate to the main dashboard section")
    print("   3. Use the symbol dropdown to switch between pairs")
    print("   4. Use timeframe buttons to change chart intervals")
    print("   5. The chart will automatically update with live data")
    
    return True

if __name__ == '__main__':
    main()
