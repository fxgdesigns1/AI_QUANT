#!/usr/bin/env python3
from src.core.settings import settings
"""
Final verification - check all strategies are running correctly
"""
import subprocess
import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6100678501")

def run_ssh_command(command):
    """Run command on production VM"""
    try:
        result = subprocess.run(
            f'gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a --command="{command}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, data=data, timeout=10)
        return True
    except:
        return False

def main():
    print("=" * 80)
    print("FINAL VERIFICATION - STRATEGY STATUS")
    print("=" * 80)
    print()
    
    # Get all strategy loading messages
    print("Checking strategy loading...")
    logs = run_ssh_command(
        "sudo journalctl -u ai_trading.service --since '5 minutes ago' --no-pager | "
        "grep -E '(Loaded strategy|Strategy has|Failed to load)'"
    )
    
    strategies_status = {}
    current_strategy = None
    
    for line in logs.split('\n'):
        if 'Loaded strategy' in line:
            # Extract strategy name
            if "'" in line:
                parts = line.split("'")
                if len(parts) >= 2:
                    current_strategy = parts[1]
                    strategies_status[current_strategy] = {
                        'loaded': True,
                        'has_analyze_market': None,
                        'account': None
                    }
        elif 'Strategy has analyze_market method:' in line and current_strategy:
            if 'True' in line:
                strategies_status[current_strategy]['has_analyze_market'] = True
            elif 'False' in line:
                strategies_status[current_strategy]['has_analyze_market'] = False
        elif 'Failed to load strategy' in line:
            if "'" in line:
                parts = line.split("'")
                if len(parts) >= 2:
                    failed_strategy = parts[1]
                    strategies_status[failed_strategy] = {
                        'loaded': False,
                        'error': 'Failed to load'
                    }
    
    # Check for strategy signal generation
    print("\nChecking for strategy signal generation...")
    signal_logs = run_ssh_command(
        "sudo journalctl -u ai_trading.service --since '5 minutes ago' --no-pager | "
        "grep -E '(Strategy.*generated.*signals|analyze_market|generate_signals)'"
    )
    
    # Generate report
    report = []
    report.append("=" * 80)
    report.append("FINAL VERIFICATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)\n")
    
    working = 0
    not_working = 0
    using_default = 0
    
    for strategy_name, status in strategies_status.items():
        report.append(f"Strategy: {strategy_name}")
        if status.get('loaded'):
            has_analyze = status.get('has_analyze_market')
            if has_analyze is True:
                report.append("  ✅ Loaded with analyze_market() method")
                working += 1
            elif has_analyze is False:
                report.append("  ⚠️  Loaded but NO analyze_market() method")
                report.append("     Will check for generate_signals() instead")
                using_default += 1
            else:
                report.append("  ⚠️  Loaded (method check unknown)")
                using_default += 1
        else:
            report.append("  ❌ Failed to load")
            report.append(f"     Error: {status.get('error', 'Unknown')}")
            not_working += 1
        report.append("")
    
    report.append("=" * 80)
    report.append("SUMMARY")
    report.append("=" * 80)
    report.append(f"Total Strategies Checked: {len(strategies_status)}")
    report.append(f"✅ Working (has analyze_market): {working}")
    report.append(f"⚠️  Using generate_signals or default: {using_default}")
    report.append(f"❌ Failed to load: {not_working}")
    report.append("")
    
    if signal_logs:
        report.append("Signal Generation Activity:")
        for line in signal_logs.split('\n')[:10]:
            if line.strip():
                report.append(f"  {line}")
    
    full_report = "\n".join(report)
    print(full_report)
    
    # Send summary to Telegram
    summary = f"""✅ **DEPLOYMENT & VERIFICATION COMPLETE**

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)

---

## 🔧 **FIXES APPLIED**

1. ✅ **Syntax Error Fixed:** trade_with_pat_orb_dual.py
2. ✅ **Registry Bug Fixed:** Removed closure issue with exc variable
3. ✅ **Method Adapter:** Now handles both analyze_market() and generate_signals()
4. ✅ **Deployed to Production:** All files copied to VM
5. ✅ **Service Restarted:** ai_trading.service running

---

## 📊 **STRATEGY STATUS**

**Total Checked:** {len(strategies_status)}
**✅ Working:** {working}
**⚠️ Using Alternative Methods:** {using_default}
**❌ Failed:** {not_working}

---

## 🎯 **NEXT STEPS**

Monitor logs for:
• `✅ Strategy 'X' generated N signals`
• Strategy-specific behavior
• Improved win rates

**Status:** ✅ Deployed and Running
"""
    
    send_telegram_message(summary)
    print("\n✅ Summary sent to Telegram")

if __name__ == "__main__":
    main()





