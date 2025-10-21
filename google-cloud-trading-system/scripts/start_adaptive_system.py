#!/usr/bin/env python3
"""
Start Adaptive Trading System
Launches the adaptive learning system for all OANDA accounts
"""

import os
import sys
import time
import signal
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.adaptive_integration import AdaptiveAccountManager

class AdaptiveSystemLauncher:
    """Launches and manages the adaptive trading system"""
    
    def __init__(self):
        self.manager = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start the adaptive system"""
        try:
            print("🚀 STARTING ADAPTIVE TRADING SYSTEM")
            print("=" * 60)
            print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Initialize the adaptive account manager
            print("\n🔧 Initializing Adaptive Account Manager...")
            self.manager = AdaptiveAccountManager()
            
            # Show initial account status
            print("\n📊 Initial Account Status:")
            account_status = self.manager.get_account_status()
            
            total_balance = 0
            total_pl = 0
            
            for account_name, status in account_status.items():
                if 'error' not in status:
                    pl_emoji = "📈" if status['total_pl'] >= 0 else "📉"
                    print(f"  {account_name}: {pl_emoji} ${status['total_pl']:,.2f} ({status['pl_percentage']:+.2f}%)")
                    print(f"    Balance: ${status['balance']:,.2f} | Positions: {status['open_positions']}")
                    total_balance += status['balance']
                    total_pl += status['total_pl']
                else:
                    print(f"  {account_name}: ❌ {status['error']}")
            
            print(f"\n💰 Portfolio Total: ${total_balance:,.2f}")
            print(f"📈 Portfolio P&L: ${total_pl:,.2f} ({total_pl/total_balance*100 if total_balance > 0 else 0:+.2f}%)")
            
            # Start adaptive monitoring
            print("\n🤖 Starting Adaptive Monitoring...")
            self.manager.start_adaptive_monitoring()
            self.running = True
            
            print("\n✅ ADAPTIVE SYSTEM STARTED SUCCESSFULLY!")
            print("📊 Real-time market monitoring active")
            print("🛡️ Automatic risk management enabled")
            print("🔔 Telegram notifications active")
            print("\n💡 The system will automatically:")
            print("   • Detect market volatility spikes")
            print("   • Adjust position sizes during high volatility")
            print("   • Pause trading during central bank events")
            print("   • Close positions during momentum reversals")
            print("   • Send alerts via Telegram")
            
            # Main monitoring loop
            self._monitoring_loop()
            
        except Exception as e:
            print(f"\n❌ Failed to start adaptive system: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        print("\n🔄 Starting monitoring loop...")
        print("Press Ctrl+C to stop")
        
        last_report_time = time.time()
        report_interval = 3600  # Send report every hour
        
        try:
            while self.running:
                current_time = time.time()
                
                # Send hourly reports
                if current_time - last_report_time >= report_interval:
                    print(f"\n📊 Sending hourly report...")
                    self.manager.send_daily_report()
                    last_report_time = current_time
                
                # Show status every 5 minutes
                if int(current_time) % 300 == 0:  # Every 5 minutes
                    self._show_status()
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"\n❌ Error in monitoring loop: {e}")
        finally:
            self.stop()
    
    def _show_status(self):
        """Show current system status"""
        try:
            system_status = self.manager.get_adaptive_system_status()
            
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - "
                  f"Condition: {system_status['current_condition'].replace('_', ' ').title()}, "
                  f"Signals: {system_status['active_signals']}")
            
        except Exception as e:
            print(f"❌ Failed to show status: {e}")
    
    def stop(self):
        """Stop the adaptive system"""
        if not self.running:
            return
        
        print("\n🛑 Stopping Adaptive Trading System...")
        
        try:
            if self.manager:
                self.manager.stop_adaptive_monitoring()
                print("✅ Adaptive monitoring stopped")
                
                # Save final learning data
                filename = self.manager.save_learning_data()
                if filename:
                    print(f"💾 Final learning data saved: {filename}")
                
                # Send shutdown notification
                self.manager.send_daily_report()  # This will show final status
                
            self.running = False
            print("✅ Adaptive system stopped successfully")
            
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")

def main():
    """Main function"""
    launcher = AdaptiveSystemLauncher()
    
    try:
        success = launcher.start()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())

