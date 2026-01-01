#!/usr/bin/env python3
from src.core.settings import settings
"""
BRUTAL HONESTY: Fetch ALL trades from OANDA API and update blotter
This script will:
1. Fetch ALL transactions from OANDA for all accounts
2. Extract all trade fills and closes
3. Update the blotter files with complete trade history
4. Report any discrepancies
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


def fetch_all_transactions(account_id: str) -> List[Dict[str, Any]]:
    """Fetch ALL transactions from OANDA for an account"""
    all_transactions = []
    page_size = 500
    max_pages = 50  # Safety limit
    
    try:
        # Fetch from last 7 days to catch all trades
        since_time = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
        
        url = f'{OANDA_BASE_URL}/v3/accounts/{account_id}/transactions'
        params = {
            'since': since_time,
            'pageSize': page_size
        }
        
        page_count = 0
        last_id = None
        
        while page_count < max_pages:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️  Error fetching transactions for {account_id}: {response.status_code} - {response.text[:200]}")
                break
            
            data = response.json()
            transactions = data.get('transactions', [])
            
            if not transactions:
                break
            
            all_transactions.extend(transactions)
            
            # Check for pagination - use lastTransactionID from response
            if 'lastTransactionID' in data:
                new_last_id = data['lastTransactionID']
                if new_last_id == last_id:
                    break  # No more pages
                last_id = new_last_id
                params['id'] = new_last_id
            else:
                break
            
            page_count += 1
        
        # Filter to trades since market open
        filtered = []
        for tx in all_transactions:
            tx_time = tx.get('time', '')
            if tx_time:
                try:
                    tx_dt = datetime.fromisoformat(tx_time.replace('Z', '+00:00'))
                    if tx_dt >= MARKET_OPEN_UTC:
                        filtered.append(tx)
                except:
                    # Include if we can't parse (better safe than sorry)
                    filtered.append(tx)
        
        print(f"✅ Fetched {len(all_transactions)} total transactions, {len(filtered)} since market open for account {account_id}")
        return filtered
    
    except Exception as e:
        print(f"❌ Error fetching transactions for {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return []


def parse_trade_from_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse complete trade information from transactions"""
    trades = []
    trade_map = {}  # Map trade_id to trade info
    
    # First pass: collect all ORDER_FILL and TRADE_CLOSE events
    for tx in transactions:
        tx_type = tx.get('type', '')
        tx_time = tx.get('time', '')
        
        if tx_type == 'ORDER_FILL':
            # This is a trade entry
            trade_id = str(tx.get('tradeOpened', {}).get('tradeID', ''))
            if not trade_id:
                continue
            
            instrument = tx.get('instrument', '')
            units = float(tx.get('units', 0))
            price = float(tx.get('price', 0))
            pl = float(tx.get('pl', 0))
            
            trade_map[trade_id] = {
                'trade_id': trade_id,
                'instrument': instrument,
                'entry_timestamp': tx_time,
                'entry_price': price,
                'units': abs(units),
                'side': 'BUY' if units > 0 else 'SELL',
                'entry_ticket': tx.get('id', ''),
                'stop_loss': None,
                'take_profit': None,
                'exit_timestamp': None,
                'exit_price': None,
                'exit_ticket': None,
                'close_type': None,
                'pnl': 0.0,
                'status': 'OPEN'
            }
            
            # Check for stop loss and take profit in the order
            if 'stopLossOrderID' in tx:
                trade_map[trade_id]['stop_loss'] = float(tx.get('stopLossOnFill', {}).get('price', 0))
            if 'takeProfitOrderID' in tx:
                trade_map[trade_id]['take_profit'] = float(tx.get('takeProfitOnFill', {}).get('price', 0))
        
        elif tx_type in ['TRADE_CLOSE', 'TAKE_PROFIT_ORDER_FILLED', 'STOP_LOSS_ORDER_FILLED']:
            # This is a trade exit
            trade_closed = tx.get('tradeClosed', {})
            trade_id = str(trade_closed.get('tradeID', ''))
            
            if trade_id in trade_map:
                trade_map[trade_id]['exit_timestamp'] = tx_time
                trade_map[trade_id]['exit_price'] = float(trade_closed.get('price', 0))
                trade_map[trade_id]['exit_ticket'] = tx.get('id', '')
                trade_map[trade_id]['pnl'] = float(tx.get('pl', 0))
                trade_map[trade_id]['status'] = 'CLOSED'
                
                if tx_type == 'TAKE_PROFIT_ORDER_FILLED':
                    trade_map[trade_id]['close_type'] = 'TAKE_PROFIT_ORDER'
                elif tx_type == 'STOP_LOSS_ORDER_FILLED':
                    trade_map[trade_id]['close_type'] = 'STOP_LOSS_ORDER'
                else:
                    trade_map[trade_id]['close_type'] = 'MANUAL'
    
    # Convert to list
    for trade_id, trade in trade_map.items():
        trades.append(trade)
    
    return trades


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
            
            for trade in existing_trades.values():
                # Calculate price change and holding time
                entry_price = float(trade.get('entry_price', 0))
                exit_price = float(trade.get('exit_price', 0))
                price_change = exit_price - entry_price if exit_price else 0
                
                entry_ts = trade.get('entry_timestamp', '')
                exit_ts = trade.get('exit_timestamp', '')
                holding_minutes = 0
                if entry_ts and exit_ts:
                    try:
                        entry_dt = datetime.fromisoformat(entry_ts.replace('Z', '+00:00'))
                        exit_dt = datetime.fromisoformat(exit_ts.replace('Z', '+00:00'))
                        holding_minutes = (exit_dt - entry_dt).total_seconds() / 60
                    except:
                        pass
                
                # Format instrument name
                instrument = trade.get('instrument', '').replace('_', '/')
                
                row = {
                    'account_id': account_id,
                    'instrument': instrument,
                    'side': trade.get('side', ''),
                    'units': trade.get('units', 0),
                    'entry_ticket': trade.get('entry_ticket', ''),
                    'entry_timestamp': entry_ts,
                    'entry_price': entry_price,
                    'stop_loss': trade.get('stop_loss', ''),
                    'take_profit': trade.get('take_profit', ''),
                    'exit_ticket': trade.get('exit_ticket', ''),
                    'exit_timestamp': exit_ts,
                    'exit_price': exit_price if exit_price else '',
                    'close_type': trade.get('close_type', ''),
                    'price_change': price_change if price_change else '',
                    'pnl': trade.get('pnl', 0),
                    'pnl_currency': 'USD',
                    'holding_minutes': round(holding_minutes, 2) if holding_minutes else ''
                }
                writer.writerow(row)
        
        print(f"✅ Updated blotter CSV: {csv_path} ({len(existing_trades)} trades)")


