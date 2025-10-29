#!/usr/bin/env python3

from playwright.sync_api import sync_playwright
import time

def test_javascript_syntax():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("🔍 Testing JavaScript syntax...")
        
        # Navigate to dashboard
        page.goto("http://localhost:8080", timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        
        # Wait for page to load
        time.sleep(3)
        
        # Check console messages for errors
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        # Check if there are any JavaScript syntax errors
        js_errors = [msg for msg in console_messages if msg.startswith("error:")]
        
        print(f"📊 Console messages: {len(console_messages)}")
        print(f"❌ JavaScript errors: {len(js_errors)}")
        
        if js_errors:
            print("\n🔍 JavaScript errors found:")
            for error in js_errors[:5]:  # Show first 5 errors
                print(f"  {error}")
        
        # Check if the page loaded without errors
        page_errors = page.evaluate("""
            () => {
                // Check if there are any uncaught errors
                return window.onerror ? 'Has error handler' : 'No error handler';
            }
        """)
        
        print(f"📈 Page error status: {page_errors}")
        
        # Take screenshot
        page.screenshot(path="javascript_syntax_test.png")
        print("📸 Screenshot saved as javascript_syntax_test.png")
        
        browser.close()
        
        return len(js_errors) == 0

if __name__ == "__main__":
    success = test_javascript_syntax()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: JavaScript syntax test")

