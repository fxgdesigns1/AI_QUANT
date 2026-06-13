#!/usr/bin/env python3
"""
Get performance metrics for each strategy over the last 24 hours.
Queries OANDA API for transactions and calculates P&L, win rate, etc.
"""

import os
import sys
import yaml
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import re

# OANDA Configuration
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# Headers for OANDA API
HEADERS = {
    'Authorization': f'Bearer {OANDA_API_KEY}',
    'Content-Type': 'application/json'
}


def load_accounts_config() -> List[Dict[str, Any]]:
    """Load active accounts from accounts.yaml"""
    yaml_paths = [
        '/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml',
        '/opt/quant_system_clean/AI_QUANT_credentials/accounts.yaml',
        os.path.join(os.path.dirname(__file__), 'AI_QUANT_credentials', 'accounts.yaml'),
        os.path.join(os.path.dirname(__file__), 'Sync folder MAC TO PC', 'DESKTOP_HANDOFF_PACKAGE', 
                     'google-cloud-trading-system', 'AI_QUANT_credentials', 'accounts.yaml'),
    ]
    
    for yaml_path in yaml_paths:
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    accounts_data = yaml.safe_load(f) or {}
                accounts_section = accounts_data.get('accounts', {})
                active_accounts = [
                    dict(acc, logical_name=name) 
                    for name, acc in accounts_section.items() 
                    if acc.get('active', True)
                ]
                return active_accounts
            except Exception as e:
                print(f"Error loading {yaml_path}: {e}")
                continue
    
    return []


def get_last_strategy_change_time() -> Optional[datetime]:
    """Reads STRATEGY_UPLOAD_LOG.md and extracts the 'Last Updated' timestamp."""
    log_path = os.path.join(os.path.dirname(__file__), 'STRATEGY_UPLOAD_LOG.md')
    if not os.path.exists(log_path):
        print(f"⚠️  Strategy upload log not found at {log_path}")
        return None

    try:
        with open(log_path, 'r') as f:
            content = f.read()
            match = re.search(r"\*\*Last Updated:\*\* (.*?)", content)
            if match:
                date_str = match.group(1).strip()
                # Example: November 16, 2025 18:03 (London Time)
                # We need to parse this into a datetime object. Ignoring (London Time) for now.
                dt = datetime.strptime(date_str.split(' (')[0], '%B %d, %Y %H:%M')
                # Assuming the timestamp in the log is UTC or can be treated as such for timedelta calc
                return dt
            else:
                print("⚠️  'Last Updated' timestamp not found in STRATEGY_UPLOAD_LOG.md")
                return None
    except Exception as e:
        print(f"Error reading or parsing STRATEGY_UPLOAD_LOG.md: {e}")
        return None


def get_account_info(account_id: str) -> Optional[Dict[str, Any]]:
    """Get account information"""
    try:
        url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json().get('account')
        return None
    except Exception as e:
        print(f"Error getting account info for {account_id}: {e}")
        return None


