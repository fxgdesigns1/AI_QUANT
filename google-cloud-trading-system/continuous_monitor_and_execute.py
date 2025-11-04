#!/usr/bin/env python3
"""
CONTINUOUS MARKET MONITOR & AUTO-EXECUTOR
Checks market every 5 minutes and executes when opportunities found
BRUTAL HONESTY - Alerts immediately if signals found but not executed
"""

import sys
sys.path.insert(0, 'src')

import time
import logging
from datetime import datetime
import pytz
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram credentials (env only)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BASE_URL = "https://ai-quant-trading.uc.r.appspot.com"

def send_telegram(message):
    """Send Telegram alert"""
    try:
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            return False
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_system_status():
    """Get current system status"""
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=60)
        return r.json()
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return None

def check_for_signals():
    """Check if scanner has generated any signals"""
    # Check logs for signals
    return 0  # Placeholder - would check actual signals

def force_execute_trades():
    """Force execute trades on all accounts"""
    try:
        r = requests.post(f"{BASE_URL}/api/force_execute_now", timeout=120)
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return None
    except Exception as e:
        logger.error(f"Force execute failed: {e}")
        return None

def analyze_market_conditions(data):
    """Analyze if market conditions are good for trading"""
    if not data or 'market_data' not in data:
        return False, "No market data"
    
    # Check if we have fresh prices
    market_data = data['market_data']
    if not market_data:
        return False, "Market data empty"
    
    # Get first account data
    first_account = list(market_data.keys())[0]
    account_data = market_data[first_account]
    
    # Check for trending or ranging markets
    trending_count = 0
    ranging_count = 0
    volatile_count = 0
    
    for instrument, mdata in account_data.items():
        regime = mdata.get('regime', 'unknown')
        if regime == 'trending':
            trending_count += 1
        elif regime == 'ranging':
            ranging_count += 1
        elif regime == 'volatile':
            volatile_count += 1
    
    # Prefer trending or ranging markets
    if trending_count >= 2 or ranging_count >= 2:
        return True, f"Good conditions: {trending_count} trending, {ranging_count} ranging"
    else:
        return False, f"Choppy: {volatile_count} volatile markets"

def main():
    """Main monitoring loop"""
    print("="*90)
    print("🔥 CONTINUOUS MARKET MONITOR - STARTING")
    print("="*90)
    print()
    print("Monitoring interval: Every 5 minutes")
    print("Auto-execution: Enabled when good setups found")
    print("Alerts: Immediate on signals or failures")
    print()
    
    london_tz = pytz.timezone('Europe/London')
    check_count = 0
    trades_executed = 0
    last_trade_time = None
    
    while True:
        try:
            check_count += 1
            now = datetime.now(london_tz)
            
            print("="*90)
            print(f"CHECK #{check_count} - {now.strftime('%H:%M:%S %Z')}")
            print("="*90)
            print()
            
            # Get system status
            data = get_system_status()
            
            if not data:
                print("❌ Failed to get system status")
                send_telegram(f"⚠️ ALERT: System status check failed at {now.strftime('%H:%M:%S')}")
                time.sleep(300)  # Wait 5 minutes
                continue
            
            # Check current positions
            total_open = 0
            if 'trading_systems' in data:
                for account_id, info in data['trading_systems'].items():
                    open_trades = info.get('open_trades', 0)
                    total_open += open_trades
            
            print(f"Open Positions: {total_open}")
            print(f"System Status: {data.get('system_status', 'unknown')}")
            print()
            
            # Analyze market conditions
            can_trade, reason = analyze_market_conditions(data)
            print(f"Market Conditions: {reason}")
            print()
            
            # Check if we should execute more trades
            if can_trade and total_open < 5:  # Limit to 5 concurrent positions
                print("✅ Good conditions detected - EXECUTING TRADE")
                print()
                
                result = force_execute_trades()
                
                if result and result.get('trades_placed', 0) > 0:
                    placed = result['trades_placed']
                    trades_executed += placed
                    last_trade_time = now
                    
                    print(f"🎉 {placed} TRADE(S) EXECUTED!")
                    
                    # Send Telegram alert
                    details = []
                    for r in result.get('results', []):
                        if r.get('status') == 'executed':
                            details.append(f"✅ {r['account']}: {r['instrument']} (Order: {r['order_id']})")
                    
                    message = f"""🎯 TRADES EXECUTED - Check #{check_count}

Time: {now.strftime('%H:%M:%S London')}
Trades Placed: {placed}

{chr(10).join(details)}

Total executed today: {trades_executed}
Open positions: {total_open + placed}
"""
                    send_telegram(message)
                else:
                    print("⚠️ Execution attempted but no trades placed")
                    print()
                    
                    # Alert if execution failed
                    if result:
                        errors = [r.get('error', 'Unknown') for r in result.get('results', []) if r.get('status') != 'executed']
                        if errors:
                            send_telegram(f"⚠️ EXECUTION FAILED at {now.strftime('%H:%M:%S')}\nErrors: {', '.join(set(errors[:3]))}")
            
            elif total_open >= 5:
                print(f"ℹ️  Max positions reached ({total_open}/5) - monitoring existing trades")
            else:
                print(f"ℹ️  Waiting for better conditions: {reason}")
            
            print()
            print(f"Summary: {trades_executed} total trades | {total_open} open | Next check in 5 min")
            print()
            
            # Wait 5 minutes
            time.sleep(300)
            
        except KeyboardInterrupt:
            print()
            print("="*90)
            print("🛑 MONITORING STOPPED")
            print("="*90)
            print(f"Total trades executed: {trades_executed}")
            break
        except Exception as e:
            print(f"❌ Error in monitoring loop: {e}")
            send_telegram(f"⚠️ MONITOR ERROR at {datetime.now().strftime('%H:%M:%S')}: {str(e)[:100]}")
            time.sleep(300)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        send_telegram(f"🚨 MONITOR CRASHED: {str(e)[:200]}")



