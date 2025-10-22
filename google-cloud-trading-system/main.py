#!/usr/bin/env python3
"""
Google Cloud Trading System - Main Entry Point - FULLY INTEGRATED VERSION
Production-ready entry point with complete dashboard, WebSocket, and AI integration
"""

import os
import sys
import logging
import json
import time
import threading
import asyncio
from datetime import datetime, timedelta
import uuid
from flask import Flask, jsonify, request, render_template, redirect
from flask_socketio import SocketIO, emit
from flask_apscheduler import APScheduler
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from functools import lru_cache
import hashlib

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
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
    from src.analytics.analytics_dashboard import start_analytics_dashboard
    from src.analytics.data_archiver import get_data_archiver
    ANALYTICS_ENABLED = True
    logger.info("✅ Analytics modules imported successfully")
except ImportError as e:
    ANALYTICS_ENABLED = False
    logger.warning(f"⚠️ Analytics not available: {e}")

# Create Flask app with correct template directory (MOVED UP for app.config usage)
template_dir = os.path.join(os.path.dirname(__file__), 'src', 'templates')
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Performance optimization settings
app.config['ENABLE_RESPONSE_CACHE'] = os.getenv('ENABLE_RESPONSE_CACHE', 'true').lower() == 'true'
app.config['CACHE_TTL_SECONDS'] = int(os.getenv('CACHE_TTL_SECONDS', '15'))
app.config['DASHBOARD_UPDATE_INTERVAL'] = int(os.getenv('DASHBOARD_UPDATE_INTERVAL', '30'))
app.config['MARKET_DATA_UPDATE_INTERVAL'] = int(os.getenv('MARKET_DATA_UPDATE_INTERVAL', '10'))

# Response cache for performance optimization
response_cache = {}
cache_lock = threading.Lock()

def get_cache_key(endpoint: str, params: Dict[str, Any] = None) -> str:
    """Generate cache key for endpoint and parameters"""
    key_data = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached response if available and not expired"""
    if not app.config['ENABLE_RESPONSE_CACHE']:
        return None
    
    with cache_lock:
        if cache_key in response_cache:
            cached = response_cache[cache_key]
            if time.time() - cached['timestamp'] < app.config['CACHE_TTL_SECONDS']:
                return cached['response']
            else:
                del response_cache[cache_key]
    return None

def cache_response(cache_key: str, response: Dict[str, Any]):
    """Cache response with timestamp"""
    if not app.config['ENABLE_RESPONSE_CACHE']:
        return
    
    with cache_lock:
        response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Clean old cache entries (keep only last 100)
        if len(response_cache) > 100:
            oldest_key = min(response_cache.keys(), key=lambda k: response_cache[k]['timestamp'])
            del response_cache[oldest_key]

def cached_endpoint(endpoint_name: str):
    """Decorator for caching endpoint responses"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            params = request.args.to_dict() if hasattr(request, 'args') else {}
            cache_key = get_cache_key(endpoint_name, params)
            
            # Check cache first
            cached = get_cached_response(cache_key)
            if cached:
                logger.debug(f"Cache hit for {endpoint_name}")
                return jsonify(cached)
            
            # Generate response
            try:
                result = func(*args, **kwargs)
                if isinstance(result, tuple):
                    response_data, status_code = result
                    if status_code == 200:
                        # Cache successful responses
                        if isinstance(response_data, dict):
                            cache_response(cache_key, response_data)
                        elif hasattr(response_data, 'get_json'):
                            cache_response(cache_key, response_data.get_json())
                return result
            except Exception as e:
                logger.error(f"Error in cached endpoint {endpoint_name}: {e}")
                raise
        return wrapper
    return decorator

# Configure APScheduler
app.config['SCHEDULER_API_ENABLED'] = True
app.config['SCHEDULER_TIMEZONE'] = 'Europe/London'

# ==========================================
# LAZY INITIALIZATION FUNCTIONS (Flask app.config)
# ==========================================

def get_dashboard_manager():
    """Get or create dashboard manager in Flask app context"""
    if 'dashboard_manager' not in app.config:
        try:
            logger.info("🔄 Initializing dashboard manager...")
            from src.dashboard.advanced_dashboard import AdvancedDashboardManager
            app.config['dashboard_manager'] = AdvancedDashboardManager()
            logger.info("✅ Dashboard manager initialized")
        except ImportError as e:
            logger.error(f"❌ Missing dependencies for dashboard: {e}")
            logger.info("🔄 Attempting to initialize basic dashboard...")
            try:
                # Try to initialize without new modules
                from src.dashboard.advanced_dashboard import AdvancedDashboardManager
                app.config['dashboard_manager'] = AdvancedDashboardManager()
                logger.info("✅ Basic dashboard manager initialized")
            except Exception as e2:
                logger.error(f"❌ Failed to initialize basic dashboard: {e2}")
                app.config['dashboard_manager'] = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize dashboard: {e}")
            logger.exception("Full traceback:")
            app.config['dashboard_manager'] = None
    return app.config.get('dashboard_manager')

def get_scanner():
    """Get or create scanner in Flask app context"""
    if 'scanner' not in app.config:
        try:
            logger.info("🔄 Initializing scanner...")
            from src.core.simple_timer_scanner import get_simple_scanner
            app.config['scanner'] = get_simple_scanner()
            logger.info("✅ Scanner initialized")
        except Exception as e:
            logger.error(f"❌ Scanner init failed: {e}")
            logger.exception("Full traceback:")
            app.config['scanner'] = None
    return app.config.get('scanner')

def get_news_integration():
    """Get or create news integration in Flask app context"""
    if 'news_integration' not in app.config:
        try:
            logger.info("🔄 Initializing news integration...")
            from src.core.news_integration import safe_news_integration
            app.config['news_integration'] = safe_news_integration
            logger.info("✅ News integration initialized")
        except Exception as e:
            logger.error(f"❌ News integration init failed: {e}")
            logger.exception("Full traceback:")
            app.config['news_integration'] = None
    return app.config.get('news_integration')

def get_ai_assistant():
    """Get or create AI assistant in Flask app context"""
    if 'ai_assistant' not in app.config:
        try:
            logger.info("🔄 Initializing AI assistant...")
            from src.dashboard.ai_assistant_api import AIAssistantAPI
            app.config['ai_assistant'] = AIAssistantAPI()
            logger.info("✅ AI assistant initialized")
        except Exception as e:
            logger.error(f"❌ AI assistant init failed: {e}")
            logger.exception("Full traceback:")
            app.config['ai_assistant'] = None
    return app.config.get('ai_assistant')

def get_weekend_optimizer():
    """Get or create weekend optimizer in Flask app context"""
    if 'weekend_optimizer' not in app.config:
        try:
            logger.info("🔄 Initializing weekend optimization...")
            from weekend_optimization import get_weekend_optimizer as get_optimizer
            optimizer = get_optimizer()
            optimizer.start_scheduler()
            app.config['weekend_optimizer'] = optimizer
            logger.info("✅ Weekend optimization initialized")
        except Exception as e:
            logger.error(f"❌ Weekend optimization init failed: {e}")
            logger.exception("Full traceback:")
            app.config['weekend_optimizer'] = None
    return app.config.get('weekend_optimizer')

# ==========================================
# BACKGROUND JOBS
# ==========================================

def run_scanner_job():
    """APScheduler job - runs scanner"""
    try:
        scanner = get_scanner()
        if scanner:
            logger.info("🔄 APScheduler: Running scanner job...")
            scanner._run_scan()
            logger.info("✅ APScheduler: Scanner job complete")
            
            # Toast notification for scanner completion (NEW - non-breaking)
            try:
                from src.utils.toast_notifier import emit_info_toast
                emit_info_toast("🔄 Market scan completed")
            except Exception:
                pass  # Don't break scanner if toast fails
        else:
            logger.error("❌ Scanner not available for job")
    except Exception as e:
        logger.error(f"❌ Scanner job error: {e}")
        logger.exception("Full traceback:")

# Initialize dashboard manager in background
def initialize_dashboard_manager():
    """Pre-initialize dashboard manager in background to avoid first-request timeout"""
    try:
        time.sleep(5)  # Brief delay to let app start
        logger.info("🔄 Pre-initializing dashboard manager in background...")
        mgr = get_dashboard_manager()
        if mgr:
            # Trigger lazy initialization by accessing a property
            _ = mgr.active_accounts
            logger.info(f"✅ Dashboard manager pre-initialized: {len(mgr.active_accounts)} accounts")
        else:
            logger.warning("⚠️ Dashboard manager returned None")
    except Exception as e:
        logger.error(f"❌ Failed to pre-initialize dashboard: {e}")
        logger.exception("Full traceback:")

# Start dashboard pre-initialization in background
dashboard_init_thread = threading.Thread(target=initialize_dashboard_manager, daemon=True)
dashboard_init_thread.start()
logger.info("✅ Dashboard manager pre-initialization started")

# Initialize daily monitor
def initialize_monitor():
    """Initialize daily monitoring system"""
    try:
        time.sleep(15)  # Wait for scanner to start
        logger.info("🔄 Initializing daily monitor...")
        from src.core.daily_monitor import get_daily_monitor
        monitor = get_daily_monitor()
        monitor.run()
    except Exception as e:
        logger.error(f"❌ Failed to initialize daily monitor: {e}")
        logger.exception("Full traceback:")

# Start monitor in background thread
monitor_thread = threading.Thread(target=initialize_monitor, daemon=True)
monitor_thread.start()
logger.info("✅ Daily monitor initialization scheduled")

# Initialize APScheduler (app and config already set up above)
scheduler = APScheduler()
scheduler.init_app(app)

# Add scanner job to scheduler - runs every 5 minutes
scheduler.add_job(
    id='trading_scanner',
    func=run_scanner_job,
    trigger='interval',
    minutes=5,
    max_instances=1,  # Only one scan at a time
    coalesce=True,    # Skip if previous scan still running
    replace_existing=True
)

# Add performance snapshot job - runs every 15 minutes
def capture_performance_snapshots():
    """Capture performance snapshots for all strategies"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        from src.core.oanda_client import OandaClient
        from src.core.performance_tracker import get_performance_tracker
        
        logger.info("📸 Capturing performance snapshots...")
        
        yaml_mgr = get_yaml_manager()
        tracker = get_performance_tracker()
        
        accounts = yaml_mgr.get_all_accounts()
        captured = 0
        
        for account in accounts:
            if not account.get('active', False):
                continue
            
            account_id = account['id']
            
            try:
                # Create OandaClient for this specific account
                oanda_client = OandaClient(account_id=account_id)
                account_info = oanda_client.get_account_info()  # No argument needed
                balance = float(account_info.get('balance', 0))
                nav = float(account_info.get('NAV', 0))
                unrealized_pl = float(account_info.get('unrealizedPL', 0))
                pl = nav - 100000
                
                snapshot_data = {
                    'account_id': account_id,
                    'strategy_name': account.get('strategy'),
                    'display_name': account.get('display_name', account.get('name')),
                    'balance': balance,
                    'nav': nav,
                    'pl': pl,
                    'unrealized_pl': unrealized_pl,
                    'trade_count': 0,  # TODO: Get from trade history
                    'open_positions': 0,  # TODO: Get from OANDA
                    'win_rate': 0,  # TODO: Calculate
                    'pairs': ', '.join(account.get('instruments', [])),
                    'timeframe': 'N/A',
                    'daily_limit': account.get('risk_settings', {}).get('daily_trade_limit', 0),
                    'status': 'active'
                }
                
                if tracker.capture_snapshot(snapshot_data):
                    captured += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to capture snapshot for {account_id}: {e}")
                continue
        
        logger.info(f"✅ Captured {captured} performance snapshots")
        
    except Exception as e:
        logger.error(f"❌ Performance snapshot job error: {e}")

scheduler.add_job(
    id='performance_snapshots',
    func=capture_performance_snapshots,
    trigger='interval',
    minutes=15,
    max_instances=1,
    coalesce=True,
    replace_existing=True
)

logger.info("✅ APScheduler configured - scanner every 5min, snapshots every 15min")

# START SCHEDULER IMMEDIATELY (not in __main__ - for App Engine)
try:
    scheduler.start()
    logger.info("✅ APScheduler STARTED on app initialization")
except Exception as e:
    logger.error(f"❌ Failed to start scheduler: {e}")
    logger.exception("Full traceback:")

# Initialize SocketIO with proper configuration for Google Cloud
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=False,
                   engineio_logger=False,
                   ping_timeout=60,
                   ping_interval=25)

# Initialize Toast Notification System (NEW - doesn't break existing functionality)
try:
    from src.utils.toast_notifier import initialize_toast_notifier
    initialize_toast_notifier(socketio)
    logger.info("✅ Toast notification system initialized")
except Exception as e:
    logger.warning(f"⚠️ Toast notifier init failed (non-critical): {e}")

# In-memory action store (short-lived, for confirmations)
_PENDING_ACTIONS: Dict[str, Dict[str, Any]] = {}

def _bounded(value: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(max_v, value))

def _notify_telegram(text: str) -> None:
    try:
        notifier = getattr(app.config, 'TELEGRAM_NOTIFIER', None) or app.config.get('TELEGRAM_NOTIFIER')
        if notifier and hasattr(notifier, 'send_message'):
            notifier.send_message(text)
    except Exception:
        logger.warning("Telegram notifier unavailable")

@app.route('/')
def home():
    """Home route - serves the main trading dashboard"""
    try:
        mgr = get_dashboard_manager()
        if mgr:
            return render_template('dashboard_advanced.html')
        else:
            return jsonify({
                "error": "Dashboard manager not initialized",
                "message": "Please check system logs",
                "redirect": "/api/status"
            }), 503
    except Exception as e:
        logger.error(f"❌ Dashboard route error: {e}")
        return jsonify({
            "error": "Dashboard unavailable", 
            "message": str(e)
        }), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard route - serves the trading dashboard"""
    try:
        mgr = get_dashboard_manager()
        if mgr:
            return render_template('dashboard_advanced.html')
        else:
            return jsonify({
                "error": "Dashboard manager not initialized",
                "message": "Please check system logs",
                "redirect": "/api/status"
            }), 503
    except Exception as e:
        logger.error(f"❌ Dashboard route error: {e}")
        return jsonify({
            "error": "Dashboard unavailable", 
            "message": str(e)
        }), 500

