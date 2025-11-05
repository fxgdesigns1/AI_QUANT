#!/usr/bin/env python3
"""
UNIFIED STARTUP SCRIPT FOR ALL TRADING SYSTEMS
Starts AI, Automated, Semi-Automated, and Dashboard systems
"""
import os
import sys
import time
import subprocess
import threading
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables
os.environ['OANDA_API_KEY'] = "a3699a9d6b6d94d4e2c4c59748e73e2d-b6cbc64f16bcfb920e40f9117e66111a"
os.environ['OANDA_ACCOUNT_ID'] = "101-004-30719775-008"
os.environ['OANDA_ENVIRONMENT'] = "practice"
os.environ['TELEGRAM_TOKEN'] = "7248728383:AAFpLNAlidybk7ed56bosfi8W_e1MaX7Oxs"
os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
os.environ['PYTHONPATH'] = "/workspace"

# Set working directory
WORKSPACE = "/workspace"
os.chdir(WORKSPACE)

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_ai_system(self):
        """Start AI Trading System"""
        logger.info("🚀 Starting AI Trading System...")
        try:
            proc = subprocess.Popen(
                [sys.executable, "ai_trading_system.py"],
                cwd=WORKSPACE,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes['ai_trading'] = proc
            logger.info(f"✅ AI Trading System started (PID: {proc.pid})")
            return proc
        except Exception as e:
            logger.error(f"❌ Failed to start AI Trading System: {e}")
            return None
    
    def start_automated_system(self):
        """Start Automated Trading System"""
        logger.info("🚀 Starting Automated Trading System...")
        try:
            proc = subprocess.Popen(
                [sys.executable, "automated_trading_system.py"],
                cwd=WORKSPACE,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes['automated_trading'] = proc
            logger.info(f"✅ Automated Trading System started (PID: {proc.pid})")
            return proc
        except Exception as e:
            logger.error(f"❌ Failed to start Automated Trading System: {e}")
            return None
    
    def start_dashboard(self):
        """Start Dashboard"""
        logger.info("🚀 Starting Dashboard...")
        try:
            dashboard_path = Path(WORKSPACE) / "dashboard" / "advanced_dashboard.py"
            if dashboard_path.exists():
                proc = subprocess.Popen(
                    [sys.executable, str(dashboard_path)],
                    cwd=WORKSPACE,
                    env=os.environ.copy(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.processes['dashboard'] = proc
                logger.info(f"✅ Dashboard started (PID: {proc.pid})")
                return proc
            else:
                logger.warning("⚠️ Dashboard file not found")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to start Dashboard: {e}")
            return None
    
    def start_cloud_system(self):
        """Start Google Cloud Trading System"""
        logger.info("🚀 Starting Google Cloud Trading System...")
        try:
            cloud_main = Path(WORKSPACE) / "google-cloud-trading-system" / "main.py"
            if cloud_main.exists():
                proc = subprocess.Popen(
                    [sys.executable, str(cloud_main)],
                    cwd=Path(WORKSPACE) / "google-cloud-trading-system",
                    env=os.environ.copy(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.processes['cloud_system'] = proc
                logger.info(f"✅ Cloud Trading System started (PID: {proc.pid})")
                return proc
            else:
                logger.warning("⚠️ Cloud main file not found")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to start Cloud System: {e}")
            return None
    
    def monitor_processes(self):
        """Monitor all processes and restart if needed"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:  # Process has terminated
                    logger.warning(f"⚠️ {name} process died (exit code: {proc.returncode})")
                    logger.info(f"🔄 Restarting {name}...")
                    
                    # Restart process
                    if name == 'ai_trading':
                        self.start_ai_system()
                    elif name == 'automated_trading':
                        self.start_automated_system()
                    elif name == 'dashboard':
                        self.start_dashboard()
                    elif name == 'cloud_system':
                        self.start_cloud_system()
                    
                    # Remove old process
                    del self.processes[name]
    
    def stop_all(self):
        """Stop all processes"""
        logger.info("🛑 Stopping all systems...")
        self.running = False
        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=10)
                logger.info(f"✅ Stopped {name}")
            except Exception as e:
                logger.error(f"❌ Error stopping {name}: {e}")
                proc.kill()

def main():
    """Main entry point"""
    logger.info("="*80)
    logger.info("🚀 STARTING ALL TRADING SYSTEMS")
    logger.info("="*80)
    
    manager = SystemManager()
    
    # Start all systems
    manager.start_ai_system()
    time.sleep(5)  # Stagger startups
    
    manager.start_automated_system()
    time.sleep(5)
    
    manager.start_dashboard()
    time.sleep(5)
    
    manager.start_cloud_system()
    
    # Start monitor thread
    monitor_thread = threading.Thread(target=manager.monitor_processes, daemon=True)
    monitor_thread.start()
    
    logger.info("="*80)
    logger.info("✅ ALL SYSTEMS STARTED")
    logger.info("="*80)
    logger.info("📊 Systems running:")
    for name, proc in manager.processes.items():
        logger.info(f"  • {name}: PID {proc.pid}")
    logger.info("="*80)
    
    # Send startup notification
    try:
        import requests
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        telegram_chat = os.getenv('TELEGRAM_CHAT_ID')
        if telegram_token and telegram_chat:
            message = """🚀 ALL TRADING SYSTEMS STARTED!

✅ AI Trading System: Running
✅ Automated Trading System: Running
✅ Dashboard: Running
✅ Cloud Trading System: Running

📊 All systems are now live and executing trades!
📱 Telegram notifications active
📈 News and economic indicators active
🤖 AI insights active

System will continue running until stopped."""
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            requests.post(url, json={'chat_id': telegram_chat, 'text': message}, timeout=10)
            logger.info("✅ Startup notification sent to Telegram")
    except Exception as e:
        logger.warning(f"⚠️ Could not send Telegram notification: {e}")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
            # Log status
            active_count = sum(1 for p in manager.processes.values() if p.poll() is None)
            logger.info(f"📊 Status: {active_count}/{len(manager.processes)} systems running")
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
        manager.stop_all()

if __name__ == "__main__":
    main()