def get_transactions_since(account_id: str, since_time: datetime) -> List[Dict[str, Any]]:
    """Get all transactions since a given time"""
    try:
        now = datetime.utcnow()
        since_str = since_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
        to_str = now.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
        
        url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}/transactions"
        
        all_transactions = []
        page_size = 500  # OANDA allows up to 500
        
        # First, try without pagination to get recent transactions
        params = {
            'from': since_str,
            'to': to_str,
            'count': page_size
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️  API Error {response.status_code}: {response.text[:200]}")
            # Try without time filter as fallback
            params = {'count': page_size}
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if response.status_code != 200:
                return []
        
        data = response.json()
        transactions = data.get('transactions', [])
        
        if not transactions:
            return []
        
        # Filter transactions to last 24 hours
        filtered_transactions = []
        for tx in transactions:
            tx_time_str = tx.get('time', '')
            if tx_time_str:
                try:
                    # Parse OANDA time format
                    tx_time = datetime.fromisoformat(tx_time_str.replace('Z', '+00:00'))
                    tx_time_utc = tx_time.replace(tzinfo=None)
                    if tx_time_utc >= since_time:
                        filtered_transactions.append(tx)
                except:
                    # If we can't parse time, include it anyway
                    filtered_transactions.append(tx)
            else:
                filtered_transactions.append(tx)
        
        # Handle pagination if needed
        all_transactions.extend(filtered_transactions)
        
        # Check for more pages using the 'id' parameter
        if len(transactions) == page_size:
            last_id = transactions[-1].get('id')
            while last_id:
                params = {
                    'id': last_id,
                    'count': page_size
                }
                response = requests.get(url, headers=HEADERS, params=params, timeout=15)
                if response.status_code != 200:
                    break
                data = response.json()
                transactions = data.get('transactions', [])
                if not transactions:
                    break
                
                # Filter to last 24 hours
                for tx in transactions:
                    tx_time_str = tx.get('time', '')
                    if tx_time_str:
                        try:
                            tx_time = datetime.fromisoformat(tx_time_str.replace('Z', '+00:00'))
                            tx_time_utc = tx_time.replace(tzinfo=None)
                            if tx_time_utc >= since_time:
                                all_transactions.append(tx)
                        except:
                            all_transactions.append(tx)
                    else:
                        all_transactions.append(tx)
                
                if len(transactions) < page_size:
                    break
                last_id = transactions[-1].get('id')
        
        return all_transactions
    except Exception as e:
        print(f"   ⚠️  Error fetching transactions: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_closed_trades_since(account_id: str, since_time: datetime) -> List[Dict[str, Any]]:
    """Get closed trades since a given time"""
    try:
        now = datetime.utcnow()
        since_str = since_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
        
        url = f"{OANDA_BASE_URL}/v3/accounts/{account_id}/trades"
        params = {
            'state': 'CLOSED',
            'count': 500
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if response.status_code != 200:
            return []
        
        data = response.json()
        all_trades = data.get('trades', [])
        
        # Filter to last 24 hours
        filtered_trades = []
        for trade in all_trades:
            close_time_str = trade.get('closeTime', '')
            if close_time_str:
                try:
                    close_time = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                    close_time_utc = close_time.replace(tzinfo=None)
                    if close_time_utc >= since_time:
                        filtered_trades.append(trade)
                except:
                    pass
        
        return filtered_trades
    except Exception as e:
        print(f"   ⚠️  Error fetching closed trades: {e}")
        return []


def calculate_performance(account_id: str, account_config: Dict[str, Any], 
                          transactions: List[Dict[str, Any]], since_time: datetime) -> Dict[str, Any]:
    """Calculate performance metrics from transactions"""
    strategy_name = account_config.get('strategy', 'unknown')
    account_name = account_config.get('name', account_id)
    
    # Get account balance info
    account_info = get_account_info(account_id)
    current_balance = float(account_info['balance']) if account_info else 0.0
    unrealized_pl = float(account_info.get('unrealizedPL', 0)) if account_info else 0.0
    
    # Also get closed trades directly
    closed_trades = get_closed_trades_since(account_id, since_time)
    
    # Process transactions
    trades = []
    total_realized_pl = 0.0
    winning_trades = 0
    losing_trades = 0
    total_volume = 0.0
    
    # Process closed trades first (more reliable)
    for trade in closed_trades:
        pl = float(trade.get('realizedPL', 0))
        if pl != 0:
            total_realized_pl += pl
            # For closed trades, initialUnits might be more reliable
            initial_units = abs(float(trade.get('initialUnits', trade.get('currentUnits', 0))))
            current_units = float(trade.get('currentUnits', 0))
            side = 'BUY' if current_units > 0 or initial_units > 0 else 'SELL'
            if initial_units == 0:
                initial_units = abs(current_units)
            
            trades.append({
                'instrument': trade.get('instrument', ''),
                'units': initial_units,
                'entry_price': float(trade.get('price', 0)),
                'exit_price': float(trade.get('averageClosePrice', 0)),
                'pl': pl,
                'time': trade.get('closeTime', ''),
                'side': side
            })
            if pl > 0:
                winning_trades += 1
            elif pl < 0:
                losing_trades += 1
    
    # Also process transactions for any additional info
    trade_map = {}
    for tx in transactions:
        tx_type = tx.get('type', '')
        tx_time = tx.get('time', '')
        
        if tx_type == 'ORDER_FILL':
            # Check for trade opened
            trade_opened = tx.get('tradeOpened', {})
            if trade_opened:
                trade_id = str(trade_opened.get('tradeID', ''))
                if trade_id and trade_id not in trade_map:
                    trade_map[trade_id] = {
                        'instrument': tx.get('instrument', ''),
                        'units': abs(float(tx.get('units', 0))),
                        'entry_price': float(tx.get('price', 0)),
                        'pl': 0.0,
                        'time': tx_time,
                        'side': 'BUY' if float(tx.get('units', 0)) > 0 else 'SELL'
                    }
                    total_volume += abs(float(tx.get('units', 0))) * abs(float(tx.get('price', 0)))
            
            # Check for trade closed
            trade_closed = tx.get('tradeClosed', {})
            if trade_closed:
                trade_id = str(trade_closed.get('tradeID', ''))
                pl = float(tx.get('pl', 0))
                if pl != 0:
                    total_realized_pl += pl
                    if trade_id not in trade_map:
                        # Create entry if we don't have it
                        trade_map[trade_id] = {
                            'instrument': tx.get('instrument', ''),
                            'units': abs(float(tx.get('units', 0))),
                            'entry_price': 0.0,
                            'pl': pl,
                            'time': tx_time,
                            'side': 'BUY' if float(tx.get('units', 0)) > 0 else 'SELL'
                        }
                    else:
                        trade_map[trade_id]['pl'] = pl
                        trade_map[trade_id]['exit_price'] = float(tx.get('price', 0))
        
        elif tx_type == 'TRADE_CLOSE':
            pl = float(tx.get('pl', 0))
            if pl != 0:
                total_realized_pl += pl
                trade_closed = tx.get('tradeClosed', {})
                if trade_closed:
                    trade_id = str(trade_closed.get('tradeID', ''))
                    if trade_id not in trade_map:
                        trade_map[trade_id] = {
                            'instrument': tx.get('instrument', ''),
                            'units': 0,
                            'entry_price': 0.0,
                            'exit_price': float(tx.get('price', 0)),
                            'pl': pl,
                            'time': tx_time,
                            'side': ''
                        }
    
    # Add any trades from transaction processing that weren't in closed trades
    for trade_id, trade in trade_map.items():
        if trade['pl'] != 0 and trade_id not in [t.get('trade_id', '') for t in trades]:
            # Check if we already counted this
            found = False
            for existing_trade in trades:
                if (existing_trade['instrument'] == trade['instrument'] and 
                    abs(existing_trade['pl'] - trade['pl']) < 0.01):
                    found = True
                    break
            if not found:
                trades.append(trade)
                if trade['pl'] > 0:
                    winning_trades += 1
                elif trade['pl'] < 0:
                    losing_trades += 1
    
    total_trades = winning_trades + losing_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Calculate average win/loss
    avg_win = sum(t['pl'] for t in trades if t['pl'] > 0) / winning_trades if winning_trades > 0 else 0.0
    avg_loss = sum(t['pl'] for t in trades if t['pl'] < 0) / losing_trades if losing_trades > 0 else 0.0
    
    # Calculate profit factor
    gross_profit = sum(t['pl'] for t in trades if t['pl'] > 0)
    gross_loss = abs(sum(t['pl'] for t in trades if t['pl'] < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    
    return {
        'account_id': account_id,
        'account_name': account_name,
        'strategy': strategy_name,
        'current_balance': current_balance,
        'unrealized_pl': unrealized_pl,
        'total_equity': current_balance + unrealized_pl,
        'realized_pl_since': total_realized_pl,
        'total_pl_since': total_realized_pl + unrealized_pl,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'total_volume': total_volume,
        'trades': trades
    }


def format_performance_report(performance_data: List[Dict[str, Any]], hours: int = 24) -> str:
    """Format performance data into a readable report"""
    report = []
    report.append("=" * 80)
    report.append(f"STRATEGY PERFORMANCE - LAST {hours} HOURS")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (London Time)")
    report.append("")
    
    if not performance_data:
        report.append("No active accounts found or no data available.")
        return "\n".join(report)
    
    # Sort by total P&L (descending)
    sorted_data = sorted(performance_data, key=lambda x: x['total_pl_since'], reverse=True)
    
    for perf in sorted_data:
        report.append("-" * 80)
        report.append(f"Strategy: {perf['strategy']}")
        report.append(f"Account: {perf['account_name']} ({perf['account_id']})")
        report.append("")
        
        # Balance and P&L
        report.append(f"💰 Current Balance: ${perf['current_balance']:.2f}")
        report.append(f"📈 Unrealized P&L: ${perf['unrealized_pl']:.2f}")
        report.append(f"💵 Total Equity: ${perf['total_equity']:.2f}")
        report.append(f"📊 Realized P&L ({hours}h): ${perf['realized_pl_since']:.2f}")
        report.append(f"🎯 Total P&L ({hours}h): ${perf['total_pl_since']:.2f}")
        report.append("")
        
        # Trade statistics
        if perf['total_trades'] > 0:
            report.append(f"📈 Total Trades: {perf['total_trades']}")
            report.append(f"✅ Winning Trades: {perf['winning_trades']}")
            report.append(f"❌ Losing Trades: {perf['losing_trades']}")
            report.append(f"📊 Win Rate: {perf['win_rate']:.1f}%")
            report.append(f"💰 Average Win: ${perf['avg_win']:.2f}")
            report.append(f"📉 Average Loss: ${perf['avg_loss']:.2f}")
            report.append(f"⚖️  Profit Factor: {perf['profit_factor']:.2f}")
            report.append(f"💵 Gross Profit: ${perf['gross_profit']:.2f}")
            report.append(f"📉 Gross Loss: ${perf['gross_loss']:.2f}")
        else:
            report.append("📊 No trades executed in the last 24 hours")
        
        report.append("")
    
    # Summary
    report.append("=" * 80)
    report.append("SUMMARY")
    report.append("=" * 80)
    
    total_pl = sum(p['total_pl_since'] for p in performance_data)
    total_realized = sum(p['realized_pl_since'] for p in performance_data)
    total_trades_all = sum(p['total_trades'] for p in performance_data)
    total_wins = sum(p['winning_trades'] for p in performance_data)
    total_losses = sum(p['losing_trades'] for p in performance_data)
    overall_win_rate = (total_wins / total_trades_all * 100) if total_trades_all > 0 else 0.0
    
    report.append(f"Total Strategies: {len(performance_data)}")
    report.append(f"Total Realized P&L ({hours}h): ${total_realized:.2f}")
    report.append(f"Total P&L ({hours}h): ${total_pl:.2f}")
    report.append(f"Total Trades ({hours}h): {total_trades_all}")
    report.append(f"Overall Win Rate: {overall_win_rate:.1f}%")
    report.append("")
    
    return "\n".join(report)


def main():
    """Main function"""
    # Get last strategy change time
    last_change_dt = get_last_strategy_change_time()
    if last_change_dt:
        now = datetime.utcnow()
        # Calculate hours since last change, ensuring it's at least 1 for consistency
        time_diff = now - last_change_dt
        hours = max(1, int(time_diff.total_seconds() / 3600))
        print(f"Calculating performance since last strategy change ({last_change_dt.strftime('%Y-%m-%d %H:%M')} London Time, approx {hours} hours ago)")
        since_time = last_change_dt
    else:
        # Fallback to 48 hours if no last change time is found or parsed
        hours = 48
        now = datetime.utcnow()
        since_time = now - timedelta(hours=hours)
        print(f"⚠️  Could not determine last strategy change time. Defaulting to last {hours} hours.")

    print("Loading account configurations...")
    accounts = load_accounts_config()
    
    if not accounts:
        print("❌ No active accounts found. Please check accounts.yaml")
        return
    
    print(f"Found {len(accounts)} active accounts")
    print("")
    
    performance_data = []
    
    for account_config in accounts:
        account_id = account_config.get('account_id')
        strategy_name = account_config.get('strategy', 'unknown')
        account_name = account_config.get('name', account_id)
        
        if not account_id:
            continue
        
        print(f"📊 Processing {account_name} ({strategy_name})...")
        
        # Get transactions
        now = datetime.utcnow()
        since_time = now - timedelta(hours=hours)
        transactions = get_transactions_since(account_id, since_time)
        print(f"   Found {len(transactions)} transactions in last {hours}h")
        
        # Calculate performance
        perf = calculate_performance(account_id, account_config, transactions, since_time)
        performance_data.append(perf)
        
        print(f"   ✅ Processed: {perf['total_trades']} trades, P&L: ${perf['total_pl_since']:.2f}")
        if perf['total_trades'] > 0:
            print(f"      Wins: {perf['winning_trades']}, Losses: {perf['losing_trades']}, Win Rate: {perf['win_rate']:.1f}%")
        print("")
    
    # Generate and print report
    report = format_performance_report(performance_data, hours)
    print(report)
    
    # Optionally save to file
    output_file = os.path.join(os.path.dirname(__file__), 'strategy_performance_24h.txt')
    try:
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save report to file: {e}")


if __name__ == "__main__":
    main()

