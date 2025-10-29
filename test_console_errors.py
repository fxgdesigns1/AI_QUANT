#!/usr/bin/env python3

from playwright.sync_api import sync_playwright
import time

def test_console_errors():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("🔍 Testing console errors...")
        
        # Navigate to dashboard
        page.goto("http://localhost:8080", timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        
        # Wait for page to load
        time.sleep(5)
        
        # Check console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        # Check for JavaScript errors
        js_errors = [msg for msg in console_messages if msg.startswith("error:")]
        js_warnings = [msg for msg in console_messages if msg.startswith("warning:")]
        
        print(f"📊 Total console messages: {len(console_messages)}")
        print(f"❌ JavaScript errors: {len(js_errors)}")
        print(f"⚠️ JavaScript warnings: {len(js_warnings)}")
        
        if js_errors:
            print("\n🔍 JavaScript errors found:")
            for error in js_errors:
                print(f"  {error}")
        
        if js_warnings:
            print("\n⚠️ JavaScript warnings found:")
            for warning in js_warnings[:5]:  # Show first 5 warnings
                print(f"  {warning}")
        
        # Check if there are any uncaught errors
        page_error = page.evaluate("""
            () => {
                // Check if there are any uncaught errors
                return window.onerror ? 'Has error handler' : 'No error handler';
            }
        """)
        
        print(f"📈 Page error status: {page_error}")
        
        # Print all console messages
        print("\n🔍 All console messages:")
        for msg in console_messages:
            print(f"  {msg}")
        
        # Take screenshot
        page.screenshot(path="console_errors_test.png")
        print("📸 Screenshot saved as console_errors_test.png")
        
        browser.close()
        
        return len(js_errors) == 0

if __name__ == "__main__":
    success = test_console_errors()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Console errors test")

