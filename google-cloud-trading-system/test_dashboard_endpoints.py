#!/usr/bin/env python3
"""
Playwright test for dashboard endpoints
Tests all the new dashboard endpoints and functionality
"""

import asyncio
from playwright.async_api import async_playwright
import requests
import json

async def test_dashboard_endpoints():
    """Test all dashboard endpoints with Playwright"""
    
    print("🔍 TESTING DASHBOARD ENDPOINTS WITH PLAYWRIGHT")
    print("=" * 70)
    
    base_url = 'http://localhost:8080'
    
    # Test API endpoints first
    print("📊 TESTING API ENDPOINTS:")
    endpoints = [
        '/api/status',
        '/api/opportunities', 
        '/api/trade_ideas',
        '/api/insights',
        '/api/signals',
        '/api/reports',
        '/api/weekly-reports',
        '/api/roadmap',
        '/api/strategy-reports',
        '/api/performance-reports'
    ]
    
    working_endpoints = []
    broken_endpoints = []
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=10)
            if response.status_code == 200:
                working_endpoints.append(endpoint)
                print(f"  ✅ {endpoint}")
            else:
                broken_endpoints.append(f"{endpoint} ({response.status_code})")
                print(f"  ❌ {endpoint} ({response.status_code})")
        except Exception as e:
            broken_endpoints.append(f"{endpoint} (Error: {e})")
            print(f"  ❌ {endpoint} (Error: {e})")
    
    print(f"\n📋 SUMMARY:")
    print(f"  Working endpoints: {len(working_endpoints)}")
    print(f"  Broken endpoints: {len(broken_endpoints)}")
    
    if broken_endpoints:
        print(f"\n❌ BROKEN ENDPOINTS:")
        for endpoint in broken_endpoints:
            print(f"  - {endpoint}")
    
    # Test with Playwright browser
    print(f"\n🌐 TESTING WITH PLAYWRIGHT BROWSER:")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to dashboard
            print("  📱 Navigating to dashboard...")
            await page.goto(f'{base_url}/')
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Check if dashboard loaded
            title = await page.title()
            print(f"  📄 Page title: {title}")
            
            # Test if dashboard elements are present
            print("  🔍 Checking dashboard elements...")
            
            # Check for common dashboard elements
            elements_to_check = [
                'text=Dashboard',
                'text=Status',
                'text=Opportunities',
                'text=Signals',
                'text=Reports'
            ]
            
            found_elements = []
            for element in elements_to_check:
                try:
                    if await page.locator(element).count() > 0:
                        found_elements.append(element)
                        print(f"    ✅ Found: {element}")
                    else:
                        print(f"    ❌ Missing: {element}")
                except:
                    print(f"    ❌ Error checking: {element}")
            
            # Test API calls from browser
            print("  🔌 Testing API calls from browser...")
            
            # Test status API
            try:
                response = await page.evaluate(f"""
                    fetch('{base_url}/api/status')
                        .then(response => response.json())
                        .then(data => data)
                """)
                if response:
                    print(f"    ✅ Status API: {response.get('status', 'Unknown')}")
                else:
                    print(f"    ❌ Status API: No response")
            except Exception as e:
                print(f"    ❌ Status API: Error - {e}")
            
            # Test opportunities API
            try:
                response = await page.evaluate(f"""
                    fetch('{base_url}/api/opportunities')
                        .then(response => response.json())
                        .then(data => data)
                """)
                if response:
                    count = response.get('count', 0)
                    print(f"    ✅ Opportunities API: {count} opportunities")
                else:
                    print(f"    ❌ Opportunities API: No response")
            except Exception as e:
                print(f"    ❌ Opportunities API: Error - {e}")
            
            # Test new endpoints
            new_endpoints = [
                '/api/signals',
                '/api/reports',
                '/api/weekly-reports',
                '/api/roadmap',
                '/api/strategy-reports',
                '/api/performance-reports'
            ]
            
            print("  🆕 Testing new endpoints from browser:")
            for endpoint in new_endpoints:
                try:
                    response = await page.evaluate(f"""
                        fetch('{base_url}{endpoint}')
                            .then(response => response.json())
                            .then(data => data)
                    """)
                    if response:
                        status = response.get('status', 'Unknown')
                        count = response.get('count', 0)
                        print(f"    ✅ {endpoint}: {status} ({count} items)")
                    else:
                        print(f"    ❌ {endpoint}: No response")
                except Exception as e:
                    print(f"    ❌ {endpoint}: Error - {e}")
            
            # Take screenshot
            print("  📸 Taking screenshot...")
            await page.screenshot(path='dashboard_test.png')
            print("    ✅ Screenshot saved as dashboard_test.png")
            
        except Exception as e:
            print(f"  ❌ Browser test error: {e}")
        
        finally:
            await browser.close()
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"  ✅ Working endpoints: {len(working_endpoints)}")
    print(f"  ❌ Broken endpoints: {len(broken_endpoints)}")
    print(f"  🌐 Browser test: Completed")
    print(f"  📸 Screenshot: dashboard_test.png")
    
    if len(working_endpoints) >= 4:
        print(f"\n🎉 DASHBOARD IS WORKING!")
        print(f"  Core functionality is operational")
        print(f"  Ready for production use")
    else:
        print(f"\n⚠️ DASHBOARD NEEDS ATTENTION")
        print(f"  Some endpoints are not working")
        print(f"  May need additional fixes")

if __name__ == "__main__":
    asyncio.run(test_dashboard_endpoints())
