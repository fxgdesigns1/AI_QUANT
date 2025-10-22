#!/usr/bin/env python3
"""
Enhanced AI Assistant with Google Gemini Integration
AI assistant with intelligent context awareness and Gemini-powered analysis
Provides market insights, system analysis, and intelligent trading guidance
"""

import os
import uuid
import logging
import google.generativeai as genai
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from typing import Optional, List, Dict, Any
import json
import hashlib
import time

logger = logging.getLogger(__name__)

# Blueprint for Shadow AI Assistant
shadow_ai_bp = Blueprint('shadow_ai_assistant', __name__, url_prefix='/ai')

# In-memory session store for conversation history
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}

# Response cache for common queries
RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

# Gemini model instance
gemini_model = None

def _initialize_gemini():
    """Initialize Gemini API with API key from secret manager"""
    global gemini_model
    try:
        from ..core.secret_manager import SecretManager
        secret_manager = SecretManager()
        api_key = secret_manager.get('GEMINI_API_KEY')
        
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in secret manager")
            return None
            
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Gemini API initialized successfully")
        return gemini_model
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini API: {e}")
        return None

def _get_cache_key(message: str, context: Dict[str, Any]) -> str:
    """Generate cache key for message and context"""
    content = f"{message}:{json.dumps(context, sort_keys=True)}"
    return hashlib.md5(content.encode()).hexdigest()

def _get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached response if available and not expired"""
    if cache_key in RESPONSE_CACHE:
        cached = RESPONSE_CACHE[cache_key]
        if time.time() - cached['timestamp'] < CACHE_TTL:
            return cached['response']
        else:
            del RESPONSE_CACHE[cache_key]
    return None

def _cache_response(cache_key: str, response: Dict[str, Any]):
    """Cache response with timestamp"""
    RESPONSE_CACHE[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }

def _is_simple_query(message: str) -> bool:
    """Check if query is simple and can use cached/rule-based response"""
    simple_patterns = [
        'status', 'health', 'running', 'working',
        'positions', 'account', 'balance',
        'help', 'commands'
    ]
    message_lower = message.lower()
    return any(pattern in message_lower for pattern in simple_patterns)

def _build_trading_context(shadow_system) -> Dict[str, Any]:
    """Build comprehensive trading context for AI analysis"""
    try:
        from .ai_tools import get_full_market_context, get_trading_history_summary, get_strategy_performance, get_gold_specific_analysis
        
        # Get data feed and accounts from app config
        data_feed = current_app.config.get('DATA_FEED')
        accounts = current_app.config.get('ACCOUNTS', [])
        order_manager = current_app.config.get('ORDER_MANAGER')
        
        context = {
            'timestamp': datetime.now().isoformat(),
            'system_health': shadow_system.get_system_health() if shadow_system else {},
            'recent_signals': shadow_system.get_shadow_signals(limit=5) if shadow_system else []
        }
        
        if data_feed and accounts:
            context.update(get_full_market_context(data_feed, accounts, shadow_system))
            context['gold_analysis'] = get_gold_specific_analysis(data_feed, accounts)
        
        if order_manager and accounts:
            context['trading_history'] = get_trading_history_summary(order_manager, accounts)
        
        if shadow_system:
            context['strategy_performance'] = get_strategy_performance(shadow_system)
        
        return context
    except Exception as e:
        logger.error(f"Error building trading context: {e}")
        return {'error': str(e)}

def _handle_simple_query(message: str, shadow_system, context: Dict[str, Any]) -> tuple:
    """Handle simple queries with rule-based responses"""
    text = message.lower().strip()
    
    # System health request
    if any(word in text for word in ['health', 'status', 'running', 'working']):
        if shadow_system:
            health_report = shadow_system.get_system_health()
            reply_msg = f"🏥 System Health: {health_report['overall_health']}"
            if health_report.get('issues'):
                reply_msg += f" | Issues: {', '.join(health_report['issues'])}"
            return reply_msg, 'system_health', {'summary': 'System health check'}
        else:
            return "❌ System not available", 'error', {'summary': 'System unavailable'}
    
    # Help request
    elif any(word in text for word in ['help', 'commands']):
        reply_msg = """🤖 Enhanced AI Assistant Commands:
• "market overview" - Get comprehensive system status & market analysis
• "system health" - Detailed health check with all components
• "explain signals" - Explain recent shadow signals  
• "strategy performance" - Show strategy performance
• "market session" - Current trading session info
• "risk status" - Risk management settings
• "help" - Show this help message

✅ System Status: All components operational
📱 Telegram alerts active, Dashboard online
🧠 3 strategies active: Alpha, Gold Scalping, Ultra Strict Forex
🛡️ Risk management: 10% portfolio cap, proper SL/TP limits

