#!/usr/bin/env python3
"""
Test ALL 10 Strategies Against This Week's Actual Market Data
Shows exactly what each strategy would have produced Mon-Thu
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator

print("📊 STRATEGY PERFORMANCE TEST - THIS WEEK (MON-THU)")
print("=" * 100)
print()

# Define all 10 active strategies
ALL_STRATEGIES = [
    {
        'name': 'momentum_trading',
        'display': '📈 Momentum Multi-Pair',
        'module': 'src.strategies.momentum_trading',
        'function': 'get_momentum_trading_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
        'account': '011'
    },
    {
        'name': 'gold_scalping',
        'display': '🥇 Gold Scalping',
        'module': 'src.strategies.gold_scalping',
        'function': 'get_gold_scalping_strategy',
        'instruments': ['XAU_USD'],
        'account': '009'
    },
    {
        'name': 'ultra_strict_forex',
        'display': '💱 Ultra Strict Fx',
        'module': 'src.strategies.ultra_strict_forex',
        'function': 'get_ultra_strict_forex_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'account': '010'
    },
    {
        'name': 'gbp_usd_5m_rank_1',
        'display': '🏆 Strategy #1',
        'module': 'src.strategies.gbp_usd_optimized',
        'function': 'get_strategy_rank_1',
        'instruments': ['GBP_USD'],
        'account': '008'
    },
    {
        'name': 'gbp_usd_5m_rank_2',
        'display': '🥈 Strategy #2',
        'module': 'src.strategies.gbp_usd_optimized',
        'function': 'get_strategy_rank_2',
        'instruments': ['GBP_USD', 'GBP_JPY'],
        'account': '007'
    },
    {
        'name': 'gbp_usd_5m_rank_3',
        'display': '🥉 Strategy #3',
        'module': 'src.strategies.gbp_usd_optimized',
        'function': 'get_strategy_rank_3',
        'instruments': ['GBP_USD', 'EUR_JPY'],
        'account': '006'
    },
    {
        'name': 'champion_75wr',
        'display': '🏆 75% WR Champion',
        'module': 'src.strategies.champion_75wr',
        'function': 'get_champion_75wr_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'account': '005'
    },
    {
        'name': 'ultra_strict_v2',
        'display': '💎 Ultra Strict V2',
        'module': 'src.strategies.ultra_strict_v2',
        'function': 'get_ultra_strict_v2_strategy',
        'instruments': ['EUR_USD', 'USD_JPY', 'AUD_USD'],
        'account': '004'
    },
    {
        'name': 'momentum_v2',
        'display': '⚡ Momentum V2',
        'module': 'src.strategies.momentum_v2',
        'function': 'get_momentum_v2_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'account': '003'
    },
    {
        'name': 'all_weather_70wr',
        'display': '🌦️ All-Weather 70WR',
        'module': 'src.strategies.all_weather_70wr',
        'function': 'get_all_weather_70wr_strategy',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD'],
        'account': '002'
    }
]

# Get 96 hours (4 days) of data to cover Mon-Thu
fetcher = get_historical_fetcher()

print("📥 Fetching this week's market data (96 hours = Mon-Thu)...")
print()

results = []

for i, strat_config in enumerate(ALL_STRATEGIES, 1):
    print(f"{i}/10: Testing {strat_config['display']}...", end=" ")
    
    try:
        # Import strategy
        module = __import__(strat_config['module'], fromlist=[strat_config['function']])
        get_strategy = getattr(module, strat_config['function'])
        strategy = get_strategy()
        
        # Get 96-hour historical data
        historical_data = {}
        for instrument in strat_config['instruments']:
            candles = fetcher.fetch_candles(instrument, count=384, granularity='M15')  # 96h @ M15
            if candles:
                historical_data[instrument] = []
                for candle in candles:
                    mid_data = candle.get('mid', {})
                    bid_data = candle.get('bid', {})
                    ask_data = candle.get('ask', {})
                    
                    historical_data[instrument].append({
                        'time': candle.get('time'),
                        'open': float(mid_data.get('o', 0)),
                        'high': float(mid_data.get('h', 0)),
                        'low': float(mid_data.get('l', 0)),
                        'close': float(mid_data.get('c', 0)),
                        'bid': float(bid_data.get('c', 0)) if bid_data else float(mid_data.get('c', 0)),
                        'ask': float(ask_data.get('c', 0)) if ask_data else float(mid_data.get('c', 0)),
                        'volume': int(candle.get('volume', 1000))
                    })
        
        # Run validation
        validator = StrategyValidator(strat_config['name'], lookback_hours=96)
        backtest_results = validator.run_strategy_backtest(strategy, historical_data)
        
        signals_96h = backtest_results['signals_generated']
        signals_per_day = signals_96h / 4  # 96h = 4 days
        avg_quality = backtest_results['avg_quality']
        
        # Estimate P&L (55% win rate, 1:3 R:R, 1% risk per trade)
        wins = int(signals_96h * 0.55)
        losses = int(signals_96h * 0.45)
        win_pnl = wins * 3000  # 3% gain
        loss_pnl = losses * 1000  # 1% loss
        net_pnl = win_pnl - loss_pnl
        
        results.append({
            'display': strat_config['display'],
            'account': strat_config['account'],
            'signals_96h': signals_96h,
            'signals_per_day': signals_per_day,
            'avg_quality': avg_quality,
            'wins': wins,
            'losses': losses,
            'net_pnl': net_pnl
        })
        
        status = "✅" if signals_per_day >= 3 else ("⚠️" if signals_per_day > 0 else "❌")
        print(f"{status} {signals_96h} signals, ~{signals_per_day:.1f}/day, \${net_pnl:,}")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:50]}")
        results.append({
            'display': strat_config['display'],
            'account': strat_config['account'],
            'signals_96h': 0,
            'signals_per_day': 0,
            'avg_quality': 0,
            'wins': 0,
            'losses': 0,
            'net_pnl': 0
        })

# Print full report
print()
print("=" * 100)
print("COMPLETE STRATEGY PERFORMANCE REPORT - THIS WEEK (MON-THU)")
print("=" * 100)
print()

print(f"{'Account':<10} {'Strategy':<30} {'Signals':<10} {'Per Day':<10} {'Quality':<10} {'Est P/L':<15} {'Status'}")
print("-" * 100)

total_signals = 0
total_pnl = 0

for r in results:
    quality_str = f"{r['avg_quality']:.1f}" if r['avg_quality'] > 0 else "N/A"
    pnl_str = f"\${r['net_pnl']:,}" if r['net_pnl'] != 0 else "\$0"
    
    if r['signals_per_day'] >= 5:
        status = "✅ EXCELLENT"
    elif r['signals_per_day'] >= 3:
        status = "✅ GOOD"
    elif r['signals_per_day'] > 0:
        status = "⚠️ LOW"
    else:
        status = "❌ NONE"
    
    print(f"{r['account']:<10} {r['display']:<30} {r['signals_96h']:<10} {r['signals_per_day']:<10.1f} {quality_str:<10} {pnl_str:<15} {status}")
    
    total_signals += r['signals_96h']
    total_pnl += r['net_pnl']

print("-" * 100)
print(f"{'TOTAL':<10} {'All 10 Strategies':<30} {total_signals:<10} {total_signals/4:<10.1f} {'':<10} \${total_pnl:,:<14} {''}")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print()

print(f"Total Signals This Week: {total_signals}")
print(f"Average Per Day: {total_signals / 4:.1f}")
print(f"Average Per Strategy: {total_signals / 10:.1f}")
print()

print(f"Estimated Weekly P/L (All 10 Accounts): \${total_pnl:,}")
print(f"Monthly Projection (4 weeks): \${total_pnl * 4:,}")
print()

if total_signals == 0:
    print("❌ CRITICAL: ZERO signals across all strategies!")
    print("   All strategies have the empty price history bug!")
    print("   Need to apply universal fix to all 9 remaining strategies.")
elif total_signals < 150:  # 10 strategies × 15 minimum
    print("⚠️  LOW: Signal count below target")
    print(f"   Expected: 150-200 signals minimum (15-20 per strategy)")
    print(f"   Actual: {total_signals}")
    print("   Some strategies need the prefill fix applied.")
else:
    print("✅ HEALTHY: Good signal generation across strategies")
    print(f"   {total_signals} signals is excellent for 4 days")

print()
print("=" * 100)







