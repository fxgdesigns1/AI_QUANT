#!/usr/bin/env python3
"""
Trade Manager Auto-Updating Dashboard
Shows LIVE data automatically with WebSocket - NO button clicks needed
Optimized to minimize API strain
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient

load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))

app = Flask(__name__, template_folder='src/templates')
app.config['SECRET_KEY'] = 'trade-manager-2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Cache to reduce API calls
cache = {
    'data': None,
    'last_update': None
}

CACHE_SECONDS = 10  # Only call OANDA every 10 seconds

def get_live_data_cached():
    """Get live data with caching to reduce API strain"""
    now = datetime.now()
    
    # Return cached data if less than 10 seconds old
    if cache['last_update'] and (now - cache['last_update']).total_seconds() < CACHE_SECONDS:
        return cache['data']
    
    # Fetch fresh data
    try:
        accounts = {
            'PRIMARY': (os.getenv('PRIMARY_ACCOUNT'), 'Ultra Strict Forex'),
            'GOLD': (os.getenv('GOLD_SCALP_ACCOUNT'), 'Gold Scalping'),
            'ALPHA': (os.getenv('STRATEGY_ALPHA_ACCOUNT'), 'Momentum Trading')
        }
        
        result = {}
        total_balance = 0
        total_pl = 0
        total_trades = 0
        
        for name, (account_id, strategy) in accounts.items():
            try:
                client = OandaClient(os.getenv('OANDA_API_KEY'), account_id, os.getenv('OANDA_ENVIRONMENT'))
                account_info = client.get_account_info()
                open_trades = client.get_open_trades()
                
                trades_list = []
                for trade in open_trades:
                    trades_list.append({
                        'id': trade['id'],
                        'instrument': trade['instrument'],
                        'units': float(trade['currentUnits']),
                        'price': float(trade['price']),
                        'unrealized_pl': float(trade['unrealizedPL']),
                        'side': 'LONG' if float(trade['currentUnits']) > 0 else 'SHORT'
                    })
                
                result[name] = {
                    'strategy': strategy,
                    'balance': float(account_info.balance),
                    'unrealized_pl': float(account_info.unrealized_pl),
                    'realized_pl': float(account_info.realized_pl),
                    'open_trades': len(open_trades),
                    'trades': trades_list,
                    'margin_used': float(account_info.margin_used)
                }
                
                total_balance += float(account_info.balance)
                total_pl += float(account_info.unrealized_pl)
                total_trades += len(open_trades)
                
            except Exception as e:
                result[name] = {'error': str(e)}
        
        data = {
            'status': 'success',
            'accounts': result,
            'totals': {
                'balance': total_balance,
                'unrealized_pl': total_pl,
                'realized_pl': sum(acc.get('realized_pl', 0) for acc in result.values() if 'error' not in acc),
                'open_trades': total_trades
            },
            'timestamp': datetime.now().isoformat()
        }
        
        cache['data'] = data
        cache['last_update'] = now
        
        return data
        
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def background_updates():
    """Send updates via WebSocket every 10 seconds"""
    while True:
        try:
            data = get_live_data_cached()
            socketio.emit('live_update', data)
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            print(f"Update error: {e}")
            time.sleep(10)

@app.route('/')
def index():
    return render_template('trade_manager_web.html')

@app.route('/api/get_live_data')
def api_get_live_data():
    """API endpoint for live data"""
    return jsonify(get_live_data_cached())

@app.route('/api/manager_status')
def manager_status():
    """Check Active Trade Manager status"""
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        is_running = 'active_trade_manager' in result.stdout
        
        actions = 0
        try:
            with open('logs/trade_manager_fixed.log', 'r') as f:
                lines = f.readlines()
                actions = sum(1 for line in lines if 'CLOSED' in line)
        except:
            pass
        
        return jsonify({
            'running': is_running,
            'status': 'ACTIVE' if is_running else 'STOPPED',
            'actions_taken': actions
        })
    except Exception as e:
        return jsonify({'running': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    print(f"✅ Client connected")
    # Send initial data immediately
    data = get_live_data_cached()
    emit('live_update', data)

if __name__ == '__main__':
    print("="*60)
    print("🚀 TRADE MANAGER AUTO-UPDATING DASHBOARD")
    print("="*60)
    print("   URL: http://localhost:8091")
    print("   Auto-Update: Every 10 seconds")
    print("   API Optimization: Cached for 10 seconds")
    print("   Data: 100% LIVE from OANDA")
    print("="*60)
    
    # Start background updates
    threading.Thread(target=background_updates, daemon=True).start()
    
    socketio.run(app, host='0.0.0.0', port=8091, debug=False, allow_unsafe_werkzeug=True)
