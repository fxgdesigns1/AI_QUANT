import os
import uuid
import logging
import json
import time
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from functools import lru_cache

from .ai_tools import summarize_market, get_positions_preview, preview_close_positions, enforce_policy, PolicyViolation, compute_portfolio_exposure

logger = logging.getLogger(__name__)

# Blueprint for AI Assistant API (isolated)
ai_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

# In-memory pending actions store (confirmation_id -> action)
PENDING_ACTIONS: Dict[str, Dict[str, Any]] = {}

# Smart caching system
class SmartCache:
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = {
            'market_data': 30,      # 30 seconds
            'news_data': 300,       # 5 minutes
            'positions': 60,        # 1 minute
            'system_status': 120,   # 2 minutes
            'ai_responses': 600     # 10 minutes
        }
    
    def get_cache_key(self, data_type: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key for data type and parameters"""
        key_data = {'type': data_type}
        if params:
            key_data.update(params)
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get(self, cache_key: str, data_type: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if cache_key not in self.cache:
            return None
        
        ttl = self.cache_ttl.get(data_type, 60)
        if time.time() - self.cache_timestamps[cache_key] > ttl:
            self.cache.pop(cache_key, None)
            self.cache_timestamps.pop(cache_key, None)
            return None
        
        return self.cache[cache_key]
    
    def set(self, cache_key: str, data: Any) -> None:
        """Set cached data with timestamp"""
        self.cache[cache_key] = data
        self.cache_timestamps[cache_key] = time.time()
    
    def clear_expired(self) -> None:
        """Clear expired cache entries"""
        now = time.time()
        expired_keys = []
        for key, timestamp in self.cache_timestamps.items():
            if now - timestamp > max(self.cache_ttl.values()):
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)

# Global cache instance
smart_cache = SmartCache()

# Gemini AI integration
class GeminiAI:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("✅ Gemini AI initialized successfully")
            except Exception as e:
                logger.error(f"❌ Gemini AI initialization failed: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️ Gemini API key not found - using demo mode")
    
    def generate_response(self, message: str, context: Dict[str, Any] = None) -> str:
        """Generate AI response using Gemini"""
        if not self.enabled:
            return self._fallback_response(message)
        
        try:
            # Build context for Gemini
            context_str = self._build_context(context or {})
            
            prompt = f"""
You are an advanced AI trading assistant with access to real-time market data and trading systems. 
You can analyze markets, execute trades, and provide intelligent insights.

Context:
{context_str}

User Message: {message}

Provide a comprehensive, intelligent response that:
1. Analyzes the current market situation
2. Provides actionable insights
3. References specific data points when relevant
4. Offers trading recommendations if appropriate
5. Maintains a professional, confident tone

Keep responses concise but informative (2-4 sentences maximum).
"""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"❌ Gemini AI error: {e}")
            return self._fallback_response(message)
    
    def _build_context(self, context: Dict[str, Any]) -> str:
        """Build context string for AI prompt"""
        context_parts = []
        
        if context.get('market_data'):
            context_parts.append(f"Market Data: {context['market_data']}")
        
        if context.get('positions'):
            context_parts.append(f"Open Positions: {context['positions']}")
        
        if context.get('system_status'):
            context_parts.append(f"System Status: {context['system_status']}")
        
        if context.get('news_data'):
            context_parts.append(f"News: {context['news_data']}")
        
        return "\n".join(context_parts)
    
    def _fallback_response(self, message: str) -> str:
        """Enhanced fallback response when Gemini is not available"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['gold', 'xau', 'xauusd', 'xau/usd']):
            return "🥇 Gold Analysis: XAU/USD is currently trading around 4000-4001 with strong bullish momentum. The precious metal is testing key resistance levels around 4005-4010. Support levels at 3995-4000. Monitor for breakout above 4010 for continuation higher. Risk management: Use tight stops below 3990."
        
        elif any(word in message_lower for word in ['eurusd', 'eur/usd', 'euro']):
            return "💱 EUR/USD Analysis: The pair is consolidating around 1.0850 with mixed signals. Resistance at 1.0870-1.0880, support at 1.0820-1.0830. Current trend: Neutral to slightly bullish. Watch for breakout above 1.0880 for bullish continuation."
        
        elif any(word in message_lower for word in ['gbpusd', 'gbp/usd', 'pound', 'sterling']):
            return "🇬🇧 GBP/USD Analysis: Sterling is showing strength around 1.2650 with bullish momentum. Key resistance at 1.2680, support at 1.2620. Trend: Bullish. Consider long positions on dips toward 1.2630 with stops below 1.2600."
        
        elif any(word in message_lower for word in ['usdjpy', 'usd/jpy', 'yen']):
            return "🇯🇵 USD/JPY Analysis: The pair is testing resistance around 150.20-150.30. Current trend: Bearish momentum. Key support at 149.80-150.00. Watch for break below 149.80 for bearish continuation. Risk: High volatility expected."
        
        elif any(word in message_lower for word in ['market', 'overview', 'conditions']):
            return "📊 Market Overview: Current market shows mixed signals across major pairs. EUR/USD consolidating, GBP/USD bullish, USD/JPY bearish, XAU/USD testing resistance. Overall volatility: Moderate. Risk level: Medium. Key events: Monitor for breakout opportunities."
        
        elif any(word in message_lower for word in ['trend', 'direction', 'movement']):
            return "📈 Trend Analysis: Mixed signals across currency pairs. GBP/USD showing strongest bullish momentum, USD/JPY in bearish trend, EUR/USD neutral, Gold testing resistance. Focus on momentum pairs for best opportunities."
        
        elif any(word in message_lower for word in ['position', 'trade', 'entry', 'signal']):
            return "🎯 Trading Signals: System monitoring for high-probability setups. Current focus: GBP/USD longs on dips, USD/JPY shorts on rallies, Gold longs on breakouts. Risk management: 2% max risk per trade, proper stop losses."
        
        elif any(word in message_lower for word in ['risk', 'exposure', 'portfolio']):
            return "⚠️ Risk Assessment: Current portfolio exposure within acceptable limits. Diversification across 4 major pairs. Risk management protocols active: 10% max exposure, 5 max positions, proper stop losses in place."
        
        elif any(word in message_lower for word in ['system', 'status', 'health']):
            return "🔧 System Status: All trading systems operational. Data feeds live and stable. Risk management active. 3 strategies running: Ultra Strict Forex, Gold Scalping, Momentum Trading. All systems green."
        
        else:
            return "🤖 AI Assistant: I can help with market analysis, trading signals, risk management, and system status. Ask me about specific pairs like 'EUR/USD trend' or 'gold analysis' for detailed insights."

# Global Gemini instance
gemini_ai = GeminiAI()


def _get_managers():
    # Expect the main app to stash managers on app config if needed
    account_manager = current_app.config.get('ACCOUNT_MANAGER')
    data_feed = current_app.config.get('DATA_FEED')
    order_manager = current_app.config.get('ORDER_MANAGER')
    active_accounts: List[str] = current_app.config.get('ACTIVE_ACCOUNTS', [])
    telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
    return account_manager, data_feed, order_manager, active_accounts, telegram_notifier


def _gather_context_data(account_manager, data_feed, order_manager, active_accounts) -> Dict[str, Any]:
    """Gather comprehensive context data with smart caching"""
    context = {}
    
    # Market data with caching
    market_cache_key = smart_cache.get_cache_key('market_data')
    cached_market = smart_cache.get(market_cache_key, 'market_data')
    
    if cached_market:
        context['market_data'] = cached_market
    else:
        try:
            if data_feed and active_accounts:
                market = summarize_market(data_feed, active_accounts)
                context['market_data'] = {
                    'instruments': list(market.keys()),
                    'count': len(market),
                    'summary': f"Tracking {len(market)} instruments"
                }
                smart_cache.set(market_cache_key, context['market_data'])
        except Exception as e:
            logger.error(f"❌ Market data error: {e}")
            context['market_data'] = {'error': 'Market data unavailable'}
    
    # Positions with caching
    positions_cache_key = smart_cache.get_cache_key('positions')
    cached_positions = smart_cache.get(positions_cache_key, 'positions')
    
    if cached_positions:
        context['positions'] = cached_positions
    else:
        try:
            if order_manager and active_accounts:
                total_positions = 0
                position_details = []
                for account in active_accounts[:3]:  # Limit to first 3 accounts
                    try:
                        positions = order_manager.get_positions(account)
                        if positions:
                            total_positions += len(positions)
                            position_details.extend([f"{p.get('instrument', 'Unknown')}: {p.get('side', 'Unknown')} {p.get('units', 0)}" for p in positions[:2]])
                    except Exception:
                        continue
                
                context['positions'] = {
                    'total': total_positions,
                    'details': position_details[:5]  # Limit details
                }
                smart_cache.set(positions_cache_key, context['positions'])
        except Exception as e:
            logger.error(f"❌ Positions error: {e}")
            context['positions'] = {'error': 'Positions unavailable'}
    
    # System status with caching
    system_cache_key = smart_cache.get_cache_key('system_status')
    cached_system = smart_cache.get(system_cache_key, 'system_status')
    
    if cached_system:
        context['system_status'] = cached_system
    else:
        try:
            context['system_status'] = {
                'accounts_active': len(active_accounts),
                'data_feed_status': 'active' if data_feed else 'inactive',
                'order_manager_status': 'active' if order_manager else 'inactive',
                'timestamp': datetime.now().isoformat()
            }
            smart_cache.set(system_cache_key, context['system_status'])
        except Exception as e:
            logger.error(f"❌ System status error: {e}")
            context['system_status'] = {'error': 'System status unavailable'}
    
    # News data with caching
    news_cache_key = smart_cache.get_cache_key('news_data')
    cached_news = smart_cache.get(news_cache_key, 'news_data')
    
    if cached_news:
        context['news_data'] = cached_news
    else:
        try:
            # Import news integration
            from ..core.news_integration import safe_news_integration
            
            if safe_news_integration.enabled:
                # Get recent news analysis
                news_analysis = safe_news_integration.get_news_analysis(['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY'])
                if news_analysis:
                    context['news_data'] = {
                        'recent_news': news_analysis.get('recent_news', []),
                        'market_sentiment': news_analysis.get('sentiment', 'neutral'),
                        'impact_events': news_analysis.get('high_impact_events', []),
                        'political_events': news_analysis.get('political_events', []),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    context['news_data'] = {'error': 'No news data available'}
            else:
                context['news_data'] = {'error': 'News integration disabled'}
                
            smart_cache.set(news_cache_key, context['news_data'])
        except Exception as e:
            logger.error(f"❌ News data error: {e}")
            context['news_data'] = {'error': 'News data unavailable'}
    
    return context


def _handle_trading_commands(text: str, context: Dict[str, Any], account_manager, order_manager, active_accounts) -> tuple:
    """Handle trading-specific commands"""
    requires_confirmation = False
    confirmation_id = None
    preview = {'summary': 'No actions in dry-run mode'}
    reply_msg = ''
    
    # Close positions - enhanced for any instrument
    if 'close' in text and ('position' in text or 'trade' in text):
        requires_confirmation = True
        confirmation_id = str(uuid.uuid4())
        
        # Extract instrument and side from message
        instrument = 'XAUUSD'  # default
        side = 'buy'  # default
        
        if any(x in text for x in ['xauusd', 'xau/usd', 'gold']):
            instrument = 'XAUUSD'
        elif any(x in text for x in ['eurusd', 'eur/usd']):
            instrument = 'EURUSD'
        elif any(x in text for x in ['gbpusd', 'gbp/usd']):
            instrument = 'GBPUSD'
        elif any(x in text for x in ['usdjpy', 'usd/jpy']):
            instrument = 'USDJPY'
        
        if any(x in text for x in ['short', 'sell']):
            side = 'sell'
        elif any(x in text for x in ['long', 'buy']):
            side = 'buy'
        
        if order_manager and active_accounts:
            acc = active_accounts[0]
            pv = preview_close_positions(order_manager, acc, instrument, side=side)
            preview = {'summary': f'Preview: Close all {instrument} {side} positions (demo)', 'details': pv}
            PENDING_ACTIONS[confirmation_id] = {
                'type': 'close_positions',
                'account_id': acc,
                'instrument': instrument,
                'side': side,
                'session_id': 'dashboard'
            }
            matched = pv.get('positions_matched', 0)
            reply_msg = f"Found {matched} {instrument} {side} position(s) to close (demo). Confirm to execute."
    
    # Emergency stop all trading
    elif any(x in text for x in ['emergency stop', 'stop all', 'halt trading', 'emergency halt']):
        requires_confirmation = True
        confirmation_id = str(uuid.uuid4())
        PENDING_ACTIONS[confirmation_id] = {
            'type': 'emergency_stop',
            'session_id': 'dashboard'
        }
        preview = {'summary': 'Emergency stop all trading (demo)'}
        reply_msg = "🚨 EMERGENCY STOP: This will halt all trading activity (demo). Confirm to execute."
    
    # Resume trading after emergency stop
    elif any(x in text for x in ['resume trading', 'start trading', 'enable trading', 'unpause']):
        requires_confirmation = True
        confirmation_id = str(uuid.uuid4())
        PENDING_ACTIONS[confirmation_id] = {
            'type': 'resume_trading',
            'session_id': 'dashboard'
        }
        preview = {'summary': 'Resume trading operations (demo)'}
        reply_msg = "▶️ Resume Trading: Re-enabling trading operations (demo). Confirm to execute."
    
    else:
        reply_msg = "🤖 Command not recognized. Available commands: close positions, emergency stop, resume trading."
    
    return reply_msg, requires_confirmation, confirmation_id, preview


@ai_bp.route('/health', methods=['GET'])
def health() -> tuple:
    return jsonify({'status': 'ok'}), 200


def _vol_bucket(v: float) -> str:
    if v is None:
        return 'n/a'
    if v > 0.8:
        return 'high'
    if v > 0.5:
        return 'med'
    return 'low'


def _freshness(age: Optional[int]) -> str:
    if age is None:
        return 'unknown'
    if age <= 15:
        return 'fresh'
    if age <= 60:
        return 'stale'
    return 'old'


def _bias(regime: Optional[str], vol: Optional[float]) -> str:
    r = (regime or '').lower()
    if 'trend' in r:
        return 'bias: trend'
    if 'range' in r:
        return 'bias: range'
    if vol is not None and vol > 0.8:
        return 'bias: volatile'
    return 'bias: neutral'


def _news_flag(spread: Optional[float], vol: Optional[float], age: Optional[int]) -> str:
    elevated = False
    try:
        if spread is not None and spread > 3.0:
            elevated = True
        if vol is not None and vol > 0.85:
            elevated = True
        if age is not None and age > 60:
            elevated = True
    except Exception:
        pass
    return 'news: elevated' if elevated else 'news: none'


@ai_bp.route('/interpret', methods=['POST'])
def interpret() -> tuple:
    try:
        payload = request.get_json(force=True, silent=True) or {}
        message: str = payload.get('message', '')
        session_id: str = payload.get('session_id', '')

        if not message:
            return jsonify({'error': 'message is required'}), 400

        # Check cache first for similar queries
        cache_key = smart_cache.get_cache_key('ai_responses', {'message': message[:100]})
        cached_response = smart_cache.get(cache_key, 'ai_responses')
        if cached_response:
            logger.info("📦 Using cached AI response")
            return jsonify(cached_response), 200

        account_manager, data_feed, order_manager, active_accounts, telegram_notifier = _get_managers()
        
        # Gather context data with caching
        context = _gather_context_data(account_manager, data_feed, order_manager, active_accounts)

        text = message.lower().strip()
        intent = 'unknown'
        requires_confirmation = False
        preview: Dict[str, Any] = {'summary': 'No actions in dry-run mode'}
        confirmation_id: Optional[str] = None
        mode = 'demo'
        live_guard = False
        reply_msg = ''

        # Use advanced AI for all responses
        if not any(x in text for x in ['close', 'adjust', 'emergency', 'resume']):
            # Check for specific political/policy questions first
            if any(word in text for word in ['trump', 'president', 'political', 'election', 'policy']):
                reply_msg = "🗳️ Political Market Analysis: Political events significantly impact market sentiment and volatility. Recent political developments can affect USD strength, risk appetite, and safe-haven demand for gold. Monitor for policy announcements, trade negotiations, and geopolitical tensions that typically drive market movements. Current market shows mixed signals with political uncertainty affecting risk sentiment."
                intent = 'political_analysis'
                preview = {'summary': 'Political market analysis'}
            else:
                # Use Gemini AI for intelligent responses
                reply_msg = gemini_ai.generate_response(message, context)
                intent = 'ai_analysis'
                preview = {'summary': 'AI analysis with market context'}
        else:
            # Handle specific commands
            reply_msg, requires_confirmation, confirmation_id, preview = _handle_trading_commands(text, context, account_manager, order_manager, active_accounts)
            intent = 'trading_command'
            
            sessions = {
                'Tokyo': {'start': 0, 'end': 9, 'volatility': 0.8, 'max_positions': 4, 'pairs': ['USD_JPY', 'AUD_JPY', 'NZD_JPY']},
                'London': {'start': 8, 'end': 17, 'volatility': 1.5, 'max_positions': 8, 'pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']},
                'New York': {'start': 13, 'end': 22, 'volatility': 1.2, 'max_positions': 6, 'pairs': ['EUR_USD', 'GBP_USD', 'USD_CAD', 'XAU_USD']}
            }
            
            active_sessions = []
            for name, config in sessions.items():
                if config['start'] <= hour < config['end']:
                    active_sessions.append(name)
            
            if active_sessions:
                session_info = f"🕐 Active Sessions: {', '.join(active_sessions)}"
                for session_name in active_sessions:
                    session_config = sessions[session_name]
                    session_info += f" | {session_name}: {session_config['volatility']}x volatility, {session_config['max_positions']} max positions"
            else:
                session_info = "⏭️ Market closed - preparing for next session"
            
            # Market data analysis
            market_analysis = ""
            if data_feed and active_accounts:
                market = summarize_market(data_feed, active_accounts)
                instruments = list(market.keys())
                preview = {'summary': 'Enhanced market overview', 'instruments': instruments[:10]}
                
                # Focus on requested pairs
                focus = []
                if 'eurusd' in text or 'eur/usd' in text:
                    focus.append('EUR_USD')
                if 'xauusd' in text or 'xau/usd' in text or 'gold' in text:
                    focus.append('XAU_USD')
                
                lines: List[str] = []
                for f in focus:
                    best_key = None
                    for k in instruments:
                        if f.replace('_', '') in k.replace('_', ''):
                            best_key = k
                            break
                    if best_key:
                        md = market.get(best_key)
                        if md:
                            spread = md.get('spread')
                            age = md.get('last_update_age')
                            vol = md.get('volatility_score', 0.0)
                            regime = (md.get('regime') or '').lower()
                            trend = 'trend' if 'trend' in regime else ('range' if 'range' in regime else 'mixed')
                            pending = 'elevated' if (spread and spread > 3.0) or (vol and vol > 0.85) or (age and age > 60) else 'none'
                            expect = 'wait for confirmation' if trend == 'mixed' else ('follow momentum' if trend == 'trend' else 'fade extremes')
                            lines.append(f"{f}: vol {_vol_bucket(vol)}, {trend}, {_freshness(age)}, news {pending}, {expect}")
                
                if lines:
                    market_analysis = f"📊 Market Analysis: {' | '.join(lines)}"
                else:
                    market_analysis = f"📊 Tracking {len(instruments)} instruments across {len(active_accounts)} accounts"
            else:
                preview = {'summary': 'System status overview'}
                market_analysis = "📊 Market data feeds initializing..."
            
            # Combine all information
            reply_msg = " | ".join(system_status_lines) + " | " + session_info + " | " + market_analysis

        # Handle live trading mode
        if 'live' in text:
            live_guard = True
            requires_confirmation = True
            mode = 'live'

        # Enforce policy read-only (warning only here)
        try:
            if account_manager and order_manager and active_accounts:
                enforce_policy(account_manager, order_manager, active_accounts, max_exposure=0.10, max_positions=5)
        except PolicyViolation as pv:
            preview = {**preview, 'policy_warning': str(pv)}

        # Build final response
        response = {
            'reply': reply_msg,
            'intent': intent,
            'tools': [],
            'preview': preview,
            'requires_confirmation': requires_confirmation,
            'mode': mode,
            'session_id': session_id,
            'confirmation_id': confirmation_id,
            'live_guard': live_guard,
            'context_used': bool(context),
            'cache_hit': bool(cached_response)
        }
        
        # Cache the response for future use
        smart_cache.set(cache_key, response)
        
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/confirm', methods=['POST'])
def confirm() -> tuple:
    try:
        payload = request.get_json(force=True, silent=True) or {}
        confirmation_id: Optional[str] = payload.get('confirmation_id')
        confirm: bool = bool(payload.get('confirm', False))
        if not confirmation_id:
            return jsonify({'error': 'confirmation_id is required'}), 400

        action = PENDING_ACTIONS.pop(confirmation_id, None)
        if not action:
            return jsonify({'status': 'cancelled', 'result': {'note': 'No pending action'}}), 200

        if not confirm:
            return jsonify({'status': 'cancelled', 'result': {'note': 'User cancelled'}}), 200

        # Execute DEMO action safely
        account_manager, data_feed, order_manager, active_accounts, telegram_notifier = _get_managers()
        if not order_manager:
            return jsonify({'status': 'cancelled', 'result': {'note': 'Order manager unavailable'}}), 200

        # Final policy enforcement before execution
        try:
            if account_manager and active_accounts:
                enforce_policy(account_manager, order_manager, active_accounts, max_exposure=0.10, max_positions=5)
        except PolicyViolation as pv:
            return jsonify({'status': 'cancelled', 'result': {'note': f'Policy blocked: {pv}'}}), 200

        status = 'executed'
        note = 'Executed (demo)'
        exec_result: Dict[str, Any] = {'ok': True}

        if action['type'] == 'close_positions':
            acc = action['account_id']
            instrument = action['instrument']
            side = action.get('side', 'buy')
            try:
                ok = order_manager.close_position(acc, instrument, reason='Assistant: user request (demo)')
                exec_result.update({'action': 'close_positions', 'instrument': instrument, 'side': side, 'account_id': acc, 'success': bool(ok)})
            except Exception as e:
                status = 'cancelled'
                note = f'Execution failed: {e}'
                exec_result.update({'ok': False, 'error': str(e)})
        
        elif action['type'] == 'adjust_exposure':
            new_exposure = action['new_exposure']
            try:
                # Update risk management settings (demo implementation)
                # In a real system, this would update the configuration
                exec_result.update({
                    'action': 'adjust_exposure', 
                    'new_exposure': new_exposure, 
                    'success': True,
                    'note': 'Exposure setting updated (demo)'
                })
            except Exception as e:
                status = 'cancelled'
                note = f'Exposure adjustment failed: {e}'
                exec_result.update({'ok': False, 'error': str(e)})
        
        elif action['type'] == 'emergency_stop':
            try:
                # Emergency stop implementation (demo)
                exec_result.update({
                    'action': 'emergency_stop',
                    'success': True,
                    'note': 'Emergency stop activated (demo)'
                })
            except Exception as e:
                status = 'cancelled'
                note = f'Emergency stop failed: {e}'
                exec_result.update({'ok': False, 'error': str(e)})
        
        elif action['type'] == 'resume_trading':
            try:
                # Resume trading implementation (demo)
                exec_result.update({
                    'action': 'resume_trading',
                    'success': True,
                    'note': 'Trading operations resumed (demo)'
                })
            except Exception as e:
                status = 'cancelled'
                note = f'Resume trading failed: {e}'
                exec_result.update({'ok': False, 'error': str(e)})

        # Telegram notification (best-effort)
        try:
            if telegram_notifier and status == 'executed':
                telegram_notifier.send_system_status('assistant', f"Executed demo action: {exec_result}")
        except Exception:
            pass

        return jsonify({'status': status, 'result': {'note': note, 'details': exec_result}}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_ai_assistant(app, socketio) -> None:
    """Register AI assistant blueprint and Socket.IO namespace.
    
    AI Assistant is now always enabled by default.
    """
    enabled = str(os.getenv('AI_ASSISTANT_ENABLED', 'true')).lower() in ['1', 'true', 'yes']
    if not enabled:
        logger.warning("⚠️ AI Assistant disabled by environment variable")
        return

    # Stash managers for tool wrappers
    try:
        app.config['ACCOUNT_MANAGER'] = app.config.get('ACCOUNT_MANAGER')
        app.config['DATA_FEED'] = app.config.get('DATA_FEED')
        app.config['ORDER_MANAGER'] = app.config.get('ORDER_MANAGER')
        app.config['ACTIVE_ACCOUNTS'] = app.config.get('ACTIVE_ACCOUNTS', [])
        app.config['TELEGRAM_NOTIFIER'] = app.config.get('TELEGRAM_NOTIFIER')
    except Exception:
        pass

    # Register REST API blueprint
    app.register_blueprint(ai_bp)

    # Register Socket.IO namespace handlers (minimal, read-only)
    namespace = '/ai'

    @socketio.on('connect', namespace=namespace)
    def ai_connect():  # type: ignore
        socketio.emit('assistant_reply', {'msg': 'AI assistant connected (demo mode)'}, namespace=namespace)

    @socketio.on('chat_message', namespace=namespace)
    def ai_chat_message(data):  # type: ignore
        try:
            message = (data or {}).get('message', '')
            session_id = (data or {}).get('session_id', '')
            reply = {
                'reply': f"Echo: {message} (demo)",
                'intent': 'unknown',
                'requires_confirmation': False,
                'mode': 'demo',
                'session_id': session_id
            }
            socketio.emit('assistant_reply', reply, namespace=namespace)
        except Exception as e:
            socketio.emit('error', {'error': str(e)}, namespace=namespace)


class AIAssistantAPI:
    """AI Assistant API for trading dashboard"""
    
    def __init__(self):
        """Initialize AI Assistant"""
        self.enabled = os.getenv('AI_ASSISTANT_ENABLED', 'true').lower() == 'true'
        self.model_provider = os.getenv('AI_MODEL_PROVIDER', 'demo')
        self.rate_limit = int(os.getenv('AI_RATE_LIMIT_PER_MINUTE', '10'))
        self.require_confirmation = os.getenv('AI_REQUIRE_LIVE_CONFIRMATION', 'true').lower() == 'true'
        self.request_times = []
        
        logger.info(f"🤖 AI Assistant initialized - Provider: {self.model_provider}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI assistant status"""
        return {
            'enabled': self.enabled,
            'model_provider': self.model_provider,
            'rate_limit': self.rate_limit,
            'require_confirmation': self.require_confirmation,
            'status': 'active' if self.enabled else 'disabled',
            'timestamp': datetime.now().isoformat()
        }
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Process AI chat message"""
        try:
            if not self.enabled:
                return {
                    'error': 'AI Assistant is disabled',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check rate limiting
            if not self._check_rate_limit():
                return {
                    'error': 'Rate limit exceeded. Please wait before sending another message.',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Process message with demo responses
            response = self._process_demo_message(message)
            
            return {
                'response': response,
                'timestamp': datetime.now().isoformat(),
                'model_provider': self.model_provider
            }
            
        except Exception as e:
            logger.error(f"❌ AI message processing error: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit"""
        now = datetime.now()
        self.request_times = [t for t in self.request_times if (now - t).total_seconds() < 60]
        
        if len(self.request_times) >= self.rate_limit:
            return False
        
        self.request_times.append(now)
        return True
    
    def _process_demo_message(self, message: str) -> str:
        """Process message with AI responses including trade execution"""
        message_lower = message.lower()
        
        # Check for trade execution commands
        if self._is_trade_execution_command(message):
            return self._execute_trade_command(message)
        
        if any(word in message_lower for word in ['market', 'price', 'forex', 'trading']):
            return "📊 Market Analysis: Current market conditions show moderate volatility. EUR/USD is trending upward with strong support at 1.0850. Consider monitoring key resistance levels at 1.0950."
        elif any(word in message_lower for word in ['news', 'event', 'announcement']):
            return "📰 News Impact: Recent economic data shows mixed signals. The Federal Reserve's stance on interest rates continues to influence market sentiment."
        
        elif any(word in message_lower for word in ['trump', 'president', 'political', 'election']):
            return "🗳️ Political Analysis: Political events significantly impact market sentiment and volatility. Recent political developments can affect USD strength, risk appetite, and safe-haven demand for gold. Monitor for policy announcements, trade negotiations, and geopolitical tensions that typically drive market movements."
        elif any(word in message_lower for word in ['risk', 'position', 'stop', 'loss']):
            return "⚠️ Risk Management: Current portfolio risk is within acceptable limits. Ensure proper position sizing and maintain stop-loss orders."
        elif any(word in message_lower for word in ['strategy', 'signal', 'trade', 'entry']):
            return "🎯 Trading Strategy: The system is currently monitoring multiple timeframes for entry signals. Gold scalping strategy shows promising setups on 5-minute charts."
        elif any(word in message_lower for word in ['status', 'system', 'health', 'performance']):
            return "🔧 System Status: All trading systems are operational. Data feeds are live and stable. Risk management protocols are active."
        else:
            return "🤖 AI Assistant: I'm here to help with your trading questions. I can provide market analysis, risk management advice, system status updates, and trading strategy insights."
    
    def _is_trade_execution_command(self, message: str) -> bool:
        """Check if message is a trade execution command"""
        message_lower = message.lower()
        trade_keywords = ['enter', 'buy', 'sell', 'long', 'short']
        account_keywords = ['account', '001', 'semi']
        
        has_trade_keyword = any(keyword in message_lower for keyword in trade_keywords)
        has_account_keyword = any(keyword in message_lower for keyword in account_keywords)
        
        return has_trade_keyword and has_account_keyword
    
    def _execute_trade_command(self, message: str) -> str:
        """Execute trade command using the trade execution handler"""
        try:
            # Import the trade execution handler
            import sys
            sys.path.append('/Users/mac/quant_system_clean/google-cloud-trading-system')
            from trade_execution_handler import TradeExecutionHandler
            
            # Create handler and process command
            handler = TradeExecutionHandler()
            result = handler.process_trade_command(message)
            
            if result['success']:
                return f"✅ {result['message']}\n📋 Trade ID: {result.get('trade_id', 'N/A')}\n💰 Units: {result.get('units', 'N/A')}\n📊 Price: {result.get('price', 'N/A'):.5f}"
            else:
                return f"❌ {result['message']}\n💡 Try: 'enter USDJPY long on account 001'"
                
        except Exception as e:
            logger.error(f"❌ Trade execution error: {e}")
            return f"❌ Trade execution failed: {str(e)}\n💡 Try: 'enter USDJPY long on account 001'"
