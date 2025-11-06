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
        # Important project paths
        self.repo_root = Path(__file__).parent
        self.gcloud_dir = self.repo_root / 'google-cloud-trading-system'
        self.accounts_yaml_path = self.gcloud_dir / 'accounts.yaml'
        self.app_yaml_path = self.gcloud_dir / 'app.yaml'
        
    def check_api_credentials(self):
        """Check if API credentials are properly configured"""
        print("\n" + "="*80)
        print("CHECK 1: API CREDENTIALS")
        print("="*80)
        
        issues = []
        
        # Check environment variables
        api_key = os.getenv('OANDA_API_KEY')
        if not api_key:
            # Try to read from app.yaml
            try:
                if self.app_yaml_path.exists():
                    import yaml
                    with open(self.app_yaml_path, 'r') as f:
                        app_cfg = yaml.safe_load(f)
                    env_vars = (app_cfg or {}).get('env_variables') or {}
                    api_key = env_vars.get('OANDA_API_KEY')
                    if api_key:
                        print("✓ API key found in app.yaml")
                else:
                    pass
            except Exception as e:
                print(f"⚠ Could not read app.yaml for API key: {e}")
            if not api_key:
                issues.append("❌ No API key found in environment or app.yaml")
                self.issues_found.append("Missing API credentials")
        else:
            print(f"✓ API key found in environment: {api_key[:10]}...{api_key[-4:]}")
        
        # Check account ID
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        if not account_id:
            # Try to read from accounts.yaml
            try:
                if self.accounts_yaml_path.exists():
                    import yaml
                    with open(self.accounts_yaml_path, 'r') as f:
                        acc_cfg = yaml.safe_load(f)
                    accounts = (acc_cfg or {}).get('accounts') or []
                    if accounts:
                        account_id = accounts[0].get('id')
                        if account_id:
                            print("✓ Account ID found in accounts.yaml")
                else:
                    pass
            except Exception as e:
                print(f"⚠ Could not read accounts.yaml for account id: {e}")
            if not account_id:
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
            
            if 'continuous_aggressive_trader.py' in result.stdout:
                running_processes.append('continuous_aggressive_trader.py')
            if 'cloud_main.py' in result.stdout:
                running_processes.append('cloud_main.py')
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
        """Check env flags that can block trading"""
        print("\n" + "="*80)
        print("CHECK 3: TRADING ENABLED / ENV FLAGS")
        print("="*80)
        
        env_name = (os.getenv('OANDA_ENV') or os.getenv('OANDA_ENVIRONMENT') or 'practice').lower()
        live_flag = (os.getenv('LIVE_TRADING') or 'false').lower() == 'true'
        dry_run = (os.getenv('DRY_RUN') or 'false').lower() == 'true'
        account_disabled = (os.getenv('ACCOUNT_DISABLED') or 'false').lower() == 'true'

        print(f"• OANDA_ENV / OANDA_ENVIRONMENT = {env_name}")
        print(f"• LIVE_TRADING = {os.getenv('LIVE_TRADING')}")
        print(f"• DRY_RUN = {os.getenv('DRY_RUN')}")
        print(f"• ACCOUNT_DISABLED = {os.getenv('ACCOUNT_DISABLED')}")

        if env_name == 'live' or live_flag:
            print("❌ Live trading mode is blocked by codepath; use practice")
            self.issues_found.append("Env set to live or LIVE_TRADING=true (blocked)")
        if dry_run:
            print("❌ DRY_RUN=true blocks execution by design")
            self.issues_found.append("DRY_RUN=true (blocked)")
        if account_disabled:
            print("❌ ACCOUNT_DISABLED=true blocks execution")
            self.issues_found.append("ACCOUNT_DISABLED=true (blocked)")
        
        return True
    
    def check_signal_generation(self):
        """Check if signals are being generated"""
        print("\n" + "="*80)
        print("CHECK 4: SIGNAL GENERATION")
        print("="*80)
        
        issues = []
        
        # Heuristic: verify scanners/executors exist in core modules
        core_files = [
            self.gcloud_dir / 'src' / 'core' / 'trading_scanner.py',
            self.gcloud_dir / 'src' / 'core' / 'strategy_executor.py',
            self.gcloud_dir / 'src' / 'core' / 'order_manager.py',
        ]
        found_any = False
        for path in core_files:
            if path.exists():
                try:
                    content = path.read_text()
                    if 'class TradingScanner' in content or 'def _execution_loop' in content:
                        found_any = True
                except Exception:
                    pass
        if found_any:
            print("✓ Signal/Execution modules present (scanner/executor/order manager)")
        else:
            print("❌ Signal/Execution modules not found where expected")
            self.issues_found.append("Core scanner/executor modules missing")
        
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
        
        # Check for continuous runner
        runner = self.gcloud_dir / 'continuous_aggressive_trader.py'
        if runner.exists():
            print("✓ Continuous trader entrypoint found")
        else:
            issues.append("continuous_aggressive_trader.py missing")
        
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
        
        # Check known blockers in order manager
        om_path = self.gcloud_dir / 'src' / 'core' / 'order_manager.py'
        if om_path.exists():
            try:
                om = om_path.read_text()
                if 'LIVE_TRADING' in om or 'DRY_RUN' in om or 'ACCOUNT_DISABLED' in om:
                    print("⚠ OrderManager has env-based hard-blocks (LIVE_TRADING/DRY_RUN/ACCOUNT_DISABLED)")
                    blocking_conditions.append('Env flags block execution if set')
            except Exception:
                pass
        
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
            str(self.accounts_yaml_path),
            str(self.repo_root / 'accounts.yaml')
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
            str(self.gcloud_dir / 'src' / 'core' / 'graceful_restart.py'),
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
        
        # Check runner for initialization delays
        runner = self.gcloud_dir / 'continuous_aggressive_trader.py'
        try:
            if runner.exists():
                content = runner.read_text()
                if 'time.sleep' in content:
                    sleep_count = content.count('time.sleep')
                    print(f"⚠ Runner has {sleep_count} time.sleep calls (expected)")
        except Exception:
            pass
        
        # Check for service configuration
        service_paths = [
            str(self.repo_root / 'ai_trading.service'),
            str(self.repo_root / 'automated_trading.service')
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
            # Read API key and account from env or config files
            api_key = None
            account_id = None
            
            api_key = os.getenv('OANDA_API_KEY')
            account_id = os.getenv('OANDA_ACCOUNT_ID')
            if not api_key and self.app_yaml_path.exists():
                try:
                    import yaml
                    with open(self.app_yaml_path, 'r') as f:
                        app_cfg = yaml.safe_load(f)
                    env_vars = (app_cfg or {}).get('env_variables') or {}
                    api_key = api_key or env_vars.get('OANDA_API_KEY')
                except Exception:
                    pass
            if not account_id and self.accounts_yaml_path.exists():
                try:
                    import yaml
                    with open(self.accounts_yaml_path, 'r') as f:
                        acc_cfg = yaml.safe_load(f)
                    accounts = (acc_cfg or {}).get('accounts') or []
                    if accounts:
                        account_id = accounts[0].get('id')
                except Exception:
                    pass
            
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
            print(f"   cd {self.gcloud_dir}")
            print("   python3 continuous_aggressive_trader.py")
            print("   OR")
            print("   nohup python3 continuous_aggressive_trader.py > continuous_trader.log 2>&1 &")
        
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