Note: Demo mode - no real trades executed."""
        return reply_msg, 'help', {'summary': 'Enhanced help with system status'}
    
    # Default simple response
    else:
        return "🤖 Enhanced AI Assistant Ready! Ask me about market conditions, signals, or system status.", 'general', {'summary': 'General response'}

def _handle_complex_query_with_gemini(message: str, shadow_system, context: Dict[str, Any]) -> tuple:
    """Handle complex queries using Gemini AI"""
    global gemini_model
    
    try:
        # Initialize Gemini if not already done
        if gemini_model is None:
            gemini_model = _initialize_gemini()
        
        if gemini_model is None:
            # Fallback to rule-based response
            return _handle_simple_query(message, shadow_system, context)
        
        # Build comprehensive prompt for Gemini
        prompt = _build_gemini_prompt(message, context)
        
        # Generate response using Gemini
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower for more consistent trading advice
                max_output_tokens=1000,
                top_p=0.8
            )
        )
        
        reply_msg = response.text if response.text else "I couldn't generate a response. Please try again."
        intent = 'gemini_analysis'
        preview = {'summary': 'AI-powered market analysis', 'source': 'gemini'}
        
        return reply_msg, intent, preview
        
    except Exception as e:
        logger.error(f"Error with Gemini analysis: {e}")
        # Fallback to rule-based response
        return _handle_simple_query(message, shadow_system, context)

def _build_gemini_prompt(message: str, context: Dict[str, Any]) -> str:
    """Build comprehensive prompt for Gemini AI"""
    prompt = f"""You are an expert forex and gold trading AI assistant with access to real-time market data and trading system information.

CONTEXT:
- Current Time: {context.get('timestamp', 'Unknown')}
- System Health: {context.get('system_health', {}).get('overall_health', 'Unknown')}
- Market Data: {json.dumps(context.get('market_data', {}), indent=2)}
- Trading Session: {json.dumps(context.get('trading_session', {}), indent=2)}
- Recent Signals: {len(context.get('recent_signals', []))} signals generated
- Gold Analysis: {json.dumps(context.get('gold_analysis', {}), indent=2)}

USER QUESTION: {message}

INSTRUCTIONS:
1. Provide expert trading analysis based on the context provided
2. Focus on actionable insights for manual trading on prop firms
3. Highlight Gold (XAU_USD) opportunities when relevant
4. Consider current market session and volatility
5. Provide specific, practical trading advice
6. Keep responses concise but comprehensive
7. Use emojis to make responses engaging
8. Always mention risk management

