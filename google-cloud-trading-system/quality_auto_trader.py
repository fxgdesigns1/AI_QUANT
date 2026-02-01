#!/usr/bin/env python3
from src.core.settings import settings
"""
QUALITY AUTO-TRADER - Waits for proper entries, no chasing
Enters at optimal levels with confirmation
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quality_scan():
    """Scan for HIGH-QUALITY setups only - no chasing"""
    from src.core.oanda_client import OandaClient
    from src.core.yaml_manager import get_yaml_manager
    import requests
    
    logger.info("🎯 QUALITY SCAN - Looking for proper entries only")
    
    yaml_mgr = get_yaml_manager()
    accounts = yaml_mgr.get_all_accounts()
    account = accounts[0]
    account_id = account['id']
    
    client = OandaClient(account_id=account_id)
    account_info = client.get_account_info()
    balance = float(account_info.balance)
    
    # Check existing positions - don't chase if already in
    headers = {
        'Authorization': f'Bearer {os.environ["OANDA_API_KEY"]}',
        'Content-Type': 'application/json'
    }
    
    trades_url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades"
    trades_resp = requests.get(trades_url, headers=headers, timeout=5)
    existing_trades = trades_resp.json().get('trades', []) if trades_resp.status_code == 200 else []
    
    # Track what we're already in
    in_position = {t['instrument'] for t in existing_trades}
    logger.info(f"Already in {len(in_position)} positions: {in_position}")
    
    # Scan main instruments
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
    trades_executed = 0
    
    for instrument in instruments:
        # Skip if already in position - NO CHASING
        if instrument in in_position:
            logger.info(f"⏸️  {instrument}: Already in position - NOT adding")
            continue
        
        try:
            # Get current price
            prices = client.get_current_prices([instrument], force_refresh=True)
            if instrument not in prices:
                continue
            
            price = prices[instrument]
            
            # Get more candles for better analysis
            candles_url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
            candles_resp = requests.get(
                candles_url, 
                headers=headers, 
                params={'count': 30, 'granularity': 'M15', 'price': 'M'},  # 15-min for quality
                timeout=5
            )
            data = candles_resp.json()
            
            if 'candles' not in data or len(data['candles']) < 20:
                continue
            
            closes = [float(c['mid']['c']) for c in data['candles'][-20:]]
            highs = [float(c['mid']['h']) for c in data['candles'][-20:]]
            lows = [float(c['mid']['l']) for c in data['candles'][-20:]]
            
            # QUALITY CHECKS - Multiple confirmations required
            ma_5 = sum(closes[-5:]) / 5
            ma_10 = sum(closes[-10:]) / 10
            ma_20 = sum(closes) / 20
            
            current = closes[-1]
            prev = closes[-2]
            
            # Momentum - require stronger move
            momentum = (closes[-1] - closes[-10]) / closes[-10] * 100
            
            # Trend strength
            trend_strength = abs(ma_5 - ma_20) / ma_20 * 100
            
            # Price action
            rising = current > prev and current > closes[-3]
            falling = current < prev and current < closes[-3]
            
            # QUALITY ENTRY CONDITIONS
            # 1. Clear trend (not ranging)
            # 2. Good momentum (>0.05% for 10 bars)
            # 3. Aligned MAs
            # 4. Price confirming direction
            # 5. Not overextended
            
            signal = None
            quality_score = 0
            
            # BULLISH QUALITY SETUP
            if ma_5 > ma_10 > ma_20:  # Aligned MAs
                quality_score += 1
                if momentum > 0.05:  # Good momentum
                    quality_score += 1
                    if rising:  # Price confirming
                        quality_score += 1
                        if trend_strength > 0.15:  # Strong trend
                            quality_score += 1
                            if current < (ma_5 + ma_20) / 2:  # Not overextended
                                quality_score += 1
                                signal = 'BUY'
            
            # BEARISH QUALITY SETUP
            elif ma_5 < ma_10 < ma_20:  # Aligned MAs
                quality_score += 1
                if momentum < -0.05:  # Good momentum
                    quality_score += 1
                    if falling:  # Price confirming
                        quality_score += 1
                        if trend_strength > 0.15:  # Strong trend
                            quality_score += 1
                            if current > (ma_5 + ma_20) / 2:  # Not overextended
                                quality_score += 1
                                signal = 'SELL'
            
            # REQUIRE HIGH QUALITY (4/5 or 5/5)
            if signal and quality_score >= 4:
                logger.info(f"✅ {instrument} {signal} - Quality: {quality_score}/5, Momentum: {momentum:.2f}%")
                
                # Calculate proper sizing
                if 'XAU' in instrument:
                    units = int((balance * 0.01) / 2.5)
                    if signal == 'SELL':
                        units = -units
                    entry = price.bid if signal == 'SELL' else price.ask
                    tp = entry + 15.0 if signal == 'BUY' else entry - 15.0
                    sl = entry - 2.5 if signal == 'BUY' else entry + 2.5
                else:
                    units = int(((balance * 0.01) / 10) * 10000)
                    units = (units // 1000) * 1000
                    if signal == 'SELL':
                        units = -units
                    entry = price.bid if signal == 'SELL' else price.ask
                    
                    if 'JPY' in instrument:
                        tp = entry + 0.30 if signal == 'BUY' else entry - 0.30
                        sl = entry - 0.10 if signal == 'BUY' else entry + 0.10
                    else:
                        tp = entry + 0.0030 if signal == 'BUY' else entry - 0.0030
                        sl = entry - 0.0010 if signal == 'BUY' else entry + 0.0010
                
                # EXECUTE QUALITY ENTRY
                logger.info(f"⚡ ENTERING: {instrument} {signal} {abs(units)} units")
                result = client.place_market_order(
                    instrument=instrument,
                    units=units,
                    stop_loss=sl,
                    take_profit=tp
                )
                
                if result:
                    trades_executed += 1
                    logger.info(f"✅ QUALITY ENTRY FILLED: {instrument} {signal}")
                    
                    # Telegram
                    try:
                        bot_token = settings.telegram_bot_token
                        chat_id = settings.telegram_chat_id
                        if bot_token and chat_id:
                            msg = f"✅ QUALITY ENTRY\n\n{instrument} {signal}\nQuality: {quality_score}/5 ⭐\nMomentum: {momentum:+.2f}%\nUnits: {abs(units):,}\nEntry: {entry:.5f if 'XAU' not in instrument else entry:.2f}"
                            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            requests.post(tg_url, json={"chat_id": chat_id, "text": msg}, timeout=3)
                    except:
                        pass
            else:
                if quality_score > 0:
                    logger.info(f"⏸️  {instrument}: Quality {quality_score}/5 - WAITING for better setup")
        
        except Exception as e:
            logger.error(f"❌ {instrument} error: {e}")
            continue
    
    logger.info(f"✅ Quality scan complete: {trades_executed} trades executed")
    return trades_executed

if __name__ == '__main__':
    quality_scan()
