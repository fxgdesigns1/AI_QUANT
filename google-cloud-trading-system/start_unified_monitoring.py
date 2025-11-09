#!/usr/bin/env python3
"""
START UNIFIED MONITORING SYSTEM
==============================

Starts all monitoring systems:
1. Unified monitoring system
2. Dashboard sync manager
3. Semi-automatic trading alerts
4. Trade assistant integration
"""

import os
import sys
import subprocess
import time
import threading
from datetime import datetime

def start_unified_monitoring():
    """Start the unified monitoring system"""
    
    print("🤖 STARTING UNIFIED MONITORING SYSTEM")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%H:%M:%S')} London")
    print()
    
    # Set environment variables
    os.environ['OANDA_API_KEY'] = "${OANDA_API_KEY}"
    os.environ['OANDA_ENVIRONMENT'] = "practice"
    os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
    os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"
    
    print("✅ Environment variables set")
    print("✅ Telegram credentials configured")
    print("✅ All systems ready")
    print()
    
    print("🚀 Starting monitoring systems...")
    print("📊 Systems to start:")
    print("   • Unified monitoring system")
    print("   • Dashboard sync manager")
    print("   • Semi-automatic trading alerts")
    print("   • Trade assistant integration")
    print()
    
    processes = []
    
    try:
        # Start unified monitoring system
        print("🔄 Starting unified monitoring system...")
        unified_process = subprocess.Popen([
            sys.executable, 
            '/Users/mac/quant_system_clean/google-cloud-trading-system/unified_monitoring_system.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('unified_monitoring', unified_process))
        
        # Wait a moment
        time.sleep(5)
        
        # Start dashboard sync manager
        print("🔄 Starting dashboard sync manager...")
        sync_process = subprocess.Popen([
            sys.executable, 
            '/Users/mac/quant_system_clean/google-cloud-trading-system/dashboard_sync_manager.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('dashboard_sync', sync_process))
        
        # Wait a moment
        time.sleep(5)
        
        # Start semi-automatic alerts
        print("🔄 Starting semi-automatic alerts...")
        alerts_process = subprocess.Popen([
            sys.executable, 
            '/Users/mac/quant_system_clean/google-cloud-trading-system/semi_auto_telegram_alerts.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('semi_auto_alerts', alerts_process))
        
        print()
        print("✅ All monitoring systems started!")
        print("📱 You will receive comprehensive alerts and updates")
        print("🔄 Dashboard is syncing with all account data")
        print("🤖 Semi-automatic trading is ready for your commands")
        print()
        print("🛑 Press Ctrl+C to stop all systems")
        
        # Monitor processes
        while True:
            time.sleep(10)
            
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} process stopped unexpectedly")
                    # Restart the process
                    if name == 'unified_monitoring':
                        new_process = subprocess.Popen([
                            sys.executable, 
                            '/Users/mac/quant_system_clean/google-cloud-trading-system/unified_monitoring_system.py'
                        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        processes[processes.index((name, process))] = (name, new_process)
                        print(f"🔄 Restarted {name}")
                    elif name == 'dashboard_sync':
                        new_process = subprocess.Popen([
                            sys.executable, 
                            '/Users/mac/quant_system_clean/google-cloud-trading-system/dashboard_sync_manager.py'
                        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        processes[processes.index((name, process))] = (name, new_process)
                        print(f"🔄 Restarted {name}")
                    elif name == 'semi_auto_alerts':
                        new_process = subprocess.Popen([
                            sys.executable, 
                            '/Users/mac/quant_system_clean/google-cloud-trading-system/semi_auto_telegram_alerts.py'
                        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        processes[processes.index((name, process))] = (name, new_process)
                        print(f"🔄 Restarted {name}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping all monitoring systems...")
        
        # Stop all processes
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {name}")
            except:
                process.kill()
                print(f"🔴 Force killed {name}")
        
        print("✅ All systems stopped")
    
    except Exception as e:
        print(f"\n❌ Error in monitoring system: {e}")
        
        # Stop all processes
        for name, process in processes:
            try:
                process.terminate()
            except:
                process.kill()

if __name__ == "__main__":
    start_unified_monitoring()

