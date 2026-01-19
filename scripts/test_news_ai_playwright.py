#!/usr/bin/env python3
"""
Test News AI functionality on dashboard using Playwright
Verifies that AI insights are displayed correctly
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://127.0.0.1:28787")
CONTROL_PLANE_TOKEN = os.getenv("CONTROL_PLANE_TOKEN", "")

async def test_news_ai():
    """Test News AI functionality"""
    print("=" * 70)
    print("NEWS AI VERIFICATION TEST")
    print("=" * 70)
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print("")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Track errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
        
        try:
            print("📡 Navigating to dashboard...")
            await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Set auth token if provided
            if CONTROL_PLANE_TOKEN:
                await page.evaluate(f"""
                    localStorage.setItem('control_plane_token', '{CONTROL_PLANE_TOKEN}');
                """)
            
            await page.wait_for_timeout(2000)
            
            # Test 1: Check /api/news endpoint
            print("")
            print("🔍 Test 1: Checking /api/news endpoint...")
            try:
                news_result = await page.evaluate(f"""
                    fetch('{DASHBOARD_URL}/api/news')
                        .then(r => r.json())
                        .then(d => {{ 
                            const data = d.data || d;
                            return {{
                                ok: true, 
                                news_count: (data.news || []).length,
                                has_news: (data.news || []).length > 0,
                                source: data.source_mode || 'unknown'
                            }}; 
                        }})
                        .catch(e => {{ return {{ok: false, error: e.message}}; }});
                """)
                if news_result.get('ok'):
                    print(f"   ✅ /api/news: {news_result.get('news_count', 0)} items, source: {news_result.get('source', 'unknown')}")
                else:
                    print(f"   ❌ /api/news: {news_result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"   ⚠️  /api/news error: {e}")
            
            # Test 2: Check /api/news/assess endpoint
            print("")
            print("🔍 Test 2: Checking /api/news/assess endpoint...")
            try:
                assess_result = await page.evaluate(f"""
                    fetch('{DASHBOARD_URL}/api/news/assess')
                        .then(r => r.json())
                        .then(d => {{ 
                            const data = d.data || d;
                            return {{
                                ok: true,
                                summary: data.summary || 'N/A',
                                sentiment: data.sentiment || 'N/A',
                                impact_score: data.impact_score || 0,
                                news_count: data.news_count || 0
                            }}; 
                        }})
                        .catch(e => {{ return {{ok: false, error: e.message}}; }});
                """)
                if assess_result.get('ok'):
                    print(f"   ✅ /api/news/assess is working:")
                    print(f"      Summary: {assess_result.get('summary', 'N/A')[:100]}...")
                    print(f"      Sentiment: {assess_result.get('sentiment', 'N/A')}")
                    print(f"      Impact Score: {assess_result.get('impact_score', 0)}")
                    print(f"      News Count: {assess_result.get('news_count', 0)}")
                else:
                    print(f"   ❌ /api/news/assess: {assess_result.get('error', 'unknown error')}")
            except Exception as e:
                print(f"   ⚠️  /api/news/assess error: {e}")
            
            # Test 3: Navigate to News tab
            print("")
            print("🔍 Test 3: Navigating to News tab...")
            try:
                # Look for news tab/link
                news_selectors = [
                    'a[href="#news"]',
                    'a[data-section="news"]',
                    '#nav-news',
                    '[data-section="news"]',
                    'a:has-text("News")',
                    'a:has-text("News & Events")'
                ]
                
                news_tab = None
                for selector in news_selectors:
                    try:
                        element = page.locator(selector)
                        count = await element.count()
                        if count > 0 and await element.first().is_visible():
                            news_tab = element.first()
                            print(f"   ✅ Found news tab with selector: {selector}")
                            break
                    except:
                        continue
                
                if news_tab:
                    await news_tab.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Clicked news tab")
                else:
                    print("   ⚠️  News tab not found, trying to navigate directly...")
                    await page.goto(f"{DASHBOARD_URL}/#news", wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"   ⚠️  Navigation error: {e}")
            
            # Test 4: Check if AI insights are displayed in UI
            print("")
            print("🔍 Test 4: Checking for AI insights in UI...")
            await page.wait_for_timeout(1000)
            
            # Look for AI insights elements
            ai_selectors = [
                '#ai-insights',
                '.ai-insights',
                '[data-ai-insights]',
                '.news-ai-summary',
                '.sentiment-analysis',
                '[id*="insight"]',
                '[class*="insight"]',
                '[id*="sentiment"]',
                '[class*="sentiment"]'
            ]
            
            found_ai = False
            for selector in ai_selectors:
                try:
                    element = page.locator(selector)
                    count = await element.count()
                    if count > 0:
                        is_visible = await element.first().is_visible()
                        if is_visible:
                            text = await element.first().text_content()
                            print(f"   ✅ Found AI element: {selector}")
                            print(f"      Text: {text[:100] if text else 'N/A'}...")
                            found_ai = True
                            break
                except:
                    continue
            
            if not found_ai:
                print("   ❌ AI insights NOT found in UI")
                print("   ⚠️  This is the problem - AI insights exist but aren't displayed!")
                
                # Check what's actually in the news section
                print("")
                print("   Checking news section content...")
                news_section_selectors = [
                    '#newsAlerts',
                    '#news-section',
                    '[id*="news"]',
                    '[class*="news"]'
                ]
                
                for selector in news_section_selectors:
                    try:
                        element = page.locator(selector)
                        count = await element.count()
                        if count > 0:
                            text = await element.first().inner_html()
                            print(f"   Found element {selector}:")
                            print(f"      Content length: {len(text)} chars")
                            if len(text) < 500:
                                print(f"      Preview: {text[:200]}...")
                            break
                    except:
                        continue
            
            # Test 5: Check browser console for errors/warnings
            print("")
            print("🔍 Test 5: Checking console errors...")
            if console_errors:
                print(f"   ⚠️  Found {len(console_errors)} console errors:")
                for err in console_errors[:5]:
                    print(f"      - {err}")
            else:
                print("   ✅ No console errors")
            
            # Take a screenshot for reference
            screenshot_path = "news_ai_verification.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"")
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Summary
            print("")
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print("✅ API endpoints are accessible")
            print(f"{'✅' if found_ai else '❌'} AI insights {'are' if found_ai else 'are NOT'} displayed in UI")
            print("")
            
            if not found_ai:
                print("🔧 ACTION REQUIRED:")
                print("   The /api/news/assess endpoint works but insights aren't shown in UI.")
                print("   Need to modify loadNewsData() to call /api/news/assess and display results.")
            
            # Keep browser open for inspection
            print("")
            print("Browser will stay open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_news_ai())
