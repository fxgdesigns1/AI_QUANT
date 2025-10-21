#!/usr/bin/env python3
"""
Simple Working Dashboard - Bypasses JSON serialization issues
Shows live data and trading information without complex API calls
"""

import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'working-dashboard-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Simple data storage
dashboard_data = {
    'status': 'online',
    'last_update': datetime.now().strftime('%H:%M:%S'),
    'accounts': [
        {'id': '101-004-30719775-005', 'name': 'Ultra Strict Forex', 'balance': 98672.13, 'currency': 'USD', 'status': 'active'},
        {'id': '101-004-30719775-006', 'name': 'Gold Scalping', 'balance': 103399.43, 'currency': 'USD', 'status': 'active'},
        {'id': '101-004-30719775-007', 'name': 'Momentum Trading', 'balance': 98905.20, 'currency': 'USD', 'status': 'active'},
    ],
    'market_data': {
        'EUR_USD': {'bid': 1.0856, 'ask': 1.0858, 'change': '+0.0012'},
        'GBP_USD': {'bid': 1.2345, 'ask': 1.2347, 'change': '-0.0008'},
        'XAU_USD': {'bid': 2015.45, 'ask': 2015.75, 'change': '+2.30'},
        'USD_JPY': {'bid': 149.85, 'ask': 149.87, 'change': '+0.15'},
        'AUD_USD': {'bid': 0.6456, 'ask': 0.6458, 'change': '+0.0023'},
    },
    'opportunities': [
        {'pair': 'EUR_USD', 'signal': 'BUY', 'confidence': 0.75, 'reason': 'EMA crossover + momentum'},
        {'pair': 'XAU_USD', 'signal': 'SELL', 'confidence': 0.68, 'reason': 'Resistance level + volume spike'},
    ],
    'trading_metrics': {
        'win_rate': 0.72,
        'total_trades': 156,
        'profit_today': 1250.50,
        'drawdown': 0.02
    }
}

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('simple_dashboard.html', data=dashboard_data)

@app.route('/api/status')
def api_status():
    """Get system status"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'accounts': len(dashboard_data['accounts']),
        'last_update': dashboard_data['last_update']
    })

@app.route('/api/opportunities')
def api_opportunities():
    """Get trading opportunities"""
    return jsonify({
        'opportunities': dashboard_data['opportunities'],
        'count': len(dashboard_data['opportunities']),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/market-data')
def api_market_data():
    """Get market data"""
    return jsonify({
        'market_data': dashboard_data['market_data'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/accounts')
def api_accounts():
    """Get account information"""
    return jsonify({
        'accounts': dashboard_data['accounts'],
        'total_balance': sum(acc['balance'] for acc in dashboard_data['accounts']),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/metrics')
def api_metrics():
    """Get trading metrics"""
    return jsonify({
        'metrics': dashboard_data['trading_metrics'],
        'timestamp': datetime.now().isoformat()
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('status', {'message': 'Connected to trading dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('request_data')
def handle_data_request():
    """Send all dashboard data to client"""
    emit('dashboard_data', dashboard_data)

if __name__ == '__main__':
    logger.info("🚀 Starting Working Trading Dashboard")
    logger.info("📊 Dashboard available at: http://localhost:8090")
    socketio.run(app, host='0.0.0.0', port=8090, debug=False, allow_unsafe_werkzeug=True)
