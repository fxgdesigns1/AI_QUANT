#!/usr/bin/env python3
"""
Advanced AI Trading Systems Dashboard - FIXED VERSION
Production-ready dashboard for Google Cloud deployment with live OANDA trading
FIXED: AI Assistant registration and proper socketio integration
"""

import os
import sys
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
import random
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../oanda_config.env'))

# Import live trading components
from ..core.account_manager import get_account_manager
from ..core.multi_account_data_feed import get_multi_account_data_feed
from ..core.multi_account_order_manager import get_multi_account_order_manager
from ..core.telegram_notifier import get_telegram_notifier
from ..strategies.ultra_strict_forex import get_ultra_strict_forex_strategy
from ..strategies.gold_scalping import get_gold_scalping_strategy
from ..strategies.momentum_trading import get_momentum_trading_strategy
from ..strategies.alpha import get_alpha_strategy

# NEW: Optional AI assistant registrar (import safe even if not enabled)
try:
    from .ai_assistant_api import register_ai_assistant  # type: ignore
except Exception:
    register_ai_assistant = None  # type: ignore

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Flask template/static directories explicitly
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_interval=25,   # seconds
    ping_timeout=60     # seconds
)

# Load configuration
def load_config():
    """Load dashboard configuration"""
    config = {
        'telegram': {
            'token': os.getenv('TELEGRAM_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID')
        },
        'data_sources': {
            'api_keys': {
                'oanda': {
                    'api_key': os.getenv('OANDA_API_KEY'),
                    'account_id': os.getenv('OANDA_ACCOUNT_ID'),
                    'environment': 'practice',
                    'base_url': 'https://api-fxpractice.oanda.com'
                }
            }
        },
        'risk_management': {
            'max_risk_per_trade': 0.02,  # 2% per trade
            'max_portfolio_risk': 0.75,   # CORRECTED: 75% total portfolio risk
            'max_correlation_risk': 0.75,
            'position_sizing_method': 'risk_based'
        },
        'data_validation': {
            'max_data_age_seconds': 300,  # 5 minutes
            'min_confidence_threshold': 0.5,  # CORRECTED: Lower threshold
            'require_live_data': True
        }
    }
    return config

@dataclass
class SystemStatus:
    name: str
    url: str
    status: str
    last_check: Optional[str]
    iteration: int
    uptime: str
    data_freshness: str
    is_live_data: bool
    last_price_update: Optional[str]
    error_count: int
    health_score: float
    risk_score: float = 0.0
    current_drawdown: float = 0.0
    daily_pl: float = 0.0

@dataclass
class MarketData:
    pair: str
    bid: float
    ask: float
    timestamp: str
    is_live: bool
    data_source: str
    spread: float
    last_update_age: int
    volatility_score: float = 0.0
    regime: str = 'unknown'
    correlation_risk: float = 0.0

@dataclass
class TradingMetrics:
    win_rate: float
    avg_duration: str
    risk_reward_ratio: float
    success_rate: float
    profit_factor: float
    timestamp: str

@dataclass
class NewsImpact:
    timestamp: str
    title: str
    impact: str  # 'high', 'medium', 'low'
    pairs: List[str]
    source: str
    confidence: float

@dataclass
class NewsItem:
    timestamp: str
    sentiment: str
    impact_score: float
    summary: str
    source: str
    is_live: bool
    confidence: float
    affected_pairs: List[str] = None

