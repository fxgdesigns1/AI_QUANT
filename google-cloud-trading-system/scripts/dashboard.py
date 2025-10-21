#!/usr/bin/env python3
'''
Adaptive System Monitoring Dashboard
Simple web dashboard to monitor the adaptive system
'''

import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.adaptive_integration import AdaptiveAccountManager

app = Flask(__name__)
manager = None

@app.route('/')
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Adaptive Trading System Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .status {{ background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .profit {{ color: #27ae60; }}
            .loss {{ color: #e74c3c; }}
            .neutral {{ color: #95a5a6; }}
            .refresh {{ float: right; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Adaptive Trading System Dashboard</h1>
                <div class="refresh">Last Updated: {timestamp}</div>
            </div>
            
            <div id="content">
                <p>Loading system status...</p>
            </div>
        </div>
        
        <script>
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('content').innerHTML = data.html;
                }});
        </script>
    </body>
    </html>
    '''.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/api/status')
def api_status():
    global manager
    
    if not manager:
        try:
            manager = AdaptiveAccountManager()
        except Exception as e:
            return jsonify({{'error': str(e)}})
    
    try:
        account_status = manager.get_account_status()
        system_status = manager.get_adaptive_system_status()
        
        # Calculate totals
        total_balance = sum(status.get('balance', 0) for status in account_status.values() if 'balance' in status)
        total_pl = sum(status.get('total_pl', 0) for status in account_status.values() if 'total_pl' in status)
        total_pl_pct = (total_pl / total_balance * 100) if total_balance > 0 else 0
        
        html = f'''
        <div class="status">
            <h2>📊 Portfolio Overview</h2>
            <p><strong>Total Balance:</strong> ${total_balance:,.2f}</p>
            <p><strong>Total P&L:</strong> <span class="{'profit' if total_pl >= 0 else 'loss'}">${total_pl:,.2f} ({total_pl_pct:+.2f}%)</span></p>
        </div>
        
        <div class="status">
            <h2>🤖 Adaptive System Status</h2>
            <p><strong>Running:</strong> {'🟢 Active' if system_status['is_running'] else '🔴 Inactive'}</p>
            <p><strong>Market Condition:</strong> {system_status['current_condition'].replace('_', ' ').title()}</p>
            <p><strong>Active Signals:</strong> {system_status['active_signals']}</p>
        </div>
        
        <div class="status">
            <h2>🏦 Account Status</h2>
        '''
        
        for account_name, status in account_status.items():
            if 'error' not in status:
                pl_class = 'profit' if status['total_pl'] >= 0 else 'loss'
                html += f'''
                <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #3498db;">
                    <h3>{account_name}</h3>
                    <p><strong>Balance:</strong> ${status['balance']:,.2f}</p>
                    <p><strong>P&L:</strong> <span class="{pl_class}">${status['total_pl']:,.2f} ({status['pl_percentage']:+.2f}%)</span></p>
                    <p><strong>Positions:</strong> {status['open_positions']}</p>
                    <p><strong>Margin Usage:</strong> {status['margin_usage_pct']:.1f}%</p>
                </div>
                '''
            else:
                html += f'<p><strong>{account_name}:</strong> ❌ {status["error"]}</p>'
        
        html += '</div>'
        
        return jsonify({'html': html})
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("🌐 Starting Adaptive System Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
