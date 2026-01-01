#!/usr/bin/env python3
from src.core.settings import settings
"""
Verify each strategy is running correctly
"""
import os
import sys
import yaml
import requests
from datetime import datetime
from typing import Dict, List, Any

# Add path for strategy registry
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system'))

# OANDA Configuration
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

HEADERS = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

def load_accounts():
    """Load active accounts"""
    yaml_paths = [
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 
                     'google-cloud-trading-system', 'AI_QUANT_credentials', 'accounts.yaml'),
        '/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml',
    ]
    
    for yaml_path in yaml_paths:
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            accounts = data.get('accounts', {})
            return [(name, acc) for name, acc in accounts.items() if acc.get('active', True)]
    return []

def check_strategy_loading(strategy_name):
    """Check if strategy can be loaded"""
    try:
        from src.strategies.registry import create_strategy, resolve_strategy_key
        
        resolved = resolve_strategy_key(strategy_name)
        if not resolved:
            return {'status': '❌', 'error': f'Strategy key "{strategy_name}" not found in registry'}
        
        strategy = create_strategy(resolved)
        if strategy is None:
            return {'status': '❌', 'error': 'Strategy returned None (dependency missing?)'}
        
        has_analyze = hasattr(strategy, 'analyze_market')
        strategy_type = type(strategy).__name__
        
        return {
            'status': '✅',
            'type': strategy_type,
            'has_analyze_market': has_analyze,
            'has_generate_signals': hasattr(strategy, 'generate_signals'),
            'resolved_key': resolved
        }
    except Exception as e:
        return {'status': '❌', 'error': str(e)}

def get_account_info(account_id):
    """Get account information"""
    try:
        url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json().get('account')
        return None
    except:
        return None

def get_recent_trades(account_id, hours=24):
    """Get recent trades"""
    try:
        from datetime import timedelta
        since_time = datetime.utcnow() - timedelta(hours=hours)
        since_str = since_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
        
        url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}/trades"
        params = {'state': 'CLOSED', 'count': 50}
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        
        if response.status_code == 200:
            trades = response.json().get('trades', [])
            # Filter to last 24h
            recent = []
            for trade in trades:
                close_time = trade.get('closeTime', '')
                if close_time and close_time >= since_str:
                    recent.append(trade)
            return recent
        return []
    except:
        return []

def analyze_strategy_status(account_name, account_config, account_id):
    """Analyze if strategy is running correctly"""
    strategy_name = account_config.get('strategy', 'unknown')
    
    # Check strategy loading
    load_result = check_strategy_loading(strategy_name)
    
    # Get account info
    account_info = get_account_info(account_id)
    balance = float(account_info['balance']) if account_info else 0
    
    # Get recent trades
    recent_trades = get_recent_trades(account_id, hours=24)
    
    # Analyze
    status = {
        'account_name': account_name,
        'account_id': account_id,
        'strategy_name': strategy_name,
        'balance': balance,
        'recent_trades_24h': len(recent_trades),
        'strategy_loading': load_result,
        'is_active': len(recent_trades) > 0 or account_info is not None,
    }
    
    # Determine if running correctly
    is_loadable = load_result.get('status') == '✅'
    has_analyze = load_result.get('has_analyze_market', False)
    has_generate = load_result.get('has_generate_signals', False)
    
    if not is_loadable:
        status['running_correctly'] = False
        status['issue'] = f"Strategy cannot be loaded: {load_result.get('error', 'Unknown error')}"
    elif not (has_analyze or has_generate):
        status['running_correctly'] = False
        status['issue'] = "Strategy loaded but missing both analyze_market() and generate_signals() methods"
    elif len(recent_trades) == 0 and account_info:
        status['running_correctly'] = '⚠️'
        status['issue'] = "Strategy loaded correctly but no trades in last 24h (may be waiting for conditions)"
    else:
        status['running_correctly'] = True
        status['issue'] = None
    
    return status

def main():
    print("=" * 80)
    print("STRATEGY VERIFICATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)\n")
    
    accounts = load_accounts()
    if not accounts:
        print("❌ No active accounts found")
        return
    
    print(f"Found {len(accounts)} active accounts\n")
    
    results = []
    for account_name, account_config in accounts:
        account_id = account_config.get('account_id')
        if not account_id:
            continue
        
        print(f"Checking {account_name} ({account_id})...")
        result = analyze_strategy_status(account_name, account_config, account_id)
        results.append(result)
        
        # Print summary
        status_icon = result['running_correctly']
        if status_icon == True:
            print(f"  {status_icon} Running correctly")
        elif status_icon == '⚠️':
            print(f"  {status_icon} Loaded but inactive")
        else:
            print(f"  {status_icon} NOT running correctly")
        print()
    
    # Generate report
    report = generate_report(results)
    print(report)
    
    # Send to Telegram
    send_to_telegram(report, results)

