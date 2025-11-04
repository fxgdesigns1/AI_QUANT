#!/usr/bin/env python3
"""
Quick Aggressive Scanner - Optimized for Cloud Scheduler
Executes in < 30 seconds to avoid timeouts
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quick_aggressive_scan():
    """Fast scan that executes immediately"""
    from src.core.oanda_client import OandaClient
    from src.core.yaml_manager import get_yaml_manager
    import requests
    
    yaml_mgr = get_yaml_manager()
    accounts = yaml_mgr.get_all_accounts()
    account = accounts[0]
    account_id = account['id']
    
    client = OandaClient(account_id=account_id)
    account_info = client.get_account_info()
    balance = float(account_info.balance)
    
    # Scan only top 4 instruments for speed
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
    trades = 0
    
    for instrument in instruments:
        try:
            prices = client.get_current_prices([instrument], force_refresh=True)
            if instrument not in prices:
                continue
            
            # Quick momentum check - get only 10 candles
            headers = {
                'Authorization': f'Bearer {os.environ["OANDA_API_KEY"]}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
            response = requests.get(url, headers=headers, params={'count': 10, 'granularity': 'M5', 'price': 'M'}, timeout=5)
            data = response.json()
            
            if 'candles' not in data or len(data['candles']) < 8:
                continue
            
            closes = [float(c['mid']['c']) for c in data['candles'][-8:]]
            
            # Fast calculation
            ma_3 = sum(closes[-3:]) / 3
            ma_5 = sum(closes[-5:]) / 5
            momentum = (closes[-1] - closes[-5]) / closes[-5] * 100
            
            signal = None
            if ma_3 > ma_5 and momentum > 0.02:
                signal = 'BUY'
            elif ma_3 < ma_5 and momentum < -0.02:
                signal = 'SELL'
            
            if signal:
                price = prices[instrument]
                
                # Quick sizing
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
                        tp = entry + 0.20 if signal == 'BUY' else entry - 0.20
                        sl = entry - 0.10 if signal == 'BUY' else entry + 0.10
                    else:
                        tp = entry + 0.0020 if signal == 'BUY' else entry - 0.0020
                        sl = entry - 0.0010 if signal == 'BUY' else entry + 0.0010
                
                # Execute
                result = client.place_market_order(instrument=instrument, units=units, stop_loss=sl, take_profit=tp)
                
                if result:
                    trades += 1
                    logger.info(f"✅ {instrument} {signal} executed")
                    
                    # Quick Telegram
                    try:
                        msg = f"✅ {instrument} {signal}\n{abs(units):,} units @ {entry:.5f if 'XAU' not in instrument else entry:.2f}"
                        import os
                        token = os.getenv("TELEGRAM_TOKEN", "")
                        tg_url = f"https://api.telegram.org/bot{token}/sendMessage" if token else None
                        requests.post(tg_url, json={"chat_id": "6100678501", "text": msg}, timeout=3)
                    except:
                        pass
        except:
            continue
    
    return trades

if __name__ == '__main__':
    result = quick_aggressive_scan()
    logger.info(f"Scan complete: {result} trades")
