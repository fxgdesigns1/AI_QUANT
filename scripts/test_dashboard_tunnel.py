#!/usr/bin/env python3
"""
Test dashboard via tunnel using Playwright
Opens browser and runs verification tests
"""

import asyncio
import subprocess
import sys
import time
import os
from playwright.async_api import async_playwright, expect

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://127.0.0.1:28787")
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN", "")

async def test_dashboard():
    """Test dashboard via tunnel"""
    print("🧪 Testing Dashboard via Tunnel")
    print(f"   URL: {DASHBOARD_URL}")
    print("")
    
    async with async_playwright() as p:
        # Launch browser (headed mode so you can see it)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Track errors
        console_errors = []
        page_errors = []
        bad_responses = []
        
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("response", lambda resp: bad_responses.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None)
        
        try:
            print("📡 Navigating to dashboard...")
            await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Set auth token if provided
            if CONTROL_PLANE_TOKEN:
                await page.evaluate(f"""
                    localStorage.setItem('control_plane_token', '{CONTROL_PLANE_TOKEN}');
                """)
                print("   ✅ Auth token set")
            
            # Wait a bit for page to load
            await page.wait_for_timeout(2000)
            
            # Check page title
            title = await page.title()
            print(f"   📄 Page title: {title}")
            
            # Test health endpoint (using page context, not request context)
            print("")
            print("🔍 Testing API endpoints...")
            try:
                # Use fetch from page context to avoid connection issues
                health_result = await page.evaluate(f"""
                    fetch('{DASHBOARD_URL}/health')
                        .then(r => r.json())
                        .then(d => {{ return {{ok: true, data: d}}; }})
                        .catch(e => {{ return {{ok: false, error: e.message}}; }});
                """)
                if health_result.get('ok'):
                    print(f"   ✅ /health: {health_result.get('data', {}).get('status', 'ok')}")
                else:
                    print(f"   ⚠️  /health: {health_result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"   ⚠️  /health error: {e}")
            
            # Test status endpoint
            try:
                status_result = await page.evaluate(f"""
                    fetch('{DASHBOARD_URL}/api/status')
                        .then(r => r.json())
                        .then(d => {{ return {{ok: true, data: d}}; }})
                        .catch(e => {{ return {{ok: false, error: e.message}}; }});
                """)
                if status_result.get('ok'):
                    print(f"   ✅ /api/status: {status_result.get('data', {}).get('system_label', 'N/A')}")
                else:
                    print(f"   ⚠️  /api/status: {status_result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"   ⚠️  /api/status error: {e}")
            
            # Test truth endpoint
            try:
                truth_result = await page.evaluate(f"""
                    fetch('{DASHBOARD_URL}/api/truth/status')
                        .then(r => r.json())
                        .then(d => {{ return {{ok: true, data: d}}; }})
                        .catch(e => {{ return {{ok: false, error: e.message}}; }});
                """)
                if truth_result.get('ok'):
                    truth_complete = truth_result.get('data', {}).get('truth', {}).get('complete', False)
                    print(f"   ✅ /api/truth/status: complete={truth_complete}")
                else:
                    print(f"   ⚠️  /api/truth/status: {truth_result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"   ⚠️  /api/truth/status error: {e}")
            
            # Check for key UI elements
            print("")
            print("🔍 Checking UI elements...")
            elements_to_check = [
                ("#nav-terminal", "Terminal tab"),
                ("#nav-journal", "Journal tab"),
                ("#nav-strategies", "Strategies tab"),
                ("#nav-news", "News tab"),
            ]
            
            for selector, name in elements_to_check:
                try:
                    element = page.locator(selector)
                    count = await element.count()
                    if count > 0:
                        is_visible = await element.first().is_visible()
                        print(f"   {'✅' if is_visible else '⚠️ '} {name}: {'visible' if is_visible else 'hidden'}")
                    else:
                        print(f"   ❌ {name}: not found")
                except Exception as e:
                    print(f"   ⚠️  {name}: error checking - {e}")
            
            # Try clicking some tabs
            print("")
            print("🖱️  Testing interactions...")
            try:
                # Click terminal tab
                terminal_tab = page.locator("#nav-terminal")
                count = await terminal_tab.count()
                if count > 0:
                    await terminal_tab.first().click()
                    await page.wait_for_timeout(500)
                    print("   ✅ Clicked terminal tab")
                
                # Click journal tab
                journal_tab = page.locator("#nav-journal")
                count = await journal_tab.count()
                if count > 0:
                    await journal_tab.first().click()
                    await page.wait_for_timeout(500)
                    print("   ✅ Clicked journal tab")
            except Exception as e:
                print(f"   ⚠️  Interaction error: {e}")
            
            # Summary
            print("")
            print("📊 Test Summary:")
            print(f"   Console errors: {len(console_errors)}")
            if console_errors:
                for err in console_errors[:5]:
                    print(f"      - {err}")
            
            print(f"   Page errors: {len(page_errors)}")
            if page_errors:
                for err in page_errors[:5]:
                    print(f"      - {err}")
            
            print(f"   Bad responses: {len(bad_responses)}")
            if bad_responses:
                for resp in bad_responses[:5]:
                    print(f"      - {resp}")
            
            # Keep browser open for manual inspection
            print("")
            print("✅ Tests complete! Browser will stay open for 30 seconds for manual inspection...")
            print("   (You can interact with the dashboard now)")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

def check_tunnel():
    """Check if tunnel is accessible"""
    import requests
    try:
        response = requests.get(f"{DASHBOARD_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("DASHBOARD TUNNEL TEST")
    print("=" * 70)
    print("")
    
    # Check tunnel first
    print("🔍 Checking tunnel connection...")
    if check_tunnel():
        print(f"   ✅ Tunnel is accessible at {DASHBOARD_URL}")
    else:
        print(f"   ❌ Tunnel not accessible at {DASHBOARD_URL}")
        print("   Please start the tunnel first:")
        print("   ./scripts/start_tunnel_and_test.sh")
        sys.exit(1)
    
    print("")
    
    # Run tests
    asyncio.run(test_dashboard())
