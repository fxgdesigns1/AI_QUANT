#!/usr/bin/env python3

from playwright.sync_api import sync_playwright
import time

def test_javascript_syntax_errors():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("🔍 Testing JavaScript syntax errors...")
        
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
        
        # Check for JavaScript syntax errors
        js_errors = [msg for msg in console_messages if msg.startswith("error:")]
        
        print(f"📊 Total console messages: {len(console_messages)}")
        print(f"❌ JavaScript errors: {len(js_errors)}")
        
        if js_errors:
            print("\n🔍 JavaScript errors found:")
            for error in js_errors:
                print(f"  {error}")
        
        # Check if JavaScript is executing at all
        js_working = page.evaluate("""
            () => {
                // Try to execute some JavaScript
                try {
                    // Check if our functions exist
                    const functions = {
                        loadTradingSignals: typeof loadTradingSignals === 'function',
                        updateTradingSignals: typeof updateTradingSignals === 'function',
                        initDashboard: typeof initDashboard === 'function'
                    };
                    
                    // Check if there are any global variables
                    const globals = Object.keys(window).filter(key => 
                        key.includes('load') || key.includes('update') || key.includes('init')
                    );
                    
                    return {
                        functions: functions,
                        globals: globals.slice(0, 10),
                        error: null
                    };
                } catch (e) {
                    return {
                        functions: {},
                        globals: [],
                        error: e.message
                    };
                }
            }
        """)
        
        print(f"📊 JavaScript execution status: {js_working}")
        
        if js_working.get('error'):
            print(f"❌ JavaScript execution error: {js_working['error']}")
        
        # Print all console messages
        print("\n🔍 All console messages:")
        for msg in console_messages:
            print(f"  {msg}")
        
        # Take screenshot
        page.screenshot(path="javascript_syntax_errors_test.png")
        print("📸 Screenshot saved as javascript_syntax_errors_test.png")
        
        browser.close()
        
        return len(js_errors) == 0 and not js_working.get('error')

if __name__ == "__main__":
    success = test_javascript_syntax_errors()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: JavaScript syntax errors test")
