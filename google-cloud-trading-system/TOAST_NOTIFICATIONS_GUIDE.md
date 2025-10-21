# 🍞 Toast Notifications System - User Guide

## Overview

The Toast Notification System provides instant visual feedback for trading events, system alerts, and user actions across all dashboard interfaces. Toasts appear as elegant pop-up messages in the top-right corner, styled to match your purple/dark gradient theme.

---

## ✨ Features

- **Real-time Notifications**: WebSocket-powered instant updates
- **4 Toast Types**: Success, Error, Warning, Info
- **Auto-dismissal**: Configurable duration (default: 3 seconds)
- **Manual Close**: Close button on each toast
- **Smart Stacking**: Multiple toasts stack beautifully
- **Mobile Responsive**: Works on all devices
- **Non-intrusive**: Doesn't block the dashboard
- **Theme-matched**: Purple/dark gradient styling

---

## 🎨 Toast Types

### Success Toast (Green) ✅
**Use for**: Successful operations, completed actions
```python
from src.utils.toast_notifier import emit_success_toast
emit_success_toast("Trade executed successfully!")
```

### Error Toast (Red) ❌
**Use for**: Errors, failures, critical issues
```python
from src.utils.toast_notifier import emit_error_toast
emit_error_toast("Failed to connect to OANDA", duration=5000)
```

### Warning Toast (Yellow) ⚠️
**Use for**: Warnings, cautions, approaching limits
```python
from src.utils.toast_notifier import emit_warning_toast
emit_warning_toast("Approaching daily trade limit")
```

### Info Toast (Blue) ℹ️
**Use for**: Informational messages, status updates
```python
from src.utils.toast_notifier import emit_info_toast
emit_info_toast("Scanner started successfully")
```

---

## 🚀 Quick Start

### For Developers: Adding Toasts to Backend Code

#### 1. Import the toast notifier
```python
from src.utils.toast_notifier import emit_toast, emit_success_toast
```

#### 2. Emit a toast notification
```python
# Basic usage
emit_toast("Your message here", 'success')

# With custom duration (in milliseconds)
emit_toast("Connection lost", 'error', duration=5000)

# Using convenience functions
emit_success_toast("Order placed!")
emit_error_toast("API error occurred")
emit_warning_toast("Risk limit reached")
emit_info_toast("System started")
```

#### 3. That's it! The toast will appear on all connected dashboards

---

## 📋 Common Use Cases

### Trade Execution
```python
from src.utils.toast_notifier import toast_trade_executed, toast_trade_error

# Successful trade
toast_trade_executed("EUR_USD", "BUY", 1.0850)
# Shows: "✅ Trade executed: EUR_USD BUY @ 1.085"

# Failed trade
toast_trade_error("GBP_USD", "Insufficient margin")
# Shows: "❌ Trade failed: GBP_USD - Insufficient margin"
```

### Trading Signals
```python
from src.utils.toast_notifier import toast_signal_generated

toast_signal_generated("XAU_USD", "STRONG BUY")
# Shows: "🎯 Signal: XAU_USD STRONG BUY"
```

### Risk Alerts
```python
from src.utils.toast_notifier import toast_risk_alert

toast_risk_alert("Daily loss limit reached")
# Shows: "⚠️ Risk Alert: Daily loss limit reached"
```

### System Events
```python
from src.utils.toast_notifier import toast_system_event

# Normal system event
toast_system_event("Scanner started")
# Shows: "🔧 System: Scanner started"

# Error event
toast_system_event("Database connection lost", is_error=True)
# Shows: "🚨 System: Database connection lost"
```

### Connection Status
```python
from src.utils.toast_notifier import toast_connection_status

# Connected
toast_connection_status(True, "OANDA")
# Shows: "✅ OANDA connected"

# Disconnected
toast_connection_status(False, "OANDA")
# Shows: "❌ OANDA disconnected"
```

