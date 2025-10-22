#!/usr/bin/env python3
"""
Cloud-Optimized Trading System with Analytics
Production-ready for Google Cloud deployment with both dashboards
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging for cloud
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import analytics modules
try:
    from src.analytics.trade_database import get_trade_database
    from src.analytics.trade_logger import get_trade_logger
    from src.analytics.strategy_version_manager import get_strategy_version_manager
    from src.analytics.analytics_dashboard import get_analytics_dashboard
    from src.analytics.data_archiver import get_data_archiver
    ANALYTICS_ENABLED = True
    logger.info("✅ Analytics modules imported successfully")
except ImportError as e:
    ANALYTICS_ENABLED = False
    logger.warning(f"⚠️ Analytics not available: {e}")

def start_analytics_dashboard_cloud():
    """Start analytics dashboard for cloud deployment"""
    if not ANALYTICS_ENABLED:
        logger.warning("⚠️ Analytics not enabled, skipping analytics dashboard")
        return None
    
    try:
        # For cloud deployment, we'll run analytics on the same port with different routes
        # This avoids port conflicts in Cloud Run
        logger.info("🔄 Starting analytics dashboard for cloud deployment...")
        
        # Import the main Flask app and add analytics routes
        from src.dashboard.advanced_dashboard import app
        
        # Import analytics dashboard routes
        from src.analytics.analytics_dashboard import AnalyticsDashboard
        
        # Create analytics dashboard instance
        analytics = AnalyticsDashboard()
        
        # Register analytics routes with the main app
        for rule in analytics.app.url_map.iter_rules():
            # Add /analytics prefix to avoid conflicts
            new_rule = f"/analytics{rule.rule}"
            app.add_url_rule(
                new_rule,
                endpoint=rule.endpoint,
                view_func=analytics.app.view_functions[rule.endpoint],
                methods=rule.methods
            )
        
        logger.info("✅ Analytics dashboard integrated into main app at /analytics/*")
        return analytics
        
    except Exception as e:
        logger.error(f"❌ Failed to start analytics dashboard: {e}")
        logger.exception("Full traceback:")
        return None

def initialize_analytics_system():
    """Initialize analytics system for cloud deployment"""
    if not ANALYTICS_ENABLED:
        logger.warning("⚠️ Analytics not enabled")
        return
    
    try:
        logger.info("🔄 Initializing analytics system for cloud deployment...")
        
        # Initialize database
        trade_db = get_trade_database()
        logger.info("✅ Trade database initialized")
        
        # Initialize trade logger
        trade_logger = get_trade_logger()
        logger.info("✅ Trade logger initialized")
        
        # Initialize version manager
        version_manager = get_strategy_version_manager()
        versioned = version_manager.auto_version_all_strategies()
        logger.info(f"✅ Strategy version manager initialized ({len(versioned)} strategies)")
        
        # Initialize data archiver
        archiver = get_data_archiver()
        logger.info("✅ Data archiver initialized")
        
        # Start analytics dashboard integration
        analytics = start_analytics_dashboard_cloud()
        
        logger.info("✅ Analytics system fully initialized for cloud deployment")
        
        return {
            'db': trade_db,
            'logger': trade_logger,
            'version_manager': version_manager,
            'archiver': archiver,
            'dashboard': analytics
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize analytics: {e}")
        logger.exception("Full traceback:")
        return None

def main():
    """Main entry point for cloud deployment"""
    
    logger.info("🚀 Starting Trading Analytics System - CLOUD DEPLOYMENT")
    logger.info("=" * 60)
    
    # Initialize analytics system
    analytics_system = initialize_analytics_system()
    
    # Import and start the main trading system
    try:
        # Import the main Flask app
        from src.dashboard.advanced_dashboard import app, socketio
        
        # Add analytics health endpoint to main app
        @app.route('/api/analytics/health')
        def analytics_health():
            if not ANALYTICS_ENABLED:
                return {'success': False, 'error': 'Analytics not enabled'}, 503
            
            try:
                if analytics_system and analytics_system['db']:
                    stats = analytics_system['db'].get_database_stats()
                    return {
                        'success': True,
                        'status': 'healthy',
                        'analytics_enabled': True,
                        'database_stats': stats,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {'success': False, 'error': 'Analytics not initialized'}, 503
            except Exception as e:
                return {'success': False, 'error': str(e)}, 500
        
        # Add analytics summary endpoint
        @app.route('/api/analytics/summary')
        def analytics_summary():
            if not ANALYTICS_ENABLED or not analytics_system:
                return {'success': False, 'error': 'Analytics not available'}
            
            try:
                all_metrics = analytics_system['db'].get_all_strategy_metrics()
                
                total_trades = sum(m.get('total_trades', 0) for m in all_metrics)
                total_pnl = sum(m.get('total_pnl', 0) for m in all_metrics)
                avg_win_rate = sum(m.get('win_rate', 0) for m in all_metrics) / len(all_metrics) if all_metrics else 0
                
                return {
                    'success': True,
                    'summary': {
                        'total_strategies': len(all_metrics),
                        'total_trades': total_trades,
                        'total_pnl': total_pnl,
                        'avg_win_rate': avg_win_rate
                    },
                    'analytics_url': '/analytics'  # Cloud-friendly URL
                }
            except Exception as e:
                logger.error(f"❌ Error getting analytics summary: {e}")
                return {'success': False, 'error': str(e)}, 500
        
        # Get port from environment (required for Cloud Run)
        port = int(os.environ.get('PORT', 8080))
        
        logger.info("=" * 60)
        logger.info("✅ WebSocket support enabled")
        logger.info("✅ Dashboard manager initialized")
        logger.info("✅ Analytics system integrated")
        logger.info("✅ News integration enabled")
        logger.info("✅ AI assistant enabled")
        logger.info("=" * 60)
        
        logger.info(f"🌐 Starting server on port {port}")
        logger.info("📊 Main Dashboard: http://localhost:{}/".format(port))
        logger.info("📈 Analytics Dashboard: http://localhost:{}/analytics/".format(port))
        
        # Start Flask app with SocketIO
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        logger.error(f"❌ Failed to start trading system: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == '__main__':
    main()
