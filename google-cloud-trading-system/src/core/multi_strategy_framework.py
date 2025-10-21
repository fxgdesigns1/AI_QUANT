#!/usr/bin/env python3
"""
Multi-Strategy Testing Framework - Main Integration
Comprehensive integration of all framework components
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .strategy_manager import get_strategy_manager
from .strategy_executor import get_multi_strategy_executor
from .data_collector import get_data_collector
from .backtesting_integration import get_backtesting_integration
from .performance_monitor import get_performance_monitor
from .dynamic_account_manager import get_account_manager
from .telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiStrategyFramework:
    """Main integration class for multi-strategy testing framework"""
    
    def __init__(self):
        """Initialize the complete multi-strategy framework"""
        # Core components
        self.strategy_manager = get_strategy_manager()
        self.multi_executor = get_multi_strategy_executor()
        self.data_collector = get_data_collector()
        self.backtesting_integration = get_backtesting_integration()
        self.performance_monitor = get_performance_monitor()
        self.account_manager = get_account_manager()
        self.telegram_notifier = TelegramNotifier()
        
        # Framework state
        self.is_running = False
        self.framework_thread = None
        self.startup_time = None
        
        # System health
        self.system_health = {
            'strategy_manager': False,
            'multi_executor': False,
            'data_collector': False,
            'backtesting_integration': False,
            'performance_monitor': False,
            'account_manager': False
        }
        
        logger.info("🎯 Multi-Strategy Testing Framework initialized")
    
    def start_framework(self):
        """Start the complete multi-strategy testing framework"""
        if self.is_running:
            logger.warning("Multi-strategy framework already running")
            return
        
        try:
            logger.info("🚀 Starting Multi-Strategy Testing Framework...")
            self.startup_time = datetime.now()
            
            # Validate system health
            self._validate_system_health()
            
            if not all(self.system_health.values()):
                logger.error("❌ System health check failed - not all components are ready")
                return False
            
            # Start all components in sequence
            self._start_all_components()
            
            # Start main framework thread
            self.is_running = True
            self.framework_thread = threading.Thread(
                target=self._framework_monitoring_loop,
                daemon=True
            )
            self.framework_thread.start()
            
            logger.info("✅ Multi-Strategy Testing Framework started successfully")
            
            # Send startup notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    "🎯 Multi-Strategy Testing Framework Started\n\n"
                    "📊 Components Active:\n"
                    f"• Strategy Manager: ✅\n"
                    f"• Multi-Strategy Executor: ✅\n"
                    f"• Data Collector: ✅\n"
                    f"• Backtesting Integration: ✅\n"
                    f"• Performance Monitor: ✅\n"
                    f"• Account Manager: ✅\n\n"
                    "🚀 Framework ready for multi-strategy testing and optimization"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start multi-strategy framework: {e}")
            return False
    
    def stop_framework(self):
        """Stop the multi-strategy testing framework"""
        if not self.is_running:
            logger.warning("Multi-strategy framework not running")
            return
        
        try:
            logger.info("🛑 Stopping Multi-Strategy Testing Framework...")
            self.is_running = False
            
            # Stop all components
            self._stop_all_components()
            
            # Wait for framework thread
            if self.framework_thread:
                self.framework_thread.join(timeout=10)
            
            logger.info("✅ Multi-Strategy Testing Framework stopped")
            
            # Send shutdown notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    "🛑 Multi-Strategy Testing Framework Stopped\n"
                    "📊 All components safely shut down"
                )
            
        except Exception as e:
            logger.error(f"❌ Error stopping multi-strategy framework: {e}")
    
    def _validate_system_health(self):
        """Validate that all system components are healthy"""
        try:
            # Check strategy manager
            self.system_health['strategy_manager'] = len(self.strategy_manager.strategies) > 0
            
            # Check account manager
            self.system_health['account_manager'] = len(self.account_manager.get_active_accounts()) > 0
            
            # Check other components (simplified health checks)
            self.system_health['multi_executor'] = True
            self.system_health['data_collector'] = True
            self.system_health['backtesting_integration'] = True
            self.system_health['performance_monitor'] = True
            
            logger.info(f"🔍 System health check: {self.system_health}")
            
        except Exception as e:
            logger.error(f"❌ System health validation failed: {e}")
    
    def _start_all_components(self):
        """Start all framework components"""
        try:
            # Start strategy manager multi-strategy testing
            self.strategy_manager.start_multi_strategy_testing()
            
            # Initialize and start executors
            self.multi_executor.initialize_executors()
            self.multi_executor.start_all_executors()
            
            # Start data collection
            self.data_collector.start_collection()
            
            # Start backtesting auto-export
            self.backtesting_integration.start_auto_export()
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            logger.info("✅ All framework components started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start framework components: {e}")
            raise
    
    def _stop_all_components(self):
        """Stop all framework components"""
        try:
            # Stop components in reverse order
            self.performance_monitor.stop_monitoring()
            self.backtesting_integration.stop_auto_export()
            self.data_collector.stop_collection()
            self.multi_executor.stop_all_executors()
            self.strategy_manager.stop_multi_strategy_testing()
            
            logger.info("✅ All framework components stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping framework components: {e}")
    
    def _framework_monitoring_loop(self):
        """Main framework monitoring loop"""
        while self.is_running:
            try:
                # Monitor system health
                self._monitor_system_health()
                
                # Check for framework-level issues
                self._check_framework_issues()
                
                # Update framework status
                self._update_framework_status()
                
                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Error in framework monitoring loop: {e}")
                time.sleep(120)  # Wait longer on error
    
    def _monitor_system_health(self):
        """Monitor health of all system components"""
        try:
            # Check if components are still running
            if not self.strategy_manager.is_running:
                logger.warning("⚠️ Strategy Manager not running")
            
            if not self.data_collector.is_collecting:
                logger.warning("⚠️ Data Collector not collecting")
            
            if not self.performance_monitor.is_monitoring:
                logger.warning("⚠️ Performance Monitor not monitoring")
            
            # Check execution status
            execution_status = self.multi_executor.get_all_execution_status()
            active_executors = execution_status.get('active_executors', 0)
            
            if active_executors == 0:
                logger.warning("⚠️ No active strategy executors")
            
        except Exception as e:
            logger.error(f"❌ System health monitoring error: {e}")
    
    def _check_framework_issues(self):
        """Check for framework-level issues and handle them"""
        try:
            # Check for critical performance issues
            dashboard_data = self.performance_monitor.get_performance_dashboard_data()
            
            if dashboard_data:
                summary = dashboard_data.get('summary', {})
                max_drawdown = summary.get('max_drawdown', 0)
                
                # Alert if drawdown is too high
                if max_drawdown > 10:  # 10% drawdown
                    logger.warning(f"🚨 High drawdown detected: {max_drawdown:.2f}%")
                    
                    if self.telegram_notifier:
                        self.telegram_notifier.send_message(
                            f"🚨 Framework Alert: High Drawdown\n"
                            f"📉 Current Drawdown: {max_drawdown:.2f}%\n"
                            f"⚠️ Consider reviewing strategy performance"
                        )
            
        except Exception as e:
            logger.error(f"❌ Framework issue checking error: {e}")
    
    def _update_framework_status(self):
        """Update framework status information"""
        try:
            # This could be used to update a status file or database
            # For now, just log the status
            uptime = datetime.now() - self.startup_time if self.startup_time else timedelta(0)
            
            logger.info(f"📊 Framework Status - Uptime: {uptime}, Running: {self.is_running}")
            
        except Exception as e:
            logger.error(f"❌ Framework status update error: {e}")
    
    def get_framework_status(self) -> Dict[str, Any]:
        """Get comprehensive framework status"""
        try:
            uptime = datetime.now() - self.startup_time if self.startup_time else timedelta(0)
            
            # Get component statuses
            strategy_status = self.strategy_manager.get_system_status()
            execution_status = self.multi_executor.get_all_execution_status()
            collection_status = self.data_collector.get_collection_status()
            integration_status = self.backtesting_integration.get_integration_status()
            monitoring_status = self.performance_monitor.get_monitoring_status()
            account_status = self.account_manager.get_all_accounts_status()
            
            return {
                'framework_running': self.is_running,
                'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                'uptime_seconds': uptime.total_seconds(),
                'system_health': self.system_health,
                'components': {
                    'strategy_manager': strategy_status,
                    'multi_executor': execution_status,
                    'data_collector': collection_status,
                    'backtesting_integration': integration_status,
                    'performance_monitor': monitoring_status,
                    'account_manager': {
                        'total_accounts': len(account_status),
                        'active_accounts': len([acc for acc in account_status.values() if acc.get('status') == 'active'])
                    }
                },
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get framework status: {e}")
            return {}
    
    def get_comprehensive_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for the UI"""
        try:
            # Get performance dashboard data
            performance_data = self.performance_monitor.get_performance_dashboard_data()
            
            # Get strategy performance comparison
            strategy_comparison = self.strategy_manager.get_strategy_performance_comparison()
            
            # Get account status
            account_status = self.account_manager.get_all_accounts_status()
            
            # Get execution status
            execution_status = self.multi_executor.get_all_execution_status()
            
            # Get data collection status
            collection_status = self.data_collector.get_collection_status()
            
            # Combine all data
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'framework_status': self.get_framework_status(),
                'performance_data': performance_data,
                'strategy_comparison': strategy_comparison,
                'account_status': account_status,
                'execution_status': execution_status,
                'data_collection': collection_status,
                'system_summary': {
                    'total_strategies': len(self.strategy_manager.strategies),
                    'active_executors': execution_status.get('active_executors', 0),
                    'total_accounts': len(account_status),
                    'data_points_collected': collection_status.get('table_counts', {}),
                    'framework_uptime': (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get comprehensive dashboard data: {e}")
            return {}
    
    def export_framework_data(self) -> str:
        """Export comprehensive framework data"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"multi_strategy_framework_export_{timestamp}.json"
            
            # Collect all framework data
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'framework_version': '1.0.0',
                    'export_type': 'comprehensive_framework_data'
                },
                'framework_status': self.get_framework_status(),
                'comprehensive_dashboard': self.get_comprehensive_dashboard_data(),
                'strategy_configurations': {
                    strategy_id: {
                        'strategy_id': config.strategy_id,
                        'strategy_name': config.strategy_name,
                        'account_name': config.account_name,
                        'instruments': config.instruments,
                        'max_positions': config.max_positions,
                        'max_daily_trades': config.max_daily_trades,
                        'risk_per_trade': config.risk_per_trade,
                        'stop_loss_pct': config.stop_loss_pct,
                        'take_profit_pct': config.take_profit_pct,
                        'enabled': config.enabled
                    }
                    for strategy_id, config in self.strategy_manager.strategies.items()
                },
                'account_isolation': self.account_manager.get_accounts_for_strategy_isolation(),
                'isolation_validation': self.account_manager.validate_strategy_isolation()
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"📊 Framework data exported: {filename}")
            
            # Send notification
            if self.telegram_notifier:
                self.telegram_notifier.send_message(
                    f"📊 Framework Data Export Complete\n"
                    f"📁 File: {filename}\n"
                    f"📈 Comprehensive multi-strategy data ready for analysis"
                )
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to export framework data: {e}")
            return ""

# Global multi-strategy framework instance
multi_strategy_framework = MultiStrategyFramework()

def get_multi_strategy_framework() -> MultiStrategyFramework:
    """Get the global multi-strategy framework instance"""
    return multi_strategy_framework