### AI Assistant Actions
```python
from src.utils.toast_notifier import toast_ai_action

# Live action
toast_ai_action("Placed 3 trades based on signals")
# Shows: "🤖 AI: Placed 3 trades based on signals"

# Dry-run action
toast_ai_action("Would place 3 trades", dry_run=True)
# Shows: "🤖 AI (Dry-run): Would place 3 trades"
```

---

## 🎮 Testing Toasts

### In Browser Console
Open any dashboard and run:
```javascript
// Test all toast types
testToasts()

// Individual toasts
showSuccessToast("This is a success!")
showErrorToast("This is an error!")
showWarningToast("This is a warning!")
showInfoToast("This is info!")
```

### From Python (Flask App Running)
```bash
# Run the test script
python3 test_toast_system.py

# Or test live emissions
python3 -c "from test_toast_system import test_live_emissions; test_live_emissions()"
```

---

## 🔧 Advanced Usage

### Custom Duration
```python
# Toast stays for 10 seconds
emit_toast("Important message", 'warning', duration=10000)

# Toast doesn't auto-dismiss (user must close manually)
emit_toast("Critical alert", 'error', duration=0)
```

### Room-specific Broadcasts
```python
# Send to specific room (if using Socket.IO rooms)
emit_toast("Admin message", 'info', room='admin_room')
```

### Conditional Toasts
```python
# Only show toast in certain conditions
if trade_successful:
    emit_success_toast(f"Trade executed: {instrument}")
else:
    emit_error_toast(f"Trade failed: {error_message}")
```

---

## 📍 Integration Points

### Where Toasts Are Already Integrated

✅ **All 9 Dashboard Templates**
- dashboard_fixed.html (Main Dashboard)
- signals_dashboard.html
- strategies_dashboard.html
- status_dashboard.html
- config_dashboard.html
- insights_dashboard.html
- trade_manager_view.html
- trade_manager_web.html
- strategy_switcher.html

✅ **Backend Systems**
- Flask main.py (WebSocket handler)
- Toast notifier utility (src/utils/toast_notifier.py)
- Component template (src/templates/components/toast_notifications.html)

### Recommended Integration Points (Add Your Own)

You can add toast notifications to:

1. **Trade Execution** (`src/core/oanda_client.py`)
   - After order placement
   - On trade errors
   - Position updates

2. **Scanner** (`src/core/candle_based_scanner.py`)
   - Signal generation
   - Scan completion
   - Strategy activation

3. **Risk Manager** (`src/core/risk_manager.py`)
   - Risk limit warnings
   - Exposure alerts
   - Drawdown notifications

4. **AI Assistant** (`src/dashboard/ai_assistant_api.py`)
   - Action confirmations
   - Dry-run notifications
   - Error messages

5. **News Integration** (`src/news/`)
   - High-impact news alerts
   - Economic calendar events

---

## 🐛 Troubleshooting

### Toast Doesn't Appear

**Problem**: Toast notifications not showing
**Solutions**:
1. Check browser console for errors
2. Verify Socket.IO is connected: `window.socket.connected`
3. Ensure Flask app is running
4. Check if Bootstrap is loaded: `typeof bootstrap !== 'undefined'`

### Multiple Toasts Overlap

**Problem**: Toasts stacking incorrectly
**Solution**: This is normal behavior - toasts stack vertically. If too many appear at once, they'll queue automatically.

### Toast Appears But Disappears Immediately

**Problem**: Duration too short
**Solution**:
```python
# Increase duration
emit_toast("Message", 'info', duration=5000)  # 5 seconds
```

### WebSocket Connection Issues

**Problem**: `Socket.IO not loaded` message in console
**Solutions**:
1. Verify Socket.IO CDN is in template head:
   ```html
   <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
   ```
2. Check network tab for blocked requests
3. Ensure Flask-SocketIO is initialized in main.py

### Styling Doesn't Match Theme

**Problem**: Toast colors look wrong
**Solution**: Check `toast_notifications.html` CSS variables match your theme colors.

---

## 📊 Performance

- **Lightweight**: ~9KB component file
- **Fast**: Instant WebSocket delivery
- **Efficient**: Auto-cleanup after dismissal
- **Scalable**: Handles 100+ toasts without lag

