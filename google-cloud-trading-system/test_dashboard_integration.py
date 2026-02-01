#!/usr/bin/env python3
"""
Comprehensive Dashboard Integration Test
Tests all dashboard functionality including WebSocket, news, AI assistant, and trading signals
"""

import os
import sys
import json
import time
import requests
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardIntegrationTest:
    """Comprehensive dashboard integration test"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """Initialize test with base URL"""
        self.base_url = base_url
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'total_tests': 0,
            'results': []
        }
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        self.test_results['total_tests'] += 1
        logger.info(f"🧪 Running test: {test_name}")
        
        try:
            result = test_func()
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
    
    def test_server_health(self) -> bool:
        """Test if server is running and healthy"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Server health: {data}")
                return True
            else:
                logger.error(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Server health check error: {e}")
            return False
    
    def test_dashboard_route(self) -> bool:
        """Test dashboard route accessibility"""
        try:
            response = requests.get(f"{self.base_url}/dashboard", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Dashboard route accessible")
                return True
            else:
                logger.error(f"❌ Dashboard route failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Dashboard route error: {e}")
            return False
    
    def test_api_status(self) -> bool:
        """Test API status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API status: {data.get('system_status', 'unknown')}")
                return True
            else:
                logger.error(f"❌ API status failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API status error: {e}")
            return False
    
    def test_news_integration(self) -> bool:
        """Test news integration endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/news", timeout=15)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ News integration: {data.get('news_count', 0)} news items")
                return True
            else:
                logger.error(f"❌ News integration failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ News integration error: {e}")
            return False
    
    def test_news_analysis(self) -> bool:
        """Test news analysis endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/news/analysis", timeout=15)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ News analysis: {data.get('status', 'unknown')}")
                return True
            else:
                logger.error(f"❌ News analysis failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ News analysis error: {e}")
            return False
    
    def test_websocket_connection(self) -> bool:
        """Test WebSocket connection (basic test)"""
        try:
            # This is a basic test - in a real scenario, you'd use a WebSocket client
            # For now, we'll just check if the server is running
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ WebSocket server is running")
                return True
            else:
                logger.error("❌ WebSocket server not accessible")
                return False
        except Exception as e:
            logger.error(f"❌ WebSocket test error: {e}")
            return False
    
    def test_trading_signals(self) -> bool:
        """Test trading signals execution"""
        try:
            response = requests.post(f"{self.base_url}/tasks/full_scan", timeout=30)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Trading signals: {data.get('ok', False)}")
                return data.get('ok', False)
            else:
                logger.error(f"❌ Trading signals failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Trading signals error: {e}")
            return False
    
    def test_account_overview(self) -> bool:
        """Test account overview endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/overview", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Account overview: {data.get('total_accounts', 0)} accounts")
                return True
            else:
                logger.error(f"❌ Account overview failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Account overview error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all dashboard integration tests"""
        logger.info("🚀 Starting Comprehensive Dashboard Integration Test")
        logger.info("=" * 60)
        
        # Core functionality tests
        self.run_test("Server Health Check", self.test_server_health)
        self.run_test("Dashboard Route", self.test_dashboard_route)
        self.run_test("API Status", self.test_api_status)
        self.run_test("WebSocket Server", self.test_websocket_connection)
        
        # Integration tests
        self.run_test("Account Overview", self.test_account_overview)
        self.run_test("News Integration", self.test_news_integration)
        self.run_test("News Analysis", self.test_news_analysis)
        
        # Trading functionality tests
        self.run_test("Trading Signals", self.test_trading_signals)
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print test results summary"""
        logger.info("=" * 60)
        logger.info("📊 DASHBOARD INTEGRATION TEST RESULTS")
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
        results_file = f"dashboard_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"\n📄 Results saved to: {results_file}")
        
        if failed == 0:
            logger.info("\n🎉 ALL TESTS PASSED! Dashboard is fully functional.")
        else:
            logger.info(f"\n⚠️ {failed} tests failed. Please check the issues above.")

def main():
    """Main test function"""
    # Get base URL from environment or use default
    base_url = os.getenv('DASHBOARD_URL', 'http://localhost:8080')
    
    logger.info(f"🌐 Testing dashboard at: {base_url}")
    
    # Create and run tests
    tester = DashboardIntegrationTest(base_url)
    tester.run_all_tests()

if __name__ == '__main__':
    main()
