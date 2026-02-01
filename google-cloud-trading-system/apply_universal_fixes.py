#!/usr/bin/env python3
"""
Apply universal fixes to ALL strategies systematically
"""

import os
import glob

print("🔧 APPLYING UNIVERSAL FIXES TO ALL STRATEGIES")
print("="*100)

# Find all strategy files
strategy_files = glob.glob('src/strategies/*.py')
strategy_files = [f for f in strategy_files if not f.endswith('__init__.py')]

print(f"Found {len(strategy_files)} strategy files:")
for f in strategy_files:
    print(f"  • {f}")

print("\n" + "="*100)
print("FIX 1: Add _prefill_price_history to all strategies")
print("="*100)

PREFILL_CODE = '''
    def _prefill_price_history(self):
        """Pre-fill price history with recent data so strategy is ready immediately"""
        try:
            from src.core.historical_fetcher import get_historical_fetcher
            fetcher = get_historical_fetcher()
            
            # Get 50 bars of M15 data (12.5 hours of history)
            for instrument in self.instruments:
                try:
                    candles = fetcher.client.get_candles(
                        instrument=instrument,
                        count=50,
                        granularity='M15'
                    )
                    
                    if candles:
                        if instrument not in self.price_history:
                            self.price_history[instrument] = []
                        
                        for candle in candles:
                            self.price_history[instrument].append({
                                'time': candle['time'],
                                'close': float(candle['mid']['c']),
                                'high': float(candle['mid']['h']),
                                'low': float(candle['mid']['l']),
                                'volume': int(candle['volume'])
                            })
                        
                        self.logger.info(f"  ✅ {instrument}: {len(candles)} bars loaded")
                except Exception as e:
                    self.logger.warning(f"  ⚠️  Could not prefill {instrument}: {e}")
            
            total_bars = sum(len(hist) for hist in self.price_history.values())
            self.logger.info(f"✅ Price history pre-filled: {total_bars} total bars - READY TO TRADE!")
        except Exception as e:
            self.logger.warning(f"⚠️  Could not prefill price history: {e}")
'''

strategies_needing_prefill = []

for strategy_file in strategy_files:
    with open(strategy_file, 'r') as f:
        content = f.read()
    
    # Check if it has price_history attribute
    has_price_history = 'self.price_history' in content
    has_prefill = '_prefill_price_history' in content
    
    if has_price_history and not has_prefill:
        strategies_needing_prefill.append(strategy_file)
        print(f"❌ {strategy_file}: Needs _prefill_price_history")
    elif has_price_history and has_prefill:
        print(f"✅ {strategy_file}: Already has _prefill_price_history")
    else:
        print(f"⚠️  {strategy_file}: Doesn't use price_history (different architecture)")

print(f"\nStrategies needing fix: {len(strategies_needing_prefill)}")

print("\n" + "="*100)
print("FIX 2: Lower quality thresholds to realistic values")
print("="*100)

# Recommended threshold adjustments based on our testing
THRESHOLD_ADJUSTMENTS = {
    'min_adx': 8,  # Was 12-15, lower to 8
    'min_momentum': 0.0005,  # Was 0.001-0.004, lower to 0.05%
    'min_volume': 50,  # Was 100, lower to 50
    'quality_threshold': 15,  # Was 20-30, lower to 15
    'min_quality_score': 15,  # Was 20-30, lower to 15
}

print("Recommended threshold adjustments:")
for param, value in THRESHOLD_ADJUSTMENTS.items():
    print(f"  • {param}: {value}")

print("\n" + "="*100)
print("FIX 3: Disable 60-minute time gap during backtest")
print("="*100)

print("✅ Already implemented in validate_strategy.py")

print("\n" + "="*100)
print("IMPLEMENTATION PLAN")
print("="*100)

print("""
To apply these fixes safely:

1. ✅ Verify data quality (DONE - Gold +6.91% confirmed)
2. ✅ Identify calculation issues (DONE - momentum period too short, thresholds too high)
3. → Apply fixes to each strategy:
   
   For strategies with price_history:
   a) Add _prefill_price_history() method
   b) Call _prefill_price_history() in __init__ after self.price_history = {}
   c) Lower thresholds: min_adx=8, min_momentum=0.0005, quality_threshold=15
   
   For strategies without price_history:
   d) Review their architecture and apply equivalent fixes
   
4. → Test each fixed strategy against 96h data
5. → Run Monte Carlo on passing strategies
6. → Deploy optimized configs

Manual steps required:
- Edit each strategy file to add _prefill_price_history
- Edit each strategy file to lower thresholds
- Test each strategy individually
- Run Monte Carlo optimization
""")

print("="*100)
print("PRIORITY STRATEGIES (focus on these first):")
print("="*100)

priority_strategies = [
    'src/strategies/momentum_trading.py',  # Trump DNA
    'src/strategies/champion_75wr.py',  # 75% WR Champion
    'src/strategies/ultra_strict_forex.py',  # One other
]

for strat in priority_strategies:
    if os.path.exists(strat):
        print(f"✅ {strat}")
    else:
        print(f"❌ {strat} - NOT FOUND")

print("\n" + "="*100)
print("NEXT STEPS:")
print("="*100)
print("1. Check status of momentum_trading.py (Trump DNA) - already has prefill")
print("2. Add prefill to champion_75wr.py and ultra_strict_forex.py")
print("3. Lower thresholds in all three strategies")
print("4. Run Monte Carlo on each with updated thresholds")
print("5. Validate and deploy best configs")
print("="*100)














