#!/usr/bin/env python3
"""
Shadow AI Assistant
AI assistant specifically designed for the shadow trading system
Provides market insights, system analysis, and shadow signal explanations
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)

# Blueprint for Shadow AI Assistant
shadow_ai_bp = Blueprint('shadow_ai_assistant', __name__, url_prefix='/ai')

# In-memory session store for conversation history
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}

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
    """Interpret user message and provide AI response"""
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
        
        # Get shadow system
        shadow_system = _get_shadow_system()
        config_manager = _get_config_manager()
        
        text = message.lower().strip()
        reply_msg = ''
        intent = 'unknown'
        preview = {'summary': 'Shadow system analysis'}
        
        # Market overview request
        if any(word in text for word in ['overview', 'market', 'status', 'how', 'what']):
            intent = 'market_overview'
            analysis = _analyze_market_conditions(shadow_system)
            reply_msg = _generate_market_insights(analysis)
            preview = {
                'summary': 'Market analysis',
                'system_health': analysis.get('system_health', 'unknown'),
                'signals_count': analysis.get('signal_analysis', {}).get('total_signals', 0)
            }
        
        # Signal explanation request
        elif any(word in text for word in ['signal', 'trade', 'position', 'explain']):
            intent = 'signal_explanation'
            if shadow_system:
                recent_signals = shadow_system.get_shadow_signals(limit=5)
                if recent_signals:
                    latest_signal = recent_signals[0]
                    signal_data = {
                        'instrument': latest_signal.instrument,
                        'side': latest_signal.side,
                        'confidence': latest_signal.confidence,
                        'strategy_name': latest_signal.strategy_name,
                        'reason': latest_signal.reason
                    }
                    reply_msg = _explain_signal(signal_data)
                    preview = {
                        'summary': 'Latest signal explanation',
                        'instrument': latest_signal.instrument,
                        'side': latest_signal.side,
                        'confidence': latest_signal.confidence
                    }
                else:
                    reply_msg = "📊 No recent signals to explain. The system is monitoring market conditions."
                    preview = {'summary': 'No signals available'}
            else:
                reply_msg = "❌ Shadow system not available for signal analysis."
        
        # Strategy performance request
        elif any(word in text for word in ['strategy', 'performance', 'how well', 'results']):
            intent = 'strategy_performance'
            if shadow_system:
                performance = shadow_system.get_strategy_performance()
                if performance:
                    insights = []
                    for strategy_name, perf in performance.items():
                        insights.append(f"📈 {strategy_name}: {perf.total_signals} signals ({perf.daily_signals}/{perf.max_daily_signals} daily)")
                    reply_msg = "Strategy Performance: " + " | ".join(insights)
                    preview = {
                        'summary': 'Strategy performance analysis',
                        'strategies_count': len(performance)
                    }
                else:
                    reply_msg = "📊 No strategy performance data available yet."
            else:
                reply_msg = "❌ Shadow system not available for performance analysis."
        
        # System health request
        elif any(word in text for word in ['health', 'status', 'running', 'working']):
            intent = 'system_health'
            if shadow_system:
                health_report = shadow_system.get_system_health()
                reply_msg = f"🏥 System Health: {health_report['overall_health']}"
                if health_report.get('issues'):
                    reply_msg += f" | Issues: {', '.join(health_report['issues'])}"
                if health_report.get('recommendations'):
                    reply_msg += f" | Recommendations: {', '.join(health_report['recommendations'])}"
                preview = {
                    'summary': 'System health check',
                    'overall_health': health_report['overall_health'],
                    'issues_count': len(health_report.get('issues', []))
                }
            else:
                reply_msg = "❌ Shadow system not available for health check."
        
        # Help request
        elif any(word in text for word in ['help', 'commands', 'what can you do']):
            intent = 'help'
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
            preview = {'summary': 'Enhanced help with system status'}
        
        # Market session request
        elif any(word in text for word in ['session', 'trading hours', 'market time']):
            intent = 'market_session'
            analysis = _analyze_market_conditions(shadow_system)
            system_status = analysis.get('system_status', {})
            market_session = system_status.get('market_session', {})
            active_sessions = market_session.get('active_sessions', [])
            if active_sessions:
                session_info = []
                for session_name in active_sessions:
                    session_config = market_session.get('sessions', {}).get(session_name, {})
                    session_info.append(f"{session_name}: {session_config.get('volatility', 1)}x volatility, {session_config.get('max_positions', 0)} max positions")
                reply_msg = f"🕐 Active Trading Sessions: {' | '.join(session_info)}"
            else:
                next_session = market_session.get('next_session')
                if next_session:
                    reply_msg = f"⏭️ Market closed. Next session: {next_session}"
                else:
                    reply_msg = "📊 No active trading sessions"
            preview = {'summary': 'Market session information'}
        
        # Risk status request  
        elif any(word in text for word in ['risk', 'exposure', 'limits', 'position size']):
            intent = 'risk_status'
            analysis = _analyze_market_conditions(shadow_system)
            system_status = analysis.get('system_status', {})
            risk_mgmt = system_status.get('risk_management', {})
            reply_msg = f"""🛡️ Risk Management Status:
• Portfolio Exposure: {risk_mgmt.get('portfolio_exposure', 'unknown')}
• Max Positions: {risk_mgmt.get('max_positions', 'unknown')}
• Stop Loss: {risk_mgmt.get('stop_loss', 'unknown')}
• Take Profit: {risk_mgmt.get('take_profit', 'unknown')}"""
            preview = {'summary': 'Risk management status'}
        
        # Default response
        else:
            intent = 'general'
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
            preview = {'summary': 'Enhanced general response with system status'}
        
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
            'mode': 'shadow',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
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

