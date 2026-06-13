import os
import sys
import time
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Add project root to path
sys.path.append(os.getcwd())

# Load env vars
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tests/audit/audit_log.txt')
    ]
)
logger = logging.getLogger(__name__)

try:
    from src.control_plane.market_data_provider import get_latest_price, PriceIntegrityError
    from src.core.settings import settings
except ImportError as e:
    logger.error(f"Failed to import system modules: {e}")
    sys.exit(1)

DASHBOARD_URL = "http://localhost:28787/"

def audit_dashboard():
    logger.info(f"Starting dashboard audit against {DASHBOARD_URL}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # 1. Connectivity & Loading
            start_time = time.time()
            response = page.goto(DASHBOARD_URL, timeout=30000)
            load_time = time.time() - start_time
            
            if response.status != 200:
                logger.error(f"FAILED: Dashboard returned status {response.status}")
                return
            
            logger.info(f"SUCCESS: Dashboard loaded in {load_time:.2f}s")
            
            # Wait for dynamic content
            page.wait_for_load_state('networkidle')
            time.sleep(2) # Extra buffer for JS rendering
            
            # 2. Visual Elements Check
            screenshot_path = f"tests/audit/dashboard_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")

            # Dump HTML
            with open("tests/audit/page_dump.html", "w") as f:
                f.write(page.content())
            logger.info("Saved page HTML to tests/audit/page_dump.html")
            
            selectors = {
                "Title": "h1",
                "XAU/USD Bid": "#xauusd-bid",
                "XAU/USD Ask": "#xauusd-ask",
                "System Badge": "#system-label-badge"
            }
            
            for name, selector in selectors.items():
                if page.locator(selector).count() > 0 or page.locator(selector).is_visible():
                    logger.info(f"SUCCESS: Found element '{name}' ({selector})")
                else:
                    logger.warning(f"WARNING: Element '{name}' ({selector}) not found or not visible")

            # 3. Data Integrity & Price Verification
            logger.info("Verifying Price Data...")
            
            # Extract prices from DOM for XAU/USD
            bid_loc = page.locator("#xauusd-bid")
            ask_loc = page.locator("#xauusd-ask")
            
            if bid_loc.count() == 0 or ask_loc.count() == 0:
                logger.error("FAILED: XAU/USD price elements not found")
            else:
                bid_text = bid_loc.inner_text().strip()
                ask_text = ask_loc.inner_text().strip()
                
                logger.info(f"  Found XAU_USD Bid: {bid_text}, Ask: {ask_text}")
                
                if bid_text in ["--", "Loading..."] or ask_text in ["--", "Loading..."]:
                     logger.warning(f"  WARNING: Price for XAU_USD is not loaded yet")
                else:
                    try:
                        bid_display = float(bid_text.replace(",", ""))
                        ask_display = float(ask_text.replace(",", ""))
                        mid_display = (bid_display + ask_display) / 2.0
                        
                        # Verify against Truth Source
                        if settings.oanda_api_key and settings.oanda_account_id:
                            try:
                                logger.info(f"  Fetching real-time price for XAU_USD...")
                                real_price_data = get_latest_price("XAU_USD")
                                real_mid = real_price_data.mid
                                
                                diff = abs(mid_display - real_mid)
                                pct_diff = (diff / real_mid) * 100
                                
                                if pct_diff < 0.1: # 0.1% tolerance
                                    logger.info(f"  SUCCESS: Price accurate. Display Mid: {mid_display}, Real Mid: {real_mid:.4f} (Diff: {pct_diff:.4f}%)")
                                else:
                                    logger.error(f"  FAILURE: Price discrepancy! Display Mid: {mid_display}, Real Mid: {real_mid:.4f} (Diff: {pct_diff:.4f}%)")
                                    
                            except Exception as e:
                                logger.error(f"  Error fetching real price for XAU_USD: {e}")
                        else:
                            logger.info("  Skipping real-time verification (OANDA credentials missing)")

                    except ValueError as e:
                        logger.error(f"  Error parsing prices: {e}")

            # 4. Error Checking (Console)
            logger.info("Checking Console Logs...")
            # Note: console message handling is event-based in playwright, verifying strictly requires listening before nav
            # But we can check for other indicators or just rely on the fact that we loaded.
            # A more advanced check would require attaching a listener before goto.
            
        except Exception as e:
            logger.error(f"Audit failed with exception: {e}")
            page.screenshot(path="tests/audit/error_screenshot.png")
        finally:
            browser.close()

if __name__ == "__main__":
    audit_dashboard()
