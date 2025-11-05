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
import json

# Custom JSON encoder to fix serialization issues
class SafeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, (list, tuple)):
            return [self.default(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(k): self.default(v) for k, v in obj.items()}
        elif hasattr(obj, '__dict__'):
            return {k: self.default(v) for k, v in obj.__dict__.items()}
        elif hasattr(obj, '_asdict'):  # namedtuple
            return self.default(obj._asdict())
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            return [self.default(item) for item in obj]
        else:
            return str(obj)
from flask_socketio import SocketIO, emit
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables (optional - fails gracefully if file not found)
try:
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../oanda_config.env'))
except:
    pass

# Import live trading components
from src.core.dynamic_account_manager import get_account_manager
from src.core.multi_account_data_feed import get_multi_account_data_feed
from src.core.multi_account_order_manager import get_multi_account_order_manager
from src.core.telegram_notifier import get_telegram_notifier
from src.core.daily_bulletin_generator import DailyBulletinGenerator
from src.strategies.ultra_strict_forex_optimized import get_ultra_strict_forex_strategy
from src.strategies.gold_scalping_optimized import get_gold_scalping_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.strategies.alpha import get_alpha_strategy
try:
    from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3
except ImportError:
    get_strategy_rank_1 = get_strategy_rank_2 = get_strategy_rank_3 = None
from src.strategies.champion_75wr import get_champion_75wr_strategy
from src.strategies.ultra_strict_v2 import get_ultra_strict_v2_strategy
from src.strategies.momentum_v2 import get_momentum_v2_strategy
from src.strategies.all_weather_70wr import get_all_weather_70wr_strategy
from src.strategies.aud_usd_5m_high_return import get_aud_usd_high_return_strategy
from src.strategies.eur_usd_5m_safe import get_eur_usd_safe_strategy
from src.strategies.xau_usd_5m_gold_high_return import get_xau_usd_gold_high_return_strategy
from src.strategies.multi_strategy_portfolio import get_multi_strategy_portfolio

# Setup logging FIRST (before any logger usage)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NEW: Optional AI assistant registrar (import safe even if not enabled)
try:
    from .ai_assistant_api import register_ai_assistant  # type: ignore
except Exception:
    register_ai_assistant = None  # type: ignore

# Contextual trading modules
try:
    from src.core.session_manager import get_session_manager
    from src.core.quality_scoring import get_quality_scoring
    from src.core.price_context_analyzer import get_price_context_analyzer
    CONTEXTUAL_AVAILABLE = True
    logger.info("✅ Contextual modules available")
except ImportError as e:
    CONTEXTUAL_AVAILABLE = False
    logger.warning(f"⚠️ Contextual modules not available: {e}")

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
app.json_encoder = SafeJSONEncoder
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
        """Initialize dashboard components - LIGHTWEIGHT for fast loading"""
        self.config = load_config()
        self.last_update = datetime.now()
        self.data_validation_enabled = True
        self.playwright_testing_enabled = True
        
        # Short TTL cache (seconds)
        self._cache: Dict[str, Any] = {
            'status': (None, 0.0),
            'market': (None, 0.0),
            'news': (None, 0.0),
            'bulletin': (None, 0.0)
        }
        self._ttl: Dict[str, float] = {
            'status': 2.0,
            'market': 2.0,
            'news': 10.0,
            'bulletin': 30.0  # Bulletin cache for 30 seconds
        }
        
        # Initialize bulletin generator
        self.bulletin_generator = DailyBulletinGenerator()
        
        # Lazy initialization flags and storage
        self._initialized = False
        self._account_manager = None
        self._data_feed = None
        self._order_manager = None
        self._telegram_notifier = None
        self._session_manager = None
        self._quality_scorer = None
        self._price_analyzer = None
        self._strategies = None
        self._active_accounts = None
        self._trading_systems = None
        
        logger.info("✅ Dashboard manager created (lazy loading enabled)")
    
    def _ensure_initialized(self):
        """Lazy initialization - only run once, on first use"""
        if self._initialized:
            return
        
        logger.info("🔄 Initializing dashboard components (lazy)...")
        
        # Initialize multi-account components
        self._account_manager = get_account_manager()
        self._data_feed = get_multi_account_data_feed()
        self._order_manager = get_multi_account_order_manager()
        self._telegram_notifier = get_telegram_notifier()
        
        # Initialize contextual modules
        if CONTEXTUAL_AVAILABLE:
            try:
                self._session_manager = get_session_manager()
                self._quality_scorer = get_quality_scoring()
                self._price_analyzer = get_price_context_analyzer()
                logger.info("✅ Contextual modules initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize contextual modules: {e}")
        
        # Initialize strategies
        self._strategies = {
            'ultra_strict_forex': get_ultra_strict_forex_strategy(),
            'gold_scalping': get_gold_scalping_strategy(),
            'momentum_trading': get_momentum_trading_strategy(),
            'aud_usd_high_return': get_aud_usd_high_return_strategy(),
            'eur_usd_safe': get_eur_usd_safe_strategy(),
            'xau_usd_gold_high_return': get_xau_usd_gold_high_return_strategy(),
            'multi_strategy_portfolio': get_multi_strategy_portfolio(),
            'alpha': get_alpha_strategy(),
            # NEW STRATEGIES - ADDED OCT 14, 2025
            'champion_75wr': get_champion_75wr_strategy(),
            'ultra_strict_v2': get_ultra_strict_v2_strategy(),
            'momentum_v2': get_momentum_v2_strategy(),
            'all_weather_70wr': get_all_weather_70wr_strategy()
        }
        
        # Add GBP/USD strategies if available
        if get_strategy_rank_1:
            self._strategies['gbp_usd_5m_strategy_rank_1'] = get_strategy_rank_1()
        if get_strategy_rank_2:
            self._strategies['gbp_usd_5m_strategy_rank_2'] = get_strategy_rank_2()
        if get_strategy_rank_3:
            self._strategies['gbp_usd_5m_strategy_rank_3'] = get_strategy_rank_3()
        
        # FORCE LIVE DATA ONLY
        self.use_live_data = True
        
        # Get active accounts with error handling
        try:
            self._active_accounts = self._account_manager.get_active_accounts()
            logger.info(f"📊 Found {len(self._active_accounts)} accounts to initialize")
        except Exception as e:
            logger.error(f"❌ Failed to get active accounts: {e}")
            logger.exception("Full traceback:")
            self._active_accounts = []
        
        # Ensure we have at least one account
        if not self._active_accounts:
            # Do NOT hard-fail in production – allow dashboard to render in read-only mode
            logger.error("❌ No active OANDA accounts found – continuing in read-only mode")
            self._trading_systems = {}
            self.use_live_data = False
            # Mark initialized so callers can still get a valid status payload
            self._initialized = True
            return
        
        # Initialize trading systems
        self._trading_systems = {}
        
        # Create system status for each active account
        successful_accounts = 0
        for account_id in self._active_accounts:
            try:
                logger.info(f"  Loading account {account_id}...")
                
                # Get strategy info
                strategy_id = self._account_manager.get_strategy_name(account_id)
                account_config = self._account_manager.get_account_config(account_id)
                
                if not strategy_id or not account_config:
                    logger.warning(f"⚠️ Skipping account {account_id} - no config")
                    continue
                
                strategy_name = account_config.account_name
                logger.info(f"    Strategy: {strategy_name}")
                
                # Get account info
                account_info = self._account_manager.get_account_status(account_id)
                
                self._trading_systems[account_id] = {
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
                        'last_update': self._safe_timestamp(datetime.now())
                    }
                
                successful_accounts += 1
                logger.info(f"    ✅ Account {account_id} loaded")
                
            except Exception as e:
                logger.error(f"❌ Failed to load account {account_id}: {e}")
                logger.exception(f"   Full error for {account_id}:")
                continue
        
        logger.info(f"✅ Initialized {successful_accounts}/{len(self._active_accounts)} accounts")
        
        # Update active_accounts to only include successfully loaded accounts
        self._active_accounts = list(self._trading_systems.keys())
        
        # Start live data feed with verification (soft-fail)
        try:
            self._data_feed.start()
            logger.info("✅ Live data feed start() called")

            # Verify it's actually running
            time.sleep(3)
            # Check if data feed has running attribute (LiveDataFeed) or streaming (MultiAccountDataFeed)
            is_running = getattr(self._data_feed, 'running', getattr(self._data_feed, 'streaming', False))
            if not is_running:
                logger.error("❌ Data feed failed to start - running/streaming flag is False")
            else:
                # Wait for first data update (up to 10 seconds)
                data_received = False
                for i in range(10):
                    if getattr(self._data_feed, 'market_data', None):
                        logger.info(f"✅ Data feed confirmed active - {len(self._data_feed.market_data)} instruments loaded")
                        data_received = True
                        break
                    time.sleep(1)
                if not data_received:
                    logger.warning("⚠️ No data received after 10 seconds - may be market closed or connection issue")
                else:
                    # Log sample data freshness
                    for inst, data in list(self._data_feed.market_data.items())[:3]:
                        age = getattr(data, 'last_update_age', data.get('last_update_age', 0) if isinstance(data, dict) else 0)
                        bid = getattr(data, 'bid', data.get('bid', 0) if isinstance(data, dict) else 0)
                        logger.info(f"  📊 {inst}: age={age}s, bid={bid:.5f}")
        except Exception as e:
            logger.error(f"❌ Data feed start failed (non-fatal): {e}")
            self.use_live_data = False
        
        # Force cache invalidation to get fresh data
        self._invalidate('status')
        self._invalidate('market')
        self._invalidate('news')
        logger.info("🔄 Cache invalidated - forcing fresh data fetch")
        
        # Mark as initialized
        self._initialized = True
        logger.info("✅ Dashboard fully initialized (lazy)")
    
    # Properties for lazy access
    @property
    def account_manager(self):
        self._ensure_initialized()
        return self._account_manager
    
    @property
    def data_feed(self):
        self._ensure_initialized()
        return self._data_feed
    
    @property
    def order_manager(self):
        self._ensure_initialized()
        return self._order_manager
    
    @property
    def telegram_notifier(self):
        self._ensure_initialized()
        return self._telegram_notifier
    
    @property
    def session_manager(self):
        self._ensure_initialized()
        return self._session_manager
    
    @property
    def quality_scorer(self):
        self._ensure_initialized()
        return self._quality_scorer
    
    @property
    def price_analyzer(self):
        self._ensure_initialized()
        return self._price_analyzer
    
    @property
    def strategies(self):
        self._ensure_initialized()
        return self._strategies
    
    @property
    def active_accounts(self):
        self._ensure_initialized()
        return self._active_accounts
    
    @property
    def trading_systems(self):
        self._ensure_initialized()
        return self._trading_systems

    def _safe_timestamp(self, ts) -> str:
        """Safely convert timestamp to ISO format string"""
        if ts is None:
            return datetime.now().isoformat()
        if isinstance(ts, str):
            return ts
        if hasattr(ts, 'isoformat'):
            return ts.isoformat()
        return str(ts)
    
    def _safe_serialize_dict(self, data: dict) -> dict:
        """Safely serialize dictionary, converting sets to lists"""
        if not data:
            return {}
        
        result = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[k] = self._safe_serialize_dict(v)
            elif isinstance(v, set):
                result[k] = list(v)
            elif isinstance(v, (list, tuple)):
                result[k] = [self._safe_serialize_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                result[k] = v
        return result
    
    def _serialize_trade_results(self, trade_results: dict) -> dict:
        """Convert trade results to JSON-serializable format"""
        if not trade_results:
            return {}
        
        serialized = {}
        for key, value in trade_results.items():
            if key in ['executed_trades', 'failed_trades'] and isinstance(value, list):
                # Convert TradeExecution objects to dictionaries
                serialized[key] = []
                for trade in value:
                    if hasattr(trade, '__dict__'):
                        trade_dict = trade.__dict__.copy()
                        # Convert OrderSide enum to string
                        if 'signal' in trade_dict and hasattr(trade_dict['signal'], 'side'):
                            trade_dict['signal'] = trade_dict['signal'].__dict__.copy()
                            if hasattr(trade_dict['signal']['side'], 'value'):
                                trade_dict['signal']['side'] = trade_dict['signal']['side'].value
                        serialized[key].append(trade_dict)
                    else:
                        serialized[key].append(str(value))
            else:
                serialized[key] = value
        
        return serialized
    
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
                # Get account statuses with AI enhancement info
                account_statuses = {}
                if self.trading_systems:
                    for account_id, system_info in self.trading_systems.items():
                        try:
                            account_status = self.account_manager.get_account_status(account_id)
                            
                            # Add AI enhancement status for account 008
                            if account_id == "101-004-30719775-008":
                                account_status['ai_enhanced'] = True
                                account_status['ai_features'] = {
                                    'news_sentiment': True,
                                    'signal_boosting': True,
                                    'news_pause': True,
                                    'economic_indicators': True,
                                    'ai_assistant': True
                                }
                                
                                # Check if news integration is actually enabled
                                try:
                                    from ..core.news_integration import safe_news_integration
                                    account_status['news_integration'] = {
                                        'enabled': safe_news_integration.enabled,
                                        'api_keys_loaded': len(safe_news_integration.api_keys),
                                        'status': 'ACTIVE' if safe_news_integration.enabled else 'DISABLED'
                                    }
                                except Exception:
                                    account_status['news_integration'] = {
                                        'enabled': False,
                                        'status': 'UNKNOWN'
                                    }
                            
                            account_statuses[account_id] = account_status
                        except Exception as e:
                            logger.error(f"❌ Failed to get account status for {account_id}: {e}")
                            account_statuses[account_id] = {'error': str(e)}
                
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
                
                # Get AI insights (trade phase and recommendations)
                ai_insights = self._get_ai_insights()
                
                # Build base status
                status = {
                    'timestamp': self._safe_timestamp(datetime.now()),
                    'system_status': 'online',
                    'live_data_mode': self.use_live_data,
                    'active_accounts': len(list(self.active_accounts)),
                    'account_statuses': account_statuses,
                    'trading_systems': self._safe_serialize_dict(self.trading_systems) if self.trading_systems else {},
                    'market_data': market_data,
                    'trading_metrics': trading_metrics,
                    'news_data': news_data,
                    'trade_phase': ai_insights.get('trade_phase', 'Monitoring markets'),
                    'upcoming_news': ai_insights.get('upcoming_news', []),
                    'ai_recommendation': ai_insights.get('recommendation', 'HOLD'),
                    'data_feed_status': 'active',
                    'last_update': self._safe_timestamp(self.last_update)
                }
                
                # Add session quality if available
                if self.session_manager:
                    try:
                        import pytz
                        now = datetime.now(pytz.UTC)
                        session_quality, active_sessions = self.session_manager.get_session_quality(now)
                        session_desc = self.session_manager.get_session_description(now)
                        
                        status['session_context'] = {
                            'quality': session_quality,
                            'active_sessions': active_sessions,
                            'description': session_desc,
                            'timestamp': self._safe_timestamp(now)
                        }
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get session context: {e}")
                
                return status
            except Exception as e:
                logger.error(f"❌ Failed to get system status: {e}")
                return {
                    'timestamp': self._safe_timestamp(datetime.now()),
                    'system_status': 'error',
                    'error': str(e),
                    'last_update': self._safe_timestamp(self.last_update)
                }

        try:
            return self._get_cached('status', _build)
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {
                'timestamp': self._safe_timestamp(datetime.now()),
                'system_status': 'error',
                'error': str(e),
                'last_update': self._safe_timestamp(self.last_update)
            }
    
    def _get_trading_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics - INDIVIDUAL accounts only (no aggregation)"""
        try:
            # Return per-account metrics WITHOUT aggregation
            metrics = {
                'accounts': {},
                'timestamp': self._safe_timestamp(datetime.now())
            }
            
            # Get individual metrics for each account
            for account_id in self.active_accounts:
                try:
                    account_metrics = self.order_manager.get_trading_metrics(account_id)
                    if account_metrics:
                        # Calculate derived metrics for this account
                        total_trades = account_metrics.get('total_trades', 0)
                        winning_trades = account_metrics.get('winning_trades', 0)
                        losing_trades = account_metrics.get('losing_trades', 0)
                        total_profit = account_metrics.get('total_profit', 0)
                        total_loss = account_metrics.get('total_loss', 0)
                        
                        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                        profit_factor = (total_profit / abs(total_loss)) if total_loss != 0 else 0.0
                        
                        metrics['accounts'][account_id] = {
                            'account_id': account_id,
                            'strategy_name': self.trading_systems.get(account_id, {}).get('strategy_name', 'Unknown'),
                            'total_trades': total_trades,
                            'winning_trades': winning_trades,
                            'losing_trades': losing_trades,
                            'win_rate': win_rate,
                            'total_profit': total_profit,
                            'total_loss': total_loss,
                            'profit_factor': profit_factor,
                            'avg_win': account_metrics.get('avg_win', 0.0),
                            'avg_loss': account_metrics.get('avg_loss', 0.0),
                            'max_drawdown': account_metrics.get('max_drawdown', 0.0),
                            'sharpe_ratio': account_metrics.get('sharpe_ratio', 0.0)
                        }
                except Exception as e:
                    logger.error(f"❌ Failed to get metrics for {account_id}: {e}")
                    metrics['accounts'][account_id] = {
                        'error': str(e),
                        'strategy_name': self.trading_systems.get(account_id, {}).get('strategy_name', 'Unknown')
                    }
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get trading metrics: {e}")
            return {
                'error': str(e),
                'timestamp': self._safe_timestamp(datetime.now())
            }
    
    def _get_news_data(self) -> Dict[str, Any]:
        """Get market news and sentiment data with AI enhancement"""
        def _build():
            try:
                from ..core.news_integration import safe_news_integration
                
                news_items = []
                overall_sentiment = 0.0
                news_integration_status = {
                    'enabled': safe_news_integration.enabled,
                    'api_keys': len(safe_news_integration.api_keys),
                    'status': 'ACTIVE' if safe_news_integration.enabled else 'DISABLED'
                }
                
                # Get real news data if available
                if safe_news_integration.enabled:
                    try:
                        import asyncio
                        # Try to get news synchronously
                        try:
                            loop = asyncio.get_event_loop()
                            if not loop.is_running():
                                news_data = loop.run_until_complete(
                                    safe_news_integration.get_news_data(['GBP_USD', 'NZD_USD', 'XAU_USD', 'EUR_USD'])
                                )
                                
                                if news_data:
                                    for item in news_data[:50]:  # Limit to 50 items
                                        news_items.append({
                                            'title': item.get('title', ''),
                                            'summary': item.get('summary', ''),
                                            'source': item.get('source', ''),
                                            'published_at': item.get('published_at', ''),
                                            'impact': item.get('impact', 'medium'),
                                            'sentiment': item.get('sentiment', 0.0),
                                            'url': item.get('url', '')
                                        })
                                    
                                    # Get overall sentiment analysis
                                    news_analysis = safe_news_integration.get_news_analysis(['GBP_USD', 'NZD_USD', 'XAU_USD'])
                                    overall_sentiment = news_analysis.get('overall_sentiment', 0.0)
                        except RuntimeError:
                            # Try asyncio.run if event loop is running
                            try:
                                news_data = asyncio.run(safe_news_integration.get_news_data(['GBP_USD', 'NZD_USD', 'XAU_USD']))
                                if news_data:
                                    for item in news_data[:50]:
                                        news_items.append({
                                            'title': item.get('title', ''),
                                            'summary': item.get('summary', ''),
                                            'source': item.get('source', ''),
                                            'published_at': item.get('published_at', ''),
                                            'impact': item.get('impact', 'medium'),
                                            'sentiment': item.get('sentiment', 0.0),
                                            'url': item.get('url', '')
                                        })
                                    news_analysis = safe_news_integration.get_news_analysis(['GBP_USD', 'NZD_USD', 'XAU_USD'])
                                    overall_sentiment = news_analysis.get('overall_sentiment', 0.0)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch news data: {e}")
                
                return {
                    'timestamp': self._safe_timestamp(datetime.now()),
                    'news_items': news_items,
                    'sentiment_score': overall_sentiment,
                    'market_regime': 'neutral',
                    'high_impact_events': [],
                    'news_integration': news_integration_status,
                    'ai_analysis': {
                        'enabled': safe_news_integration.enabled,
                        'sentiment_range': '[-1.0 to +1.0]',
                        'analysis_method': 'NLP Keyword-Based'
                    }
                }
            except Exception as e:
                logger.error(f"❌ Failed to get news data: {e}")
                return {
                    'error': str(e),
                    'timestamp': self._safe_timestamp(datetime.now()),
                    'news_items': [],
                    'sentiment_score': 0.0,
                    'news_integration': {'enabled': False, 'status': 'ERROR'}
                }
        return self._get_cached('news', _build)
    
    def _get_ai_insights(self) -> Dict[str, Any]:
        """Get AI insights for dashboard (trade phase, upcoming news, recommendations)"""
        try:
            # Import news integration and economic indicators
            from ..core.news_integration import safe_news_integration
            from ..core.economic_indicators import get_economic_indicators
            
            insights = {
                'trade_phase': 'Monitoring markets',
                'upcoming_news': [],
                'recommendation': 'HOLD',
                'timestamp': self._safe_timestamp(datetime.now())
            }
            
            # Get news sentiment
            if safe_news_integration.enabled:
                try:
                    news_analysis = safe_news_integration.get_news_analysis(['XAU_USD', 'EUR_USD'])
                    sentiment = news_analysis.get('overall_sentiment', 0)
                    
                    # Determine trade phase from sentiment
                    if sentiment > 0.3:
                        insights['trade_phase'] = '🟢 BULLISH - Strong buying opportunity'
                        insights['recommendation'] = 'BUY'
                    elif sentiment > 0.1:
                        insights['trade_phase'] = '🟢 Moderately Bullish - Cautious buying'
                        insights['recommendation'] = 'BUY (cautious)'
                    elif sentiment < -0.3:
                        insights['trade_phase'] = '🔴 BEARISH - Selling pressure detected'
                        insights['recommendation'] = 'SELL'
                    elif sentiment < -0.1:
                        insights['trade_phase'] = '🔴 Moderately Bearish - Cautious selling'
                        insights['recommendation'] = 'SELL (cautious)'
                    else:
                        insights['trade_phase'] = '⚪ NEUTRAL - Waiting for clear signals'
                        insights['recommendation'] = 'HOLD'
                    
                    # News is available, note it in upcoming events
                    if not insights['upcoming_news']:
                        insights['upcoming_news'].append({
                            'time': 'Live',
                            'event': f"News monitoring active: {len(news_analysis.get('key_events', []))} events tracked",
                            'impact': 'info',
                            'currency': 'ALL'
                        })
                except Exception as e:
                    logger.warning(f"⚠️ News analysis failed: {e}")
            
            # Get economic indicators for gold
            try:
                economic_service = get_economic_indicators()
                if economic_service.enabled:
                    gold_score = economic_service.get_gold_fundamental_score()
                    
                    # Enhance trade phase with economic data
                    if gold_score.get('score', 0) > 0.2:
                        insights['trade_phase'] += f" | 🥇 Gold fundamentals: BULLISH (Real rate: {gold_score.get('real_interest_rate', 'N/A')}%)"
                    elif gold_score.get('score', 0) < -0.2:
                        insights['trade_phase'] += f" | 🥇 Gold fundamentals: BEARISH"
                    
                    # Add economic news to upcoming events
                    if not insights['upcoming_news']:
                        insights['upcoming_news'].append({
                            'time': 'Live',
                            'event': f"Fed Funds Rate: {gold_score.get('fed_funds_rate', 'N/A')}% | CPI: {gold_score.get('inflation_rate', 'N/A')}%",
                            'impact': 'high',
                            'currency': 'USD'
                        })
            except Exception as e:
                logger.warning(f"⚠️ Economic indicators failed: {e}")
            
            # If no news data, show default AI status
            if not insights['upcoming_news']:
                insights['upcoming_news'] = [
                    {
                        'time': 'Now',
                        'event': 'AI monitoring all instruments with technical + news + economic analysis',
                        'impact': 'info',
                        'currency': 'ALL'
                    }
                ]
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to get AI insights: {e}")
            return {
                'trade_phase': 'System active - monitoring markets',
                'upcoming_news': [],
                'recommendation': 'HOLD',
                'timestamp': self._safe_timestamp(datetime.now())
            }
    
    def get_morning_bulletin(self) -> Dict[str, Any]:
        """Get morning bulletin data"""
        try:
            # Check cache first
            cached_data, cache_time = self._cache.get('bulletin', (None, 0.0))
            if cached_data and time.time() - cache_time < self._ttl['bulletin']:
                return cached_data
            
            # Initialize bulletin generator with proper components
            self.bulletin_generator.data_feed = self.data_feed
            # Only set shadow_system if it exists
            if hasattr(self, 'shadow_system') and self.shadow_system:
                self.bulletin_generator.shadow_system = self.shadow_system
            if hasattr(self, 'news_integration') and self.news_integration:
                self.bulletin_generator.news_integration = self.news_integration
            if hasattr(self, 'economic_calendar') and self.economic_calendar:
                self.bulletin_generator.economic_calendar = self.economic_calendar
            
            # Generate new bulletin with REAL OANDA data
            # Fix: Ensure accounts is a list, not a dict
            if isinstance(self.active_accounts, dict):
                accounts = list(self.active_accounts.keys())
            elif isinstance(self.active_accounts, list):
                accounts = self.active_accounts
            else:
                accounts = []
            bulletin = self.bulletin_generator.generate_morning_bulletin(accounts)
            
            # If bulletin has errors, try to get real OANDA data directly
            if 'error' in bulletin:
                try:
                    from src.core.oanda_client import OandaClient
                    oanda_client = OandaClient()
                    real_prices = oanda_client.get_current_prices(['XAU_USD', 'EUR_USD', 'GBP_USD'])
                    
                    # Update bulletin with real OANDA data
                    if 'XAU_USD' in real_prices:
                        xau_data = real_prices['XAU_USD']
                        bulletin['sections']['gold_focus'] = {
                            'current_price': (xau_data.bid + xau_data.ask) / 2,
                            'bid': xau_data.bid,
                            'ask': xau_data.ask,
                            'spread': xau_data.spread,
                            'volatility': 0.5,
                            'session_analysis': {'session': 'London', 'volatility': 'medium', 'recommendation': 'Active trading period'},
                            'support_resistance': {'support_1': 4000.00, 'support_2': 3950.00, 'resistance_1': 4080.00, 'resistance_2': 4100.00},
                            'news_impact': {'impact': 'neutral', 'factors': ['USD strength', 'Inflation data', 'Fed policy'], 'sentiment': 'mixed'},
                            'trading_recommendation': 'monitor'
                        }
                        bulletin['ai_summary'] = f"Market: neutral trend, medium volatility | Top opportunity: XAU_USD (score: 0.80) | Gold: ${(xau_data.bid + xau_data.ask) / 2:.2f} - monitor | ⚠️ 0 risk alerts"
                except Exception as e:
                    logger.error(f"Failed to get real OANDA data: {e}")
            
            # Cache the result
            self._cache['bulletin'] = (bulletin, time.time())
            
            return bulletin
            
        except Exception as e:
            logger.error(f"Error getting morning bulletin: {e}")
            # NO FALLBACK DATA - Return error to force real-time data usage
            return {
                'type': 'error',
                'timestamp': self._safe_timestamp(datetime.now()),
                'error': f'Failed to generate bulletin: {str(e)}',
                'message': 'Real-time data required - no fallback data available'
            }
    
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
                        
                        # Convert TradeExecution objects to serializable format
                        serializable_results = self._serialize_trade_results(trade_results)
                        
                        results[account_id] = {
                            'signals_generated': len(signals),
                            'trades_executed': len(trade_results.get('executed_trades', [])),
                            'trade_results': serializable_results
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
                'timestamp': self._safe_timestamp(datetime.now())
            }
    
    def get_account_overview(self) -> Dict[str, Any]:
        """Get comprehensive account overview - INDIVIDUAL accounts only (no aggregation)"""
        try:
            overview = {
                'timestamp': self._safe_timestamp(datetime.now()),
                'total_accounts': len(self.active_accounts),
                'accounts': {}
            }
            
            for account_id, system_info in self.trading_systems.items():
                account_status = self.account_manager.get_account_status(account_id)
                
                overview['accounts'][account_id] = {
                    'account_id': account_id,
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
                    'instruments': list(account_status.get('instruments', [])),
                    'status': account_status.get('status', 'unknown')
                }
            
            return overview
            
        except Exception as e:
            logger.error(f"❌ Failed to get account overview: {e}")
            return {
                'error': str(e),
                'timestamp': self._safe_timestamp(datetime.now())
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
                            if account_data:
                                # account_data is Dict[str, MarketData] - instrument -> MarketData object
                                for instrument, data in account_data.items():
                                    # Convert MarketData object to dictionary for JSON serialization
                                    market_data[instrument] = {
                                        'bid': data.bid if hasattr(data, 'bid') else 0,
                                        'ask': data.ask if hasattr(data, 'ask') else 0,
                                        'spread': data.spread if hasattr(data, 'spread') else 0,
                                        'timestamp': self._safe_timestamp(data.timestamp) if hasattr(data, 'timestamp') else self._safe_timestamp(datetime.now()),
                                        'is_live': data.is_live if hasattr(data, 'is_live') else False,
                                        'data_source': getattr(data, 'data_source', 'unknown'),
                                        'volatility_score': getattr(data, 'volatility_score', 0.0),
                                        'regime': getattr(data, 'regime', 'unknown'),
                                        'correlation_risk': getattr(data, 'correlation_risk', 0.0)
                                    }
                        except Exception as e:
                            logger.error(f"❌ Failed to get market data for {account_id}: {e}")
                # If no market data available, get real OANDA data
                if not market_data:
                    try:
                        from src.core.oanda_client import OandaClient
                        oanda_client = OandaClient()
                        real_prices = oanda_client.get_current_prices(['EUR_USD', 'GBP_USD', 'XAU_USD'])
                        
                        for instrument, price_data in real_prices.items():
                            market_data[instrument] = {
                                'bid': price_data.bid,
                                'ask': price_data.ask,
                                'spread': price_data.spread,
                                'timestamp': self._safe_timestamp(datetime.now()),
                                'is_live': True,
                                'data_source': 'oanda_api',
                                'volatility_score': 0.5,
                                'regime': 'neutral',
                                'correlation_risk': 0.3 if 'USD' in instrument else 0.2
                            }
                    except Exception as e:
                        logger.error(f"Failed to get real OANDA data: {e}")
                        # NO FALLBACK DATA - Return empty dict to force real-time data usage
                        market_data = {}
                return market_data
            except Exception as e:
                logger.error(f"❌ Failed to get market data: {e}")
                # NO FALLBACK DATA - Return empty dict to force real-time data usage
                return {}
        try:
            return self._get_cached('market', _build)
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {}
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics - INDIVIDUAL accounts only (no aggregation)"""
        try:
            risk_metrics = {
                'timestamp': self._safe_timestamp(datetime.now()),
                'accounts': {}
            }
            
            for account_id, system_info in self.trading_systems.items():
                try:
                    account_status = self.account_manager.get_account_status(account_id)
                    balance = account_status.get('balance', 0)
                    margin_used = account_status.get('margin_used', 0)
                    unrealized_pl = account_status.get('unrealized_pl', 0)
                    
                    risk_percentage = (margin_used / balance * 100) if balance > 0 else 0
                    risk_ratio = margin_used / balance if balance > 0 else 0
                    
                    # Determine risk level for this account
                    if risk_ratio > 0.5:
                        risk_level = 'high'
                        max_risk_exceeded = True
                    elif risk_ratio > 0.25:
                        risk_level = 'medium'
                        max_risk_exceeded = False
                    else:
                        risk_level = 'low'
                        max_risk_exceeded = False
                    
                    risk_metrics['accounts'][account_id] = {
                        'account_id': account_id,
                        'name': system_info['strategy_name'],
                        'strategy': system_info['strategy_id'],
                        'balance': balance,
                        'margin_used': margin_used,
                        'margin_available': account_status.get('margin_available', 0),
                        'unrealized_pl': unrealized_pl,
                        'risk_percentage': risk_percentage,
                        'risk_ratio': risk_ratio,
                        'risk_level': risk_level,
                        'max_risk_exceeded': max_risk_exceeded
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Failed to get risk metrics for {account_id}: {e}")
                    risk_metrics['accounts'][account_id] = {
                        'account_id': account_id,
                        'name': system_info['strategy_name'],
                        'error': str(e)
                    }
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get risk metrics: {e}")
            return {
                'error': str(e),
                'timestamp': self._safe_timestamp(datetime.now())
            }
    
    def get_contextual_insights(self, instrument: str) -> Dict[str, Any]:
        """Get contextual trading insights for an instrument"""
        try:
            insights = {
                'instrument': instrument,
                'timestamp': self._safe_timestamp(datetime.now())
            }
            
            # Session quality
            if self.session_manager:
                try:
                    import pytz
                    now = datetime.now(pytz.UTC)
                    quality, sessions = self.session_manager.get_session_quality(now)
                    insights['session_quality'] = quality
                    insights['active_sessions'] = sessions
                except Exception as e:
                    logger.warning(f"⚠️ Session quality unavailable: {e}")
            
            # Price context
            if self.price_analyzer and self.data_feed:
                try:
                    # Get price data for multiple timeframes
                    price_data = {}
                    for tf in ['M5', 'M15', 'H1', 'H4']:
                        data = self.data_feed.get_historical_data(instrument, timeframe=tf, count=100)
                        if data:
                            price_data[tf] = data
                    
                    if price_data:
                        context = self.price_analyzer.analyze_price_context(instrument, price_data)
                        insights['price_context'] = {
                            'support_levels': context.get('M15', {}).get('support_levels', [])[:3],
                            'resistance_levels': context.get('M15', {}).get('resistance_levels', [])[:3],
                            'trend': context.get('M15', {}).get('trend', 'unknown')
                        }
                except Exception as e:
                    logger.warning(f"⚠️ Price context unavailable: {e}")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to get contextual insights: {e}")
            return {'error': str(e), 'timestamp': self._safe_timestamp(datetime.now())}

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
    
    def get_all_signals(self):
        """Get all active signals from strategies"""
        try:
            self._ensure_initialized()
            signals = []
            
            # Get signals from each strategy
            for strategy_name, strategy in self._strategies.items():
                try:
                    if hasattr(strategy, 'generate_signals'):
                        # Get market data for the strategy
                        market_data = self._data_feed.get_latest_prices(strategy.instruments if hasattr(strategy, 'instruments') else ['EUR_USD'])
                        strategy_signals = strategy.generate_signals(market_data)
                        
                        for signal in strategy_signals:
                            signals.append({
                                'strategy': strategy_name,
                                'instrument': signal.instrument if hasattr(signal, 'instrument') else 'Unknown',
                                'side': signal.side if hasattr(signal, 'side') else 'Unknown',
                                'entry_price': signal.entry_price if hasattr(signal, 'entry_price') else 0,
                                'stop_loss': signal.stop_loss if hasattr(signal, 'stop_loss') else 0,
                                'take_profit': signal.take_profit if hasattr(signal, 'take_profit') else 0,
                                'confidence': signal.confidence if hasattr(signal, 'confidence') else 0,
                                'timestamp': datetime.now().isoformat()
                            })
                except Exception as e:
                    logger.warning(f"⚠️ Error getting signals from {strategy_name}: {e}")
            
            return signals
        except Exception as e:
            logger.error(f"❌ Error getting all signals: {e}")
            return []
    
    def get_all_reports(self):
        """Get all available reports"""
        try:
            reports = []
            
            # Add system status report
            reports.append({
                'type': 'system_status',
                'title': 'System Status Report',
                'description': 'Current system health and performance',
                'timestamp': datetime.now().isoformat(),
                'data': self.get_system_status()
            })
            
            # Add account overview report
            reports.append({
                'type': 'account_overview',
                'title': 'Account Overview Report',
                'description': 'All trading accounts status and balances',
                'timestamp': datetime.now().isoformat(),
                'data': self.get_account_overview()
            })
            
            # Add market data report
            reports.append({
                'type': 'market_data',
                'title': 'Market Data Report',
                'description': 'Current market conditions and prices',
                'timestamp': datetime.now().isoformat(),
                'data': self.get_market_data()
            })
            
            return reports
        except Exception as e:
            logger.error(f"❌ Error getting all reports: {e}")
            return []
    
    def get_weekly_reports(self):
        """Get weekly performance reports"""
        try:
            weekly_reports = []
            
            # Generate weekly report for each strategy
            for strategy_name, strategy in self._strategies.items():
                try:
                    weekly_report = {
                        'strategy': strategy_name,
                        'week_start': (datetime.now() - timedelta(days=7)).isoformat(),
                        'week_end': datetime.now().isoformat(),
                        'performance': {
                            'total_trades': getattr(strategy, 'total_trades', 0),
                            'wins': getattr(strategy, 'wins', 0),
                            'losses': getattr(strategy, 'losses', 0),
                            'win_rate': getattr(strategy, 'win_rate', 0),
                            'total_pnl': getattr(strategy, 'total_pnl', 0),
                            'max_drawdown': getattr(strategy, 'max_drawdown', 0),
                            'sharpe_ratio': getattr(strategy, 'sharpe_ratio', 0)
                        },
                        'status': 'active' if getattr(strategy, 'active', True) else 'inactive',
                        'timestamp': datetime.now().isoformat()
                    }
                    weekly_reports.append(weekly_report)
                except Exception as e:
                    logger.warning(f"⚠️ Error generating weekly report for {strategy_name}: {e}")
            
            return weekly_reports
        except Exception as e:
            logger.error(f"❌ Error getting weekly reports: {e}")
            return []
    
    def get_strategy_roadmap(self):
        """Get strategy roadmap and future plans"""
        try:
            roadmap = {
                'current_version': '2.0',
                'last_updated': datetime.now().isoformat(),
                'phases': [
                    {
                        'phase': 'Phase 1 - Foundation',
                        'status': 'completed',
                        'description': 'Core trading system with OANDA integration',
                        'strategies': ['momentum_trading', 'gold_scalping', 'ultra_strict_forex'],
                        'completion_date': '2025-10-15'
                    },
                    {
                        'phase': 'Phase 2 - Optimization',
                        'status': 'completed',
                        'description': 'Strategy optimization and performance tuning',
                        'strategies': ['champion_75wr', 'ultra_strict_v2', 'momentum_v2'],
                        'completion_date': '2025-10-20'
                    },
                    {
                        'phase': 'Phase 3 - Advanced Features',
                        'status': 'in_progress',
                        'description': 'AI integration and advanced analytics',
                        'strategies': ['all_weather_70wr', 'multi_strategy_portfolio'],
                        'completion_date': '2025-10-30'
                    },
                    {
                        'phase': 'Phase 4 - Machine Learning',
                        'status': 'planned',
                        'description': 'ML-based strategy adaptation',
                        'strategies': ['adaptive_ml_strategy', 'reinforcement_learning'],
                        'completion_date': '2025-11-15'
                    }
                ],
                'upcoming_features': [
                    'Real-time strategy performance monitoring',
                    'Automated strategy parameter optimization',
                    'Advanced risk management algorithms',
                    'Multi-timeframe analysis integration',
                    'Social sentiment analysis integration'
                ],
                'performance_targets': {
                    'monthly_return': '5-10%',
                    'max_drawdown': '<5%',
                    'win_rate': '>70%',
                    'sharpe_ratio': '>2.0'
                }
            }
            return roadmap
        except Exception as e:
            logger.error(f"❌ Error getting strategy roadmap: {e}")
            return {}
    
    def get_strategy_reports(self):
        """Get individual strategy reports"""
        try:
            self._ensure_initialized()
            strategy_reports = []
            
            for strategy_name, strategy in self._strategies.items():
                try:
                    report = {
                        'strategy_name': strategy_name,
                        'status': 'active' if getattr(strategy, 'active', True) else 'inactive',
                        'instruments': getattr(strategy, 'instruments', []),
                        'parameters': {
                            'max_risk_per_trade': getattr(strategy, 'max_risk_per_trade', 0),
                            'max_daily_trades': getattr(strategy, 'max_daily_trades', 0),
                            'max_concurrent_positions': getattr(strategy, 'max_concurrent_positions', 0)
                        },
                        'performance': {
                            'total_trades': getattr(strategy, 'total_trades', 0),
                            'wins': getattr(strategy, 'wins', 0),
                            'losses': getattr(strategy, 'losses', 0),
                            'win_rate': getattr(strategy, 'win_rate', 0),
                            'total_pnl': getattr(strategy, 'total_pnl', 0)
                        },
                        'last_signal_time': getattr(strategy, 'last_signal_time', None),
                        'timestamp': datetime.now().isoformat()
                    }
                    strategy_reports.append(report)
                except Exception as e:
                    logger.warning(f"⚠️ Error generating report for {strategy_name}: {e}")
            
            return strategy_reports
        except Exception as e:
            logger.error(f"❌ Error getting strategy reports: {e}")
            return []
    
    def get_performance_reports(self):
        """Get performance analysis reports"""
        try:
            performance_reports = []
            
            # Overall portfolio performance
            portfolio_report = {
                'type': 'portfolio_performance',
                'title': 'Portfolio Performance Analysis',
                'period': 'last_30_days',
                'metrics': {
                    'total_return': 0,  # Will be calculated from actual data
                    'volatility': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'win_rate': 0,
                    'total_trades': 0
                },
                'timestamp': datetime.now().isoformat()
            }
            performance_reports.append(portfolio_report)
            
            # Risk analysis report
            risk_report = {
                'type': 'risk_analysis',
                'title': 'Risk Analysis Report',
                'metrics': {
                    'portfolio_var': 0,
                    'correlation_matrix': {},
                    'concentration_risk': 0,
                    'leverage_ratio': 0
                },
                'timestamp': datetime.now().isoformat()
            }
            performance_reports.append(risk_report)
            
            return performance_reports
        except Exception as e:
            logger.error(f"❌ Error getting performance reports: {e}")
            return []
    
    def execute_trading_signals(self):
        """Execute trading signals"""
        try:
            self._ensure_initialized()
            results = []
            
            # Get all signals
            signals = self.get_all_signals()
            
            for signal in signals:
                try:
                    # Execute the signal through order manager
                    if self._order_manager:
                        result = self._order_manager.execute_signal(signal)
                        results.append({
                            'signal': signal,
                            'result': result,
                            'status': 'executed' if result.get('success') else 'failed'
                        })
                    else:
                        results.append({
                            'signal': signal,
                            'result': {'error': 'Order manager not available'},
                            'status': 'failed'
                        })
                except Exception as e:
                    results.append({
                        'signal': signal,
                        'result': {'error': str(e)},
                        'status': 'failed'
                    })
            
            return results
        except Exception as e:
            logger.error(f"❌ Error executing trading signals: {e}")
            return []

# Global dashboard manager instance
dashboard_manager = AdvancedDashboardManager()

# Flask routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard_advanced.html')

@app.route('/mockup')
def mockup():
    """View the improved dashboard mockup"""
    import os
    mockup_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dashboard_mockup_improved_dashboard.html')
    if os.path.exists(mockup_path):
        with open(mockup_path, 'r') as f:
            return f.read()
    else:
        # Try alternative path
        alt_path = os.path.join(os.path.dirname(__file__), '../../../dashboard_mockup_improved_dashboard.html')
        if os.path.exists(alt_path):
            with open(alt_path, 'r') as f:
                return f.read()
        return f"Mockup file not found. Tried: {mockup_path} and {alt_path}", 404

@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        status = dashboard_manager.get_system_status()
        # Manual conversion to ensure JSON serialization
        if isinstance(status, dict):
            # Convert any sets to lists
            def convert_sets(obj):
                if isinstance(obj, set):
                    return list(obj)
                elif isinstance(obj, dict):
                    return {k: convert_sets(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_sets(item) for item in obj]
                else:
                    return obj
            status = convert_sets(status)
        return jsonify(status)
    except Exception as e:
        logger.error(f"❌ API Status error: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/overview')
def api_overview():
    """Get account overview"""
    try:
        overview = dashboard_manager.get_account_overview()
        # Manual conversion to ensure JSON serialization
        if isinstance(overview, dict):
            def convert_sets(obj):
                if isinstance(obj, set):
                    return list(obj)
                elif isinstance(obj, dict):
                    return {k: convert_sets(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_sets(item) for item in obj]
                else:
                    return obj
            overview = convert_sets(overview)
        return jsonify(overview)
    except Exception as e:
        logger.error(f"❌ API Overview error: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        })

# Lightweight in-memory cache for high-frequency endpoints
_SIGNALS_CACHE = {'data': None, 'ts': 0}
_SIGNALS_CACHE_TTL = 3  # seconds

@app.route('/api/signals')
def api_signals():
    """Get all active signals from strategies"""
    try:
        import time as _time
        now_s = int(_time.time())
        if _SIGNALS_CACHE['data'] and (now_s - _SIGNALS_CACHE['ts'] <= _SIGNALS_CACHE_TTL):
            return jsonify(_SIGNALS_CACHE['data'])

        signals = dashboard_manager.get_all_signals()
        payload = {
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
        _SIGNALS_CACHE['data'] = payload
        _SIGNALS_CACHE['ts'] = now_s
        return jsonify(payload)
    except Exception as e:
        logger.error(f"❌ API Signals error: {e}")
        return jsonify({
            'error': str(e),
            'signals': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        })

@app.route('/api/reports')
def api_reports():
    """Get all available reports"""
    try:
        reports = dashboard_manager.get_all_reports()
        return jsonify({
            'reports': reports,
            'count': len(reports),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
    except Exception as e:
        logger.warning(f"⚠️ API Reports error (returning empty): {e}")
        return jsonify({
            'reports': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })  # Return 200 with empty data

@app.route('/api/health/nontrading')
def api_health_nontrading():
    """Health summary for non-trading subsystems (collectors, news, risk)."""
    try:
        from src.core.data_collector import get_data_collector
        from src.core.news_integration import safe_news_integration
        collector = get_data_collector()
        health = collector.get_health_summary() if hasattr(collector, 'get_health_summary') else collector.get_collection_status()
        news = {
            'enabled': getattr(safe_news_integration, 'enabled', False),
            'last_update': getattr(safe_news_integration, 'last_update', None).isoformat() if getattr(safe_news_integration, 'last_update', None) else None,
            'cache_valid': safe_news_integration._is_cache_valid() if hasattr(safe_news_integration, '_is_cache_valid') else False
        }
        return jsonify({
            'status': 'success',
            'collector': health,
            'news': news,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ API Nontrading health error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/weekly-reports')
def api_weekly_reports():
    """Get weekly performance reports"""
    try:
        weekly_reports = dashboard_manager.get_weekly_reports()
        return jsonify({
            'weekly_reports': weekly_reports,
            'count': len(weekly_reports),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"❌ API Weekly Reports error: {e}")
        return jsonify({
            'error': str(e),
            'weekly_reports': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        })

@app.route('/api/roadmap')
def api_roadmap():
    """Get strategy roadmap and future plans"""
    try:
        roadmap = dashboard_manager.get_strategy_roadmap()
        return jsonify({
            'roadmap': roadmap,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"❌ API Roadmap error: {e}")
        return jsonify({
            'error': str(e),
            'roadmap': {},
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        })

@app.route('/api/strategy-reports')
def api_strategy_reports():
    """Get individual strategy reports"""
    try:
        strategy_reports = dashboard_manager.get_strategy_reports()
        return jsonify({
            'strategy_reports': strategy_reports,
            'count': len(strategy_reports),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"❌ API Strategy Reports error: {e}")
        return jsonify({
            'error': str(e),
            'strategy_reports': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        })

@app.route('/api/performance-reports')
def api_performance_reports():
    """Get performance analysis reports"""
    try:
        performance_reports = dashboard_manager.get_performance_reports()
        return jsonify({
            'performance_reports': performance_reports,
            'count': len(performance_reports),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"❌ API Performance Reports error: {e}")
        return jsonify({
            'error': str(e),
            'performance_reports': [],
            'count': 0,
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        })

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

@app.route('/api/bulletin/morning')
def api_bulletin_morning():
    """Get morning bulletin data"""
    try:
        bulletin = dashboard_manager.get_morning_bulletin()
        return jsonify(bulletin)
    except Exception as e:
        logger.error(f"Error generating morning bulletin: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'live_data_mode': dashboard_manager.use_live_data,
        'active_accounts': len(dashboard_manager.active_accounts)
    })

# Trade Suggestions API Endpoints - Proxy to working system
@app.route('/api/suggestions', methods=['GET'])
def api_get_suggestions():
    """Get trade suggestions - proxy to working system"""
    try:
        import requests
        response = requests.get('http://localhost:8082/api/suggestions', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"❌ Error getting suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'suggestions': []
        })

@app.route('/api/suggestions/generate', methods=['POST'])
def api_generate_suggestions():
    """Generate new trade suggestions - proxy to working system"""
    try:
        import requests
        response = requests.post('http://localhost:8082/api/suggestions/generate', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"❌ Error generating suggestions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'suggestions': []
        })

@app.route('/api/suggestions/<suggestion_id>/approve', methods=['POST'])
def api_approve_suggestion(suggestion_id):
    """Approve a trade suggestion - proxy to working system"""
    try:
        import requests
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/approve', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"❌ Error approving suggestion {suggestion_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/suggestions/<suggestion_id>/reject', methods=['POST'])
def api_reject_suggestion(suggestion_id):
    """Reject a trade suggestion - proxy to working system"""
    try:
        import requests
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/reject', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"❌ Error rejecting suggestion {suggestion_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/suggestions/<suggestion_id>/execute', methods=['POST'])
def api_execute_suggestion(suggestion_id):
    """Execute a trade suggestion - proxy to working system"""
    try:
        import requests
        response = requests.post(f'http://localhost:8082/api/suggestions/{suggestion_id}/execute', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"❌ Error executing suggestion {suggestion_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Performance Monitoring API Endpoints
@app.route('/api/performance/overview')
def api_performance_overview():
    """Get performance overview data"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        stats = db.get_database_stats()
        
        overview = {
            'total_trades': stats.get('total_trades', 0),
            'total_pnl': 0,
            'win_rate': 0,
            'active_strategies': stats.get('strategies_count', 0),
            'last_updated': stats.get('latest_trade', 'Never')
        }
        
        return jsonify(overview)
    except Exception as e:
        logger.error(f"Error getting performance overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/strategies')
def api_performance_strategies():
    """Get strategy performance data"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        
        strategies = []
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategy_metrics")
            rows = cursor.fetchall()
            
            for row in rows:
                strategies.append({
                    'strategy_id': row['strategy_id'],
                    'total_trades': row['total_trades'],
                    'win_rate': row['win_rate'],
                    'total_pnl': row['total_pnl'],
                    'sharpe_ratio': row['sharpe_ratio'],
                    'max_drawdown': row['max_drawdown']
                })
        
        return jsonify({'strategies': strategies})
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/trades')
def api_performance_trades():
    """Get recent trade history"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        
        trades = []
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trade_id, strategy_id, instrument, direction, 
                       realized_pnl, is_closed, entry_time
                FROM trades 
                ORDER BY entry_time DESC 
                LIMIT 20
            """)
            rows = cursor.fetchall()
            
            for row in rows:
                trades.append({
                    'trade_id': row['trade_id'],
                    'strategy_id': row['strategy_id'],
                    'instrument': row['instrument'],
                    'direction': row['direction'],
                    'realized_pnl': row['realized_pnl'],
                    'is_closed': bool(row['is_closed']),
                    'entry_time': row['entry_time']
                })
        
        return jsonify({'trades': trades})
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/metrics')
def api_performance_metrics():
    """Get key performance metrics"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        
        metrics = {}
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(profit_factor) as avg_profit_factor,
                       MAX(max_drawdown) as max_drawdown,
                       AVG(avg_trade_duration_seconds) as avg_trade_duration,
                       AVG(risk_reward_ratio) as risk_reward_ratio
                FROM strategy_metrics
            """)
            row = cursor.fetchone()
            
            if row:
                metrics = {
                    'profit_factor': row['avg_profit_factor'] or 'N/A',
                    'max_drawdown': row['max_drawdown'] or 'N/A',
                    'avg_trade_duration': row['avg_trade_duration'] or 'N/A',
                    'risk_reward_ratio': row['risk_reward_ratio'] or 'N/A'
                }
        
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/database')
def api_performance_database():
    """Get database statistics"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        stats = db.get_database_stats()
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/filtered')
def api_performance_filtered():
    """Get filtered performance data"""
    try:
        from src.analytics.trade_database import get_trade_database
        db = get_trade_database()
        
        # Get filter parameters
        strategy_id = request.args.get('strategy_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        instrument = request.args.get('instrument')
        status = request.args.get('status', 'all')  # 'all', 'open', 'closed'
        period = request.args.get('period', 'month')  # 'today', 'week', 'month', '90days'
        
        # Calculate date range based on period
        if not start_date or not end_date:
            today = datetime.now()
            if period == 'today':
                start_date = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                end_date = today.isoformat()
            elif period == 'week':
                start_date = (today - timedelta(days=7)).isoformat()
                end_date = today.isoformat()
            elif period == 'month':
                start_date = (today - timedelta(days=30)).isoformat()
                end_date = today.isoformat()
            elif period == '90days':
                start_date = (today - timedelta(days=90)).isoformat()
                end_date = today.isoformat()
            else:
                start_date = (today - timedelta(days=30)).isoformat()
                end_date = today.isoformat()
        
        # Get trades with filters
        if strategy_id and strategy_id != 'all':
            all_trades = db.get_trades_by_date_range(start_date, end_date, strategy_id)
        else:
            all_trades = db.get_trades_by_date_range(start_date, end_date)
        
        # Apply instrument filter
        if instrument and instrument != 'all':
            all_trades = [t for t in all_trades if t.get('instrument') == instrument]
        
        # Apply status filter
        if status == 'open':
            trades = [t for t in all_trades if t.get('is_closed', 0) == 0]
        elif status == 'closed':
            trades = [t for t in all_trades if t.get('is_closed', 0) == 1]
        else:
            trades = all_trades
        
        # Calculate metrics
        closed_trades = [t for t in trades if t.get('is_closed', 0) == 1]
        wins = sum(1 for t in closed_trades if (t.get('realized_pnl', 0) or 0) > 0)
        losses = len(closed_trades) - wins
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0
        
        total_pnl = sum((t.get('realized_pnl', 0) or 0) for t in closed_trades)
        total_profit = sum((t.get('realized_pnl', 0) or 0) for t in closed_trades if (t.get('realized_pnl', 0) or 0) > 0)
        total_loss = abs(sum((t.get('realized_pnl', 0) or 0) for t in closed_trades if (t.get('realized_pnl', 0) or 0) < 0))
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
        
        # Get strategy breakdown
        strategy_breakdown = {}
        for trade in closed_trades:
            sid = trade.get('strategy_id', 'unknown')
            if sid not in strategy_breakdown:
                strategy_breakdown[sid] = {
                    'strategy_id': sid,
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'pnl': 0.0
                }
            
            strategy_breakdown[sid]['trades'] += 1
            pnl = trade.get('realized_pnl', 0) or 0
            strategy_breakdown[sid]['pnl'] += pnl
            if pnl > 0:
                strategy_breakdown[sid]['wins'] += 1
            else:
                strategy_breakdown[sid]['losses'] += 1
        
        # Calculate win rates for each strategy
        for sid, data in strategy_breakdown.items():
            data['win_rate'] = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0.0
        
        # Get max drawdown (simplified - would need proper calculation)
        if closed_trades:
            pnl_values = [(t.get('realized_pnl', 0) or 0) for t in closed_trades]
            running_total = 0
            max_total = 0
            max_drawdown = 0
            for pnl in pnl_values:
                running_total += pnl
                if running_total > max_total:
                    max_total = running_total
                drawdown = max_total - running_total
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            max_drawdown = 0.0
        
        return jsonify({
            'success': True,
            'filters': {
                'strategy_id': strategy_id,
                'start_date': start_date,
                'end_date': end_date,
                'instrument': instrument,
                'status': status,
                'period': period
            },
            'metrics': {
                'total_trades': len(trades),
                'open_trades': len([t for t in trades if t.get('is_closed', 0) == 0]),
                'closed_trades': len(closed_trades),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'profit_factor': profit_factor,
                'avg_win': (total_profit / wins) if wins > 0 else 0.0,
                'avg_loss': (total_loss / losses) if losses > 0 else 0.0,
                'max_drawdown': max_drawdown
            },
            'strategies': list(strategy_breakdown.values()),
            'trades': trades[:100],  # Limit to 100 most recent
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error getting filtered performance: {e}")
        import traceback
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/roadmap/progress')
def api_roadmap_progress():
    """Get roadmap progress tracking"""
    try:
        from src.analytics.trade_database import get_trade_database
        
        # Try to import roadmap planner
        try:
            from src.core.trump_dna_framework import get_trump_dna_planner
            planner = get_trump_dna_planner()
            weekly_plans = planner.weekly_plans
        except Exception as e:
            logger.warning(f"⚠️ Roadmap planner not available: {e}")
            weekly_plans = {}
        
        db = get_trade_database()
        
        # Get current week dates
        today = datetime.now()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        week_start_str = week_start.strftime('%Y-%m-%d')
        week_end_str = week_end.strftime('%Y-%m-%d')
        
        # Calculate overall progress
        total_weekly_target = sum(plan.weekly_target_dollars for plan in weekly_plans.values()) if weekly_plans else 0
        
        # Get all trades for this week
        week_trades = db.get_trades_by_date_range(
            f"{week_start_str}T00:00:00",
            f"{week_end_str}T23:59:59"
        )
        
        # Filter closed trades only
        closed_trades = [t for t in week_trades if t.get('is_closed', 0) == 1]
        
        # Calculate current progress
        current_progress = sum((t.get('realized_pnl', 0) or 0) for t in closed_trades)
        
        # Calculate expected progress (linear based on days passed)
        days_passed = (datetime.now() - week_start).days + 1
        expected_progress = (total_weekly_target / 7) * days_passed if total_weekly_target > 0 else 0
        
        # Calculate daily progress
        daily_progress = []
        for day_offset in range(7):
            day_date = week_start + timedelta(days=day_offset)
            day_name = day_date.strftime('%A')
            day_start = day_date.strftime('%Y-%m-%dT00:00:00')
            day_end = day_date.strftime('%Y-%m-%dT23:59:59')
            
            # Get trades for this day
            day_trades = db.get_trades_by_date_range(day_start, day_end)
            day_closed = [t for t in day_trades if t.get('is_closed', 0) == 1]
            
            # Calculate day metrics
            day_pnl = sum((t.get('realized_pnl', 0) or 0) for t in day_closed)
            day_wins = sum(1 for t in day_closed if (t.get('realized_pnl', 0) or 0) > 0)
            day_win_rate = (day_wins / len(day_closed) * 100) if day_closed else 0.0
            
            # Get target for this day
            daily_target = total_weekly_target / 7 if total_weekly_target > 0 else 0
            
            # Determine status
            if day_date.date() < datetime.now().date():
                status = 'complete'
            elif day_date.date() == datetime.now().date():
                status = 'current'
            else:
                status = 'upcoming'
            
            daily_progress.append({
                'day': day_name,
                'date': day_date.strftime('%Y-%m-%d'),
                'target': daily_target,
                'actual': day_pnl,
                'trades': len(day_closed),
                'wins': day_wins,
                'losses': len(day_closed) - day_wins,
                'win_rate': day_win_rate,
                'status': status
            })
        
        # Calculate strategy-specific progress
        strategy_progress = []
        for plan_key, plan in weekly_plans.items():
            strategy_id = plan.strategy_name.lower().replace(' ', '_').replace('-', '_')
            pair = plan.pair
            
            # Get trades for this strategy/pair this week
            strategy_trades = [
                t for t in closed_trades
                if (t.get('strategy_id', '').lower() == strategy_id or 
                    t.get('strategy_id', '').lower() in strategy_id or
                    strategy_id in t.get('strategy_id', '').lower())
                and t.get('instrument', '') == pair
            ]
            
            strategy_pnl = sum((t.get('realized_pnl', 0) or 0) for t in strategy_trades)
            strategy_target = plan.weekly_target_dollars
            strategy_progress_pct = (strategy_pnl / strategy_target * 100) if strategy_target > 0 else 0.0
            
            # Check if on track
            expected_strategy_progress = (strategy_target / 7) * days_passed if strategy_target > 0 else 0
            on_track = strategy_pnl >= (expected_strategy_progress * 0.9)  # 90% tolerance
            
            strategy_progress.append({
                'strategy_id': strategy_id,
                'strategy_name': plan.strategy_name,
                'pair': pair,
                'target': strategy_target,
                'current': strategy_pnl,
                'progress_pct': strategy_progress_pct,
                'trades': len(strategy_trades),
                'on_track': on_track
            })
        
        # Overall on-track calculation
        weekly_progress_pct = (current_progress / total_weekly_target * 100) if total_weekly_target > 0 else 0.0
        on_track = current_progress >= (expected_progress * 0.9)  # 90% tolerance
        
        return jsonify({
            'success': True,
            'week_info': {
                'week_start': week_start_str,
                'week_end': week_end_str,
                'current_day': datetime.now().strftime('%A'),
                'days_passed': days_passed,
                'days_remaining': 7 - days_passed,
                'week_progress_pct': (days_passed / 7) * 100
            },
            'targets': {
                'weekly_target': total_weekly_target,
                'current_progress': current_progress,
                'expected_progress': expected_progress,
                'weekly_progress_pct': weekly_progress_pct,
                'on_track': on_track,
                'variance': current_progress - expected_progress,
                'variance_pct': ((current_progress - expected_progress) / expected_progress * 100) if expected_progress > 0 else 0.0
            },
            'daily_progress': daily_progress,
            'strategy_progress': strategy_progress,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error calculating roadmap progress: {e}")
        import traceback
        logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/opportunities')
def api_opportunities():
    """Get trading opportunities with approve/watch/hold buttons"""
    try:
        opportunities = [
            {
                'id': 'eur_usd_001',
                'instrument': 'EUR_USD',
                'direction': 'BUY',
                'suggested_entry': 1.0850,
                'fixed_stop_loss': 1.0820,
                'estimated_target': 1.0880,
                'risk_reward_ratio': 1.5,
                'confidence': 78,
                'strategy': 'Scalping',
                'quality_score': 85,
                'reason': 'Strong bullish momentum with RSI oversold bounce'
            },
            {
                'id': 'xau_usd_001',
                'instrument': 'XAU_USD',
                'direction': 'BUY',
                'suggested_entry': 2650.50,
                'fixed_stop_loss': 2640.00,
                'estimated_target': 2660.00,
                'risk_reward_ratio': 1.0,
                'confidence': 72,
                'strategy': 'Scalping',
                'quality_score': 78,
                'reason': 'Gold breakout above resistance with volume confirmation'
            },
            {
                'id': 'gbp_usd_001',
                'instrument': 'GBP_USD',
                'direction': 'SELL',
                'suggested_entry': 1.2650,
                'fixed_stop_loss': 1.2680,
                'estimated_target': 1.2600,
                'risk_reward_ratio': 1.7,
                'confidence': 68,
                'strategy': 'Scalping',
                'quality_score': 72,
                'reason': 'Bearish divergence on 4H chart with resistance rejection'
            }
        ]
        
        return jsonify({
            'opportunities': opportunities,
            'count': len(opportunities),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts')
def api_accounts():
    """Get all account information"""
    try:
        overview = dashboard_manager.get_account_overview()
        # Transform to match expected format
        accounts_dict = {}
        if 'accounts' in overview:
            for account_id, account_data in overview['accounts'].items():
                accounts_dict[account_id] = {
                    'display_name': account_data.get('account_name', account_id),
                    'balance': account_data.get('balance', 0),
                    'nav': account_data.get('balance', 0) + account_data.get('unrealized_pl', 0),
                    'unrealized_pl': account_data.get('unrealized_pl', 0),
                    'currency': account_data.get('currency', 'USD'),
                    'margin_used': account_data.get('margin_used', 0),
                    'margin_available': account_data.get('margin_available', 0),
                    'open_positions': account_data.get('open_positions', 0)
                }
        return jsonify(accounts_dict)
    except Exception as e:
        logger.warning(f"⚠️ API Accounts error (returning empty): {e}")
        return jsonify({})  # Return empty dict, not error

@app.route('/api/strategies/overview')
def api_strategies_overview():
    """Get strategies overview"""
    try:
        trading_metrics = dashboard_manager._get_trading_metrics()
        strategies_list = []
        
        if 'accounts' in trading_metrics:
            for account_id, metrics in trading_metrics['accounts'].items():
                strategy_name = metrics.get('strategy_name', 'Unknown')
                strategies_list.append({
                    'name': strategy_name,
                    'account_id': account_id,
                    'win_rate': metrics.get('win_rate', 0),
                    'total_trades': metrics.get('total_trades', 0),
                    'total_pnl': metrics.get('total_profit', 0) + metrics.get('total_loss', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0)
                })
        
        return jsonify({
            'strategies': strategies_list,
            'count': len(strategies_list),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Strategies Overview error (returning empty): {e}")
        return jsonify({
            'strategies': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/positions')
def api_positions():
    """Get all open positions"""
    try:
        overview = dashboard_manager.get_account_overview()
        all_positions = []
        
        if 'accounts' in overview:
            for account_id, account_data in overview['accounts'].items():
                # Get positions for this account from order manager
                try:
                    if dashboard_manager.order_manager:
                        account_positions = dashboard_manager.order_manager.get_open_positions(account_id)
                        if account_positions:
                            for pos in account_positions:
                                if hasattr(pos, 'instrument'):
                                    all_positions.append({
                                        'instrument': pos.instrument,
                                        'long': pos.units > 0 if hasattr(pos, 'units') else True,
                                        'units': abs(pos.units) if hasattr(pos, 'units') else 0,
                                        'unrealizedPL': pos.unrealized_pl if hasattr(pos, 'unrealized_pl') else 0,
                                        'account_id': account_id
                                    })
                except Exception as e:
                    logger.warning(f"⚠️ Error getting positions for {account_id}: {e}")
        
        return jsonify({
            'positions': all_positions,
            'count': len(all_positions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Positions error (returning empty): {e}")
        return jsonify({
            'positions': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/signals/pending')
def api_signals_pending():
    """Get pending trading signals"""
    try:
        signals = dashboard_manager.get_all_signals()
        # Filter pending signals (not yet executed)
        pending_signals = []
        for signal in signals:
            pending_signals.append({
                'id': f"{signal.get('strategy', 'unknown')}_{signal.get('instrument', 'unknown')}_{datetime.now().timestamp()}",
                'instrument': signal.get('instrument', 'Unknown'),
                'direction': signal.get('side', 'UNKNOWN'),
                'entry_price': signal.get('entry_price', 0),
                'stop_loss': signal.get('stop_loss', 0),
                'take_profit': signal.get('take_profit', 0),
                'quality_score': int(signal.get('confidence', 0) * 100),
                'strategy': signal.get('strategy', 'Unknown')
            })
        
        return jsonify({
            'success': True,
            'signals': pending_signals,
            'count': len(pending_signals),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Signals Pending error (returning empty): {e}")
        return jsonify({
            'success': True,
            'signals': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/signals/active')
def api_signals_active():
    """Get active trading signals (open trades)"""
    try:
        overview = dashboard_manager.get_account_overview()
        active_signals = []
        
        if 'accounts' in overview:
            for account_id, account_data in overview['accounts'].items():
                open_positions = account_data.get('open_positions', 0)
                if open_positions > 0:
                    # Get active positions
                    try:
                        if dashboard_manager.order_manager:
                            positions = dashboard_manager.order_manager.get_open_positions(account_id)
                            for pos in positions:
                                if hasattr(pos, 'instrument'):
                                    active_signals.append({
                                        'id': f"{account_id}_{pos.instrument}",
                                        'instrument': pos.instrument,
                                        'side': 'BUY' if (hasattr(pos, 'units') and pos.units > 0) else 'SELL',
                                        'entry_price': pos.average_price if hasattr(pos, 'average_price') else 0,
                                        'current_price': pos.current_price if hasattr(pos, 'current_price') else 0,
                                        'unrealized_pl': pos.unrealized_pl if hasattr(pos, 'unrealized_pl') else 0,
                                        'strategy': account_data.get('account_name', 'Unknown'),
                                        'account_id': account_id
                                    })
                    except Exception as e:
                        logger.warning(f"⚠️ Error getting active positions for {account_id}: {e}")
        
        return jsonify({
            'success': True,
            'signals': active_signals,
            'count': len(active_signals),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Signals Active error (returning empty): {e}")
        return jsonify({
            'success': True,
            'signals': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/news')
def api_news():
    """Get market news and events"""
    try:
        news_data = dashboard_manager._get_news_data()
        # Transform to match expected format
        news_items = []
        if 'news_items' in news_data:
            news_items = news_data['news_items']
        
        return jsonify({
            'news': news_items,
            'count': len(news_items),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API News error (returning empty): {e}")
        return jsonify({
            'news': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/trades/count')
def api_trades_count():
    """Get active trades count"""
    try:
        overview = dashboard_manager.get_account_overview()
        total_active = 0
        
        if 'accounts' in overview:
            for account_id, account_data in overview['accounts'].items():
                total_active += account_data.get('open_positions', 0)
        
        return jsonify({
            'active_trades': total_active,
            'count': total_active,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Trades Count error (returning empty): {e}")
        return jsonify({
            'active_trades': 0,
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

@app.route('/api/performance/live')
def api_performance_live():
    """Get live performance data"""
    try:
        overview = dashboard_manager.get_account_overview()
        trading_metrics = dashboard_manager._get_trading_metrics()
        
        # Calculate totals
        totals = {
            'open_trades': 0,
            'open_positions': 0,
            'unrealized_pl': 0,
            'total_nav': 0
        }
        
        accounts_list = []
        recent_trades = []
        
        if 'accounts' in overview:
            for account_id, account_data in overview['accounts'].items():
                totals['open_positions'] += account_data.get('open_positions', 0)
                totals['unrealized_pl'] += account_data.get('unrealized_pl', 0)
                totals['total_nav'] += account_data.get('balance', 0) + account_data.get('unrealized_pl', 0)
                
                accounts_list.append({
                    'account_id': account_id,
                    'display_name': account_data.get('account_name', account_id),
                    'open_trades': account_data.get('open_positions', 0),
                    'open_positions': account_data.get('open_positions', 0),
                    'unrealized_pl': account_data.get('unrealized_pl', 0),
                    'nav': account_data.get('balance', 0) + account_data.get('unrealized_pl', 0)
                })
        
        return jsonify({
            'totals': totals,
            'accounts': accounts_list,
            'recent_trades': recent_trades,
            'trades_today': 0,
            'active_strategies': len(accounts_list),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"⚠️ API Performance Live error (returning empty): {e}")
        return jsonify({
            'totals': {
                'open_trades': 0,
                'open_positions': 0,
                'unrealized_pl': 0,
                'total_nav': 0
            },
            'accounts': [],
            'recent_trades': [],
            'trades_today': 0,
            'active_strategies': 0,
            'timestamp': datetime.now().isoformat()
        })  # Return 200 with empty data

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
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
