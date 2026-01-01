#!/usr/bin/env python3
from src.core.settings import settings
"""
Fetch ALL trades using the closed trades endpoint and update blotter
This is more reliable than the transactions endpoint
"""
import os
import sys
import json
import csv
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import pytz

# OANDA Configuration
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")
HEADERS = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}

# Account mapping
ACCOUNT_STRATEGY_MAP = {
    '101-004-30719775-005': 'all_weather_70wr',
    '101-004-30719775-006': 'gbp_rank_1',
    '101-004-30719775-007': 'gold_scalping',
    '101-004-30719775-008': 'momentum_trading',
    '101-004-30719775-009': 'gbp_rank_2',
    '101-004-30719775-010': 'gbp_rank_3',
    '101-004-30719775-011': 'dynamic_multi_pair_unified',
}

# London timezone
LONDON_TZ = pytz.timezone('Europe/London')
# Market opened this week - Monday Nov 17, 2025 at 8:00 AM London time
MARKET_OPEN = LONDON_TZ.localize(datetime(2025, 11, 17, 8, 0, 0))
MARKET_OPEN_UTC = MARKET_OPEN.astimezone(pytz.UTC)


def get_all_accounts() -> List[str]:
    """Get all OANDA accounts"""
    try:
        response = requests.get(f'{OANDA_BASE_URL}/v3/accounts', headers=HEADERS, timeout=10)
        if response.status_code == 200:
            accounts = response.json().get('accounts', [])
            return [acc['id'] for acc in accounts]
        return []
    except Exception as e:
        print(f"❌ Error fetching accounts: {e}")
        return list(ACCOUNT_STRATEGY_MAP.keys())