class AdvancedDashboardManager:
    """Production dashboard manager with live OANDA data and trading - FIXED"""
    
    def __init__(self):
        """Initialize dashboard components"""
        self.config = load_config()
        self.last_update = datetime.now()
        self.data_validation_enabled = True
        self.playwright_testing_enabled = True
        # Short TTL cache (seconds)
        self._cache: Dict[str, Any] = {
            'status': (None, 0.0),
            'market': (None, 0.0),
            'news': (None, 0.0)
        }
        self._ttl: Dict[str, float] = {
            'status': 2.0,
            'market': 2.0,
            'news': 10.0
        }
        
        # Initialize multi-account components
        self.account_manager = get_account_manager()
        self.data_feed = get_multi_account_data_feed()
        self.order_manager = get_multi_account_order_manager()
        self.telegram_notifier = get_telegram_notifier()
        
        # Initialize strategies
        self.strategies = {
            'ultra_strict_forex': get_ultra_strict_forex_strategy(),
            'gold_scalping': get_gold_scalping_strategy(),
            'momentum_trading': get_momentum_trading_strategy(),
            'alpha': get_alpha_strategy()
        }
        
        # FORCE LIVE DATA ONLY - No simulated data allowed
        self.use_live_data = True  # Always use live data
        
        # Get active accounts
        self.active_accounts = self.account_manager.get_active_accounts()
        
        # Ensure we have at least one account for live trading
        if not self.active_accounts:
            logger.error("❌ No active OANDA accounts found - cannot proceed without live data")
            raise ValueError("No active OANDA accounts configured - live data required")
        
        # Initialize trading systems with account-specific status
        self.trading_systems = {}
        
        # Map accounts to their strategies - CORRECTED MAPPINGS
        account_strategy_map = {
            os.getenv('PRIMARY_ACCOUNT'): ('gold_scalping', 'Gold Scalping 5M'),  # Account 009
            os.getenv('GOLD_SCALP_ACCOUNT'): ('ultra_strict_forex', 'Ultra Strict Fx 15M'),  # Account 010
            os.getenv('STRATEGY_ALPHA_ACCOUNT'): ('momentum_trading', 'Combined Portfolio')  # Account 011
        }
        
        # Create system status for each active account
        for account_id in self.active_accounts:
            if account_id in account_strategy_map:
                strategy_id, strategy_name = account_strategy_map[account_id]
                
                # Get account info
                account_info = self.account_manager.get_account_status(account_id)
                
                self.trading_systems[account_id] = {
                    'account_id': account_id,
                    'strategy_id': strategy_id,
                    'strategy_name': strategy_name,
                    'status': 'active',
                    'balance': account_info.get('balance', 0),
                    'currency': account_info.get('currency', 'USD'),
                    'unrealized_pl': account_info.get('unrealized_pl', 0),
                    'realized_pl': account_info.get('realized_pl', 0),
                    'margin_used': account_info.get('margin_used', 0),
                    'margin_available': account_info.get('margin_available', 0),
                    'open_trades': account_info.get('open_trades', 0),
                    'open_positions': account_info.get('open_positions', 0),
                    'risk_settings': account_info.get('risk_settings', {}),
                    'instruments': account_info.get('instruments', []),
                    'last_update': datetime.now().isoformat()
                }
        
        # Start live data feed
        self.data_feed.start()
        logger.info("✅ Live data feed started")
        
        # Initialize dashboard
        logger.info("✅ Advanced dashboard initialized")
        logger.info("📊 Live data mode: ENABLED")
        
        # FIXED: Register AI assistant with proper parameters
        if register_ai_assistant:
            try:
                # Store managers in app config for AI assistant access
                app.config['ACCOUNT_MANAGER'] = self.account_manager
                app.config['DATA_FEED'] = self.data_feed
                app.config['ORDER_MANAGER'] = self.order_manager
                app.config['ACTIVE_ACCOUNTS'] = self.active_accounts
                app.config['TELEGRAM_NOTIFIER'] = self.telegram_notifier
                
                # Register AI assistant with both app and socketio
                register_ai_assistant(app, socketio)
                logger.info("✅ AI Assistant registered successfully")
            except Exception as e:
                logger.warning(f"⚠️ AI Assistant registration failed: {e}")
        else:
            logger.info("ℹ️ AI Assistant not available")

    # ----------------------
    # Cache helpers
    # ----------------------
    def _get_cached(self, key: str, builder):
        try:
            now = time.time()
            val, ts = self._cache.get(key, (None, 0.0))
            if val is not None and (now - ts) < self._ttl.get(key, 0):
                return val
            fresh = builder()
            self._cache[key] = (fresh, now)
            return fresh
        except Exception:
            # If cache fails, return builder result directly to avoid masking data
            return builder()
    
    def _invalidate(self, key: str):
        self._cache[key] = (None, 0.0)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        def _build():
            try:
                # Get account statuses
                account_statuses = {}
                for account_id, system_info in self.trading_systems.items():
                    account_status = self.account_manager.get_account_status(account_id)
                    account_statuses[account_id] = account_status
                
                # Get market data
                market_data = {}
                for account_id in self.active_accounts:
                    try:
                        account_data = self.data_feed.get_latest_data(account_id)
                        if account_data:
                            market_data[account_id] = account_data
                    except Exception as e:
                        logger.error(f"❌ Failed to get market data for {account_id}: {e}")
                
                # Get trading metrics
                trading_metrics = self._get_trading_metrics()
                
                # Get news data
                news_data = self._get_news_data()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'system_status': 'online',
                    'live_data_mode': self.use_live_data,
                    'active_accounts': len(self.active_accounts),
                    'account_statuses': account_statuses,
                    'trading_systems': self.trading_systems,
                    'market_data': market_data,
                    'trading_metrics': trading_metrics,
                    'news_data': news_data,
                    'data_feed_status': 'active',
                    'last_update': self.last_update.isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Failed to get system status: {e}")
                return {
                    'timestamp': datetime.now().isoformat(),
                    'system_status': 'error',
                    'error': str(e),
                    'last_update': self.last_update.isoformat()
                }

        try:
            return self._get_cached('status', _build)
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'system_status': 'error',
                'error': str(e),
                'last_update': self.last_update.isoformat()
            }
    
    def _get_trading_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        try:
            # Get metrics from order manager
            metrics = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Aggregate metrics from all accounts
            for account_id in self.active_accounts:
                try:
                    account_metrics = self.order_manager.get_trading_metrics(account_id)
                    if account_metrics:
                        metrics['total_trades'] += account_metrics.get('total_trades', 0)
                        metrics['winning_trades'] += account_metrics.get('winning_trades', 0)
                        metrics['losing_trades'] += account_metrics.get('losing_trades', 0)
                        metrics['total_profit'] += account_metrics.get('total_profit', 0)
                        metrics['total_loss'] += account_metrics.get('total_loss', 0)
                except Exception as e:
                    logger.error(f"❌ Failed to get metrics for {account_id}: {e}")
            
            # Calculate derived metrics
            if metrics['total_trades'] > 0:
                metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
                metrics['profit_factor'] = metrics['total_profit'] / max(metrics['total_loss'], 1)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get trading metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_news_data(self) -> Dict[str, Any]:
        """Get market news and sentiment data"""
        def _build():
            try:
                # Placeholder news structure; real integration elsewhere
                return {
                    'timestamp': datetime.now().isoformat(),
                    'news_items': [],
                    'sentiment_score': 0.0,
                    'market_regime': 'neutral',
                    'high_impact_events': []
                }
            except Exception as e:
                logger.error(f"❌ Failed to get news data: {e}")
                return {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        return self._get_cached('news', _build)
    
    def execute_trading_signals(self) -> Dict[str, Any]:
        """Execute trading signals for all accounts"""
        try:
            results = {}
            
            for account_id, system_info in self.trading_systems.items():
                try:
                    strategy_id = system_info['strategy_id']
                    strategy = self.strategies.get(strategy_id)
                    
                    if not strategy:
                        logger.error(f"❌ Strategy {strategy_id} not found for account {account_id}")
                        continue
                    
                    # Get market data for this account
                    market_data = self.data_feed.get_latest_data(account_id)
                    if not market_data:
                        logger.warning(f"⚠️ No market data available for {account_id}")
                        continue
                    
                    # Generate signals
                    signals = strategy.analyze_market(market_data)
                    
                    if signals:
                        # Execute trades
                        trade_results = self.order_manager.execute_trades(account_id, signals)
                        results[account_id] = {
                            'signals_generated': len(signals),
                            'trades_executed': len(trade_results.get('executed_trades', [])),
                            'trade_results': trade_results
                        }
                        
                        # Send Telegram notification
                        if self.telegram_notifier and trade_results.get('executed_trades'):
                            message = f"🎯 {system_info['strategy_name']}: {len(trade_results['executed_trades'])} trades executed"
                            self.telegram_notifier.send_message(message)
                    else:
                        results[account_id] = {
                            'signals_generated': 0,
                            'trades_executed': 0,
                            'message': 'No signals generated'
                        }
                        
                except Exception as e:
                    logger.error(f"❌ Failed to execute signals for {account_id}: {e}")
                    results[account_id] = {
                        'error': str(e),
                        'signals_generated': 0,
                        'trades_executed': 0
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trading signals: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_account_overview(self) -> Dict[str, Any]:
        """Get comprehensive account overview"""
        try:
            overview = {
                'timestamp': datetime.now().isoformat(),
                'total_accounts': len(self.active_accounts),
                'total_balance': 0.0,
                'total_unrealized_pl': 0.0,
                'total_realized_pl': 0.0,
                'total_margin_used': 0.0,
                'total_open_positions': 0,
                'accounts': {}
            }
            
            for account_id, system_info in self.trading_systems.items():
                account_status = self.account_manager.get_account_status(account_id)
                
                overview['accounts'][account_id] = {
                    'account_name': system_info['strategy_name'],
                    'strategy': system_info['strategy_id'],
                    'balance': account_status.get('balance', 0),
                    'currency': account_status.get('currency', 'USD'),
                    'unrealized_pl': account_status.get('unrealized_pl', 0),
                    'realized_pl': account_status.get('realized_pl', 0),
                    'margin_used': account_status.get('margin_used', 0),
                    'margin_available': account_status.get('margin_available', 0),
                    'open_positions': account_status.get('open_positions', 0),
                    'risk_settings': account_status.get('risk_settings', {}),
                    'instruments': account_status.get('instruments', []),
                    'status': account_status.get('status', 'unknown')
                }
                
                # Aggregate totals
                overview['total_balance'] += account_status.get('balance', 0)
                overview['total_unrealized_pl'] += account_status.get('unrealized_pl', 0)
                overview['total_realized_pl'] += account_status.get('realized_pl', 0)
                overview['total_margin_used'] += account_status.get('margin_used', 0)
                overview['total_open_positions'] += account_status.get('open_positions', 0)
            
            return overview
            
        except Exception as e:
            logger.error(f"❌ Failed to get account overview: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        def _build():
            try:
                market_data = {}
                # Get market data from data feed
                if self.data_feed:
                    for account_id in self.active_accounts:
                        try:
                            account_data = self.data_feed.get_latest_data(account_id)
                            if account_data and 'instruments' in account_data:
                                for instrument, data in account_data['instruments'].items():
                                    market_data[instrument] = {
                                        'bid': data.get('bid', 0),
                                        'ask': data.get('ask', 0),
                                        'spread': data.get('spread', 0),
                                        'timestamp': data.get('timestamp', datetime.now().isoformat()),
                                        'is_live': data.get('is_live', False),
                                        'data_source': data.get('data_source', 'unknown'),
                                        'volatility_score': data.get('volatility_score', 0.0),
                                        'regime': data.get('regime', 'unknown'),
                                        'correlation_risk': data.get('correlation_risk', 0.0)
                                    }
                        except Exception as e:
                            logger.error(f"❌ Failed to get market data for {account_id}: {e}")
                return market_data
            except Exception as e:
                logger.error(f"❌ Failed to get market data: {e}")
                return {}
        try:
            return self._get_cached('market', _build)
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {}
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        try:
            risk_metrics = {
                'timestamp': datetime.now().isoformat(),
                'total_risk': 0.0,
                'risk_percentage': 0.0,
                'exposure_ratio': 0.0,
                'correlation_risk': 0.0,
                'risk_level': 'low',
                'max_risk_exceeded': False,
                'accounts': {}
            }
            
            total_balance = 0.0
            total_margin_used = 0.0
            
            for account_id, system_info in self.trading_systems.items():
                try:
                    account_status = self.account_manager.get_account_status(account_id)
                    balance = account_status.get('balance', 0)
                    margin_used = account_status.get('margin_used', 0)
                    
                    risk_metrics['accounts'][account_id] = {
                        'name': system_info['strategy_name'],
                        'balance': balance,
                        'margin_used': margin_used,
                        'risk_percentage': (margin_used / balance * 100) if balance > 0 else 0,
                        'risk_level': 'high' if margin_used / balance > 0.5 else 'medium' if margin_used / balance > 0.25 else 'low'
                    }
                    
                    total_balance += balance
                    total_margin_used += margin_used
                    
                except Exception as e:
                    logger.error(f"❌ Failed to get risk metrics for {account_id}: {e}")
                    risk_metrics['accounts'][account_id] = {
                        'name': system_info['strategy_name'],
                        'error': str(e)
                    }
            
            # Calculate overall risk metrics
            if total_balance > 0:
                risk_metrics['total_risk'] = total_margin_used / total_balance
                risk_metrics['risk_percentage'] = risk_metrics['total_risk'] * 100
                risk_metrics['exposure_ratio'] = total_margin_used / total_balance
                
                if risk_metrics['total_risk'] > 0.75:
                    risk_metrics['risk_level'] = 'high'
                    risk_metrics['max_risk_exceeded'] = True
                elif risk_metrics['total_risk'] > 0.5:
                    risk_metrics['risk_level'] = 'medium'
                else:
                    risk_metrics['risk_level'] = 'low'
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get risk metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def update_system_status(self):
        """Update system status - async wrapper"""
        try:
            # This method is called by the background thread
            # Just return success for now
            return True
        except Exception as e:
            logger.error(f"❌ System status update error: {e}")
            return False
    
    async def update_market_data(self):
        """Update market data - async wrapper"""
        try:
            # This method is called by the background thread
            # Just return success for now
            return True
        except Exception as e:
            logger.error(f"❌ Market data update error: {e}")
            return False
    
    async def update_news_data(self):
        """Update news data - async wrapper"""
        try:
            # This method is called by the background thread
            # Just return success for now
            return True
        except Exception as e:
            logger.error(f"❌ News data update error: {e}")
            return False
    
    async def update_portfolio_risk(self):
        """Update portfolio risk - async wrapper"""
        try:
            # This method is called by the background thread
            # Just return success for now
            return True
        except Exception as e:
            logger.error(f"❌ Portfolio risk update error: {e}")
            return False

# Global dashboard manager instance
dashboard_manager = AdvancedDashboardManager()

# Flask routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard_advanced.html')

@app.route('/api/status')
def api_status():
    """Get system status"""
    return jsonify(dashboard_manager.get_system_status())

@app.route('/api/overview')
def api_overview():
    """Get account overview"""
    return jsonify(dashboard_manager.get_account_overview())

@app.route('/api/execute_signals', methods=['POST'])
def api_execute_signals():
    """Execute trading signals"""
    try:
        results = dashboard_manager.execute_trading_signals()
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Failed to execute signals: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'live_data_mode': dashboard_manager.use_live_data,
        'active_accounts': len(dashboard_manager.active_accounts)
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("📱 Client connected to dashboard")
    emit('status', {'message': 'Connected to live trading dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("📱 Client disconnected from dashboard")

@socketio.on('request_status')
def handle_status_request():
    """Handle status update request"""
    try:
        status = dashboard_manager.get_system_status()
        emit('status_update', status)
    except Exception as e:
        logger.error(f"❌ Failed to send status update: {e}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    logger.info("🚀 Starting Advanced Trading Dashboard")
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)
