#!/usr/bin/env python3
"""
Send Comprehensive Market Overview and Account Snapshot to Telegram
"""
import os
import sys
import yaml
import requests
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv('oanda_config.env')

from src.core.oanda_client import OandaClient

# Telegram config (env only)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram(message):
    """Send message to Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set in environment")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        # Try with data= first (form-encoded), then json=
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            return True
        # If that fails, try with json=
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram: {e}")
        return False

def load_accounts():
    """Load accounts from accounts.yaml"""
    try:
        config_path = Path(__file__).parent / 'accounts.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('accounts', [])
    except Exception as e:
        print(f"Error loading accounts: {e}")
        return []

def get_market_data(client, instruments):
    """Get current market prices"""
    try:
        prices = client.get_current_prices(instruments)
        market_data = {}
        for instrument, price_obj in prices.items():
            if price_obj:
                market_data[instrument] = {
                    'bid': price_obj.bid,
                    'ask': price_obj.ask,
                    'mid': (price_obj.bid + price_obj.ask) / 2,
                    'spread': price_obj.ask - price_obj.bid,
                    'spread_pips': (price_obj.ask - price_obj.bid) * 10000 if not instrument.endswith('JPY') else (price_obj.ask - price_obj.bid) * 100
                }
        return market_data
    except Exception as e:
        print(f"Error getting market data: {e}")
        return {}

def get_account_status(client):
    """Get account status"""
    try:
        account_info = client.get_account_info()
        open_trades = client.get_open_trades()
        positions_dict = client.get_positions()
        
        # Calculate total P&L
        total_unrealized = account_info.unrealized_pl
        total_realized = account_info.realized_pl
        total_pl = total_unrealized + total_realized
        
        # Get position details (positions_dict is a dict, not a list)
        position_details = []
        for instrument, pos in positions_dict.items():
            if pos.long_units != 0 or pos.short_units != 0:
                side = "LONG" if pos.long_units > 0 else "SHORT"
                units = abs(pos.long_units) if pos.long_units != 0 else abs(pos.short_units)
                position_details.append({
                    'instrument': instrument,
                    'side': side,
                    'units': units,
                    'unrealized_pl': pos.unrealized_pl
                })
        
        return {
            'balance': account_info.balance,
            'currency': account_info.currency,
            'unrealized_pl': total_unrealized,
            'realized_pl': total_realized,
            'total_pl': total_pl,
            'pl_percentage': (total_pl / account_info.balance * 100) if account_info.balance > 0 else 0,
            'margin_used': account_info.margin_used,
            'margin_available': account_info.margin_available,
            'open_trades': account_info.open_trade_count,
            'open_positions': account_info.open_position_count,
            'position_details': position_details
        }
    except Exception as e:
        print(f"Error getting account status: {e}")
        return {'error': str(e)}

def format_currency(value, currency='USD'):
    """Format currency value"""
    if currency == 'USD' or currency == 'GBP':
        return f"${value:,.2f}" if currency == 'USD' else f"£{value:,.2f}"
    return f"{value:,.2f} {currency}"

def main():
    """Main function"""
    print("="*80)
    print("📊 COMPREHENSIVE MARKET & ACCOUNT SNAPSHOT")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} London")
    print("="*80)
    
    # Load accounts
    accounts_config = load_accounts()
    active_accounts = [acc for acc in accounts_config if acc.get('active', False)]
    
    if not active_accounts:
        print("❌ No active accounts found")
        return
    
    print(f"\n✅ Found {len(active_accounts)} active accounts")
    
    # Initialize OANDA client (use first account for market data)
    api_key = os.getenv('OANDA_API_KEY')
    environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
    first_account_id = active_accounts[0]['id']
    
    # Get all unique instruments
    all_instruments = set()
    for acc in active_accounts:
        all_instruments.update(acc.get('instruments', []))
    
    all_instruments = sorted(list(all_instruments))
    print(f"📈 Getting market data for {len(all_instruments)} instruments...")
    
    # Get market data
    market_client = OandaClient(api_key=api_key, account_id=first_account_id, environment=environment)
    market_data = get_market_data(market_client, all_instruments)
    
    # Get account statuses
    print(f"\n💰 Getting status for {len(active_accounts)} accounts...")
    account_statuses = {}
    
    for acc_config in active_accounts:
        account_id = acc_config['id']
        account_name = acc_config.get('display_name', acc_config.get('name', 'Unknown'))
        strategy = acc_config.get('strategy', 'unknown')
        
        try:
            client = OandaClient(api_key=api_key, account_id=account_id, environment=environment)
            status = get_account_status(client)
            account_statuses[account_id] = {
                'name': account_name,
                'strategy': strategy,
                'status': status
            }
            print(f"✅ {account_name}: Balance {format_currency(status.get('balance', 0), status.get('currency', 'USD'))}")
        except Exception as e:
            print(f"❌ Error getting status for {account_name}: {e}")
            account_statuses[account_id] = {
                'name': account_name,
                'strategy': strategy,
                'status': {'error': str(e)}
            }
    
    # Build Telegram message
    now = datetime.now()
    message = f"""📊 <b>MARKET OVERVIEW & ACCOUNT SNAPSHOT</b>