def fetch_closed_trades(account_id: str, count: int = 500) -> List[Dict[str, Any]]:
    """Fetch closed trades from OANDA"""
    try:
        url = f'{OANDA_BASE_URL}/v3/accounts/{account_id}/trades'
        params = {
            'state': 'CLOSED',
            'count': count
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"⚠️  Error fetching closed trades for {account_id}: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        trades = data.get('trades', [])
        
        # Filter to trades since market open
        filtered = []
        for trade in trades:
            close_time_str = trade.get('closeTime', '')
            if close_time_str:
                try:
                    close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                    if close_dt >= MARKET_OPEN_UTC:
                        filtered.append(trade)
                except:
                    pass
        
        print(f"✅ Fetched {len(trades)} total closed trades, {len(filtered)} since market open for account {account_id}")
        return filtered
    
    except Exception as e:
        print(f"❌ Error fetching closed trades for {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return []


def fetch_open_trades(account_id: str) -> List[Dict[str, Any]]:
    """Fetch open trades from OANDA"""
    try:
        url = f'{OANDA_BASE_URL}/v3/accounts/{account_id}/openTrades'
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        trades = data.get('trades', [])
        
        # Filter to trades opened since market open
        filtered = []
        for trade in trades:
            open_time_str = trade.get('openTime', '')
            if open_time_str:
                try:
                    open_dt = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
                    if open_dt >= MARKET_OPEN_UTC:
                        filtered.append(trade)
                except:
                    # Include if we can't parse
                    filtered.append(trade)
        
        print(f"✅ Fetched {len(trades)} open trades, {len(filtered)} opened since market open for account {account_id}")
        return filtered
    
    except Exception as e:
        print(f"❌ Error fetching open trades for {account_id}: {e}")
        return []


def convert_trade_to_blotter_format(trade: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """Convert OANDA trade format to blotter format"""
    instrument = trade.get('instrument', '').replace('_', '/')
    units = abs(float(trade.get('currentUnits', trade.get('initialUnits', 0))))
    side = 'BUY' if float(trade.get('currentUnits', trade.get('initialUnits', 0))) > 0 else 'SELL'
    
    entry_price = float(trade.get('price', 0))
    exit_price = float(trade.get('averageClosePrice', 0)) if trade.get('averageClosePrice') else None
    
    # Calculate price change
    price_change = None
    if exit_price:
        if side == 'BUY':
            price_change = exit_price - entry_price
        else:
            price_change = entry_price - exit_price
    
    # Calculate holding time
    holding_minutes = 0
    open_time = trade.get('openTime', '')
    close_time = trade.get('closeTime', '')
    if open_time and close_time:
        try:
            open_dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
            close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
            holding_minutes = (close_dt - open_dt).total_seconds() / 60
        except:
            pass
    
    pnl = float(trade.get('realizedPL', 0))
    
    # Determine close type
    close_type = None
    if close_time:
        # Check if it was TP or SL based on price movement
        if exit_price:
            stop_loss = float(trade.get('stopLossOrderID', 0)) if trade.get('stopLossOrderID') else None
            take_profit = float(trade.get('takeProfitOrderID', 0)) if trade.get('takeProfitOrderID') else None
            
            # Heuristic: if price moved in favor and hit TP, it's TP; otherwise SL
            if pnl > 0:
                close_type = 'TAKE_PROFIT_ORDER'
            else:
                close_type = 'STOP_LOSS_ORDER'
        else:
            close_type = 'MANUAL'
    
    return {
        'account_id': account_id,
        'instrument': instrument,
        'side': side,
        'units': units,
        'entry_ticket': str(trade.get('id', '')),
        'entry_timestamp': open_time,
        'entry_price': entry_price,
        'stop_loss': trade.get('stopLossOrderID', ''),
        'take_profit': trade.get('takeProfitOrderID', ''),
        'exit_ticket': str(trade.get('id', '')),
        'exit_timestamp': close_time if close_time else '',
        'exit_price': exit_price if exit_price else '',
        'close_type': close_type if close_type else '',
        'price_change': price_change if price_change is not None else '',
        'pnl': pnl,
        'pnl_currency': 'USD',
        'holding_minutes': round(holding_minutes, 2) if holding_minutes else ''
    }


def update_blotter_csv(account_id: str, trades: List[Dict[str, Any]], data_dir: str):
    """Update or create blotter CSV file"""
    csv_path = os.path.join(data_dir, f'blotter_{account_id}.csv')
    
    # Read existing trades if file exists
    existing_trades = {}
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry_ticket = row.get('entry_ticket', '')
                if entry_ticket:
                    existing_trades[entry_ticket] = row
    
    # Merge with new trades
    for trade in trades:
        entry_ticket = trade.get('entry_ticket', '')
        if entry_ticket and entry_ticket not in existing_trades:
            existing_trades[entry_ticket] = trade
    
    # Write updated blotter
    if existing_trades:
        fieldnames = [
            'account_id', 'instrument', 'side', 'units', 'entry_ticket', 'entry_timestamp',
            'entry_price', 'stop_loss', 'take_profit', 'exit_ticket', 'exit_timestamp',
            'exit_price', 'close_type', 'price_change', 'pnl', 'pnl_currency', 'holding_minutes'
        ]
        
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Sort by entry timestamp
            sorted_trades = sorted(existing_trades.values(), key=lambda x: x.get('entry_timestamp', ''))
            
            for trade in sorted_trades:
                writer.writerow(trade)
        
        print(f"✅ Updated blotter CSV: {csv_path} ({len(existing_trades)} trades)")
    else:
        print(f"⚠️  No trades to write for account {account_id}")


def main():
    """Main execution"""
    print("=" * 80)
    print("FETCHING ALL TRADES FROM OANDA API (CLOSED TRADES ENDPOINT)")
    print("Market opened: Monday Nov 17, 2025 8:00 AM London time")
    print("=" * 80)
    
    # Determine data directory
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 'google-cloud-trading-system', 'data'),
        os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'data'),
        '/opt/quant_system_clean/google-cloud-trading-system/data',
        os.path.join(os.path.dirname(__file__), 'data'),
    ]
    
    data_dir = None
    for path in possible_paths:
        if os.path.exists(path):
            data_dir = path
            break
    
    if not data_dir:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
    
    print(f"📁 Using data directory: {data_dir}")
    
    # Get all accounts
    accounts = get_all_accounts()
    print(f"📊 Found {len(accounts)} accounts")
    
    # Fetch trades for each account
    all_trades_by_account = {}
    total_trades = 0
    
    for account_id in accounts:
        print(f"\n{'='*80}")
        print(f"Processing account: {account_id}")
        print(f"{'='*80}")
        
        # Fetch closed trades
        closed_trades = fetch_closed_trades(account_id)
        
        # Fetch open trades
        open_trades = fetch_open_trades(account_id)
        
        # Convert to blotter format
        all_trades = []
        for trade in closed_trades:
            blotter_trade = convert_trade_to_blotter_format(trade, account_id)
            all_trades.append(blotter_trade)
        
        for trade in open_trades:
            blotter_trade = convert_trade_to_blotter_format(trade, account_id)
            all_trades.append(blotter_trade)
        
        all_trades_by_account[account_id] = all_trades
        total_trades += len(all_trades)
        
        print(f"📈 Found {len(all_trades)} total trades for account {account_id} ({len(closed_trades)} closed, {len(open_trades)} open)")
        
        # Update blotter CSV
        if all_trades:
            update_blotter_csv(account_id, all_trades, data_dir)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Total accounts processed: {len(accounts)}")
    print(f"✅ Total trades found: {total_trades}")
    print(f"✅ Blotter files updated in: {data_dir}")
    print(f"{'='*80}")
    
    # Per-account summary
    for account_id, trades in all_trades_by_account.items():
        if not trades:
            continue
        
        closed = [t for t in trades if t.get('exit_timestamp')]
        open_trades = [t for t in trades if not t.get('exit_timestamp')]
        total_pnl = sum(float(t.get('pnl', 0)) for t in closed)
        wins = sum(1 for t in closed if float(t.get('pnl', 0)) > 0)
        losses = sum(1 for t in closed if float(t.get('pnl', 0)) < 0)
        
        print(f"\nAccount {account_id}:")
        print(f"  Total trades: {len(trades)}")
        print(f"  Closed: {len(closed)}")
        print(f"  Open: {len(open_trades)}")
        if closed:
            print(f"  P&L: {total_pnl:.2f} USD")
            print(f"  Wins: {wins} | Losses: {losses}")
            print(f"  Win Rate: {(wins/len(closed)*100):.1f}%")


if __name__ == '__main__':
    main()

