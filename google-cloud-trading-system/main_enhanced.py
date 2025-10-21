#!/usr/bin/env python3
"""
Enhanced Google Cloud Trading System with Safe News Integration
NON-BREAKING enhancement that preserves all existing functionality
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
import asyncio

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app with template directory
template_dir = os.path.join(os.path.dirname(__file__), 'src', 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'src', 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Initialize Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_interval=25,
    ping_timeout=60
)

# Initialize enhanced dashboard manager with proper error handling
dashboard_manager = None
try:
    logger.info("🔄 Initializing enhanced dashboard manager...")
    from src.dashboard.advanced_dashboard_enhanced import EnhancedAdvancedDashboardManager
    dashboard_manager = EnhancedAdvancedDashboardManager()
    logger.info("✅ Enhanced dashboard manager initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize enhanced dashboard manager: {e}")
    logger.exception("Full traceback:")
    # Fallback to existing dashboard manager
    try:
        from src.dashboard.advanced_dashboard import AdvancedDashboardManager
        dashboard_manager = AdvancedDashboardManager()
        logger.info("✅ Fallback to existing dashboard manager")
    except Exception as e2:
        logger.error(f"❌ Fallback dashboard manager also failed: {e2}")
        dashboard_manager = None

# Initialize news integration
news_integration = None
try:
    from src.core.news_integration import safe_news_integration
    news_integration = safe_news_integration
    logger.info("✅ News integration initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ News integration initialization failed: {e}")
    news_integration = None

# FIXED: Register AI Assistant blueprint with main app
try:
    from src.dashboard.ai_assistant_api import ai_bp
    app.register_blueprint(ai_bp)
    logger.info("✅ AI Assistant blueprint registered with main app")
except Exception as e:
    logger.warning(f"⚠️ AI Assistant blueprint registration failed: {e}")

@app.route('/')
def home():
    """Home route - serve dashboard"""
    try:
        return render_template('dashboard_fixed.html')
    except Exception as e:
        logger.error(f"❌ Failed to serve dashboard: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": str(datetime.now())
        }), 500

@app.route('/api/system-status')
def system_status():
    """Enhanced system status API endpoint"""
    status = {
        "status": "running",
        "message": "Enhanced trading system is active with news integration",
        "dashboard_manager": "initialized" if dashboard_manager else "failed",
        "ai_assistant": "enabled",
        "news_integration": "enabled" if news_integration else "disabled",
        "enhanced_features": {
            "news_apis": "integrated",
            "sentiment_analysis": "enabled",
            "news_filtering": "active",
            "ai_enhancements": "enabled"
        }
    }
    
    # Add news integration status
    if news_integration:
        status["news_status"] = {
            "enabled": news_integration.enabled,
            "api_keys_available": len(news_integration.api_keys),
            "last_update": news_integration.last_update
        }
    
    return jsonify(status)

@app.route('/api/news')
def get_news():
    """Get news data API endpoint"""
    try:
        if news_integration:
            news_data = asyncio.run(news_integration.get_news_data())
            return jsonify({
                "status": "success",
                "data": news_data,
                "count": len(news_data),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "News integration not available",
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"❌ News API failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/news/analysis')
def get_news_analysis():
    """Get news analysis API endpoint"""
    try:
        if news_integration:
            analysis = news_integration.get_news_analysis()
            return jsonify({
                "status": "success",
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "News integration not available",
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"❌ News analysis API failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# All existing routes preserved...
@app.route('/api/status')
def status():
    """Status route"""
    if dashboard_manager:
        try:
            system_status = dashboard_manager.get_system_status()
            return jsonify(system_status)
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": str(datetime.now())
            })
    else:
        return jsonify({
            "status": "error",
            "message": "Dashboard manager not initialized",
            "timestamp": str(datetime.now())
        })

@app.route('/api/overview')
def overview():
    """Account overview route"""
    if dashboard_manager:
        try:
            overview = dashboard_manager.get_account_overview()
            return jsonify(overview)
        except Exception as e:
            logger.error(f"❌ Failed to get account overview: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": str(datetime.now())
            }), 500
    else:
        return jsonify({
            "status": "error",
            "message": "Dashboard manager not initialized",
            "timestamp": str(datetime.now())
        })

@app.route('/api/trades/count')
def trade_count():
    """Trade count route"""
    return jsonify({
        "count": 0,
        "timestamp": str(datetime.now())
    })

@app.route('/api/health')
def health():
    """Health check route"""
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.now()),
        "dashboard_manager": "initialized" if dashboard_manager else "failed",
        "ai_assistant": "enabled",
        "news_integration": "enabled" if news_integration else "disabled"
    })

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("📱 Client connected to enhanced dashboard")
    emit('status', {'message': 'Connected to enhanced live trading dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("📱 Client disconnected from enhanced dashboard")

@socketio.on('request_update')
def handle_update_request():
    """Handle general update request - emit all dashboard data"""
    try:
        if dashboard_manager:
            # Get system status
            status = dashboard_manager.get_system_status()
            
            # Emit all the events the dashboard expects
            emit('systems_update', status.get('trading_systems', {}))
            emit('market_update', status.get('market_data', {}))
            emit('risk_update', status.get('account_statuses', {}))
            emit('metrics_update', status.get('trading_metrics', {}))
            emit('news_update', status.get('news_data', {}))
            
            # Emit individual account updates
            for account_id, account_data in status.get('account_statuses', {}).items():
                emit('account_update', account_data)
            
            logger.info("✅ Emitted all enhanced dashboard updates")
        else:
            emit('error', {'message': 'Dashboard manager not initialized'})
    except Exception as e:
        logger.error(f"❌ Failed to send updates: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_status')
def handle_status_request():
    """Handle status update request"""
    try:
        if dashboard_manager:
            status = dashboard_manager.get_system_status()
            emit('status_update', status)
        else:
            emit('error', {'message': 'Dashboard manager not initialized'})
    except Exception as e:
        logger.error(f"❌ Failed to send status update: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_market_data')
def handle_market_data_request():
    """Handle market data request"""
    try:
        if dashboard_manager:
            # Get market data from data feed
            market_data = {}
            for account_id in dashboard_manager.active_accounts:
                try:
                    account_data = dashboard_manager.data_feed.get_latest_data(account_id)
                    if account_data:
                        market_data[account_id] = account_data
                except Exception as e:
                    logger.error(f"❌ Failed to get market data for {account_id}: {e}")
            
            emit('market_update', market_data)
        else:
            emit('error', {'message': 'Dashboard manager not initialized'})
    except Exception as e:
        logger.error(f"❌ Failed to send market data: {e}")
        emit('error', {'message': str(e)})

# Safe task endpoint to run a one-shot market update and signal execution
@app.route('/tasks/full_scan', methods=['POST'])
def full_scan():
    if request.method != 'POST':
        return jsonify({"ok": False, "error": "POST required"}), 405
    
    if dashboard_manager is None:
        logger.error("❌ Dashboard manager not available for full scan")
        return jsonify({"ok": False, "error": "dashboard manager unavailable"}), 503
    
    try:
        logger.info("🔄 Starting enhanced full market scan...")
        
        # Execute trading signals
        results = dashboard_manager.execute_trading_signals()
        
        # Emit update via Socket.IO
        socketio.emit('scan_complete', {
            'results': results,
            'timestamp': str(datetime.now())
        })
        
        logger.info(f"✅ Enhanced full scan completed: {results}")
        return jsonify({
            "ok": True, 
            "results": results,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"❌ Enhanced full scan error: {e}")
        logger.exception("Full traceback:")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Get port from environment (required for Google Cloud)
    port = int(os.environ.get('PORT', 8080))
    
    logger.info("🚀 Starting Enhanced Google Cloud Trading System with News Integration")
    logger.info("=" * 70)
    logger.info(f"🌐 Starting enhanced server on port {port}")
    logger.info(f"📰 News integration: {'enabled' if news_integration else 'disabled'}")
    
    # Start the application with Socket.IO (production mode)
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
