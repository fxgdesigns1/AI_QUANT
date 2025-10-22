#!/usr/bin/env python3
"""
Analytics Dashboard - Standalone Dashboard on Port 8081
Deep dive analytics and performance analysis
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, send_file
import threading
import json

from .trade_database import get_trade_database
from .trade_logger import get_trade_logger
from .metrics_calculator import get_metrics_calculator
from .strategy_version_manager import get_strategy_version_manager
from .data_archiver import get_data_archiver

logger = logging.getLogger(__name__)


class AnalyticsDashboard:
    """Standalone analytics dashboard application"""
    
    def __init__(self, port: int = 8081):
        """Initialize analytics dashboard"""
        self.port = port
        self.db = get_trade_database()
        self.trade_logger = get_trade_logger()
        self.metrics_calc = get_metrics_calculator()
        self.version_manager = get_strategy_version_manager()
        self.archiver = get_data_archiver()
        
        # Create Flask app
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'analytics')
        static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
        
        self.app = Flask(__name__, 
                        template_folder=template_dir,
                        static_folder=static_dir)
        
        self.app.config['SECRET_KEY'] = 'analytics-dashboard-secret-key'
        
        # Register routes
        self._register_routes()
        
        logger.info(f"✅ Analytics dashboard initialized on port {port}")
    
    def _register_routes(self):
        """Register all Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main overview page"""
            return render_template('overview.html')
        
        @self.app.route('/strategy/<strategy_id>')
        def strategy_detail(strategy_id):
            """Strategy detail page"""
            return render_template('strategy_detail.html', strategy_id=strategy_id)
        
        @self.app.route('/trades')
        def trade_history():
            """Trade history page"""
            return render_template('trade_history.html')
        
        @self.app.route('/comparison')
        def comparison():
            """Strategy comparison page"""
            return render_template('comparison.html')
        
        @self.app.route('/charts')
        def charts():
            """Charts and visualizations page"""
            return render_template('charts.html')
        
        @self.app.route('/versions/<strategy_id>')
        def version_history(strategy_id):
            """Strategy version history page"""
            return render_template('version_history.html', strategy_id=strategy_id)
        
        # API Endpoints
        
        @self.app.route('/api/strategies')
        def api_strategies():
            """Get list of all strategies with summary metrics"""
            try:
                all_metrics = self.db.get_all_strategy_metrics()
                
                strategies = []
                for metrics in all_metrics:
                    strategy_id = metrics['strategy_id']
                    
                    # Get version info
                    current_version = self.version_manager.get_current_version(strategy_id)
                    
                    # Get open trades count
                    open_trades = self.db.get_open_trades(strategy_id)
                    
                    strategies.append({
                        'strategy_id': strategy_id,
                        'current_version': current_version,
                        'metrics': metrics,
                        'open_trades_count': len(open_trades)
                    })
                
                return jsonify({
                    'success': True,
                    'strategies': strategies,
                    'total_count': len(strategies)
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting strategies: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/strategy/<strategy_id>/metrics')
        def api_strategy_metrics(strategy_id):
            """Get comprehensive metrics for a strategy"""
            try:
                # Get closed trades
                days = int(request.args.get('days', 90))
                closed_trades = self.db.get_closed_trades(strategy_id, days=days)
                
                # Calculate metrics
                metrics = self.metrics_calc.calculate_all_metrics(closed_trades, strategy_id)
                
                # Get open trades
                open_trades = self.db.get_open_trades(strategy_id)
                
                # Get version info
                current_version = self.version_manager.get_current_version(strategy_id)
                
                return jsonify({
                    'success': True,
                    'strategy_id': strategy_id,
                    'current_version': current_version,
                    'metrics': metrics,
                    'open_trades_count': len(open_trades),
                    'closed_trades_count': len(closed_trades),
                    'period_days': days
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting strategy metrics: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/strategy/<strategy_id>/trades')
        def api_strategy_trades(strategy_id):
            """Get trade list for a strategy"""
            try:
                # Get parameters
                days = int(request.args.get('days', 30))
                limit = int(request.args.get('limit', 100))
                offset = int(request.args.get('offset', 0))
                closed_only = request.args.get('closed_only', 'false').lower() == 'true'
                
                # Get trades
                if closed_only:
                    trades = self.db.get_closed_trades(strategy_id, days=days)
                else:
                    closed = self.db.get_closed_trades(strategy_id, days=days)
                    open_trades = self.db.get_open_trades(strategy_id)
                    trades = closed + open_trades
                
                # Apply pagination
                total_count = len(trades)
                trades_page = trades[offset:offset+limit]
                
                return jsonify({
                    'success': True,
                    'trades': trades_page,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting strategy trades: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/strategy/<strategy_id>/performance-chart')
        def api_strategy_performance_chart(strategy_id):
            """Get time-series data for performance charts"""
            try:
                days = int(request.args.get('days', 30))
                
                # Get daily snapshots
                snapshots = self.db.get_daily_snapshots(strategy_id, days=days)
                
                # If no snapshots, calculate from trades
                if not snapshots:
                    closed_trades = self.db.get_closed_trades(strategy_id, days=days)
                    daily_metrics = self.metrics_calc.calculate_daily_breakdown(closed_trades, days=days)
                    
                    # Convert to snapshot format
                    snapshots = []
                    for date, metrics in daily_metrics.items():
                        snapshots.append({
                            'date': date,
                            'trades_count': metrics.get('total_trades', 0),
                            'net_pnl': metrics.get('total_pnl', 0),
                            'win_rate': metrics.get('win_rate', 0),
                            'max_drawdown': metrics.get('max_drawdown', 0)
                        })
                    
                    snapshots.sort(key=lambda x: x['date'])
                
                # Calculate cumulative P&L
                cumulative_pnl = 0
                for snapshot in snapshots:
                    cumulative_pnl += snapshot.get('net_pnl', 0)
                    snapshot['cumulative_pnl'] = cumulative_pnl
                
                return jsonify({
                    'success': True,
                    'strategy_id': strategy_id,
                    'snapshots': snapshots,
                    'period_days': days
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting performance chart data: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/strategy/<strategy_id>/versions')
        def api_strategy_versions(strategy_id):
            """Get version history for a strategy"""
            try:
                versions = self.version_manager.get_version_history(strategy_id)
                
                return jsonify({
                    'success': True,
                    'strategy_id': strategy_id,
                    'versions': versions,
                    'total_versions': len(versions)
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting strategy versions: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/compare')
        def api_compare_strategies():
            """Compare multiple strategies"""
            try:
                strategy_ids = request.args.get('strategies', '').split(',')
                strategy_ids = [s.strip() for s in strategy_ids if s.strip()]
                
                if len(strategy_ids) < 2:
                    return jsonify({
                        'success': False,
                        'error': 'At least 2 strategies required for comparison'
                    }), 400
                
                comparison_data = []
                
                for strategy_id in strategy_ids:
                    metrics = self.db.get_strategy_metrics(strategy_id)
                    if metrics:
                        comparison_data.append({
                            'strategy_id': strategy_id,
                            'metrics': metrics
                        })
                
                return jsonify({
                    'success': True,
                    'strategies': comparison_data,
                    'comparison_count': len(comparison_data)
                })
                
            except Exception as e:
                logger.error(f"❌ Error comparing strategies: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/trades/search')
        def api_search_trades():
            """Search trades with filters"""
            try:
                # Get filters from query params
                strategy_id = request.args.get('strategy_id')
                instrument = request.args.get('instrument')
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                win_only = request.args.get('win_only', 'false').lower() == 'true'
                loss_only = request.args.get('loss_only', 'false').lower() == 'true'
                
                # Set defaults for dates
                if not end_date:
                    end_date = datetime.now().isoformat()
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).isoformat()
                
                # Get trades
                trades = self.db.get_trades_by_date_range(start_date, end_date, strategy_id)
                
                # Apply filters
                if instrument:
                    trades = [t for t in trades if t.get('instrument') == instrument]
                
                if win_only:
                    trades = [t for t in trades if t.get('realized_pnl', 0) > 0]
                elif loss_only:
                    trades = [t for t in trades if t.get('realized_pnl', 0) <= 0]
                
                return jsonify({
                    'success': True,
                    'trades': trades,
                    'total_count': len(trades),
                    'filters': {
                        'strategy_id': strategy_id,
                        'instrument': instrument,
                        'start_date': start_date,
                        'end_date': end_date,
                        'win_only': win_only,
                        'loss_only': loss_only
                    }
                })
                
            except Exception as e:
                logger.error(f"❌ Error searching trades: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/export/trades')
        def api_export_trades():
            """Export trades to CSV"""
            try:
                strategy_id = request.args.get('strategy_id')
                days = int(request.args.get('days', 30))
                
                trades = self.db.get_closed_trades(strategy_id, days=days)
                
                if not trades:
                    return jsonify({
                        'success': False,
                        'error': 'No trades to export'
                    }), 404
                
                # Create CSV
                import csv
                import io
                
                output = io.StringIO()
                fieldnames = list(trades[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(trades)
                
                # Prepare response
                output.seek(0)
                filename = f"trades_{strategy_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                
                return send_file(
                    io.BytesIO(output.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename
                )
                
            except Exception as e:
                logger.error(f"❌ Error exporting trades: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/database/stats')
        def api_database_stats():
            """Get database statistics"""
            try:
                stats = self.db.get_database_stats()
                archive_stats = self.archiver.get_archive_stats()
                
                return jsonify({
                    'success': True,
                    'database': stats,
                    'archives': archive_stats
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting database stats: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint"""
            return jsonify({
                'success': True,
                'status': 'healthy',
                'service': 'analytics-dashboard',
                'port': self.port,
                'timestamp': datetime.now().isoformat()
            })
    
    def run(self, debug: bool = False, threaded: bool = True):
        """Run the analytics dashboard"""
        logger.info(f"🚀 Starting analytics dashboard on port {self.port}...")
        self.app.run(
            host='0.0.0.0',
            port=self.port,
            debug=debug,
            threaded=threaded
        )
    
    def run_in_thread(self):
        """Run dashboard in background thread"""
        thread = threading.Thread(target=self.run, kwargs={'debug': False}, daemon=True)
        thread.start()
        logger.info(f"✅ Analytics dashboard started in background on port {self.port}")
        return thread


# Singleton instance
_analytics_dashboard_instance = None
_analytics_dashboard_lock = threading.Lock()


def get_analytics_dashboard(port: int = 8081) -> AnalyticsDashboard:
    """Get singleton analytics dashboard instance"""
    global _analytics_dashboard_instance
    
    if _analytics_dashboard_instance is None:
        with _analytics_dashboard_lock:
            if _analytics_dashboard_instance is None:
                _analytics_dashboard_instance = AnalyticsDashboard(port=port)
    
    return _analytics_dashboard_instance


def start_analytics_dashboard(port: int = 8081, background: bool = True):
    """Start the analytics dashboard"""
    dashboard = get_analytics_dashboard(port)
    
    if background:
        return dashboard.run_in_thread()
    else:
        dashboard.run()

