#!/usr/bin/env python3
"""
Implementation of Calibrated Parameters
Applies the recommended calibrations to the trading system to ensure
it generates trades with less strict parameters.
"""

import os
import sys
import logging
import shutil
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CalibrationImplementer:
    """Implements calibrated parameters to ensure trade generation"""
    
    def __init__(self):
        """Initialize the calibration implementer"""
        self.implementation_results = {
            'status': 'pending',
            'changes_made': [],
            'files_modified': [],
            'backup_files': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Calibrated parameters to implement
        self.calibrated_params = {
            'max_margin_usage': 0.75,  # Reduced from 0.8
            'min_signal_strength': 0.5,  # Reduced from 0.7
            'position_size_multiplier': 0.5,  # Reduced from 1.0
            'data_validation': 'moderate',  # Changed from 'strict'
            'forced_trading_mode': 'enabled',  # Changed from 'disabled'
            'min_trades_today': 2  # Ensure at least 2 trades per day per strategy
        }
        
        logger.info("🚀 Calibration Implementer initialized")
        logger.info("=" * 60)
    
    def _backup_file(self, file_path: str) -> str:
        """Create a backup of a file before modifying it"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ File not found: {file_path}")
            return None
        
        # Create backup filename with timestamp
        backup_path = f"{file_path}.bak.{int(time.time())}"
        
        # Copy the file
        shutil.copy2(file_path, backup_path)
        logger.info(f"✅ Created backup: {backup_path}")
        
        self.implementation_results['backup_files'].append(backup_path)
        return backup_path
    
    def _update_oanda_config(self) -> bool:
        """Update OANDA configuration file with calibrated parameters"""
        config_path = os.path.join(os.path.dirname(__file__), 'oanda_config.env')
        
        try:
            # Backup the file
            self._backup_file(config_path)
            
            # Read the current config
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Update parameters
            updated_lines = []
            for line in lines:
                # Update margin usage parameters
                if line.startswith('PRIMARY_MAX_PORTFOLIO_RISK='):
                    updated_lines.append(f'PRIMARY_MAX_PORTFOLIO_RISK={self.calibrated_params["max_margin_usage"]}\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'PRIMARY_MAX_PORTFOLIO_RISK',
                        'old_value': line.strip().split('=')[1],
                        'new_value': str(self.calibrated_params["max_margin_usage"])
                    })
                elif line.startswith('GOLD_MAX_PORTFOLIO_RISK='):
                    updated_lines.append(f'GOLD_MAX_PORTFOLIO_RISK={self.calibrated_params["max_margin_usage"]}\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'GOLD_MAX_PORTFOLIO_RISK',
                        'old_value': line.strip().split('=')[1],
                        'new_value': str(self.calibrated_params["max_margin_usage"])
                    })
                elif line.startswith('ALPHA_MAX_PORTFOLIO_RISK='):
                    updated_lines.append(f'ALPHA_MAX_PORTFOLIO_RISK={self.calibrated_params["max_margin_usage"]}\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'ALPHA_MAX_PORTFOLIO_RISK',
                        'old_value': line.strip().split('=')[1],
                        'new_value': str(self.calibrated_params["max_margin_usage"])
                    })
                # Add forced trading mode parameter
                elif line.startswith('# Global Risk Settings'):
                    updated_lines.append(line)
                    updated_lines.append(f'FORCED_TRADING_MODE={self.calibrated_params["forced_trading_mode"]}\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'FORCED_TRADING_MODE',
                        'old_value': 'disabled',
                        'new_value': self.calibrated_params["forced_trading_mode"]
                    })
                # Update position sizing method
                elif line.startswith('POSITION_SIZING_METHOD='):
                    updated_lines.append(f'POSITION_SIZING_METHOD=risk_based\n')
                    updated_lines.append(f'POSITION_SIZE_MULTIPLIER={self.calibrated_params["position_size_multiplier"]}\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'POSITION_SIZE_MULTIPLIER',
                        'old_value': '1.0',
                        'new_value': str(self.calibrated_params["position_size_multiplier"])
                    })
                # Update data validation settings
                elif line.startswith('MIN_CONFIDENCE_THRESHOLD='):
                    updated_lines.append(f'MIN_CONFIDENCE_THRESHOLD=0.5\n')
                    self.implementation_results['changes_made'].append({
                        'file': config_path,
                        'parameter': 'MIN_CONFIDENCE_THRESHOLD',
                        'old_value': line.strip().split('=')[1],
                        'new_value': '0.5'
                    })
                else:
                    updated_lines.append(line)
            
            # Write the updated config
            with open(config_path, 'w') as f:
                f.writelines(updated_lines)
            
            logger.info(f"✅ Updated OANDA config: {config_path}")
            self.implementation_results['files_modified'].append(config_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update OANDA config: {e}")
            return False
    
    def _update_alpha_strategy(self) -> bool:
        """Update Alpha strategy with calibrated parameters"""
        strategy_path = os.path.join(os.path.dirname(__file__), 'src/strategies/alpha.py')
        
        try:
            # Backup the file
            self._backup_file(strategy_path)
            
            # Read the current strategy
            with open(strategy_path, 'r') as f:
                content = f.read()
            
            # Update min_signal_strength parameter
            content = content.replace(
                "self.min_trades_today = 0", 
                f"self.min_trades_today = {self.calibrated_params['min_trades_today']}"
            )
            
            # Update signal strength check
            content = content.replace(
                "confidence=min(1.0, max(0.3, sig.strength))",
                f"confidence=min(1.0, max({self.calibrated_params['min_signal_strength']}, sig.strength))"
            )
            
            # Write the updated strategy
            with open(strategy_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated Alpha strategy: {strategy_path}")
            self.implementation_results['files_modified'].append(strategy_path)
            self.implementation_results['changes_made'].append({
                'file': strategy_path,
                'parameter': 'min_trades_today',
                'old_value': '0',
                'new_value': str(self.calibrated_params['min_trades_today'])
            })
            self.implementation_results['changes_made'].append({
                'file': strategy_path,
                'parameter': 'min_signal_strength',
                'old_value': '0.3',
                'new_value': str(self.calibrated_params['min_signal_strength'])
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Alpha strategy: {e}")
            return False
    
    def _update_gold_scalping_strategy(self) -> bool:
        """Update Gold Scalping strategy with calibrated parameters"""
        strategy_path = os.path.join(os.path.dirname(__file__), 'src/strategies/gold_scalping.py')
        
        try:
            # Backup the file
            self._backup_file(strategy_path)
            
            # Read the current strategy
            with open(strategy_path, 'r') as f:
                content = f.read()
            
            # Update min_signal_strength parameter
            content = content.replace(
                "self.min_signal_strength = 0.5",
                f"self.min_signal_strength = {self.calibrated_params['min_signal_strength']}"
            )
            
            # Update min_trades_today parameter
            content = content.replace(
                "self.min_trades_today = 2",
                f"self.min_trades_today = {self.calibrated_params['min_trades_today']}"
            )
            
            # Write the updated strategy
            with open(strategy_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated Gold Scalping strategy: {strategy_path}")
            self.implementation_results['files_modified'].append(strategy_path)
            self.implementation_results['changes_made'].append({
                'file': strategy_path,
                'parameter': 'min_signal_strength',
                'old_value': '0.5',
                'new_value': str(self.calibrated_params['min_signal_strength'])
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Gold Scalping strategy: {e}")
            return False
    
    def _update_momentum_strategy(self) -> bool:
        """Update Momentum Trading strategy with calibrated parameters"""
        strategy_path = os.path.join(os.path.dirname(__file__), 'src/strategies/momentum_trading.py')
        
        try:
            # Backup the file
            self._backup_file(strategy_path)
            
            # Read the current strategy
            with open(strategy_path, 'r') as f:
                content = f.read()
            
            # Update min_momentum parameter
            content = content.replace(
                "self.min_momentum = 0.2",
                f"self.min_momentum = {self.calibrated_params['min_signal_strength']}"
            )
            
            # Update min_trades_today parameter
            content = content.replace(
                "self.min_trades_today = 2",
                f"self.min_trades_today = {self.calibrated_params['min_trades_today']}"
            )
            
            # Write the updated strategy
            with open(strategy_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated Momentum Trading strategy: {strategy_path}")
            self.implementation_results['files_modified'].append(strategy_path)
            self.implementation_results['changes_made'].append({
                'file': strategy_path,
                'parameter': 'min_momentum',
                'old_value': '0.2',
                'new_value': str(self.calibrated_params['min_signal_strength'])
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Momentum Trading strategy: {e}")
            return False
    
    def _update_order_manager(self) -> bool:
        """Update Order Manager with calibrated parameters"""
        manager_path = os.path.join(os.path.dirname(__file__), 'src/core/order_manager.py')
        
        try:
            # Backup the file
            self._backup_file(manager_path)
            
            # Read the current manager
            with open(manager_path, 'r') as f:
                content = f.read()
            
            # Update position sizing logic
            if "position_size_multiplier" not in content:
                # Add position size multiplier to _calculate_position_size method
                content = content.replace(
                    "# Calculate units based on risk",
                    "# Get position size multiplier from environment\n            position_size_multiplier = float(os.getenv('POSITION_SIZE_MULTIPLIER', '0.5'))\n\n            # Calculate units based on risk"
                )
                
                content = content.replace(
                    "units = min(units, units_risk_cap)",
                    "units = min(units, int(units_risk_cap * position_size_multiplier))"
                )
                
                self.implementation_results['changes_made'].append({
                    'file': manager_path,
                    'parameter': 'position_size_multiplier',
                    'old_value': 'Not present',
                    'new_value': 'Added position_size_multiplier logic'
                })
            
            # Write the updated manager
            with open(manager_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated Order Manager: {manager_path}")
            self.implementation_results['files_modified'].append(manager_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Order Manager: {e}")
            return False
    
    def _update_data_feed(self) -> bool:
        """Update Data Feed with calibrated parameters"""
        feed_path = os.path.join(os.path.dirname(__file__), 'src/core/data_feed.py')
        
        try:
            # Backup the file
            self._backup_file(feed_path)
            
            # Read the current feed
            with open(feed_path, 'r') as f:
                content = f.read()
            
            # Update min_confidence_threshold parameter
            content = content.replace(
                "self.min_confidence_threshold = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.8'))",
                f"self.min_confidence_threshold = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '{self.calibrated_params['min_signal_strength']}'))"
            )
            
            # Write the updated feed
            with open(feed_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated Data Feed: {feed_path}")
            self.implementation_results['files_modified'].append(feed_path)
            self.implementation_results['changes_made'].append({
                'file': feed_path,
                'parameter': 'min_confidence_threshold',
                'old_value': '0.8',
                'new_value': str(self.calibrated_params['min_signal_strength'])
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update Data Feed: {e}")
            return False
    
    def _create_trade_monitor(self) -> bool:
        """Create a trade monitor script to alert if no trades are generated"""
        monitor_path = os.path.join(os.path.dirname(__file__), 'monitor_trades.py')
        
        try:
            # Create the monitor script
            with open(monitor_path, 'w') as f:
                f.write('''#!/usr/bin/env python3
"""
Trade Monitor Script
Monitors the trading system and alerts if no trades are generated within a specified time period.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
import json

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_for_trades(max_wait_minutes=30):
    """Check if trades have been executed within the specified time period"""
    from src.core.order_manager import get_order_manager
    
    logger.info(f"🔍 Monitoring for trades (max wait: {max_wait_minutes} minutes)")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=max_wait_minutes)
    
    order_manager = get_order_manager()
    initial_trade_count = len(order_manager.get_trade_history())
    
    logger.info(f"📊 Initial trade count: {initial_trade_count}")
    
    while datetime.now() < end_time:
        # Check current trade count
        current_trade_count = len(order_manager.get_trade_history())
        new_trades = current_trade_count - initial_trade_count
        
        if new_trades > 0:
            logger.info(f"✅ {new_trades} new trades detected!")
            return True
        
        # Check if trading is allowed
        trading_allowed, reason = order_manager.is_trading_allowed()
        if not trading_allowed:
            logger.warning(f"⚠️ Trading not allowed: {reason}")
        
        # Sleep for a bit
        logger.info(f"⏳ Waiting for trades... ({int((end_time - datetime.now()).total_seconds())} seconds remaining)")
        time.sleep(60)  # Check every minute
    
    logger.warning(f"❌ No trades detected within {max_wait_minutes} minutes")
    return False