def update_live_trade_blotter_json(trades_by_account: Dict[str, List[Dict[str, Any]]], data_dir: str):
    """Update the main live_trade_blotter.json file"""
    json_path = os.path.join(data_dir, 'live_trade_blotter_trades.json')
    
    all_trades = []
    for account_id, trades in trades_by_account.items():
        for trade in trades:
            trade['account_id'] = account_id
            trade['strategy'] = ACCOUNT_STRATEGY_MAP.get(account_id, 'unknown')
            all_trades.append(trade)
    
    # Sort by entry timestamp
    all_trades.sort(key=lambda x: x.get('entry_timestamp', ''))
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_trades, f, indent=2, default=str)
    
    print(f"✅ Updated live trade blotter JSON: {json_path} ({len(all_trades)} trades)")


def main():
    """Main execution"""
    print("=" * 80)
    print("FETCHING ALL TRADES FROM OANDA API")
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
        
        # Fetch all transactions
        transactions = fetch_all_transactions(account_id)
        
        # Parse trades
        trades = parse_trade_from_transactions(transactions)
        all_trades_by_account[account_id] = trades
        total_trades += len(trades)
        
        print(f"📈 Found {len(trades)} trades for account {account_id}")
        
        # Update blotter CSV
        update_blotter_csv(account_id, trades, data_dir)
    
    # Update main JSON blotter
    update_live_trade_blotter_json(all_trades_by_account, data_dir)
    
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
        closed = [t for t in trades if t.get('status') == 'CLOSED']
        open_trades = [t for t in trades if t.get('status') == 'OPEN']
        total_pnl = sum(float(t.get('pnl', 0)) for t in closed)
        wins = sum(1 for t in closed if float(t.get('pnl', 0)) > 0)
        losses = sum(1 for t in closed if float(t.get('pnl', 0)) < 0)
        
        print(f"\nAccount {account_id}:")
        print(f"  Total trades: {len(trades)}")
        print(f"  Closed: {len(closed)}")
        print(f"  Open: {len(open_trades)}")
        print(f"  P&L: {total_pnl:.2f} USD")
        print(f"  Wins: {wins} | Losses: {losses}")
        if closed:
            print(f"  Win Rate: {(wins/len(closed)*100):.1f}%")


if __name__ == '__main__':
    main()

