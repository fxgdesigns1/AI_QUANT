#!/usr/bin/env python3

from playwright.sync_api import sync_playwright
import time

def test_javascript_execution_detailed():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("🔍 Testing JavaScript execution in detail...")
        
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
        
        # Check if JavaScript is executing at all
        js_working = page.evaluate("""
            () => {
                // Check if our functions exist
                const functions = {
                    loadTradingSignals: typeof loadTradingSignals === 'function',
                    updateTradingSignals: typeof updateTradingSignals === 'function',
                    initDashboard: typeof initDashboard === 'function',
                    initAIAssistant: typeof initAIAssistant === 'function'
                };
                
                // Check if there are any global variables
                const globals = Object.keys(window).filter(key => 
                    key.includes('load') || key.includes('update') || key.includes('init')
                );
                
                // Check if there are any script tags
                const scripts = document.querySelectorAll('script');
                
                // Check if there are any uncaught errors
                const hasErrorHandler = window.onerror ? true : false;
                
                return {
                    functions: functions,
                    globals: globals.slice(0, 10),
                    scriptCount: scripts.length,
                    hasErrorHandler: hasErrorHandler,
                    lastScript: scripts.length > 0 ? scripts[scripts.length - 1].src || 'inline' : 'none'
                };
            }
        """)
        
        print(f"📊 JavaScript execution status: {js_working}")
        
        # Check if signals are loading
        signals_status = page.evaluate("""
            () => {
                const container = document.getElementById('tradingSignals');
                if (!container) return 'No tradingSignals element found';
                
                const text = container.textContent || container.innerText || '';
                if (text.includes('Loading trading signals')) {
                    return 'Still loading';
                } else if (text.includes('No active signals')) {
                    return 'No signals';
                } else if (text.includes('EUR/USD') || text.includes('XAU/USD') || text.includes('GBP/USD')) {
                    return 'Signals loaded successfully';
                } else {
                    return `Unknown state: ${text.substring(0, 100)}`;
                }
            }
        """)
        
        print(f"📈 Signals status: {signals_status}")
        
        # Print console messages
        print("\n🔍 Console messages:")
        for msg in console_messages[-10:]:  # Last 10 messages
            print(f"  {msg}")
        
        # Take screenshot
        page.screenshot(path="javascript_execution_detailed_test.png")
        print("📸 Screenshot saved as javascript_execution_detailed_test.png")
        
        browser.close()
        
        return signals_status == 'Signals loaded successfully'

if __name__ == "__main__":
    success = test_javascript_execution_detailed()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: JavaScript execution detailed test")