---

## 🔒 Security

- **No User Input**: Backend controls all messages
- **XSS Protected**: Messages are escaped
- **WebSocket Validated**: Only authorized connections
- **No PII**: Avoid sending sensitive data in toasts

---

## 🎯 Best Practices

### DO ✅
- Use appropriate toast types for the context
- Keep messages concise (under 100 characters)
- Add emoji for visual clarity (✅❌⚠️ℹ️)
- Test toasts before deploying
- Use meaningful messages that help users

### DON'T ❌
- Don't spam toasts (limit to important events)
- Don't put sensitive data in toasts
- Don't use toasts for critical confirmations (use modals)
- Don't make toasts stay forever (use 0 duration sparingly)
- Don't ignore toast types (use correct severity)

---

## 📖 API Reference

### Main Functions

#### `emit_toast(message, toast_type, duration, room)`
Base function for emitting toasts.

**Parameters**:
- `message` (str): Toast message text
- `toast_type` (str): 'success', 'error', 'warning', or 'info'
- `duration` (int): Duration in milliseconds (default: 3000)
- `room` (str, optional): Specific Socket.IO room

**Returns**: `bool` - True if successful

#### `emit_success_toast(message, duration, room)`
Emit a success toast (green).

#### `emit_error_toast(message, duration, room)`
Emit an error toast (red).

#### `emit_warning_toast(message, duration, room)`
Emit a warning toast (yellow).

#### `emit_info_toast(message, duration, room)`
Emit an info toast (blue).

### Convenience Functions

#### `toast_trade_executed(instrument, side, price)`
Toast for successful trade execution.

#### `toast_trade_error(instrument, error_msg)`
Toast for trade execution errors.

#### `toast_signal_generated(instrument, signal_type)`
Toast for new trading signals.

#### `toast_risk_alert(message)`
Toast for risk management alerts.

#### `toast_system_event(message, is_error)`
Toast for system events.

#### `toast_connection_status(connected, service)`
Toast for connection status changes.

#### `toast_ai_action(action, dry_run)`
Toast for AI assistant actions.

---

## 🎨 Customization

### Changing Toast Colors

Edit `src/templates/components/toast_notifications.html`:

```css
/* Success Toast */
.custom-toast.toast-success {
    border-left: 4px solid #YOUR_COLOR;
}

/* Error Toast */
.custom-toast.toast-error {
    border-left: 4px solid #YOUR_COLOR;
}

/* Warning Toast */
.custom-toast.toast-warning {
    border-left: 4px solid #YOUR_COLOR;
}

/* Info Toast */
.custom-toast.toast-info {
    border-left: 4px solid #YOUR_COLOR;
}
```

### Changing Toast Position

```css
#toast-container {
    top: 20px;    /* Distance from top */
    right: 20px;  /* Distance from right */
    /* For bottom-right: */
    /* bottom: 20px; top: auto; */
}
```

### Changing Default Duration

In your Python code:
```python
# Change default for all toasts
DEFAULT_DURATION = 5000  # 5 seconds
emit_toast(message, type, duration=DEFAULT_DURATION)
```

---

## 📞 Support

If you encounter issues:

1. Run the test script: `python3 test_toast_system.py`
2. Check browser console for errors
3. Verify Flask app is running
4. Review this guide for troubleshooting tips

---

## ✅ Checklist for Adding Toasts to New Code

- [ ] Import toast_notifier functions
- [ ] Identify key events that need notifications
- [ ] Choose appropriate toast type (success/error/warning/info)
- [ ] Keep messages concise and actionable
- [ ] Test locally before deploying
- [ ] Verify toast appears on dashboard
- [ ] Check message is clear and helpful
- [ ] Ensure no sensitive data in message

---

## 🎉 You're Ready!

The toast notification system is fully integrated and ready to use. Start adding toasts to your trading events and enjoy instant visual feedback!

**Remember**: Toasts enhance user experience - use them wisely! 🍞✨

---

*Toast Notifications Guide v1.0*
*Created: October 18, 2025*
*For: AI Trading System*



