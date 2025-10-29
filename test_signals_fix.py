#!/usr/bin/env python3

from playwright.sync_api import sync_playwright
import time

def test_signals_fix():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print("🔍 Testing trade signals fix...")
        
        # Navigate to dashboard
        page.goto("http://localhost:8080", timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        
        # Wait for page to load
        time.sleep(3)
        
        # Check console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        # Check if JavaScript is working
        js_working = page.evaluate("""
            () => {
                // Check if our functions exist
                return {
                    loadTradingSignals: typeof loadTradingSignals === 'function',
                    updateTradingSignals: typeof updateTradingSignals === 'function',
                    initDashboard: typeof initDashboard === 'function'
                };
            }
        """)
        
        print(f"📊 JavaScript functions available: {js_working}")
        
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
        page.screenshot(path="signals_fix_test.png")
        print("📸 Screenshot saved as signals_fix_test.png")
        
        browser.close()
        
        return signals_status == 'Signals loaded successfully'

if __name__ == "__main__":
    success = test_signals_fix()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Trade signals fix test")

