#!/usr/bin/env python3
"""
Market Update & Execute Ready Positions
Checks system status, sends Telegram market update, and executes ready trades
"""

import os
import sys
import requests
import json
from datetime import datetime
from typing import Dict, List, Any

# Add google-cloud-trading-system to path
trading_system_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system')
sys.path.insert(0, trading_system_path)
sys.path.insert(0, os.path.join(trading_system_path, 'src'))

# Import with try/except for graceful fallback
try:
    from src.core.telegram_notifier import get_telegram_notifier
    from src.core.order_manager import OrderManager
    from src.core.account_manager import get_account_manager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Some imports failed: {e}")
    IMPORTS_AVAILABLE = False
    # Fallback: use direct API calls only

# Configuration
GOOGLE_CLOUD_URL = os.getenv('GOOGLE_CLOUD_TRADING_URL', 'https://ai-quant-trading.uc.r.appspot.com')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def check_system_status() -> Dict[str, Any]:
    """Check system status via API"""
    try:
        response = requests.get(f"{GOOGLE_CLOUD_URL}/api/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_market_data() -> Dict[str, Any]:
    """Get current market data"""
    try:
        response = requests.get(f"{GOOGLE_CLOUD_URL}/api/sidebar/live-prices", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"⚠️ Market data fetch failed: {e}")
        return {}

def scan_for_signals() -> List[Dict[str, Any]]:
    """Trigger scan for trading signals"""
    try:
        # Use the premium scan endpoint
        scan_token = os.getenv('SCAN_TRIGGER_TOKEN', 'scan_7d8f5c5f8b2a4a8f')
        response = requests.post(
            f"{GOOGLE_CLOUD_URL}/api/premium/scan",
            json={"token": scan_token},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('signals', [])
        else:
            print(f"⚠️ Scan returned HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Scan failed: {e}")
        return []

def execute_position(signal: Dict[str, Any]) -> bool:
    """Execute a trading position via API"""
    try:
        if not IMPORTS_AVAILABLE:
            # Fallback: use API endpoint
            response = requests.post(
                f"{GOOGLE_CLOUD_URL}/api/premium/execute",
                json={"signal": signal},
                timeout=30
            )
            return response.status_code == 200
        
        account_id = signal.get('account_id')
        instrument = signal.get('instrument')
        side = signal.get('side')
        entry_price = signal.get('entry_price')
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        confidence = signal.get('confidence', 0.7)
        strategy = signal.get('strategy', 'Unknown')
        
        if not all([account_id, instrument, side, entry_price]):
            print(f"⚠️ Incomplete signal data: {signal}")
            return False
        
        # Get order manager
        order_manager = OrderManager(account_id=account_id)
        
        # Create trade signal
        from src.core.models import TradeSignal, TradeSide
        trade_side = TradeSide.BUY if side.upper() == 'BUY' else TradeSide.SELL
        
        trade_signal = TradeSignal(
            account_id=account_id,
            instrument=instrument,
            side=trade_side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strategy=strategy
        )
        
        # Execute trade
        execution = order_manager.execute_trade(trade_signal)
        
        if execution.success:
            print(f"✅ Trade executed: {instrument} {side} @ {entry_price}")
            
            # Send Telegram alert
            telegram = get_telegram_notifier()
            if telegram and telegram.enabled:
                account_manager = get_account_manager()
                account_name = account_manager.get_account_display_name(account_id) or f"Account {account_id[-3:]}"
                
                telegram.send_trade_alert(
                    account_name=account_name,
                    instrument=instrument,
                    side=side,
                    price=entry_price,
                    confidence=confidence,
                    strategy=strategy,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=execution.order.units if execution.order else None
                )
            
            return True
        else:
            print(f"❌ Trade execution failed: {execution.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Position execution error: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_market_update(status: Dict, market_data: Dict) -> str:
    """Create formatted market update message"""
    status_emoji = "✅" if status.get('status') == 'online' else "⚠️"
    status_text = status.get('status', 'unknown').upper()
    
    lines = [
        f"📊 <b>MARKET UPDATE</b>",
        f"",
        f"<b>System Status:</b> {status_emoji} {status_text}",
        f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f""
    ]
    
    # Add market prices if available
    if market_data and 'prices' in market_data:
        lines.append("<b>Current Prices:</b>")
        prices = market_data['prices']
        for pair, price_info in list(prices.items())[:5]:  # Top 5 pairs
            if isinstance(price_info, dict):
                bid = price_info.get('bid', 0)
                ask = price_info.get('ask', 0)
                spread = (ask - bid) * 10000 if ask > bid else 0
                lines.append(f"• {pair}: {bid:.5f} / {ask:.5f} (spread: {spread:.1f} pips)")
            else:
                lines.append(f"• {pair}: {price_info}")
        lines.append("")
    
    # Add account info if available
    if status.get('active_accounts', 0) > 0:
        lines.append(f"<b>Active Accounts:</b> {status.get('active_accounts', 0)}")
    
    lines.append(f"")
    lines.append(f"#MarketUpdate #{datetime.now().strftime('%Y%m%d')}")
    
    return "\n".join(lines)

def main():
    """Main execution"""
    print("=" * 70)
    print("📊 MARKET UPDATE & POSITION EXECUTION")
    print("=" * 70)
    
    # 1. Check system status
    print("\n1️⃣ Checking system status...")
    status = check_system_status()
    print(f"   Status: {status.get('status', 'unknown')}")
    
    # 2. Get market data
    print("\n2️⃣ Fetching market data...")
    market_data = get_market_data()
    print(f"   Market data: {'✅' if market_data else '❌'}")
    
    # 3. Send Telegram market update
    print("\n3️⃣ Sending Telegram market update...")
    telegram = None
    if IMPORTS_AVAILABLE:
        telegram = get_telegram_notifier()
    if telegram and telegram.enabled:
        market_update = create_market_update(status, market_data)
        success = telegram.send_message(market_update, message_type="market_update")
        if success:
            print("   ✅ Market update sent to Telegram")
        else:
            print("   ⚠️ Failed to send market update (rate limited or disabled)")
    else:
        print("   ⚠️ Telegram notifier disabled or not configured")
    
    # 4. Scan for ready positions
    print("\n4️⃣ Scanning for ready positions...")
    signals = scan_for_signals()
    print(f"   Found {len(signals)} ready positions")
    
    # 5. Execute ready positions
    if signals:
        print("\n5️⃣ Executing ready positions...")
        executed = 0
        for signal in signals:
            if execute_position(signal):
                executed += 1
        
        print(f"\n✅ Execution complete: {executed}/{len(signals)} positions entered")
        
        # Send summary to Telegram
        if IMPORTS_AVAILABLE and telegram and telegram.enabled and executed > 0:
            summary = f"""
🎯 <b>POSITION EXECUTION SUMMARY</b>

<b>Executed:</b> {executed} positions
<b>Total Signals:</b> {len(signals)}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

#TradingAlert #ExecutionSummary
            """.strip()
            telegram.send_message(summary, message_type="execution_summary")
    else:
        print("\n✅ No ready positions found - waiting for better setups")
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()

