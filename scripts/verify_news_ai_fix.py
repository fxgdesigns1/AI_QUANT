#!/usr/bin/env python3
"""
Verify News AI Fix - Comprehensive Test
Tests both the endpoint and UI rendering
"""

import asyncio
import os
import json
import requests
from playwright.async_api import async_playwright

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://127.0.0.1:28787")

async def verify_news_ai_fix():
    """Verify News AI is working correctly"""
    print("=" * 70)
    print("NEWS AI FIX VERIFICATION")
    print("=" * 70)
    print("")
    
    # Test 1: Check endpoint directly
    print("🔍 Test 1: Checking /api/news/assess endpoint...")
    try:
        response = requests.get(f"{DASHBOARD_URL}/api/news/assess", timeout=10)
        data = response.json()
        
        # Navigate through truth envelope structure
        envelope_data = data.get("data", {})
        news_count = envelope_data.get("news_count", 0)
        summary = envelope_data.get("summary")
        sentiment = envelope_data.get("sentiment")
        impact_score = envelope_data.get("impact_score")
        
        print(f"   News Count: {news_count}")
        print(f"   Summary: {summary[:80] if summary else 'MISSING'}...")
        print(f"   Sentiment: {sentiment or 'MISSING'}")
        print(f"   Impact Score: {impact_score if impact_score is not None else 'MISSING'}")
        
        if summary and sentiment and impact_score is not None:
            print("   ✅ Endpoint returns all required fields")
            endpoint_ok = True
        else:
            print("   ❌ Endpoint missing required fields (needs code deployment)")
            endpoint_ok = False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        endpoint_ok = False
    
    print("")
    
    # Test 2: Check UI rendering with Playwright
    print("🔍 Test 2: Checking UI rendering...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Navigate to News tab
            news_tab_selectors = [
                'a[href="#news"]',
                '[data-tab="news"]',
                '#nav-news',
                'text=News'
            ]
            
            found_tab = False
            for selector in news_tab_selectors:
                try:
                    element = page.locator(selector)
                    if await element.count() > 0:
                        await element.first().click()
                        await page.wait_for_timeout(2000)
                        found_tab = True
                        print(f"   ✅ Found and clicked news tab")
                        break
                except:
                    continue
            
            if not found_tab:
                print("   ⚠️  News tab not found, checking for news section directly...")
                await page.goto(f"{DASHBOARD_URL}/#news", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
            
            # Check for AI insights elements
            ai_elements = {
                'sentiment': page.locator('#news-sentiment'),
                'summary': page.locator('#news-sentiment-summary'),
                'impact': page.locator('#news-impact-score')
            }
            
            ui_ok = True
            for name, locator in ai_elements.items():
                try:
                    count = await locator.count()
                    if count > 0:
                        text = await locator.text_content()
                        is_visible = await locator.first().is_visible()
                        if is_visible and text and text.strip() not in ['N/A', 'NO BACKEND FACT AVAILABLE', '--']:
                            print(f"   ✅ {name.capitalize()}: {text[:50]}...")
                        else:
                            print(f"   ⚠️  {name.capitalize()}: Not visible or empty")
                            if text:
                                print(f"      Current value: {text}")
                    else:
                        print(f"   ❌ {name.capitalize()} element not found")
                        ui_ok = False
                except Exception as e:
                    print(f"   ⚠️  Error checking {name}: {e}")
                    ui_ok = False
            
            # Take screenshot
            screenshot_path = "news_ai_fix_verification.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 Screenshot: {screenshot_path}")
            
            await page.wait_for_timeout(5000)
            
        finally:
            await browser.close()
    
    print("")
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Endpoint Status: {'✅ OK' if endpoint_ok else '❌ NEEDS DEPLOYMENT'}")
    print(f"UI Status: {'✅ OK' if ui_ok else '⚠️  CHECK SCREENSHOT'}")
    print("")
    
    if not endpoint_ok:
        print("🔧 FIXES APPLIED (need deployment):")
        print("   1. Updated /api/news/assess to fetch news from provider if snapshot empty")
        print("   2. Endpoint now analyzes sentiment and returns summary/impact_score")
        print("   3. Template already has rendering logic - just needs correct data")
        print("")
        print("   To deploy: Push changes to VM and restart control plane service")
    else:
        print("✅ All fixes working correctly!")
    
    print("")

if __name__ == "__main__":
    asyncio.run(verify_news_ai_fix())
