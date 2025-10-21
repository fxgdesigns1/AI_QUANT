#!/usr/bin/env python3
"""
Simple Dashboard - Redirects to Advanced Dashboard
This file exists for backward compatibility with any scripts that reference it.
"""

import sys
import os

# Add the dashboard directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))

# Import and run the advanced dashboard
from advanced_dashboard import app, socketio

if __name__ == '__main__':
    print("🚀 Starting Trading Dashboard on port 8090...")
    print("📊 Dashboard available at: http://localhost:8090")
    socketio.run(app, host='0.0.0.0', port=8090, debug=False, allow_unsafe_werkzeug=True)


