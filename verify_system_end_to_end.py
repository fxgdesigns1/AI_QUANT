#!/usr/bin/env python3
"""
END-TO-END SYSTEM VERIFICATION SCRIPT
Verifies all components from scanning to execution to tracking
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src'))

class SystemVerifier:
    """Verify all system components"""
    
    def __init__(self):
        self.base_url = os.getenv('DASHBOARD_URL', 'https://ai-quant-trading.uc.r.appspot.com')
        self.results = {
            'scanner': {'status': 'unknown', 'details': ''},
            'signal_generation': {'status': 'unknown', 'details': ''},
            'execution': {'status': 'unknown', 'details': ''},
            'telegram': {'status': 'unknown', 'details': ''},
            'dashboard': {'status': 'unknown', 'details': ''},
            'roadmap': {'status': 'unknown', 'details': ''},
            'tracking': {'status': 'unknown', 'details': ''},
            'ai_system': {'status': 'unknown', 'details': ''}
        }
    
    def verify_scanner(self) -> Dict[str, Any]:
        """Verify scanner is configured and accessible"""
        logger.info("🔍 Verifying scanner...")
        
        try:
            # Check cron endpoint
            url = f"{self.base_url}/cron/quality-scan"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'operational',
                    'details': f"Scanner endpoint accessible: {data.get('message', 'OK')}",
                    'endpoint': url,
                    'response': data
                }
            else:
                return {
                    'status': 'error',
                    'details': f"Scanner endpoint returned {response.status_code}",
                    'endpoint': url
                }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Scanner verification failed: {str(e)}"
            }
    
    def verify_signal_generation(self) -> Dict[str, Any]:
        """Verify signal generation is working"""
        logger.info("🔍 Verifying signal generation...")
        
        try:
            # Check if strategies are loaded
            from src.core.simple_timer_scanner import SimpleTimerScanner
            scanner = SimpleTimerScanner()
            
            strategy_count = len(scanner.strategies)
            account_count = len(scanner.accounts)
            
            return {
                'status': 'operational',
                'details': f"Strategies loaded: {strategy_count}, Accounts: {account_count}",
                'strategies': list(scanner.strategies.keys()),
                'accounts': list(scanner.accounts.keys())
            }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Signal generation verification failed: {str(e)}"
            }
    
    def verify_execution(self) -> Dict[str, Any]:
        """Verify execution system"""
        logger.info("🔍 Verifying execution system...")
        
        try:
            # Check OrderManager
            from src.core.order_manager import get_order_manager
            from src.core.yaml_manager import get_yaml_manager
            
            yaml_mgr = get_yaml_manager()
            accounts = yaml_mgr.get_all_accounts()
            
            active_accounts = [acc for acc in accounts if acc.get('active', False)]
            
            # Try to get order manager for first active account
            if active_accounts:
                account_id = active_accounts[0]['id']
                om = get_order_manager(account_id)
                
                return {
                    'status': 'operational',
                    'details': f"OrderManager initialized for {len(active_accounts)} accounts",
                    'active_accounts': len(active_accounts),
                    'test_account': account_id
                }
            else:
                return {
                    'status': 'warning',
                    'details': "No active accounts found"
                }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Execution verification failed: {str(e)}"
            }
    
    def verify_telegram(self) -> Dict[str, Any]:
        """Verify Telegram notifications"""
        logger.info("🔍 Verifying Telegram...")
        
        try:
            from src.core.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            
            if notifier.enabled:
                return {
                    'status': 'operational',
                    'details': f"Telegram enabled, chat ID: {notifier.chat_id}",
                    'rate_limit': f"{notifier.min_interval_seconds}s",
                    'daily_limit': notifier.max_daily_messages
                }
            else:
                return {
                    'status': 'disabled',
                    'details': "Telegram notifier disabled (missing token or chat ID)"
                }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Telegram verification failed: {str(e)}"
            }
    
    def verify_dashboard(self) -> Dict[str, Any]:
        """Verify dashboard is accessible"""
        logger.info("🔍 Verifying dashboard...")
        
        try:
            url = f"{self.base_url}/dashboard"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return {
                    'status': 'operational',
                    'details': f"Dashboard accessible at {url}",
                    'status_code': response.status_code
                }
            else:
                return {
                    'status': 'error',
                    'details': f"Dashboard returned {response.status_code}",
                    'url': url
                }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Dashboard verification failed: {str(e)}"
            }
    
    def verify_roadmap(self) -> Dict[str, Any]:
        """Verify weekly roadmap generation"""
        logger.info("🔍 Verifying roadmap...")
        
        try:
            from src.core.trump_dna_framework import get_trump_dna_planner
            
            planner = get_trump_dna_planner()
            plans = planner.generate_all_weekly_plans()
            
            return {
                'status': 'operational',
                'details': f"Generated {len(plans)} weekly roadmaps",
                'roadmaps': list(plans.keys())
            }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Roadmap verification failed: {str(e)}"
            }
    
    def verify_tracking(self) -> Dict[str, Any]:
        """Verify tracking system"""
        logger.info("🔍 Verifying tracking...")
        
        try:
            from src.core.performance_tracker import PerformanceTracker
            
            tracker = PerformanceTracker()
            
            # Check if database exists and is accessible
            snapshots = tracker.get_latest_snapshots()
            
            return {
                'status': 'operational',
                'details': f"Performance tracker initialized, {len(snapshots)} snapshots",
                'database': tracker.db_path
            }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"Tracking verification failed: {str(e)}"
            }
    
    def verify_ai_system(self) -> Dict[str, Any]:
        """Verify AI assistant system"""
        logger.info("🔍 Verifying AI system...")
        
        try:
            from src.dashboard.ai_assistant_api import GeminiAI
            
            ai = GeminiAI()
            
            if ai.enabled:
                # Test AI response
                test_response = ai.generate_response("Test message", {})
                
                return {
                    'status': 'operational',
                    'details': f"AI system enabled, Vertex AI: {ai.use_vertex_ai}",
                    'test_response': test_response[:100] if test_response else "No response"
                }
            else:
                return {
                    'status': 'disabled',
                    'details': "AI system disabled (missing API key)"
                }
        except Exception as e:
            return {
                'status': 'error',
                'details': f"AI system verification failed: {str(e)}"
            }
    
    def run_all_verifications(self) -> Dict[str, Any]:
        """Run all verifications"""
        logger.info("=" * 80)
        logger.info("🔍 STARTING END-TO-END SYSTEM VERIFICATION")
        logger.info("=" * 80)
        
        self.results['scanner'] = self.verify_scanner()
        self.results['signal_generation'] = self.verify_signal_generation()
        self.results['execution'] = self.verify_execution()
        self.results['telegram'] = self.verify_telegram()
        self.results['dashboard'] = self.verify_dashboard()
        self.results['roadmap'] = self.verify_roadmap()
        self.results['tracking'] = self.verify_tracking()
        self.results['ai_system'] = self.verify_ai_system()
        
        # Generate summary
        operational = sum(1 for r in self.results.values() if r['status'] == 'operational')
        errors = sum(1 for r in self.results.values() if r['status'] == 'error')
        warnings = sum(1 for r in self.results.values() if r['status'] == 'warning')
        disabled = sum(1 for r in self.results.values() if r['status'] == 'disabled')
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_components': len(self.results),
            'operational': operational,
            'errors': errors,
            'warnings': warnings,
            'disabled': disabled,
            'results': self.results
        }
        
        return summary
    
    def print_report(self, summary: Dict[str, Any]):
        """Print verification report"""
        print("\n" + "=" * 80)
        print("📊 SYSTEM VERIFICATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {summary['timestamp']}")
        print(f"\nComponents Checked: {summary['total_components']}")
        print(f"✅ Operational: {summary['operational']}")
        print(f"❌ Errors: {summary['errors']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"🔴 Disabled: {summary['disabled']}")
        print("\n" + "-" * 80)
        print("DETAILED RESULTS:")
        print("-" * 80)
        
        for component, result in summary['results'].items():
            status_emoji = {
                'operational': '✅',
                'error': '❌',
                'warning': '⚠️',
                'disabled': '🔴',
                'unknown': '❓'
            }
            emoji = status_emoji.get(result['status'], '❓')
            print(f"\n{emoji} {component.upper()}")
            print(f"   Status: {result['status']}")
            print(f"   Details: {result['details']}")
        
        print("\n" + "=" * 80)
        
        # Overall status
        if summary['errors'] == 0 and summary['operational'] >= 6:
            print("🎉 SYSTEM IS FULLY OPERATIONAL")
        elif summary['errors'] <= 2 and summary['operational'] >= 5:
            print("🟡 SYSTEM IS MOSTLY OPERATIONAL (minor issues)")
        else:
            print("🔴 SYSTEM HAS ISSUES - Review errors above")
        print("=" * 80 + "\n")

def main():
    """Main verification function"""
    verifier = SystemVerifier()
    summary = verifier.run_all_verifications()
    verifier.print_report(summary)
    
    # Save report to file
    report_file = f"system_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Full report saved to: {report_file}")

if __name__ == "__main__":
    main()