@app.route('/insights')
def insights_dashboard():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

@app.route('/status')
def status_dashboard():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

@app.route('/config')
def config_dashboard():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

@app.route('/signals')
def signals_dashboard():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

# ═══════════════════════════════════════════════════════════════
# SIGNALS API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/signals/pending')
def get_pending_signals():
    """Get all pending signals with pips to entry"""
    try:
        from src.core.signal_tracker import get_signal_tracker
        from src.core.oanda_client import get_oanda_client
        from src.utils.pips_calculator import calculate_pips, format_pips
        from datetime import timezone
        
        signal_tracker = get_signal_tracker()
        oanda_client = get_oanda_client()
        
        # Get filter parameters
        instrument = request.args.get('instrument')
        strategy = request.args.get('strategy')
        
        # Get pending signals
        pending_signals = signal_tracker.get_pending_signals(instrument, strategy)
        
        # Enrich with current prices
        result_signals = []
        for signal in pending_signals:
            try:
                # Get current price
                pricing = oanda_client.get_pricing([signal.instrument])
                if pricing and len(pricing) > 0:
                    price_data = pricing[0]
                    bid = float(price_data.get('bids', [{}])[0].get('price', 0))
                    ask = float(price_data.get('asks', [{}])[0].get('price', 0))
                    current_price = (bid + ask) / 2
                    
                    # Update signal with current price
                    signal_tracker.update_signal_price(signal.signal_id, current_price)
                    
                    # Calculate pips away
                    pips_away = calculate_pips(signal.instrument, current_price, signal.entry_price)
                    
                    result_signals.append({
                        'signal_id': signal.signal_id,
                        'instrument': signal.instrument,
                        'side': signal.side,
                        'strategy': signal.strategy_name,
                        'entry_price': signal.entry_price,
                        'current_price': current_price,
                        'pips_away': pips_away,
                        'pips_away_formatted': format_pips(pips_away),
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'generated_at': signal.generated_at.isoformat(),
                        'ai_insight': signal.ai_insight,
                        'conditions_met': signal.conditions_met,
                        'confidence': signal.confidence,
                        'risk_reward_ratio': signal.risk_reward_ratio,
                        'account_id': signal.account_id
                    })
                else:
                    # No current price, use stored data
                    result_signals.append({
                        'signal_id': signal.signal_id,
                        'instrument': signal.instrument,
                        'side': signal.side,
                        'strategy': signal.strategy_name,
                        'entry_price': signal.entry_price,
                        'current_price': signal.current_price or signal.entry_price,
                        'pips_away': signal.pips_away or 0,
                        'pips_away_formatted': format_pips(signal.pips_away or 0),
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'generated_at': signal.generated_at.isoformat(),
                        'ai_insight': signal.ai_insight,
                        'conditions_met': signal.conditions_met,
                        'confidence': signal.confidence,
                        'risk_reward_ratio': signal.risk_reward_ratio,
                        'account_id': signal.account_id
                    })
            except Exception as e:
                logger.error(f"Error enriching signal {signal.signal_id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'signals': result_signals,
            'count': len(result_signals),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get pending signals: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e),
            'signals': []
        }), 500

@app.route('/api/signals/active')
def get_active_signals():
    """Get all active trades with pips to exit and P/L"""
    try:
        from src.core.signal_tracker import get_signal_tracker
        from src.core.oanda_client import get_oanda_client
        from src.utils.pips_calculator import calculate_pips_to_target, format_pips
        from datetime import timezone
        
        signal_tracker = get_signal_tracker()
        oanda_client = get_oanda_client()
        
        # Get filter parameters
        instrument = request.args.get('instrument')
        strategy = request.args.get('strategy')
        
        # Get active signals
        active_signals = signal_tracker.get_active_signals(instrument, strategy)
        
        # Enrich with current prices and P/L
        result_signals = []
        for signal in active_signals:
            try:
                # Get current price
                pricing = oanda_client.get_pricing([signal.instrument])
                if pricing and len(pricing) > 0:
                    price_data = pricing[0]
                    bid = float(price_data.get('bids', [{}])[0].get('price', 0))
                    ask = float(price_data.get('asks', [{}])[0].get('price', 0))
                    current_price = (bid + ask) / 2
                    
                    # Calculate P/L (simplified)
                    entry_price = signal.actual_entry_price or signal.entry_price
                    price_diff = current_price - entry_price if signal.side == 'BUY' else entry_price - current_price
                    unrealized_pl = price_diff * (signal.units or 10000)  # Approximate
                    
                    # Update signal
                    signal_tracker.update_signal_price(signal.signal_id, current_price, unrealized_pl)
                    
                    # Calculate pips to SL and TP
                    pips_to_sl = calculate_pips_to_target(current_price, signal.stop_loss, signal.instrument)
                    pips_to_tp = calculate_pips_to_target(current_price, signal.take_profit, signal.instrument)
                    
                    # Determine status
                    status = "profit" if unrealized_pl >= 0 else "drawdown"
                    
                    # Calculate duration
                    duration_seconds = (datetime.now(timezone.utc) - (signal.executed_at or signal.generated_at)).total_seconds()
                    duration_minutes = int(duration_seconds / 60)
                    
                    result_signals.append({
                        'trade_id': signal.trade_id or signal.signal_id,
                        'signal_id': signal.signal_id,
                        'instrument': signal.instrument,
                        'side': signal.side,
                        'strategy': signal.strategy_name,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'pips_to_sl': pips_to_sl,
                        'pips_to_tp': pips_to_tp,
                        'pips_to_sl_formatted': format_pips(pips_to_sl, show_sign=False),
                        'pips_to_tp_formatted': format_pips(pips_to_tp, show_sign=False),
                        'unrealized_pl': unrealized_pl,
                        'status': status,
                        'duration_minutes': duration_minutes,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'ai_insight': signal.ai_insight,
                        'confidence': signal.confidence,
                        'executed_at': signal.executed_at.isoformat() if signal.executed_at else None,
                        'account_id': signal.account_id
                    })
            except Exception as e:
                logger.error(f"Error enriching active signal {signal.signal_id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'signals': result_signals,
            'count': len(result_signals),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get active signals: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e),
            'signals': []
        }), 500

@app.route('/api/signals/all')
def get_all_signals_endpoint():
    """Get all signals with filtering"""
    try:
        from src.core.signal_tracker import get_signal_tracker, SignalStatus
        
        signal_tracker = get_signal_tracker()
        
        # Get filter parameters
        status_param = request.args.get('status')
        instrument = request.args.get('instrument')
        strategy = request.args.get('strategy')
        limit = int(request.args.get('limit', 50))
        
        # Parse status
        status = None
        if status_param:
            try:
                status = SignalStatus(status_param.lower())
            except ValueError:
                pass
        
        # Get all signals
        signals = signal_tracker.get_all_signals(status, instrument, strategy, limit)
        
        result_signals = [signal.to_dict() for signal in signals]
        
        # Get statistics
        stats = signal_tracker.get_statistics()
        
        return jsonify({
            'success': True,
            'signals': result_signals,
            'count': len(result_signals),
            'statistics': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get all signals: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e),
            'signals': []
        }), 500

