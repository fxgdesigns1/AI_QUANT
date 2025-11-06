#!/usr/bin/env python3
"""
Daily Telegram Updates - Morning Briefing & Evening Summary
Runs continuously, sends updates at scheduled times
"""
import requests
import schedule
import time
from datetime import datetime
import json
import os

def get_telegram_token():
    """Get Telegram token from env or config file"""
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token or token in ['', 'your_telegram_bot_token_here']:
        # Try reading from config file
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'app.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'env_variables' in config:
                        token = config['env_variables'].get('TELEGRAM_TOKEN', '')
        except Exception as e:
            print(f"⚠️ Could not read config: {e}")
        # Fallback to known working token
        if not token or token in ['', 'your_telegram_bot_token_here']:
            token = '7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs'
    return token

def get_telegram_chat_id():
    """Get Telegram chat ID from env or config file"""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not chat_id or chat_id in ['', 'your_telegram_chat_id_here']:
        # Try reading from config file
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'app.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'env_variables' in config:
                        chat_id = config['env_variables'].get('TELEGRAM_CHAT_ID', '')
        except Exception as e:
            print(f"⚠️ Could not read config: {e}")
        # Fallback to known working chat ID
        if not chat_id or chat_id in ['', 'your_telegram_chat_id_here']:
            chat_id = '6100678501'
    return chat_id

TELEGRAM_TOKEN = get_telegram_token()
CHAT_ID = get_telegram_chat_id()
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")

def get_status_from_oanda():
    """Get status directly from OANDA API when dashboard is unavailable"""
    if not OANDA_API_KEY:
        return None
    
    try:
        # Import OANDA client
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from core.oanda_client import OandaClient
        
        account_id = os.getenv("OANDA_ACCOUNT_ID") or os.getenv("PRIMARY_ACCOUNT", "101-004-30719775-008")
        client = OandaClient(api_key=OANDA_API_KEY, account_id=account_id)
        
        # Get account info
        account = client.get_account()
        if not account:
            return None
        
        # Get market prices
        instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'AUD_USD']
        prices = client.get_current_prices(instruments)
        
        market_data = {}
        for instrument, price_data in prices.items():
            if hasattr(price_data, 'bid') and hasattr(price_data, 'ask'):
                market_data[instrument] = {
                    'bid': price_data.bid,
                    'ask': price_data.ask,
                    'timestamp': datetime.now().isoformat()
                }
        
        # Build status response
        return {
            'account_statuses': {
                account_id: {
                    'balance': account.balance,
                    'open_positions': account.open_position_count,
                    'active': True
                }
            },
            'market_data': market_data,
            'trade_phase': 'Active',
            'ai_recommendation': 'MONITOR',
            'trading_metrics': {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'total_loss': 0.0
            }
        }
    except Exception as e:
        print(f"❌ Error getting OANDA data: {e}")
        return None

def send_telegram(message):
    """Send message to Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram: {e}")
        return False

def get_cloud_status():
    """Get status from cloud system or local dashboard - FIXED CONNECTION"""
    # Try cloud system first
    cloud_urls = [
        "https://ai-quant-trading.uc.r.appspot.com/api/status",
        "http://localhost:8080/api/status"
    ]
    
    for url in cloud_urls:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected to: {url}")
                return data
        except Exception as e:
            print(f"⚠️ Failed to connect to {url}: {e}")
            continue
    
    # If both fail, get data directly from OANDA
    print("⚠️ Dashboard unavailable, fetching data directly from OANDA...")
    return get_status_from_oanda()

def morning_briefing():
    """Send morning briefing at 6:00 AM London"""
    print(f"\n{'='*60}")
    print(f"🌅 MORNING BRIEFING - {datetime.now().strftime('%I:%M %p')}")
    print(f"{'='*60}")
    
    status = get_cloud_status()
    
    if not status:
        message = """🌅 <b>MORNING BRIEFING - System Issue</b>
⏰ 6:00 AM London Time

⚠️ Unable to connect to cloud system.
Will retry and send update when connection restored.
"""
        send_telegram(message)
        return
    
    # Get account data
    accounts = status.get("account_statuses", {})
    total_balance = sum(acc.get("balance", 0) for acc in accounts.values())
    total_positions = sum(acc.get("open_positions", 0) for acc in accounts.values())
    
    # Get market data
    market_data = status.get("market_data", {})
    trade_phase = status.get("trade_phase", "Active")
    ai_rec = status.get("ai_recommendation", "MONITOR")
    
    # Format market prices
    market_prices = ""
    if market_data:
        for instrument, data in list(market_data.items())[:5]:  # Show top 5
            bid = data.get('bid', 0)
            ask = data.get('ask', 0)
            mid = (bid + ask) / 2 if bid and ask else 0
            spread = ask - bid if bid and ask else 0
            market_prices += f"\n{instrument.replace('_', '/')}: {mid:.5f} (spread: {spread:.5f})"
    else:
        market_prices = "\n📡 Fetching live prices..."
    
    # Get current date
    today = datetime.now().strftime("%A %b %d")
    
    message = f"""🌅 <b>GOOD MORNING - {today.upper()}</b>
