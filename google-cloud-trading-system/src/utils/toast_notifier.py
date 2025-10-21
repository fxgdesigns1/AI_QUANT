"""
Toast Notification Utility
Emits real-time toast notifications to frontend dashboards via WebSocket
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Global socketio instance (will be set by main.py)
_socketio = None


def initialize_toast_notifier(socketio_instance):
    """
    Initialize the toast notifier with SocketIO instance
    
    Args:
        socketio_instance: Flask-SocketIO instance from main.py
    """
    global _socketio
    _socketio = socketio_instance
    logger.info("✅ Toast notifier initialized")


def emit_toast(message: str, toast_type: str = 'info', duration: int = 3000, room: Optional[str] = None):
    """
    Emit a toast notification to all connected dashboard clients
    
    Args:
        message (str): The message to display in the toast
        toast_type (str): Type of toast - 'success', 'error', 'warning', or 'info'
        duration (int): Duration in milliseconds (default: 3000, use 0 for no auto-dismiss)
        room (str, optional): Specific room to broadcast to (default: all clients)
    
    Example:
        emit_toast("Trade executed successfully!", 'success')
        emit_toast("Connection lost", 'error', duration=5000)
    """
    if _socketio is None:
        logger.warning("⚠️ Toast notifier not initialized - cannot emit toast")
        return False
    
    # Validate toast type
    valid_types = ['success', 'error', 'warning', 'info']
    if toast_type not in valid_types:
        logger.warning(f"⚠️ Invalid toast type '{toast_type}', using 'info'")
        toast_type = 'info'
    
    try:
        payload = {
            'message': message,
            'type': toast_type,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        # Emit to all clients or specific room
        if room:
            _socketio.emit('toast_notification', payload, room=room)
        else:
            _socketio.emit('toast_notification', payload, broadcast=True)
        
        logger.debug(f"📢 Toast emitted: [{toast_type}] {message}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to emit toast: {e}")
        return False


def emit_success_toast(message: str, duration: int = 3000, room: Optional[str] = None):
    """Emit a success toast (green) - for successful operations"""
    return emit_toast(message, 'success', duration, room)


def emit_error_toast(message: str, duration: int = 5000, room: Optional[str] = None):
    """Emit an error toast (red) - for errors and failures"""
    return emit_toast(message, 'error', duration, room)


def emit_warning_toast(message: str, duration: int = 4000, room: Optional[str] = None):
    """Emit a warning toast (yellow) - for warnings and cautions"""
    return emit_toast(message, 'warning', duration, room)


def emit_info_toast(message: str, duration: int = 3000, room: Optional[str] = None):
    """Emit an info toast (blue) - for informational messages"""
    return emit_toast(message, 'info', duration, room)


# Convenience functions for common trading events
def toast_trade_executed(instrument: str, side: str, price: float):
    """Toast for successful trade execution"""
    return emit_success_toast(f"✅ Trade executed: {instrument} {side} @ {price}")


def toast_trade_error(instrument: str, error_msg: str):
    """Toast for trade execution errors"""
    return emit_error_toast(f"❌ Trade failed: {instrument} - {error_msg}")


def toast_signal_generated(instrument: str, signal_type: str):
    """Toast for new trading signals"""
    return emit_info_toast(f"🎯 Signal: {instrument} {signal_type}")


def toast_risk_alert(message: str):
    """Toast for risk management alerts"""
    return emit_warning_toast(f"⚠️ Risk Alert: {message}")


def toast_system_event(message: str, is_error: bool = False):
    """Toast for system events (startup, shutdown, errors)"""
    if is_error:
        return emit_error_toast(f"🚨 System: {message}")
    else:
        return emit_info_toast(f"🔧 System: {message}")


def toast_connection_status(connected: bool, service: str = "OANDA"):
    """Toast for connection status changes"""
    if connected:
        return emit_success_toast(f"✅ {service} connected")
    else:
        return emit_error_toast(f"❌ {service} disconnected")


def toast_ai_action(action: str, dry_run: bool = False):
    """Toast for AI assistant actions"""
    if dry_run:
        return emit_warning_toast(f"🤖 AI (Dry-run): {action}")
    else:
        return emit_info_toast(f"🤖 AI: {action}")


# Get socketio instance (for manual usage if needed)
def get_socketio():
    """Get the SocketIO instance"""
    return _socketio



