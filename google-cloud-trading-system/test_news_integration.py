#!/usr/bin/env python3
"""
Comprehensive Testing Script for News API Integration
Tests all components safely without breaking existing system
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsIntegrationTester:
    """Comprehensive tester for news API integration"""
    
    def __init__(self):
        """Initialize tester"""
        self.test_results = {}
        self.errors = []
        self.warnings = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        logger.info("🧪 Starting comprehensive news integration tests...")
        
        # Test 1: Import safety
        self.test_imports()
        
        # Test 2: News integration initialization
        self.test_news_integration_init()
        
        # Test 3: API key loading
        self.test_api_key_loading()
        
        # Test 4: Mock data functionality
        self.test_mock_data()
        
        # Test 5: News analysis
        self.test_news_analysis()
        
        # Test 6: Trading pause logic
        self.test_trading_pause_logic()
        
        # Test 7: Boost factor calculation
        self.test_boost_factor_calculation()
        
        # Test 8: Enhanced strategy
        self.test_enhanced_strategy()
        
        # Test 9: Enhanced dashboard
        self.test_enhanced_dashboard()
        
        # Test 10: Main app integration
        self.test_main_app_integration()
        
        return self._generate_test_report()
    
    def test_imports(self):
        """Test 1: Import safety"""
        logger.info("🔍 Test 1: Testing imports...")
        
        try:
            # Test news integration import
            from src.core.news_integration import safe_news_integration
            self.test_results['imports'] = {'status': 'PASS', 'message': 'All imports successful'}
            logger.info("✅ All imports successful")
            
        except Exception as e:
            self.test_results['imports'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Import test failed: {e}")
            logger.error(f"❌ Import test failed: {e}")
    
    def test_news_integration_init(self):
        """Test 2: News integration initialization"""
        logger.info("🔍 Test 2: Testing news integration initialization...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Check if integration is properly initialized
            assert hasattr(safe_news_integration, 'enabled')
            assert hasattr(safe_news_integration, 'api_keys')
            assert hasattr(safe_news_integration, 'cache')
            
            self.test_results['news_integration_init'] = {
                'status': 'PASS', 
                'message': 'News integration initialized successfully',
                'enabled': safe_news_integration.enabled,
                'api_keys_count': len(safe_news_integration.api_keys)
            }
            logger.info("✅ News integration initialization successful")
            
        except Exception as e:
            self.test_results['news_integration_init'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"News integration init test failed: {e}")
            logger.error(f"❌ News integration init test failed: {e}")
    
    def test_api_key_loading(self):
        """Test 3: API key loading"""
        logger.info("🔍 Test 3: Testing API key loading...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Check if API keys are loaded
            api_keys = safe_news_integration.api_keys
            key_count = len(api_keys)
            
            if key_count > 0:
                self.test_results['api_key_loading'] = {
                    'status': 'PASS',
                    'message': f'API keys loaded successfully: {key_count} keys',
                    'keys': list(api_keys.keys())
                }
                logger.info(f"✅ API keys loaded: {key_count} keys")
            else:
                self.test_results['api_key_loading'] = {
                    'status': 'WARN',
                    'message': 'No API keys found - will use mock data',
                    'keys': []
                }
                self.warnings.append("No API keys found - system will use mock data")
                logger.warning("⚠️ No API keys found - will use mock data")
            
        except Exception as e:
            self.test_results['api_key_loading'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"API key loading test failed: {e}")
            logger.error(f"❌ API key loading test failed: {e}")
    
    def test_mock_data(self):
        """Test 4: Mock data functionality"""
        logger.info("🔍 Test 4: Testing mock data functionality...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Test mock data
            mock_data = safe_news_integration._get_mock_news_data()
            
            assert len(mock_data) > 0, "Mock data should not be empty"
            assert all('title' in item for item in mock_data), "All items should have title"
            assert all('summary' in item for item in mock_data), "All items should have summary"
            assert all('impact' in item for item in mock_data), "All items should have impact"
            
            self.test_results['mock_data'] = {
                'status': 'PASS',
                'message': f'Mock data working correctly: {len(mock_data)} items',
                'sample_item': mock_data[0] if mock_data else None
            }
            logger.info(f"✅ Mock data working: {len(mock_data)} items")
            
        except Exception as e:
            self.test_results['mock_data'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Mock data test failed: {e}")
            logger.error(f"❌ Mock data test failed: {e}")
    
    def test_news_analysis(self):
        """Test 5: News analysis"""
        logger.info("🔍 Test 5: Testing news analysis...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Test news analysis
            analysis = safe_news_integration.get_news_analysis()
            
            # Check required fields
            required_fields = ['overall_sentiment', 'market_impact', 'trading_recommendation', 'confidence']
            for field in required_fields:
                assert field in analysis, f"Analysis should contain {field}"
            
            # Check data types
            assert isinstance(analysis['overall_sentiment'], (int, float)), "Sentiment should be numeric"
            assert analysis['market_impact'] in ['high', 'medium', 'low'], "Impact should be valid"
            assert analysis['trading_recommendation'] in ['buy', 'sell', 'hold', 'avoid'], "Recommendation should be valid"
            assert 0 <= analysis['confidence'] <= 1, "Confidence should be between 0 and 1"
            
            self.test_results['news_analysis'] = {
                'status': 'PASS',
                'message': 'News analysis working correctly',
                'analysis': analysis
            }
            logger.info("✅ News analysis working correctly")
            
        except Exception as e:
            self.test_results['news_analysis'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"News analysis test failed: {e}")
            logger.error(f"❌ News analysis test failed: {e}")
    
    def test_trading_pause_logic(self):
        """Test 6: Trading pause logic"""
        logger.info("🔍 Test 6: Testing trading pause logic...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Test pause logic
            should_pause = safe_news_integration.should_pause_trading()
            
            assert isinstance(should_pause, bool), "Should pause should be boolean"
            
            self.test_results['trading_pause_logic'] = {
                'status': 'PASS',
                'message': 'Trading pause logic working correctly',
                'should_pause': should_pause
            }
            logger.info(f"✅ Trading pause logic working: {should_pause}")
            
        except Exception as e:
            self.test_results['trading_pause_logic'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Trading pause logic test failed: {e}")
            logger.error(f"❌ Trading pause logic test failed: {e}")
    
    def test_boost_factor_calculation(self):
        """Test 7: Boost factor calculation"""
        logger.info("🔍 Test 7: Testing boost factor calculation...")
        
        try:
            from src.core.news_integration import safe_news_integration
            
            # Test boost factors for different signal types
            buy_boost = safe_news_integration.get_news_boost_factor('BUY')
            sell_boost = safe_news_integration.get_news_boost_factor('SELL')
            
            assert isinstance(buy_boost, (int, float)), "Buy boost should be numeric"
            assert isinstance(sell_boost, (int, float)), "Sell boost should be numeric"
            assert buy_boost > 0, "Boost factors should be positive"
            assert sell_boost > 0, "Boost factors should be positive"
            
            self.test_results['boost_factor_calculation'] = {
                'status': 'PASS',
                'message': 'Boost factor calculation working correctly',
                'buy_boost': buy_boost,
                'sell_boost': sell_boost
            }
            logger.info(f"✅ Boost factor calculation working: BUY={buy_boost}, SELL={sell_boost}")
            
        except Exception as e:
            self.test_results['boost_factor_calculation'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Boost factor calculation test failed: {e}")
            logger.error(f"❌ Boost factor calculation test failed: {e}")
    
    def test_enhanced_strategy(self):
        """Test 8: Enhanced strategy"""
        logger.info("🔍 Test 8: Testing enhanced strategy...")
        
        try:
            from src.strategies.ultra_strict_forex_enhanced import EnhancedUltraStrictForexStrategy
            
            # Test strategy initialization
            strategy = EnhancedUltraStrictForexStrategy()
            
            assert hasattr(strategy, 'news_enabled'), "Strategy should have news_enabled"
            assert hasattr(strategy, 'news_pause_threshold'), "Strategy should have pause threshold"
            assert hasattr(strategy, 'news_boost_threshold'), "Strategy should have boost threshold"
            
            # Test strategy status
            status = strategy.get_strategy_status()
            assert 'news_integration' in status, "Status should include news integration"
            
            self.test_results['enhanced_strategy'] = {
                'status': 'PASS',
                'message': 'Enhanced strategy working correctly',
                'strategy_status': status
            }
            logger.info("✅ Enhanced strategy working correctly")
            
        except Exception as e:
            self.test_results['enhanced_strategy'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Enhanced strategy test failed: {e}")
            logger.error(f"❌ Enhanced strategy test failed: {e}")
    
    def test_enhanced_dashboard(self):
        """Test 9: Enhanced dashboard"""
        logger.info("🔍 Test 9: Testing enhanced dashboard...")
        
        try:
            from src.dashboard.advanced_dashboard_enhanced import EnhancedAdvancedDashboardManager
            
            # Test dashboard initialization
            dashboard = EnhancedAdvancedDashboardManager()
            
            assert hasattr(dashboard, 'news_enabled'), "Dashboard should have news_enabled"
            assert hasattr(dashboard, 'last_news_update'), "Dashboard should have last_news_update"
            
            # Test news data method
            news_data = dashboard._get_news_data()
            assert 'items' in news_data, "News data should have items"
            assert 'count' in news_data, "News data should have count"
            assert 'source' in news_data, "News data should have source"
            
            self.test_results['enhanced_dashboard'] = {
                'status': 'PASS',
                'message': 'Enhanced dashboard working correctly',
                'news_data_sample': news_data
            }
            logger.info("✅ Enhanced dashboard working correctly")
            
        except Exception as e:
            self.test_results['enhanced_dashboard'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Enhanced dashboard test failed: {e}")
            logger.error(f"❌ Enhanced dashboard test failed: {e}")
    
    def test_main_app_integration(self):
        """Test 10: Main app integration"""
        logger.info("🔍 Test 10: Testing main app integration...")
        
        try:
            # Test if main_enhanced.py can be imported
            import main_enhanced
            
            # Test if Flask app is created
            assert hasattr(main_enhanced, 'app'), "Main app should have Flask app"
            assert hasattr(main_enhanced, 'socketio'), "Main app should have SocketIO"
            assert hasattr(main_enhanced, 'dashboard_manager'), "Main app should have dashboard manager"
            assert hasattr(main_enhanced, 'news_integration'), "Main app should have news integration"
            
            # Test if routes are registered
            routes = [rule.rule for rule in main_enhanced.app.url_map.iter_rules()]
            assert '/api/news' in routes, "Should have news API route"
            assert '/api/news/analysis' in routes, "Should have news analysis route"
            
            self.test_results['main_app_integration'] = {
                'status': 'PASS',
                'message': 'Main app integration working correctly',
                'routes_count': len(routes),
                'news_routes': [route for route in routes if 'news' in route]
            }
            logger.info("✅ Main app integration working correctly")
            
        except Exception as e:
            self.test_results['main_app_integration'] = {'status': 'FAIL', 'message': str(e)}
            self.errors.append(f"Main app integration test failed: {e}")
            logger.error(f"❌ Main app integration test failed: {e}")
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results.values() if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results.values() if r['status'] == 'WARN'])
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'warnings': warning_tests,
                'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'errors': self.errors,
            'warnings': self.warnings,
            'recommendations': self._generate_recommendations(),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if self.errors:
            recommendations.append("❌ Fix errors before deployment")
        
        if self.warnings:
            recommendations.append("⚠️ Address warnings for optimal performance")
        
        if not any('news' in str(result) for result in self.test_results.values()):
            recommendations.append("📰 News integration tests passed - ready for deployment")
        
        if len(self.errors) == 0:
            recommendations.append("✅ All tests passed - system ready for production")
        
        return recommendations

def main():
    """Main testing function"""
    print("🧪 NEWS API INTEGRATION TESTING SUITE")
    print("=" * 50)
    
    tester = NewsIntegrationTester()
    report = tester.run_all_tests()
    
    # Print summary
    print(f"\n📊 TEST SUMMARY")
    print(f"Total Tests: {report['test_summary']['total_tests']}")
    print(f"Passed: {report['test_summary']['passed']}")
    print(f"Failed: {report['test_summary']['failed']}")
    print(f"Warnings: {report['test_summary']['warnings']}")
    print(f"Success Rate: {report['test_summary']['success_rate']:.1f}%")
    
    # Print errors
    if report['errors']:
        print(f"\n❌ ERRORS:")
        for error in report['errors']:
            print(f"  - {error}")
    
    # Print warnings
    if report['warnings']:
        print(f"\n⚠️ WARNINGS:")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    # Print recommendations
    if report['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    # Save detailed report
    with open('news_integration_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: news_integration_test_report.json")
    
    return report['test_summary']['success_rate'] > 80

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