def generate_report(results):
    """Generate formatted report"""
    report = []
    report.append("=" * 80)
    report.append("STRATEGY VERIFICATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)\n")
    
    for result in results:
        report.append("-" * 80)
        report.append(f"Account: {result['account_name']}")
        report.append(f"Strategy: {result['strategy_name']}")
        report.append(f"Account ID: {result['account_id']}")
        report.append(f"Balance: ${result['balance']:.2f}")
        report.append(f"Trades (24h): {result['recent_trades_24h']}")
        report.append("")
        
        # Strategy loading status
        load_result = result['strategy_loading']
        report.append(f"Strategy Loading: {load_result.get('status', '?')}")
        if load_result.get('type'):
            report.append(f"  Type: {load_result['type']}")
        if load_result.get('resolved_key'):
            report.append(f"  Resolved Key: {load_result['resolved_key']}")
        if load_result.get('has_analyze_market') is not None:
            report.append(f"  Has analyze_market(): {load_result['has_analyze_market']}")
        if load_result.get('has_generate_signals') is not None:
            report.append(f"  Has generate_signals(): {load_result['has_generate_signals']}")
        if load_result.get('error'):
            report.append(f"  Error: {load_result['error']}")
        report.append("")
        
        # Running status
        status_icon = result['running_correctly']
        if status_icon == True:
            report.append("✅ STATUS: Running correctly")
            report.append("   Strategy is loadable and has a valid execution method (analyze_market or generate_signals)")
            if result['recent_trades_24h'] > 0:
                report.append(f"   Active: {result['recent_trades_24h']} trades in last 24h")
            else:
                report.append("   Note: No trades in last 24h (may be waiting for conditions)")
        elif status_icon == '⚠️':
            report.append("⚠️ STATUS: Loaded but inactive")
            report.append("   Strategy is loaded correctly but not generating trades")
            report.append("   Possible reasons:")
            report.append("   - Market conditions don't match strategy filters")
            report.append("   - Strategy filters too strict")
            report.append("   - Outside trading hours")
        else:
            report.append("❌ STATUS: NOT running correctly")
            report.append(f"   Issue: {result.get('issue', 'Unknown')}")
            report.append("   Action: Strategy will use default logic (fallback)")
        report.append("")
    
    # Summary
    report.append("=" * 80)
    report.append("SUMMARY")
    report.append("=" * 80)
    
    running = sum(1 for r in results if r['running_correctly'] == True)
    inactive = sum(1 for r in results if r['running_correctly'] == '⚠️')
    not_working = sum(1 for r in results if r['running_correctly'] == False)
    
    report.append(f"Total Strategies: {len(results)}")
    report.append(f"✅ Running Correctly: {running}")
    report.append(f"⚠️ Loaded but Inactive: {inactive}")
    report.append(f"❌ Not Working: {not_working}")
    report.append("")
    
    if not_working > 0:
        report.append("⚠️ WARNING: Some strategies cannot be loaded")
        report.append("   These will use default logic until dependencies are available")
        report.append("   Check production VM for required modules (src.core.order_manager, etc.)")
    
    return "\n".join(report)

def send_to_telegram(report, results):
    """Send report to Telegram"""
    try:
        TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6100678501")
        
        # Create summary message
        summary = "🔍 **STRATEGY VERIFICATION REPORT**\n\n"
        
        running = sum(1 for r in results if r['running_correctly'] == True)
        inactive = sum(1 for r in results if r['running_correctly'] == '⚠️')
        not_working = sum(1 for r in results if r['running_correctly'] == False)
        
        summary += f"**Total:** {len(results)} strategies\n"
        summary += f"✅ **Running:** {running}\n"
        summary += f"⚠️ **Inactive:** {inactive}\n"
        summary += f"❌ **Not Working:** {not_working}\n\n"
        summary += "---\n\n"
        
        # Add each strategy
        for result in results:
            status_icon = result['running_correctly']
            if status_icon == True:
                status_text = "✅ Running"
            elif status_icon == '⚠️':
                status_text = "⚠️ Inactive"
            else:
                status_text = "❌ Not Working"
            
            summary += f"**{result['account_name']}**\n"
            summary += f"Strategy: `{result['strategy_name']}`\n"
            summary += f"Status: {status_text}\n"
            summary += f"Trades (24h): {result['recent_trades_24h']}\n"
            
            if result.get('issue'):
                summary += f"Issue: {result['issue']}\n"
            
            load_result = result['strategy_loading']
            if load_result.get('has_analyze_market') or load_result.get('has_generate_signals'):
                summary += "Has execution method: ✅\n"
            else:
                summary += "Has execution method: ❌\n"
            
            summary += "\n"
        
        # Send summary
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': summary, 'parse_mode': 'Markdown'}
        requests.post(url, data=data, timeout=10)
        
        print("✅ Report sent to Telegram")
    except Exception as e:
        print(f"⚠️ Could not send to Telegram: {e}")

if __name__ == "__main__":
    main()




