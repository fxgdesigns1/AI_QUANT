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

TELEGRAM_TOKEN = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
CHAT_ID = "6100678501"
OANDA_API_KEY = "REMOVED_SECRET"

def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram: {e}")
        return False

def get_cloud_status():
    """Get status from LOCAL dashboard system - SYNCHRONIZED DATA"""
    try:
        response = requests.get(
            "http://localhost:8080/api/status",
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting local dashboard status: {e}")
        return None

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
    trade_phase = status.get("trade_phase", "Unknown")
    ai_rec = status.get("ai_recommendation", "HOLD")
    
    message = f"""🌅 <b>GOOD MORNING - FRIDAY OCT 10</b>
⏰ 6:00 AM London Time

━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 <b>PORTFOLIO STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Balance: ${total_balance:,.2f}
Active Accounts: {len(accounts)}
Open Positions: {total_positions}
System Status: 🟢 Online

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


