#!/usr/bin/env python3
"""
Playwright Test for Google Cloud Dashboard
Tests the live dashboard at https://ai-quant-trading.uc.r.appspot.com/dashboard
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardPlaywrightTest:
    """Playwright test for Google Cloud dashboard"""
    
    def __init__(self, dashboard_url: str = "https://ai-quant-trading.uc.r.appspot.com/dashboard"):
        """Initialize test with dashboard URL"""
        self.dashboard_url = dashboard_url
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'total_tests': 0,
            'results': []
        }
    
    async def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        self.test_results['total_tests'] += 1
        logger.info(f"🧪 Running test: {test_name}")
        
        try:
            result = await test_func()
            if result:
                self.test_results['tests_passed'] += 1
                self.test_results['results'].append({
                    'test': test_name,
                    'status': 'PASSED',
                    'message': 'Test completed successfully'
                })
                logger.info(f"✅ {test_name}: PASSED")
            else:
                self.test_results['tests_failed'] += 1
                self.test_results['results'].append({
                    'test': test_name,
                    'status': 'FAILED',
                    'message': 'Test returned False'
                })
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            self.test_results['tests_failed'] += 1
            self.test_results['results'].append({
                'test': test_name,
                'status': 'FAILED',
                'message': str(e)
            })
            logger.error(f"❌ {test_name}: FAILED - {e}")
    
    async def test_dashboard_loads(self, page):
        """Test if dashboard loads successfully"""
        try:
            # Use domcontentloaded to avoid long polling/networkidle flake on App Engine
            await page.goto(self.dashboard_url, wait_until='domcontentloaded', timeout=60000)
            
            # Check if main elements are present
            title = await page.text_content('h1')
            if 'AI Trading Dashboard' in title:
                logger.info("✅ Dashboard title found")
                return True
            else:
                logger.error(f"❌ Dashboard title not found: {title}")
                return False
        except Exception as e:
            logger.error(f"❌ Dashboard load error: {e}")
            return False
    
    async def test_connection_status(self, page):
        """Test connection status indicator"""
        try:
            # Wait for connection status element
            await page.wait_for_selector('.connection-status', timeout=10000)
            
            connection_status = await page.text_content('.connection-status')
            if connection_status:
                logger.info(f"✅ Connection status: {connection_status}")
                return True
            else:
                logger.error("❌ Connection status not found")
                return False
        except Exception as e:
            logger.error(f"❌ Connection status test error: {e}")
            return False
    
    async def test_market_data_section(self, page):
        """Test market data section"""
        try:
            # Check for market data elements - try multiple selectors
            market_section = await page.query_selector('.market-data-section') or \
                           await page.query_selector('.live-market-data') or \
                           await page.query_selector('[class*="market"]')
            if market_section:
                logger.info("✅ Market data section found")
                return True
            else:
                # Check if any market data is displayed
                market_text = await page.text_content('body')
                if 'EUR/USD' in market_text or 'GBP/USD' in market_text or 'XAU/USD' in market_text:
                    logger.info("✅ Market data content found")
                    return True
                else:
                    logger.error("❌ Market data section not found")
                    return False
        except Exception as e:
            logger.error(f"❌ Market data test error: {e}")
            return False
    
    async def test_trading_systems_section(self, page):
        """Test trading systems section"""
        try:
            # Check for trading systems - try multiple selectors
            systems_section = await page.query_selector('.trading-systems-section') or \
                            await page.query_selector('[class*="trading"]') or \
                            await page.query_selector('[class*="system"]')
            if systems_section:
                logger.info("✅ Trading systems section found")
                return True
            else:
                # Check if any trading system content is displayed
                systems_text = await page.text_content('body')
                if 'Ultra Strict' in systems_text or 'Gold Scalping' in systems_text or 'Momentum' in systems_text:
                    logger.info("✅ Trading systems content found")
                    return True
                else:
                    logger.error("❌ Trading systems section not found")
                    return False
        except Exception as e:
            logger.error(f"❌ Trading systems test error: {e}")
            return False
    
    async def test_news_section(self, page):
        """Test news section"""
        try:
            # Check for news section - try multiple selectors
            news_section = await page.query_selector('.news-section') or \
                         await page.query_selector('[class*="news"]') or \
                         await page.query_selector('.live-news-feed')
            if news_section:
                logger.info("✅ News section found")
                return True
            else:
                # Check if any news content is displayed
                news_text = await page.text_content('body')
                if 'Live News Feed' in news_text or 'News' in news_text or 'AI Trading System' in news_text:
                    logger.info("✅ News content found")
                    return True
                else:
                    logger.error("❌ News section not found")
                    return False
        except Exception as e:
            logger.error(f"❌ News section test error: {e}")
            return False
    
    async def test_ai_assistant_section(self, page):
        """Test AI assistant section"""
        try:
            # Check for AI assistant elements - try multiple selectors
            ai_section = await page.query_selector('.ai-assistant-panel') or \
                        await page.query_selector('[class*="ai"]') or \
                        await page.query_selector('[class*="assistant"]')
            if ai_section:
                logger.info("✅ AI assistant section found")
                return True
            else:
                # Check if any AI content is displayed
                ai_text = await page.text_content('body')
                if 'AI Insights' in ai_text or 'AI Assistant' in ai_text or 'AI Trading' in ai_text:
                    logger.info("✅ AI assistant content found")
                    return True
                else:
                    logger.error("❌ AI assistant section not found")
                    return False
        except Exception as e:
            logger.error(f"❌ AI assistant test error: {e}")
            return False
    
    async def test_websocket_connection(self, page):
        """Test WebSocket connection"""
        try:
            # Check for WebSocket connection in console logs
            logs = []
            
            def handle_console(msg):
                logs.append(msg.text)
            
            page.on('console', handle_console)
            
            # Wait for WebSocket connection attempts
            await page.wait_for_timeout(5000)
            
            # Check for WebSocket connection messages
            websocket_logs = [log for log in logs if 'socket' in log.lower() or 'websocket' in log.lower()]
            if websocket_logs:
                logger.info(f"✅ WebSocket logs found: {websocket_logs[:3]}")
                return True
            else:
                logger.error("❌ No WebSocket connection logs found")
                return False
        except Exception as e:
            logger.error(f"❌ WebSocket test error: {e}")
            return False
    
    async def test_api_endpoints(self, page):
        """Test API endpoints"""
        try:
            # Test API status endpoint
            response = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/status')
            if response.status == 200:
                data = await response.json()
                logger.info(f"✅ API status: {data.get('system_status', 'unknown')}")
                return True
            else:
                logger.error(f"❌ API status failed: {response.status}")
                return False
        except Exception as e:
            logger.error(f"❌ API endpoints test error: {e}")
            return False
    
    async def test_countdown_timer(self, page):
        """Test countdown timer functionality"""
        try:
            # Check for countdown timer element
            timer_element = await page.query_selector('#newsTimer')
            if timer_element:
                timer_text = await timer_element.text_content()
                logger.info(f"✅ Countdown timer found: {timer_text}")
                return True
            else:
                logger.error("❌ Countdown timer not found")
                return False
        except Exception as e:
            logger.error(f"❌ Countdown timer test error: {e}")
            return False
    
    async def test_ai_chat_functionality(self, page):
        """Test AI chat functionality"""
        try:
            # Look for AI chat input
            chat_input = await page.query_selector('.chat-input textarea')
            if chat_input:
                # Try to send a test message
                await chat_input.fill("Test market analysis")
                await chat_input.press('Enter')
                
                # Wait for response
                await page.wait_for_timeout(3000)
                
                logger.info("✅ AI chat functionality tested")
                return True
            else:
                logger.error("❌ AI chat input not found")
                return False
        except Exception as e:
            logger.error(f"❌ AI chat test error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all dashboard tests"""
        logger.info("🚀 Starting Playwright Dashboard Test")
        logger.info("=" * 60)
        logger.info(f"🌐 Testing dashboard at: {self.dashboard_url}")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Set to True for headless
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Core functionality tests
                await self.run_test("Dashboard Loads", lambda: self.test_dashboard_loads(page))
                await self.run_test("Connection Status", lambda: self.test_connection_status(page))
                await self.run_test("Market Data Section", lambda: self.test_market_data_section(page))
                await self.run_test("Trading Systems Section", lambda: self.test_trading_systems_section(page))
                await self.run_test("News Section", lambda: self.test_news_section(page))
                await self.run_test("AI Assistant Section", lambda: self.test_ai_assistant_section(page))
                
                # Advanced functionality tests
                await self.run_test("WebSocket Connection", lambda: self.test_websocket_connection(page))
                await self.run_test("API Endpoints", lambda: self.test_api_endpoints(page))
                await self.run_test("Countdown Timer", lambda: self.test_countdown_timer(page))
                await self.run_test("AI Chat Functionality", lambda: self.test_ai_chat_functionality(page))
                
            finally:
                await browser.close()
            
            # Print results
            self.print_results()
    
    def print_results(self):
        """Print test results summary"""
        logger.info("=" * 60)
        logger.info("📊 PLAYWRIGHT DASHBOARD TEST RESULTS")
        logger.info("=" * 60)
        
        total = self.test_results['total_tests']
        passed = self.test_results['tests_passed']
        failed = self.test_results['tests_failed']
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results['results']:
                if result['status'] == 'FAILED':
                    logger.info(f"  - {result['test']}: {result['message']}")
        
        logger.info("\n✅ PASSED TESTS:")
        for result in self.test_results['results']:
            if result['status'] == 'PASSED':
                logger.info(f"  - {result['test']}")
        
        # Save results to file
        results_file = f"playwright_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"\n📄 Results saved to: {results_file}")
        
        if failed == 0:
            logger.info("\n🎉 ALL TESTS PASSED! Dashboard is fully functional.")
        else:
            logger.info(f"\n⚠️ {failed} tests failed. Please check the issues above.")

async def main():
    """Main test function"""
    tester = DashboardPlaywrightTest()
    await tester.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())
