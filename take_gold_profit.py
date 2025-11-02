#!/usr/bin/env python3
"""
Take partial profit on gold position
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add google-cloud-trading-system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
load_dotenv(env_path)

from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import get_telegram_notifier

GOLD_ACCOUNT = '101-004-30719775-001'

def take_partial_profit(percentage: float = 50.0):
    """
    Take partial profit on gold position
    
    Args:
        percentage: Percentage of position to close (default 50%)
    """
    
    print("\n" + "="*80)
    print("🥇 GOLD POSITION - PARTIAL PROFIT TAKING")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80 + "\n")
    
    try:
        # Initialize client
        client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=GOLD_ACCOUNT,
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        # Get current gold position
        print("📊 Fetching current gold position...")
        trades = client.get_open_trades()
        gold_trades = [t for t in trades if t['instrument'] == 'XAU_USD']
        
        if not gold_trades:
            print("❌ No gold positions found!")
            return
        
        print(f"✅ Found {len(gold_trades)} gold trade(s)\n")
        
        # Calculate total position
        total_units = sum(float(t['currentUnits']) for t in gold_trades)
        total_pl = sum(float(t['unrealizedPL']) for t in gold_trades)
        
        # Get current price
        prices = client.get_current_prices(['XAU_USD'])
        current_price = prices['XAU_USD'].bid
        
        print(f"Current Gold Position:")
        print(f"  Total Units: {total_units:,.0f}")
        print(f"  Current Price: ${current_price:,.2f}")
        print(f"  Unrealized P&L: ${total_pl:,.2f}")
        print(f"  P&L per unit: ${total_pl/total_units:.2f}\n")
        
        # Calculate units to close
        units_to_close = int(total_units * (percentage / 100))
        expected_profit = (total_pl / total_units) * units_to_close
        
        print(f"Partial Close Plan:")
        print(f"  Percentage to close: {percentage}%")
        print(f"  Units to close: {units_to_close:,}")
        print(f"  Expected profit: ${expected_profit:,.2f}")
        print(f"  Remaining units: {int(total_units - units_to_close):,}\n")
        
        # Confirm action
        print("⚠️  This will execute a LIVE trade on your DEMO account!")
        confirmation = input("Type 'YES' to confirm: ")
        
        if confirmation.upper() != 'YES':
            print("\n❌ Cancelled. No trades executed.")
            return
        
        print("\n🚀 Executing partial close...")
        
        # Close the position partially
        # For LONG positions, we SELL to close
        result = client.place_market_order(
            instrument='XAU_USD',
            units=-units_to_close  # Negative to close long position
        )
        
        print(f"✅ Order executed successfully!")
        print(f"   Order ID: {result.order_id}")
        print(f"   Units: {result.units}")
        print(f"   Status: {result.status}")
        
        # Send Telegram notification
        notifier = get_telegram_notifier()
        if notifier.enabled:
            message = f"""
🥇 <b>GOLD PROFIT TAKEN</b>

✅ Partial position closed successfully

<b>Details:</b>
• Closed: {units_to_close:,} units ({percentage}%)
• Profit: ${expected_profit:,.2f}
• Price: ${current_price:,.2f}
• Remaining: {int(total_units - units_to_close):,} units

#ProfitTaking #Gold #RiskManagement
"""
            notifier.send_message(message)
        
        print(f"\n{'='*80}")
        print(f"✅ PROFIT TAKEN SUCCESSFULLY")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def show_current_status():
    """Show current gold position without closing"""
    
    print("\n" + "="*80)
    print("🥇 GOLD POSITION - CURRENT STATUS")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80 + "\n")
    
    try:
        client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=GOLD_ACCOUNT,
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        # Get trades
        trades = client.get_open_trades()
        gold_trades = [t for t in trades if t['instrument'] == 'XAU_USD']
        
        if not gold_trades:
            print("❌ No gold positions found!")
            return
        
        # Get current price
        prices = client.get_current_prices(['XAU_USD'])
        current_price = prices['XAU_USD'].bid
        
        print(f"Current Market:")
        print(f"  Bid: ${prices['XAU_USD'].bid:,.2f}")
        print(f"  Ask: ${prices['XAU_USD'].ask:,.2f}")
        print(f"  Spread: ${prices['XAU_USD'].spread:.2f}\n")
        
        total_units = 0
        total_pl = 0
        
        print(f"Open Trades:")
        for i, trade in enumerate(gold_trades, 1):
            units = float(trade['currentUnits'])
            entry = float(trade['price'])
            pl = float(trade['unrealizedPL'])
            
            total_units += units
            total_pl += pl
            
            print(f"\n  {i}. Trade ID: {trade['id']}")
            print(f"     Units: {units:,.0f}")
            print(f"     Entry: ${entry:,.2f}")
            print(f"     P&L: ${pl:,.2f}")
            
            if 'stopLossOrder' in trade:
                sl = float(trade['stopLossOrder']['price'])
                print(f"     Stop Loss: ${sl:,.2f}")
            
            if 'takeProfitOrder' in trade:
                tp = float(trade['takeProfitOrder']['price'])
                print(f"     Take Profit: ${tp:,.2f}")
        
        print(f"\n{'─'*80}")
        print(f"Total Position:")
        print(f"  Units: {total_units:,.0f}")
        print(f"  Current Price: ${current_price:,.2f}")
        print(f"  Unrealized P&L: ${total_pl:,.2f}")
        print(f"  P&L per unit: ${total_pl/total_units:.2f}")
        print(f"  ROI: {(total_pl / (total_units * current_price)) * 100:.2f}%")
        print(f"{'─'*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'status':
            show_current_status()
        elif sys.argv[1].lower() == 'close':
            percentage = 50.0
            if len(sys.argv) > 2:
                percentage = float(sys.argv[2])
            take_partial_profit(percentage)
        else:
            print("Usage:")
            print("  python take_gold_profit.py status         # Show current position")
            print("  python take_gold_profit.py close [pct]    # Close percentage (default 50%)")
    else:
        print("\n🥇 Gold Position Management")
        print("="*80)
        print("\nOptions:")
        print("  1. Show current status")
        print("  2. Take 50% profit")
        print("  3. Take 75% profit")
        print("  4. Take 100% profit (close all)")
        print("  0. Exit")
        print()
        
        choice = input("Enter choice: ")
        
        if choice == '1':
            show_current_status()
        elif choice == '2':
            take_partial_profit(50.0)
        elif choice == '3':
            take_partial_profit(75.0)
        elif choice == '4':
            take_partial_profit(100.0)
        else:
            print("Cancelled.")






















