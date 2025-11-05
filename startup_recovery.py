#!/usr/bin/env python3
"""
STARTUP RECOVERY SCRIPT
Clears stale halts and ensures system is ready for trading
Run this on Monday mornings or after system restarts
"""
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from ai_trading_system import AITradingSystem
    
    logger.info("🚀 Starting recovery check...")
    
    system = AITradingSystem()
    
    # Force clear any halts
    now = datetime.utcnow()
    weekday = now.weekday()
    
    logger.info(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"📅 Day of week: {weekday} (0=Monday, 6=Sunday)")
    
    # Clear news halts
    if system.news_halt_until:
        logger.info(f"🧹 Clearing news halt (was until: {system.news_halt_until})")
        system.news_halt_until = None
    else:
        logger.info("✅ No news halt active")
    
    # Clear sentiment throttles
    if system.throttle_until:
        logger.info(f"🧹 Clearing sentiment throttle (was until: {system.throttle_until})")
        system.throttle_until = None
        # Restore risk
        if hasattr(system, 'base_risk'):
            system.risk_per_trade = system.base_risk
            logger.info(f"✅ Risk restored to {system.risk_per_trade*100:.1f}%")
    else:
        logger.info("✅ No sentiment throttle active")
    
    # Ensure trading is enabled
    if not system.trading_enabled:
        logger.warning("⚠️ Trading is disabled - enabling...")
        system.trading_enabled = True
        logger.info("✅ Trading enabled")
    else:
        logger.info("✅ Trading is enabled")
    
    # Send Telegram notification
    try:
        message = f"""🔄 STARTUP RECOVERY COMPLETE

📅 Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}
✅ Stale halts cleared
✅ System ready for trading
💰 Risk: {system.risk_per_trade*100:.1f}%
⚙️ Trading: {'ENABLED' if system.trading_enabled else 'DISABLED'}

🚀 System is ready to trade!"""
        
        system.send_telegram_message(message)
        logger.info("✅ Recovery notification sent")
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
    
    logger.info("✅ Recovery complete - System is ready")
    
except Exception as e:
    logger.error(f"❌ Recovery failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
