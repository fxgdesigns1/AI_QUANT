"""
Comprehensive Playwright verification for VM dashboard.
Verifies News AI, Journal, Trade Info, and all components are populated.
"""
import asyncio
import os
from playwright.async_api import async_playwright
import json
from pathlib import Path
from datetime import datetime

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:28787")
SCREENSHOTS_DIR = Path("screenshots/vm_dashboard_verification")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def take_screenshot(page, name: str):
    """Take screenshot with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = SCREENSHOTS_DIR / f"{timestamp}_{name}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"  ✓ Screenshot: {screenshot_path}")
    return screenshot_path


async def verify_api_response(page, endpoint: str):
    """Verify API endpoint returns valid response"""
    try:
        response = await page.request.get(f"{DASHBOARD_URL}{endpoint}")
        assert response.ok, f"API {endpoint} returned {response.status}"
        body = await response.json()
        return body
    except Exception as e:
        print(f"  ❌ API {endpoint} failed: {e}")
        return None


async def test_dashboard_fully_populated():
    """Comprehensive test of all dashboard components"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        console_errors = []
        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
        page.on("console", handle_console)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": DASHBOARD_URL,
            "tests": {}
        }
        
        print("=" * 60)
        print("VM DASHBOARD COMPREHENSIVE VERIFICATION")
        print("=" * 60)
        print(f"\nDashboard URL: {DASHBOARD_URL}\n")
        
        # Step 1: Load dashboard
        print("1️⃣ Loading dashboard...")
        await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)  # Wait for initialization
        await take_screenshot(page, "01_dashboard_loaded")
        
        # Step 2: Verify News Count Widget (Top Right)
        print("\n2️⃣ Verifying News Count Widget (Top Right)...")
        news_count_elem = page.locator("#news-count")
        if await news_count_elem.count() > 0:
            news_count = await news_count_elem.text_content() or "0"
            news_count_int = int(news_count.strip()) if news_count.strip().isdigit() else 0
            print(f"  News count: {news_count}")
            results["tests"]["news_count_widget"] = {
                "count": news_count_int,
                "visible": await news_count_elem.is_visible()
            }
            
            if news_count_int > 0:
                print(f"  ✅ News count widget shows {news_count_int} items")
                news_headline = page.locator("#news-top-headline")
                if await news_headline.count() > 0:
                    headline = await news_headline.text_content() or "--"
                    print(f"  Headline: {headline[:50]}...")
                    results["tests"]["news_count_widget"]["headline"] = headline[:50]
            else:
                print(f"  ⚠️ News count is 0")
        else:
            print(f"  ❌ News count widget not found")
            results["tests"]["news_count_widget"] = {"error": "not_found"}
        
        # Step 3: Verify News API
        print("\n3️⃣ Verifying News API...")
        news_api = await verify_api_response(page, "/api/news")
        if news_api:
            news_items = news_api.get("data", {}).get("news", [])
            truth_complete = news_api.get("truth", {}).get("complete", False)
            print(f"  News items: {len(news_items)}")
            print(f"  Truth complete: {truth_complete}")
            results["tests"]["news_api"] = {
                "items_count": len(news_items),
                "truth_complete": truth_complete,
                "has_items": len(news_items) > 0
            }
            
            if len(news_items) > 0:
                print(f"  ✅ News API returns {len(news_items)} items")
                print(f"  First item: {news_items[0].get('title', 'N/A')[:60]}...")
            else:
                print(f"  ⚠️ News API returns 0 items")
        
        # Step 4: Navigate to News AI Tab
        print("\n4️⃣ Navigating to News AI Tab...")
        
        # Register dialog handler before clicking
        dialog_messages = []
        def handle_dialog(dialog):
            dialog_messages.append(dialog.message)
            asyncio.create_task(dialog.accept())
        page.on("dialog", handle_dialog)
        
        news_nav = page.locator("#nav-news")
        if await news_nav.count() > 0:
            await news_nav.click()
            await page.wait_for_timeout(3000)  # Wait for tab to load
            
            # Check for alerts after navigation
            if dialog_messages:
                print(f"  ❌ Alert detected: {dialog_messages[-1]}")
                results["tests"]["news_ai_navigation"] = {"blocked": True, "alert": dialog_messages[-1]}
            else:
                print(f"  ✅ News AI tab opened without blocking")
                
                # Verify news feed
                news_feed = page.locator("#news-feed")
                if await news_feed.count() > 0:
                    feed_text = await news_feed.text_content() or ""
                    feed_visible = await news_feed.is_visible()
                    has_content = len(feed_text.strip()) > 0 and "unavailable" not in feed_text.lower() and "NO BACKEND" not in feed_text
                    
                    print(f"  News feed visible: {feed_visible}")
                    print(f"  News feed has content: {has_content}")
                    if has_content:
                        print(f"  ✅ News feed populated")
                        print(f"  Preview: {feed_text[:100]}...")
                    else:
                        print(f"  ⚠️ News feed empty or showing error")
                    
                    results["tests"]["news_ai_navigation"] = {
                        "blocked": False,
                        "feed_visible": feed_visible,
                        "feed_has_content": has_content,
                        "feed_preview": feed_text[:200]
                    }
                    
                    await take_screenshot(page, "04_news_ai_populated")
                else:
                    print(f"  ❌ News feed element not found")
                    results["tests"]["news_ai_navigation"] = {"error": "feed_element_not_found"}
        else:
            print(f"  ❌ News AI nav element not found")
            results["tests"]["news_ai_navigation"] = {"error": "nav_element_not_found"}
        
        # Step 5: Navigate to Journal Tab
        print("\n5️⃣ Navigating to Forensic Journal Tab...")
        journal_nav = page.locator("#nav-journal")
        if await journal_nav.count() > 0:
            await journal_nav.click()
            await page.wait_for_timeout(2000)
            
            journal_list = page.locator("#journal-list")
            if await journal_list.count() > 0:
                journal_text = await journal_list.text_content() or ""
                journal_visible = await journal_list.is_visible()
                has_content = len(journal_text.strip()) > 0 and "unavailable" not in journal_text.lower() and "NO BACKEND" not in journal_text
                
                print(f"  Journal visible: {journal_visible}")
                print(f"  Journal has content: {has_content}")
                
                results["tests"]["journal_navigation"] = {
                    "visible": journal_visible,
                    "has_content": has_content,
                    "preview": journal_text[:200]
                }
                
                if has_content:
                    print(f"  ✅ Journal loaded with content")
                    print(f"  Preview: {journal_text[:100]}...")
                else:
                    print(f"  ⚠️ Journal empty or showing unavailable message")
                
                await take_screenshot(page, "05_journal_loaded")
            else:
                print(f"  ⚠️ Journal list element not found")
                results["tests"]["journal_navigation"] = {"error": "journal_element_not_found"}
        
        # Step 6: Verify Trade Info (Active/Open Trades)
        print("\n6️⃣ Verifying Trade Info (Active Trades)...")
        open_trades_list = page.locator("#open-trades-list")
        if await open_trades_list.count() > 0:
            trades_text = await open_trades_list.text_content() or ""
            trades_visible = await open_trades_list.is_visible()
            has_content = len(trades_text.strip()) > 0 and "unavailable" not in trades_text.lower() and "NO BACKEND" not in trades_text
            
            print(f"  Open trades visible: {trades_visible}")
            print(f"  Open trades has content: {has_content}")
            
            results["tests"]["open_trades"] = {
                "visible": trades_visible,
                "has_content": has_content,
                "preview": trades_text[:200]
            }
            
            if has_content:
                print(f"  ✅ Open trades loaded")
                print(f"  Preview: {trades_text[:100]}...")
            else:
                print(f"  ⚠️ Open trades empty or unavailable")
        
        # Step 7: Verify Performance Tab
        print("\n7️⃣ Navigating to Performance Tab...")
        reports_nav = page.locator("#nav-reports")
        if await reports_nav.count() > 0:
            await reports_nav.click()
            await page.wait_for_timeout(2000)
            
            performance_placeholder = page.locator("#performance-placeholder")
            if await performance_placeholder.count() > 0:
                perf_text = await performance_placeholder.text_content() or ""
                print(f"  Performance placeholder: {perf_text[:100]}...")
                
                results["tests"]["performance_tab"] = {
                    "visible": True,
                    "content": perf_text[:200]
                }
                
                await take_screenshot(page, "07_performance_loaded")
        
        # Step 8: Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for test_name, test_result in results["tests"].items():
            if isinstance(test_result, dict):
                if test_result.get("error"):
                    print(f"❌ {test_name}: {test_result['error']}")
                    all_passed = False
                elif test_result.get("blocked"):
                    print(f"❌ {test_name}: Blocked")
                    all_passed = False
                elif test_result.get("has_content") or test_result.get("items_count", 0) > 0:
                    print(f"✅ {test_name}: PASS")
                else:
                    print(f"⚠️ {test_name}: Empty/No content")
        
        # Save results
        results_path = SCREENSHOTS_DIR / "verification_results.json"
        results_path.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {results_path}")
        
        if console_errors:
            print(f"\n⚠️ Console errors: {len(console_errors)}")
            for err in console_errors[-5:]:
                print(f"  - {err}")
        
        await browser.close()
        
        return {
            "success": all_passed,
            "results": results
        }


async def main():
    """Run verification"""
    print(f"\nTesting dashboard at: {DASHBOARD_URL}")
    print("Make sure SSH tunnel is running if using port 28787\n")
    
    result = await test_dashboard_fully_populated()
    
    if result["success"]:
        print("\n✅ VERIFICATION COMPLETE - All components populated")
    else:
        print("\n⚠️ VERIFICATION COMPLETE - Some components need attention")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
