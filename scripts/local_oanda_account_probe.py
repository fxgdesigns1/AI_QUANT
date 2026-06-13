#!/usr/bin/env python3
"""
Local OANDA Account Probe
Reusable script to verify OANDA credentials and retrieve account info.
Loads credentials from .env automatically - no arguments needed.

Usage:
    python3 scripts/local_oanda_account_probe.py                    # Check default account from .env
    python3 scripts/local_oanda_account_probe.py 001 002 003        # Check specific account suffixes
"""

from dotenv import load_dotenv
import os
import requests
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

# Load .env automatically from project root
load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY')
BASE_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
ACCOUNT_ID_PREFIX = os.getenv('ACCOUNT_ID_PREFIX')
ACCOUNT_SUFFIX_ALLOWLIST = os.getenv('ACCOUNT_SUFFIX_ALLOWLIST', '')
ENV = os.getenv('OANDA_ENV', 'practice')

if not API_KEY:
    print("❌ ERROR: Missing OANDA_API_KEY in .env", file=sys.stderr)
    sys.exit(1)

BASE_URL = 'https://api-fxpractice.oanda.com/v3' if ENV == 'practice' else 'https://api-fxtrade.oanda.com/v3'

HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

def get(endpoint, params=None):
    """Make GET request to OANDA API."""
    r = requests.get(f'{BASE_URL}{endpoint}', headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def get_account_id_from_suffix(suffix: str) -> str:
    """Convert account suffix (e.g., '001') to full account ID."""
    if ACCOUNT_ID_PREFIX:
        # Use ACCOUNT_ID_PREFIX if available
        return f"{ACCOUNT_ID_PREFIX}{suffix.zfill(3)}"
    elif BASE_ACCOUNT_ID:
        # Replace last 3 digits with suffix
        base = BASE_ACCOUNT_ID[:-3]
        return f"{base}{suffix.zfill(3)}"
    else:
        # If no base account ID, assume full ID format
        return suffix

def get_account_list() -> List[str]:
    """Get list of account IDs from environment configuration."""
    if ACCOUNT_ID_PREFIX and ACCOUNT_SUFFIX_ALLOWLIST:
        # Use ACCOUNT_ID_PREFIX + ACCOUNT_SUFFIX_ALLOWLIST
        suffixes = [s.strip() for s in ACCOUNT_SUFFIX_ALLOWLIST.split(',') if s.strip()]
        return [f"{ACCOUNT_ID_PREFIX}{s.zfill(3)}" for s in suffixes]
    elif BASE_ACCOUNT_ID:
        # Use single OANDA_ACCOUNT_ID
        return [BASE_ACCOUNT_ID]
    else:
        return []

def fetch_closed_trades(account_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch closed trades from OANDA API using transactions endpoint.
    
    The /trades endpoint only returns OPEN trades. Closed trades must be found
    via transactions with types: TRADE_CLOSE, TAKE_PROFIT_ORDER_FILLED, STOP_LOSS_ORDER_FILLED
    or ORDER_FILL transactions with non-zero PL (realized profit/loss).
    
    Note: If no transactions found in the time window, we try a longer window (7 days)
    to find historical closed trades.
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace('+00:00', 'Z')
        
        # Get transactions from last N hours
        transactions = get(f'/accounts/{account_id}/transactions', params={'since': since, 'count': 500})
        all_transactions = transactions.get('transactions', [])
        
        # If no transactions in requested window and we're looking for 24h, try 30 days
        if not all_transactions and hours <= 24:
            since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace('+00:00', 'Z')
            try:
                transactions_30d = get(f'/accounts/{account_id}/transactions', params={'since': since_30d, 'count': 500})
                all_transactions = transactions_30d.get('transactions', [])
            except:
                pass
        
        # Closed trade transaction types
        close_types = ['TRADE_CLOSE', 'TAKE_PROFIT_ORDER_FILLED', 'STOP_LOSS_ORDER_FILLED']
        
        closed_trades = []
        seen_trade_ids = set()
        
        for tx in all_transactions:
            tx_type = tx.get('type', '')
            
            # Check for explicit close transaction types
            if tx_type in close_types:
                trade_closed = tx.get('tradeClosed', {})
                if trade_closed:
                    trade_id = str(trade_closed.get('tradeID', ''))
                    if trade_id and trade_id not in seen_trade_ids:
                        # Build closed trade record from transaction
                        closed_trade = {
                            'id': trade_id,
                            'instrument': trade_closed.get('instrument', ''),
                            'units': trade_closed.get('units', '0'),
                            'price': trade_closed.get('price', '0'),
                            'realizedPL': tx.get('pl', '0'),
                            'closeTime': tx.get('time', ''),
                            'closeType': tx_type,
                            'transactionID': tx.get('id', '')
                        }
                        closed_trades.append(closed_trade)
                        seen_trade_ids.add(trade_id)
            
            # Also check for ORDER_FILL with non-zero PL (indicates closed trade)
            elif tx_type == 'ORDER_FILL':
                pl = float(tx.get('pl', 0))
                if pl != 0:  # Non-zero PL means this closed a trade
                    # Check if this transaction has tradeClosed info
                    trade_closed = tx.get('tradeClosed', {})
                    if trade_closed:
                        trade_id = str(trade_closed.get('tradeID', ''))
                        if trade_id and trade_id not in seen_trade_ids:
                            closed_trade = {
                                'id': trade_id,
                                'instrument': trade_closed.get('instrument', tx.get('instrument', '')),
                                'units': trade_closed.get('units', tx.get('units', '0')),
                                'price': trade_closed.get('price', tx.get('price', '0')),
                                'realizedPL': str(pl),
                                'closeTime': tx.get('time', ''),
                                'closeType': 'ORDER_FILL',
                                'transactionID': tx.get('id', '')
                            }
                            closed_trades.append(closed_trade)
                            seen_trade_ids.add(trade_id)
        
        # Sort by close time (most recent first)
        closed_trades.sort(key=lambda x: x.get('closeTime', ''), reverse=True)
        
        return closed_trades
    except Exception as e:
        # Don't print error to stderr in production, but log it
        return []

def compute_closed_trade_stats(closed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute win rate and statistics from closed trades."""
    if not closed_trades:
        return {
            'closed_trades': 0,
            'wins': 0,
            'losses': 0,
            'breakeven': 0,
            'win_rate_pct': None,
            'realized_pl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
    
    wins = []
    losses = []
    breakeven = []
    total_realized_pl = 0.0
    
    for trade in closed_trades:
        realized_pl = float(trade.get('realizedPL', 0))
        total_realized_pl += realized_pl
        
        if realized_pl > 0:
            wins.append(realized_pl)
        elif realized_pl < 0:
            losses.append(realized_pl)
        else:
            breakeven.append(realized_pl)
    
    total = len(wins) + len(losses) + len(breakeven)
    win_rate = (len(wins) / total * 100) if total > 0 else None
    
    return {
        'closed_trades': total,
        'wins': len(wins),
        'losses': len(losses),
        'breakeven': len(breakeven),
        'win_rate_pct': win_rate,
        'realized_pl': total_realized_pl,
        'avg_win': sum(wins) / len(wins) if wins else 0.0,
        'avg_loss': sum(losses) / len(losses) if losses else 0.0
    }

def probe_account(account_id: str, include_24h: bool = True) -> Dict[str, Any]:
    """Probe a single OANDA account and return all data."""
    result = {
        'account_id': account_id,
        'success': False,
        'error': None,
        'summary': None,
        'trades': None,
        'open_trades': None,
        'closed_trades_24h': None,
        'closed_trade_stats': None,
        'positions': None,
        'transactions_24h': None,
        'orders_24h': None
    }
    
    try:
        # Get account summary
        summary = get(f'/accounts/{account_id}/summary')
        result['summary'] = summary['account']
        
        # Get all trades (includes both open and closed)
        trades = get(f'/accounts/{account_id}/trades')
        all_trades = trades.get('trades', [])
        
        # Separate open and closed trades
        open_trades = [t for t in all_trades if t.get('state') != 'CLOSED']
        result['trades'] = all_trades
        result['open_trades'] = open_trades
        
        # Get closed trades - try 24h first, then 7 days if none found
        if include_24h:
            closed_trades_24h = fetch_closed_trades(account_id, hours=24)
            # If no closed trades in 24h, try 7 days (168 hours)
            if not closed_trades_24h:
                closed_trades_24h = fetch_closed_trades(account_id, hours=168)
            result['closed_trades_24h'] = closed_trades_24h
            result['closed_trade_stats'] = compute_closed_trade_stats(closed_trades_24h)
        
        # Get open positions
        positions = get(f'/accounts/{account_id}/positions')
        result['positions'] = positions.get('positions', [])
        
        # Get 24-hour transactions if requested
        if include_24h:
            since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat().replace('+00:00', 'Z')
            transactions = get(f'/accounts/{account_id}/transactions', params={'since': since, 'count': 500})
            result['transactions_24h'] = transactions.get('transactions', [])
            
            # Also try getting transactions without time filter to see if there are any at all
            if not result['transactions_24h']:
                try:
                    all_tx = get(f'/accounts/{account_id}/transactions', params={'count': 500})
                    result['all_transactions_sample'] = len(all_tx.get('transactions', []))
                except:
                    pass
            
            # Get orders from last 24 hours
            orders = get(f'/accounts/{account_id}/orders', params={'since': since, 'count': 500})
            result['orders_24h'] = orders.get('orders', [])
        
        result['success'] = True
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            result['error'] = 'Invalid API key (401 Unauthorized)'
        elif e.response.status_code == 404:
            result['error'] = 'Account ID not found (404 Not Found)'
        else:
            result['error'] = f'HTTP {e.response.status_code}: {e.response.text[:200]}'
        return result
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {str(e)}'
        return result

def format_transaction(tx: Dict[str, Any]) -> str:
    """Format a transaction for display."""
    tx_type = tx.get('type', 'UNKNOWN')
    time_str = tx.get('time', '')[:19].replace('T', ' ')
    
    if tx_type == 'ORDER_FILL':
        instrument = tx.get('instrument', 'N/A')
        units = tx.get('units', '0')
        price = tx.get('price', '0')
        pl = tx.get('pl', '0')
        return f"   {time_str} | {tx_type} | {instrument} {units} @ {price} | P&L: {pl}"
    else:
        return f"   {time_str} | {tx_type} | {tx.get('instrument', 'N/A')}"

class TeeOutput:
    """Write to both console and file."""
    def __init__(self, file_path):
        self.console = sys.stdout
        self.file = open(file_path, 'w', encoding='utf-8')
    
    def write(self, text):
        self.console.write(text)
        self.file.write(text)
        self.file.flush()
    
    def flush(self):
        self.console.flush()
        self.file.flush()
    
    def close(self):
        self.file.close()

def display_account_data(data: Dict[str, Any]):
    """Display formatted account data."""
    account_id = data['account_id']
    
    print(f"\n{'='*70}")
    print(f"📊 ACCOUNT: {account_id}")
    print(f"{'='*70}")
    
    if not data['success']:
        print(f"❌ ERROR: {data['error']}")
        return
    
    summary = data['summary']
    print(f"\n💰 ACCOUNT SUMMARY")
    print(f"   Balance: {summary['balance']} {summary['currency']}")
    print(f"   NAV: {summary['NAV']} {summary['currency']}")
    print(f"   Unrealized P&L: {summary.get('unrealizedPL', '0')} {summary['currency']}")
    print(f"   Margin Used: {summary.get('marginUsed', '0')} {summary['currency']}")
    print(f"   Margin Available: {summary.get('marginAvailable', '0')} {summary['currency']}")
    
    # CLOSED TRADES STATISTICS - Most Important
    if data.get('closed_trade_stats'):
        stats = data['closed_trade_stats']
        closed_trades = data.get('closed_trades_24h', [])
        # Determine time window based on oldest closed trade
        if closed_trades:
            oldest_time = min(t.get('closeTime', '') for t in closed_trades if t.get('closeTime'))
            print(f"\n🎯 CLOSED TRADES - WIN RATE ANALYSIS")
        else:
            print(f"\n🎯 CLOSED TRADES (SEARCHED 24H + 7D) - WIN RATE ANALYSIS")
            transactions_count = len(data.get('transactions_24h', []))
            all_tx_count = data.get('all_transactions_sample', 0)
            if transactions_count == 0 and all_tx_count == 0:
                print(f"   ⚠️  WARNING: No transactions found in API response")
                print(f"   💡 Possible reasons:")
                print(f"      - Closed trades may be older than 7 days")
                print(f"      - Practice account may have limited transaction history")
                print(f"      - API may require different authentication/parameters")
        print(f"   Closed Trades Found: {stats['closed_trades']}")
        print(f"   Wins: {stats['wins']} | Losses: {stats['losses']} | Breakeven: {stats['breakeven']}")
        if stats['win_rate_pct'] is not None:
            print(f"   Win Rate: {stats['win_rate_pct']:.2f}%")
        else:
            print(f"   Win Rate: N/A (no closed trades found in searched period)")
        print(f"   Realized P&L: {stats['realized_pl']:.2f} {summary['currency']}")
        if stats['wins'] > 0:
            print(f"   Avg Win: {stats['avg_win']:.2f} {summary['currency']}")
        if stats['losses'] > 0:
            print(f"   Avg Loss: {stats['avg_loss']:.2f} {summary['currency']}")
        
        # Show recent closed trades
        closed_trades = data.get('closed_trades_24h', [])
        if closed_trades:
            print(f"\n   Recent Closed Trades:")
            for trade in sorted(closed_trades, key=lambda x: x.get('closeTime', ''), reverse=True)[:10]:
                instrument = trade.get('instrument', 'N/A')
                units = trade.get('initialUnits', trade.get('currentUnits', '0'))
                realized_pl = float(trade.get('realizedPL', 0))
                close_time = trade.get('closeTime', '')[:19].replace('T', ' ')
                result_icon = "✅" if realized_pl > 0 else "❌" if realized_pl < 0 else "➖"
                print(f"      {result_icon} {close_time} | {instrument} {units} units | P&L: {realized_pl:.2f}")
            if len(closed_trades) > 10:
                print(f"      ... and {len(closed_trades) - 10} more")
    
    # Open Trades
    open_trades = data.get('open_trades', data.get('trades', []))
    print(f"\n📈 OPEN TRADES: {len(open_trades)}")
    if open_trades:
        for trade in open_trades:
            if trade.get('state') != 'CLOSED':  # Double-check
                print(f"   - {trade['instrument']} {trade.get('currentUnits', trade.get('initialUnits', '0'))} units")
                print(f"     ID: {trade['id']} | Open: {trade.get('openTime', '')[:19]}")
                print(f"     Price: {trade.get('price', 'N/A')} | Unrealized P&L: {trade.get('unrealizedPL', '0')}")
    else:
        print("   (No open trades)")
    
    # Open Positions
    positions = data['positions']
    active_positions = [p for p in positions if float(p['long']['units']) != 0 or float(p['short']['units']) != 0]
    print(f"\n📊 OPEN POSITIONS: {len(active_positions)}")
    if active_positions:
        for pos in active_positions:
            long_units = pos['long']['units']
            short_units = pos['short']['units']
            print(f"   - {pos['instrument']}: Long {long_units}, Short {short_units}")
            print(f"     Unrealized P&L: {pos.get('unrealizedPL', '0')}")
    else:
        print("   (No open positions)")
    
    # 24-Hour Transactions
    if data['transactions_24h'] is not None:
        transactions = data['transactions_24h']
        order_fills = [tx for tx in transactions if tx.get('type') == 'ORDER_FILL']
        total_pnl = sum(float(tx.get('pl', 0)) for tx in order_fills)
        
        print(f"\n🕐 LAST 24 HOURS - TRANSACTIONS")
        print(f"   Total Transactions: {len(transactions)}")
        print(f"   Order Fills: {len(order_fills)}")
        print(f"   Realized P&L: {total_pnl:.2f} {summary['currency']}")
        
        if order_fills:
            print(f"\n   Recent Order Fills:")
            for tx in sorted(order_fills, key=lambda x: x.get('time', ''), reverse=True)[:10]:
                print(format_transaction(tx))
            if len(order_fills) > 10:
                print(f"   ... and {len(order_fills) - 10} more")
        
        # Show other transaction types
        other_txs = [tx for tx in transactions if tx.get('type') != 'ORDER_FILL']
        if other_txs:
            print(f"\n   Other Transactions ({len(other_txs)}):")
            for tx in sorted(other_txs, key=lambda x: x.get('time', ''), reverse=True)[:5]:
                print(format_transaction(tx))
    
    # 24-Hour Orders
    if data['orders_24h'] is not None:
        orders = data['orders_24h']
        print(f"\n📋 LAST 24 HOURS - ORDERS")
        print(f"   Total Orders: {len(orders)}")
        if orders:
            for order in sorted(orders, key=lambda x: x.get('createTime', ''), reverse=True)[:5]:
                order_type = order.get('type', 'UNKNOWN')
                instrument = order.get('instrument', 'N/A')
                units = order.get('units', '0')
                state = order.get('state', 'UNKNOWN')
                time_str = order.get('createTime', '')[:19].replace('T', ' ')
                print(f"   {time_str} | {order_type} | {instrument} {units} | State: {state}")

def main():
    """Probe OANDA account(s) and display comprehensive info."""
    # Create logs directory if it doesn't exist
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f'OANDA_ACCOUNT_PROBE_{timestamp}.log'
    json_file = logs_dir / f'OANDA_ACCOUNT_PROBE_{timestamp}.json'
    
    # Redirect output to both console and log file
    tee = TeeOutput(log_file)
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = tee
    sys.stderr = tee
    
    try:
        print(f"🔍 OANDA Account Probe - 24 Hour Analysis")
        print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"   Environment: {ENV}")
        print(f"   Base Account ID: {BASE_ACCOUNT_ID or 'Not set in .env'}")
        print(f"   Log File: {log_file}")
        print(f"   JSON File: {json_file}")
        
        # Determine which accounts to check
        if len(sys.argv) > 1:
            # Account suffixes provided as arguments
            suffixes = sys.argv[1:]
            account_ids = [get_account_id_from_suffix(suffix) for suffix in suffixes]
        else:
            # Try to get accounts from environment
            account_ids = get_account_list()
            if not account_ids:
                print("❌ ERROR: No accounts configured. Set OANDA_ACCOUNT_ID or ACCOUNT_ID_PREFIX+ACCOUNT_SUFFIX_ALLOWLIST in .env", file=sys.stderr)
                return 1
        
        print(f"   Checking {len(account_ids)} account(s)...\n")
        
        all_success = True
        all_account_data = []
        
        for account_id in account_ids:
            data = probe_account(account_id, include_24h=True)
            display_account_data(data)
            all_account_data.append(data)
            if not data['success']:
                all_success = False
        
        print(f"\n{'='*70}")
        if all_success:
            print("✅ All accounts probed successfully")
        else:
            print("⚠️  Some accounts had errors")
        
        # Save JSON data
        json_output = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'environment': ENV,
            'accounts': all_account_data
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, default=str)
        
        print(f"\n📝 Log saved to: {log_file}")
        print(f"📊 JSON data saved to: {json_file}")
        
        return 0 if all_success else 1
        
    finally:
        # Restore stdout/stderr and close log file
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        tee.close()

if __name__ == '__main__':
    sys.exit(main())
