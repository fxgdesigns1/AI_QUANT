"""
Playwright verification for News AI truth level fix.
Captures baseline behavior and verifies fix allows read-only navigation.
"""
import asyncio
import os
from playwright.async_api import async_playwright
import json
from pathlib import Path

BASE_URL = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:8787")
SCREENSHOTS_DIR = Path("screenshots/news_ai_truth_fix")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def take_screenshot(page, name: str):
    """Take screenshot with consistent naming"""
    screenshot_path = SCREENSHOTS_DIR / f"{name}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"✓ Screenshot saved: {screenshot_path}")
    return screenshot_path


async def verify_api_response(page, endpoint: str):
    """Verify API endpoint returns truth envelope"""
    response = await page.request.get(f"{BASE_URL}{endpoint}")
    assert response.ok, f"API {endpoint} returned {response.status}"
    body = await response.json()
    assert "truth" in body, f"Response missing 'truth' envelope: {endpoint}"
    return body


async def test_baseline_truth_blocking():
    """Phase 1: Capture baseline - News AI blocked by TRUTH_LEVEL"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))
        
        # Capture dialogs (truth level alerts)
        dialog_messages = []
        async def handle_dialog(dialog):
            dialog_messages.append(dialog.message)
            await dialog.accept()
        page.on("dialog", handle_dialog)
        
        print("\n=== PHASE 1: BASELINE VERIFICATION ===")
        
        # Navigate to dashboard with cache bypass
        print(f"Navigating to {BASE_URL}...")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        # Hard refresh to bypass cache
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)  # Wait for initialization
        
        # Verify dashboard loaded
        await take_screenshot(page, "01_dashboard_loaded")
        
        # Check API responses
        print("\nChecking API responses...")
        news_response = await verify_api_response(page, "/api/news")
        truth_status = await verify_api_response(page, "/api/truth/status")
        
        print(f"  /api/news truth.complete: {news_response.get('truth', {}).get('complete')}")
        print(f"  /api/truth/status truth.complete: {truth_status.get('truth', {}).get('complete')}")
        print(f"  /api/truth/status system_truth_state: {truth_status.get('data', {}).get('system_truth_state')}")
        
        # Try to click News AI tab
        print("\nAttempting to click News AI tab...")
        news_nav = page.locator("#nav-news")
        if await news_nav.count() > 0:
            await news_nav.click()
            await page.wait_for_timeout(2000)  # Wait for truth gate check
            
            # Check if alert appeared
            if dialog_messages:
                print(f"  ✓ Alert detected: {dialog_messages[-1]}")
                await take_screenshot(page, "02_baseline_truth_level_blocked")
                
                # Verify News tab is NOT visible
                news_tab = page.locator("#tab-news")
                is_visible = await news_tab.is_visible() if await news_tab.count() > 0 else False
                print(f"  News tab visible: {is_visible} (expected: False)")
                
                return {
                    "blocked": True,
                    "alert_message": dialog_messages[-1],
                    "news_tab_visible": is_visible,
                    "news_truth_complete": news_response.get('truth', {}).get('complete'),
                    "system_truth_state": truth_status.get('data', {}).get('system_truth_state')
                }
            else:
                print("  ⚠ No alert detected - News tab may have opened")
                await take_screenshot(page, "02_baseline_no_block")
        else:
            print("  ⚠ News nav element not found")
            await take_screenshot(page, "02_baseline_nav_not_found")
        
        await browser.close()
        return {"blocked": False, "reason": "Alert not triggered"}


async def test_fixed_news_visibility():
    """Phase 2: Verify News AI visible after fix"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        dialog_messages = []
        async def handle_dialog(dialog):
            dialog_messages.append(dialog.message)
            await dialog.accept()
        page.on("dialog", handle_dialog)
        
        print("\n=== PHASE 2: FIXED VERIFICATION ===")
        
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        # Hard refresh to bypass cache
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Verify async showTab exists
        has_async_showTab = await page.evaluate("typeof showTab === 'function' && showTab.constructor.name === 'AsyncFunction'")
        print(f"  Async showTab exists: {has_async_showTab}")
        if not has_async_showTab:
            print("  ⚠ WARNING: showTab is not async - old code may be cached")
        
        # Click News AI tab
        print("Clicking News AI tab...")
        news_nav = page.locator("#nav-news")
        assert await news_nav.count() > 0, "News nav element not found"
        
        await news_nav.click()
        await page.wait_for_timeout(2000)  # Wait for navigation
        
        # Verify no alert
        if dialog_messages:
            print(f"  ❌ Alert still present: {dialog_messages[-1]}")
            await take_screenshot(page, "03_fix_failed_alert_present")
            await browser.close()
            return {"success": False, "reason": "Alert still blocking navigation"}
        
        print("  ✓ No alert - navigation allowed")
        
        # Wait for tab to appear and check visibility
        try:
            news_tab = page.locator("#tab-news")
            await news_tab.wait_for(state="attached", timeout=5000)
            is_visible = await news_tab.is_visible()
            has_active_class = await news_tab.evaluate("el => el.classList.contains('active')")
            print(f"  News tab visible: {is_visible}")
            print(f"  News tab has active class: {has_active_class}")
            
            # Check if tab content exists
            news_feed = page.locator("#news-feed")
            await news_feed.wait_for(state="attached", timeout=3000)
            feed_visible = await news_feed.is_visible()
            feed_text = await news_feed.text_content() or ""
            print(f"  News feed visible: {feed_visible}")
            print(f"  News feed has content: {len(feed_text) > 0}")
            
            if not is_visible and not has_active_class:
                await take_screenshot(page, "03_fix_failed_tab_hidden")
                await browser.close()
                return {"success": False, "reason": "News tab not visible or active"}
        except Exception as e:
            print(f"  ⚠ Error checking tab visibility: {e}")
            await take_screenshot(page, "03_fix_error_checking_tab")
            await browser.close()
            return {"success": False, "reason": f"Error checking tab: {e}"}
        
        # Verify content renders (either news items or explicit empty state)
        await take_screenshot(page, "04_news_ai_visible")
        
        # Check for news feed content or empty state
        news_feed = page.locator("#news-feed")
        news_count = page.locator("#news-count")
        
        has_content = False
        if await news_feed.count() > 0:
            feed_text = await news_feed.text_content() or ""
            if "unavailable" not in feed_text.lower() and len(feed_text.strip()) > 0:
                has_content = True
                print(f"  ✓ News feed has content: {feed_text[:100]}")
        
        if await news_count.count() > 0:
            count_text = await news_count.text_content() or ""
            print(f"  News count: {count_text}")
        
        # Also check journal and performance tabs
        print("\nVerifying other read-only views...")
        
        # Journal
        journal_nav = page.locator("#nav-journal")
        if await journal_nav.count() > 0:
            await journal_nav.click()
            await page.wait_for_timeout(2000)
            if not dialog_messages:
                journal_tab = page.locator("#tab-journal")
                journal_visible = await journal_tab.is_visible() if await journal_tab.count() > 0 else False
                print(f"  Journal tab visible: {journal_visible}")
                if journal_visible:
                    await take_screenshot(page, "05_journal_visible")
        
        # Performance
        reports_nav = page.locator("#nav-reports")
        if await reports_nav.count() > 0:
            await reports_nav.click()
            await page.wait_for_timeout(2000)
            if not dialog_messages:
                reports_tab = page.locator("#tab-reports")
                reports_visible = await reports_tab.is_visible() if await reports_tab.count() > 0 else False
                print(f"  Reports tab visible: {reports_visible}")
                if reports_visible:
                    await take_screenshot(page, "06_performance_visible")
        
        await browser.close()
        return {
            "success": True,
            "news_visible": is_visible,
            "has_content": has_content,
            "alerts_triggered": len(dialog_messages)
        }


async def main():
    """Run both baseline and fixed verification"""
    print("=" * 60)
    print("NEWS AI TRUTH LEVEL FIX - PLAYWRIGHT VERIFICATION")
    print("=" * 60)
    
    # Phase 1: Baseline (skip if fix already applied)
    print("\n[Optional] Running baseline verification...")
    baseline_result = await test_baseline_truth_blocking()
    
    # Phase 2: Fixed verification
    print("\nRunning fixed verification...")
    fixed_result = await test_fixed_news_visibility()
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"\nBaseline (blocking): {baseline_result.get('blocked', 'N/A')}")
    print(f"Fixed (visible): {fixed_result.get('success', False)}")
    
    if fixed_result.get("success"):
        print("\n✅ SUCCESS: News AI is visible without truth level blocking")
    else:
        print(f"\n❌ FAILED: {fixed_result.get('reason', 'Unknown error')}")
    
    # Save results
    results = {
        "baseline": baseline_result,
        "fixed": fixed_result
    }
    results_path = SCREENSHOTS_DIR / "verification_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    asyncio.run(main())
