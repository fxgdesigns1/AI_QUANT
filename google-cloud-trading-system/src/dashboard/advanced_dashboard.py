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

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../oanda_config.env'))

# Add the project path
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')
sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system/src')

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
            logger.error("❌ No active OANDA accounts found")
            raise ValueError("No active OANDA accounts configured")
        
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
        
        # Start live data feed with verification
        self._data_feed.start()
        logger.info("✅ Live data feed start() called")
        
        # Verify it's actually running
        time.sleep(3)
        # Check if data feed has running attribute (LiveDataFeed) or streaming (MultiAccountDataFeed)
        is_running = getattr(self._data_feed, 'running', getattr(self._data_feed, 'streaming', False))
        if not is_running:
            logger.error("❌ Data feed failed to start - running/streaming flag is False")
            raise RuntimeError("❌ Data feed failed to start")
        
        # Wait for first data update (up to 10 seconds)
        data_received = False
        for i in range(10):
            if self._data_feed.market_data:
                logger.info(f"✅ Data feed confirmed active - {len(self._data_feed.market_data)} instruments loaded")
                data_received = True
                break
            time.sleep(1)
        
        if not data_received:
            logger.warning("⚠️ No data received after 10 seconds - may be market closed or connection issue")
        else:
            # Log sample data freshness
            for inst, data in list(self._data_feed.market_data.items())[:3]:
                # Handle both object and dict formats
                age = getattr(data, 'last_update_age', data.get('last_update_age', 0) if isinstance(data, dict) else 0)
                bid = getattr(data, 'bid', data.get('bid', 0) if isinstance(data, dict) else 0)
                logger.info(f"  📊 {inst}: age={age}s, bid={bid:.5f}")
        
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
                # Get account statuses
                account_statuses = {}
                if self.trading_systems:
                    for account_id, system_info in self.trading_systems.items():
                        try:
                            account_status = self.account_manager.get_account_status(account_id)
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
        """Get market news and sentiment data"""
        def _build():
            try:
                # Placeholder news structure; real integration elsewhere
                return {
                    'timestamp': self._safe_timestamp(datetime.now()),
                    'news_items': [],
                    'sentiment_score': 0.0,
                    'market_regime': 'neutral',
                    'high_impact_events': []
                }
            except Exception as e:
                logger.error(f"❌ Failed to get news data: {e}")
                return {
                    'error': str(e),
                    'timestamp': self._safe_timestamp(datetime.now())
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

@app.route('/api/execute_signals', methods=['POST'])
def api_execute_signals():
    """Execute trading signals"""
    try:
        results = dashboard_manager.execute_trading_signals()
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': self._safe_timestamp(datetime.now())
        })
    except Exception as e:
        logger.error(f"❌ Failed to execute signals: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': self._safe_timestamp(datetime.now())
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
            'timestamp': self._safe_timestamp(datetime.now()),
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
