#!/usr/bin/env python3
"""
Analytics Dashboard Application
Separate Flask app for performance tracking and analysis
Runs independently on port 8081
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import threading
import time

# Add paths for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv('oanda_config.env')
load_dotenv('../oanda_config.env')

# Import with proper path handling
try:
    from database.models import PerformanceDatabase
    from collectors.oanda_collector import ReadOnlyOandaCollector
    from collectors.scheduler import CollectorScheduler
    from analytics.performance import PerformanceAnalytics
    from analytics.strategy_comparison import StrategyComparison
    from analytics.change_analysis import ChangeImpactAnalyzer
except ImportError:
    # Fallback for local development
    from analytics.database.models import PerformanceDatabase
    from analytics.collectors.oanda_collector import ReadOnlyOandaCollector
    from analytics.collectors.scheduler import CollectorScheduler
    from analytics.analytics.performance import PerformanceAnalytics
    from analytics.analytics.strategy_comparison import StrategyComparison
    from analytics.analytics.change_analysis import ChangeImpactAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'analytics-secret-key')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
db = PerformanceDatabase()
collector = ReadOnlyOandaCollector(db)
scheduler = CollectorScheduler(collector)
analytics = PerformanceAnalytics(db)
comparator = StrategyComparison(db)
change_analyzer = ChangeImpactAnalyzer(db)

logger.info("✅ Analytics dashboard initialized")

# ============================================================================
# HOME & OVERVIEW ROUTES
# ============================================================================

@app.route('/')
def home():
    """Home page - redirects to overview"""
    return render_template('overview.html')

@app.route('/overview')
def overview():
    """Overview dashboard"""
    return render_template('overview.html')

@app.route('/api/overview/data')
def overview_data():
    """Get overview data for all accounts"""
    try:
        accounts = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD_SCALP': os.getenv('GOLD_SCALP_ACCOUNT'),
            'STRATEGY_ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        overview = {
            'accounts': [],
            'total_balance': 0.0,
            'total_unrealized_pl': 0.0,
            'total_trades_today': 0,
            'system_win_rate': 0.0,
            'timestamp': datetime.now().isoformat()
        }
        
        for name, account_id in accounts.items():
            if not account_id:
                continue
            
            # Get latest snapshot
            snapshot = db.get_latest_snapshot(account_id)
            
            if snapshot:
                overview['accounts'].append({
                    'name': name,
                    'account_id': account_id,
                    'balance': snapshot.get('balance', 0.0),
                    'equity': snapshot.get('equity', 0.0),
                    'unrealized_pl': snapshot.get('unrealized_pl', 0.0),
                    'daily_pl': snapshot.get('daily_pl', 0.0),
                    'daily_trades': snapshot.get('daily_trades', 0),
                    'win_rate': snapshot.get('win_rate', 0.0)
                })
                
                overview['total_balance'] += snapshot.get('balance', 0.0)
                overview['total_unrealized_pl'] += snapshot.get('unrealized_pl', 0.0)
                overview['total_trades_today'] += snapshot.get('daily_trades', 0)
        
        # Calculate system-wide win rate
        if overview['accounts']:
            overview['system_win_rate'] = sum(a['win_rate'] for a in overview['accounts']) / len(overview['accounts'])
        
        return jsonify(overview)
        
    except Exception as e:
        logger.error(f"❌ Overview data error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ACCOUNT ROUTES
# ============================================================================

@app.route('/account/<account_name>')
def account_view(account_name):
    """Account detail view"""
    return render_template('account.html', account_name=account_name)

@app.route('/api/account/<account_name>/data')
def account_data(account_name):
    """Get detailed account data"""
    try:
        # Map account name to ID
        account_map = {
            'PRIMARY': os.getenv('PRIMARY_ACCOUNT'),
            'GOLD_SCALP': os.getenv('GOLD_SCALP_ACCOUNT'),
            'STRATEGY_ALPHA': os.getenv('STRATEGY_ALPHA_ACCOUNT')
        }
        
        account_id = account_map.get(account_name.upper())
        if not account_id:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get latest snapshot
        snapshot = db.get_latest_snapshot(account_id)
        
        # Get equity curve
        equity_curve = db.get_equity_curve(account_id, days=30)
        
        # Get recent trades
        recent_trades = db.get_trades(account_id=account_id, status='closed', limit=50)
        
        # Get comprehensive metrics
        metrics = analytics.calculate_comprehensive_metrics(account_id=account_id, days=30)
        
        return jsonify({
            'account_name': account_name,
            'account_id': account_id,
            'snapshot': snapshot,
            'equity_curve': [{'timestamp': t, 'equity': e} for t, e in equity_curve],
            'recent_trades': recent_trades[:10],  # Last 10 trades
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Account data error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STRATEGY ROUTES
# ============================================================================

@app.route('/strategy/<strategy_name>')
def strategy_view(strategy_name):
    """Strategy detail view"""
    return render_template('strategy.html', strategy_name=strategy_name)

@app.route('/api/strategy/<strategy_name>/data')
def strategy_data(strategy_name):
    """Get detailed strategy data"""
    try:
        # Get comprehensive metrics
        metrics = analytics.calculate_comprehensive_metrics(strategy_name=strategy_name, days=30)
        
        # Get recent trades
        recent_trades = db.get_trades(strategy_name=strategy_name, status='closed', limit=50)
        
        # Get strategy changes
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT * FROM strategy_changes
            WHERE strategy_name = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (strategy_name,))
        changes = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'strategy_name': strategy_name,
            'metrics': metrics,
            'recent_trades': recent_trades[:10],
            'recent_changes': changes,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Strategy data error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# COMPARISON ROUTES
# ============================================================================

@app.route('/compare')
def compare_view():
    """Strategy comparison view"""
    return render_template('comparison.html')

@app.route('/api/compare', methods=['POST'])
def compare_strategies():
    """Compare two strategies"""
    try:
        data = request.get_json()
        strategy_a = data.get('strategy_a')
        strategy_b = data.get('strategy_b')
        days = data.get('days', 30)
        
        if not strategy_a or not strategy_b:
            return jsonify({'error': 'Both strategies required'}), 400
        
        comparison = comparator.compare_strategies(strategy_a, strategy_b, days)
        
        return jsonify(comparison)
        
    except Exception as e:
        logger.error(f"❌ Comparison error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# CHANGE TRACKING ROUTES
# ============================================================================

@app.route('/changes')
def changes_view():
    """Changes tracking view"""
    return render_template('changes.html')

@app.route('/api/changes/recent')
def recent_changes():
    """Get recent strategy changes"""
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT * FROM strategy_changes
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        changes = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Recent changes error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/changes/<change_id>/analyze', methods=['POST'])
def analyze_change(change_id):
    """Analyze impact of a specific change"""
    try:
        data = request.get_json() or {}
        lookback_days = data.get('lookback_days', 30)
        
        analysis = change_analyzer.analyze_change_impact(change_id, lookback_days)
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"❌ Change analysis error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# DATA COLLECTION ROUTES
# ============================================================================

@app.route('/api/collector/status')
def collector_status():
    """Get collector status"""
    try:
        status = collector.get_collection_status()
        scheduler_stats = scheduler.get_stats()
        
        return jsonify({
            **status,
            'scheduler': scheduler_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Collector status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collector/collect', methods=['POST'])
def trigger_collection():
    """Manually trigger data collection"""
    try:
        collector.collect_all_data()
        return jsonify({
            'status': 'success',
            'message': 'Data collection triggered',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Collection trigger error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'analytics-dashboard',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected',
        'collector': 'active' if scheduler.running else 'stopped'
    })

@app.route('/api/stats')
def stats():
    """Get system statistics"""
    try:
        db_stats = db.get_database_stats()
        
        return jsonify({
            **db_stats,
            'collector_running': scheduler.running,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("📱 Client connected to analytics dashboard")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("📱 Client disconnected from analytics dashboard")

# ============================================================================
# BACKGROUND UPDATES
# ============================================================================

def broadcast_updates():
    """Broadcast updates via WebSocket"""
    while True:
        try:
            time.sleep(5)  # Every 5 seconds
            
            # Get fresh data
            db_stats = db.get_database_stats()
            
            # Broadcast to all connected clients
            socketio.emit('stats_update', {
                'stats': db_stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Broadcast error: {e}")
            time.sleep(10)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('ANALYTICS_PORT', 8081))
    
    logger.info("🚀 Starting Analytics Dashboard")
    logger.info("=" * 60)
    logger.info(f"📊 Analytics Dashboard")
    logger.info(f"🌐 Port: {port}")
    logger.info(f"📁 Database: {db.db_path}")
    logger.info(f"🔄 Collector: {'Active' if scheduler.running else 'Stopped'}")
    logger.info("=" * 60)
    
    # Start data collector scheduler
    scheduler.start()
    
    # Start background update thread
    update_thread = threading.Thread(target=broadcast_updates, daemon=True)
    update_thread.start()
    
    # Initial data collection
    logger.info("🔄 Running initial data collection...")
    collector.collect_all_data()
    logger.info("✅ Initial data collection complete")
    
    # Run Flask app
    logger.info(f"✅ Analytics Dashboard running on http://localhost:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

