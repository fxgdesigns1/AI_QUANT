#!/usr/bin/env python3
"""
Local Dashboard API (Flask)
Serves trade data and stats to the React frontend.

TRUTH SOURCE:
- STRICTLY OANDA Authoritative Data (data/processed/trades_flat.json)
- Per docs/OANDA_DATA_POLICY.md

Config:
- DATA_SOURCE: 'oanda_authoritative' (Hardcoded enforcement)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Configuration
DATA_SOURCE = 'oanda_authoritative'
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
FRONTEND_BUILD_DIR = PROJECT_ROOT / 'frontend/fxg-dashboard/dist'

app = Flask(__name__, static_folder=str(FRONTEND_BUILD_DIR))
CORS(app)  # Enable CORS for local dev

def load_data():
    """Load data strictly from the authoritative OANDA file."""
    trades_file = DATA_DIR / 'processed' / 'trades_flat.json'
    stats_file = DATA_DIR / 'processed' / 'stats.json'
    
    trades = []
    stats = {}
    data_confidence = "UNKNOWN"
    source_used = "none"

    # 1. Load Authoritative Trades
    if trades_file.exists():
        try:
            with open(trades_file, 'r') as f:
                data = json.load(f)
                trades = data.get('trades', [])
                data_confidence = data.get('data_confidence', 'HIGH')
                source_used = data.get('source', 'oanda_authoritative')
        except Exception as e:
            print(f"Error reading authoritative trades: {e}")
            
    # 2. Load pre-computed stats
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)
                stats = stats_data.get('overall', {})
                # Stats file might have its own confidence derived from the data
                if stats_data.get('data_confidence'):
                    data_confidence = stats_data.get('data_confidence')
        except Exception as e:
            print(f"Error reading stats: {e}")

    return {
        "trades": trades, 
        "stats": stats, 
        "data_confidence": data_confidence,
        "source": source_used
    }

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "source": DATA_SOURCE})

@app.route('/api/accounts')
def get_accounts():
    """Return list of all discovered OANDA accounts."""
    data = load_data()
    trades = data['trades']
    # Extract unique accounts from trades
    accounts = sorted(list(set(t.get('account_id') for t in trades if t.get('account_id'))))
    return jsonify({
        "success": True,
        "count": len(accounts),
        "accounts": accounts
    })

@app.route('/api/trades')
def get_trades():
    data = load_data()
    trades = data['trades']
    
    # Filtering
    account_id = request.args.get('account_id')
    account_suffix = request.args.get('account_suffix')
    instrument = request.args.get('instrument')
    direction = request.args.get('direction')
    
    filtered_trades = []
    for t in trades:
        if account_id and t.get('account_id') != account_id:
            continue
        if account_suffix and t.get('account_suffix') != account_suffix:
            continue
        if instrument and t.get('instrument') != instrument:
            continue
        if direction and t.get('direction') != direction:
            continue
        filtered_trades.append(t)
        
    # Sort by time desc
    filtered_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    
    return jsonify({
        "success": True,
        "count": len(filtered_trades),
        "source": data['source'],
        "trades": filtered_trades
    })

@app.route('/api/stats')
def get_stats():
    data = load_data()
    return jsonify({
        "success": True,
        "source": data['source'],
        "data_confidence": data['data_confidence'],
        "stats": data['stats']
    })

@app.route('/api/stats/account')
def get_account_stats():
    # Load raw stats file for granular data
    stats_file = DATA_DIR / 'processed' / 'stats.json'
    account_stats = {}
    
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                full_stats = json.load(f)
                account_stats = full_stats.get('by_account', {})
        except:
            pass
            
    return jsonify({
        "success": True,
        "stats": account_stats
    })

@app.route('/api/stats/pair')
def get_pair_stats():
    # Load raw stats file for granular data
    stats_file = DATA_DIR / 'processed' / 'stats.json'
    pair_stats = {}
    
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                full_stats = json.load(f)
                pair_stats = full_stats.get('by_pair', {})
        except:
            pass
            
    return jsonify({
        "success": True,
        "stats": pair_stats
    })

@app.route('/api/filters')
def get_filters():
    data = load_data()
    trades = data['trades']
    
    accounts = sorted(list(set(t.get('account_suffix') for t in trades if t.get('account_suffix'))))
    instruments = sorted(list(set(t.get('instrument') for t in trades if t.get('instrument'))))
    
    return jsonify({
        "success": True,
        "accounts": accounts,
        "instruments": instruments
    })

# Serve Frontend (Catch-all)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(str(FRONTEND_BUILD_DIR), path)):
        return send_from_directory(str(FRONTEND_BUILD_DIR), path)
    else:
        return send_from_directory(str(FRONTEND_BUILD_DIR), 'index.html')

if __name__ == '__main__':
    print(f"🚀 Starting Local Dashboard API (Source: {DATA_SOURCE})")
    print(f"   Data Dir: {DATA_DIR}")
    print("   STRICTLY ENFORCING OANDA AUTHORITATIVE DATA")
    app.run(host='0.0.0.0', port=5001, debug=True)
