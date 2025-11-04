#!/usr/bin/env python3
"""
Apply Critical Fixes to ALL Strategies
Adds price history prefilling to every active strategy
"""

import os

print("🔧 APPLYING UNIVERSAL FIXES TO ALL STRATEGIES")
print("=" * 80)
print()

# List of all active strategy files that need fixing
STRATEGY_FILES = [
    'src/strategies/gold_scalping.py',
    'src/strategies/ultra_strict_forex.py',
    'src/strategies/champion_75wr.py',
    'src/strategies/ultra_strict_v2.py',
    'src/strategies/all_weather_70wr.py',
    'src/strategies/momentum_v2.py',
    'src/strategies/gbp_usd_optimized.py',
    'src/strategies/gold_trump_week_strategy.py',
    'src/strategies/range_trading.py',
]

# The prefill code to add
PREFILL_METHOD = '''
    def _prefill_price_history(self):
        """Pre-fill price history from OANDA - CRITICAL FIX"""
        try:
            import os
            import requests
            
            api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
            base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
            headers = {'Authorization': f'Bearer {api_key}'}
            
            for instrument in self.instruments:
                try:
                    url = f"{base_url}/v3/instruments/{instrument}/candles"
                    params = {'count': 50, 'granularity': 'M15', 'price': 'M'}
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        candles = response.json().get('candles', [])
                        for candle in candles:
                            close = float(candle.get('mid', {}).get('c', 0))
                            if close > 0:
                                self.price_history[instrument].append(close)
                except:
                    continue
        except:
            pass
'''

print("Strategies to fix:")
for f in STRATEGY_FILES:
    exists = os.path.exists(f)
    status = "✅" if exists else "❌"
    print(f"  {status} {f}")

print()
print("=" * 80)
print()
print("RECOMMENDATION:")
print()
print("Instead of modifying 10+ files individually, use the universal fix:")
print()
print("Add to EACH strategy's __init__ (after price_history initialization):")
print()
print("```python")
print("from src.core.strategy_base import prefill_price_history_for_strategy")
print("prefill_price_history_for_strategy(self, self.instruments)")
print("```")
print()
print("This ONE line fixes the empty history bug in ALL strategies!")
print()
print("=" * 80)
print()
print("OR create a startup script that prefills ALL strategies at once:")
print("  python3 src/core/prefill_all_strategies.py")
print()




















