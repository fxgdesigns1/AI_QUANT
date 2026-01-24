#!/usr/bin/env python3
"""
Local OANDA Trade Pull
Pulls CLOSED trades from OANDA for all accounts using the authoritative /trades endpoint.
Bypasses transaction reconstruction (Stage 2) by fetching directly from source.

Output:
    data/processed/trades_flat.json (Ready for stats_engine)
    data/raw/{account_id}_trades.json (Raw backup)

Usage:
    python scripts/local_oanda_trade_pull.py
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# OANDA Configuration
API_KEY = os.getenv('OANDA_API_KEY')
ENV = os.getenv('OANDA_ENV', 'practice')

if not API_KEY:
    print("❌ ERROR: Missing OANDA_API_KEY in .env", file=sys.stderr)
    sys.exit(1)

BASE_URL = 'https://api-fxpractice.oanda.com/v3' if ENV == 'practice' else 'https://api-fxtrade.oanda.com/v3'

HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

def get_account_ids() -> List[str]:
    """Discover all accounts owned by the API key."""
    try:
        print(f"   🔎 Discovering accounts from {BASE_URL}/accounts...")
        resp = requests.get(f'{BASE_URL}/accounts', headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        accounts = data.get('accounts', [])
        return [acc.get('id') for acc in accounts]
    except Exception as e:
        print(f'❌ Failed to discover accounts: {e}')
        sys.exit(1)

def fetch_closed_trades(account_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all CLOSED trades for an account using the authoritative /trades endpoint.
    Handles pagination via beforeID.
    """
    all_trades = []
    last_id = None
    batch_size = 500  # Max allowed by OANDA
    
    print(f"   Fetching closed trades for {account_id}...")
    
    while True:
        params = {
            'state': 'CLOSED',
            'count': batch_size
        }
        if last_id:
            params['beforeID'] = last_id
            
        try:
            resp = requests.get(
                f'{BASE_URL}/accounts/{account_id}/trades',
                headers=HEADERS,
                params=params,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            trades = data.get('trades', [])
            
            if not trades:
                break
                
            all_trades.extend(trades)
            last_id = trades[-1].get('id')
            
            print(f"   Fetched {len(trades)} trades (Total: {len(all_trades)})")
            
            if len(trades) < batch_size:
                break
                
        except Exception as e:
            print(f"   ❌ Error fetching trades: {e}")
            break
            
    return all_trades

def normalize_trade(trade: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """
    Normalize OANDA trade object to internal schema.
    Computes derived fields like result and rr_ratio.
    """
    # Basic fields
    trade_id = trade.get('id')
    instrument = trade.get('instrument')
    price = float(trade.get('price', 0.0))
    initial_units = float(trade.get('initialUnits', 0.0))
    current_units = float(trade.get('currentUnits', 0.0)) # Should be 0 for closed
    direction = 'LONG' if initial_units > 0 else 'SHORT'
    
    # Times
    open_time = trade.get('openTime')
    close_time = trade.get('closeTime')
    
    # P&L
    realized_pl = float(trade.get('realizedPL', 0.0))
    close_price = float(trade.get('averageClosePrice', 0.0))
    
    # Orders (TP/SL)
    tp_order = trade.get('takeProfitOrder')
    sl_order = trade.get('stopLossOrder')
    
    tp_price = float(tp_order.get('price')) if tp_order else None
    sl_price = float(sl_order.get('price')) if sl_order else None
    
    # Derived: Result
    if realized_pl > 0:
        result = 'WIN'
    elif realized_pl < 0:
        result = 'LOSS'
    else:
        result = 'BREAKEVEN'
        
    # Derived: RR Ratio
    rr_ratio = None
    if tp_price and sl_price and price:
        try:
            if direction == 'LONG':
                risk = abs(price - sl_price)
                reward = abs(tp_price - price)
            else:
                risk = abs(tp_price - price)
                reward = abs(price - sl_price)
            
            if risk > 0:
                rr_ratio = reward / risk
        except:
            pass
            
    # Derived: Duration
    duration_seconds = None
    try:
        start = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
        duration_seconds = int((end - start).total_seconds())
    except:
        pass

    return {
        'trade_id': trade_id,
        'account_id': account_id,
        'account_suffix': account_id.split('-')[-1] if '-' in account_id else account_id,
        'instrument': instrument,
        'direction': direction,
        'entry_time': open_time,
        'entry_price': price,
        'entry_units': initial_units,
        'exit_time': close_time,
        'exit_price': close_price,
        'exit_type': 'CLOSED', # Generic
        'realized_pl': realized_pl,
        'result': result,
        'tp_price': tp_price,
        'sl_price': sl_price,
        'rr_ratio': rr_ratio,
        'duration_seconds': duration_seconds,
        'is_closed': True,
        'source': 'authoritative_endpoint'
    }

def main():
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / 'data' / 'raw'
    processed_dir = project_root / 'data' / 'processed'
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("📥 OANDA Authoritative Trade Pull")
    print("=" * 70)
    
    account_ids = get_account_ids()
    if not account_ids:
        return 1
        
    print(f"Found {len(account_ids)} accounts")
    
    all_normalized_trades = []
    
    for account_id in account_ids:
        print(f"\n📊 Processing {account_id}...")
        
        # Fetch
        trades = fetch_closed_trades(account_id)
        
        # Save Raw
        raw_file = raw_dir / f"{account_id}_trades.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump({
                'account_id': account_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'count': len(trades),
                'trades': trades
            }, f, indent=2)
            
        # Normalize
        for t in trades:
            normalized = normalize_trade(t, account_id)
            all_normalized_trades.append(normalized)
            
    # Save Normalized (bypassing trade_rebuilder)
    output_file = processed_dir / 'trades_flat.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'trade_count': len(all_normalized_trades),
            'data_confidence': 'HIGH',
            'source': 'oanda_authoritative',
            'trades': all_normalized_trades
        }, f, indent=2, default=str)
        
    print("\n" + "=" * 70)
    print(f"✅ Saved {len(all_normalized_trades)} trades to {output_file}")
    print("Ready for stats_engine")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
