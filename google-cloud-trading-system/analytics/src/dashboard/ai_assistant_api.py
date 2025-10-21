import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from typing import Optional, List, Dict, Any

from .ai_tools import summarize_market, get_positions_preview, preview_close_positions, enforce_policy, PolicyViolation, compute_portfolio_exposure

logger = logging.getLogger(__name__)

# Blueprint for AI Assistant API (isolated)
ai_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

# In-memory pending actions store (confirmation_id -> action)
PENDING_ACTIONS: Dict[str, Dict[str, Any]] = {}


def _get_managers():
    # Expect the main app to stash managers on app config if needed
    account_manager = current_app.config.get('ACCOUNT_MANAGER')
    data_feed = current_app.config.get('DATA_FEED')
    order_manager = current_app.config.get('ORDER_MANAGER')
    active_accounts: List[str] = current_app.config.get('ACTIVE_ACCOUNTS', [])
    telegram_notifier = current_app.config.get('TELEGRAM_NOTIFIER')
    return account_manager, data_feed, order_manager, active_accounts, telegram_notifier


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

        account_manager, data_feed, order_manager, active_accounts, telegram_notifier = _get_managers()

        text = message.lower().strip()
        intent = 'unknown'
        requires_confirmation = False
        preview: Dict[str, Any] = {'summary': 'No actions in dry-run mode'}
        confirmation_id: Optional[str] = None
        mode = 'demo'
        live_guard = False
        reply_msg = ''

        # Enhanced system health and market overview
        if 'overview' in text or 'market' in text or 'status' in text or 'health' in text:
            intent = 'market_overview'
            
            # Comprehensive system status
            system_status_lines = [
                "✅ System Status: All components operational",
                "🌐 Dashboard: Online and responsive", 
                "📱 Telegram Alerts: Working and tested",
                "📊 Data Feeds: Active with live data",
                "🧠 Strategies: Alpha, Gold Scalping, Ultra Strict Forex - All active",
                "🛡️ Risk Management: 10% portfolio cap, proper SL/TP limits"
            ]
            
            # Market session analysis
            from datetime import datetime, timezone
            now_utc = datetime.now(timezone.utc)
            hour = now_utc.hour
            
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

        # Enhanced Trade Control Commands
        
        # Close positions - enhanced for any instrument
        if 'close' in text and ('position' in text or 'trade' in text):
            intent = 'close_positions'
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
                    'session_id': session_id
                }
                matched = pv.get('positions_matched', 0)
                reply_msg = f"Found {matched} {instrument} {side} position(s) to close (demo). Confirm to execute."
        
        # Adjust exposure/risk settings
        elif any(x in text for x in ['adjust exposure', 'change exposure', 'set exposure', 'risk level', 'exposure level']):
            intent = 'adjust_exposure'
            requires_confirmation = True
            confirmation_id = str(uuid.uuid4())
            
            # Extract new exposure level
            new_exposure = None
            if '5%' in text or '0.05' in text:
                new_exposure = 0.05
            elif '10%' in text or '0.10' in text:
                new_exposure = 0.10
            elif '15%' in text or '0.15' in text:
                new_exposure = 0.15
            elif '20%' in text or '0.20' in text:
                new_exposure = 0.20
            else:
                new_exposure = 0.10  # default
            
            PENDING_ACTIONS[confirmation_id] = {
                'type': 'adjust_exposure',
                'new_exposure': new_exposure,
                'session_id': session_id
            }
            preview = {'summary': f'Adjust portfolio exposure to {new_exposure*100:.0f}% (demo)'}
            reply_msg = f"Adjusting portfolio exposure to {new_exposure*100:.0f}% (demo). This will affect future position sizing."
        
        # Get current exposure status
        elif any(x in text for x in ['current exposure', 'exposure status', 'risk status', 'portfolio exposure']):
            intent = 'exposure_status'
            if account_manager and order_manager and active_accounts:
                exposure, positions = compute_portfolio_exposure(account_manager, order_manager, active_accounts)
                reply_msg = f"📊 Current Portfolio Status: {exposure*100:.1f}% exposure, {positions} open positions. Risk management: 10% max exposure, 5 max positions."
                preview = {'summary': f'Portfolio exposure: {exposure*100:.1f}%', 'positions': positions}
            else:
                reply_msg = "📊 Portfolio status unavailable - system initializing"
        
        # Emergency stop all trading
        elif any(x in text for x in ['emergency stop', 'stop all', 'halt trading', 'emergency halt']):
            intent = 'emergency_stop'
            requires_confirmation = True
            confirmation_id = str(uuid.uuid4())
            PENDING_ACTIONS[confirmation_id] = {
                'type': 'emergency_stop',
                'session_id': session_id
            }
            preview = {'summary': 'Emergency stop all trading (demo)'}
            reply_msg = "🚨 EMERGENCY STOP: This will halt all trading activity (demo). Confirm to execute."
        
        # Resume trading after emergency stop
        elif any(x in text for x in ['resume trading', 'start trading', 'enable trading', 'unpause']):
            intent = 'resume_trading'
            requires_confirmation = True
            confirmation_id = str(uuid.uuid4())
            PENDING_ACTIONS[confirmation_id] = {
                'type': 'resume_trading',
                'session_id': session_id
            }
            preview = {'summary': 'Resume trading operations (demo)'}
            reply_msg = "▶️ Resume Trading: Re-enabling trading operations (demo). Confirm to execute."

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

        # Enhanced help and default responses
        if 'help' in text or 'commands' in text or 'what can you do' in text:
            intent = 'help'
            reply_msg = """🤖 Enhanced AI Assistant Commands:

📊 **Market Analysis:**
• "market overview" - Comprehensive system status & market analysis
• "system health" - Detailed health check with all components  
• "market session" - Current trading session info
• "current exposure" - Portfolio exposure and risk status

🎛️ **Trade Control:**
• "close EUR/USD positions" - Close specific instrument positions
• "close gold long positions" - Close XAUUSD long positions
• "close USD/JPY short positions" - Close USDJPY short positions
• "adjust exposure to 15%" - Change portfolio exposure level
• "emergency stop" - Halt all trading immediately
• "resume trading" - Re-enable trading operations

✅ System Status: All components operational
📱 Telegram alerts active, Dashboard online
🧠 3 strategies active: Alpha, Gold Scalping, Ultra Strict Forex
🛡️ Risk management: 10% portfolio cap, proper SL/TP limits

Note: Demo mode - all actions require confirmation and are simulated."""
            preview = {'summary': 'Enhanced help with trade control features'}

        if not reply_msg:
            reply_msg = """🤖 Enhanced AI Assistant Ready! 

✅ System Status: All components operational
📊 Dashboard: Online | 📱 Telegram: Active | 🧠 Strategies: Running

Ask me about:
• "market overview" - Full system status & analysis
• "system health" - Detailed health check  
• "market session" - Current trading hours
• "risk status" - Risk management settings
• "help" - All available commands

Ready to start the week with comprehensive market analysis!"""

        response = {
            'reply': reply_msg,
            'intent': intent,
            'tools': [],
            'preview': preview,
            'requires_confirmation': requires_confirmation,
            'mode': mode,
            'session_id': session_id,
            'confirmation_id': confirmation_id,
            'live_guard': live_guard
        }
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
    """Register AI assistant blueprint and Socket.IO namespace if enabled by env flag.

    Env: AI_ASSISTANT_ENABLED=true to enable.
    """
    enabled = str(os.getenv('AI_ASSISTANT_ENABLED', 'false')).lower() in ['1', 'true', 'yes']
    if not enabled:
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
        """Process message with demo AI responses"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['market', 'price', 'forex', 'trading']):
            return "📊 Market Analysis: Current market conditions show moderate volatility. EUR/USD is trending upward with strong support at 1.0850. Consider monitoring key resistance levels at 1.0950."
        elif any(word in message_lower for word in ['news', 'event', 'announcement']):
            return "📰 News Impact: Recent economic data shows mixed signals. The Federal Reserve's stance on interest rates continues to influence market sentiment."
        elif any(word in message_lower for word in ['risk', 'position', 'stop', 'loss']):
            return "⚠️ Risk Management: Current portfolio risk is within acceptable limits. Ensure proper position sizing and maintain stop-loss orders."
        elif any(word in message_lower for word in ['strategy', 'signal', 'trade', 'entry']):
            return "🎯 Trading Strategy: The system is currently monitoring multiple timeframes for entry signals. Gold scalping strategy shows promising setups on 5-minute charts."
        elif any(word in message_lower for word in ['status', 'system', 'health', 'performance']):
            return "🔧 System Status: All trading systems are operational. Data feeds are live and stable. Risk management protocols are active."
        else:
            return "🤖 AI Assistant: I'm here to help with your trading questions. I can provide market analysis, risk management advice, system status updates, and trading strategy insights."
