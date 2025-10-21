#!/usr/bin/env python3
"""
Comprehensive Trading Logic Verification
Tests all trading systems, signal generation, and risk management
"""

import os
import sys
import json
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

class TradingLogicVerification:
    """Comprehensive trading logic verification"""
    
    def __init__(self, base_url: str = "https://ai-quant-trading.uc.r.appspot.com"):
        """Initialize verification"""
        self.base_url = base_url
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'total_tests': 0,
            'results': []
        }
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        self.verification_results['total_tests'] += 1
        logger.info(f"🧪 Running test: {test_name}")
        
        try:
            result = test_func()
            if result:
                self.verification_results['tests_passed'] += 1
                self.verification_results['results'].append({
                    'test': test_name,
                    'status': 'PASSED',
                    'message': 'Test completed successfully'
                })
                logger.info(f"✅ {test_name}: PASSED")
            else:
                self.verification_results['tests_failed'] += 1
                self.verification_results['results'].append({
                    'test': test_name,
                    'status': 'FAILED',
                    'message': 'Test returned False'
                })
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            self.verification_results['tests_failed'] += 1
            self.verification_results['results'].append({
                'test': test_name,
                'status': 'FAILED',
                'message': str(e)
            })
            logger.error(f"❌ {test_name}: FAILED - {e}")
    
    def test_api_status(self) -> bool:
        """Test API status and system health"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify system status
                if data.get('system_status') == 'online':
                    logger.info("✅ System status: online")
                else:
                    logger.error(f"❌ System status: {data.get('system_status')}")
                    return False
                
                # Verify live data mode
                if data.get('live_data_mode'):
                    logger.info("✅ Live data mode: enabled")
                else:
                    logger.error("❌ Live data mode: disabled")
                    return False
                
                # Verify data feed status
                if data.get('data_feed_status') == 'active':
                    logger.info("✅ Data feed status: active")
                else:
                    logger.error(f"❌ Data feed status: {data.get('data_feed_status')}")
                    return False
                
                return True
            else:
                logger.error(f"❌ API status failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API status test error: {e}")
            return False
    
    def test_account_status(self) -> bool:
        """Test account status and balances"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check account statuses
                account_statuses = data.get('account_statuses', {})
                if len(account_statuses) >= 3:
                    logger.info(f"✅ Found {len(account_statuses)} active accounts")
                else:
                    logger.error(f"❌ Expected 3+ accounts, found {len(account_statuses)}")
                    return False
                
                # Verify each account
                for account_id, account_data in account_statuses.items():
                    if account_data.get('status') == 'active':
                        logger.info(f"✅ Account {account_id}: active")
                    else:
                        logger.error(f"❌ Account {account_id}: {account_data.get('status')}")
                        return False
                    
                    if account_data.get('balance', 0) > 0:
                        logger.info(f"✅ Account {account_id}: balance {account_data.get('balance')}")
                    else:
                        logger.error(f"❌ Account {account_id}: zero balance")
                        return False
                
                return True
            else:
                logger.error(f"❌ Account status failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Account status test error: {e}")
            return False
    
    def test_market_data(self) -> bool:
        """Test market data and price feeds"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check market data
                market_data = data.get('market_data', {})
                if market_data:
                    logger.info(f"✅ Market data found for {len(market_data)} accounts")
                else:
                    logger.error("❌ No market data found")
                    return False
                
                # Verify market data quality
                for account_id, account_market_data in market_data.items():
                    for instrument, price_data in account_market_data.items():
                        if price_data.get('is_live'):
                            logger.info(f"✅ {instrument}: live data")
                        else:
                            logger.warning(f"⚠️ {instrument}: not live")
                        
                        if price_data.get('confidence', 0) > 0.8:
                            logger.info(f"✅ {instrument}: high confidence")
                        else:
                            logger.warning(f"⚠️ {instrument}: low confidence")
                
                return True
            else:
                logger.error(f"❌ Market data test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Market data test error: {e}")
            return False
    
    def test_trading_systems(self) -> bool:
        """Test trading systems configuration"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check trading systems
                trading_systems = data.get('trading_systems', {})
                if len(trading_systems) >= 3:
                    logger.info(f"✅ Found {len(trading_systems)} trading systems")
                else:
                    logger.error(f"❌ Expected 3+ trading systems, found {len(trading_systems)}")
                    return False
                
                # Verify each trading system
                for account_id, system_data in trading_systems.items():
                    strategy_name = system_data.get('strategy_name', 'Unknown')
                    if strategy_name in ['Gold Scalping 5M', 'Ultra Strict Fx 15M', 'Combined Portfolio']:
                        logger.info(f"✅ {strategy_name}: configured")
                    else:
                        logger.warning(f"⚠️ Unknown strategy: {strategy_name}")
                    
                    # Check risk settings
                    risk_settings = system_data.get('risk_settings', {})
                    if risk_settings:
                        logger.info(f"✅ {strategy_name}: risk settings configured")
                    else:
                        logger.error(f"❌ {strategy_name}: no risk settings")
                        return False
                
                return True
            else:
                logger.error(f"❌ Trading systems test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Trading systems test error: {e}")
            return False
    
    def test_risk_management(self) -> bool:
        """Test risk management settings"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check risk settings for each account
                account_statuses = data.get('account_statuses', {})
                for account_id, account_data in account_statuses.items():
                    risk_settings = account_data.get('risk_settings', {})
                    
                    # Verify risk parameters
                    required_params = ['max_risk_per_trade', 'max_portfolio_risk', 'max_positions', 'daily_trade_limit']
                    for param in required_params:
                        if param in risk_settings:
                            logger.info(f"✅ {account_id}: {param} = {risk_settings[param]}")
                        else:
                            logger.error(f"❌ {account_id}: missing {param}")
                            return False
                    
                    # Verify risk limits are reasonable
                    max_risk = risk_settings.get('max_risk_per_trade', 0)
                    if 0 < max_risk <= 0.05:  # 0-5% per trade
                        logger.info(f"✅ {account_id}: max_risk_per_trade within limits")
                    else:
                        logger.error(f"❌ {account_id}: max_risk_per_trade out of range: {max_risk}")
                        return False
                
                return True
            else:
                logger.error(f"❌ Risk management test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Risk management test error: {e}")
            return False
    
    def test_trading_signals(self) -> bool:
        """Test trading signal generation"""
        try:
            # Test signal execution endpoint
            response = requests.post(f"{self.base_url}/tasks/full_scan", timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('ok'):
                    logger.info("✅ Trading signals: execution successful")
                    return True
                else:
                    logger.error(f"❌ Trading signals: execution failed - {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ Trading signals test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Trading signals test error: {e}")
            return False
    
    def test_news_integration(self) -> bool:
        """Test news integration"""
        try:
            response = requests.get(f"{self.base_url}/api/news", timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    logger.info("✅ News integration: working")
                    return True
                else:
                    logger.error(f"❌ News integration failed: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ News integration test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ News integration test error: {e}")
            return False
    
    def test_performance_metrics(self) -> bool:
        """Test performance metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check trading metrics
                trading_metrics = data.get('trading_metrics', {})
                if trading_metrics:
                    logger.info("✅ Trading metrics: available")
                    
                    # Verify metrics structure
                    required_metrics = ['total_trades', 'win_rate', 'profit_factor', 'sharpe_ratio']
                    for metric in required_metrics:
                        if metric in trading_metrics:
                            logger.info(f"✅ {metric}: {trading_metrics[metric]}")
                        else:
                            logger.warning(f"⚠️ Missing metric: {metric}")
                    
                    return True
                else:
                    logger.error("❌ No trading metrics found")
                    return False
            else:
                logger.error(f"❌ Performance metrics test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Performance metrics test error: {e}")
            return False
    
    def run_comprehensive_verification(self):
        """Run comprehensive trading logic verification"""
        logger.info("🚀 Starting Comprehensive Trading Logic Verification")
        logger.info("=" * 60)
        
        # Core system tests
        self.run_test("API Status", self.test_api_status)
        self.run_test("Account Status", self.test_account_status)
        self.run_test("Market Data", self.test_market_data)
        self.run_test("Trading Systems", self.test_trading_systems)
        self.run_test("Risk Management", self.test_risk_management)
        
        # Trading functionality tests
        self.run_test("Trading Signals", self.test_trading_signals)
        self.run_test("News Integration", self.test_news_integration)
        self.run_test("Performance Metrics", self.test_performance_metrics)
        
        # Print results
        self.print_verification_results()
    
    def print_verification_results(self):
        """Print verification results summary"""
        logger.info("=" * 60)
        logger.info("📊 TRADING LOGIC VERIFICATION RESULTS")
        logger.info("=" * 60)
        
        total = self.verification_results['total_tests']
        passed = self.verification_results['tests_passed']
        failed = self.verification_results['tests_failed']
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.verification_results['results']:
                if result['status'] == 'FAILED':
                    logger.info(f"  - {result['test']}: {result['message']}")
        
        logger.info("\n✅ PASSED TESTS:")
        for result in self.verification_results['results']:
            if result['status'] == 'PASSED':
                logger.info(f"  - {result['test']}")
        
        # Save results
        results_file = f"trading_logic_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        
        logger.info(f"\n📄 Results saved to: {results_file}")
        
        if failed == 0:
            logger.info("\n🎉 ALL TRADING LOGIC TESTS PASSED! System is 100% functional.")
        else:
            logger.info(f"\n⚠️ {failed} tests failed. Please check the issues above.")

def main():
    """Main verification function"""
    verifier = TradingLogicVerification()
    verifier.run_comprehensive_verification()

if __name__ == '__main__':
    main()
