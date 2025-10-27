#!/usr/bin/env python3
"""
Trade Suggestions Integration for Main Dashboard
Simple integration that adds Trade Suggestions to the main dashboard
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system/src')

app = Flask(__name__)

# Trade Suggestions API Endpoints - Proxy to working system
@app.route('/api/suggestions', methods=['GET'])
def api_get_suggestions():
    """Get trade suggestions - proxy to working system"""
    try:
        response = requests.get('http://localhost:8082/api/suggestions', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'suggestions': []
        })

@app.route('/api/suggestions/generate', methods=['POST'])
def api_generate_suggestions():
    """Generate new trade suggestions - proxy to working system"""
    try:
        response = requests.post('http://localhost:8082/api/suggestions/generate', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'suggestions': []
        })

@app.route('/api/suggestions/<suggestion_id>/approve', methods=['POST'])
def api_approve_suggestion(suggestion_id):
    """Approve a trade suggestion - proxy to working system"""
    try:
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/approve', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/suggestions/<suggestion_id>/reject', methods=['POST'])
def api_reject_suggestion(suggestion_id):
    """Reject a trade suggestion - proxy to working system"""
    try:
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/reject', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/suggestions/<suggestion_id>/execute', methods=['POST'])
def api_execute_suggestion(suggestion_id):
    """Execute a trade suggestion - proxy to working system"""
    try:
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/execute', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'Trade Suggestions Integration'
    })

if __name__ == '__main__':
    print("🚀 Starting Trade Suggestions Integration...")
    print("📊 Proxying to: http://localhost:8082")
    print("🌐 Available on: http://localhost:8084")
    app.run(host='0.0.0.0', port=8084, debug=False)
