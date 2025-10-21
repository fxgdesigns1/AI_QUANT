#!/usr/bin/env python3
"""
Simple Analytics Dashboard for Google Cloud - Minimal Version
"""

import os
from flask import Flask, jsonify, render_template
from datetime import datetime

# Set template folder
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def home():
    """Main dashboard page"""
    try:
        return render_template('overview.html')
    except Exception as e:
        # Fallback to JSON if template missing
        return jsonify({
            'status': 'running',
            'service': 'analytics-dashboard',
            'message': 'Analytics dashboard is operational',
            'error': f'Template error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'analytics-dashboard',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/overview')
def overview():
    """Overview page"""
    try:
        return render_template('overview.html')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'operational',
        'version': '1.0.0',
        'features': [
            'account_monitoring',
            'performance_analytics',
            'strategy_tracking'
        ],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/overview/data')
def overview_data():
    """Get overview data from main trading system"""
    try:
        import requests
        
        # Fetch data from main trading system
        trading_url = 'https://ai-quant-trading.uc.r.appspot.com/api/status'
        response = requests.get(trading_url, timeout=10)
        
        if response.ok:
            data = response.json()
            accounts_data = data.get('account_statuses', {})
            
            # Transform to analytics format
            accounts = []
            total_balance = 0.0
            total_unrealized = 0.0
            total_trades = 0
            
            for acc_id, acc in accounts_data.items():
                account_info = {
                    'name': acc.get('account_name', acc_id[-3:]),
                    'account_id': acc_id,
                    'balance': acc.get('balance', 0.0),
                    'equity': acc.get('balance', 0.0) + acc.get('unrealized_pl', 0.0),
                    'unrealized_pl': acc.get('unrealized_pl', 0.0),
                    'daily_pl': 0.0,  # Not available from status
                    'daily_trades': 0,  # Not available from status
                    'win_rate': 0.0  # Not available from status
                }
                accounts.append(account_info)
                
                total_balance += acc.get('balance', 0.0)
                total_unrealized += acc.get('unrealized_pl', 0.0)
                total_trades += acc.get('open_trades', 0)
            
            return jsonify({
                'accounts': accounts,
                'total_balance': total_balance,
                'total_unrealized_pl': total_unrealized,
                'total_trades_today': total_trades,
                'system_win_rate': 0.0,  # Calculate from trade history
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Fallback to empty data
            return jsonify({
                'accounts': [],
                'total_balance': 0.0,
                'total_unrealized_pl': 0.0,
                'total_trades_today': 0,
                'system_win_rate': 0.0,
                'message': 'Unable to fetch data from trading system',
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        # Fallback on error
        return jsonify({
            'accounts': [],
            'total_balance': 0.0,
            'total_unrealized_pl': 0.0,
            'total_trades_today': 0,
            'system_win_rate': 0.0,
            'error': str(e),
            'message': 'Error fetching data',
            'timestamp': datetime.now().isoformat()
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


