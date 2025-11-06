#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT - Why No Trades/Insights/Signals?
Comprehensive check of all system components
"""

import os
import sys
import requests
import yaml
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

def check_environment_variables():
    """Check critical environment variables"""
    print_header("1. ENVIRONMENT VARIABLES CHECK")
    
    issues = []
    
    # Check app.yaml
    try:
        with open('app.yaml', 'r') as f:
            config = yaml.safe_load(f)
            env_vars = config.get('env_variables', {})
            
            # Trading flags
            weekend_mode = env_vars.get('WEEKEND_MODE', 'true')
            trading_disabled = env_vars.get('TRADING_DISABLED', 'true')
            auto_trading = env_vars.get('AUTO_TRADING_ENABLED', 'false')
            scanner_enabled = env_vars.get('ENABLE_CANDLE_SCANNER', 'false')
            signal_gen = env_vars.get('SIGNAL_GENERATION', 'disabled')
            
            if weekend_mode.lower() == 'true':
                print_error(f"WEEKEND_MODE is 'true' - Trading disabled!")
                issues.append("WEEKEND_MODE")
            else:
                print_success(f"WEEKEND_MODE: {weekend_mode}")
            
            if trading_disabled.lower() == 'true':
                print_error(f"TRADING_DISABLED is 'true' - Trading disabled!")
                issues.append("TRADING_DISABLED")
            else:
                print_success(f"TRADING_DISABLED: {trading_disabled}")
            
            if auto_trading.lower() != 'true':
                print_warning(f"AUTO_TRADING_ENABLED: {auto_trading} (should be 'true')")
                issues.append("AUTO_TRADING")
            else:
                print_success(f"AUTO_TRADING_ENABLED: {auto_trading}")
            
            if scanner_enabled.lower() != 'true':
                print_warning(f"ENABLE_CANDLE_SCANNER: {scanner_enabled} (should be 'true')")
                issues.append("SCANNER")
            else:
                print_success(f"ENABLE_CANDLE_SCANNER: {scanner_enabled}")
            
            if signal_gen.lower() != 'enabled':
                print_warning(f"SIGNAL_GENERATION: {signal_gen} (should be 'enabled')")
                issues.append("SIGNAL_GEN")
            else:
                print_success(f"SIGNAL_GENERATION: {signal_gen}")
            
            # Telegram check
            telegram_token = env_vars.get('TELEGRAM_TOKEN', '')
            telegram_chat = env_vars.get('TELEGRAM_CHAT_ID', '')
            
            if not telegram_token or telegram_token == 'your_telegram_bot_token_here':
                print_error("TELEGRAM_TOKEN not configured!")
                issues.append("TELEGRAM_TOKEN")
            else:
                print_success(f"TELEGRAM_TOKEN: Configured (ends with ...{telegram_token[-10:]})")
            
            if not telegram_chat or telegram_chat == 'your_telegram_chat_id_here':
                print_error("TELEGRAM_CHAT_ID not configured!")
                issues.append("TELEGRAM_CHAT_ID")
            else:
                print_success(f"TELEGRAM_CHAT_ID: {telegram_chat}")
            
            # Check minimum confidence
            min_conf = env_vars.get('MIN_SIGNAL_CONFIDENCE', '0.80')
            print_info(f"MIN_SIGNAL_CONFIDENCE: {min_conf}")
            
    except Exception as e:
        print_error(f"Failed to read app.yaml: {e}")
        issues.append("CONFIG_FILE")
    
    return issues

def check_cron_configuration():
    """Check if cron jobs are configured"""
    print_header("2. CRON JOBS CHECK")
    
    issues = []
    
    try:
        with open('cron.yaml', 'r') as f:
            cron_config = yaml.safe_load(f)
            cron_jobs = cron_config.get('cron', [])
            
            if not cron_jobs:
                print_error("No cron jobs configured!")
                issues.append("NO_CRON")
                return issues
            
            print_info(f"Found {len(cron_jobs)} cron job(s):")
            
            for job in cron_jobs:
                desc = job.get('description', 'Unknown')
                url = job.get('url', 'Unknown')
                schedule = job.get('schedule', 'Unknown')
                print_info(f"  • {desc}")
                print_info(f"    URL: {url}")
                print_info(f"    Schedule: {schedule}")
                
                # Check if scanner cron exists
                if 'quality-scan' in url or 'scan' in url.lower():
                    print_success("Scanner cron job found!")
            
    except FileNotFoundError:
        print_error("cron.yaml not found!")
        issues.append("CRON_MISSING")
    except Exception as e:
        print_error(f"Error reading cron.yaml: {e}")
        issues.append("CRON_ERROR")
    
    return issues

def check_cloud_system_status():
    """Check if cloud system is responding"""
    print_header("3. CLOUD SYSTEM STATUS CHECK")
    
    issues = []
    base_url = "https://ai-quant-trading.uc.r.appspot.com"
    
    endpoints = {
        '/api/health': 'Health Check',
        '/api/status': 'System Status',
        '/cron/quality-scan': 'Quality Scanner',
    }
    
    for endpoint, name in endpoints.items():
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print_success(f"{name} ({endpoint}): Responding")
                if endpoint == '/api/status':
                    data = response.json()
                    print_info(f"  System Status: {data.get('status', 'unknown')}")
            elif response.status_code == 404:
                print_error(f"{name} ({endpoint}): Not Found (404)")
                issues.append(f"{endpoint}_404")
            elif response.status_code == 503:
                print_error(f"{name} ({endpoint}): Service Unavailable (503)")
                issues.append(f"{endpoint}_503")
            else:
                print_warning(f"{name} ({endpoint}): Status {response.status_code}")
                issues.append(f"{endpoint}_{response.status_code}")
                
        except requests.exceptions.Timeout:
            print_error(f"{name} ({endpoint}): Timeout")
            issues.append(f"{endpoint}_TIMEOUT")
        except requests.exceptions.ConnectionError:
            print_error(f"{name} ({endpoint}): Connection Error")
            issues.append(f"{endpoint}_CONNECTION")
        except Exception as e:
            print_error(f"{name} ({endpoint}): {e}")
            issues.append(f"{endpoint}_ERROR")
    
    return issues

def check_scanner_initialization():
    """Check if scanner is initialized in main.py"""
    print_header("4. SCANNER INITIALIZATION CHECK")
    
    issues = []
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
            # Check for scanner initialization
            if 'candle_based_scanner' in content.lower() or 'get_candle_scanner' in content:
                print_success("Scanner import found in main.py")
            else:
                print_error("Scanner not imported in main.py!")
                issues.append("SCANNER_IMPORT")
            
            if 'start_scanning' in content:
                print_success("Scanner start method found")
            else:
                print_warning("Scanner start_scanning() not called")
                issues.append("SCANNER_START")
            
            if 'threading' in content and 'scanner' in content.lower():
                print_success("Background thread for scanner found")
            else:
                print_warning("Scanner may not be running in background thread")
                issues.append("SCANNER_THREAD")
                
    except Exception as e:
        print_error(f"Error checking main.py: {e}")
        issues.append("MAIN_PY_ERROR")
    
    return issues

def check_telegram_connection():
    """Test Telegram connection"""
    print_header("5. TELEGRAM CONNECTION CHECK")
    
    issues = []
    
    try:
        with open('app.yaml', 'r') as f:
            config = yaml.safe_load(f)
            env_vars = config.get('env_variables', {})
            token = env_vars.get('TELEGRAM_TOKEN', '')
            chat_id = env_vars.get('TELEGRAM_CHAT_ID', '')
        
        if not token or token == 'your_telegram_bot_token_here':
            print_error("TELEGRAM_TOKEN not set")
            issues.append("TELEGRAM_TOKEN")
            return issues
        
        if not chat_id:
            print_error("TELEGRAM_CHAT_ID not set")
            issues.append("TELEGRAM_CHAT_ID")
            return issues
        
        # Test send message
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_name = data.get('result', {}).get('username', 'Unknown')
                print_success(f"Telegram bot connected: @{bot_name}")
            else:
                print_error(f"Telegram API error: {data.get('description', 'Unknown')}")
                issues.append("TELEGRAM_API")
        else:
            print_error(f"Telegram API returned {response.status_code}")
            issues.append("TELEGRAM_HTTP")
            
        # Test send to chat
        test_msg = f"🔍 Diagnostic Test - {datetime.now().strftime('%H:%M:%S')}"
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        send_response = requests.post(send_url, json={
            'chat_id': chat_id,
            'text': test_msg
        }, timeout=5)
        
        if send_response.status_code == 200:
            print_success("Test message sent successfully!")
        else:
            error_data = send_response.json()
            print_error(f"Failed to send test message: {error_data.get('description', 'Unknown error')}")
            issues.append("TELEGRAM_SEND")
            
    except Exception as e:
        print_error(f"Telegram check failed: {e}")
        issues.append("TELEGRAM_ERROR")
    
    return issues

def generate_report(all_issues):
    """Generate final diagnostic report"""
    print_header("DIAGNOSTIC SUMMARY")
    
    if not all_issues:
        print_success("No critical issues found!")
        print_info("System should be generating trades/signals.")
        print_info("Possible reasons for no trades:")
        print_info("  1. Market conditions don't meet strategy criteria")
        print_info("  2. Confidence thresholds too strict")
        print_info("  3. Scanner cron jobs not running (check Google Cloud console)")
        print_info("  4. All strategies filtering out signals")
    else:
        print_error(f"Found {len(all_issues)} potential issue(s):")
        for issue in all_issues:
            print(f"  • {issue}")
        
        print("\n" + YELLOW + "RECOMMENDED ACTIONS:" + RESET)
        
        if "WEEKEND_MODE" in all_issues or "TRADING_DISABLED" in all_issues:
            print_warning("1. Enable trading in app.yaml:")
            print("   WEEKEND_MODE: 'false'")
            print("   TRADING_DISABLED: 'false'")
        
        if "SCANNER" in all_issues or "SCANNER_IMPORT" in all_issues:
            print_warning("2. Ensure scanner is initialized in main.py")
            print("   Add scanner initialization code")
        
        if any("TELEGRAM" in issue for issue in all_issues):
            print_warning("3. Fix Telegram configuration in app.yaml")
        
        if "CRON_MISSING" in all_issues:
            print_warning("4. Deploy cron.yaml to Google Cloud")
            print("   gcloud app deploy cron.yaml")
        
        print("\n" + BLUE + "Next Steps:" + RESET)
        print("1. Fix the issues above")
        print("2. Redeploy to Google Cloud")
        print("3. Check Google Cloud logs for scanner activity")
        print("4. Verify cron jobs are running in Cloud Console")

if __name__ == "__main__":
    print(f"\n{BLUE}🔍 TRADING SYSTEM DIAGNOSTIC TOOL{RESET}")
    print(f"{BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    
    all_issues = []
    
    all_issues.extend(check_environment_variables())
    all_issues.extend(check_cron_configuration())
    all_issues.extend(check_cloud_system_status())
    all_issues.extend(check_scanner_initialization())
    all_issues.extend(check_telegram_connection())
    
    generate_report(all_issues)
    
    print(f"\n{BLUE}{'='*80}{RESET}\n")




