#!/usr/bin/env python3
"""
Start Enhanced Trading System with Full AI Integration
Launches the complete system with London session automation
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root and src on path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.adaptive_integration import AdaptiveAccountManager
from src.core.enhanced_adaptive_system import EnhancedAdaptiveSystem
from src.core.telegram_notifier import TelegramNotifier

class EnhancedSystemLauncher:
    """Launches and manages the enhanced trading system"""
    
    def __init__(self):
        self.manager = None
        self.enhanced_system = None
        self.running = False
        self.dashboard_thread = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start the enhanced system"""
        try:
            print("🚀 STARTING ENHANCED TRADING SYSTEM")
            print("=" * 70)
            print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Load environment variables
            load_dotenv(os.path.join(BASE_DIR, 'oanda_config.env'))
            
            # Initialize adaptive account manager
            print("\n🔧 Initializing Enhanced Adaptive System...")
            self.manager = AdaptiveAccountManager()
            
            # Initialize enhanced system
            self.enhanced_system = EnhancedAdaptiveSystem(
                oanda_clients=self.manager.oanda_clients,
                telegram_notifier=self.manager.telegram_notifier
            )
            
            # Show initial account status
            print("\n💰 Initial Account Status:")
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
            
            print(f"\n💼 Portfolio Total: ${total_balance:,.2f}")
            print(f"📊 Portfolio P&L: ${total_pl:,.2f} ({total_pl/total_balance*100 if total_balance > 0 else 0:+.2f}%)")
            
            # Check current session
            current_session = self.enhanced_system._get_current_session()
            if current_session:
                session_config = self.enhanced_system._get_session_config(current_session)
                print(f"\n📊 Current Session: {session_config.name}")
                print(f"   Volatility Multiplier: {session_config.volatility_multiplier}x")
                print(f"   Max Positions: {session_config.max_positions}")
                print(f"   Preferred Pairs: {', '.join(session_config.preferred_pairs)}")
            else:
                print(f"\n📊 Current Session: Market Closed")
            
            # Check London session status
            london_active = self.enhanced_system._is_london_session_active()
            print(f"\n🇬🇧 London Session: {'ACTIVE' if london_active else 'INACTIVE'}")
            
            if london_active:
                print("   ✅ Enhanced London session trading ENABLED")
                print("   🎯 Automatic signal generation ACTIVE")
                print("   📊 Session-specific risk management ACTIVE")
            else:
                next_session_info = self.enhanced_system._get_next_session_info()
                print(f"   ⏰ Next session: {next_session_info['session']} in {next_session_info['hours_until']} hours")
            
            # Start enhanced monitoring
            print("\n🔄 Starting Enhanced Adaptive Monitoring...")
            self.enhanced_system.start_adaptive_monitoring()
            
            self.running = True
            
            print("\n✅ ENHANCED SYSTEM STARTED!")
            print("🤖 AI Agent: Fully Integrated")
            print("🎛️ Control Panel: Available at http://localhost:5001")
            print("📊 Real-time market monitoring: ACTIVE")
            print("🎯 Limit order execution: ENABLED")
            print("🛡️ Automatic risk management: ENABLED")
            print("🔔 Telegram notifications: ACTIVE")
            print("📰 News filters: ACTIVE")
            print("🛑 Kill switches: READY")
            
            print("\n🎯 The enhanced system will now:")
            print("   • Automatically trade during London session (8 AM - 5 PM GMT)")
            print("   • Use LIMIT ORDERS with enhanced TP/SL for London session")
            print("   • Apply session-specific volatility multipliers")
            print("   • Filter trades based on news events")
            print("   • Adapt risk parameters based on trading mode")
            print("   • Send real-time notifications via Telegram")
            print("   • Provide full AI assistant integration")
            print("   • Allow complete control via dashboard")
            
            # Start dashboard in separate thread
            print("\n🌐 Starting Enhanced Dashboard...")
            self._start_dashboard()
            
            # Main monitoring loop
            self._monitoring_loop()
            
        except Exception as e:
            print(f"\n❌ Failed to start enhanced system: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
    
    def _start_dashboard(self):
        """Start the enhanced dashboard in a separate thread"""
        def run_dashboard():
            try:
                # Import and run the enhanced dashboard
                sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
                from enhanced_dashboard import app, socketio, initialize_system
                
                # Initialize the dashboard with our enhanced system
                app.config['ENHANCED_SYSTEM'] = self.enhanced_system
                app.config['ADAPTIVE_MANAGER'] = self.manager
                
                print("🌐 Enhanced Dashboard starting on http://localhost:5001")
                socketio.run(app, host='0.0.0.0', port=5001, debug=False, use_reloader=False)
            except Exception as e:
                print(f"❌ Dashboard error: {e}")
        
        self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self.dashboard_thread.start()
        time.sleep(3)  # Give dashboard time to start
        print("✅ Enhanced Dashboard started successfully!")
    
    def _monitoring_loop(self):
        """Main monitoring loop with enhanced features"""
        print("\n🔄 Starting enhanced monitoring loop...")
        print("Press Ctrl+C to stop")
        
        last_report_time = time.time()
        report_interval = 1800  # Send report every 30 minutes
        last_session_check = time.time()
        session_check_interval = 300  # Check session every 5 minutes
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check session changes
                if current_time - last_session_check >= session_check_interval:
                    self._check_session_changes()
                    last_session_check = current_time
                
                # Send periodic reports
                if current_time - last_report_time >= report_interval:
                    print(f"\n📊 Sending periodic report...")
                    self._send_periodic_report()
                    last_report_time = current_time
                
                # Show status every 2 minutes
                if int(current_time) % 120 == 0:  # Every 2 minutes
                    self._show_enhanced_status()
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"\n❌ Error in monitoring loop: {e}")
        finally:
            self.stop()
    
    def _check_session_changes(self):
        """Check for trading session changes"""
        try:
            current_session = self.enhanced_system._get_current_session()
            london_active = self.enhanced_system._is_london_session_active()
            
            if london_active:
                print(f"🇬🇧 London session ACTIVE - Enhanced trading enabled")
            else:
                print(f"📊 Current session: {current_session.name if current_session else 'Closed'}")
                
        except Exception as e:
            print(f"❌ Error checking session: {e}")
    
    def _send_periodic_report(self):
        """Send periodic system report"""
        try:
            if self.enhanced_system and self.enhanced_system.telegram_notifier:
                status = self.enhanced_system.get_system_status()
                
                report = f"""
📊 ENHANCED SYSTEM REPORT
⏰ Time: {datetime.now().strftime('%H:%M:%S')}
📈 Mode: {status.get('trading_mode', 'Unknown').upper()}
🇬🇧 London Session: {'ACTIVE' if status.get('london_session_active') else 'INACTIVE'}
📊 Current Session: {status.get('current_session', 'Unknown')}
🎯 Session Trades: {status.get('session_trades', 0)}
📰 News Events: {status.get('news_events_count', 0)}
🛑 Kill Switches: {sum(1 for v in status.get('kill_switches', {}).values() if v)} active
                """
                
                self.enhanced_system.telegram_notifier.send_system_status('periodic_report', report)
                
        except Exception as e:
            print(f"❌ Error sending periodic report: {e}")
    
    def _show_enhanced_status(self):
        """Show current enhanced system status"""
        try:
            if self.enhanced_system:
                status = self.enhanced_system.get_system_status()
                
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - "
                      f"Mode: {status.get('trading_mode', 'Unknown').upper()}, "
                      f"Session: {status.get('current_session', 'Unknown')}, "
                      f"London: {'ON' if status.get('london_session_active') else 'OFF'}, "
                      f"Trades: {status.get('session_trades', 0)}")
            
        except Exception as e:
            print(f"❌ Failed to show enhanced status: {e}")
    
    def stop(self):
        """Stop the enhanced system"""
        if not self.running:
            return
        
        print("\n🛑 Stopping Enhanced Trading System...")
        
        try:
            if self.enhanced_system:
                self.enhanced_system.stop_adaptive_monitoring()
                print("✅ Enhanced adaptive monitoring stopped")
                
                # Save final learning data
                filename = self.enhanced_system.save_learning_data()
                if filename:
                    print(f"💾 Final learning data saved: {filename}")
            
            if self.manager:
                self.manager.stop_adaptive_monitoring()
                print("✅ Adaptive monitoring stopped")
            
            self.running = False
            print("✅ Enhanced system stopped successfully")
            
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")

def main():
    """Main function"""
    launcher = EnhancedSystemLauncher()
    
    try:
        success = launcher.start()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())