⏰ {datetime.now().strftime('%I:%M %p')} London Time

━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 <b>PORTFOLIO STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Balance: ${total_balance:,.2f}
Active Accounts: {len(accounts)}
Open Positions: {total_positions}
System Status: 🟢 Online

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>LIVE MARKET PRICES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━{market_prices}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>TODAY'S PLAN</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Phase: {trade_phase}
AI Recommendation: <b>{ai_rec}</b>

<b>Trading Schedule:</b>
• Now - 2:00 PM: Light activity expected
• 2:00-5:00 PM: ⭐ PRIME TIME (main window)
• 5:00-9:00 PM: Moderate activity + exits

Expected Trades Today: 7-15 signals
Target Win Rate: 65-75%
Daily Goal: +0.5% to +2.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>MARKET CONDITIONS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Early London session - markets waking up
Volatility: Low to Moderate
Best opportunities: 2-5 PM London/NY overlap

━━━━━━━━━━━━━━━━━━━━━━━━━━

System will alert you to quality setups as they appear. Prime time starts in 8 hours!

Have a great trading day! 💼📈
"""
    
    if send_telegram(message):
        print("✅ Morning briefing sent successfully")
    else:
        print("❌ Failed to send morning briefing")

def evening_summary():
    """Send evening summary at 9:30 PM London"""
    print(f"\n{'='*60}")
    print(f"🌙 EVENING SUMMARY - {datetime.now().strftime('%I:%M %p')}")
    print(f"{'='*60}")
    
    status = get_cloud_status()
    
    if not status:
        message = """🌙 <b>EVENING SUMMARY - System Issue</b>
⏰ 9:30 PM London Time

⚠️ Unable to retrieve today's data.
Will send update when connection restored.
"""
        send_telegram(message)
        return
    
    # Get metrics
    metrics = status.get("trading_metrics", {})
    accounts = status.get("account_statuses", {})
    
    total_balance = sum(acc.get("balance", 0) for acc in accounts.values())
    total_trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)
    total_profit = metrics.get("total_profit", 0)
    total_loss = metrics.get("total_loss", 0)
    net_pl = total_profit + total_loss
    
    message = f"""🌙 <b>EVENING SUMMARY - FRIDAY OCT 10</b>
⏰ 9:30 PM London Time

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>TODAY'S RESULTS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Trades: {total_trades}
Win Rate: {win_rate:.1f}%
Net P/L: ${net_pl:,.2f}
"""
    
    if net_pl > 0:
        message += f"Daily Return: +{(net_pl/total_balance)*100:.2f}% ✅\n"
    elif net_pl < 0:
        message += f"Daily Return: {(net_pl/total_balance)*100:.2f}% ⚠️\n"
    else:
        message += "Daily Return: 0.00% (No trades)\n"
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 <b>PORTFOLIO STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

End of Day Balance: ${total_balance:,.2f}
Active Accounts: {len(accounts)}
Open Positions: {sum(acc.get("open_positions", 0) for acc in accounts.values())}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>WEEKLY PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Week Target: +2% minimum, +6% goal
Current Progress: Tracking...

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 <b>TOMORROW (SATURDAY)</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Market Status: 🔴 CLOSED (Weekend)
System Status: Monitoring only
Trading Resumes: Monday 9:00 AM

━━━━━━━━━━━━━━━━━━━━━━━━━━

Enjoy your weekend! Next briefing: Monday 6:00 AM 🌅
"""
    
    if send_telegram(message):
        print("✅ Evening summary sent successfully")
    else:
        print("❌ Failed to send evening summary")

def main():
    """Main scheduler loop"""
    print("="*60)
    print("📱 TELEGRAM DAILY UPDATES SCHEDULER STARTED")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    print()
    print("Schedule:")
    print("  🌅 Morning Briefing: 6:00 AM London")
    print("  🌙 Evening Summary: 9:30 PM London (21:30)")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)
    
    # Schedule jobs
    schedule.every().day.at("06:00").do(morning_briefing)
    schedule.every().day.at("21:30").do(evening_summary)
    
    # Send startup notification
    startup_msg = f"""🤖 <b>Daily Updates Scheduler Active</b>

Automated Telegram updates now running:
• 🌅 Morning briefing: 6:00 AM
• 🌙 Evening summary: 9:30 PM

System: Online and monitoring ✅
Started: {datetime.now().strftime('%I:%M %p')}
"""
    send_telegram(startup_msg)
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        # Install schedule if needed
        try:
            import schedule
        except ImportError:
            print("Installing schedule library...")
            import subprocess
            subprocess.check_call(["pip3", "install", "schedule"])
            import schedule
        
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scheduler stopped by user")
        send_telegram("⚠️ Daily updates scheduler stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        send_telegram(f"❌ Daily updates scheduler error: {e}")


