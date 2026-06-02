import sys
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8787"

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"Loading {BASE_URL}...")
        try:
            page.goto(BASE_URL, timeout=10000)
        except Exception as e:
            print(f"Failed to load dashboard: {e}")
            return False

        # Wait for initial load
        page.wait_for_load_state("networkidle")
        time.sleep(2) # Extra buffer for JS rendering

        # --- Verify News Tab ---
        print("Clicking News Tab...")
        page.locator("#nav-news").click()
        time.sleep(2)
        
        # The text might be "News Feed Error" or "Unable to load news feed" or "No news items returned"
        news_error = page.locator("text=News Feed Error").is_visible() or \
                     page.locator("text=Unable to load news feed").is_visible() or \
                     page.locator("text=No news items returned").is_visible()
        
        if news_error:
            print("FAIL: News Feed Error detected.")
        else:
            print("PASS: No News Feed Error.")

        # --- Verify Performance Tab ---
        print("Clicking Performance Tab...")
        page.locator("#nav-reports").click()
        time.sleep(2)
        
        # Text: "Failed to load performance data"
        perf_error = page.locator("text=Failed to load performance data").is_visible()
        
        # Check specific sections
        strategies_loaded = page.locator("#strategies-container .glass-card").count() > 0
        accounts_loaded = page.locator("#accounts-container .glass-card").count() > 0
        
        print("-" * 40)
        print("VERIFICATION RESULTS:")
        
        if news_error:
            print("FAIL: News Feed Error detected (Expected in diagnosis).")
        else:
            print("PASS: No News Feed Error.")
            
        if perf_error:
            print("FAIL: Performance Data Error detected (Expected in diagnosis).")
        else:
            print("PASS: No Performance Data Error.")
            
        print("-" * 40)
        
        browser.close()
        
        # Return False if we see the errors we want to fix
        if news_error or perf_error:
            return False
        return True

if __name__ == "__main__":
    # Check if server is up
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print(f"Server not running at {BASE_URL}. Please start it first.")
        sys.exit(1)
        
    success = verify_dashboard()
    # Invert success because we expect failure now? 
    # No, the script should return False if dashboard is broken.
    sys.exit(0 if success else 1)
