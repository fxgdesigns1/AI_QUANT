#!/usr/bin/env python3
"""
Fixed Dashboard - Original Beautiful Design with Working Data
Uses the working API to provide data to the original dashboard template
"""

import os
import sys
import json
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fixed-dashboard-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Working API URL
WORKING_API_URL = "http://localhost:8081"

def get_api_data(endpoint):
    """Get data from working API"""
    try:
        response = requests.get(f"{WORKING_API_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API error {response.status_code} for {endpoint}")
            return None
    except Exception as e:
        logger.error(f"Failed to get data from {endpoint}: {e}")
        return None

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard_advanced.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard_advanced.html')

@app.route('/api/status')
def api_status():
    """Get system status"""
    data = get_api_data('/api/status')
    if data:
        return jsonify(data)
    else:
        return jsonify({'status': 'error', 'message': 'API unavailable'})

@app.route('/api/opportunities')
def api_opportunities():
    """Get trading opportunities"""
    data = get_api_data('/api/opportunities')
    if data:
        return jsonify(data)
    else:
        return jsonify({'opportunities': [], 'count': 0, 'timestamp': datetime.now().isoformat()})

@app.route('/api/market-data')
def api_market_data():
    """Get market data"""
    data = get_api_data('/api/market-data')
    if data:
        return jsonify(data)
    else:
        return jsonify({'market_data': {}, 'timestamp': datetime.now().isoformat()})

@app.route('/api/accounts')
def api_accounts():
    """Get account information"""
    data = get_api_data('/api/accounts')
    if data:
        return jsonify(data)
    else:
        return jsonify({'accounts': [], 'total_balance': 0, 'timestamp': datetime.now().isoformat()})

@app.route('/api/metrics')
def api_metrics():
    """Get trading metrics"""
    data = get_api_data('/api/metrics')
    if data:
        return jsonify(data)
    else:
        return jsonify({'metrics': {}, 'timestamp': datetime.now().isoformat()})

@app.route('/api/overview')
def api_overview():
    """Get account overview"""
    data = get_api_data('/api/overview')
    if data:
        return jsonify(data)
    else:
        return jsonify({'accounts': {}, 'total_accounts': 0, 'timestamp': datetime.now().isoformat()})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to fixed dashboard')
    emit('status', {'message': 'Connected to trading dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from fixed dashboard')

@socketio.on('request_data')
def handle_data_request():
    """Send dashboard data to client"""
    status_data = get_api_data('/api/status')
    opportunities_data = get_api_data('/api/opportunities')
    accounts_data = get_api_data('/api/accounts')
    
    dashboard_data = {
        'status': status_data or {'status': 'offline'},
        'opportunities': opportunities_data or {'opportunities': []},
        'accounts': accounts_data or {'accounts': []},
        'timestamp': datetime.now().isoformat()
    }
    
    emit('dashboard_data', dashboard_data)

if __name__ == '__main__':
    logger.info("🚀 Starting Fixed Dashboard - Original Design with Working Data")
    logger.info("📊 Dashboard available at: http://localhost:8080")
    logger.info("🔗 Using working API at: http://localhost:8081")
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)

