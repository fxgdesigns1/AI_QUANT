#!/usr/bin/env python3
"""
Deploy Adaptive Trading System
Final deployment script for the adaptive learning system
"""

import os
import sys
import subprocess
from datetime import datetime

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

def deploy_adaptive_system():
    """Deploy the adaptive system"""
    print("🚀 DEPLOYING ADAPTIVE TRADING SYSTEM")
    print("=" * 60)
    print(f"⏰ Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Run tests
    print("\n🧪 STEP 1: Running System Tests")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            sys.executable, 'scripts/test_adaptive_system.py'
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            print("✅ All tests passed successfully")
        else:
            print("❌ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False
    
    # Step 2: Check system requirements
    print("\n🔧 STEP 2: Checking System Requirements")
    print("-" * 40)
    
    # Check if OANDA config exists
    config_file = os.path.join(BASE_DIR, 'oanda_config.env')
    if os.path.exists(config_file):
        print("✅ OANDA configuration found")
    else:
        print("❌ OANDA configuration not found")
        return False
    
    # Check if adaptive config exists
    adaptive_config = os.path.join(BASE_DIR, 'config', 'adaptive_config.yaml')
    if os.path.exists(adaptive_config):
        print("✅ Adaptive system configuration found")
    else:
        print("❌ Adaptive system configuration not found")
        return False
    
    # Step 3: Create startup script
    print("\n📝 STEP 3: Creating Startup Script")
    print("-" * 40)
    
    startup_script = """#!/bin/bash
# Adaptive Trading System Startup Script
# Generated on {timestamp}

echo "🚀 Starting Adaptive Trading System..."
echo "⏰ Start Time: $(date)"

# Change to project directory
cd {project_dir}

# Start the adaptive system
python3 scripts/start_adaptive_system.py

echo "🛑 Adaptive Trading System Stopped"
echo "⏰ Stop Time: $(date)"
""".format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        project_dir=BASE_DIR
    )
    
    startup_file = os.path.join(BASE_DIR, 'start_adaptive.sh')
    with open(startup_file, 'w') as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod(startup_file, 0o755)
    print(f"✅ Startup script created: {startup_file}")
    
    # Step 4: Create systemd service (optional)
    print("\n⚙️ STEP 4: Creating System Service")
    print("-" * 40)
    
    service_content = f"""[Unit]
Description=Adaptive Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory={BASE_DIR}
ExecStart=/usr/bin/python3 {BASE_DIR}/scripts/start_adaptive_system.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = os.path.join(BASE_DIR, 'adaptive-trading-system.service')
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"✅ System service created: {service_file}")
    print("💡 To install as system service:")
    print(f"   sudo cp {service_file} /etc/systemd/system/")
    print("   sudo systemctl enable adaptive-trading-system")
    print("   sudo systemctl start adaptive-trading-system")
    
    # Step 5: Create monitoring dashboard
    print("\n📊 STEP 5: Creating Monitoring Dashboard")
    print("-" * 40)
    
    dashboard_script = """#!/usr/bin/env python3
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
        
        return jsonify({{'html': html}})
        
    except Exception as e:
        return jsonify({{'error': str(e)}})

if __name__ == '__main__':
    print("🌐 Starting Adaptive System Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
"""
    
    dashboard_file = os.path.join(BASE_DIR, 'scripts', 'dashboard.py')
    with open(dashboard_file, 'w') as f:
        f.write(dashboard_script)
    
    print(f"✅ Monitoring dashboard created: {dashboard_file}")
    print("💡 To start dashboard: python3 scripts/dashboard.py")
    
    # Step 6: Final deployment summary
    print("\n🎉 DEPLOYMENT COMPLETE!")
    print("=" * 60)
    
    print("\n📋 DEPLOYMENT SUMMARY:")
    print("✅ Adaptive system tests passed")
    print("✅ Configuration files validated")
    print("✅ Startup script created")
    print("✅ System service created")
    print("✅ Monitoring dashboard created")
    
    print("\n🚀 TO START THE ADAPTIVE SYSTEM:")
    print(f"   ./start_adaptive.sh")
    print("   OR")
    print(f"   python3 scripts/start_adaptive_system.py")
    
    print("\n📊 TO MONITOR THE SYSTEM:")
    print("   python3 scripts/dashboard.py")
    print("   Then open: http://localhost:5000")
    
    print("\n🔧 TO INSTALL AS SYSTEM SERVICE:")
    print(f"   sudo cp {service_file} /etc/systemd/system/")
    print("   sudo systemctl enable adaptive-trading-system")
    print("   sudo systemctl start adaptive-trading-system")
    
    print("\n🛡️ ADAPTIVE SYSTEM FEATURES:")
    print("   • Real-time market condition detection")
    print("   • Automatic risk parameter adjustment")
    print("   • Strategy-specific adaptations")
    print("   • Telegram notifications")
    print("   • Emergency position management")
    print("   • Learning data collection")
    
    print(f"\n⏰ Deployment completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == '__main__':
    success = deploy_adaptive_system()
    sys.exit(0 if success else 1)

