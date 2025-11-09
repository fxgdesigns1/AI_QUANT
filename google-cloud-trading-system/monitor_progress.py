#!/usr/bin/env python3
"""
Monitor optimization progress and send updates every 10 minutes
"""

import os
import sys
import time
import subprocess
from datetime import datetime

sys.path.insert(0, '.')

def get_progress():
    """Get latest progress from log"""
    try:
        result = subprocess.run(
            ["grep", "Progress:", "priority_optimization.log"],
            capture_output=True,
            text=True,
            cwd="/Users/mac/quant_system_clean/google-cloud-trading-system"
        )
        lines = result.stdout.strip().split("\n")
        if lines and lines[-1]:
            # Extract percentage from last line
            import re
            match = re.search(r'\((\d+\.\d+)%\)', lines[-1])
            if match:
                return float(match.group(1))
    except:
        pass
    return 0.0

def send_telegram_update(progress, trades_count):
    """Send progress update via Telegram"""
    os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
    os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"
    
    from src.core.telegram_notifier import TelegramNotifier
    
    notifier = TelegramNotifier()
    
    eta_minutes = int((100 - progress) / (progress / 10)) if progress > 0 else 0
    
    message = f"""⚙️ **OPTIMIZATION PROGRESS UPDATE**

**Trump DNA Strategy:**
Progress: {progress:.1f}% complete
Trades per test: {trades_count} trades
ETA: ~{eta_minutes} minutes

System running smoothly! Will update again in 10 minutes.

📊 Next: 75% WR Champion & Gold Scalping"""
    
    notifier.send_system_status('OPTIMIZATION RUNNING', message)

def main():
    print("\n" + "="*70)
    print("MONITORING OPTIMIZATION - 10 MINUTE UPDATES")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70 + "\n")
    
    last_update_time = time.time()
    update_interval = 600  # 10 minutes in seconds
    
    while True:
        # Check if process still running
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        if "optimize_priority_strategies.py" not in result.stdout:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ Optimization completed!")
            
            # Send completion notification
            os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
            os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"
            from src.core.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            notifier.send_system_status('OPTIMIZATION COMPLETE', 
                '✅ Priority strategies optimization finished! Preparing results...')
            break
        
        current_time = time.time()
        progress = get_progress()
        
        # Get recent trade counts
        try:
            result = subprocess.run(
                ["grep", "Backtest complete:", "priority_optimization.log"],
                capture_output=True,
                text=True,
                cwd="/Users/mac/quant_system_clean/google-cloud-trading-system"
            )
            lines = result.stdout.strip().split("\n")
            if lines and lines[-1]:
                import re
                match = re.search(r'(\d+) trades closed', lines[-1])
                trades = match.group(1) if match else "?"
            else:
                trades = "?"
        except:
            trades = "?"
        
        # Send update every 10 minutes
        if current_time - last_update_time >= update_interval:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sending 10-minute update...")
            print(f"  Progress: {progress:.1f}%")
            print(f"  Recent trades: {trades}")
            
            try:
                send_telegram_update(progress, trades)
                print("  ✅ Update sent to Telegram")
            except Exception as e:
                print(f"  ⚠️ Failed to send: {str(e)}")
            
            last_update_time = current_time
        
        # Console update every minute
        if int(current_time) % 60 < 5:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {progress:.1f}% | Recent: {trades} trades")
        
        time.sleep(5)  # Check every 5 seconds

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Monitoring stopped")
        print("Optimization continues in background")