⏰ {now.strftime('%Y-%m-%d %H:%M:%S')} London

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 <b>MARKET PRICES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Market data section
    for instrument in sorted(market_data.keys()):
        data = market_data[instrument]
        mid = data['mid']
        spread_pips = data['spread_pips']
        
        # Format price based on instrument
        if instrument == 'XAU_USD':
            price_str = f"${mid:,.2f}"
        elif instrument.endswith('JPY'):
            price_str = f"{mid:.3f}"
        else:
            price_str = f"{mid:.5f}"
        
        message += f"• <b>{instrument.replace('_', '/')}:</b> {price_str} (Spread: {spread_pips:.1f} pips)\n"
    
    # Account summary
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>ACCOUNT SUMMARY</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    total_balance = 0
    total_unrealized = 0
    total_realized = 0
    total_positions = 0
    
    for account_id, acc_data in account_statuses.items():
        name = acc_data['name']
        strategy = acc_data['strategy']
        status = acc_data['status']
        
        if 'error' in status:
            message += f"\n❌ <b>{name}</b> ({strategy})\n   Error: {status['error']}\n"
            continue
        
        balance = status.get('balance', 0)
        currency = status.get('currency', 'USD')
        unrealized = status.get('unrealized_pl', 0)
        realized = status.get('realized_pl', 0)
        total_pl = status.get('total_pl', 0)
        pl_pct = status.get('pl_percentage', 0)
        open_positions = status.get('open_positions', 0)
        position_details = status.get('position_details', [])
        
        total_balance += balance
        total_unrealized += unrealized
        total_realized += realized
        total_positions += open_positions
        
        # P&L emoji
        pl_emoji = "🟢" if total_pl >= 0 else "🔴"
        
        message += f"""
{pl_emoji} <b>{name}</b> ({strategy})
   Balance: {format_currency(balance, currency)}
   Unrealized P&L: {format_currency(unrealized, currency)} ({unrealized/balance*100 if balance > 0 else 0:+.2f}%)
   Realized P&L: {format_currency(realized, currency)}
   Total P&L: {format_currency(total_pl, currency)} ({pl_pct:+.2f}%)
   Open Positions: {open_positions}
"""
        
        # Show position details
        if position_details:
            message += "   Positions:\n"
            for pos in position_details[:5]:  # Show max 5 positions
                pos_emoji = "📈" if pos['unrealized_pl'] >= 0 else "📉"
                message += f"   {pos_emoji} {pos['instrument']} {pos['side']}: {format_currency(pos['unrealized_pl'], currency)}\n"
            if len(position_details) > 5:
                message += f"   ... and {len(position_details) - 5} more\n"
    
    # Portfolio totals
    total_pl_all = total_unrealized + total_realized
    total_pl_pct = (total_pl_all / total_balance * 100) if total_balance > 0 else 0
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>PORTFOLIO TOTALS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Balance: {format_currency(total_balance, 'USD')}
Total Unrealized P&L: {format_currency(total_unrealized, 'USD')}
Total Realized P&L: {format_currency(total_realized, 'USD')}
Total P&L: {format_currency(total_pl_all, 'USD')} ({total_pl_pct:+.2f}%)
Total Open Positions: {total_positions}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#MarketSnapshot #AccountStatus
"""
    
    # Send message
    print(f"\n📱 Sending to Telegram...")
    if send_telegram(message):
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
