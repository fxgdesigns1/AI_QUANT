#!/usr/bin/env python3
"""
Local Dashboard API (Flask)
Serves trade data and stats to the React frontend.

TRUTH SOURCE:
- Primary: VM Execution Logs (data/processed/vm_trades_flat.json)
- Secondary: OANDA Reconciliation (data/processed/trades_flat.json) - LEGACY FALLBACK

Config:
- DATA_SOURCE: 'vm_logs' | 'oanda' (Default: 'vm_logs')
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Configuration
DATA_SOURCE = os.getenv('DASHBOARD_DATA_SOURCE', 'vm_logs')
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
FRONTEND_BUILD_DIR = PROJECT_ROOT / 'frontend/fxg-dashboard/dist'

app = Flask(__name__, static_folder=str(FRONTEND_BUILD_DIR))
CORS(app)  # Enable CORS for local dev

def load_data():
    """Load data based on configured source"""
    vm_file = DATA_DIR / 'processed' / 'vm_trades_flat.json'
    legacy_file = DATA_DIR / 'processed' / 'trades_flat.json'
    stats_file = DATA_DIR / 'processed' / 'stats.json'
    
    trades = []
    stats = {}
    data_confidence = "UNKNOWN"
    source_used = "none"

    # 1. Try Primary Source (VM Logs)
    if DATA_SOURCE == 'vm_logs' and vm_file.exists():
        try:
            with open(vm_file, 'r') as f:
                data = json.load(f)
                trades = data.get('trades', [])
                data_confidence = data.get('data_confidence', 'HIGH')
                source_used = data.get('source', 'vm_logs')
        except Exception as e:
            print(f"Error reading VM logs: {e}")

    # 2. Fallback to OANDA (if configured or VM logs failed/missing)
    if not trades and legacy_file.exists():
        try:
            with open(legacy_file, 'r') as f:
                data = json.load(f)
                trades = data.get('trades', [])
                data_confidence = data.get('data_confidence', 'LOW') # OANDA pull is less granular
                source_used = data.get('source', 'oanda_legacy')
        except Exception as e:
            print(f"Error reading legacy logs: {e}")
            
    # 3. Load pre-computed stats (computed by stats_engine.py which respects priority)
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)
                stats = stats_data.get('overall', {})
                # Stats engine might overwrite confidence based on its own logic
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

@app.route('/api/trades')
def get_trades():
    data = load_data()
    trades = data['trades']
    
    # Filtering
    account_suffix = request.args.get('account_suffix')
    instrument = request.args.get('instrument')
    
    if account_suffix:
        trades = [t for t in trades if t.get('account_suffix') == account_suffix]
    if instrument:
        trades = [t for t in trades if t.get('instrument') == instrument]
        
    # Sort by time desc
    trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return jsonify({
        "success": True,
        "count": len(trades),
        "source": data['source'],
        "trades": trades
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
    app.run(host='0.0.0.0', port=5001, debug=True)