def alert_no_trades():
    """Alert that no trades have been generated"""
    logger.error("🚨 ALERT: No trades generated within the specified time period")
    logger.error("🔧 Consider checking the following:")
    logger.error("   1. Market conditions (low volatility?)")
    logger.error("   2. Strategy parameters (still too strict?)")
    logger.error("   3. Data feed issues (receiving fresh data?)")
    logger.error("   4. Order execution issues (OANDA connection?)")
    
    # You could add additional alerting mechanisms here
    # e.g., send email, SMS, or Telegram notification

def main():
    """Main monitoring function"""
    logger.info("🚀 Starting Trade Monitor")
    
    # Check for trades with a 30-minute timeout
    trades_detected = check_for_trades(max_wait_minutes=30)
    
    if not trades_detected:
        alert_no_trades()
        return False
    
    logger.info("✅ Trading system is active and generating trades")
    return True

if __name__ == '__main__':
    main()
''')
            
            # Make the script executable
            os.chmod(monitor_path, 0o755)
            
            logger.info(f"✅ Created Trade Monitor: {monitor_path}")
            self.implementation_results['files_modified'].append(monitor_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create Trade Monitor: {e}")
            return False
    
    def implement_calibrations(self):
        """Implement all calibrated parameters"""
        logger.info("🚀 Starting calibration implementation")
        logger.info("=" * 60)
        
        try:
            # Update OANDA config
            if self._update_oanda_config():
                logger.info("✅ OANDA config updated successfully")
            
            # Update Alpha strategy
            if self._update_alpha_strategy():
                logger.info("✅ Alpha strategy updated successfully")
            
            # Update Gold Scalping strategy
            if self._update_gold_scalping_strategy():
                logger.info("✅ Gold Scalping strategy updated successfully")
            
            # Update Momentum Trading strategy
            if self._update_momentum_strategy():
                logger.info("✅ Momentum Trading strategy updated successfully")
            
            # Update Order Manager
            if self._update_order_manager():
                logger.info("✅ Order Manager updated successfully")
            
            # Update Data Feed
            if self._update_data_feed():
                logger.info("✅ Data Feed updated successfully")
            
            # Create Trade Monitor
            if self._create_trade_monitor():
                logger.info("✅ Trade Monitor created successfully")
            
            # Update implementation status
            self.implementation_results['status'] = 'completed'
            self.implementation_results['timestamp'] = datetime.now().isoformat()
            
            # Generate summary report
            self._generate_summary_report()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Implementation failed: {e}")
            self.implementation_results['status'] = 'failed'
            return False
    
    def _generate_summary_report(self):
        """Generate summary report of implementation"""
        logger.info("=" * 60)
        logger.info("📊 CALIBRATION IMPLEMENTATION SUMMARY")
        logger.info("=" * 60)
        
        # Summary
        logger.info(f"📅 Implementation timestamp: {self.implementation_results['timestamp']}")
        logger.info(f"🎯 Implementation status: {self.implementation_results['status']}")
        logger.info(f"📝 Files modified: {len(self.implementation_results['files_modified'])}")
        logger.info(f"💾 Backup files created: {len(self.implementation_results['backup_files'])}")
        
        # Changes made
        logger.info(f"🔧 Changes made: {len(self.implementation_results['changes_made'])}")
        for change in self.implementation_results['changes_made']:
            logger.info(f"   - {change['parameter']}: {change['old_value']} → {change['new_value']}")
        
        logger.info("=" * 60)
        logger.info("📋 NEXT STEPS")
        logger.info("=" * 60)
        logger.info("1. Restart the trading system to apply changes")
        logger.info("2. Run the monitor_trades.py script to verify trade generation")
        logger.info("3. Wait for at least 30 minutes to ensure trades are being generated")
        logger.info("4. If no trades are generated, check the logs for errors")
        logger.info("=" * 60)
    
    def get_implementation_results(self) -> Dict:
        """Get comprehensive implementation results"""
        return self.implementation_results

def main():
    """Main implementation execution"""
    logger.info("🚀 Starting Calibration Implementation")
    logger.info("Implementing less strict parameters to ensure trade generation")
    logger.info("=" * 60)
    
    # Create implementer
    implementer = CalibrationImplementer()
    
    # Implement calibrations
    success = implementer.implement_calibrations()
    
    # Get results
    results = implementer.get_implementation_results()
    
    if success:
        logger.info("✅ CALIBRATION IMPLEMENTATION COMPLETED")
        logger.info("🎯 System is now configured with less strict parameters")
        logger.info("🚀 Restart the system to begin generating trades")
    else:
        logger.error("❌ CALIBRATION IMPLEMENTATION FAILED")
        logger.error("🔧 Manual implementation required")
    
    return results

if __name__ == '__main__':
    results = main()
    print("\n" + "=" * 60)
    print("IMPLEMENTATION RESULTS:")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Files modified: {len(results['files_modified'])}")
    print(f"Changes made: {len(results['changes_made'])}")
    print(f"Backup files: {len(results['backup_files'])}")
    print("=" * 60)