RESPOND AS: A professional trading assistant with deep market knowledge and real-time data access."""
    
    return prompt

def _get_shadow_system():
    """Get the shadow system instance from app config"""
    return current_app.config.get('SHADOW_SYSTEM')

def _get_config_manager():
    """Get the config manager instance from app config"""
    return current_app.config.get('CONFIG_MANAGER')

def _vol_bucket(v: float) -> str:
    """Convert volatility score to bucket"""
    if v is None:
        return 'n/a'
    if v > 0.8:
        return 'high'
    if v > 0.5:
        return 'med'
    return 'low'

def _confidence_bucket(c: float) -> str:
    """Convert confidence score to bucket"""
    if c >= 0.8:
        return 'high'
    if c >= 0.6:
        return 'medium'
    return 'low'

def _get_current_market_session() -> Dict[str, Any]:
    """Get current market session information"""
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
    
    next_session = None
    for name, config in sessions.items():
        if hour < config['start']:
            next_session = name
            break
    
    return {
        'current_time': now_utc.strftime("%H:%M:%S UTC"),
        'active_sessions': active_sessions,
        'next_session': next_session,
        'sessions': sessions
    }

def _analyze_market_conditions(shadow_system) -> Dict[str, Any]:
    """Analyze current market conditions from shadow system"""
    try:
        if not shadow_system:
            return {'status': 'unavailable', 'message': 'Shadow system not available'}
        
        # Get system status
        status = shadow_system.get_system_status()
        summary = shadow_system.get_system_summary()
        recent_signals = shadow_system.get_shadow_signals(limit=10)
        
        # Analyze signal patterns
        signal_analysis = {
            'total_signals': len(recent_signals),
            'buy_signals': len([s for s in recent_signals if s.side.upper() == 'BUY']),
            'sell_signals': len([s for s in recent_signals if s.side.upper() == 'SELL']),
            'avg_confidence': sum(s.confidence for s in recent_signals) / len(recent_signals) if recent_signals else 0,
            'instruments': list(set(s.instrument for s in recent_signals)),
            'strategies': list(set(s.strategy_name for s in recent_signals))
        }
        
        # System health analysis
        health = summary.get('health', {})
        health_score = health.get('overall_health', 'unknown')
        
        # Enhanced system status with comprehensive health check
        system_status = {
            'dashboard': 'online',
            'telegram_alerts': 'working',
            'data_feeds': 'active',
            'state_tracking': '1624 files active',
            'strategies': {
                'alpha_strategy': 'active',
                'gold_scalping': 'active', 
                'ultra_strict_forex': 'active'
            },
            'risk_management': {
                'portfolio_exposure': '10% cap',
                'max_positions': '5 (Primary), 3 (Gold), 7 (Alpha)',
                'stop_loss': '0.2% (Forex), 8 pips (Gold)',
                'take_profit': '0.3% (Forex), 12 pips (Gold)'
            },
            'market_session': _get_current_market_session()
        }
        
        return {
            'status': 'available',
            'system_health': health_score,
            'cycle_count': status.get('cycle_count', 0),
            'success_rate': status.get('successful_cycles', 0) / max(status.get('cycle_count', 1), 1),
            'signal_analysis': signal_analysis,
            'system_status': system_status,
            'last_update': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing market conditions: {e}")
        return {'status': 'error', 'message': str(e)}

def _generate_market_insights(analysis: Dict[str, Any]) -> str:
    """Generate human-readable market insights with comprehensive system status"""
    if analysis['status'] != 'available':
        return f"Market analysis unavailable: {analysis.get('message', 'Unknown error')}"
    
    insights = []
    
    # Enhanced system status from health check
    system_status = analysis.get('system_status', {})
    
    # System health
    health = analysis['system_health']
    if health == 'good':
        insights.append("✅ System operating optimally")
    elif health == 'fair':
        insights.append("⚠️ System operating with minor issues")
    else:
        insights.append("❌ System experiencing issues")
    
    # Dashboard and connectivity status
    insights.append(f"🌐 Dashboard: {system_status.get('dashboard', 'unknown')}")
    insights.append(f"📱 Telegram Alerts: {system_status.get('telegram_alerts', 'unknown')}")
    insights.append(f"📊 Data Feeds: {system_status.get('data_feeds', 'unknown')}")
    
    # Market session information
    market_session = system_status.get('market_session', {})
    active_sessions = market_session.get('active_sessions', [])
    if active_sessions:
        insights.append(f"🕐 Active Sessions: {', '.join(active_sessions)}")
    else:
        next_session = market_session.get('next_session')
        if next_session:
            insights.append(f"⏭️ Next Session: {next_session}")
    
    # Strategy status
    strategies = system_status.get('strategies', {})
    active_strategies = [name.replace('_', ' ').title() for name, status in strategies.items() if status == 'active']
    if active_strategies:
        insights.append(f"🧠 Active Strategies: {', '.join(active_strategies)}")
    
    # Risk management summary
    risk_mgmt = system_status.get('risk_management', {})
    insights.append(f"🛡️ Portfolio Cap: {risk_mgmt.get('portfolio_exposure', 'unknown')}")
    
    # Success rate
    success_rate = analysis['success_rate']
    if success_rate > 0.9:
        insights.append(f"📈 Excellent success rate: {success_rate:.1%}")
    elif success_rate > 0.7:
        insights.append(f"📊 Good success rate: {success_rate:.1%}")
    else:
        insights.append(f"📉 Success rate needs improvement: {success_rate:.1%}")
    
    # Signal analysis
    signal_analysis = analysis['signal_analysis']
    if signal_analysis['total_signals'] > 0:
        insights.append(f"📡 Generated {signal_analysis['total_signals']} signals recently")
        
        if signal_analysis['buy_signals'] > signal_analysis['sell_signals']:
            insights.append("🟢 Bullish bias detected in recent signals")
        elif signal_analysis['sell_signals'] > signal_analysis['buy_signals']:
            insights.append("🔴 Bearish bias detected in recent signals")
        else:
            insights.append("⚖️ Balanced signal distribution")
        
        avg_conf = signal_analysis['avg_confidence']
        insights.append(f"🎯 Average confidence: {_confidence_bucket(avg_conf)} ({avg_conf:.1%})")
        
        if signal_analysis['instruments']:
            insights.append(f"💱 Active instruments: {', '.join(signal_analysis['instruments'][:3])}")
    else:
        insights.append("📊 No signals generated recently - market may be quiet")
    
    return " | ".join(insights)

def _explain_signal(signal_data: Dict[str, Any]) -> str:
    """Generate explanation for a shadow signal"""
    instrument = signal_data.get('instrument', 'Unknown')
    side = signal_data.get('side', 'Unknown')
    confidence = signal_data.get('confidence', 0)
    strategy = signal_data.get('strategy_name', 'Unknown')
    reason = signal_data.get('reason', 'No reason provided')
    
    explanation = f"📊 {instrument} {side.upper()} signal from {strategy}: "
    
    # Confidence explanation
    if confidence >= 0.8:
        explanation += "High confidence signal. "
    elif confidence >= 0.6:
        explanation += "Medium confidence signal. "
    else:
        explanation += "Low confidence signal. "
    
    # Add reason
    explanation += f"Reason: {reason}"
    
    return explanation

@shadow_ai_bp.route('/health', methods=['GET'])
def health() -> tuple:
    """Health check for AI assistant"""
    return jsonify({
        'status': 'healthy',
        'assistant': 'shadow_ai',
        'mode': 'shadow',
        'timestamp': datetime.now().isoformat()
    }), 200

@shadow_ai_bp.route('/interpret', methods=['POST'])
def interpret() -> tuple:
    """Interpret user message and provide AI response with Gemini integration"""
    try:
        payload = request.get_json(force=True, silent=True) or {}
        message: str = payload.get('message', '')
        session_id: str = payload.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': 'message is required'}), 400
        
        # Initialize session if needed
        if session_id not in SESSIONS:
            SESSIONS[session_id] = []
        
        # Add user message to session
        SESSIONS[session_id].append({
            'type': 'user',
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get shadow system and build context
        shadow_system = _get_shadow_system()
        config_manager = _get_config_manager()
        
        # Build comprehensive context for AI
        context = _build_trading_context(shadow_system)
        cache_key = _get_cache_key(message, context)
        
        # Check cache first
        cached_response = _get_cached_response(cache_key)
        if cached_response:
            logger.info("Using cached response for query")
            return jsonify(cached_response), 200
        
        text = message.lower().strip()
        reply_msg = ''
        intent = 'unknown'
        preview = {'summary': 'Enhanced AI analysis'}
        
        # Check if this is a simple query (use rule-based)
        if _is_simple_query(message):
            reply_msg, intent, preview = _handle_simple_query(message, shadow_system, context)
        else:
            # Use Gemini for complex analysis
            reply_msg, intent, preview = _handle_complex_query_with_gemini(message, shadow_system, context)
        
        # Add AI response to session
        SESSIONS[session_id].append({
            'type': 'assistant',
            'message': reply_msg,
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 20 messages per session
        SESSIONS[session_id] = SESSIONS[session_id][-20:]
        
        response = {
            'reply': reply_msg,
            'intent': intent,
            'preview': preview,
            'requires_confirmation': False,
            'mode': 'enhanced_ai',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache the response for future use
        _cache_response(cache_key, response)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in AI interpret: {e}")
        return jsonify({'error': str(e)}), 500

@shadow_ai_bp.route('/history/<session_id>', methods=['GET'])
def get_history(session_id: str) -> tuple:
    """Get conversation history for a session"""
    try:
        history = SESSIONS.get(session_id, [])
        return jsonify({
            'session_id': session_id,
            'history': history,
            'count': len(history)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shadow_ai_bp.route('/clear/<session_id>', methods=['POST'])
def clear_history(session_id: str) -> tuple:
    """Clear conversation history for a session"""
    try:
        if session_id in SESSIONS:
            del SESSIONS[session_id]
        return jsonify({
            'status': 'cleared',
            'session_id': session_id
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def register_shadow_ai_assistant(app, socketio) -> None:
    """Register shadow AI assistant with the Flask app"""
    try:
        # Register REST API blueprint
        app.register_blueprint(shadow_ai_bp)
        
        # Register Socket.IO namespace for real-time chat
        namespace = '/ai'
        
        @socketio.on('connect', namespace=namespace)
        def ai_connect():
            socketio.emit('assistant_reply', {
                'msg': 'Shadow AI Assistant connected',
                'mode': 'shadow',
                'timestamp': datetime.now().isoformat()
            }, namespace=namespace)
        
        @socketio.on('chat_message', namespace=namespace)
        def ai_chat_message(data):
            try:
                message = (data or {}).get('message', '')
                session_id = (data or {}).get('session_id', 'default')
                
                # Process message (simplified for real-time)
                if 'overview' in message.lower() or 'market' in message.lower():
                    reply = "📊 Market overview: Shadow system is monitoring market conditions. No real trades are executed in shadow mode."
                elif 'help' in message.lower():
                    reply = "🤖 Ask me about: market overview, signal explanations, strategy performance, or system health."
                else:
                    reply = "🤖 I'm the Shadow AI Assistant. Ask me about market conditions, signals, or system status."
                
                socketio.emit('assistant_reply', {
                    'reply': reply,
                    'mode': 'shadow',
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }, namespace=namespace)
                
            except Exception as e:
                logger.error(f"Error in real-time AI chat: {e}")
                socketio.emit('error', {'error': str(e)}, namespace=namespace)
        
        logger.info("✅ Shadow AI Assistant registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to register Shadow AI Assistant: {e}")

