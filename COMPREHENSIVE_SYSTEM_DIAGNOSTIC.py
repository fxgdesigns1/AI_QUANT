#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM DIAGNOSTIC
Identifies ALL reasons why trades aren't executing and system startup issues
"""
import os
import sys
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveDiagnostic:
    def __init__(self):
        self.issues_found = []
        self.warnings = []
        self.recommendations = []
        
    def check_api_credentials(self):
        """Check if API credentials are properly configured"""
        print("\n" + "="*80)
        print("CHECK 1: API CREDENTIALS")
        print("="*80)
        
        issues = []
        
        # Check environment variables
        api_key = os.getenv('OANDA_API_KEY')
        if not api_key:
            # Check hardcoded in files
            if Path('/workspace/ai_trading_system.py').exists():
                with open('/workspace/ai_trading_system.py', 'r') as f:
                    content = f.read()
                    if 'OANDA_API_KEY' in content:
                        print("✓ API key found in code (hardcoded)")
                        api_key = "FOUND_IN_CODE"
                    else:
                        issues.append("❌ No API key found in code or environment")
                        self.issues_found.append("Missing API credentials")
        else:
            print(f"✓ API key found in environment: {api_key[:10]}...{api_key[-4:]}")
        
        # Check account ID
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        if not account_id:
            if Path('/workspace/ai_trading_system.py').exists():
                with open('/workspace/ai_trading_system.py', 'r') as f:
                    content = f.read()
                    if 'OANDA_ACCOUNT_ID' in content:
                        print("✓ Account ID found in code")
                        account_id = "FOUND_IN_CODE"
                    else:
                        issues.append("❌ No account ID found")
                        self.issues_found.append("Missing account ID")
        else:
            print(f"✓ Account ID found: {account_id}")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ Credentials check passed")
        
        return api_key and account_id
    
    def check_system_running(self):
        """Check if any trading system is actually running"""
        print("\n" + "="*80)
        print("CHECK 2: SYSTEM RUNNING STATUS")
        print("="*80)
        
        import subprocess
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            running_processes = []
            
            if 'ai_trading_system.py' in result.stdout:
                running_processes.append('ai_trading_system.py')
            if 'automated_trading_system.py' in result.stdout:
                running_processes.append('automated_trading_system.py')
            if 'comprehensive_trading_system.py' in result.stdout:
                running_processes.append('comprehensive_trading_system.py')
            if 'main.py' in result.stdout:
                running_processes.append('main.py')
            
            if running_processes:
                print(f"✓ Found running processes: {', '.join(running_processes)}")
                return True
            else:
                print("❌ NO TRADING SYSTEM IS RUNNING")
                self.issues_found.append("System not running - no process executing trades")
                print("\n💡 This is likely the PRIMARY issue - system needs to be started")
                return False
        except Exception as e:
            print(f"⚠ Could not check running processes: {e}")
            return None
    
    def check_trading_enabled_flag(self):
        """Check if trading_enabled flag is set"""
        print("\n" + "="*80)
        print("CHECK 3: TRADING ENABLED FLAG")
        print("="*80)
        
        if Path('/workspace/ai_trading_system.py').exists():
            with open('/workspace/ai_trading_system.py', 'r') as f:
                content = f.read()
                if 'self.trading_enabled = True' in content:
                    print("✓ Trading enabled flag defaults to True")
                elif 'self.trading_enabled = False' in content:
                    print("❌ Trading enabled flag defaults to False")
                    self.issues_found.append("Trading disabled by default")
                else:
                    print("⚠ Trading enabled flag not clearly set")
        
        # Check if there's a way to enable it
        if 'def run_trading_cycle' in content:
            if 'if not self.trading_enabled:' in content:
                print("⚠ Trading cycle checks trading_enabled flag")
                print("  → System may be disabled even if running")
        
        return True
    
    def check_signal_generation(self):
        """Check if signals are being generated"""
        print("\n" + "="*80)
        print("CHECK 4: SIGNAL GENERATION")
        print("="*80)
        
        issues = []
        
        # Check if analyze_market method exists
        if Path('/workspace/ai_trading_system.py').exists():
            with open('/workspace/ai_trading_system.py', 'r') as f:
                content = f.read()
                
                if 'def analyze_market' in content:
                    print("✓ analyze_market method exists")
                    
                    # Check for restrictive conditions
                    restrictive_patterns = [
                        ('spread >', 'Spread filtering may be too restrictive'),
                        ('max_spread', 'Maximum spread limits may block trades'),
                        ('in_london_session', 'Session checks may block trades'),
                        ('confirm_above >= 2', 'Confirmation requirements may be too strict'),
                        ('confirm_below >= 2', 'Confirmation requirements may be too strict'),
                        ('news_halt_until', 'News halts may be blocking trades'),
                        ('is_news_halt_active', 'News halt checks may block trades'),
                        ('is_throttle_active', 'Throttle checks may block trades'),
                    ]
                    
                    for pattern, description in restrictive_patterns:
                        if pattern in content:
                            print(f"⚠ Found potentially restrictive condition: {description}")
                            issues.append(description)
                    
                    # Check signal generation logic
                    if 'signals.append' in content:
                        print("✓ Signal generation code exists")
                    else:
                        print("❌ No signal generation code found")
                        self.issues_found.append("Signal generation code missing")
                else:
                    print("❌ analyze_market method not found")
                    self.issues_found.append("Missing analyze_market method")
        
        if issues:
            print("\n⚠ Potential blocking conditions found:")
            for issue in issues:
                print(f"  • {issue}")
        
        return len(issues) == 0
    
    def check_execution_flow(self):
        """Check if execution flow is complete"""
        print("\n" + "="*80)
        print("CHECK 5: EXECUTION FLOW")
        print("="*80)
        
        issues = []
        
        if Path('/workspace/ai_trading_system.py').exists():
            with open('/workspace/ai_trading_system.py', 'r') as f:
                content = f.read()
                
                # Check main loop
                if 'def main' in content:
                    print("✓ Main function exists")
                    
                    # Check if run_trading_cycle is called
                    if 'run_trading_cycle' in content:
                        print("✓ run_trading_cycle method exists")
                        
                        # Check if it's called in main loop
                        if 'system.run_trading_cycle()' in content:
                            print("✓ run_trading_cycle is called in main loop")
                        else:
                            issues.append("run_trading_cycle not called in main")
                    
                    # Check if execute_trade is called
                    if 'def execute_trade' in content:
                        print("✓ execute_trade method exists")
                        
                        # Check if it's called from run_trading_cycle
                        lines = content.split('\n')
                        in_run_cycle = False
                        for i, line in enumerate(lines):
                            if 'def run_trading_cycle' in line:
                                in_run_cycle = True
                            elif in_run_cycle and line.strip().startswith('def '):
                                in_run_cycle = False
                            elif in_run_cycle and 'execute_trade' in line:
                                print("✓ execute_trade is called from run_trading_cycle")
                                break
                        else:
                            if in_run_cycle:
                                print("⚠ execute_trade may not be called from run_trading_cycle")
                    else:
                        issues.append("execute_trade method missing")
        
        if issues:
            for issue in issues:
                print(f"❌ {issue}")
                self.issues_found.append(issue)
        else:
            print("✅ Execution flow appears complete")
        
        return len(issues) == 0
    
    def check_blocking_conditions(self):
        """Check for conditions that block trade execution"""
        print("\n" + "="*80)
        print("CHECK 6: BLOCKING CONDITIONS")
        print("="*80)
        
        blocking_conditions = []
        
        if Path('/workspace/ai_trading_system.py').exists():
            with open('/workspace/ai_trading_system.py', 'r') as f:
                content = f.read()
                
                # Check for guards that block execution
                checks = [
                    ('if not self.trading_enabled:', 'Trading disabled flag'),
                    ('if self.daily_trade_count >=', 'Daily trade limit reached'),
                    ('if len(self.active_trades) >=', 'Max concurrent trades reached'),
                    ('if self.is_news_halt_active():', 'News halt active'),
                    ('if self.is_throttle_active():', 'Sentiment throttle active'),
                    ('if total_live >= self.max_concurrent_trades:', 'Global cap reached'),
                    ('if sym_live >= current_symbol_cap:', 'Per-symbol cap reached'),
                    ('if units == 0:', 'Position size too small'),
                    ('if stop_distance <= 0:', 'Invalid stop distance'),
                ]
                
                for pattern, description in checks:
                    if pattern in content:
                        blocking_conditions.append(description)
                        print(f"⚠ Found blocking condition: {description}")
        
        if blocking_conditions:
            print(f"\n⚠ Found {len(blocking_conditions)} potential blocking conditions")
            print("  → These may prevent trades from executing")
            self.warnings.append(f"{len(blocking_conditions)} blocking conditions found")
        else:
            print("✓ No obvious blocking conditions found")
        
        return blocking_conditions
    
    def check_strategy_switching(self):
        """Check strategy switching mechanism"""
        print("\n" + "="*80)
        print("CHECK 7: STRATEGY SWITCHING")
        print("="*80)
        
        issues = []
        
        # Check for accounts.yaml
        yaml_paths = [
            '/workspace/google-cloud-trading-system/accounts.yaml',
            '/workspace/accounts.yaml'
        ]
        
        yaml_found = False
        for path in yaml_paths:
            if Path(path).exists():
                print(f"✓ Found accounts.yaml at {path}")
                yaml_found = True
                
                # Check if it has strategy configurations
                try:
                    import yaml
                    with open(path, 'r') as f:
                        config = yaml.safe_load(f)
                        accounts = config.get('accounts', [])
                        print(f"✓ Found {len(accounts)} accounts in config")
                        
                        for acc in accounts:
                            strategy = acc.get('strategy', 'N/A')
                            active = acc.get('active', False)
                            status = "ACTIVE" if active else "INACTIVE"
                            print(f"  • Account {acc.get('id', 'N/A')[-3:]}: {strategy} ({status})")
                except Exception as e:
                    print(f"⚠ Error reading accounts.yaml: {e}")
                break
        
        if not yaml_found:
            print("❌ accounts.yaml not found")
            issues.append("Strategy configuration file missing")
            self.issues_found.append("Missing accounts.yaml")
        
        # Check for graceful restart mechanism
        restart_paths = [
            '/workspace/google-cloud-trading-system/src/core/graceful_restart.py',
        ]
        
        for path in restart_paths:
            if Path(path).exists():
                print(f"✓ Found graceful restart mechanism")
                break
        else:
            print("⚠ Graceful restart mechanism not found")
            issues.append("Strategy switching may require manual restart")
        
        if issues:
            for issue in issues:
                print(f"❌ {issue}")
        else:
            print("✅ Strategy switching appears configured")
        
        return len(issues) == 0
    
    def check_startup_issues(self):
        """Check for startup-related issues"""
        print("\n" + "="*80)
        print("CHECK 8: STARTUP ISSUES")
        print("="*80)
        
        issues = []
        
        # Check for dependencies
        if Path('/workspace/ai_trading_system.py').exists():
            with open('/workspace/ai_trading_system.py', 'r') as f:
                content = f.read()
                imports = []
                for line in content.split('\n'):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        imports.append(line.strip())
                
                print(f"✓ Found {len(imports)} imports")
                
                # Check for potentially slow imports
                slow_imports = ['news_manager', 'adaptive_store']
                for imp in slow_imports:
                    if imp in content:
                        print(f"⚠ Found potentially slow import: {imp}")
        
        # Check for initialization delays
        if 'time.sleep' in content:
            sleep_count = content.count('time.sleep')
            print(f"⚠ Found {sleep_count} time.sleep calls (may cause delays)")
        
        # Check for service configuration
        service_paths = [
            '/workspace/ai_trading.service',
            '/workspace/automated_trading.service'
        ]
        
        for path in service_paths:
            if Path(path).exists():
                print(f"✓ Found service file: {path}")
                with open(path, 'r') as f:
                    service_content = f.read()
                    if 'RestartSec=10' in service_content:
                        print("  • Restart delay: 10 seconds")
                    if 'WorkingDirectory' in service_content:
                        print(f"  • Working directory configured")
        
        if issues:
            for issue in issues:
                print(f"❌ {issue}")
        else:
            print("✅ Startup configuration appears reasonable")
        
        return len(issues) == 0
    
    def test_live_signal_generation(self):
        """Test if signals can be generated right now"""
        print("\n" + "="*80)
        print("CHECK 9: LIVE SIGNAL GENERATION TEST")
        print("="*80)
        
        try:
            # Try to import and test
            sys.path.insert(0, '/workspace')
            
            # Read API key from file
            api_key = None
            account_id = None
            
            if Path('/workspace/ai_trading_system.py').exists():
                with open('/workspace/ai_trading_system.py', 'r') as f:
                    content = f.read()
                    import re
                    match = re.search(r"OANDA_API_KEY\s*=\s*['\"]([^'\"]+)['\"]", content)
                    if match:
                        api_key = match.group(1)
                    match = re.search(r"OANDA_ACCOUNT_ID\s*=\s*['\"]([^'\"]+)['\"]", content)
                    if match:
                        account_id = match.group(1)
            
            if api_key and account_id:
                print(f"✓ Using API key: {api_key[:10]}...{api_key[-4:]}")
                print(f"✓ Using account: {account_id}")
                
                # Test API connection
                try:
                    headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    }
                    url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}"
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        account_info = response.json()['account']
                        balance = account_info.get('balance', 'N/A')
                        print(f"✓ API connection successful - Balance: ${balance}")
                        
                        # Try to get prices
                        url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/pricing"
                        params = {'instruments': 'EUR_USD,GBP_USD,XAU_USD'}
                        response = requests.get(url, headers=headers, params=params, timeout=10)
                        
                        if response.status_code == 200:
                            prices = response.json().get('prices', [])
                            print(f"✓ Price data accessible - {len(prices)} instruments")
                            return True
                        else:
                            print(f"❌ Cannot get prices: {response.status_code}")
                            return False
                    else:
                        print(f"❌ API connection failed: {response.status_code}")
                        return False
                except Exception as e:
                    print(f"❌ API test failed: {e}")
                    return False
            else:
                print("❌ Cannot extract API credentials for test")
                return False
        except Exception as e:
            print(f"❌ Live test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_report(self):
        """Generate comprehensive diagnostic report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE DIAGNOSTIC REPORT")
        print("="*80)
        
        print(f"\n📊 Summary:")
        print(f"  • Critical Issues: {len(self.issues_found)}")
        print(f"  • Warnings: {len(self.warnings)}")
        print(f"  • Recommendations: {len(self.recommendations)}")
        
        if self.issues_found:
            print(f"\n❌ CRITICAL ISSUES FOUND:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print(f"\n⚠ WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print(f"\n💡 PRIMARY RECOMMENDATIONS:")
        
        # Primary issue: System not running
        if "System not running" in str(self.issues_found):
            print("\n1. START THE SYSTEM:")
            print("   cd /workspace")
            print("   python3 ai_trading_system.py")
            print("   OR")
            print("   nohup python3 ai_trading_system.py > trading.log 2>&1 &")
        
        # Trading disabled
        if "Trading disabled" in str(self.issues_found):
            print("\n2. ENABLE TRADING:")
            print("   - Check if trading_enabled flag is True")
            print("   - Use Telegram command: /start_trading")
            print("   - Or modify code to default to True")
        
        # Blocking conditions
        if self.warnings and "blocking conditions" in str(self.warnings):
            print("\n3. REVIEW BLOCKING CONDITIONS:")
            print("   - Check news halt status")
            print("   - Check daily trade limits")
            print("   - Check concurrent trade limits")
            print("   - Review spread filters")
            print("   - Check session time requirements")
        
        # Strategy switching
        if "Strategy switching" in str(self.issues_found):
            print("\n4. FIX STRATEGY SWITCHING:")
            print("   - Ensure accounts.yaml exists and is configured")
            print("   - Implement graceful restart mechanism")
            print("   - Test strategy switching manually")
        
        print("\n" + "="*80)
        print("DIAGNOSTIC COMPLETE")
        print("="*80)
    
    def run_all_checks(self):
        """Run all diagnostic checks"""
        print("\n" + "="*80)
        print("COMPREHENSIVE SYSTEM DIAGNOSTIC")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_api_credentials()
        self.check_system_running()
        self.check_trading_enabled_flag()
        self.check_signal_generation()
        self.check_execution_flow()
        self.check_blocking_conditions()
        self.check_strategy_switching()
        self.check_startup_issues()
        self.test_live_signal_generation()
        
        self.generate_report()

if __name__ == "__main__":
    diagnostic = ComprehensiveDiagnostic()
    diagnostic.run_all_checks()