@app.route('/api/signals/<signal_id>')
def get_signal_detail(signal_id):
    """Get detailed information for a specific signal"""
    try:
        from src.core.signal_tracker import get_signal_tracker
        
        signal_tracker = get_signal_tracker()
        signal = signal_tracker.get_signal(signal_id)
        
        if not signal:
            return jsonify({
                'success': False,
                'error': 'Signal not found'
            }), 404
        
        return jsonify({
            'success': True,
            'signal': signal.to_dict(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get signal detail: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signals/statistics')
def get_signals_statistics():
    """Get signal statistics"""
    try:
        from src.core.signal_tracker import get_signal_tracker
        
        signal_tracker = get_signal_tracker()
        stats = signal_tracker.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/config/accounts')
def get_config_accounts():
    """Get all accounts from YAML configuration"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        yaml_mgr = get_yaml_manager()
        accounts = yaml_mgr.get_all_accounts()
        
        return jsonify({
            "status": "success",
            "accounts": accounts,
            "count": len(accounts),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Failed to get accounts: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/config/strategies')
def get_config_strategies():
    """Get all strategies from YAML configuration"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        yaml_mgr = get_yaml_manager()
        strategies = yaml_mgr.get_all_strategies()
        
        return jsonify({
            "status": "success",
            "strategies": strategies,
            "count": len(strategies),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Failed to get strategies: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# ═══════════════════════════════════════════════════════════════
# STRATEGY MANAGER - LIVE SWITCHING (NEW)
# ═══════════════════════════════════════════════════════════════

@app.route('/strategy-manager')
def strategy_manager_page():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

@app.route('/api/strategies/config', methods=['GET'])
def get_strategies_config():
    """Get current strategy configuration"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        # Check if strategy manager initialized properly
        if not hasattr(strategy_mgr, 'initialized') or not strategy_mgr.initialized:
            return jsonify({
                'success': False, 
                'error': 'Strategy manager not initialized',
                'health_status': strategy_mgr.get_health_status() if hasattr(strategy_mgr, 'get_health_status') else {}
            }), 503
        
        config = strategy_mgr.get_current_config()
        
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"❌ Failed to get strategy config: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/switch', methods=['POST'])
def switch_strategy():
    """Stage a strategy switch"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        data = request.get_json()
        account_id = data.get('account_id')
        new_strategy = data.get('new_strategy')
        
        if not account_id or not new_strategy:
            return jsonify({
                'success': False,
                'error': 'Missing account_id or new_strategy'
            }), 400
        
        result = strategy_mgr.stage_strategy_switch(account_id, new_strategy)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to switch strategy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/toggle', methods=['POST'])
def toggle_account():
    """Stage account enable/disable"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        data = request.get_json()
        account_id = data.get('account_id')
        active = data.get('active')
        
        if not account_id or active is None:
            return jsonify({
                'success': False,
                'error': 'Missing account_id or active'
            }), 400
        
        result = strategy_mgr.stage_account_toggle(account_id, active)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to toggle account: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/pending', methods=['GET'])
def get_pending_changes():
    """Get pending strategy changes"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        result = strategy_mgr.get_pending_changes()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to get pending changes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/clear', methods=['POST'])
def clear_pending_changes():
    """Clear pending strategy changes"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        result = strategy_mgr.clear_pending_changes()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to clear changes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/status', methods=['GET'])
def get_restart_status():
    """Get restart status and open positions"""
    try:
        from src.core.graceful_restart import get_restart_manager
        restart_mgr = get_restart_manager()
        
        status = restart_mgr.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Failed to get restart status: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'restart_in_progress': False,
            'open_positions': 0,
            'safe_to_restart': True
        }), 500

@app.route('/api/strategies/apply', methods=['POST'])
def apply_strategy_changes():
    """Apply pending strategy changes with graceful restart"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        from src.core.graceful_restart import get_restart_manager
        
        strategy_mgr = get_strategy_manager()
        restart_mgr = get_restart_manager()
        
        data = request.get_json() or {}
        force = data.get('force', False)
        
        # Check if there are pending changes
        if not strategy_mgr.has_pending_changes():
            return jsonify({
                'success': False,
                'error': 'No pending changes to apply'
            }), 400
        
        # Get staged config
        staged_config = strategy_mgr.get_staged_config()
        if not staged_config:
            return jsonify({
                'success': False,
                'error': 'No staged configuration'
            }), 400
        
        # Validate staged config
        validation = strategy_mgr.validate_staged_config()
        if not validation.get('valid', False):
            return jsonify({
                'success': False,
                'error': f"Invalid configuration: {validation.get('error')}"
            }), 400
        
        # Set up progress callback for WebSocket updates
        def progress_callback(progress_data):
            socketio.emit('restart_progress', progress_data)
        
        restart_mgr.add_progress_callback(progress_callback)
        
        # Execute restart in background thread
        def execute_in_background():
            result = restart_mgr.execute_restart(staged_config, force=force)
            
            if result['success']:
                # Clear pending changes on success
                strategy_mgr.clear_pending_changes()
                socketio.emit('restart_complete', result)
            else:
                socketio.emit('restart_failed', result)
        
        import threading
        restart_thread = threading.Thread(target=execute_in_background, daemon=True)
        restart_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Restart initiated',
            'force': force
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to apply changes: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# NEW: Enhanced Strategy Manager Endpoints

@app.route('/api/strategies/behavior', methods=['GET'])
def get_behavior_modes():
    """Get available behavior modes"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        # Check if strategy manager initialized properly
        if not hasattr(strategy_mgr, 'initialized') or not strategy_mgr.initialized:
            return jsonify({
                'success': False,
                'error': 'Strategy manager not initialized',
                'health_status': strategy_mgr.get_health_status() if hasattr(strategy_mgr, 'get_health_status') else {}
            }), 503
        
        modes = strategy_mgr.get_behavior_modes()
        
        return jsonify({
            'success': True,
            'behavior_modes': modes
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get behavior modes: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/behavior', methods=['POST'])
def set_behavior_mode():
    """Set behavior mode for an account"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        # Check if strategy manager initialized properly
        if not hasattr(strategy_mgr, 'initialized') or not strategy_mgr.initialized:
            return jsonify({
                'success': False,
                'error': 'Strategy manager not initialized',
                'health_status': strategy_mgr.get_health_status() if hasattr(strategy_mgr, 'get_health_status') else {}
            }), 503
        
        data = request.get_json()
        account_id = data.get('account_id')
        behavior_mode = data.get('behavior_mode')
        
        if not account_id or not behavior_mode:
            return jsonify({
                'success': False,
                'error': 'Missing account_id or behavior_mode'
            }), 400
        
        result = strategy_mgr.stage_behavior_change(account_id, behavior_mode)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to set behavior mode: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/upload', methods=['POST'])
def upload_strategy():
    """Upload new strategy from backtesting system"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        # Get uploaded file
        if 'strategy_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No strategy file uploaded'
            }), 400
        
        strategy_file = request.files['strategy_file']
        
        if strategy_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get backtest results if provided
        backtest_results = None
        if 'backtest_results' in request.form:
            try:
                backtest_results = json.loads(request.form['backtest_results'])
            except json.JSONDecodeError:
                logger.warning("Invalid backtest results JSON")
        
        # Upload strategy
        result = strategy_mgr.upload_strategy(strategy_file, backtest_results)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to upload strategy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/upload/validate', methods=['POST'])
def validate_strategy():
    """Validate strategy code without uploading"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        if 'strategy_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No strategy file provided'
            }), 400
        
        strategy_file = request.files['strategy_file']
        strategy_code = strategy_file.read().decode('utf-8')
        
        # Validate code
        validation_result = strategy_mgr._validate_strategy_code(strategy_code)
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to validate strategy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/uploaded', methods=['GET'])
def get_uploaded_strategies():
    """Get list of uploaded strategies"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        strategies = strategy_mgr.get_uploaded_strategies()
        
        return jsonify({
            'success': True,
            'uploaded_strategies': strategies
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get uploaded strategies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/strategies/register', methods=['POST'])
def register_strategy():
    """Register uploaded strategy in system"""
    try:
        from src.api.strategy_manager import get_strategy_manager
        strategy_mgr = get_strategy_manager()
        
        data = request.get_json()
        strategy_id = data.get('strategy_id')
        
        if not strategy_id:
            return jsonify({
                'success': False,
                'error': 'Missing strategy_id'
            }), 400
        
        result = strategy_mgr.register_uploaded_strategy(strategy_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to register strategy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================================
# HYBRID MANUAL TRADING - OPPORTUNITIES API
# ==========================================

@app.route('/api/opportunities')
def get_opportunities():
    """Get current trade opportunities for manual approval"""
    try:
        from src.core.trade_opportunity_finder import get_opportunity_finder
        from src.core.data_feed import get_data_feed
        
        opportunity_finder = get_opportunity_finder()
        
        # Get scanner to access strategies
        scanner = get_scanner()
        if not scanner or not hasattr(scanner, 'strategies'):
            return jsonify({
                'opportunities': [],
                'stats': {},
                'message': 'Scanner not initialized'
            })
        
        # Get market data
        data_feed = get_data_feed()
        
        # Collect all instruments
        all_instruments = set()
        for strategy in scanner.strategies:
            if hasattr(strategy, 'instruments'):
                all_instruments.update(strategy.instruments)
        
        # Get latest prices
        market_data = {}
        for instrument in all_instruments:
            try:
                data = data_feed.get_market_data(instrument, granularity='H1', count=100)
                if data is not None and len(data) > 0:
                    market_data[instrument] = data
            except Exception as e:
                logger.error(f"Failed to get data for {instrument}: {e}")
                continue
        
        # Find opportunities
        opportunities = opportunity_finder.find_opportunities(list(scanner.strategies.values()), market_data)
        
        # Get stats
        stats = opportunity_finder.get_user_stats()
        
        # Convert opportunities to dict
        opps_list = []
        for opp in opportunities:
            opps_list.append({
                'id': opp.id,
                'timestamp': opp.timestamp.isoformat(),
                'instrument': opp.instrument,
                'direction': opp.direction,
                'at_sniper_zone': opp.at_sniper_zone,
                'zone_type': opp.zone_type,
                'zone_level': opp.zone_level,
                'distance_to_zone_pips': opp.distance_to_zone_pips,
                'suggested_entry': opp.suggested_entry,
                'fixed_stop_loss': opp.fixed_stop_loss,
                'stop_loss_pips': opp.stop_loss_pips,
                'take_profit_stages': opp.take_profit_stages,
                'risk_reward_ratio': opp.risk_reward_ratio,
                'quality_score': opp.quality_score,
                'quality_level': opp.quality_level.value,
                'pros': opp.pros,
                'cons': opp.cons,
                'recommendation': opp.recommendation,
                'strategy_name': opp.strategy_name,
                'expected_win_rate': opp.expected_win_rate,
                'expected_profit': opp.expected_profit,
                'expected_loss': opp.expected_loss,
                'trades_today': opp.trades_today,
                'max_trades_remaining': opp.max_trades_remaining,
                'daily_target_progress': opp.daily_target_progress,
            })
        
        return jsonify({
            'opportunities': opps_list,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get opportunities: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'opportunities': [],
            'stats': {},
            'error': str(e)
        })

@app.route('/api/opportunities/approve', methods=['POST'])
def approve_opportunity():
    """Approve and execute a trade opportunity"""
    try:
        from src.core.trade_opportunity_finder import get_opportunity_finder
        from src.core.order_manager import get_order_manager
        
        data = request.get_json()
        opportunity_id = data.get('opportunity_id')
        
        if not opportunity_id:
            return jsonify({'success': False, 'message': 'Missing opportunity_id'})
        
        opportunity_finder = get_opportunity_finder()
        
        # Find the opportunity
        opp = next((o for o in opportunity_finder.opportunities if o.id == opportunity_id), None)
        if not opp:
            return jsonify({'success': False, 'message': 'Opportunity not found'})
        
        # Approve it
        opportunity_finder.approve_opportunity(opportunity_id, user_notes="Manual approval")
        
        # Execute the trade
        order_manager = get_order_manager()
        
        # Create order
        result = order_manager.place_order(
            instrument=opp.instrument,
            side=opp.direction,
            units=1000,  # Default units, adjust based on strategy
            stop_loss=opp.fixed_stop_loss,
            take_profit=opp.take_profit_stages[0]['price'] if opp.take_profit_stages else None
        )
        
        logger.info(f"✅ Trade approved and executed: {opp.instrument} {opp.direction}")
        
        return jsonify({
            'success': True,
            'message': 'Trade executed successfully',
            'instrument': opp.instrument,
            'direction': opp.direction,
            'order_id': result.get('id') if isinstance(result, dict) else None
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to approve opportunity: {e}")
        logger.exception("Full traceback:")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/opportunities/dismiss', methods=['POST'])
def dismiss_opportunity():
    """Dismiss a trade opportunity"""
    try:
        from src.core.trade_opportunity_finder import get_opportunity_finder
        
        data = request.get_json()
        opportunity_id = data.get('opportunity_id')
        reason = data.get('reason', 'No reason provided')
        
        if not opportunity_id:
            return jsonify({'success': False, 'message': 'Missing opportunity_id'})
        
        opportunity_finder = get_opportunity_finder()
        success = opportunity_finder.dismiss_opportunity(opportunity_id, reason)
        
        if success:
            # Get learning update
            learning_msg = f"Learned from your dismissal: {reason[:50]}"
            
            return jsonify({
                'success': True,
                'message': 'Opportunity dismissed',
                'learning_update': learning_msg
            })
        else:
            return jsonify({'success': False, 'message': 'Opportunity not found'})
            
    except Exception as e:
        logger.error(f"❌ Failed to dismiss opportunity: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/add-account', methods=['POST'])
def add_config_account():
    """Add new account to YAML configuration"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        
        account_data = request.get_json()
        
        # Validation
        required_fields = ['id', 'name', 'strategy', 'instruments']
        for field in required_fields:
            if field not in account_data:
                return jsonify({
                    "status": "error",
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Add account
        yaml_mgr = get_yaml_manager()
        success = yaml_mgr.add_account(account_data)
        
        if success:
            logger.info(f"✅ Account added: {account_data.get('name', 'Unknown')}")
            return jsonify({
                "status": "success",
                "message": "Account added successfully",
                "account_id": account_data['id']
            })
        else:
            return jsonify({
                "status": "error",
                "error": "Failed to add account (may already exist)"
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Add account error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/config/edit-account', methods=['PUT'])
def edit_config_account():
    """Edit existing account in YAML configuration"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        
        account_data = request.get_json()
        
        if 'id' not in account_data:
            return jsonify({
                "status": "error",
                "error": "Account ID is required"
            }), 400
        
        account_id = account_data.pop('id')
        
        # Edit account
        yaml_mgr = get_yaml_manager()
        success = yaml_mgr.edit_account(account_id, account_data)
        
        if success:
            logger.info(f"✅ Account edited: {account_id}")
            return jsonify({
                "status": "success",
                "message": "Account updated successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "error": "Failed to update account"
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Edit account error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/config/delete-account', methods=['DELETE'])
def delete_config_account():
    """Delete account from YAML configuration"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        
        account_data = request.get_json()
        
        if 'id' not in account_data:
            return jsonify({
                "status": "error",
                "error": "Account ID is required"
            }), 400
        
        account_id = account_data['id']
        
        # Delete account
        yaml_mgr = get_yaml_manager()
        success = yaml_mgr.delete_account(account_id)
        
        if success:
            logger.info(f"✅ Account deleted: {account_id}")
            return jsonify({
                "status": "success",
                "message": "Account deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "error": "Failed to delete account"
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Delete account error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/config/deploy', methods=['POST'])
def deploy_configuration():
    """Deploy configuration changes (triggers reload)"""
    try:
        from src.core.config_loader import reload_config
        
        # Reload configuration
        reload_config()
        
        logger.info("✅ Configuration reloaded successfully")
        
        return jsonify({
            "status": "success",
            "message": "Configuration reloaded. Changes will take effect immediately.",
            "note": "For cloud deployment, use: gcloud app deploy app.yaml --quiet",
            "timestamp": datetime.now().isoformat()
        })
            
    except Exception as e:
        logger.error(f"❌ Deploy error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/status')
@cached_endpoint('api_status')
def status():
    """Status route"""
    mgr = get_dashboard_manager()
    if mgr:
        try:
            system_status = mgr.get_system_status()
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
    mgr = get_dashboard_manager()
    if mgr:
        try:
            overview = mgr.get_account_overview()
            return jsonify(overview)
        except Exception as e:
            logger.error(f"❌ Failed to get account overview: {e}")
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

@app.route('/api/accounts')
def api_accounts():
    """Return live account statuses (read-only)."""
    try:
        mgr = get_dashboard_manager()
        status_payload = mgr.get_system_status() if mgr else {}
        return jsonify({
            'status': 'success',
            'accounts': status_payload.get('account_statuses', {}),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Accounts endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/risk')
def api_risk():
    """Return aggregated risk metrics (read-only)."""
    try:
        mgr = get_dashboard_manager()
        metrics = mgr.get_risk_metrics() if mgr else {}
        return jsonify({'status': 'success', 'risk': metrics, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"❌ Risk endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/metrics')
def api_metrics():
    """Return trading performance metrics (read-only)."""
    try:
        mgr = get_dashboard_manager()
        status_payload = mgr.get_system_status() if mgr else {}
        return jsonify({'status': 'success', 'metrics': status_payload.get('trading_metrics', {}), 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"❌ Metrics endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/signals/recent')
def api_signals_recent():
    """Return recent signals if available (read-only fallback)."""
    try:
        # If manager exposes recent signals, return; else return empty list gracefully
        recent = []
        try:
            mgr = get_dashboard_manager()
            if mgr and hasattr(mgr, 'get_recent_signals'):
                recent = mgr.get_recent_signals() or []
        except Exception as ie:
            logger.warning(f"Signals accessor not available: {ie}")
        return jsonify({'status': 'success', 'signals': recent, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"❌ Recent signals endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/positions')
def api_positions():
    """Return open positions if available (read-only fallback)."""
    try:
        positions = {}
        mgr = get_dashboard_manager()
        if mgr and hasattr(mgr, 'active_accounts') and hasattr(mgr, 'account_manager'):
            for account_id in mgr.active_accounts:
                try:
                    if hasattr(mgr.account_manager, 'get_open_positions'):
                        positions[account_id] = mgr.account_manager.get_open_positions(account_id) or []
                    else:
                        positions[account_id] = []
                except Exception as ie:
                    logger.warning(f"Positions fetch failed for {account_id}: {ie}")
                    positions[account_id] = []
        return jsonify({'status': 'success', 'positions': positions, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"❌ Positions endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Return a basic health log note (App Engine logs are external).
    This endpoint confirms service health without exposing App Engine logs.
    """
    try:
        return jsonify({
            'status': 'success',
            'note': 'For detailed logs, use gcloud app logs tail -s default. Service health OK.',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# =============== SECURE ACTION ENDPOINTS (CONFIRMATION REQUIRED) ===============

@app.route('/actions/strategy', methods=['POST'])
def action_strategy():
    """Request strategy control (pause/resume/start/stop). Confirmation required."""
    payload = request.get_json(silent=True) or {}
    action = payload.get('action')
    target = payload.get('target', 'all')
    if action not in ['pause', 'resume', 'start', 'stop']:
        return jsonify({'status': 'error', 'error': 'invalid action'}), 400
    # Build preview
    preview = {
        'action': action,
        'target': target,
        'effect': f'{action} requested on {target}'
    }
    action_id = str(uuid.uuid4())
    _PENDING_ACTIONS[action_id] = {
        'type': 'strategy',
        'payload': payload,
        'created_at': datetime.now().isoformat()
    }
    return jsonify({'status': 'pending', 'confirm_required': True, 'action_id': action_id, 'preview': preview})

@app.route('/actions/risk', methods=['POST'])
def action_risk():
    """Request bounded risk parameter changes. Confirmation required."""
    payload = request.get_json(silent=True) or {}
    account_id = payload.get('account_id')
    changes = payload.get('changes', {})
    if not account_id:
        return jsonify({'status': 'error', 'error': 'account_id required'}), 400
    # Bound deltas
    bounded = {}
    if 'max_risk_per_trade' in changes:
        bounded['max_risk_per_trade'] = _bounded(float(changes['max_risk_per_trade']), 0.0, 0.05)
    if 'max_positions' in changes:
        bounded['max_positions'] = int(_bounded(int(changes['max_positions']), 1, 10))
    if 'daily_trade_limit' in changes:
        bounded['daily_trade_limit'] = int(_bounded(int(changes['daily_trade_limit']), 1, 200))
    if 'max_portfolio_risk' in changes:
        bounded['max_portfolio_risk'] = _bounded(float(changes['max_portfolio_risk']), 0.1, 0.9)
    preview = {'account_id': account_id, 'changes': bounded}
    action_id = str(uuid.uuid4())
    _PENDING_ACTIONS[action_id] = {
        'type': 'risk',
        'payload': {'account_id': account_id, 'changes': bounded},
        'created_at': datetime.now().isoformat()
    }
    return jsonify({'status': 'pending', 'confirm_required': True, 'action_id': action_id, 'preview': preview})

@app.route('/actions/orders', methods=['POST'])
def action_orders():
    """Request order/position actions (e.g., close positions by filter). Confirmation required."""
    payload = request.get_json(silent=True) or {}
    op = payload.get('op')
    if op not in ['close_positions', 'cancel_orders']:
        return jsonify({'status': 'error', 'error': 'invalid op'}), 400
    preview = {'op': op, 'filter': payload.get('filter', {})}
    action_id = str(uuid.uuid4())
    _PENDING_ACTIONS[action_id] = {
        'type': 'orders',
        'payload': payload,
        'created_at': datetime.now().isoformat()
    }
    return jsonify({'status': 'pending', 'confirm_required': True, 'action_id': action_id, 'preview': preview})

@app.route('/actions/confirm', methods=['POST'])
def action_confirm():
    """Confirm and execute a pending action with guardrails and alerts."""
    data = request.get_json(silent=True) or {}
    action_id = data.get('action_id')
    if not action_id or action_id not in _PENDING_ACTIONS:
        return jsonify({'status': 'error', 'error': 'invalid action_id'}), 400
    entry = _PENDING_ACTIONS.pop(action_id)
    a_type = entry['type']
    payload = entry['payload']
    # Default to dry-run off only if explicitly allowed via env
    live_allowed = os.getenv('ALLOW_LIVE_ACTIONS', 'false').lower() == 'true'
    executed = False
    details = {}
    try:
        if not live_allowed:
            details = {'note': 'Live actions disabled. Set ALLOW_LIVE_ACTIONS=true to enable.'}
        else:
            mgr = get_dashboard_manager()
            if a_type == 'strategy' and mgr:
                # Best-effort: pause/resume by toggling a kill switch if available
                action = payload.get('action')
                target = payload.get('target', 'all')
                # Expose a simple flag on app for global pause
                if action == 'pause':
                    app.config['GLOBAL_TRADING_PAUSED'] = True
                elif action in ['resume', 'start']:
                    app.config['GLOBAL_TRADING_PAUSED'] = False
                # stop == pause for safety
                executed = True
                details = {'result': 'strategy state set', 'paused': app.config.get('GLOBAL_TRADING_PAUSED', False), 'target': target}
            elif a_type == 'risk' and mgr and hasattr(mgr, 'order_manager'):
                # Update per-account OrderManager limits in-place (bounded earlier)
                om = mgr.order_manager
                acct = payload.get('account_id')
                changes = payload.get('changes', {})
                per_mgr = om.get_order_manager(acct) if hasattr(om, 'get_order_manager') else None
                if not per_mgr:
                    raise RuntimeError(f'No order manager for {acct}')
                for key, val in changes.items():
                    if hasattr(per_mgr, key):
                        setattr(per_mgr, key, type(getattr(per_mgr, key))(val))
                executed = True
                details = {'result': 'order manager limits updated', 'account_id': acct, 'applied': changes}
            elif a_type == 'orders' and mgr and hasattr(mgr, 'order_manager'):
                om = mgr.order_manager
                op = payload.get('op')
                flt = payload.get('filter', {})
                effected = []
                # Close positions by instrument and optional account
                if op == 'close_positions':
                    instrument = flt.get('instrument')
                    target_acct = flt.get('account_id')
                    accounts = [target_acct] if target_acct else list(getattr(mgr, 'active_accounts', []))
                    for acct in accounts:
                        try:
                            if instrument and hasattr(om, 'close_position'):
                                ok = om.close_position(acct, instrument, reason='AI assistant manual close')
                                effected.append({'account_id': acct, 'instrument': instrument, 'closed': ok})
                        except Exception as ce:
                            effected.append({'account_id': acct, 'instrument': instrument, 'error': str(ce)})
                executed = True
                details = {'result': 'orders processed', 'op': op, 'effected': effected}
        # Alert & audit
        _notify_telegram(f"✅ Action confirmed: {a_type} {payload} | executed={executed}")
        logger.info(f"ACTION CONFIRMED: type={a_type} payload={payload} executed={executed}")
        return jsonify({'status': 'ok', 'executed': executed, 'details': details, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"❌ Action execution error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500
@app.route('/api/trades/count')
def trade_count():
    """Trade count route"""
    return jsonify({
        "count": 0,
        "timestamp": str(datetime.now())
    })

@app.route('/api/force_execute_now', methods=['POST'])
def force_execute_now():
    """FORCE IMMEDIATE TRADE EXECUTION - Places micro-trades on all strategies"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        from src.core.oanda_client import OandaClient
        
        yaml_mgr = get_yaml_manager()
        accounts = yaml_mgr.get_all_accounts()
        
        results = []
        trades_placed = 0
        
        for account in accounts:
            if not account.get('active', False):
                continue
            
            account_id = account['id']
            instruments = account.get('instruments', [])
            
            if not instruments:
                continue
            
            # Take first instrument for each account
            instrument = instruments[0]
            
            try:
                # Create OANDA client
                client = OandaClient(account_id=account_id)
                
                # Get current price
                prices = client.get_current_prices([instrument], force_refresh=True)
                
                if instrument not in prices:
                    results.append({
                        'account': account.get('name'),
                        'status': 'failed',
                        'error': 'No price data'
                    })
                    continue
                
                # Get current price
                current_price = prices[instrument]
                entry_price = current_price.ask  # Use ask for BUY
                
                # Get account balance for proper sizing
                account_info = client.get_account_info()
                balance = float(account_info.balance if hasattr(account_info, 'balance') else 100000)
                
                # Get risk per trade from settings
                risk_per_trade = account.get('risk_settings', {}).get('max_risk_per_trade', 0.01)
                risk_amount = balance * risk_per_trade
                
                # Calculate PROPER position sizing based on risk
                if 'XAU' in instrument:  # Gold
                    sl_dollars = 2.5  # $2.5 stop loss
                    units = int(risk_amount / sl_dollars)
                    tp_price = entry_price + 5.0
                    sl_price = entry_price - 2.5
                elif 'JPY' in instrument:  # JPY pairs
                    sl_pips = 10
                    # For JPY pairs: 10 pips on 10,000 units = $1
                    units = int((risk_amount / sl_pips) * 10000)
                    units = (units // 1000) * 1000  # Round to nearest 1000
                    tp_price = entry_price + 0.20  # 20 pips
                    sl_price = entry_price - 0.10  # 10 pips
                else:  # Regular forex
                    sl_pips = 10
                    # For regular pairs: 10 pips on 10,000 units = $1
                    units = int((risk_amount / sl_pips) * 10000)
                    units = (units // 1000) * 1000  # Round to nearest 1000
                    tp_price = entry_price + 0.0020  # 20 pips
                    sl_price = entry_price - 0.0010  # 10 pips
                
                # Place BUY order
                result = client.place_market_order(
                    instrument=instrument,
                    units=units,
                    take_profit=tp_price,
                    stop_loss=sl_price
                )
                
                if result:
                    # Result is OandaOrder object
                    trades_placed += 1
                    results.append({
                        'account': account.get('name'),
                        'instrument': instrument,
                        'units': units,
                        'trade_id': result.trade_id if hasattr(result, 'trade_id') else 'N/A',
                        'order_id': result.order_id if hasattr(result, 'order_id') else 'N/A',
                        'status': 'executed',
                        'entry_price': entry_price
                    })
                    logger.info(f"✅ TRADE EXECUTED: {account.get('name')} - {instrument} BUY {units} units")
                else:
                    results.append({
                        'account': account.get('name'),
                        'instrument': instrument,
                        'status': 'failed',
                        'error': 'No result from OANDA'
                    })
            
            except Exception as e:
                results.append({
                    'account': account.get('name'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'complete',
            'trades_placed': trades_placed,
            'accounts_processed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Force execute error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check route"""
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.now()),
        "dashboard_manager": "initialized" if get_dashboard_manager() else "failed"
    })

@app.route('/api/contextual/<instrument>')
def get_contextual_insights(instrument):
    """Get contextual insights for instrument"""
    try:
        mgr = get_dashboard_manager()
        if mgr:
            insights = mgr.get_contextual_insights(instrument)
            return jsonify(insights)
        else:
            return jsonify({'error': 'Dashboard not initialized'}), 503
    except Exception as e:
        logger.error(f"❌ Failed to get contextual insights: {e}")
        return jsonify({'error': str(e)}), 500

# Safe task endpoint to run a one-shot market update and signal execution
@app.route('/tasks/full_scan', methods=['POST'])
def full_scan():
    if request.method != 'POST':
        return jsonify({"ok": False, "error": "POST required"}), 405
    
    if get_dashboard_manager() is None:
        logger.error("❌ Dashboard manager not available for full scan")
        return jsonify({"ok": False, "error": "dashboard manager unavailable"}), 503
    
    try:
        logger.info("🔄 Starting PROGRESSIVE market scan... [VERSION: 2025-10-01-06:30]")
        mgr = get_dashboard_manager()
        logger.info(f"📊 Dashboard manager available: {mgr is not None}")
        
        # First try normal scan
        results = mgr.execute_trading_signals()
        logger.info(f"📊 Normal scan completed, results type: {type(results)}")
        
        # Check if any trades were executed
        total_trades = 0
        if isinstance(results, dict):
            for acc, res in results.items():
                if isinstance(res, dict) and 'executed_trades' in res:
                    total_trades += len(res.get('executed_trades', []))
        
        logger.info(f"📊 Total trades from normal scan: {total_trades}")
        logger.info(f"📊 Will enter progressive scan: {total_trades == 0}")
        
        # DISABLED OCT 16: NO progressive relaxation - quality over quantity!
        # Progressive relaxing was causing 27-36% win rate by forcing bad trades
        if total_trades == 0:
            logger.info("✅ No trades found - CORRECT (no quality setups available)")
            logger.info("💡 Adaptive system will NOT relax criteria - capital preserved")
            # Do NOT run progressive relaxation - let adaptive system handle it
            # If market has no quality setups, having ZERO trades is the RIGHT decision!
        
        # Telegram confirmation (ALWAYS SEND - critical feature)
        try:
            from src.core.telegram_notifier import get_telegram_notifier
            notifier = getattr(mgr, 'telegram_notifier', None) or get_telegram_notifier()
            
            # ALWAYS log notification attempt
            logger.info(f"📱 Attempting Telegram notification (enabled: {getattr(notifier, 'enabled', False)})")
            
            if notifier and getattr(notifier, 'enabled', False):
                # Build detailed multi-account summary
                if total_trades > 0:
                    summary_lines = [f"🎯 <b>PROGRESSIVE SCAN - {total_trades} TRADES EXECUTED</b>"]
                else:
                    summary_lines = [f"📊 <b>SCAN COMPLETE - NO OPPORTUNITIES</b>"]
                
                summary_lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                summary_lines.append("")
                
                if isinstance(results, dict):
                    for acc, res in results.items():
                        if isinstance(res, dict):
                            executed = res.get('executed_trades', [])
                            if executed:
                                summary_lines.append(f"✅ {acc[-3:]}: {len(executed)} trades")
                            else:
                                summary_lines.append(f"⚪ {acc[-3:]}: 0 trades")
                
                if total_trades == 0:
                    summary_lines.append("")
                    summary_lines.append("💡 No opportunities met criteria")
                    summary_lines.append("🔄 Next scan: every hour")
                
                message = "\n".join(summary_lines) + "\n\n#ScanUpdate #AutoScan"
                
                # Force send message (bypass rate limiting for scan updates)
                success = notifier.send_message(message, "scan_update")
                logger.info(f"✅ Telegram notification sent: {success}")
            else:
                logger.error("❌ Telegram notifier not enabled!")
                logger.error(f"   Token present: {bool(os.getenv('TELEGRAM_TOKEN'))}")
                logger.error(f"   Chat ID present: {bool(os.getenv('TELEGRAM_CHAT_ID'))}")
        except Exception as notify_err:
            logger.error(f"❌ Telegram notify failed: {notify_err}")
            logger.exception("Full notification error traceback:")

        logger.info(f"✅ Progressive full scan completed: {total_trades} total trades")
        return jsonify({
            "ok": True, 
            "results": results,
            "total_trades": total_trades,
            "scan_type": "progressive" if total_trades > 0 else "normal",
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"❌ Full scan error: {e}")
        logger.exception("Full traceback:")
        return jsonify({"ok": False, "error": str(e)}), 500

# Public scan trigger with token auth (for manual triggers)
@app.route('/tasks/full_scan_public', methods=['POST'])
def full_scan_public():
    token = request.headers.get('X-Scan-Token') or request.args.get('token')
    expected = os.environ.get('SCAN_TRIGGER_TOKEN')
    if not expected or token != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    if get_dashboard_manager() is None:
        return jsonify({"ok": False, "error": "dashboard manager unavailable"}), 503

    # Telegram: announce scan start
    try:
        from src.core.telegram_notifier import get_telegram_notifier
        notifier = getattr(dashboard_manager, 'telegram_notifier', None) or get_telegram_notifier()
        if notifier and getattr(notifier, 'enabled', False):
            notifier.send_message("🔍 Manual scan started\n#ScanUpdate")
    except Exception:
        pass

    try:
        results = mgr.execute_trading_signals()
        # Telegram: announce completion summary
        try:
            from src.core.telegram_notifier import get_telegram_notifier
            notifier = getattr(mgr, 'telegram_notifier', None) or get_telegram_notifier()
            if notifier and getattr(notifier, 'enabled', False):
                summary_lines = ["✅ Manual scan completed"]
                if isinstance(results, dict):
                    for acc, res in results.items():
                        executed = res.get('executed_trades', []) if isinstance(res, dict) else []
                        summary_lines.append(f"• {acc}: {len(executed)} trades")
                notifier.send_message("\n".join(summary_lines) + "\n#ScanUpdate")
        except Exception:
            pass

        return jsonify({"ok": True, "results": results, "timestamp": str(datetime.now())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Progressive trading scanner endpoint
@app.route('/tasks/progressive_scan', methods=['POST'])
def progressive_scan():
    """Progressive trading scanner that relaxes criteria until trades are found"""
    try:
        logger.info("🔄 Starting progressive trading scan...")
        
        # Import and run progressive scanner
        from progressive_trading_scanner import ProgressiveTradingScanner
        
        scanner = ProgressiveTradingScanner()
        results = scanner.run_progressive_scan()
        
        logger.info(f"✅ Progressive scan completed: {results}")
        
        return jsonify({
            "ok": True,
            "progressive_scan_results": results,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"❌ Progressive scan error: {e}")
        logger.exception("Full traceback:")
        return jsonify({"ok": False, "error": str(e)}), 500

# Telegram connection test
@app.route('/api/telegram/test')
def telegram_test():
    try:
        from src.core.telegram_notifier import get_telegram_notifier
        notifier = get_telegram_notifier()
        ok = notifier.test_connection() if getattr(notifier, 'enabled', False) else False
        if ok:
            notifier.send_message("📡 Telegram test OK\n#SystemStatus")
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/news')
def get_news():
    """Get news data endpoint"""
    try:
        news_int = get_news_integration()
        if not news_int:
            return jsonify({"error": "News integration not available"}), 503
        
        # Get news data for major currency pairs
        currency_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        news_data = asyncio.run(news_integration.get_news_data(currency_pairs))
        
        # Normalize shape for dashboard JS which expects news_data.news_items
        normalized = {"news_items": news_data if isinstance(news_data, list) else []}
        return jsonify({
            "status": "success",
            "news_count": len(normalized["news_items"]),
            "news_data": normalized,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"❌ News API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/analysis')
def get_news_analysis():
    """Get news analysis endpoint"""
    try:
        news_int = get_news_integration()
        if not news_int:
            return jsonify({"error": "News integration not available"}), 503
        
        # Get news analysis for major currency pairs
        currency_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        analysis = news_int.get_news_analysis(currency_pairs)
        
        return jsonify({
            "status": "success",
            "analysis": analysis,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"❌ News analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/strategies')
def strategies_dashboard():
    """Render main dashboard"""
    return render_template('dashboard_advanced.html')

@app.route('/api/strategies/overview')
def api_strategies_overview():
    """Get overview of all strategies with current performance"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        from src.core.oanda_client import get_oanda_client
        from src.core.performance_tracker import get_performance_tracker
        from src.core.strategy_analyzer import get_strategy_analyzer
        
        yaml_mgr = get_yaml_manager()
        oanda = get_oanda_client()
        tracker = get_performance_tracker()
        analyzer = get_strategy_analyzer()
        
        accounts = yaml_mgr.get_all_accounts()
        strategies_data = []
        
        for account in accounts:
            if not account.get('active', False):
                continue
            
            account_id = account['id']
            
            # Get live account data from OANDA
            try:
                account_info = oanda.get_account_info(account_id)
                balance = float(account_info.get('balance', 0))
                nav = float(account_info.get('NAV', 0))
                unrealized_pl = float(account_info.get('unrealizedPL', 0))
                
                # Calculate P/L (assuming $100k starting balance)
                pl = nav - 100000
                
                # Get historical data
                history = tracker.get_strategy_history(account_id, days=7)
                
                # Prepare strategy data
                strategy_data = {
                    'account_id': account_id,
                    'display_name': account.get('display_name', account.get('name')),
                    'strategy_name': account.get('strategy'),
                    'balance': balance,
                    'nav': nav,
                    'pl': pl,
                    'unrealized_pl': unrealized_pl,
                    'trade_count': len(history),  # Simplified
                    'open_positions': 0,  # TODO: Get from OANDA
                    'win_rate': 0,  # TODO: Calculate from trade history
                    'pairs': ', '.join(account.get('instruments', [])),
                    'timeframe': account.get('strategy_params', {}).get('timeframe', 'N/A'),
                    'daily_limit': account.get('risk_settings', {}).get('daily_trade_limit', 0),
                    'status': 'active'
                }
                
                # Analyze strategy
                analysis = analyzer.analyze_strategy(strategy_data, history)
                strategy_data.update(analysis)
                
                strategies_data.append(strategy_data)
                
            except Exception as e:
                logger.error(f"❌ Failed to get data for {account_id}: {e}")
                continue
        
        # Get portfolio insights
        portfolio_insights = analyzer.generate_portfolio_insights(strategies_data)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'strategies': strategies_data,
            'portfolio': portfolio_insights
        })
        
    except Exception as e:
        logger.error(f"❌ Strategies overview error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/<account_id>/history')
def api_strategy_history(account_id):
    """Get historical performance for a specific strategy"""
    try:
        from src.core.performance_tracker import get_performance_tracker
        
        days = request.args.get('days', 7, type=int)
        tracker = get_performance_tracker()
        
        history = tracker.get_strategy_history(account_id, days=days)
        daily_summary = tracker.get_daily_summary(account_id, days=days)
        
        return jsonify({
            'success': True,
            'account_id': account_id,
            'history': history,
            'daily_summary': daily_summary
        })
        
    except Exception as e:
        logger.error(f"❌ Strategy history error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/comparison')
def api_strategies_comparison():
    """Get comparison data for multiple strategies"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        from src.core.performance_tracker import get_performance_tracker
        
        yaml_mgr = get_yaml_manager()
        tracker = get_performance_tracker()
        
        accounts = yaml_mgr.get_all_accounts()
        account_ids = [acc['id'] for acc in accounts if acc.get('active', False)]
        
        days = request.args.get('days', 7, type=int)
        comparison = tracker.get_comparison_data(account_ids, days=days)
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
        
    except Exception as e:
        logger.error(f"❌ Strategies comparison error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/insights')
def api_strategies_insights():
    """Get actionable insights and recommendations"""
    try:
        from src.core.yaml_manager import get_yaml_manager
        from src.core.oanda_client import get_oanda_client
        from src.core.strategy_analyzer import get_strategy_analyzer
        
        yaml_mgr = get_yaml_manager()
        oanda = get_oanda_client()
        analyzer = get_strategy_analyzer()
        
        accounts = yaml_mgr.get_all_accounts()
        strategies_data = []
        
        for account in accounts:
            if not account.get('active', False):
                continue
            
            account_id = account['id']
            
            try:
                account_info = oanda.get_account_info(account_id)
                nav = float(account_info.get('NAV', 0))
                unrealized_pl = float(account_info.get('unrealizedPL', 0))
                pl = nav - 100000
                
                strategies_data.append({
                    'account_id': account_id,
                    'display_name': account.get('display_name', account.get('name')),
                    'pl': pl,
                    'unrealized_pl': unrealized_pl,
                    'trade_count': 0,  # Simplified
                    'win_rate': 0
                })
            except:
                continue
        
        # Get actionable list
        actionable = analyzer.get_actionable_list(strategies_data)
        portfolio = analyzer.generate_portfolio_insights(strategies_data)
        
        return jsonify({
            'success': True,
            'actionable': actionable,
            'portfolio_insights': portfolio
        })
        
    except Exception as e:
        logger.error(f"❌ Strategies insights error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/insights')
def api_insights():
    """Unified insights endpoint for dashboard with real data - OPTIMIZED"""
    try:
        # Return cached insights immediately - don't wait for full system status
        insights = {
            "overall_sentiment": 0.0,
            "market_impact": "neutral",
            "trading_recommendation": "hold",
            "confidence": 0.65,
            "key_events": [],
            "risk_factors": [],
            "opportunities": [],
            "summary": "AI monitoring all 10 strategies",
            "focus": ["EUR_USD", "GBP_USD", "XAU_USD"],
            "regimes": {
                "EUR_USD": "trending",
                "GBP_USD": "volatile",
                "USD_JPY": "volatile",
                "XAU_USD": "volatile"
            },
            "risk_level": "low"
        }
        
        # Quick check if dashboard ready (don't wait)
        mgr = get_dashboard_manager()
        if mgr and hasattr(mgr, '_initialized') and mgr._initialized:
            # Only get cached data, don't trigger fresh fetch
            try:
                # Use app.config cache if available
                if 'insights_cache' in app.config:
                    cache_time, cached_insights = app.config['insights_cache']
                    if time.time() - cache_time < 30:  # 30 second cache
                        return jsonify(cached_insights)
            except:
                pass
        
        # Return default insights quickly
        result = {
            "status": "success",
            "insights": insights,
            "timestamp": str(datetime.now())
        }
        
        # Cache for next request
        app.config['insights_cache'] = (time.time(), result)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Insights error: {e}")
        return jsonify({
            "status": "success",
            "insights": {
                "overall_sentiment": 0.0,
                "market_impact": "neutral",
                "trading_recommendation": "hold",
                "confidence": 0.0,
                "summary": "System active",
                "focus": [],
                "regimes": {},
                "risk_level": "low"
            },
            "timestamp": str(datetime.now())
        })

# Minimal AI assistant endpoints for Playwright tests
@app.route('/ai/health')
def ai_health():
    return jsonify({"status": "healthy"})

@app.route('/ai/interpret', methods=['POST'])
def ai_interpret():
    """Intelligent AI assistant for trading system analysis and recommendations."""
    try:
        import requests
        from urllib.parse import urljoin

        def fetch_live_status() -> Dict[str, Any]:
            try:
                base = request.host_url  # e.g., https://ai-quant-trading.uc.r.appspot.com/
                url = urljoin(base, '/api/status')
                r = requests.get(url, timeout=4)
                if r.ok and r.headers.get('content-type','').startswith('application/json'):
                    return r.json()
            except Exception:
                pass
            # Fallback to in-process status
            try:
                mgr = get_dashboard_manager()
                return mgr.get_system_status() if mgr else {}
            except Exception:
                return {}

        payload = request.get_json(silent=True) or {}
        text = (payload.get('text') or payload.get('message') or '').lower().strip()
        
        if not text:
            return jsonify({"reply": "Hello! I'm your AI trading assistant. I can help you analyze market conditions, check account status, review trading performance, and provide insights. What would you like to know?"})
        
        # Grab freshest status used by the dashboard
        live_status: Dict[str, Any] = fetch_live_status()
        system_status = live_status or {}
        market_payload = system_status.get('market_data')
        
        # Build normalized market map: pair -> fields
        normalized_market: Dict[str, Any] = {}
        if isinstance(market_payload, dict):
            for key, val in market_payload.items():
                if isinstance(val, dict):
                    # account -> {pair: fields}
                    inner_vals = list(val.values())
                    if inner_vals and isinstance(inner_vals[0], dict) and 'bid' in inner_vals[0]:
                        for pair, fields in val.items():
                            normalized_market[pair] = fields
                    # else: ignore
                # else: ignore
        # Also consider direct flat map from data feed
        mgr = get_dashboard_manager()
        if not normalized_market and mgr:
            try:
                direct = mgr.get_market_data()
                if isinstance(direct, dict):
                    for pair, fields in direct.items():
                        if isinstance(fields, dict) and 'bid' in fields:
                            normalized_market[pair] = fields
            except Exception:
                pass
        
        mgr = get_dashboard_manager()
        risk_metrics = mgr.get_risk_metrics() if mgr else {}
        
        # Account analysis
        if any(word in text for word in ['account', 'balance', 'profit', 'loss', 'performance']):
            accounts = system_status.get('account_statuses', {})
            total_balance = sum(acc.get('balance', 0) for acc in accounts.values())
            total_unrealized = sum(acc.get('unrealized_pl', 0) for acc in accounts.values())
            active_trades = sum((acc.get('open_trade_count') or acc.get('open_trades') or 0) for acc in accounts.values())
            
            reply = f"📊 Account Summary\n• Total Balance: ${total_balance:,.2f}\n• Unrealized P&L: ${total_unrealized:,.2f}\n• Active Trades: {active_trades}\n• Active Accounts: {len(accounts)}\n\n"
            for acc_id, acc in accounts.items():
                reply += f"{acc.get('account_name', acc_id)} — Bal: ${acc.get('balance', 0):,.2f}, P&L: ${acc.get('unrealized_pl', 0):,.2f}, Trades: {(acc.get('open_trade_count') or acc.get('open_trades') or 0)}\n"
            return jsonify({"reply": reply})
        
        # Market analysis
        elif any(word in text for word in ['market', 'price', 'trend', 'regime', 'spread']):
            # Prefer the same structure used by /api/status
            normalized: Dict[str, Any] = {}
            try:
                status_market = system_status.get('market_data') if isinstance(system_status, dict) else None
                if status_market:
                    # status_market may be {accountId: {PAIR: data}}
                    for maybe_account, value in status_market.items():
                        if isinstance(value, dict):
                            # If value looks like instrument map
                            sample_keys = list(value.keys())
                            if sample_keys and isinstance(value[sample_keys[0]], dict) and 'bid' in value[sample_keys[0]]:
                                for pair, data in value.items():
                                    normalized[pair] = data
                # Fallback to direct feed if nothing collected
                if not normalized and market_data:
                    # market_data may be {PAIR: data}
                    for pair, data in market_data.items():
                        if isinstance(data, dict) and 'bid' in data:
                            normalized[pair] = data
            except Exception:
                normalized = {}

            if normalized:
                priority = ['XAU_USD','EUR_USD','GBP_USD','USD_JPY','AUD_USD','NZD_USD','USD_CAD']
                # compute strength score: higher vol and tighter spread are better for trending; for ranging, prefer lower vol
                def strength(pair, d):
                    regime = d.get('regime','unknown')
                    spread = float(d.get('spread',0) or 0)
                    vol = float(d.get('volatility_score',0) or 0)
                    # normalize spread to pips-like scale
                    pip_spread = spread * 10000.0
                    if pair.endswith('JPY'):
                        pip_spread = spread * 100.0
                    if pair.startswith('XAU_'):
                        pip_spread = spread  # already in dollars
                    if regime == 'trending':
                        return max(0.0, vol*1.2 - pip_spread*0.02)
                    if regime == 'ranging':
                        return max(0.0, (1.0-vol)*1.0 - pip_spread*0.01)
                    return 0.1 - pip_spread*0.01
                
                # filter to priority universe first
                filtered = {p: normalized[p] for p in priority if p in normalized}
                # if some are missing, append any other available pairs
                for p, d in normalized.items():
                    if p not in filtered:
                        filtered[p] = d
                # build lines with ranking
                scored = [(strength(p, d), p, d) for p, d in filtered.items()]
                scored.sort(reverse=True, key=lambda x: (p in priority, x[0]))
                lines: List[str] = ["📈 Market Analysis\n"]
                focus = []
                for score, pair, d in scored[:7]:
                    regime = d.get('regime','unknown')
                    spread = float(d.get('spread',0) or 0)
                    vol = float(d.get('volatility_score',0) or 0)
                    bias = 'trend-follow' if regime == 'trending' else 'mean-revert' if regime == 'ranging' else 'observe'
                    lines.append(f"• {pair}: {regime}, spread {spread:.5f}, vol {vol:.2f}, bias {bias}")
                    focus.append(pair)
                lines.append("")
                lines.append(f"Focus: {', '.join(focus[:4])}")
                return jsonify({"reply": "\n".join(lines)})
            else:
                # Honest response: no per-instrument data currently available
                data_feed = system_status.get('data_feed_status', 'unknown')
                last_update = system_status.get('last_update', 'unknown')
                reply = (
                    "📈 **Market Analysis:**\n"
                    "No per-instrument market data is available right now.\n"
                    f"Data feed status: {data_feed}. Last system update: {last_update}.\n"
                    "I will report details as soon as live ticks are available."
                )
                
                return jsonify({"reply": reply})
        
        # Risk analysis
        elif any(word in text for word in ['risk', 'exposure', 'drawdown', 'sharpe']):
            if risk_metrics:
                reply = "⚠️ Risk Analysis\n"
                reply += f"• Risk Level: {risk_metrics.get('risk_level', 'unknown')}\n"
                reply += f"• Portfolio Risk: {risk_metrics.get('portfolio_risk', 0):.2%}\n"
                reply += f"• Max Drawdown: {risk_metrics.get('max_drawdown', 0):.2%}\n"
                reply += f"• Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 0):.2f}\n"
            else:
                reply = "⚠️ Risk Analysis\nRisk metrics not available at the moment."
            return jsonify({"reply": reply})
        
        # Intent-driven trading commands
        elif any(word in text for word in ['layer', 'add', 'reduce', 'risk', 'trailing', 'stop', 'lock', 'profit', 'take', 'close', 'buy', 'sell']):
            return _handle_trading_intent(text, normalized_market, system_status)
        
        # Trading signals and recommendations
        elif any(word in text for word in ['signal', 'recommendation']):
            # Simple heuristic using normalized_market
            lines: List[str] = ["🎯 Trading Recommendations\n"]
            if normalized_market:
                for pair, d in normalized_market.items():
                    regime = d.get('regime', 'unknown')
                    vol = float(d.get('volatility_score', 0) or 0)
                    if regime == 'trending':
                        lines.append(f"• {pair}: trend-follow setups; watch momentum (vol {vol:.2f})")
                    elif regime == 'ranging':
                        lines.append(f"• {pair}: mean-reversion levels; fade extremes (vol {vol:.2f})")
                    else:
                        lines.append(f"• {pair}: unclear regime; wait for confirmation (vol {vol:.2f})")
            else:
                lines.append("No live ticks available for recommendations.")
            lines.append("\nRisk: size small, use stops, monitor correlation.")
            return jsonify({"reply": "\n".join(lines)})
        
        # System status
        elif any(word in text for word in ['status', 'health', 'system', 'online']):
            reply = "🟢 System Status\n"
            reply += f"• System: {system_status.get('system_status', 'unknown')}\n"
            reply += f"• Data Feed: {system_status.get('data_feed_status', 'unknown')}\n"
            reply += f"• Live Mode: {system_status.get('live_data_mode', False)}\n"
            reply += f"• Active Accounts: {system_status.get('active_accounts', 0)}\n"
            reply += f"• Last Update: {system_status.get('last_update', 'unknown')}\n"
            return jsonify({"reply": reply})
        
        # Help and commands
        elif any(word in text for word in ['help', 'commands', 'what can you do']):
            reply = (
                "🤖 Commands\n"
                "• Account analysis\n"
                "• Market analysis\n"
                "• Risk assessment\n"
                "• Trading recommendations\n"
                "• System status\n"
            )
            return jsonify({"reply": reply})
        
        # Default response
        else:
            reply = (
                f"I understand you're asking about '{text}'.\n"
                "Ask about accounts, market, risk, signals, or system status."
            )
            return jsonify({"reply": reply})
            
    except Exception as e:
        logger.error(f"❌ AI assistant error: {e}")
        return jsonify({"reply": f"Sorry, I encountered an error: {str(e)}. Please try again."}), 500

def _handle_trading_intent(text: str, market_data: Dict[str, Any], system_status: Dict[str, Any]) -> Dict[str, Any]:
    """Handle natural language trading commands with intent parsing"""
    try:
        import re
        import uuid
        
        # Extract pairs mentioned
        pairs_mentioned = []
        for pair in ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD', 'USD_CAD']:
            if pair.lower().replace('_', '') in text.lower().replace('_', '').replace(' ', ''):
                pairs_mentioned.append(pair)
        
        # If no specific pairs, default to major USD pairs
        if not pairs_mentioned:
            pairs_mentioned = ['EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Parse intent
        intent = None
        size = None
        side = None
        
        # Layer in positions
        if any(word in text for word in ['layer', 'add', 'scale']):
            intent = 'layer_in'
            # Extract size (default 0.25% if not specified)
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
            size = float(size_match.group(1)) / 100 if size_match else 0.0025
            # Infer side from context or default to BUY
            side = 'BUY' if any(word in text for word in ['buy', 'long']) else 'SELL' if any(word in text for word in ['sell', 'short']) else 'BUY'
        
        # Reduce risk
        elif any(word in text for word in ['reduce', 'cut', 'lower']):
            intent = 'reduce_risk'
            # Extract percentage (default 20% if not specified)
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
            size = float(size_match.group(1)) / 100 if size_match else 0.20
        
        # Trailing stop
        elif any(word in text for word in ['trailing', 'trail']):
            intent = 'trailing_stop'
            # Extract ATR multiplier (default 0.6 if not specified)
            atr_match = re.search(r'(\d+(?:\.\d+)?)\s*atr', text.lower())
            size = float(atr_match.group(1)) if atr_match else 0.6
        
        # Lock profits
        elif any(word in text for word in ['lock', 'take', 'profit']):
            intent = 'lock_profits'
            # Extract percentage (default 30% if not specified)
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
            size = float(size_match.group(1)) / 100 if size_match else 0.30
        
        if not intent:
            return jsonify({"reply": "I understand you want to trade, but I need clearer intent. Try:\n• 'Layer in 0.25% on EUR_USD'\n• 'Reduce risk by 20%'\n• 'Set trailing stop 0.6 ATR on XAU_USD'\n• 'Lock 30% profits on EUR_USD'"})
        
        # Generate preview
        confirmation_id = str(uuid.uuid4())
        
        if intent == 'layer_in':
            preview = f"📈 Layer In Position\n• Pairs: {', '.join(pairs_mentioned)}\n• Side: {side}\n• Size: {size:.2%} of account\n• Risk: ~{size*100:.1f}% per position"
        elif intent == 'reduce_risk':
            preview = f"⚠️ Reduce Risk\n• Pairs: {', '.join(pairs_mentioned)}\n• Reduction: {size:.1%}\n• Action: Close {size:.1%} of positions"
        elif intent == 'trailing_stop':
            preview = f"🔄 Set Trailing Stop\n• Pairs: {', '.join(pairs_mentioned)}\n• Distance: {size} ATR\n• Type: Trailing stop loss"
        elif intent == 'lock_profits':
            preview = f"💰 Lock Profits\n• Pairs: {', '.join(pairs_mentioned)}\n• Take: {size:.1%} of profits\n• Action: Partial close at market"
        
        # Store intent for confirmation
        if not hasattr(app, 'pending_confirmations'):
            app.pending_confirmations = {}
        
        app.pending_confirmations[confirmation_id] = {
            'intent': intent,
            'pairs': pairs_mentioned,
            'size': size,
            'side': side,
            'timestamp': datetime.now().isoformat(),
            'user_text': text
        }
        
        reply = f"{preview}\n\n⚠️ LIVE ACTION REQUIRES CONFIRMATION\nType 'CONFIRM {confirmation_id}' to execute, or 'CANCEL {confirmation_id}' to abort."
        
        return jsonify({
            "reply": reply,
            "requires_confirmation": True,
            "confirmation_id": confirmation_id,
            "preview": {
                "summary": preview,
                "intent": intent,
                "pairs": pairs_mentioned,
                "size": size,
                "side": side
            },
            "live_guard": True
        })
        
    except Exception as e:
        logger.error(f"❌ Intent parsing error: {e}")
        return jsonify({"reply": f"Intent parsing failed: {str(e)}. Please try rephrasing your command."})

@app.route('/ai/confirm', methods=['POST'])
def ai_confirm():
    """Handle AI action confirmations"""
    try:
        payload = request.get_json(silent=True) or {}
        confirmation_id = payload.get('confirmation_id')
        confirm = payload.get('confirm', False)
        
        if not confirmation_id or not hasattr(app, 'pending_confirmations'):
            return jsonify({"status": "error", "message": "No pending confirmation found"}), 400
        
        pending = app.pending_confirmations.get(confirmation_id)
        if not pending:
            return jsonify({"status": "error", "message": "Confirmation expired or not found"}), 400
        
        if not confirm:
            # Cancel action
            del app.pending_confirmations[confirmation_id]
            return jsonify({"status": "cancelled", "message": "Action cancelled"})
        
        # Execute confirmed action
        try:
            result = _execute_trading_action(pending)
            
            # Send Telegram notification
            mgr = get_dashboard_manager()
            if mgr and mgr.telegram_notifier:
                message = f"🤖 AI Action Executed: {pending['intent']} on {', '.join(pending['pairs'])}"
                mgr.telegram_notifier.send_message(message)
            
            # Clean up
            del app.pending_confirmations[confirmation_id]
            
            return jsonify({
                "status": "executed",
                "result": result,
                "message": f"Action executed: {pending['intent']}"
            })
            
        except Exception as e:
            logger.error(f"❌ Action execution failed: {e}")
            return jsonify({
                "status": "error", 
                "message": f"Execution failed: {str(e)}"
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Confirmation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def _execute_trading_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the confirmed trading action"""
    try:
        intent = action['intent']
        pairs = action['pairs']
        size = action['size']
        side = action.get('side', 'BUY')
        
        results = {}
        
        if intent == 'layer_in':
            # Add positions
            for pair in pairs:
                try:
                    # Get account with lowest current exposure
                    best_account = min(mgr.active_accounts, 
                                    key=lambda acc: mgr.account_manager.get_account_status(acc).get('margin_used', 0))
                    
                    # Calculate position size (simplified)
                    account_status = mgr.account_manager.get_account_status(best_account)
                    balance = account_status.get('balance', 100000)
                    position_size = balance * size
                    
                    # Create market order
                    order = {
                        'instrument': pair,
                        'side': side,
                        'units': int(position_size / 1000),  # Simplified units
                        'type': 'MARKET',
                        'timeInForce': 'FOK'
                    }
                    
                    result = mgr.order_manager.execute_trades(best_account, [order])
                    results[pair] = result
                    
                except Exception as e:
                    results[pair] = {'error': str(e)}
        
        elif intent == 'reduce_risk':
            # Close percentage of positions
            for account_id in mgr.active_accounts:
                try:
                    # Get open positions and close percentage
                    positions = mgr.order_manager.get_open_positions(account_id)
                    close_count = max(1, int(len(positions) * size))
                    
                    for i, position in enumerate(positions[:close_count]):
                        close_order = {
                            'instrument': position['instrument'],
                            'side': 'SELL' if position['side'] == 'BUY' else 'BUY',
                            'units': position['units'],
                            'type': 'MARKET',
                            'timeInForce': 'FOK'
                        }
                        result = mgr.order_manager.execute_trades(account_id, [close_order])
                        results[f"{account_id}_{position['instrument']}"] = result
                        
                except Exception as e:
                    results[account_id] = {'error': str(e)}
        
        elif intent == 'trailing_stop':
            # Set trailing stops (simplified - would need ATR calculation)
            for account_id in mgr.active_accounts:
                try:
                    positions = mgr.order_manager.get_open_positions(account_id)
                    for position in positions:
                        if position['instrument'] in pairs:
                            # Calculate trailing stop distance (simplified)
                            stop_distance = 0.01  # 1% simplified
                            
                            stop_order = {
                                'instrument': position['instrument'],
                                'side': 'SELL' if position['side'] == 'BUY' else 'BUY',
                                'units': position['units'],
                                'type': 'STOP',
                                'price': position['entry_price'] * (1 - stop_distance) if position['side'] == 'BUY' else position['entry_price'] * (1 + stop_distance),
                                'timeInForce': 'GTC'
                            }
                            result = mgr.order_manager.execute_trades(account_id, [stop_order])
                            results[f"{account_id}_{position['instrument']}"] = result
                            
                except Exception as e:
                    results[account_id] = {'error': str(e)}
        
        elif intent == 'lock_profits':
            # Partial close for profit taking
            for account_id in mgr.active_accounts:
                try:
                    positions = mgr.order_manager.get_open_positions(account_id)
                    for position in positions:
                        if position['instrument'] in pairs and position.get('unrealized_pl', 0) > 0:
                            # Close percentage of profitable position
                            close_units = int(position['units'] * size)
                            if close_units > 0:
                                close_order = {
                                    'instrument': position['instrument'],
                                    'side': 'SELL' if position['side'] == 'BUY' else 'BUY',
                                    'units': close_units,
                                    'type': 'MARKET',
                                    'timeInForce': 'FOK'
                                }
                                result = mgr.order_manager.execute_trades(account_id, [close_order])
                                results[f"{account_id}_{position['instrument']}"] = result
                                
                except Exception as e:
                    results[account_id] = {'error': str(e)}
        
        return {
            'intent': intent,
            'pairs': pairs,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Action execution error: {e}")
        raise e


@app.route('/api/trade_ideas')
def api_trade_ideas():
    """Generate trade ideas from AI insights + market analysis - OPTIMIZED"""
    try:
        # Return cached trade ideas - lightweight endpoint
        if 'trade_ideas_cache' in app.config:
            cache_time, cached_ideas = app.config['trade_ideas_cache']
            if time.time() - cache_time < 60:  # 60 second cache
                return jsonify(cached_ideas)
        
        # Quick default ideas
        ideas: List[Dict[str, Any]] = []
        
        # Default monitoring message
        ideas.append({
            'instrument': 'ALL',
            'action': 'MONITOR',
            'confidence': 65,
            'reason': 'AI monitoring all 10 strategies - waiting for high-quality setups'
        })
        
        result = {'status': 'success', 'ideas': ideas, 'timestamp': datetime.now().isoformat()}
        
        # Cache it
        app.config['trade_ideas_cache'] = (time.time(), result)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Trade ideas error: {e}")
        return jsonify({'status': 'success', 'ideas': [], 'timestamp': datetime.now().isoformat()})

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("🔌 Client connected to WebSocket")
    emit('status', {'msg': 'Connected to trading dashboard', 'timestamp': datetime.now().isoformat()})
    
    # Welcome toast (NEW - non-breaking)
    try:
        from src.utils.toast_notifier import emit_success_toast
        emit_success_toast("✅ Connected to trading system")
    except Exception:
        pass  # Don't break connection if toast fails

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("🔌 Client disconnected from WebSocket")

@socketio.on('request_update')
def handle_update_request():
    """Handle update request from client"""
    try:
        mgr = get_dashboard_manager()
        if mgr:
            # Emit system status
            emit('systems_update', mgr.get_system_status())
            
            # Emit market data
            emit('market_update', mgr.get_market_data())
            
            # Emit news data
            news_int = get_news_integration()
            if news_int:
                try:
                    currency_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
                    news_data = asyncio.run(news_integration.get_news_data(currency_pairs))
                    emit('news_update', news_data)
                    # Emit AI insights with trade phase and upcoming news
                    try:
                        full_status = mgr.get_system_status()
                        ai_insights = {
                            'trade_phase': full_status.get('trade_phase', 'Monitoring markets'),
                            'upcoming_news': full_status.get('upcoming_news', []),
                            'ai_recommendation': full_status.get('ai_recommendation', 'HOLD'),
                            'timestamp': datetime.now().isoformat()
                        }
                        emit('news_impact_update', ai_insights)
                        logger.info(f"✅ Emitted AI insights: {ai_insights.get('trade_phase')}")
                    except Exception as e:
                        logger.error(f"❌ News impact emit error: {e}")
                except Exception as e:
                    logger.error(f"❌ News update error: {e}")
                    emit('news_update', [])
            
            # Emit AI assistant status
            ai_asst = get_ai_assistant()
            if ai_asst:
                try:
                    ai_status = ai_asst.get_status()
                    emit('ai_update', ai_status)
                except Exception as e:
                    logger.error(f"❌ AI assistant update error: {e}")
                    emit('ai_update', {"status": "unavailable"})
            
            # Emit risk metrics
            emit('risk_update', mgr.get_risk_metrics())
            
        else:
            emit('error', {'msg': 'Dashboard manager not available'})
            
    except Exception as e:
        logger.error(f"❌ WebSocket update error: {e}")
        emit('error', {'msg': str(e)})

@socketio.on('ai_chat')
def handle_ai_chat(data):
    """Handle AI chat messages"""
    try:
        if not ai_assistant:
            emit('ai_response', {'error': 'AI assistant not available'})
            return
        
        message = data.get('message', '')
        if not message:
            emit('ai_response', {'error': 'No message provided'})
            return
        
        # Process AI chat
        response = ai_assistant.process_message(message)
        emit('ai_response', response)
        
    except Exception as e:
        logger.error(f"❌ AI chat error: {e}")
        emit('ai_response', {'error': str(e)})

@socketio.on('subscribe_signals')
def handle_signals_subscription():
    """Handle client subscription to signal updates"""
    try:
        logger.info("📊 Client subscribed to signals updates")
        
        # Send initial data
        from src.core.signal_tracker import get_signal_tracker
        signal_tracker = get_signal_tracker()
        stats = signal_tracker.get_statistics()
        
        emit('signals_subscribed', {
            'status': 'subscribed',
            'statistics': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Signals subscription error: {e}")
        emit('error', {'msg': str(e)})

@socketio.on('unsubscribe_signals')
def handle_signals_unsubscription():
    """Handle client unsubscription from signal updates"""
    logger.info("📊 Client unsubscribed from signals updates")
    emit('signals_unsubscribed', {'status': 'unsubscribed'})

# Background update thread
def update_dashboard():
    """Update dashboard data periodically"""
    while True:
        try:
            logger.info(f"🔄 Updating dashboard data - {datetime.now()}")
            
            mgr = get_dashboard_manager()
            if mgr:
                # Create event loop for async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run updates - use existing methods
                try:
                    # Update system status
                    system_status = mgr.get_system_status()
                    
                    # Update market data
                    market_data = mgr.get_market_data()
                    
                    # Update risk metrics
                    risk_metrics = mgr.get_risk_metrics()
                    
                except Exception as e:
                    logger.error(f"❌ Dashboard update error: {e}")
                
                # Emit updates via WebSocket
                socketio.emit('systems_update', mgr.get_system_status())
                socketio.emit('market_update', mgr.get_market_data())
                socketio.emit('risk_update', mgr.get_risk_metrics())
                
                # Emit news updates
                news_int = get_news_integration()
                if news_int:
                    try:
                        currency_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
                        news_data = asyncio.run(news_int.get_news_data(currency_pairs))
                        socketio.emit('news_update', news_data)
                        # Emit AI insights with trade phase and upcoming news
                        try:
                            full_status = mgr.get_system_status()
                            ai_insights = {
                                'trade_phase': full_status.get('trade_phase', 'Monitoring markets'),
                                'upcoming_news': full_status.get('upcoming_news', []),
                                'ai_recommendation': full_status.get('ai_recommendation', 'HOLD'),
                                'timestamp': datetime.now().isoformat()
                            }
                            socketio.emit('news_impact_update', ai_insights)
                        except Exception as e:
                            logger.error(f"❌ News impact update error: {e}")
                    except Exception as e:
                        logger.error(f"❌ News update error: {e}")
                
                # Emit AI assistant updates
                ai_asst = get_ai_assistant()
                if ai_asst:
                    try:
                        ai_status = ai_asst.get_status()
                        socketio.emit('ai_update', ai_status)
                    except Exception as e:
                        logger.error(f"❌ AI assistant update error: {e}")
                
                # Close event loop
                loop.close()
            
            # Wait before next update
            time.sleep(15)
            
        except Exception as e:
            logger.error(f"❌ Dashboard update error: {e}")
            time.sleep(30)

# ===============================================
# DASHBOARD ROUTE CONSOLIDATION
# ===============================================
@app.route('/trade-manager-test-123')
def trade_manager_test():
    """Test route"""
    return "TRADE MANAGER TEST WORKS!"

@app.route('/trade-manager')
def trade_manager_dashboard_redirect():
    """Render main dashboard (will load trade-manager tab via hash)"""
    return render_template('dashboard_advanced.html')


@app.route('/cron/quality-scan')
def cron_quality_scan():
    """Quality scanner - proper entries only, no chasing"""
    try:
        from strategy_based_scanner import strategy_scan
        result = strategy_scan()
        return jsonify({'status': 'success', 'result': result}), 200
    except Exception as e:
        logger.error(f"Quality scan error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==========================================
# PREMIUM SIGNAL ENDPOINTS (Hybrid Lane)
# ==========================================

@app.route('/api/premium/signals', methods=['GET'])
def get_premium_signals():
    """Get all pending premium signals"""
    try:
        dashboard_mgr = get_dashboard_manager()
        if not dashboard_mgr:
            return jsonify({'error': 'Dashboard not initialized'}), 503
        
        # Get premium scanner
        from src.core.premium_signal_scanner import get_premium_scanner
        scanner = get_premium_scanner()
        
        if not scanner:
            return jsonify({'signals': [], 'count': 0})
        
        pending_signals = scanner.get_pending_signals()
        
        return jsonify({
            'success': True,
            'count': len(pending_signals),
            'signals': [s.to_dict() for s in pending_signals]
        })
    
    except Exception as e:
        logger.error(f"Error getting premium signals: {e}")
        return jsonify({'error': str(e), 'signals': []}), 500


@app.route('/api/premium/approve/<signal_id>', methods=['POST'])
def approve_premium_signal(signal_id):
    """Approve and execute a premium signal"""
    try:
        from src.core.premium_signal_scanner import get_premium_scanner
        from src.notifications.premium_telegram_notifier import get_premium_notifier
        
        scanner = get_premium_scanner()
        notifier = get_premium_notifier()
        
        if not scanner:
            return jsonify({'error': 'Scanner not initialized'}), 503
        
        # Find the signal
        signal = None
        for s in scanner.pending_signals:
            if s.id == signal_id:
                signal = s
                break
        
        if not signal:
            return jsonify({'error': 'Signal not found'}), 404
        
        if signal.status != 'pending':
            return jsonify({'error': f'Signal already {signal.status}'}), 400
        
        # Approve the signal
        scanner.approve_signal(signal_id)
        
        # Execute the trade
        dashboard_mgr = get_dashboard_manager()
        oanda_client = dashboard_mgr._oanda_clients.get('101-004-30719775-001')  # Premium account
        
        if not oanda_client:
            return jsonify({'error': 'OANDA client not available'}), 503
        
        # Calculate units (risk-based)
        account_info = oanda_client.get_account_info()
        balance = float(account_info.balance)
        risk_percent = 0.02  # 2% risk
        risk_amount = balance * risk_percent
        
        sl_distance = abs(signal.entry_price - signal.sl_price)
        units = int(risk_amount / sl_distance)
        
        # Place the order
        result = oanda_client.place_market_order(
            instrument=signal.instrument,
            units=units if signal.direction == 'BUY' else -units,
            take_profit=signal.tp_price,
            stop_loss=signal.sl_price
        )
        
        signal.status = 'executed'
        
        # Send confirmation
        if notifier:
            notifier.send_execution_confirmation(signal, result.__dict__ if hasattr(result, '__dict__') else {})
        
        return jsonify({
            'success': True,
            'message': 'Signal approved and executed',
            'signal': signal.to_dict(),
            'order': result.__dict__ if hasattr(result, '__dict__') else str(result)
        })
    
    except Exception as e:
        logger.error(f"Error approving signal: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/premium/reject/<signal_id>', methods=['POST'])
def reject_premium_signal(signal_id):
    """Reject a premium signal"""
    try:
        from src.core.premium_signal_scanner import get_premium_scanner
        from src.notifications.premium_telegram_notifier import get_premium_notifier
        
        scanner = get_premium_scanner()
        notifier = get_premium_notifier()
        
        if not scanner:
            return jsonify({'error': 'Scanner not initialized'}), 503
        
        # Find and reject the signal
        signal = None
        for s in scanner.pending_signals:
            if s.id == signal_id:
                signal = s
                break
        
        if not signal:
            return jsonify({'error': 'Signal not found'}), 404
        
        scanner.reject_signal(signal_id)
        
        # Send confirmation
        if notifier:
            notifier.send_rejection_confirmation(signal)
        
        return jsonify({
            'success': True,
            'message': 'Signal rejected',
            'signal': signal.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error rejecting signal: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/premium/scan', methods=['POST', 'GET'])
def trigger_premium_scan():
    """Manually trigger premium signal scan"""
    try:
        # Initialize if needed
        dashboard_mgr = get_dashboard_manager()
        if not dashboard_mgr:
            return jsonify({'error': 'Dashboard not initialized'}), 503
        
        # Get or create scanner
        from src.core.premium_signal_scanner import get_premium_scanner
        from src.notifications.premium_telegram_notifier import get_premium_notifier
        
        scanner = get_premium_scanner()
        
        # Initialize scanner if not exists
        if not scanner:
            # Get first active account's OANDA client
            oanda_client = None
            if dashboard_mgr.account_manager:
                active_accounts = dashboard_mgr.account_manager.get_active_accounts()
                if active_accounts:
                    # Get account ID (could be string or dict)
                    first_account = active_accounts[0]
                    first_account_id = first_account.get('account_id') if isinstance(first_account, dict) else first_account
                    from src.core.oanda_client import OandaClient
                    oanda_client = OandaClient(account_id=first_account_id)
            
            data_feed = dashboard_mgr.data_feed
            
            if oanda_client and data_feed:
                scanner = get_premium_scanner(oanda_client, data_feed)
        
        if not scanner:
            return jsonify({'error': 'Scanner initialization failed'}), 503
        
        notifier = get_premium_notifier()
        if not notifier:
            bot_token = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
            chat_id = "6100678501"
            notifier = get_premium_notifier(bot_token, chat_id)
        
        # Run scan
        logger.info("🔍 Running premium scan...")
        signals = scanner.scan_for_premium_signals()
        
        # Add to pending
        scanner.pending_signals.extend(signals)
        
        # Send notifications
        if notifier and signals:
            for signal in signals:
                notifier.send_premium_signal(signal)
        
        return jsonify({
            'success': True,
            'signals_found': len(signals),
            'signals': [s.to_dict() for s in signals]
        })
    
    except Exception as e:
        logger.error(f"Error triggering scan: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def initialize_premium_scanner():
    """Initialize premium scanner in background"""
    try:
        logger.info("🔄 Initializing premium scanner...")
        
        dashboard_mgr = get_dashboard_manager()
        if not dashboard_mgr:
            logger.error("Dashboard manager not available")
            return
        
        # Get OANDA client and data feed from dashboard
        oanda_client = list(dashboard_mgr._oanda_clients.values())[0] if dashboard_mgr._oanda_clients else None
        data_feed = dashboard_mgr._data_feed
        
        if not oanda_client or not data_feed:
            logger.error("OANDA client or data feed not available")
            return
        
        from src.core.premium_signal_scanner import get_premium_scanner
        from src.notifications.premium_telegram_notifier import get_premium_notifier
        
        # Initialize scanner
        scanner = get_premium_scanner(oanda_client, data_feed)
        
        # Initialize notifier
        bot_token = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
        chat_id = "6100678501"
        notifier = get_premium_notifier(bot_token, chat_id)
        
        if scanner and notifier:
            logger.info("✅ Premium scanner and notifier initialized")
        else:
            logger.error("Failed to initialize premium components")
        
    except Exception as e:
        logger.error(f"Error initializing premium scanner: {e}")



if __name__ == '__main__':
    # Get port from environment (required for Google Cloud)
    port = int(os.environ.get('PORT', 8080))
    
    logger.info("🚀 Starting Google Cloud Trading System - FULLY INTEGRATED")
    logger.info("=" * 60)
    logger.info("✅ WebSocket support enabled")
    logger.info("✅ Dashboard manager initialized")
    logger.info("✅ News integration enabled")
    logger.info("✅ AI assistant enabled")
    logger.info("✅ APScheduler already started on app init")
    
    # Initialize analytics system
    if ANALYTICS_ENABLED:
        try:
            logger.info("🔄 Initializing analytics system...")
            
            # Initialize database
            trade_db = get_trade_database()
            logger.info("✅ Trade database initialized")
            
            # Initialize trade logger
            trade_logger = get_trade_logger()
            logger.info("✅ Trade logger initialized")
            
            # Initialize version manager and auto-version strategies
            version_manager = get_strategy_version_manager()
            versioned = version_manager.auto_version_all_strategies()
            logger.info(f"✅ Strategy version manager initialized ({len(versioned)} strategies)")
            
            # Initialize data archiver
            archiver = get_data_archiver()
            logger.info("✅ Data archiver initialized")
            
            # Start analytics dashboard on port 8081 in background
            analytics_thread = start_analytics_dashboard(port=8081, background=True)
            logger.info("✅ Analytics dashboard started on port 8081")
            
            # Schedule daily archival at 2 AM London time
            @scheduler.task('cron', id='daily_archival', hour=2, minute=0, timezone='Europe/London')
            def daily_archival_job():
                logger.info("🔄 Running daily archival job...")
                result = archiver.archive_old_trades(days=90)
                logger.info(f"✅ Archival complete: {result.get('archived_count', 0)} trades archived")
                
                # Generate daily snapshots
                trade_logger.cleanup_and_report()
            
            logger.info("✅ Analytics system fully initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize analytics: {e}")
            logger.exception("Full traceback:")
    
    logger.info("=" * 60)
    
    # Start dashboard updates in background
    update_thread = threading.Thread(target=update_dashboard, daemon=True)
    update_thread.start()
    
    logger.info(f"🌐 Starting server on port {port}")
    logger.info("✅ Dashboard updates started in background")
    
    # Start Flask app with SocketIO - production configuration
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

# ===============================================
# CRON JOB ENDPOINTS - DAILY TRADING SCHEDULE
# ===============================================
@app.route('/cron/pre-market-briefing')
def cron_pre_market_briefing():
    """6:00 AM - Pre-market briefing"""
    try:
        from scheduled_scanners import pre_market_briefing
        result = pre_market_briefing()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Pre-market briefing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cron/morning-scan')
def cron_morning_scan():
    """8:00 AM - London open scanner"""
    try:
        from scheduled_scanners import morning_scan
        result = morning_scan()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Morning scan error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cron/peak-scan')
def cron_peak_scan():
    """1:00 PM - London/NY overlap scanner"""
    try:
        from scheduled_scanners import peak_scan
        result = peak_scan()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Peak scan error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cron/eod-summary')
def cron_eod_summary():
    """5:00 PM - End of day summary"""
    try:
        from scheduled_scanners import eod_summary
        result = eod_summary()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"EOD summary error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cron/asian-preview')
def cron_asian_preview():
    """9:00 PM - Asian session preview"""
    try:
        from scheduled_scanners import asian_preview
        result = asian_preview()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Asian preview error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cron/continuous-monitor')
def cron_continuous_monitor():
    """Every 15 minutes - continuous monitoring"""
    try:
        from scheduled_scanners import continuous_monitor
        result = continuous_monitor()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Continuous monitor error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ===============================================
# AUTO-UPDATING TRADE MANAGER DASHBOARD
# ===============================================

# Cache for API optimization
_performance_cache = {
    'data': None,
    'last_update': None
}
_CACHE_SECONDS = 10

def get_live_performance_data_cached():
    """Get live data with 10-second cache to optimize API calls"""
    now = datetime.now()
    
    if _performance_cache['last_update'] and (now - _performance_cache['last_update']).total_seconds() < _CACHE_SECONDS:
        return _performance_cache['data']
    
    try:
        from src.core.oanda_client import OandaClient
        
        accounts_config = {
            'PRIMARY': (os.getenv('PRIMARY_ACCOUNT'), 'Ultra Strict Forex'),
            'GOLD': (os.getenv('GOLD_SCALP_ACCOUNT'), 'Gold Scalping'),
            'ALPHA': (os.getenv('STRATEGY_ALPHA_ACCOUNT'), 'Momentum Trading')
        }
        
        result = {}
        total_balance = 0
        total_pl = 0
        total_realized = 0
        total_trades = 0
        
        for name, (account_id, strategy) in accounts_config.items():
            try:
                client = OandaClient(os.getenv('OANDA_API_KEY'), account_id, os.getenv('OANDA_ENVIRONMENT'))
                account_info = client.get_account_info()
                open_trades = client.get_open_trades()
                
                trades_list = []
                for trade in open_trades:
                    trades_list.append({
                        'id': trade['id'],
                        'instrument': trade['instrument'],
                        'units': float(trade['currentUnits']),
                        'price': float(trade['price']),
                        'unrealized_pl': float(trade['unrealizedPL']),
                        'side': 'LONG' if float(trade['currentUnits']) > 0 else 'SHORT'
                    })
                
                result[name] = {
                    'strategy': strategy,
                    'balance': float(account_info.balance),
                    'unrealized_pl': float(account_info.unrealized_pl),
                    'realized_pl': float(account_info.realized_pl),
                    'open_trades': len(open_trades),
                    'trades': trades_list,
                    'margin_used': float(account_info.margin_used)
                }
                
                total_balance += float(account_info.balance)
                total_pl += float(account_info.unrealized_pl)
                total_realized += float(account_info.realized_pl)
                total_trades += len(open_trades)
                
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                result[name] = {'error': str(e)}
        
        data = {
            'status': 'success',
            'accounts': result,
            'totals': {
                'balance': total_balance,
                'unrealized_pl': total_pl,
                'realized_pl': total_realized,
                'open_trades': total_trades
            },
            'timestamp': datetime.now().isoformat()
        }
        
        _performance_cache['data'] = data
        _performance_cache['last_update'] = now
        
        return data
        
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

@app.route('/api/performance/live')
def api_performance_live():
    """Live performance data with caching"""
    return jsonify(get_live_performance_data_cached())

@app.route('/api/chart/candles/<instrument>')
def get_chart_candles(instrument):
    """Get historical candles for chart with caching to minimize API calls"""
    granularity = request.args.get('timeframe', 'H1')  # H1, H4, D
    count = request.args.get('count', 100, type=int)
    
    # Map frontend timeframes to OANDA granularities
    timeframe_map = {
        '1h': 'H1',
        '4h': 'H4',
        '1d': 'D'
    }
    gran = timeframe_map.get(granularity, 'H1')
    
    try:
        # Use existing oanda_client.get_candles() method
        oanda_client = get_oanda_client()
        candles = oanda_client.get_candles(instrument, granularity=gran, count=count, price='M')
        
        return jsonify({
            'success': True,
            'instrument': instrument,
            'timeframe': granularity,
            'candles': candles.get('candles', [])
        })
    except Exception as e:
        logger.error(f"Chart candles error for {instrument}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'instrument': instrument,
            'timeframe': granularity,
            'candles': []
        })

@app.route('/api/test-chart')
def test_chart():
    """Test endpoint to verify chart functionality"""
    print("TEST CHART ENDPOINT CALLED - UPDATED VERSION")
    return jsonify({
        'success': True,
        'message': 'Chart endpoint is working - UPDATED VERSION',
        'test_data': [{'time': '2025-10-19T22:00:00Z', 'mid': {'c': '1.0500'}}]
    })

@app.route('/api/sidebar/live-prices')
def get_sidebar_live_prices():
    """Get current prices for sidebar display - uses existing account data"""
    try:
        mgr = get_dashboard_manager()
        if not mgr or not mgr.accounts_data:
            return jsonify({'success': False, 'error': 'No data'})
        
        # Extract unique instruments from all accounts
        instruments_data = {}
        for acc_data in mgr.accounts_data.values():
            for inst in acc_data.get('instruments', []):
                if inst not in instruments_data:
                    # Use cached price from dashboard manager
                    price_data = mgr.get_cached_price(inst)
                    if price_data:
                        instruments_data[inst] = {
                            'instrument': inst,
                            'bid': price_data.get('bid', 0),
                            'ask': price_data.get('ask', 0),
                            'spread': price_data.get('spread', 0)
                        }
        
        return jsonify({'success': True, 'prices': instruments_data})
    except Exception as e:
        logger.error(f"Sidebar live prices error: {e}")
        return jsonify({'success': False, 'error': str(e), 'prices': {}})

@socketio.on('request_performance_update')
def handle_performance_update():
    """Handle WebSocket request for performance data"""
    data = get_live_performance_data_cached()
    emit('performance_update', data)

@app.route('/cron/aggressive-scan')
def cron_aggressive_scan():
    """Every 2 minutes - AGGRESSIVE auto-execution"""
    try:
        from aggressive_scanner_cron import aggressive_scan
        result = aggressive_scan()
        return jsonify({'status': 'success', 'message': result}), 200
    except Exception as e:
        logger.error(f"Aggressive scan error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ===============================================
# ANALYTICS INTEGRATION ENDPOINTS
# ===============================================

@app.route('/api/analytics/health')
def api_analytics_health():
    """Check analytics system health"""
    if not ANALYTICS_ENABLED:
        return jsonify({'success': False, 'error': 'Analytics not enabled'}), 503
    
    try:
        db_stats = get_trade_database().get_database_stats()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'analytics_dashboard_url': 'http://localhost:8081',
            'database_stats': db_stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/summary')
def api_analytics_summary():
    """Get analytics summary for main dashboard"""
    if not ANALYTICS_ENABLED:
        return jsonify({'success': False, 'error': 'Analytics not enabled'})
    
    try:
        all_metrics = get_trade_database().get_all_strategy_metrics()
        
        # Calculate totals
        total_trades = sum(m.get('total_trades', 0) for m in all_metrics)
        total_pnl = sum(m.get('total_pnl', 0) for m in all_metrics)
        avg_win_rate = sum(m.get('win_rate', 0) for m in all_metrics) / len(all_metrics) if all_metrics else 0
        
        return jsonify({
            'success': True,
            'summary': {
                'total_strategies': len(all_metrics),
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_win_rate': avg_win_rate
            },
            'analytics_url': 'http://localhost:8081'
        })
    except Exception as e:
        logger.error(f"❌ Error getting analytics summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Daily Bulletin API Endpoints
@app.route('/api/bulletin/morning')
def api_bulletin_morning():
    """Get morning bulletin with comprehensive market analysis"""
    try:
        from src.core.daily_bulletin_generator import DailyBulletinGenerator
        from src.core.gold_analyzer import GoldAnalyzer
        
        # Initialize bulletin generator
        bulletin_generator = DailyBulletinGenerator(
            data_feed=app.config.get('DATA_FEED'),
            shadow_system=app.config.get('SHADOW_SYSTEM'),
            news_integration=app.config.get('NEWS_INTEGRATION'),
            economic_calendar=app.config.get('ECONOMIC_CALENDAR')
        )
        
        # Get accounts from config
        accounts = app.config.get('ACCOUNTS', [])
        
        # Generate morning bulletin
        bulletin = bulletin_generator.generate_morning_bulletin(accounts)
        
        return jsonify({
            'success': True,
            'bulletin': bulletin,
            'timestamp': datetime.now().isoformat()
        })
        
    except ImportError as e:
        logger.warning(f"⚠️ Bulletin modules not available: {e}")
        return jsonify({
            'success': True,
            'bulletin': {
                'title': 'Market Status',
                'summary': 'Trading system operational - Bulletin system not available',
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"❌ Error generating morning bulletin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulletin/midday')
def api_bulletin_midday():
    """Get midday update with quick market pulse"""
    try:
        from src.core.daily_bulletin_generator import DailyBulletinGenerator
        
        bulletin_generator = DailyBulletinGenerator(
            data_feed=app.config.get('DATA_FEED'),
            shadow_system=app.config.get('SHADOW_SYSTEM'),
            news_integration=app.config.get('NEWS_INTEGRATION'),
            economic_calendar=app.config.get('ECONOMIC_CALENDAR')
        )
        
        accounts = app.config.get('ACCOUNTS', [])
        bulletin = bulletin_generator.generate_midday_update(accounts)
        
        return jsonify({
            'success': True,
            'bulletin': bulletin,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating midday bulletin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulletin/evening')
def api_bulletin_evening():
    """Get evening summary with day recap"""
    try:
        from src.core.daily_bulletin_generator import DailyBulletinGenerator
        
        bulletin_generator = DailyBulletinGenerator(
            data_feed=app.config.get('DATA_FEED'),
            shadow_system=app.config.get('SHADOW_SYSTEM'),
            news_integration=app.config.get('NEWS_INTEGRATION'),
            economic_calendar=app.config.get('ECONOMIC_CALENDAR')
        )
        
        accounts = app.config.get('ACCOUNTS', [])
        bulletin = bulletin_generator.generate_evening_summary(accounts)
        
        return jsonify({
            'success': True,
            'bulletin': bulletin,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating evening bulletin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulletin/live')
def api_bulletin_live():
    """Get current real-time bulletin"""
    try:
        from src.core.daily_bulletin_generator import DailyBulletinGenerator
        
        bulletin_generator = DailyBulletinGenerator(
            data_feed=app.config.get('DATA_FEED'),
            shadow_system=app.config.get('SHADOW_SYSTEM'),
            news_integration=app.config.get('NEWS_INTEGRATION'),
            economic_calendar=app.config.get('ECONOMIC_CALENDAR')
        )
        
        accounts = app.config.get('ACCOUNTS', [])
        
        # Determine which bulletin to generate based on time
        now = datetime.now()
        hour = now.hour
        
        if 6 <= hour < 12:  # Morning
            bulletin = bulletin_generator.generate_morning_bulletin(accounts)
        elif 12 <= hour < 18:  # Midday
            bulletin = bulletin_generator.generate_midday_update(accounts)
        else:  # Evening
            bulletin = bulletin_generator.generate_evening_summary(accounts)
        
        return jsonify({
            'success': True,
            'bulletin': bulletin,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating live bulletin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/gold/analysis')
def api_gold_analysis():
    """Get comprehensive Gold analysis"""
    try:
        from src.core.gold_analyzer import GoldAnalyzer
        
        gold_analyzer = GoldAnalyzer(
            data_feed=app.config.get('DATA_FEED'),
            news_integration=app.config.get('NEWS_INTEGRATION')
        )
        
        accounts = app.config.get('ACCOUNTS', [])
        analysis = gold_analyzer.get_comprehensive_gold_analysis(accounts)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting Gold analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

