#!/usr/bin/env python3
"""
Detailed Dashboard Analysis
Identifies specific issues with dashboard loading and functionality
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

class DetailedDashboardAnalysis:
    """Detailed analysis of dashboard issues"""
    
    def __init__(self, dashboard_url: str = "https://ai-quant-trading.uc.r.appspot.com/dashboard"):
        """Initialize analysis"""
        self.dashboard_url = dashboard_url
        self.issues = []
        self.solutions = []
    
    async def analyze_dashboard_loading(self, page):
        """Analyze dashboard loading issues"""
        logger.info("🔍 Analyzing dashboard loading...")
        
        try:
            # Try to load the dashboard with different strategies
            await page.goto(self.dashboard_url, wait_until='domcontentloaded', timeout=15000)
            
            # Check if page loaded
            title = await page.title()
            logger.info(f"📄 Page title: {title}")
            
            # Check for specific elements
            elements_to_check = [
                ('h1', 'Dashboard title'),
                ('.connection-status', 'Connection status'),
                ('.live-market-data', 'Market data section'),
                ('.trading-systems', 'Trading systems'),
                ('.news-section', 'News section'),
                ('.ai-assistant-panel', 'AI assistant'),
                ('#newsTimer', 'Countdown timer'),
                ('.chat-input', 'AI chat input')
            ]
            
            for selector, description in elements_to_check:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        logger.info(f"✅ {description}: Found - '{text[:50]}...'")
                    else:
                        logger.warning(f"❌ {description}: Not found")
                        self.issues.append(f"Missing {description}")
                except Exception as e:
                    logger.error(f"❌ {description}: Error - {e}")
                    self.issues.append(f"Error with {description}: {e}")
            
            # Check for JavaScript errors
            js_errors = []
            def handle_console(msg):
                if msg.type == 'error':
                    js_errors.append(msg.text)
            
            page.on('console', handle_console)
            await page.wait_for_timeout(5000)
            
            if js_errors:
                logger.error(f"❌ JavaScript errors found: {js_errors}")
                self.issues.extend(js_errors)
            else:
                logger.info("✅ No JavaScript errors detected")
            
            return len(self.issues) == 0
            
        except Exception as e:
            logger.error(f"❌ Dashboard loading analysis failed: {e}")
            self.issues.append(f"Dashboard loading failed: {e}")
            return False
    
    async def analyze_websocket_connection(self, page):
        """Analyze WebSocket connection issues"""
        logger.info("🔍 Analyzing WebSocket connection...")
        
        try:
            # Monitor WebSocket events
            websocket_events = []
            
            def handle_console(msg):
                if 'socket' in msg.text.lower() or 'websocket' in msg.text.lower():
                    websocket_events.append(msg.text)
            
            page.on('console', handle_console)
            
            # Wait for WebSocket connection attempts
            await page.wait_for_timeout(10000)
            
            if websocket_events:
                logger.info(f"✅ WebSocket events detected: {websocket_events}")
                return True
            else:
                logger.warning("❌ No WebSocket events detected")
                self.issues.append("No WebSocket connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket analysis failed: {e}")
            self.issues.append(f"WebSocket analysis failed: {e}")
            return False
    
    async def analyze_ai_chat_functionality(self, page):
        """Analyze AI chat functionality"""
        logger.info("🔍 Analyzing AI chat functionality...")
        
        try:
            # Look for AI chat elements
            chat_selectors = [
                '.ai-assistant-panel',
                '.chat-input',
                '.chat-input textarea',
                'textarea[placeholder*="Ask"]',
                'textarea[placeholder*="chat"]',
                'textarea[placeholder*="message"]'
            ]
            
            chat_found = False
            for selector in chat_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(f"✅ AI chat element found: {selector}")
                        chat_found = True
                        
                        # Try to interact with it
                        try:
                            await element.fill("Test message")
                            await element.press('Enter')
                            logger.info("✅ AI chat interaction successful")
                        except Exception as e:
                            logger.warning(f"⚠️ AI chat interaction failed: {e}")
                            self.issues.append(f"AI chat interaction failed: {e}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {e}")
            
            if not chat_found:
                logger.error("❌ No AI chat elements found")
                self.issues.append("AI chat elements not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ AI chat analysis failed: {e}")
            self.issues.append(f"AI chat analysis failed: {e}")
            return False
    
    async def analyze_trading_logic(self, page):
        """Analyze trading logic and signal generation"""
        logger.info("🔍 Analyzing trading logic...")
        
        try:
            # Check for trading signals
            signal_elements = [
                '.trading-signals',
                '.signals',
                '.active-trades',
                '.trading-performance'
            ]
            
            signals_found = False
            for selector in signal_elements:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        logger.info(f"✅ Trading signals found: {text[:100]}...")
                        signals_found = True
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {e}")
            
            if not signals_found:
                logger.warning("❌ No trading signals found")
                self.issues.append("Trading signals not displayed")
            
            # Check for market data
            market_data_found = False
            market_selectors = [
                '.market-data',
                '.live-market-data',
                '.price-data',
                '[class*="market"]'
            ]
            
            for selector in market_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if any(pair in text for pair in ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD']):
                            logger.info(f"✅ Market data found: {text[:100]}...")
                            market_data_found = True
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {e}")
            
            if not market_data_found:
                logger.warning("❌ No market data found")
                self.issues.append("Market data not displayed")
            
            return signals_found and market_data_found
            
        except Exception as e:
            logger.error(f"❌ Trading logic analysis failed: {e}")
            self.issues.append(f"Trading logic analysis failed: {e}")
            return False
    
    async def run_comprehensive_analysis(self):
        """Run comprehensive dashboard analysis"""
        logger.info("🚀 Starting Comprehensive Dashboard Analysis")
        logger.info("=" * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Run all analyses
                await self.analyze_dashboard_loading(page)
                await self.analyze_websocket_connection(page)
                await self.analyze_ai_chat_functionality(page)
                await self.analyze_trading_logic(page)
                
            finally:
                await browser.close()
            
            # Print results
            self.print_analysis_results()
    
    def print_analysis_results(self):
        """Print detailed analysis results"""
        logger.info("=" * 60)
        logger.info("📊 COMPREHENSIVE DASHBOARD ANALYSIS RESULTS")
        logger.info("=" * 60)
        
        if self.issues:
            logger.info(f"❌ ISSUES FOUND ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                logger.info(f"  {i}. {issue}")
        else:
            logger.info("✅ NO ISSUES FOUND - Dashboard is fully functional!")
        
        # Generate solutions
        self.generate_solutions()
        
        if self.solutions:
            logger.info(f"\n🔧 RECOMMENDED SOLUTIONS ({len(self.solutions)}):")
            for i, solution in enumerate(self.solutions, 1):
                logger.info(f"  {i}. {solution}")
        
        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'issues': self.issues,
            'solutions': self.solutions,
            'total_issues': len(self.issues),
            'total_solutions': len(self.solutions)
        }
        
        results_file = f"dashboard_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n📄 Analysis results saved to: {results_file}")
    
    def generate_solutions(self):
        """Generate solutions for identified issues"""
        for issue in self.issues:
            if "Missing" in issue and "AI assistant" in issue:
                self.solutions.append("Fix AI assistant panel CSS selectors and ensure proper initialization")
            elif "Missing" in issue and "chat" in issue:
                self.solutions.append("Add AI chat input elements to dashboard template")
            elif "WebSocket" in issue:
                self.solutions.append("Fix WebSocket connection configuration and event handling")
            elif "JavaScript" in issue:
                self.solutions.append("Fix JavaScript errors in dashboard template")
            elif "Trading signals" in issue:
                self.solutions.append("Ensure trading signals are properly displayed in dashboard")
            elif "Market data" in issue:
                self.solutions.append("Fix market data display and real-time updates")
            else:
                self.solutions.append(f"Investigate and fix: {issue}")

async def main():
    """Main analysis function"""
    analyzer = DetailedDashboardAnalysis()
    await analyzer.run_comprehensive_analysis()

if __name__ == '__main__':
    asyncio.run(main())
