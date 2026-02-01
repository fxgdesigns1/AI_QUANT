#!/usr/bin/env python3
"""
Working API for Original Dashboard
Provides data to the beautiful dashboard without JSON serialization issues
"""

from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dashboard.data_fix import get_working_data, safe_serialize

app = Flask(__name__)
CORS(app)

@app.route('/api/status')
def api_status():
    """Get system status"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'status': 'online',
        'timestamp': data['timestamp'],
        'accounts': len(data['accounts']),
        'last_update': data['system_status']['last_update'],
        'live_data_mode': data['system_status']['live_data_mode'],
        'active_accounts': data['system_status']['active_accounts'],
        'data_feed_status': data['system_status']['data_feed_status']
    }))

@app.route('/api/opportunities')
def api_opportunities():
    """Get trading opportunities"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'opportunities': data['opportunities'],
        'count': len(data['opportunities']),
        'timestamp': data['timestamp']
    }))

@app.route('/api/market-data')
def api_market_data():
    """Get market data"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'market_data': data['market_data'],
        'timestamp': data['timestamp']
    }))

@app.route('/api/accounts')
def api_accounts():
    """Get account information"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'accounts': data['accounts'],
        'total_balance': sum(acc['balance'] for acc in data['accounts']),
        'timestamp': data['timestamp']
    }))

@app.route('/api/metrics')
def api_metrics():
    """Get trading metrics"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'metrics': data['trading_metrics'],
        'timestamp': data['timestamp']
    }))

@app.route('/api/overview')
def api_overview():
    """Get account overview"""
    data = get_working_data()
    return jsonify(safe_serialize({
        'total_accounts': len(data['accounts']),
        'accounts': {acc['id']: acc for acc in data['accounts']},
        'timestamp': data['timestamp']
    }))

if __name__ == '__main__':
    print("🚀 Starting Working API for Dashboard")
    print("📊 API available at: http://localhost:8081")
    app.run(host='0.0.0.0', port=8081, debug=False)

